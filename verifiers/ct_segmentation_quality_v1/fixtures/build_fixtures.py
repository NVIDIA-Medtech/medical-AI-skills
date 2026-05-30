#!/usr/bin/env python3
"""Regenerate the deterministic NIfTI fixtures for ct_segmentation_quality_v1.

Run from repo root:
    python verifiers/ct_segmentation_quality_v1/fixtures/build_fixtures.py
"""
from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np

FIXTURES = Path(__file__).resolve().parent

# Synthetic-only geometry. Deliberately coarse 10 mm isotropic spacing so
# blob voxel counts in a small cube map to adult-range organ volumes
# (1 voxel = 1 mL). Real CTs have ~1 mm spacing; this is a fixture.
SHAPE = (40, 40, 40)
SPACING = (10.0, 10.0, 10.0)
VOXEL_ML = float(np.prod(SPACING)) / 1000.0  # 1.0 mL


def _ball(shape, center, radius, value):
    zs, ys, xs = np.ogrid[: shape[0], : shape[1], : shape[2]]
    dist2 = (zs - center[0]) ** 2 + (ys - center[1]) ** 2 + (xs - center[2]) ** 2
    return np.where(dist2 <= radius * radius, value, 0)


def _build_pass_mask() -> np.ndarray:
    mask = np.zeros(SHAPE, dtype=np.int16)
    # 1 voxel = 1 mL at 10 mm isotropic spacing.
    # liver (~900 mL) right side
    liver = _ball(SHAPE, center=(20, 15, 28), radius=6, value=1)
    # spleen (~113 mL) left side, smaller than liver
    spleen = _ball(SHAPE, center=(20, 15, 10), radius=3, value=3)
    # right kidney (~113 mL)
    rk = _ball(SHAPE, center=(10, 25, 30), radius=3, value=5)
    # left kidney (~113 mL), symmetric
    lk = _ball(SHAPE, center=(10, 25, 8), radius=3, value=14)
    for blob in (liver, spleen, rk, lk):
        mask = np.where(blob != 0, blob, mask)
    return mask


def _build_fragmented_mask(base: np.ndarray) -> np.ndarray:
    """Replace the single-blob spleen (label 3) with 60 scattered voxels."""
    mask = base.copy()
    mask[mask == 3] = 0
    rng = np.random.default_rng(seed=42)
    n_fragments = 60
    placed = 0
    while placed < n_fragments:
        z = int(rng.integers(2, SHAPE[0] - 2))
        y = int(rng.integers(2, SHAPE[1] - 2))
        x = int(rng.integers(2, 14))  # left side, like spleen
        if mask[z, y, x] == 0:
            mask[z, y, x] = 3
            placed += 1
    return mask


def _affine() -> np.ndarray:
    aff = np.eye(4)
    aff[0, 0] = SPACING[0]
    aff[1, 1] = SPACING[1]
    aff[2, 2] = SPACING[2]
    return aff


def _output_json(mask_path: Path, mask: np.ndarray, *, ground_truth_path: str | None) -> dict:
    label_ids = sorted(int(v) for v in np.unique(mask) if int(v) != 0)
    counts = {}
    inv = {1: "liver", 3: "spleen", 5: "right kidney", 14: "left kidney"}
    for lid in label_ids:
        counts[inv.get(lid, f"label_id_{lid}")] = int((mask == lid).sum())
    return {
        "skill": "nv_segment_ct",
        "model": "NVIDIA-Medtech/NV-Segment-CT (VISTA3D)",
        "model_repo": "https://huggingface.co/nvidia/NV-Segment-CT",
        "license": "NVIDIA Open Model License (commercial-friendly)",
        "input": {
            "path": "synthetic_ct.nii.gz",
            "shape": list(SHAPE),
            "ndim": 3,
            "spacing": list(SPACING),
            "ground_truth_path": ground_truth_path,
        },
        "output": {
            "path": str(mask_path.name),
            "shape": list(mask.shape),
            "label_prompts_requested": [1, 3, 5, 14],
            "label_ids_present": label_ids,
            "unexpected_label_ids": [],
            "label_set_valid": True,
            "class_counts": counts,
            "any_label_present": True,
            "geometry": {
                "input_shape": list(SHAPE),
                "output_shape": list(SHAPE),
                "shape_match": True,
                "input_spacing": list(SPACING),
                "output_spacing": list(SPACING),
                "spacing_match": True,
                "affine_max_abs_diff": 0.0,
                "affine_match": True,
            },
        },
        "invocation": {
            "official_helper": "hugging_face_pipeline.HuggingFacePipelineHelper",
            "pipeline_name": "vista3d",
            "weights_dir": "fixture",
        },
        "runtime": {
            "model_load_seconds": 0.0,
            "inference_seconds": 0.0,
            "device": "cpu",
        },
        "intended_use_disclaimer": "Fixture data; engineering verification only.",
    }


def _validation_summary() -> dict:
    return {
        "overall_status": "passed",
        "schema_status": "passed",
        "sanity_status": "passed",
    }


def _manifest() -> dict:
    return {
        "run_id": "fixture",
        "skill_id": "nv_segment_ct",
        "skill_version": "0.2.0",
    }


def _write_pack(
    pack_dir: Path,
    mask: np.ndarray,
    *,
    ground_truth: np.ndarray | None = None,
    ground_truth_basename: str | None = None,
) -> None:
    pack_dir.mkdir(parents=True, exist_ok=True)
    aff = _affine()
    mask_path = pack_dir / "predicted_seg.nii.gz"
    nib.save(nib.Nifti1Image(mask.astype(np.int16), aff), str(mask_path))

    gt_path = None
    if ground_truth is not None and ground_truth_basename is not None:
        gt_path = pack_dir / ground_truth_basename
        nib.save(nib.Nifti1Image(ground_truth.astype(np.int16), aff), str(gt_path))

    output = _output_json(
        mask_path,
        mask,
        ground_truth_path=ground_truth_basename if gt_path else None,
    )
    (pack_dir / "output.json").write_text(json.dumps(output, indent=2) + "\n")
    (pack_dir / "validation_summary.json").write_text(
        json.dumps(_validation_summary(), indent=2) + "\n"
    )
    (pack_dir / "manifest.json").write_text(json.dumps(_manifest(), indent=2) + "\n")


def main() -> None:
    pass_mask = _build_pass_mask()
    _write_pack(FIXTURES / "pass_pack", pass_mask)
    fragmented = _build_fragmented_mask(pass_mask)
    _write_pack(FIXTURES / "fragmented_pack", fragmented)
    # GT pack: predicted == GT for a clean Dice=1.0 run.
    _write_pack(
        FIXTURES / "gt_pass_pack",
        pass_mask,
        ground_truth=pass_mask,
        ground_truth_basename="reference_seg.nii.gz",
    )
    print("Fixtures regenerated under", FIXTURES)


if __name__ == "__main__":
    main()
