#!/usr/bin/env python3
"""Verify dicom_series_preflight evidence packs (pass / warn / fail)."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from verifiers._shared.verifier_kit import load_pack_json, make_check, run_grader  # noqa: E402

VERIFIER_ID = "medagent.verifiers.dicom_preflight_quality_v1"
VERIFIER_VERSION = "0.1.0"
TARGET_SKILL_IDS = {"dicom_series_preflight", "medagent.dicom_series_preflight"}


def _public_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def grade(pack_dir: Path) -> dict[str, Any]:
    pack_dir = pack_dir.resolve()
    output = load_pack_json(pack_dir, "output.json")
    val_sum = load_pack_json(pack_dir, "validation_summary.json")
    skill_id = load_pack_json(pack_dir, "manifest.json").get("skill_id") or ""

    checks: list[dict[str, Any]] = []
    findings = output.get("findings") or []
    skill_verdict = (output.get("preflight") or {}).get("verdict", "fail")

    checks.append(make_check(
        "skill_pack_readable",
        output.get("skill") == "dicom_series_preflight",
        "output.json present and skill id matches",
    ))
    checks.append(make_check(
        "source_skill_passed",
        val_sum.get("overall_status") == "passed",
        f"source pack overall={val_sum.get('overall_status')!r}",
    ))

    fail_findings = [f for f in findings if f.get("level") == "fail"]
    warn_findings = [f for f in findings if f.get("level") == "warn"]

    checks.append(make_check(
        "no_fail_findings",
        len(fail_findings) == 0,
        f"fail findings: {[f.get('code') for f in fail_findings]}",
    ))
    checks.append(make_check(
        "orientation_ok",
        (output.get("orientation") or {}).get("axcodes_match") is True,
        f"axcodes={(output.get('orientation') or {}).get('axcodes')}",
    ))
    checks.append(make_check(
        "single_series",
        (output.get("series") or {}).get("single_series") is True,
        f"n_series={(output.get('series') or {}).get('n_series')}",
    ))
    checks.append(make_check(
        "no_corrupt_instances",
        (output.get("inventory") or {}).get("n_corrupt", 1) == 0,
        f"n_corrupt={(output.get('inventory') or {}).get('n_corrupt')}",
    ))

    if (output.get("phi") or {}).get("phi_present"):
        checks.append(make_check(
            "phi_disclosed",
            True,
            "PHI tags present — engineering warn only",
            level="warn",
        ))

    hard_fail = any(c["status"] == "fail" for c in checks)
    has_warn = any(c["status"] == "warn" for c in checks) or bool(warn_findings)

    if hard_fail or fail_findings:
        overall = "fail"
    elif has_warn or skill_verdict == "warn":
        overall = "warn"
    else:
        overall = "pass"

    return {
        "verifier": {"id": VERIFIER_ID, "version": VERIFIER_VERSION},
        "target": {
            "evidence_pack": _public_path(pack_dir),
            "skill_id": skill_id,
            "source_overall_status": val_sum.get("overall_status"),
            "skill_preflight_verdict": skill_verdict,
        },
        "preflight_gate": {
            "findings": findings,
            "n_fail": len(fail_findings),
            "n_warn": len(warn_findings),
            "verdict": overall,
            "acceptable": overall in ("pass", "warn"),
        },
        "checks": checks,
        "overall": overall,
    }


if __name__ == "__main__":
    run_grader(grade)
