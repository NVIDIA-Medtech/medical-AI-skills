#!/usr/bin/env python3
"""Verify holohub_imaging_ai_segmentator evidence packs for segmentation floors."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from verifiers._shared.verifier_kit import (  # noqa: E402
    load_pack_json,
    make_check,
    resolve_pack_artifact,
    run_grader,
)

VERIFIER_ID = "medagent.verifiers.holohub_imaging_segmentation_quality_v1"
VERIFIER_VERSION = "0.1.0"
TARGET_SKILL_IDS = {"holohub_imaging_ai_segmentator", "medagent.holohub_imaging_ai_segmentator"}


def _public_path(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        resolved = path.resolve()
    except (OSError, ValueError):
        return str(path)
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def _resolve_artifact(pack_dir: Path, rel: str) -> Path:
    return resolve_pack_artifact(pack_dir, rel, pack_dir / "artifacts")


def _first_file(output: dict[str, Any], pack_dir: Path, *keys: str) -> Path | None:
    cur: Any = output
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    if not isinstance(cur, dict):
        return None
    files = cur.get("files") or []
    if not files or not isinstance(files[0], dict):
        return None
    rel = str(files[0].get("path") or "")
    if not rel:
        return None
    path = _resolve_artifact(pack_dir, rel)
    return path if path.is_file() else None


def _nifti_foreground_fraction(path: Path) -> dict[str, Any] | None:
    try:
        import nibabel as nib  # type: ignore
        import numpy as np  # type: ignore
    except ImportError:
        return None
    try:
        data = np.asanyarray(nib.load(str(path)).dataobj)
        if data.size == 0:
            return {"foreground_voxel_fraction": 0.0, "max_label": 0}
        max_label = int(data.max())
        fg = int((data > 0).sum())
        return {
            "foreground_voxel_fraction": round(fg / data.size, 6),
            "max_label": max_label,
        }
    except Exception as e:
        return {"error": repr(e)}


def grade(pack_dir: Path) -> dict[str, Any]:
    pack_dir = pack_dir.resolve()
    output_payload = load_pack_json(pack_dir, "output.json")
    validation = load_pack_json(pack_dir, "validation_summary.json")
    manifest = load_pack_json(pack_dir, "manifest.json")

    skill_id = manifest.get("skill_id") or output_payload.get("skill_id") or ""
    source_status = validation.get("overall_status", "")
    output = output_payload.get("output") or {}
    seg_signals = output.get("seg_signals") or {}
    invocation = output_payload.get("invocation") or {}

    dicom_seg = output.get("dicom_seg") or {}
    nifti = output.get("nifti") or {}
    nifti_orig = nifti.get("original") or {}
    nifti_seg = nifti.get("segmentation") or {}

    seg_nifti_path = _first_file(output, pack_dir, "nifti", "segmentation")

    floor_checks = [
        make_check("output_json_present", bool(output_payload), "output.json loaded"),
        make_check(
            "target_skill_is_imaging",
            skill_id in TARGET_SKILL_IDS,
            f"skill_id={skill_id!r}",
            actual=skill_id,
            expected=sorted(TARGET_SKILL_IDS),
        ),
        make_check(
            "source_pack_passed",
            source_status == "passed",
            f"source overall_status={source_status!r}",
            actual=source_status,
            expected="passed",
        ),
        make_check(
            "holohub_exit_clean",
            invocation.get("exit_code") == 0,
            f"exit_code={invocation.get('exit_code')!r}",
        ),
        make_check(
            "dicom_seg_present",
            int(dicom_seg.get("count") or 0) >= 1,
            f"dicom_seg.count={dicom_seg.get('count')}",
        ),
        make_check(
            "dicom_seg_nonempty",
            int(dicom_seg.get("total_bytes") or 0) > 50_000,
            f"dicom_seg.total_bytes={dicom_seg.get('total_bytes')}",
        ),
        make_check(
            "nifti_original_present",
            int(nifti_orig.get("count") or 0) >= 1,
            f"nifti.original.count={nifti_orig.get('count')}",
        ),
        make_check(
            "nifti_segmentation_present",
            int(nifti_seg.get("count") or 0) >= 1,
            f"nifti.segmentation.count={nifti_seg.get('count')}",
        ),
        make_check(
            "seg_pixel_max_gt_zero",
            int(seg_signals.get("seg_pixel_max_value") or 0) > 0,
            f"seg_pixel_max_value={seg_signals.get('seg_pixel_max_value')}",
        ),
        make_check(
            "no_empty_segmentation_warning",
            seg_signals.get("empty_segmentation_warning") is False,
            f"empty_segmentation_warning={seg_signals.get('empty_segmentation_warning')!r}",
        ),
    ]

    domain_floor = {
        "verdict": "pass" if all(c["status"] == "pass" for c in floor_checks) else "fail",
        "checks": floor_checks,
    }

    nifti_metrics: dict[str, Any] = {
        "verdict": "skipped",
        "reason": "segmentation NIfTI not on disk under pack",
        "path": str(seg_nifti_path) if seg_nifti_path else None,
    }
    if seg_nifti_path is not None:
        stats = _nifti_foreground_fraction(seg_nifti_path)
        if stats is None:
            nifti_metrics = {
                "verdict": "skipped",
                "reason": "nibabel/numpy unavailable for optional NIfTI load",
                "path": str(seg_nifti_path),
            }
        elif stats.get("error"):
            nifti_metrics = {
                "verdict": "fail",
                "reason": stats["error"],
                "path": str(seg_nifti_path),
            }
        else:
            fg_frac = float(stats["foreground_voxel_fraction"])
            max_label = int(stats["max_label"])
            nifti_ok = fg_frac > 0.0 and max_label > 0
            nifti_metrics = {
                "verdict": "pass" if nifti_ok else "fail",
                "reason": "foreground voxels present in segmentation NIfTI"
                if nifti_ok
                else "segmentation NIfTI is all background",
                "path": str(seg_nifti_path),
                "foreground_voxel_fraction": fg_frac,
                "max_label": max_label,
            }

    overall = (
        "pass"
        if domain_floor["verdict"] == "pass"
        and nifti_metrics.get("verdict") in ("pass", "skipped")
        else "fail"
    )

    return {
        "verifier": {"id": VERIFIER_ID, "version": VERIFIER_VERSION},
        "target": {
            "evidence_pack": _public_path(pack_dir),
            "skill_id": skill_id,
            "source_overall_status": source_status,
            "holohub_commit": invocation.get("holohub_commit"),
        },
        "artifact_inventory": {
            "dicom_seg_count": int(dicom_seg.get("count") or 0),
            "dicom_seg_bytes": int(dicom_seg.get("total_bytes") or 0),
            "nifti_original_count": int(nifti_orig.get("count") or 0),
            "nifti_segmentation_count": int(nifti_seg.get("count") or 0),
            "seg_signals": seg_signals,
        },
        "domain_floor": domain_floor,
        "nifti_metrics": nifti_metrics,
        "overall": overall,
    }


if __name__ == "__main__":
    run_grader(grade, sort_keys=True)
