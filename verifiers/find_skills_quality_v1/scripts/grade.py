#!/usr/bin/env python3
"""Verify find_skills evidence packs."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from verifiers._shared.verifier_kit import load_pack_json, make_check, run_grader  # noqa: E402

VERIFIER_ID = "medagent.verifiers.find_skills_quality_v1"
VERIFIER_VERSION = "0.1.0"
TARGET_SKILL_IDS = {"find_skills", "medagent.find_skills"}
DISCLAIMER_TERMS = ("Engineering selection aid only", "Verify the chosen skill's manifest")
_WORD_RE = re.compile(r"[a-z0-9]+")


def _public_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def _words(text: Any) -> set[str]:
    raw = text if isinstance(text, str) else json.dumps(text, sort_keys=True)
    return set(_WORD_RE.findall(raw.replace("_", " ").replace("-", " ").lower()))


def _manifest_for(path_value: Any) -> tuple[Path | None, dict[str, Any]]:
    if not isinstance(path_value, str) or not path_value:
        return None, {}
    if path_value.startswith("/") or ".." in Path(path_value).parts:
        return None, {}
    manifest_path = REPO_ROOT / path_value / "skill_manifest.yaml"
    if not manifest_path.is_file():
        return manifest_path, {}
    try:
        data = yaml.safe_load(manifest_path.read_text()) or {}
    except yaml.YAMLError:
        return manifest_path, {}
    return manifest_path, data if isinstance(data, dict) else {}


def _recommendation_path_checks(recommendations: list[Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for idx, rec in enumerate(recommendations):
        if not isinstance(rec, dict):
            checks.append(make_check(f"recommendation_{idx}_shape", False, "recommendation must be an object"))
            continue
        rec_id = rec.get("id")
        rec_path = rec.get("path")
        rec_kind = rec.get("kind")
        manifest_path, manifest = _manifest_for(rec_path)
        checks.append(
            make_check(
                f"recommendation_{idx}_manifest_exists",
                bool(manifest),
                f"id={rec_id!r}, path={rec_path!r}",
            )
        )
        if manifest:
            expected_kind = "skill" if str(rec_path).startswith("skills/") else "verifier"
            checks.extend(
                [
                    make_check(
                        f"recommendation_{idx}_id_matches_manifest",
                        manifest.get("id") == rec_id,
                        f"reported={rec_id!r}, manifest={manifest.get('id')!r}",
                    ),
                    make_check(
                        f"recommendation_{idx}_kind_matches_path",
                        rec_kind == expected_kind,
                        f"reported={rec_kind!r}, expected={expected_kind!r}",
                    ),
                ]
            )
        elif manifest_path is not None:
            checks.append(
                make_check(
                    f"recommendation_{idx}_manifest_readable",
                    False,
                    f"manifest path did not parse: {_public_path(manifest_path)}",
                )
            )
    return checks


def grade(pack_dir: Path) -> dict[str, Any]:
    pack_dir = pack_dir.resolve()
    output = load_pack_json(pack_dir, "output.json")
    validation = load_pack_json(pack_dir, "validation_summary.json")
    manifest = load_pack_json(pack_dir, "manifest.json")
    skill_id = str(manifest.get("skill_id") or "")

    recommendations_raw = output.get("recommendations") or []
    recommendations = recommendations_raw if isinstance(recommendations_raw, list) else []
    top = output.get("top_recommendation") or {}
    top_id = top.get("id") if isinstance(top, dict) else None
    top_score = top.get("score") if isinstance(top, dict) else None
    scores = [
        rec.get("score")
        for rec in recommendations
        if isinstance(rec, dict) and isinstance(rec.get("score"), int)
    ]
    query = (output.get("input") or {}).get("query")
    query_words = _words(query)
    expected_top = "medagent.nv_segment_ct" if {"segment", "ct", "nifti", "volume"} <= query_words else None
    no_fit = output.get("no_fit")
    disclaimer = str(output.get("intended_use_disclaimer") or "")

    checks: list[dict[str, Any]] = [
        make_check(
            "target_skill_matches",
            skill_id in TARGET_SKILL_IDS,
            f"skill_id={skill_id!r}",
        ),
        make_check(
            "source_pack_passed",
            validation.get("overall_status") == "passed",
            f"source pack overall={validation.get('overall_status')!r}",
        ),
        make_check(
            "query_present",
            isinstance(query, str) and query.strip() != "",
            f"query={query!r}",
        ),
        make_check(
            "catalog_count_positive",
            isinstance((output.get("catalog") or {}).get("count"), int)
            and (output.get("catalog") or {}).get("count") >= len(recommendations),
            f"catalog.count={(output.get('catalog') or {}).get('count')!r}, recommendations={len(recommendations)}",
        ),
        make_check(
            "recommendations_nonempty",
            len(recommendations) > 0,
            f"recommendations={len(recommendations)}",
        ),
        make_check(
            "top_recommendation_is_first",
            bool(recommendations) and isinstance(recommendations[0], dict) and recommendations[0].get("id") == top_id,
            f"top={top_id!r}, first={(recommendations[0].get('id') if recommendations and isinstance(recommendations[0], dict) else None)!r}",
        ),
        make_check(
            "scores_sorted_desc",
            len(scores) == len(recommendations) and scores == sorted(scores, reverse=True),
            f"scores={scores!r}",
        ),
        make_check(
            "no_fit_matches_top_score",
            isinstance(top_score, int) and isinstance(no_fit, bool) and no_fit == (top_score <= 0),
            f"no_fit={no_fit!r}, top_score={top_score!r}",
        ),
        make_check(
            "self_excluded",
            all(isinstance(rec, dict) and rec.get("id") != "medagent.find_skills" for rec in recommendations),
            "find_skills must not recommend itself",
        ),
        make_check(
            "ct_nifti_fixture_top_match",
            expected_top is None or top_id == expected_top,
            f"expected={expected_top!r}, actual={top_id!r}",
        ),
        make_check(
            "selection_scope_disclosed",
            all(term in disclaimer for term in DISCLAIMER_TERMS),
            "disclaimer must preserve engineering-only and manifest-inspection scope",
        ),
    ]
    checks.extend(_recommendation_path_checks(recommendations))

    hard_fail = any(check["status"] == "fail" for check in checks)
    has_warn = any(check["status"] == "warn" for check in checks)
    if hard_fail:
        overall = "fail"
    elif has_warn:
        overall = "warn"
    else:
        overall = "pass"

    fail_checks = [check for check in checks if check["status"] == "fail"]
    warn_checks = [check for check in checks if check["status"] == "warn"]

    return {
        "verifier": {"id": VERIFIER_ID, "version": VERIFIER_VERSION},
        "target": {
            "evidence_pack": _public_path(pack_dir),
            "skill_id": skill_id,
            "source_overall_status": validation.get("overall_status"),
        },
        "selector_quality": {
            "n_fail": len(fail_checks),
            "n_warn": len(warn_checks),
            "verdict": overall,
            "acceptable": overall in {"pass", "warn"},
            "query": query,
            "catalog_count": (output.get("catalog") or {}).get("count"),
            "recommendation_count": len(recommendations),
            "top_id": top_id,
        },
        "checks": checks,
        "warnings": [check["reason"] for check in warn_checks],
        "overall": overall,
    }


if __name__ == "__main__":
    run_grader(grade)
