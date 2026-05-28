#!/usr/bin/env python3
"""Rank local Medical AI Skills skills and verifiers for a short engineering task."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[int("3")]

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("find_skills requires PyYAML (repo v0 dependency)") from exc


def load_manifest(path: Path) -> dict:
    """Load a YAML skill manifest (stdlib-only; no eval_engine import)."""
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"invalid YAML in {path}: {e}") from e
    if not isinstance(data, dict):
        raise ValueError(f"manifest root must be a mapping: {path}")
    return data


def iter_spec_manifests() -> list[Path]:
    """Committed skill and verifier manifests, excluding fixture specs."""
    manifests: list[Path] = []
    for root_name in ("skills", "verifiers"):
        root = REPO_ROOT / root_name
        if not root.is_dir():
            continue
        for manifest_path in sorted(root.rglob("skill_manifest.yaml")):
            if "fixtures" in manifest_path.relative_to(root).parts:
                continue
            manifests.append(manifest_path)
    return manifests

STOPWORDS = frozenset(
    "a an and are can do for have how i in is it me my of or the to use want with".split()
)
NO_GPU_SENTINELS: frozenset[Any] = frozenset({None, False, "", "none"})
_WORD_RE = re.compile(r"[a-z0-9]+")


def _words(value: Any) -> list[str]:
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True)
    words = _WORD_RE.findall(text.replace("_", " ").replace("-", " ").lower())
    return [word for word in words if word not in STOPWORDS and len(word) > 1]


def _read_query(raw: str) -> str:
    candidate = Path(raw)
    if candidate.exists() and candidate.is_file():
        return candidate.read_text().strip()
    return raw.strip()


def _project_io(items: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "name": item.get("name", ""),
            "type": item.get("type", ""),
            "formats": item.get("formats", []),
        }
        for item in items
        if isinstance(item, dict)
    ]


def _candidate(manifest_path: Path, kind: str) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    skill_dir = manifest_path.parent
    intended_use = manifest.get("intended_use") or {}
    runtime = manifest.get("runtime") or {}
    side_effects = runtime.get("side_effects") or {}
    inputs = manifest.get("inputs") or []
    outputs = manifest.get("outputs") or []
    limitations = manifest.get("limitations") or []
    paired = manifest.get("paired_verifiers") or []
    rel_path = skill_dir.relative_to(REPO_ROOT).as_posix()
    searchable = {
        "id": manifest.get("id") or skill_dir.name,
        "path": rel_path,
        "summary": intended_use.get("summary") or "",
        "inputs": inputs,
        "outputs": outputs,
        "limitations": limitations,
        "paired_verifiers": paired,
        "not_for": intended_use.get("not_for") or [],
    }
    return {
        "id": manifest.get("id") or skill_dir.name,
        "path": rel_path,
        "kind": kind,
        "summary": " ".join(str(intended_use.get("summary") or "").split()),
        "scope": intended_use.get("scope") or "",
        "not_for": intended_use.get("not_for") or [],
        "inputs": _project_io(inputs),
        "outputs": _project_io(outputs),
        "paired_verifiers": [
            {"id": item.get("id", ""), "status": item.get("status", "")}
            for item in paired
            if isinstance(item, dict)
        ],
        "requires_gpu": side_effects.get("requires_gpu", "none"),
        "requires_docker": bool(side_effects.get("requires_docker")),
        "limitations": [" ".join(str(item).split()) for item in limitations[:int("3")]],
        "_search_words": frozenset(_words(searchable)),
    }


def _iter_candidates() -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for path in iter_spec_manifests():
        if path.parent.name == "find-skills":
            continue
        kind = "skill" if path.parent.parent.name == "skills" else "verifier"
        candidates.append(_candidate(path, kind))
    return candidates


def _score(
    query_words: set[str],
    query_l: str,
    candidate: dict[str, Any],
) -> tuple[int, list[str]]:
    matched = sorted(query_words & candidate["_search_words"])
    score = len(matched)

    cid = str(candidate["id"]).lower()
    if {"ct", "segment"} <= query_words and "segment_ct" in cid:
        score += int("8")
    if {"dicom", "metadata"} <= query_words and "dicom_metadata" in cid:
        score += int("8")
    if {"dicom", "series", "volume"} <= query_words and "dicom_series_to_volume" in cid:
        score += int("8")
    if "radiology" in query_words and "summarizer" in cid:
        score += int("8")
    if "endoscopy" in query_words and "endoscopy" in cid:
        score += int("5")
    if "benchmark" in query_words and "benchmark" in cid:
        score += int("5")
    if "audit" in query_words and "completeness" in cid:
        score += int("5")
    if "verifier" in query_l and candidate["kind"] == "verifier":
        score += int("3")

    return score, matched


def _rationale(candidate: dict[str, Any], matched_terms: list[str]) -> str:
    bits: list[str] = []
    if matched_terms:
        bits.append("matched terms: " + ", ".join(matched_terms[:int("8")]))
    if candidate["inputs"]:
        bits.append(
            "inputs: "
            + ", ".join(
                f"{item['name']}({','.join(item.get('formats') or []) or item['type']})"
                for item in candidate["inputs"][:2]
            )
        )
    if candidate["outputs"]:
        bits.append(
            "outputs: "
            + ", ".join(item["name"] or item["type"] for item in candidate["outputs"][:2])
        )
    return "; ".join(bits) or "closest declared spec match"


def _caveats(candidate: dict[str, Any]) -> list[str]:
    caveats: list[str] = []
    if candidate.get("requires_gpu") not in NO_GPU_SENTINELS:
        caveats.append(f"requires GPU: {candidate['requires_gpu']}")
    if candidate.get("requires_docker"):
        caveats.append("requires Docker")
    for item in candidate.get("limitations", [])[:2]:
        if item:
            caveats.append(item)
    return caveats


def recommend(query: str, *, limit: int = int("3")) -> dict[str, Any]:
    candidates = _iter_candidates()
    query_words = set(_words(query))
    query_l = query.lower()
    ranked: list[dict[str, Any]] = []
    for candidate in candidates:
        score, matched = _score(query_words, query_l, candidate)
        public = {k: v for k, v in candidate.items() if not k.startswith("_")}
        public.update(
            {
                "score": score,
                "matched_terms": matched,
                "rationale": _rationale(candidate, matched),
                "caveats": _caveats(candidate),
            }
        )
        ranked.append(public)
    ranked.sort(key=lambda item: (-int(item["score"]), str(item["id"])))
    recommendations = ranked[: max(1, limit)]
    no_fit = not recommendations or int(recommendations[0]["score"]) <= 0
    return {
        "skill": "find_skills",
        "input": {"query": query},
        "catalog": {"count": len(candidates)},
        "top_recommendation": recommendations[0] if recommendations else {},
        "recommendations": recommendations,
        "no_fit": no_fit,
        "intended_use_disclaimer": (
            "Engineering selection aid only. Verify the chosen skill's manifest, "
            "side effects, and limitations before running it."
        ),
    }


def _markdown(payload: dict[str, Any]) -> str:
    query = payload["input"]["query"]
    recs = payload["recommendations"]
    lines = [f"Query: {query}", ""]
    if payload["no_fit"]:
        lines.append("No strong committed Medical AI Skills skill match was found.")
        lines.append("")
    for idx, rec in enumerate(recs, start=1):
        lines.append(f"{idx}. `{rec['id']}` ({rec['kind']}, path: `{rec['path']}`)")
        lines.append(f"   Score: {rec['score']}")
        lines.append(f"   Why: {rec['rationale']}")
        if rec["caveats"]:
            lines.append("   Caveats: " + " | ".join(rec["caveats"][:int("3")]))
        lines.append("")
    lines.append(payload["intended_use_disclaimer"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="task text or path to a text fixture")
    parser.add_argument("--limit", type=int, default=int("3"), help="number of matches to emit")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--markdown", action="store_true", help="emit markdown")
    args = parser.parse_args(argv)

    query = _read_query(args.query)
    payload = recommend(query, limit=args.limit)
    emit_json = args.json or not args.markdown
    if emit_json:
        sys.stdout.write(json.dumps(payload, indent=2))
    else:
        sys.stdout.write(_markdown(payload))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
