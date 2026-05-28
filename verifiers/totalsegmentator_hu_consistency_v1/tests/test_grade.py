"""Tests for totalsegmentator_hu_consistency_v1.

Synthetic packs built inline. Strategy: create a CT volume whose voxel
intensities follow a known map per organ, plus a mask that paints the
same regions with the matching label IDs. The verifier should report
median HU close to the planted value for each class.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import nibabel as nib
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
VERIFIER = REPO_ROOT / "verifiers" / "totalsegmentator_hu_consistency_v1"
SCRIPT = VERIFIER / "scripts" / "grade.py"


def _build_pack(
    pack_dir: Path,
    *,
    plant_hu: dict[int, float] | None = None,
) -> Path:
    """Build a pack with a CT + mask. plant_hu maps label_id -> HU value."""
    pack_dir.mkdir(parents=True, exist_ok=True)
    shape = (60, 60, 30)
    affine = np.diag([1.5, 1.5, 1.5, 1.0])
    ct = np.full(shape, -100.0, dtype=np.float32)  # background "air-ish"
    mask = np.zeros(shape, dtype=np.int16)

    # Default content: liver (5) @ 50 HU, spleen (1) @ 45 HU,
    # kidney_right (2) @ 35 HU, kidney_left (3) @ 35 HU, vertebrae_L1 (31) @ 400 HU,
    # lung_upper_lobe_left (10) @ -800 HU.
    if plant_hu is None:
        plant_hu = {5: 50, 1: 45, 2: 35, 3: 35, 31: 400, 10: -800}

    slabs = {
        5: (slice(0, 30), slice(0, 30), slice(0, 30)),
        1: (slice(30, 60), slice(0, 20), slice(0, 15)),
        2: (slice(0, 15), slice(30, 55), slice(0, 15)),
        3: (slice(15, 30), slice(30, 55), slice(0, 15)),
        31: (slice(30, 45), slice(30, 50), slice(0, 15)),
        10: (slice(45, 60), slice(30, 50), slice(0, 15)),
    }
    for lid, hu in plant_hu.items():
        if lid not in slabs:
            continue
        sl = slabs[lid]
        ct[sl] = hu
        mask[sl] = lid

    ct_path = pack_dir / "ct.nii.gz"
    mask_path = pack_dir / "predicted_seg.nii.gz"
    nib.save(nib.Nifti1Image(ct, affine), str(ct_path))
    nib.save(nib.Nifti1Image(mask, affine), str(mask_path))

    output_payload = {
        "skill": "totalsegmentator",
        "task": "total",
        "input": {"path": str(ct_path)},
        "output": {"path": str(mask_path), "shape": list(shape)},
    }
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


def test_planted_hu_within_bounds_passes(tmp_path: Path) -> None:
    pack = _build_pack(tmp_path / "good_pack")
    payload = _run_script(pack)

    assert payload["overall"] == "pass", payload
    hu = payload["hu_consistency"]
    assert hu["verdict"] == "pass"
    assert hu["classes_out_of_range"] == []
    # All 6 classes have bounds and are in-range
    assert hu["checked_count"] == 6
    assert hu["passing_count"] == 6
    by_name = {row["name"]: row for row in hu["per_class"]}
    assert by_name["liver"]["median_hu"] == 50.0
    assert by_name["spleen"]["median_hu"] == 45.0
    assert by_name["lung_upper_lobe_left"]["median_hu"] == -800.0


def test_liver_mask_planted_on_air_surfaces_in_per_class(tmp_path: Path) -> None:
    """The 'mask on the wrong tissue' failure mode: liver mask painted on
    voxels that are air-like (-900 HU). With only 1/6 classes failing,
    overall pass_fraction (5/6 = 0.833) still beats the 0.7 floor so
    the verdict is pass — but classes_out_of_range surfaces the liver
    issue for the agent / human to act on. This is intentional: an
    isolated mis-placement should not silently nuke the whole report."""
    pack = _build_pack(
        tmp_path / "wrong_tissue",
        plant_hu={5: -900, 1: 45, 2: 35, 3: 35, 31: 400, 10: -800},  # liver on air
    )
    payload = _run_script(pack)

    hu = payload["hu_consistency"]
    # Per-class catches it
    assert "liver" in hu["classes_out_of_range"]
    liver = next(r for r in hu["per_class"] if r["name"] == "liver")
    assert liver["median_hu"] == -900.0
    assert liver["in_range"] is False
    # But overall passes because 5/6 = 0.833 >= 0.7
    assert hu["pass_fraction"] > 0.7
    assert hu["verdict"] == "pass"
    assert payload["overall"] == "pass"


def test_below_min_pass_fraction_fails(tmp_path: Path) -> None:
    """When too many classes are out of HU range, the verdict fails."""
    # 5 of 6 organs planted at wrong HU (liver, spleen, kidneys, vertebra all
    # on air). Only lung is correct. 1/6 = 0.167 < 0.7 threshold.
    pack = _build_pack(
        tmp_path / "mostly_wrong",
        plant_hu={5: -900, 1: -900, 2: -900, 3: -900, 31: -900, 10: -800},
    )
    payload = _run_script(pack)
    assert payload["overall"] == "fail"
    hu = payload["hu_consistency"]
    assert hu["pass_fraction"] < 0.7
    assert hu["verdict"] == "fail"


def test_skipped_when_inputs_unreadable(tmp_path: Path) -> None:
    """When the pack references a CT path that doesn't exist, the verifier
    surfaces this as overall fail with a clear reason."""
    pack_dir = tmp_path / "broken_pack"
    pack_dir.mkdir()
    (pack_dir / "output.json").write_text(json.dumps({
        "skill": "totalsegmentator",
        "input": {"path": "/nonexistent/ct.nii.gz"},
        "output": {"path": "/nonexistent/mask.nii.gz"},
    }))
    (pack_dir / "validation_summary.json").write_text(json.dumps({"overall_status": "passed"}))
    (pack_dir / "manifest.json").write_text(json.dumps({"skill_id": "totalsegmentator"}))

    payload = _run_script(pack_dir)
    assert payload["overall"] == "fail"
    assert payload["hu_consistency"]["verdict"] == "skipped"
