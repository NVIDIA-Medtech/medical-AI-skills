#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Verify dicom_series_to_volume evidence packs."""

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

VERIFIER_ID = "medagent.verifiers.dicom_volume_quality_v1"
VERIFIER_VERSION = "0.1.0"
TARGET_SKILL_IDS = {"dicom_series_to_volume", "medagent.dicom_series_to_volume"}
DISCLAIMER_TERMS = (
    "Engineering verification only",
    "Not a vetted clinical",
    "does not auto-reorient",
)
TOLERANCE = 1e-3


def _public_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def _as_float_array(value: Any) -> np.ndarray | None:
    try:
        return np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        return None


def _same_numbers(reported: Any, actual: Any, *, atol: float = TOLERANCE) -> bool:
    reported_arr = _as_float_array(reported)
    actual_arr = _as_float_array(actual)
    if reported_arr is None or actual_arr is None:
        return False
    return reported_arr.shape == actual_arr.shape and bool(
        np.allclose(reported_arr, actual_arr, atol=atol)
    )


def _load_nifti(path: Path) -> tuple[nib.Nifti1Image | None, np.ndarray | None, str | None]:
    try:
        img = nib.load(str(path))
        data = np.asanyarray(img.dataobj)
    except Exception as exc:
        return None, None, str(exc)
    return img, data, None


def grade(pack_dir: Path) -> dict[str, Any]:
    pack_dir = pack_dir.resolve()
    output = load_pack_json(pack_dir, "output.json")
    validation = load_pack_json(pack_dir, "validation_summary.json")
    manifest = load_pack_json(pack_dir, "manifest.json")
    skill_id = str(manifest.get("skill_id") or "")

    output_info = output.get("output") or {}
    declared_path = output_info.get("path")
    artifact_path = (
        resolve_pack_artifact(pack_dir, declared_path, REPO_ROOT)
        if declared_path
        else pack_dir / ""
    )
    artifact_exists = bool(declared_path) and artifact_path.exists()

    img = None
    data = None
    load_error = "artifact path not declared"
    if artifact_exists:
        img, data, load_error = _load_nifti(artifact_path)

    actual_shape = list(img.shape) if img is not None else []
    actual_spacing = (
        [float(v) for v in img.header.get_zooms()[: len(actual_shape)]] if img is not None else []
    )
    actual_axcodes = list(nib.aff2axcodes(img.affine)) if img is not None else []
    actual_affine = img.affine.tolist() if img is not None else []
    voxel_min = float(np.nanmin(data)) if data is not None and data.size else None
    voxel_max = float(np.nanmax(data)) if data is not None and data.size else None
    actual_hu_range = (
        [voxel_min, voxel_max] if voxel_min is not None and voxel_max is not None else []
    )
    n_slices_reported = output.get("n_slices")
    shape_reported = output_info.get("shape")
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
            "modality_ct",
            output.get("modality") == "CT",
            f"modality={output.get('modality')!r}",
        ),
        make_check(
            "single_series",
            output.get("single_series") is True,
            f"single_series={output.get('single_series')!r}",
        ),
        make_check(
            "no_inconsistent_shape",
            output.get("inconsistent_shape") is False,
            f"inconsistent_shape={output.get('inconsistent_shape')!r}",
        ),
        make_check(
            "output_artifact_declared",
            bool(declared_path),
            f"output.path={declared_path!r}",
        ),
        make_check(
            "output_artifact_exists",
            artifact_exists,
            f"resolved={_public_path(artifact_path)}",
        ),
        make_check(
            "nifti_loadable",
            img is not None,
            "NIfTI loaded" if img is not None else f"load error={load_error}",
        ),
        make_check(
            "shape_matches_nifti",
            shape_reported == actual_shape,
            f"reported={shape_reported!r}, actual={actual_shape!r}",
        ),
        make_check(
            "spacing_matches_nifti",
            _same_numbers(output_info.get("spacing"), actual_spacing[:3]),
            f"reported={output_info.get('spacing')!r}, actual={actual_spacing[:3]!r}",
        ),
        make_check(
            "axcodes_match_nifti",
            output_info.get("axcodes") == actual_axcodes[:3],
            f"reported={output_info.get('axcodes')!r}, actual={actual_axcodes[:3]!r}",
        ),
        make_check(
            "affine_matches_nifti",
            _same_numbers(output_info.get("affine"), actual_affine),
            "reported affine matches loaded NIfTI affine",
        ),
        make_check(
            "finite_voxels",
            data is not None and data.size > 0 and bool(np.isfinite(data).all()),
            f"shape={actual_shape!r}",
        ),
        make_check(
            "hu_range_matches_nifti",
            _same_numbers(output.get("hu_range"), actual_hu_range),
            f"reported={output.get('hu_range')!r}, actual={actual_hu_range!r}",
        ),
        make_check(
            "n_slices_matches_shape",
            isinstance(n_slices_reported, int)
            and len(actual_shape) >= 3
            and n_slices_reported == actual_shape[2],
            f"n_slices={n_slices_reported!r}, shape={actual_shape!r}",
        ),
        make_check(
            "scope_disclosed",
            all(term in disclaimer for term in DISCLAIMER_TERMS),
            "disclaimer must preserve engineering-only, non-clinical, no-auto-reorient scope",
        ),
    ]

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
            "output_artifact": _public_path(artifact_path) if declared_path else None,
        },
        "volume_quality": {
            "n_fail": len(fail_checks),
            "n_warn": len(warn_checks),
            "verdict": overall,
            "acceptable": overall in {"pass", "warn"},
            "shape": actual_shape,
            "spacing": [round(float(v), 4) for v in actual_spacing[:3]],
            "axcodes": actual_axcodes[:3],
            "hu_range": actual_hu_range,
        },
        "checks": checks,
        "warnings": [check["reason"] for check in warn_checks],
        "overall": overall,
    }


if __name__ == "__main__":
    run_grader(grade)
