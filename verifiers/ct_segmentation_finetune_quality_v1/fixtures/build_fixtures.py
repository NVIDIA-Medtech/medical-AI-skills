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

"""Generate synthetic nv_segment_ct_finetune evidence packs for verifier tests.

Writes three pack variants under fixtures/:
  pass_pack/      valid checkpoint, healthy trajectory, clean audit, full label coverage.
  regress_pack/   same shape but `output.regressed=true` + improvement<0.
  bad_audit_pack/ dataset_audit.shape_consistent=false; the verifier should fail.

The checkpoint stand-in is a 1.2 MB random binary (well above the 1 MB floor).
When torch is installed at test time the verifier will try to torch.load it
and fail loadability — but the verifier treats `checkpoint_loadable=False` as
a fail, so we instead emit a tiny real torch.save state_dict when torch is
present at build time. The fallback (random bytes) is what CI sees; the
verifier's tier handles `checkpoint_loadable=None` (no torch in env) as
acceptable.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parent
PACKS = ("pass_pack", "regress_pack", "bad_audit_pack")
CHECKPOINT_BYTES = 1_200_000  # > CHECKPOINT_MIN_BYTES (1_000_000)


def _write_ckpt(path: Path) -> None:
    """Write a checkpoint stand-in ≥ 1 MB.

    With torch: torch.save a state_dict large enough to clear the 1 MB
    integrity floor naturally — never pad with random bytes, that corrupts
    the pickle. Without torch: write a 1.2 MB random binary; the verifier
    treats `checkpoint_loadable=None` (no torch in env) as acceptable.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import torch

        # 800x800 float32 ≈ 2.56 MB raw; pickle overhead trivial. Single
        # tensor, no funny structure, so torch.load reconstructs cleanly.
        state = {"layer0.weight": torch.zeros(800, 800), "layer0.bias": torch.zeros(800)}
        torch.save(state, str(path))
    except Exception:
        path.write_bytes(os.urandom(CHECKPOINT_BYTES))


def _base_output() -> dict:
    return {
        "skill": "nv_segment_ct_finetune",
        "model": "VISTA3D",
        "model_repo": "nvidia/Medical-AI",
        "version": "0.3.0",
        "input": {
            "dataset_dir": "<repo>/.workbench_data/datasets/Task09_Spleen",
            "datalist": "skills/nv-segment-ct-finetune/fixtures/datalist_spleen_finetune.json",
            "n_train_cases": 8,
            "label_mappings": {"default": [[1, 3]]},
            "label_mapping_resolution": {},
            "dataset_audit": {
                "datalist_source": "msd09_spleen",
                "n_pairs": 8,
                "shape_consistent": True,
                "affine_max_drift_max": 1e-6,
                "label_uniques_sampled": [[0, 1]],
                "user_label_idx_present_in_sample": True,
                "orientation_codes_seen": ["LPS"],
                "orientation_consistent": True,
                "image_dtypes_seen": ["float32"],
                "label_dtypes_seen": ["uint8"],
                "image_hu_range_seen": [-1024, 1500],
                "image_looks_like_ct": True,
                "fg_volumes_ml_seen": [180.0, 210.5, 195.2],
                "fg_components_seen": [1, 1, 1],
                "anatomy": "spleen",
                "anatomy_volume_all_in_range": True,
                "anatomy_components_all_match": True,
                "per_sample": [],
            },
            "smoke": False,
        },
        "environment": {
            "gpu_count": 1,
            "gpu_total_mb": 48000,
            "gpu_free_mb": 47000,
            "host_ram_mb": 64000,
            "cuda_available": True,
        },
        "plan": {
            "patch_size": [96, 96, 96],
            "train_dataset_cache_rate": 0.5,
            "epochs": 3,
            "learning_rate": 0.0001,
            "nproc_per_node": 1,
            "multi_gpu": False,
            "rationale": ["smoke build"],
        },
        "invocation": {
            "command": "monai.bundle run training --config_file ...",
            "command_prefix": "python -m",
            "config_stack": ["train.yaml", "data.yaml", "override.yaml"],
            "multi_gpu": False,
            "cwd": "/<home>/Medical AI Skills",
        },
        "output": {
            "finetuned_ckpt": "checkpoint.pt",
            "finetuned_ckpt_exists": True,
            "pretrained_ckpt": "bundle/models/model.pt",
            "recommended_ckpt": "checkpoint.pt",
            "baseline_val_dice": 0.45,
            "best_val_dice": 0.72,
            "best_epoch_index": 2,
            "improvement_over_baseline": 0.27,
            "regressed": False,
            "improved": True,
            "sanity_recovery_demonstrated": None,
            "val_dice_per_epoch": [0.50, 0.65, 0.72],
            "train_loss_first": 1.2,
            "train_loss_last": 0.3,
            "train_loss_finite": True,
            "oom": False,
        },
        "runtime": {"wall_seconds": 33.0, "peak_gpu_mb": 12000, "return_code": 0},
        "cost": {"steps": [{"step": "train", "seconds": 30.0}], "total_seconds": 33.0},
        "intended_use_disclaimer": "Engineering verification only.",
    }


def _write_pack(name: str, mutator) -> None:
    pack = FIXTURE_DIR / name
    pack.mkdir(parents=True, exist_ok=True)
    output = _base_output()
    mutator(output)
    (pack / "output.json").write_text(json.dumps(output, indent=2))
    (pack / "manifest.json").write_text(
        json.dumps(
            {
                "pack_format_version": "1.0.0",
                "pack_kind": "skill_run",
                "run_id": f"{name}_run",
                "skill_id": "nv_segment_ct_finetune",
                "skill_version": "0.3.0",
                "skill_dir": "skills/nv-segment-ct-finetune",
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
    _write_ckpt(pack / "checkpoint.pt")


def _pass(output: dict) -> None:
    pass


def _regress(output: dict) -> None:
    output["output"]["best_val_dice"] = 0.40
    output["output"]["improvement_over_baseline"] = -0.05
    output["output"]["regressed"] = True
    output["output"]["improved"] = False
    output["output"]["val_dice_per_epoch"] = [0.50, 0.45, 0.40]


def _bad_audit(output: dict) -> None:
    output["input"]["dataset_audit"]["shape_consistent"] = False
    output["input"]["dataset_audit"]["orientation_consistent"] = False


def main() -> None:
    _write_pack("pass_pack", _pass)
    _write_pack("regress_pack", _regress)
    _write_pack("bad_audit_pack", _bad_audit)


if __name__ == "__main__":
    main()
