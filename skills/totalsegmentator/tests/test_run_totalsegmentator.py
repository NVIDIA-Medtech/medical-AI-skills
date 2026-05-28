"""Unit tests for the TotalSegmentator wrapper.

These tests only exercise the pure helpers (geometry, mask summary, device
resolution, task licence). They do NOT invoke the upstream
`totalsegmentator.python_api`, which would require the installed package +
downloaded weights + GPU.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_totalsegmentator.py"
spec = importlib.util.spec_from_file_location("run_totalsegmentator", SCRIPT)
run_totalsegmentator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(run_totalsegmentator)


def _write_nifti(path: Path, data: np.ndarray, affine: np.ndarray) -> nib.Nifti1Image:
    img = nib.Nifti1Image(data, affine)
    nib.save(img, str(path))
    return img


def test_mask_summary_with_roi_subset_flags_extras(tmp_path: Path) -> None:
    affine = np.diag([float("1.5"), float("1.5"), float("2.0"), float("1.0")])
    input_img = _write_nifti(tmp_path / "ct.nii.gz", np.zeros((4, 5, 6)), affine)
    mask = np.zeros((4, 5, 6), dtype=np.int16)
    # liver(1)=12 voxels, spleen(3)=1 voxel
    mask[1:3, 1:4, 2:4] = 1
    mask[3, 3, 3] = 3
    mask_path = tmp_path / "ct_totalseg.nii.gz"
    _write_nifti(mask_path, mask, affine)

    summary = run_totalsegmentator._mask_summary(
        mask_path,
        input_img,
        requested_label_ids=[1],  # caller only asked for liver
        class_map={1: "liver", 3: "spleen"},
    )

    assert summary["label_prompts_requested"] == [1]
    assert summary["label_ids_present"] == [1, 3]
    assert summary["unexpected_label_ids"] == [3]
    assert summary["label_set_valid"] is False
    assert summary["class_counts"] == {"liver": 12, "spleen": 1}
    assert summary["voxel_volume_ml"] == 0.0045
    assert summary["geometry"]["shape_match"] is True
    assert summary["geometry"]["affine_match"] is True


def test_mask_summary_without_roi_subset_uses_full_class_map(tmp_path: Path) -> None:
    """When no --roi-subset is given, the full class_map is treated as
    'requested' — any out-of-range label IDs (e.g. corrupted output)
    should still land in unexpected_label_ids."""
    affine = np.eye(4)
    input_img = _write_nifti(tmp_path / "ct.nii.gz", np.zeros((4, 5, 6)), affine)
    mask = np.zeros((4, 5, 6), dtype=np.int16)
    mask[1, 1, 1] = 5
    mask[2, 2, 2] = 999  # out-of-range
    mask_path = tmp_path / "ct_totalseg.nii.gz"
    _write_nifti(mask_path, mask, affine)

    class_map = {i: f"class_{i}" for i in range(1, 118)}  # 117-class total task

    summary = run_totalsegmentator._mask_summary(
        mask_path,
        input_img,
        requested_label_ids=[],
        class_map=class_map,
    )

    assert summary["label_prompts_requested"] == []  # we didn't restrict
    assert summary["label_ids_present"] == [5, 999]
    assert summary["unexpected_label_ids"] == [999]
    assert summary["label_set_valid"] is False
    assert summary["any_label_present"] is True


def test_geometry_summary_detects_affine_mismatch(tmp_path: Path) -> None:
    input_img = _write_nifti(tmp_path / "ct.nii.gz", np.zeros((4, 5, 6)), np.eye(4))
    shifted = np.eye(4)
    shifted[0, 3] = 10.0
    output_img = _write_nifti(tmp_path / "mask.nii.gz", np.zeros((4, 5, 6)), shifted)

    geom = run_totalsegmentator._geometry_summary(input_img, output_img)
    assert geom["shape_match"] is True
    assert geom["spacing_match"] is True
    assert geom["affine_match"] is False
    assert geom["affine_max_abs_diff"] == 10.0


def test_task_license_marks_academic_tasks() -> None:
    assert run_totalsegmentator._task_license("total") == "non_commercial"
    assert run_totalsegmentator._task_license("total_mr") == "non_commercial"
    assert run_totalsegmentator._task_license("face") == "academic_only"
    assert run_totalsegmentator._task_license("brain_structures") == "academic_only"
    assert run_totalsegmentator._task_license("heartchambers_highres") == "academic_only"


def test_resolve_device_translates_to_ts_argument() -> None:
    pytest.importorskip("torch")
    ts_arg, resolved = run_totalsegmentator._resolve_device("cpu")
    assert ts_arg == "cpu" and resolved == "cpu"
    ts_arg, resolved = run_totalsegmentator._resolve_device("cuda")
    assert ts_arg == "gpu" and resolved == "cuda"
