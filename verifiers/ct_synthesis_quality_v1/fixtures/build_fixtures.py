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

"""Generate synthetic nv_generate_ct_rflow evidence packs for verifier tests.

Writes three pack variants under fixtures/:
  pass_pack/                 image has air-range + bone-range voxels, label has
                             a non-empty in-range class set, geometry matches.
  constant_image_pack/       image is a constant float (silent diffusion failure).
  out_of_range_label_pack/   label contains an id outside the VISTA3D 132-class
                             schema.

Run via `python verifiers/ct_synthesis_quality_v1/fixtures/build_fixtures.py`
or via the verifier's conftest (auto-regenerates if a pack is missing).
"""

from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np

FIXTURE_DIR = Path(__file__).resolve().parent
PACK_NAMES = ("pass_pack", "constant_image_pack", "out_of_range_label_pack")
SHAPE = (8, 8, 8)
AFFINE = np.diag([1.5, 1.5, 2.0, 1.0])


def _save_pair(pack: Path, stem: str, image: np.ndarray, mask: np.ndarray) -> tuple[str, str]:
    pack.mkdir(parents=True, exist_ok=True)
    img_path = pack / f"{stem}_image.nii.gz"
    lbl_path = pack / f"{stem}_label.nii.gz"
    nib.save(nib.Nifti1Image(image.astype(np.float32), AFFINE), str(img_path))
    nib.save(nib.Nifti1Image(mask.astype(np.int16), AFFINE), str(lbl_path))
    return str(img_path), str(lbl_path)


def _output_payload(samples: list[dict], output_label_mapping: list[dict]) -> dict:
    requested_anatomy = [str(item["anatomy"]) for item in output_label_mapping]
    expected_output_ids = sorted({int(item["output_label_id"]) for item in output_label_mapping})
    union_label_ids = sorted({lid for s in samples for lid in s.get("label_ids_present", [])})
    return {
        "skill": "nv_generate_ct_rflow",
        "model": "NVIDIA-Medtech/NV-Generate-CTMR (rflow-ct)",
        "model_repo": "https://github.com/NVIDIA-Medtech/NV-Generate-CTMR",
        "model_weights_repo": "https://huggingface.co/nvidia/NV-Generate-CT",
        "license": "NVIDIA Open Model License (commercial-friendly)",
        "input": {
            "config_infer_override_path": None,
            "config_infer_override": {},
            "anatomy_list_requested": requested_anatomy,
            "body_region_requested": ["chest"],
            "num_output_samples_requested": 1,
            "output_size_requested": [256, 256, 256],
            "spacing_requested": [1.5, 1.5, 2.0],
            "random_seed": 0,
            "version": "rflow-ct",
        },
        "output": {
            "directory": "<pack>",
            "samples": samples,
            "num_samples": len(samples),
            "all_pairs_readable": True,
            "all_geometry_consistent": True,
            "any_foreground_present": True,
            "all_images_nonconstant": True,
            "all_images_hu_like": True,
            "union_label_ids_present": union_label_ids,
            "output_label_mapping": output_label_mapping,
            "expected_output_label_ids": expected_output_ids,
            "missing_expected_output_label_ids": sorted(
                set(expected_output_ids) - set(union_label_ids)
            ),
            "all_effective_anatomy_labels_present": set(expected_output_ids).issubset(
                union_label_ids
            ),
        },
        "invocation": {
            "upstream_root": "/<home>/nv-generate-ctmr",
            "upstream_commit": "0" * 40,
            "command": ["python", "-m", "scripts.inference", "--version", "rflow-ct"],
            "exit_code": 0,
            "subprocess_seconds": 60.0,
            "model_inventory": {"all_present": True, "files": []},
            "rendered_infer_config": {"num_output_samples": 1},
            "rendered_env_output_dir": "<pack>",
        },
        "runtime": {"subprocess_seconds": 60.0, "device": "cuda"},
        "logs": {"stdout_tail": "", "stderr_tail": ""},
        "intended_use_disclaimer": "Engineering verification only.",
    }


def _write_pack(
    name: str, image: np.ndarray, mask: np.ndarray, output_label_mapping: list[dict]
) -> None:
    pack = FIXTURE_DIR / name
    stem = "sample_20260519_120000_000000"
    img_path, lbl_path = _save_pair(pack, stem, image, mask)
    sample = {
        "image_path": Path(img_path).name,
        "label_path": Path(lbl_path).name,
        "image_readable": True,
        "label_readable": True,
        "image_shape": list(image.shape),
        "label_shape": list(mask.shape),
        "image_spacing": [1.5, 1.5, 2.0],
        "label_spacing": [1.5, 1.5, 2.0],
        "label_ids_present": sorted(int(v) for v in np.unique(mask).tolist() if int(v) != 0),
        "label_id_count": int(len(np.unique(mask)) - (1 if 0 in np.unique(mask) else 0)),
        "label_foreground_voxels": int((mask != 0).sum()),
        "shape_match": True,
        "spacing_match": True,
        "affine_match": True,
        "image_hu_min": float(image.min()),
        "image_hu_max": float(image.max()),
        "image_hu_negative_present": bool((image < -500).any()),
        "image_hu_bone_present": bool((image > 200).any()),
        "image_nonconstant": bool(image.max() - image.min() > 1.0),
    }
    (pack / "output.json").write_text(
        json.dumps(_output_payload([sample], output_label_mapping), indent=2) + "\n"
    )
    (pack / "manifest.json").write_text(
        json.dumps(
            {
                "pack_format_version": "1.0.0",
                "pack_kind": "skill_run",
                "run_id": f"{name}_run",
                "skill_id": "nv_generate_ct_rflow",
                "skill_version": "0.1.0",
                "skill_dir": "skills/nv-generate-ct-rflow",
            },
            indent=2,
        )
    )
    (pack / "validation_summary.json").write_text(
        json.dumps(
            {
                "overall_status": "passed",
                "preflight_status": "passed",
                "sanity_status": "passed",
            },
            indent=2,
        )
    )


def main() -> None:
    rng = np.random.default_rng(0)
    # pass_pack: bimodal HU distribution (air + bone), mask has classes 3, 23.
    good_image = rng.uniform(-1000, 600, size=SHAPE).astype(np.float32)
    good_mask = np.zeros(SHAPE, dtype=np.int16)
    good_mask[2:5, 2:5, 2:5] = 3
    good_mask[6, 6, 6] = 23
    good_mapping = [
        {"anatomy": "spleen", "maisi_label_id": 3, "output_label_id": 3},
        {"anatomy": "lung tumor", "maisi_label_id": 23, "output_label_id": 23},
    ]
    _write_pack("pass_pack", good_image, good_mask, good_mapping)

    # constant_image_pack: every voxel = 0.0 (diffusion sampler degenerate).
    const_image = np.zeros(SHAPE, dtype=np.float32)
    _write_pack("constant_image_pack", const_image, good_mask, good_mapping)

    # out_of_range_label_pack: image is fine; mask has id 999 (outside VISTA3D 132).
    bad_mask = np.zeros(SHAPE, dtype=np.int16)
    bad_mask[1, 1, 1] = 999
    bad_mapping = [{"anatomy": "lung tumor", "maisi_label_id": 23, "output_label_id": 999}]
    _write_pack("out_of_range_label_pack", good_image, bad_mask, bad_mapping)


if __name__ == "__main__":
    main()
