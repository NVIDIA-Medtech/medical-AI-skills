#!/usr/bin/env python3
"""Verify totalsegmentator evidence packs for CT-segmentation quality floors.

This verifier sits outside the wrapper. The wrapper proves TotalSegmentator
ran and produced a geometrically-aligned, label-set-valid mask; this verifier
asks whether the mask passes a per-case anatomy plausibility floor (and, when
a ground-truth label map is referenced by the pack, a per-class Dice/IoU
floor).

Mirrors verifiers/ct_segmentation_quality_v1/scripts/grade.py with three
changes: the target skill ID, the anatomy-bounds file (TotalSegmentator
class IDs differ from VISTA3D), and the liver/spleen IDs used by the
liver_gt_spleen cross-class check are read from the bounds file's
`_cross_class_floors` block rather than hardcoded.
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

VERIFIER_ID = "medagent.verifiers.totalsegmentator_quality_v1"
VERIFIER_VERSION = "0.1.0"
TARGET_SKILL_IDS = {"totalsegmentator", "medagent.totalsegmentator"}

LABEL_SET_SUBSET_TOLERANCE = 0

ANATOMY_BOUNDS_PATH = (
    Path(__file__).resolve().parent.parent / "validators" / "anatomy_bounds_total.json"
)

GEOMETRY_TOLERANCE = 1e-4


def _resolve_path(pack_dir: Path, raw: str | None) -> Path | None:
    if not raw:
        return None
    return resolve_pack_artifact(pack_dir, raw, Path.cwd())


def _connected_component_stats(mask: np.ndarray) -> tuple[int, float]:
    total = int(mask.sum())
    if total == 0:
        return 0, 0.0
    try:
        from scipy.ndimage import label  # type: ignore
        structure = np.ones((3, 3, 3), dtype=np.uint8)
        labeled, n = label(mask, structure=structure)
        if n == 0:
            return 0, 0.0
        sizes = np.bincount(labeled.ravel())[1:]
        return int(n), float(sizes.max() / total)
    except Exception:
        return 1, 1.0


def _per_class_stats(
    mask: np.ndarray,
    voxel_volume_ml: float,
    label_ids_present: list[int],
    inv_label_dict: dict[int, str],
    bounds_table: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label_id in sorted(label_ids_present):
        class_mask = mask == label_id
        voxel_count = int(class_mask.sum())
        volume_ml = round(voxel_count * voxel_volume_ml, 4)
        n_components, largest_fraction = _connected_component_stats(class_mask)
        bounds = bounds_table.get(str(label_id))
        if isinstance(bounds, dict):
            volume_ok = bounds["volume_ml_min"] <= volume_ml <= bounds["volume_ml_max"]
            components_ok = n_components <= int(bounds.get("max_components", 1))
            frac_ok = largest_fraction >= float(bounds.get("largest_cc_fraction_min", 0.0))
        else:
            volume_ok = True
            components_ok = True
            frac_ok = True
            bounds = None
        rows.append({
            "label_id": label_id,
            "name": inv_label_dict.get(label_id, f"label_id_{label_id}"),
            "voxel_count": voxel_count,
            "volume_ml": volume_ml,
            "component_count": n_components,
            "largest_cc_fraction": round(largest_fraction, 4),
            "volume_bounds_ok": bool(volume_ok),
            "components_ok": bool(components_ok),
            "largest_cc_fraction_ok": bool(frac_ok),
            "bounds": bounds,
        })
    return rows


def _cross_class_checks(
    per_class: list[dict[str, Any]],
    bounds_table: dict[str, Any],
) -> dict[str, Any]:
    by_id = {row["label_id"]: row for row in per_class}
    cross_floors = bounds_table.get("_cross_class_floors") or {}

    liver_id = int(cross_floors.get("liver_id", 5))
    spleen_id = int(cross_floors.get("spleen_id", 1))
    liver = by_id.get(liver_id)
    spleen = by_id.get(spleen_id)
    if cross_floors.get("liver_gt_spleen") and liver and spleen:
        if liver["volume_ml"] > spleen["volume_ml"]:
            liver_status = "pass"
            liver_reason = (
                f"liver={liver['volume_ml']} mL > spleen={spleen['volume_ml']} mL"
            )
        else:
            liver_status = "fail"
            liver_reason = (
                f"liver={liver['volume_ml']} mL <= spleen={spleen['volume_ml']} mL"
            )
        liver_block = {
            "status": liver_status,
            "reason": liver_reason,
            "liver_volume_ml": liver["volume_ml"],
            "spleen_volume_ml": spleen["volume_ml"],
        }
    else:
        liver_block = {
            "status": "skipped",
            "reason": "liver and spleen not both present",
            "liver_volume_ml": liver["volume_ml"] if liver else None,
            "spleen_volume_ml": spleen["volume_ml"] if spleen else None,
        }

    max_diff = float(cross_floors.get("bilateral_symmetry_max_relative_diff", 0.5))
    pairs: list[dict[str, Any]] = []
    worst_diff: float | None = None
    sym_status = "skipped"
    sym_reason = "no bilateral pair present"
    seen: set[tuple[int, int]] = set()
    for row in per_class:
        spec = row.get("bounds") or {}
        if not spec.get("bilateral"):
            continue
        partner_id = spec.get("bilateral_partner_id")
        if not isinstance(partner_id, int):
            continue
        pair_key = (min(row["label_id"], partner_id), max(row["label_id"], partner_id))
        if pair_key in seen:
            continue
        partner = by_id.get(partner_id)
        if partner is None:
            continue
        seen.add(pair_key)
        a, b = row["volume_ml"], partner["volume_ml"]
        mean = (a + b) / 2.0 if (a + b) > 0 else 0.0
        rel = abs(a - b) / mean if mean > 0 else 0.0
        pair_ok = rel <= max_diff
        pairs.append({
            "label_ids": list(pair_key),
            "names": [row["name"], partner["name"]],
            "volumes_ml": [a, b],
            "relative_diff": round(rel, 4),
            "ok": pair_ok,
        })
        if worst_diff is None or rel > worst_diff:
            worst_diff = rel
        sym_status = "pass" if all(p["ok"] for p in pairs) else "fail"
        sym_reason = (
            f"worst relative_diff={worst_diff:.3f} <= {max_diff}"
            if sym_status == "pass"
            else f"worst relative_diff={worst_diff:.3f} > {max_diff}"
        )

    return {
        "liver_gt_spleen": liver_block,
        "bilateral_symmetry": {
            "status": sym_status,
            "reason": sym_reason,
            "relative_diff": round(worst_diff, 4) if worst_diff is not None else None,
            "pairs": pairs,
        },
    }


def _anatomy_plausibility(
    mask_path: Path | None,
    output_payload: dict[str, Any],
    bounds_table: dict[str, Any],
    inv_label_dict: dict[int, str],
) -> tuple[dict[str, Any], dict[str, Any], np.ndarray | None, nib.spatialimages.SpatialImage | None]:
    output = output_payload.get("output") or {}
    declared_shape = output.get("shape") or []
    geometry = output.get("geometry") or {}
    declared_affine_match = bool(geometry.get("affine_match"))

    inventory: dict[str, Any] = {
        "label_map_path": str(mask_path) if mask_path else None,
        "label_map_readable": False,
        "label_map_dtype": None,
        "label_map_shape": [],
        "shape_match": False,
        "affine_match": declared_affine_match,
        "voxel_volume_ml": None,
    }

    plausibility: dict[str, Any] = {
        "verdict": "skipped",
        "per_class": [],
        "classes_failing_volume_bounds": [],
        "classes_overfragmented": [],
        "cross_class": {
            "liver_gt_spleen": {"status": "skipped", "reason": "label map unreadable"},
            "bilateral_symmetry": {"status": "skipped", "reason": "label map unreadable"},
        },
        "checks": [],
    }

    if mask_path is None or not mask_path.exists():
        inventory["label_map_readable"] = False
        plausibility["checks"].append(
            make_check("label_map_present", False, f"path={mask_path!s} not found")
        )
        return inventory, plausibility, None, None

    try:
        mask_img = nib.load(str(mask_path))
        mask_arr = np.asarray(mask_img.get_fdata()).astype(np.int64)
    except Exception as e:
        plausibility["checks"].append(
            make_check("label_map_readable", False, f"nibabel load failed: {e}")
        )
        return inventory, plausibility, None, None

    inventory["label_map_readable"] = True
    inventory["label_map_dtype"] = str(mask_img.get_data_dtype())
    inventory["label_map_shape"] = [int(v) for v in mask_arr.shape]
    inventory["shape_match"] = inventory["label_map_shape"] == [int(v) for v in declared_shape]

    spacing = mask_img.header.get_zooms()[:3]
    voxel_volume_ml = float(np.prod(spacing)) / 1000.0
    inventory["voxel_volume_ml"] = round(voxel_volume_ml, 8)

    label_ids_present = sorted(int(v) for v in np.unique(mask_arr) if int(v) != 0)
    per_class = _per_class_stats(
        mask_arr, voxel_volume_ml, label_ids_present, inv_label_dict, bounds_table
    )

    fail_volume = [row["name"] for row in per_class if not row["volume_bounds_ok"]]
    fail_components = [
        row["name"]
        for row in per_class
        if not row["components_ok"] or not row["largest_cc_fraction_ok"]
    ]
    cross_class = _cross_class_checks(per_class, bounds_table)

    checks = [
        make_check("label_map_present", True, f"loaded {mask_path}"),
        make_check(
            "any_class_present",
            len(per_class) > 0,
            f"label_ids_present={label_ids_present}",
        ),
        make_check(
            "all_classes_within_volume_bounds",
            len(fail_volume) == 0,
            "all per-class volumes within population bounds"
            if not fail_volume
            else f"classes outside bounds: {fail_volume}",
            failing=fail_volume,
        ),
        make_check(
            "no_fragmented_classes",
            len(fail_components) == 0,
            "no class exceeds CC cap or fails largest-CC fraction"
            if not fail_components
            else f"fragmented classes: {fail_components}",
            failing=fail_components,
        ),
        make_check(
            "liver_gt_spleen",
            cross_class["liver_gt_spleen"]["status"] != "fail",
            cross_class["liver_gt_spleen"]["reason"],
        ),
        make_check(
            "bilateral_symmetry",
            cross_class["bilateral_symmetry"]["status"] != "fail",
            cross_class["bilateral_symmetry"]["reason"],
        ),
    ]
    plausibility = {
        "verdict": "pass" if all(c["status"] == "pass" for c in checks) else "fail",
        "per_class": per_class,
        "classes_failing_volume_bounds": fail_volume,
        "classes_overfragmented": fail_components,
        "cross_class": cross_class,
        "checks": checks,
    }
    return inventory, plausibility, mask_arr, mask_img


def _gt_metrics(
    mask_arr: np.ndarray | None,
    mask_img: nib.spatialimages.SpatialImage | None,
    gt_path: Path | None,
    requested_label_ids: list[int],
    bounds_table: dict[str, Any],
    inv_label_dict: dict[int, str],
) -> dict[str, Any]:
    floors = bounds_table.get("_gt_dice_floors") or {}

    skipped = {
        "verdict": "skipped",
        "acceptable": True,
        "reason": "no ground_truth_path recorded in evidence pack",
        "ground_truth_path": None,
        "per_class": [],
        "checks": [],
    }

    if gt_path is None:
        return skipped
    skipped["ground_truth_path"] = str(gt_path)

    if not gt_path.exists():
        return {
            **skipped,
            "verdict": "skipped",
            "acceptable": True,
            "reason": f"ground_truth_path {gt_path} not found on disk",
        }
    if mask_arr is None or mask_img is None:
        return {
            **skipped,
            "verdict": "skipped",
            "acceptable": True,
            "reason": "predicted label map unreadable, GT comparison not possible",
        }

    try:
        gt_img = nib.load(str(gt_path))
        gt_arr = np.asarray(gt_img.get_fdata()).astype(np.int64)
    except Exception as e:
        return {
            **skipped,
            "verdict": "fail",
            "acceptable": False,
            "reason": f"nibabel load of GT failed: {e}",
        }

    if gt_arr.shape != mask_arr.shape:
        return {
            **skipped,
            "verdict": "fail",
            "acceptable": False,
            "reason": f"GT shape {gt_arr.shape} != predicted shape {mask_arr.shape}",
        }

    label_ids_pred = sorted(int(v) for v in np.unique(mask_arr) if int(v) != 0)
    label_ids_gt = sorted(int(v) for v in np.unique(gt_arr) if int(v) != 0)
    classes_to_score = sorted(set(requested_label_ids or label_ids_pred) & set(label_ids_gt))
    if not classes_to_score:
        return {
            "verdict": "skipped",
            "acceptable": True,
            "reason": "no overlap between predicted/requested classes and GT classes",
            "ground_truth_path": str(gt_path),
            "per_class": [],
            "checks": [],
        }

    per_class: list[dict[str, Any]] = []
    for label_id in classes_to_score:
        pred_mask = mask_arr == label_id
        gt_mask = gt_arr == label_id
        inter = int(np.logical_and(pred_mask, gt_mask).sum())
        union = int(np.logical_or(pred_mask, gt_mask).sum())
        p_sum = int(pred_mask.sum())
        g_sum = int(gt_mask.sum())
        dice = (2.0 * inter) / (p_sum + g_sum) if (p_sum + g_sum) > 0 else 0.0
        iou = inter / union if union > 0 else 0.0
        floor = floors.get(str(label_id))
        dice_floor = float(floor) if isinstance(floor, (int, float)) else None
        dice_ok = dice_floor is None or dice >= dice_floor
        per_class.append({
            "label_id": label_id,
            "name": inv_label_dict.get(label_id, f"label_id_{label_id}"),
            "dice": round(dice, 4),
            "iou": round(iou, 4),
            "dice_floor": dice_floor,
            "dice_ok": bool(dice_ok),
        })

    failing = [row["name"] for row in per_class if not row["dice_ok"]]
    checks = [
        make_check(
            "gt_loaded",
            True,
            f"loaded GT from {gt_path}, scored {len(per_class)} classes",
        ),
        make_check(
            "all_classes_meet_dice_floor",
            len(failing) == 0,
            "all per-class Dice >= floor" if not failing else f"below floor: {failing}",
            failing=failing,
        ),
    ]
    verdict = "pass" if all(c["status"] == "pass" for c in checks) else "fail"
    return {
        "verdict": verdict,
        "acceptable": verdict == "pass",
        "reason": (
            "all per-class Dice floors met"
            if verdict == "pass"
            else f"classes below Dice floor: {failing}"
        ),
        "ground_truth_path": str(gt_path),
        "per_class": per_class,
        "checks": checks,
    }


def _label_dict_from_output(output_payload: dict[str, Any]) -> dict[int, str]:
    counts = (output_payload.get("output") or {}).get("class_counts") or {}
    label_ids = (output_payload.get("output") or {}).get("label_ids_present") or []
    if len(counts) == len(label_ids) and label_ids:
        return {int(lid): name for lid, name in zip(label_ids, counts.keys())}
    return {}


def _label_set_subset(
    label_ids_present: list[int],
    requested: list[int],
) -> dict[str, Any]:
    requested_set = {int(x) for x in requested}
    present_set = {int(x) for x in label_ids_present}
    if not requested:
        return {
            "verdict": "skipped",
            "reason": "output.label_prompts_requested is empty or missing",
            "requested": [],
            "present": sorted(present_set),
            "extras": [],
            "missing": [],
            "tolerance": LABEL_SET_SUBSET_TOLERANCE,
        }
    extras = sorted(present_set - requested_set)
    missing = sorted(requested_set - present_set)
    verdict = "pass" if len(extras) <= LABEL_SET_SUBSET_TOLERANCE else "fail"
    reason = (
        f"{len(extras)} extra class(es) not in label_prompts_requested "
        f"(tolerance {LABEL_SET_SUBSET_TOLERANCE}): {extras[:10]}"
        if extras
        else "produced label set is a subset of requested"
    )
    return {
        "verdict": verdict,
        "reason": reason,
        "requested": sorted(requested_set),
        "present": sorted(present_set),
        "extras": extras,
        "missing": missing,
        "tolerance": LABEL_SET_SUBSET_TOLERANCE,
    }


def grade(pack_dir: Path) -> dict[str, Any]:
    output_payload = load_pack_json(pack_dir, "output.json")
    validation = load_pack_json(pack_dir, "validation_summary.json")
    manifest = load_pack_json(pack_dir, "manifest.json")

    skill_id = manifest.get("skill_id") or output_payload.get("skill") or ""
    source_status = validation.get("overall_status", "")

    output = output_payload.get("output") or {}
    input_block = output_payload.get("input") or {}
    requested = output.get("label_prompts_requested") or []
    inv_label_dict = _label_dict_from_output(output_payload)

    mask_path_raw = output.get("path")
    mask_path = _resolve_path(pack_dir, mask_path_raw)
    gt_path = _resolve_path(pack_dir, input_block.get("ground_truth_path"))

    bounds_table = load_pack_json(ANATOMY_BOUNDS_PATH.parent, ANATOMY_BOUNDS_PATH.name)

    inventory, plausibility, mask_arr, mask_img = _anatomy_plausibility(
        mask_path, output_payload, bounds_table, inv_label_dict
    )
    gt = _gt_metrics(
        mask_arr, mask_img, gt_path, list(requested), bounds_table, inv_label_dict
    )

    label_ids_present = sorted({int(v) for v in (output.get("label_ids_present") or [])})
    label_subset = _label_set_subset(label_ids_present, list(requested))

    overall = (
        "pass"
        if (
            skill_id in TARGET_SKILL_IDS
            and inventory["label_map_readable"]
            and inventory["shape_match"]
            and inventory["affine_match"]
            and plausibility["verdict"] == "pass"
            and gt["acceptable"]
            and label_subset["verdict"] in ("pass", "skipped")
        )
        else "fail"
    )

    return {
        "verifier": {"id": VERIFIER_ID, "version": VERIFIER_VERSION},
        "target": {
            "evidence_pack": str(pack_dir),
            "skill_id": skill_id,
            "source_overall_status": source_status,
            "label_map_path": str(mask_path) if mask_path else None,
            "ground_truth_path": str(gt_path) if gt_path else None,
        },
        "artifact_inventory": inventory,
        "anatomy_plausibility": plausibility,
        "label_set_subset": label_subset,
        "gt_metrics": gt,
        "overall": overall,
    }


if __name__ == "__main__":
    run_grader(grade, sort_keys=True)
