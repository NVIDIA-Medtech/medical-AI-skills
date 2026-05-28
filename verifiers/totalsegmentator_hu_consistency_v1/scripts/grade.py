#!/usr/bin/env python3
"""Verify totalsegmentator evidence packs for per-organ HU consistency.

For each label ID present in the predicted multilabel mask, samples voxels
from the recorded input CT volume and checks that the median HU falls
within a population-typical range for that tissue. Catches mask-in-wrong-
place failures that the anatomy_plausibility tier can't see (geometrically
plausible mask placed on a different organ).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from verifiers._shared.verifier_kit import (  # noqa: E402
    load_pack_json,
    make_check,
    resolve_pack_artifact,
    run_grader,
)

VERIFIER_ID = "medagent.verifiers.totalsegmentator_hu_consistency_v1"
VERIFIER_VERSION = "0.1.0"
TARGET_SKILL_IDS = {"totalsegmentator"}

HU_BOUNDS_PATH = (
    Path(__file__).resolve().parent.parent / "validators" / "hu_bounds_total.json"
)


def _resolve_path(pack_dir: Path, raw: str | None) -> Path | None:
    if not raw:
        return None
    return resolve_pack_artifact(pack_dir, raw, Path.cwd())


def _per_class_hu_stats(
    ct: np.ndarray,
    mask: np.ndarray,
    bounds_table: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    label_ids = sorted(int(v) for v in np.unique(mask) if int(v) != 0)
    for label_id in label_ids:
        class_voxels = ct[mask == label_id]
        if class_voxels.size == 0:
            continue
        median = float(np.median(class_voxels))
        mean = float(np.mean(class_voxels))
        std = float(np.std(class_voxels))
        p10 = float(np.percentile(class_voxels, 10))
        p90 = float(np.percentile(class_voxels, 90))
        bounds = bounds_table.get(str(label_id))
        if isinstance(bounds, dict):
            hu_min = float(bounds["hu_min"])
            hu_max = float(bounds["hu_max"])
            in_range = hu_min <= median <= hu_max
            name = bounds.get("name", f"label_id_{label_id}")
            check_status = "checked"
        else:
            hu_min = None
            hu_max = None
            in_range = True  # neutral when no bound defined
            name = f"label_id_{label_id}"
            check_status = "no_bounds"
        rows.append({
            "label_id": label_id,
            "name": name,
            "voxel_count": int(class_voxels.size),
            "median_hu": round(median, 2),
            "mean_hu": round(mean, 2),
            "std_hu": round(std, 2),
            "p10_hu": round(p10, 2),
            "p90_hu": round(p90, 2),
            "hu_min_expected": hu_min,
            "hu_max_expected": hu_max,
            "in_range": bool(in_range),
            "check_status": check_status,
        })
    return rows


def _input_inventory(
    ct_path: Path | None,
    mask_path: Path | None,
) -> tuple[dict[str, Any], np.ndarray | None, np.ndarray | None]:
    inv: dict[str, Any] = {
        "input_volume_path": str(ct_path) if ct_path else None,
        "input_volume_readable": False,
        "label_map_path": str(mask_path) if mask_path else None,
        "label_map_readable": False,
        "shape_match": False,
        "affine_match": False,
        "input_shape": [],
        "mask_shape": [],
    }
    if ct_path is None or not ct_path.exists():
        return inv, None, None
    if mask_path is None or not mask_path.exists():
        return inv, None, None
    try:
        ct_img = nib.load(str(ct_path))
        ct_arr = np.asarray(ct_img.get_fdata()).astype(np.float32)
        inv["input_volume_readable"] = True
        inv["input_shape"] = [int(v) for v in ct_arr.shape]
    except Exception:
        return inv, None, None
    try:
        mask_img = nib.load(str(mask_path))
        mask_arr = np.asarray(mask_img.get_fdata()).astype(np.int64)
        inv["label_map_readable"] = True
        inv["mask_shape"] = [int(v) for v in mask_arr.shape]
    except Exception:
        return inv, ct_arr, None
    inv["shape_match"] = inv["input_shape"] == inv["mask_shape"]
    affine_diff = float(np.max(np.abs(ct_img.affine - mask_img.affine)))
    inv["affine_match"] = affine_diff <= 1e-4
    if not inv["shape_match"]:
        return inv, ct_arr, None
    return inv, ct_arr, mask_arr


def grade(pack_dir: Path) -> dict[str, Any]:
    output_payload = load_pack_json(pack_dir, "output.json")
    validation = load_pack_json(pack_dir, "validation_summary.json")
    manifest = load_pack_json(pack_dir, "manifest.json")

    skill_id = manifest.get("skill_id") or output_payload.get("skill") or ""
    source_status = validation.get("overall_status", "")

    output = output_payload.get("output") or {}
    input_block = output_payload.get("input") or {}

    ct_path = _resolve_path(pack_dir, input_block.get("path"))
    mask_path = _resolve_path(pack_dir, output.get("path"))

    bounds_table = load_pack_json(HU_BOUNDS_PATH.parent, HU_BOUNDS_PATH.name)
    min_pass_fraction = float(bounds_table.get("_min_pass_fraction", 0.7))

    inventory, ct_arr, mask_arr = _input_inventory(ct_path, mask_path)

    if ct_arr is None or mask_arr is None:
        hu_block: dict[str, Any] = {
            "verdict": "skipped",
            "reason": "input CT and/or mask unreadable or shape-mismatched",
            "per_class": [],
            "classes_out_of_range": [],
            "checked_count": 0,
            "passing_count": 0,
            "pass_fraction": 0.0,
            "min_pass_fraction": min_pass_fraction,
            "checks": [
                make_check(
                    "load_inputs",
                    False,
                    f"CT readable={inventory['input_volume_readable']} mask readable={inventory['label_map_readable']} shape_match={inventory['shape_match']}",
                )
            ],
        }
        overall = "fail"
    else:
        per_class = _per_class_hu_stats(ct_arr, mask_arr, bounds_table)
        checked = [row for row in per_class if row["check_status"] == "checked"]
        passing = [row for row in checked if row["in_range"]]
        out_of_range = [
            f"{row['name']} (median {row['median_hu']} HU, expected "
            f"{row['hu_min_expected']}-{row['hu_max_expected']})"
            for row in checked
            if not row["in_range"]
        ]
        pass_fraction = (len(passing) / len(checked)) if checked else 1.0
        verdict_ok = pass_fraction >= min_pass_fraction and bool(checked)

        checks = [
            make_check(
                "any_class_checked",
                bool(checked),
                f"{len(checked)} class(es) had HU bounds defined out of {len(per_class)} present",
            ),
            make_check(
                "pass_fraction_meets_floor",
                pass_fraction >= min_pass_fraction,
                f"{len(passing)}/{len(checked)} classes within HU range "
                f"(fraction={pass_fraction:.3f} >= {min_pass_fraction})",
                failing=out_of_range,
            ),
        ]
        hu_block = {
            "verdict": "pass" if verdict_ok else "fail",
            "reason": (
                f"{len(passing)}/{len(checked)} per-class median HU within "
                f"population range (>= {min_pass_fraction:.0%})"
                if verdict_ok
                else f"only {len(passing)}/{len(checked)} per-class median HU within range "
                f"(need >= {min_pass_fraction:.0%})"
            ),
            "per_class": per_class,
            "classes_out_of_range": [row["name"] for row in checked if not row["in_range"]],
            "checked_count": len(checked),
            "passing_count": len(passing),
            "pass_fraction": round(pass_fraction, 4),
            "min_pass_fraction": min_pass_fraction,
            "checks": checks,
        }
        overall = "pass" if (verdict_ok and skill_id in TARGET_SKILL_IDS) else "fail"

    return {
        "verifier": {"id": VERIFIER_ID, "version": VERIFIER_VERSION},
        "target": {
            "evidence_pack": str(pack_dir),
            "skill_id": skill_id,
            "source_overall_status": source_status,
            "input_volume_path": str(ct_path) if ct_path else None,
            "label_map_path": str(mask_path) if mask_path else None,
        },
        "input_inventory": inventory,
        "hu_consistency": hu_block,
        "overall": overall,
    }


if __name__ == "__main__":
    run_grader(grade, sort_keys=True)
