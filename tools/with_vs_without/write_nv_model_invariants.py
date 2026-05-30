#!/usr/bin/env python3
"""Write stable NV with-vs-without invariant snapshots.

Raw study records are intentionally local and ignored. This snapshot is the
small, git-trackable surface that should change only when the protocol,
selected documentation, staged-source fixtures, backend protocol, or material
outcomes change.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.with_vs_without import audit_nv_model_studies as audit  # noqa: E402
from tools.with_vs_without import (
    manifest_nv_model_data_transfer as transfer,
)  # noqa: E402
from tools.with_vs_without import run_nv_model_studies as studies  # noqa: E402

SNAPSHOT_PATH = REPO_ROOT / "tools/with_vs_without/data/nv_model_study_invariants.json"
SCHEMA_VERSION = 1
EXPERIMENT_ID = "nv-model-with-vs-without"
EXCLUDED_FIELDS = (
    "absolute local paths",
    "generated commands",
    "provider responses",
    "stdout/stderr tails",
    "token usage",
    "timestamps",
    "run logs",
    "environment.lock content",
    "downloaded model/cache paths",
)


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return _sha256_bytes(encoded)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _git_tracked_files(path: Path) -> list[str]:
    rel = _rel(path)
    try:
        proc = subprocess.run(
            ["git", "ls-files", "--", rel],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except Exception:
        return []
    return sorted(line.strip() for line in proc.stdout.splitlines() if line.strip())


def _tracked_path_fingerprint(path_text: str) -> dict[str, Any]:
    path = REPO_ROOT / path_text
    if not path.exists():
        return {
            "path": path_text,
            "exists": False,
            "kind": "missing",
            "tracked_file_count": 0,
            "byte_count": 0,
            "sha256": None,
        }

    tracked_files = _git_tracked_files(path)
    if path.is_file() and not tracked_files:
        data = path.read_bytes()
        return {
            "path": path_text,
            "exists": True,
            "kind": "file",
            "tracked_file_count": 0,
            "byte_count": len(data),
            "sha256": _sha256_bytes(data),
        }

    file_records: list[dict[str, Any]] = []
    total_bytes = 0
    for rel_file in tracked_files:
        data = (REPO_ROOT / rel_file).read_bytes()
        total_bytes += len(data)
        file_records.append(
            {"path": rel_file, "byte_count": len(data), "sha256": _sha256_bytes(data)}
        )
    return {
        "path": path_text,
        "exists": True,
        "kind": "directory" if path.is_dir() else "file",
        "tracked_file_count": len(file_records),
        "byte_count": total_bytes,
        "sha256": _sha256_json(file_records),
    }


def _repeat_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(record.get("repeats"), list):
        return list(record["repeats"])
    if isinstance(record.get("final"), dict):
        return [record["final"]]
    return [record]


def _repeat_outcomes(record: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for repeat in _repeat_rows(record):
        score = repeat.get("score") or {}
        rows.append(
            {
                "repeat": int(repeat.get("repeat", len(rows) + 1)),
                "passed": bool(score.get("passed")),
                "score": score.get("score"),
                "steps_to_pass": repeat.get("steps_to_pass", "unresolved"),
            }
        )
    return rows


def _summary_from_record(record: dict[str, Any]) -> dict[str, Any]:
    outcomes = _repeat_outcomes(record)
    scores = [
        row["score"]
        for row in outcomes
        if isinstance(row.get("score"), (int, float))
        and not isinstance(row["score"], bool)
    ]
    return {
        "backend": str(record.get("backend", "")),
        "arm": str(record.get("arm", "")),
        "repeat_count": len(outcomes),
        "pass_count": sum(1 for row in outcomes if row["passed"]),
        "scores": scores,
        "mean_score": (sum(scores) / len(scores)) if scores else None,
        "steps_to_pass": [row["steps_to_pass"] for row in outcomes],
        "outcome_fingerprint": _sha256_json(outcomes),
    }


def _aggregate_summaries(
    skill: str, mode: str, study_root: Path
) -> list[dict[str, Any]]:
    study_dir = audit._study_dir_for_mode(study_root, skill, mode)
    rows: list[dict[str, Any]] = []
    for backend, arm, filename in audit._study_checks_for_mode(mode):
        path = study_dir / filename
        if not path.exists():
            rows.append(
                {
                    "backend": backend,
                    "arm": arm,
                    "repeat_count": 0,
                    "pass_count": 0,
                    "scores": [],
                    "mean_score": None,
                    "steps_to_pass": [],
                    "outcome_fingerprint": None,
                    "missing": True,
                }
            )
            continue
        rows.append(_summary_from_record(_read_json(path)))
    return sorted(rows, key=lambda row: (row["backend"], row["arm"]))


def _snapshot_documents(transfer_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    by_path: dict[str, dict[str, Any]] = {}
    for entry in transfer_manifest.get("entries", []):
        for doc in entry.get("documentation", []):
            if isinstance(doc, dict) and isinstance(doc.get("path"), str):
                by_path[doc["path"]] = {
                    "path": doc["path"],
                    "exists": bool(doc.get("exists")),
                    "byte_count": int(doc.get("byte_count") or 0),
                    "sha256": doc.get("sha256"),
                }
    return [by_path[path] for path in sorted(by_path)]


def _prompt_artifact_records(
    skills: list[str], prompt_root: Path
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for skill in skills:
        path = prompt_root / f"eval_nv_model_studies_{skill}_prompts.json"
        data = path.read_bytes() if path.exists() else b""
        parsed = json.loads(data) if data else []
        rows.append(
            {
                "skill": skill,
                "path": _rel(path),
                "exists": path.exists(),
                "record_count": len(parsed) if isinstance(parsed, list) else None,
                "sha256": _sha256_bytes(data) if data else None,
            }
        )
    return rows


def _outcome_records(
    audit_report: dict[str, Any],
    *,
    study_root: Path,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for skill_record in audit_report["skills"]:
        skill = str(skill_record["skill"])
        modes = []
        for mode_record in skill_record["outcome"]["modes"]:
            mode = str(mode_record["mode"])
            paired = {
                key: mode_record.get(key)
                for key in (
                    "expected_pairs",
                    "matched",
                    "with_wins",
                    "without_wins",
                    "ties",
                    "signal",
                    "status",
                    "supports_skill_advantage",
                    "reason",
                )
            }
            sign_test = mode_record.get("paired_sign_test") or {}
            paired["decisive_pairs"] = sign_test.get("decisive_pairs")
            paired["one_sided_sign_test_p"] = sign_test.get("one_sided_sign_test_p")
            aggregate_summaries = _aggregate_summaries(skill, mode, study_root)
            modes.append(
                {
                    "mode": mode,
                    "paired_outcome": paired,
                    "aggregate_summaries": aggregate_summaries,
                    "mode_fingerprint": _sha256_json(
                        {"paired": paired, "aggregates": aggregate_summaries}
                    ),
                }
            )
        rows.append(
            {
                "skill": skill,
                "status": skill_record["status"],
                "prompt_artifact_status": skill_record["prompt_artifact"]["status"],
                "study_artifact_status": skill_record["study_artifacts"]["status"],
                "outcome_status": skill_record["outcome"]["status"],
                "modes": sorted(modes, key=lambda row: row["mode"]),
            }
        )
    return sorted(rows, key=lambda row: row["skill"])


def build_snapshot(
    *,
    skills: list[str] | None = None,
    repeats: int = studies.DIRECT_REPEATS,
    prompt_root: Path = studies.PROMPT_ARTIFACT_ROOT,
    study_root: Path = studies.STUDY_ROOT,
) -> dict[str, Any]:
    selected = skills or sorted(studies.SCENARIOS)
    audit_report = audit.audit_all(
        skills=selected, prompt_root=prompt_root, study_root=study_root, repeats=repeats
    )
    transfer_manifest = transfer.build_manifest(
        skills=selected,
        mode="all",
        repeats=repeats,
        max_correction_steps=studies.DIRECT_MAX_CORRECTION_STEPS,
        resume_missing=True,
        study_root=study_root,
    )
    documents = _snapshot_documents(transfer_manifest)
    prompt_artifacts = _prompt_artifact_records(selected, prompt_root)
    source_fixtures = [
        _tracked_path_fingerprint(studies.SCENARIOS[skill].fixture)
        for skill in selected
    ]
    staged_inputs = [
        {
            "skill": skill,
            "staged_user_input": str(
                studies._staged_input_path(studies.SCENARIOS[skill]).relative_to(
                    REPO_ROOT
                )
            ),
            "source_fixture": studies.SCENARIOS[skill].fixture,
        }
        for skill in selected
    ]
    outcomes = _outcome_records(audit_report, study_root=study_root)
    protocol = {
        "direct_prompt_style": "minimal",
        "path_prompt_style": "path",
        "max_correction_steps": studies.DIRECT_MAX_CORRECTION_STEPS,
        "repeats": repeats,
        "arms": ["with", "without"],
        "modes": ["codex-opus", "nemotron-correction"],
        "skills": selected,
    }
    material = {
        "protocol": protocol,
        "payload_fingerprint": transfer_manifest["payload_fingerprint"],
        "backend_protocols": transfer_manifest["summary"]["backend_protocols"],
        "documents": documents,
        "prompt_artifacts": prompt_artifacts,
        "source_fixtures": source_fixtures,
        "staged_inputs": staged_inputs,
        "outcomes": outcomes,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "generated_by": "tools/with_vs_without/write_nv_model_invariants.py",
        "record_policy": {
            "track_in_git": True,
            "raw_records_location": "runs/with_vs_without_nv/",
            "excluded_fields": list(EXCLUDED_FIELDS),
        },
        "audit_status": audit_report["status"],
        "audit_summary": audit_report["summary"],
        "fingerprints": {
            "payload": transfer_manifest["payload_fingerprint"],
            "documents": _sha256_json(documents),
            "source_fixtures": _sha256_json(source_fixtures),
            "prompt_artifacts": _sha256_json(prompt_artifacts),
            "outcomes": _sha256_json(outcomes),
            "material": _sha256_json(material),
        },
        **material,
    }


def snapshot_text(snapshot: dict[str, Any]) -> str:
    return json.dumps(snapshot, indent=2, sort_keys=True) + "\n"


def write_snapshot(
    *,
    output: Path = SNAPSHOT_PATH,
    skills: list[str] | None = None,
    repeats: int = studies.DIRECT_REPEATS,
) -> dict[str, Any]:
    snapshot = build_snapshot(skills=skills, repeats=repeats)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(snapshot_text(snapshot))
    return snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=SNAPSHOT_PATH)
    parser.add_argument("--repeats", type=int, default=studies.DIRECT_REPEATS)
    parser.add_argument("--skills", nargs="+", choices=sorted(studies.SCENARIOS))
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the output file does not match the current local invariant snapshot",
    )
    args = parser.parse_args(argv)
    snapshot = build_snapshot(skills=args.skills, repeats=args.repeats)
    text = snapshot_text(snapshot)
    if args.check:
        current = args.output.read_text() if args.output.exists() else ""
        if current != text:
            print(
                f"invariant snapshot is out of date: {_rel(args.output)}",
                file=sys.stderr,
            )
            return 1
        print(f"invariant snapshot is current: {_rel(args.output)}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text)
    print(f"wrote invariant snapshot: {_rel(args.output)}")
    print(f"material fingerprint: {snapshot['fingerprints']['material']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
