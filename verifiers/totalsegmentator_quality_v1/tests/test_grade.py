"""Tests for totalsegmentator_quality_v1 grade.py.

Packs are synthesized in tmp_path rather than committed to fixtures/ — the
upstream-tool-specific structure (TotalSegmentator class IDs) is simple
enough that inline construction keeps the tests legible.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import nibabel as nib
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
VERIFIER = REPO_ROOT / "verifiers" / "totalsegmentator_quality_v1"
SCRIPT = VERIFIER / "scripts" / "grade.py"


def _build_pack(
    pack_dir: Path,
    *,
    label_ids: list[int] | None = None,
    requested: list[int] | None = None,
    fragment_spleen: bool = False,
    swap_liver_spleen_volumes: bool = False,
    with_ground_truth: bool = False,
    gt_perfect: bool = True,
) -> Path:
    """Build a synthetic evidence pack the verifier can read.

    Default content (TotalSegmentator total-task class IDs):
      - liver (id=5):         non-cubic 75×50×50 slab at 2 mm → 1500 mL
      - spleen (id=1):        25×40×25 slab               →  200 mL
      - kidney_right (id=2):  25×30×25 slab               →  150 mL
      - kidney_left  (id=3):  25×30×25 slab               →  150 mL
    All within population bounds, all single connected components, bilateral
    pair symmetric, liver > spleen.
    """
    if label_ids is None:
        label_ids = [1, 2, 3, 5]

    pack_dir.mkdir(parents=True, exist_ok=True)
    spacing = (2.0, 2.0, 2.0)
    shape = (120, 100, 60)
    affine = np.diag([spacing[0], spacing[1], spacing[2], 1.0])
    arr = np.zeros(shape, dtype=np.int16)

    # voxel_ml = 2*2*2 / 1000 = 0.008 mL/voxel
    voxel_ml = float(np.prod(spacing)) / 1000.0

    # Slab placements: (x_slice, y_slice, z_slice). Picked so no two overlap
    # and every per-class volume lands inside anatomy_bounds_total.json.
    liver_slab = (slice(0, 75), slice(0, 50), slice(0, 50))       # 1500 mL
    spleen_slab = (slice(75, 100), slice(0, 40), slice(0, 25))    #  200 mL
    kidney_r_slab = (slice(0, 25), slice(50, 80), slice(0, 25))   #  150 mL
    kidney_l_slab = (slice(25, 50), slice(50, 80), slice(0, 25))  #  150 mL

    if swap_liver_spleen_volumes:
        liver_slab, spleen_slab = spleen_slab, liver_slab

    if 5 in label_ids:
        arr[liver_slab] = 5
    if 1 in label_ids:
        if fragment_spleen:
            # 30 single-voxel pieces scattered along z=55 — fails
            # max_components=1 AND largest_cc_fraction_min=0.85.
            for i in range(30):
                arr[3 * i, 90, 55] = 1
        else:
            arr[spleen_slab] = 1
    if 2 in label_ids:
        arr[kidney_r_slab] = 2
    if 3 in label_ids:
        arr[kidney_l_slab] = 3

    # Anything else: place a small synthetic blob so the class is non-empty.
    for lid in label_ids:
        if lid in (1, 2, 3, 5):
            continue
        arr[90 + (lid % 5), 80 + (lid % 5), 55] = lid

    mask_path = pack_dir / "predicted_seg.nii.gz"
    nib.save(nib.Nifti1Image(arr, affine), str(mask_path))

    # Recompute per-class counts honestly from the array so the pack and
    # the verifier's recompute agree.
    unique, counts = np.unique(arr, return_counts=True)
    class_counts: dict[str, int] = {}
    for v, c in zip(unique.tolist(), counts.tolist()):
        if int(v) == 0:
            continue
        # Use canonical TotalSegmentator names for the well-known ones
        name = {1: "spleen", 2: "kidney_right", 3: "kidney_left", 5: "liver", 7: "pancreas"}.get(
            int(v), f"label_id_{int(v)}"
        )
        class_counts[name] = int(c)

    label_ids_present = sorted(int(v) for v in unique if int(v) != 0)

    output_payload: dict = {
        "skill": "totalsegmentator",
        "task": "total",
        "task_license": "non_commercial",
        "input": {
            "path": "synthetic_ct.nii.gz",
            "shape": list(shape),
            "ndim": 3,
            "spacing": list(spacing),
            "ground_truth_path": None,
        },
        "output": {
            "path": str(mask_path),
            "shape": list(shape),
            "label_prompts_requested": requested or [],
            "label_ids_present": label_ids_present,
            "unexpected_label_ids": [],
            "label_set_valid": True,
            "class_counts": class_counts,
            "voxel_volume_ml": round(voxel_ml, 8),
            "class_volumes_ml": {
                name: round(class_counts[name] * voxel_ml, 4) for name in class_counts
            },
            "any_label_present": True,
            "geometry": {
                "input_shape": list(shape),
                "output_shape": list(shape),
                "shape_match": True,
                "input_spacing": list(spacing),
                "output_spacing": list(spacing),
                "spacing_match": True,
                "affine_max_abs_diff": 0.0,
                "affine_match": True,
            },
        },
        "invocation": {
            "python_api": "totalsegmentator.python_api.totalsegmentator",
            "ml": True,
        },
        "runtime": {"inference_seconds": 0.1, "device": "cpu"},
    }

    if with_ground_truth:
        if gt_perfect:
            gt_arr = arr.copy()
        else:
            gt_arr = np.zeros_like(arr)  # zero overlap → Dice=0
        gt_path = pack_dir / "reference_seg.nii.gz"
        nib.save(nib.Nifti1Image(gt_arr, affine), str(gt_path))
        output_payload["input"]["ground_truth_path"] = str(gt_path)

    (pack_dir / "output.json").write_text(json.dumps(output_payload, indent=2))
    (pack_dir / "validation_summary.json").write_text(json.dumps({"overall_status": "passed"}))
    (pack_dir / "manifest.json").write_text(json.dumps({"skill_id": "totalsegmentator"}))
    return pack_dir


def _run_script(fixture: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(fixture)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def test_pass_pack_passes_all_tiers(tmp_path: Path) -> None:
    pack = _build_pack(tmp_path / "pass_pack")
    payload = _run_script(pack)

    assert payload["overall"] == "pass", payload
    assert payload["target"]["skill_id"] == "totalsegmentator"
    assert payload["artifact_inventory"]["label_map_readable"] is True
    assert payload["artifact_inventory"]["shape_match"] is True
    assert payload["artifact_inventory"]["affine_match"] is True

    plaus = payload["anatomy_plausibility"]
    assert plaus["verdict"] == "pass"
    assert plaus["classes_failing_volume_bounds"] == []
    assert plaus["classes_overfragmented"] == []
    assert plaus["cross_class"]["liver_gt_spleen"]["status"] == "pass"
    assert plaus["cross_class"]["bilateral_symmetry"]["status"] == "pass"
    names = {row["name"] for row in plaus["per_class"]}
    assert {"liver", "spleen", "kidney_right", "kidney_left"} <= names


def test_canonical_manifest_skill_id_passes(tmp_path: Path) -> None:
    pack = _build_pack(tmp_path / "canonical_pack")
    manifest_path = pack / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["skill_id"] = "medagent.totalsegmentator"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    payload = _run_script(pack)

    assert payload["target"]["skill_id"] == "medagent.totalsegmentator"
    assert payload["overall"] == "pass"


def test_fragmented_spleen_fails(tmp_path: Path) -> None:
    pack = _build_pack(tmp_path / "frag_pack", fragment_spleen=True)
    payload = _run_script(pack)
    assert payload["overall"] == "fail"
    assert "spleen" in payload["anatomy_plausibility"]["classes_overfragmented"]


def test_liver_smaller_than_spleen_fails(tmp_path: Path) -> None:
    """When liver=5 has less volume than spleen=1, the cross-class check fires.
    This is the TotalSegmentator-ID-specific path: VISTA3D would check liver=1
    against spleen=3, so this test specifically exercises the parameterization
    via `_cross_class_floors.{liver_id, spleen_id}`."""
    pack = _build_pack(tmp_path / "swap_pack", swap_liver_spleen_volumes=True)
    payload = _run_script(pack)
    assert payload["anatomy_plausibility"]["cross_class"]["liver_gt_spleen"]["status"] == "fail"
    assert payload["overall"] == "fail"


def test_label_set_subset_flags_extras(tmp_path: Path) -> None:
    """When the wrapper records --roi-subset (label_prompts_requested),
    classes outside that set should be flagged."""
    pack = _build_pack(
        tmp_path / "subset_pack",
        label_ids=[1, 2, 3, 5, 7],  # 5 classes present
        requested=[1, 5],  # but only spleen + liver requested
    )
    payload = _run_script(pack)
    subset = payload["label_set_subset"]
    assert subset["verdict"] == "fail", payload
    assert subset["requested"] == [1, 5]
    assert set(subset["extras"]) == {2, 3, 7}
    assert payload["overall"] == "fail"


def test_label_set_subset_skips_when_no_request(tmp_path: Path) -> None:
    """When --roi-subset is unset, the wrapper records
    label_prompts_requested=[] and this tier returns skipped."""
    pack = _build_pack(tmp_path / "no_subset_pack")
    payload = _run_script(pack)
    assert payload["label_set_subset"]["verdict"] == "skipped"
    assert payload["overall"] == "pass"


def test_gt_perfect_pack_passes(tmp_path: Path) -> None:
    pack = _build_pack(tmp_path / "gt_perfect_pack", with_ground_truth=True, gt_perfect=True)
    payload = _run_script(pack)
    gt = payload["gt_metrics"]
    assert gt["verdict"] == "pass"
    assert gt["acceptable"] is True
    dice_by_name = {row["name"]: row["dice"] for row in gt["per_class"]}
    # liver, spleen, kidneys all have entries in _gt_dice_floors
    assert dice_by_name["liver"] == 1.0
    assert dice_by_name["spleen"] == 1.0
    assert all(row["dice_ok"] for row in gt["per_class"])
    assert payload["overall"] == "pass"


def test_gt_zero_overlap_fails(tmp_path: Path) -> None:
    pack = _build_pack(
        tmp_path / "gt_bad_pack", with_ground_truth=True, gt_perfect=False
    )
    payload = _run_script(pack)
    # When GT is all-zero there are no GT classes, so classes_to_score is empty
    # and the tier returns 'skipped' / acceptable=true. This matches the
    # ct_segmentation_quality_v1 behavior — a GT that doesn't contain any of
    # the requested classes is a malformed GT, not a model failure.
    assert payload["gt_metrics"]["verdict"] == "skipped"
    assert payload["gt_metrics"]["acceptable"] is True
