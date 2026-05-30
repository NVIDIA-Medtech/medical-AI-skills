#!/usr/bin/env python3
"""Verify dicom_metadata_extract evidence packs."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from verifiers._shared.verifier_kit import load_pack_json, make_check, run_grader  # noqa: E402

VERIFIER_ID = "medagent.verifiers.dicom_metadata_quality_v1"
VERIFIER_VERSION = "0.1.0"
TARGET_SKILL_IDS = {"dicom_metadata_extract", "medagent.dicom_metadata_extract"}
DISCLAIMER_TERMS = ("Standard DICOM", "Private tags", "Burnt-in pixel")


def _public_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def _present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and value > 0


def grade(pack_dir: Path) -> dict[str, Any]:
    pack_dir = pack_dir.resolve()
    output = load_pack_json(pack_dir, "output.json")
    validation = load_pack_json(pack_dir, "validation_summary.json")
    manifest = load_pack_json(pack_dir, "manifest.json")
    skill_id = str(manifest.get("skill_id") or "")

    study = output.get("study") or {}
    image = output.get("image") or {}
    transfer_syntax = output.get("transfer_syntax") or {}
    phi_present = output.get("phi_present")
    phi_tags_found = output.get("phi_tags_found")
    disclaimer = str(output.get("phi_scope_disclaimer") or "")

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
            "modality_present",
            _present(output.get("modality")),
            f"modality={output.get('modality')!r}",
        ),
        make_check(
            "transfer_syntax_present",
            _present(transfer_syntax.get("uid")) and _present(transfer_syntax.get("name")),
            f"transfer_syntax={transfer_syntax!r}",
        ),
        make_check(
            "study_uid_present",
            _present(study.get("StudyInstanceUID")),
            f"StudyInstanceUID={study.get('StudyInstanceUID')!r}",
        ),
        make_check(
            "image_dimensions_positive",
            _positive_int(image.get("Rows")) and _positive_int(image.get("Columns")),
            f"Rows={image.get('Rows')!r}, Columns={image.get('Columns')!r}",
        ),
        make_check(
            "phi_flag_is_boolean",
            isinstance(phi_present, bool),
            f"phi_present={phi_present!r}",
        ),
        make_check(
            "phi_tags_list_shape",
            isinstance(phi_tags_found, list) and all(isinstance(item, str) for item in phi_tags_found),
            "phi_tags_found must be a list of tag-name strings",
        ),
    ]

    if isinstance(phi_present, bool) and isinstance(phi_tags_found, list):
        checks.append(
            make_check(
                "phi_flag_consistent",
                (phi_present and len(phi_tags_found) > 0) or (not phi_present and len(phi_tags_found) == 0),
                f"phi_present={phi_present!r}, n_phi_tags={len(phi_tags_found)}",
            )
        )

    checks.append(
        make_check(
            "phi_scope_disclosed",
            all(term in disclaimer for term in DISCLAIMER_TERMS),
            "scope disclaimer must mention standard DICOM, private tags, and burnt-in pixel limits",
        )
    )

    warnings: list[str] = []
    if phi_present is True:
        tag_list = ", ".join(phi_tags_found or [])
        warning = f"standard PHI tags present: {tag_list or 'unspecified'}"
        warnings.append(warning)
        checks.append(make_check("standard_phi_present", False, warning, level="warn"))

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
        "metadata_quality": {
            "n_fail": len(fail_checks),
            "n_warn": len(warn_checks),
            "verdict": overall,
            "acceptable": overall in {"pass", "warn"},
        },
        "checks": checks,
        "warnings": warnings,
        "overall": overall,
    }


if __name__ == "__main__":
    run_grader(grade)
