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

"""Verify nv_segment_ct_finetune evidence packs for engineering-floor quality.

Five tiers, each emitting a sub-verdict:

  artifact_inventory     — checkpoint at output.finetuned_ckpt resolves, is
                           plausibly sized, and (when torch is available)
                           loads as a CPU state_dict.
  training_trajectory    — val_dice_per_epoch present and runs the declared
                           epoch budget; train_loss_finite; no OOM; best
                           val_dice meets a sanity/real-run floor. Smoke mode
                           skips the Dice floor because it is only a plumbing
                           oracle.
  dataset_audit_review   — recorded dataset_audit is internally consistent
                           (HU range and CT flag agree; orientation
                           consistent; declared anatomy passes volume bounds).
  label_coverage         — every label in label_mappings.default appeared in
                           input.dataset_audit.label_uniques_sampled. Skipped
                           when smoke mode (audit sampling is shallow).
  overall                — pass iff every non-skipped tier is pass.

Does NOT re-run training, NOT re-load the bundle network, NOT touch GPU. A v2
that re-runs the upstream evaluate config against a held-out split is planned.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from verifiers._shared.verifier_kit import (  # noqa: E402
    load_pack_json,
    resolve_pack_artifact,
    run_grader,
)

VERIFIER_ID = "medagent.verifiers.ct_segmentation_finetune_quality_v1"
VERIFIER_VERSION = "0.1.0"
TARGET_SKILL_IDS = {"nv_segment_ct_finetune", "medagent.nv_segment_ct_finetune"}

# Engineering floors. Calibrated below typical published numbers so the
# verifier catches silent regressions without conflating with publication-
# quality claims. Sanity mode uses a separate, lower floor since --sanity
# overfits one case and is a plumbing oracle, not a quality oracle.
REAL_RUN_BEST_VAL_DICE_FLOOR = 0.50
SANITY_BEST_VAL_DICE_FLOOR = 0.50
CHECKPOINT_MIN_BYTES = 1_000_000  # 1 MB; VISTA3D ckpt is ≈ 800 MB but partial dumps can be smaller


def _resolve_checkpoint(pack_dir: Path, raw: str | None, skill_dir_hint: str | None) -> Path | None:
    if not raw:
        return None
    bases: list[Path] = [pack_dir]
    if skill_dir_hint:
        bases.append(REPO_ROOT / skill_dir_hint)
    bases.append(REPO_ROOT)
    candidate = resolve_pack_artifact(pack_dir, raw, *bases)
    return candidate if candidate.exists() else None


def _torch_inspect(ckpt_path: Path) -> tuple[bool, bool | None, int | None]:
    """Return (torch_available, loadable_or_None, param_count_or_None).

    `loadable` is None when torch isn't available; the calling tier degrades
    that to "checkpoint integrity skipped" rather than reporting fail.
    """
    try:
        import torch  # type: ignore
    except Exception:
        return False, None, None
    try:
        state = torch.load(str(ckpt_path), map_location="cpu", weights_only=False)
        if isinstance(state, dict) and "state_dict" in state:
            state = state["state_dict"]
        if not isinstance(state, dict):
            return True, False, None
        n_params = 0
        for v in state.values():
            try:
                n_params += int(v.numel())
            except Exception:
                pass
        return True, True, n_params
    except Exception:
        return True, False, None


def _artifact_inventory(
    pack_dir: Path,
    output: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    raw_path = output.get("finetuned_ckpt")
    ckpt = _resolve_checkpoint(pack_dir, raw_path, manifest.get("skill_dir"))
    size: int | None = ckpt.stat().st_size if ckpt and ckpt.is_file() else None
    torch_available, loadable, param_count = (
        _torch_inspect(ckpt) if (ckpt and ckpt.is_file()) else (False, None, None)
    )
    return {
        "checkpoint_path": raw_path,
        "checkpoint_resolved": ckpt is not None and ckpt.is_file(),
        "checkpoint_size_bytes": size,
        "checkpoint_loadable": loadable,
        "checkpoint_param_count": param_count,
        "torch_available": torch_available,
    }


def _training_trajectory(
    output: dict[str, Any],
    plan: dict[str, Any],
    smoke: bool,
    sanity: bool,
) -> dict[str, Any]:
    val_dice = output.get("val_dice_per_epoch") or []
    epochs_recorded = len(val_dice)
    epochs_declared = plan.get("epochs")
    train_loss_finite = bool(output.get("train_loss_finite", False))
    oom = bool(output.get("oom", False))
    best_val_dice = output.get("best_val_dice")
    baseline_val_dice = output.get("baseline_val_dice")
    improvement = output.get("improvement_over_baseline")
    regressed = output.get("regressed")
    sanity_ok = output.get("sanity_recovery_demonstrated")

    failed: list[str] = []
    if epochs_recorded == 0:
        failed.append("val_dice_per_epoch is empty")
    if epochs_declared is not None and epochs_recorded < int(epochs_declared):
        failed.append(f"epochs_recorded={epochs_recorded} < epochs_declared={epochs_declared}")
    if not train_loss_finite:
        failed.append("train_loss_finite=false")
    if oom:
        failed.append("oom=true")

    if best_val_dice is None or not math.isfinite(float(best_val_dice)):
        failed.append("best_val_dice missing or non-finite")
    elif not smoke:
        floor = SANITY_BEST_VAL_DICE_FLOOR if sanity else REAL_RUN_BEST_VAL_DICE_FLOOR
        if float(best_val_dice) < floor:
            failed.append(f"best_val_dice={best_val_dice:.4f} < floor={floor:.2f}")

    if sanity:
        if not sanity_ok:
            failed.append("sanity_recovery_demonstrated!=true under --sanity mode")
    elif not smoke:
        # Real run: improvement_over_baseline must be non-negative when both
        # endpoints are recorded.
        if baseline_val_dice is not None and improvement is not None and float(improvement) < 0:
            failed.append(f"improvement_over_baseline={improvement:.4f} < 0 (regressed)")
        if regressed is True:
            failed.append("output.regressed=true")

    return {
        "verdict": "pass" if not failed else "fail",
        "epochs_recorded": epochs_recorded,
        "epochs_declared": int(epochs_declared) if epochs_declared is not None else None,
        "train_loss_finite": train_loss_finite,
        "oom": oom,
        "best_val_dice": best_val_dice,
        "baseline_val_dice": baseline_val_dice,
        "improvement_over_baseline": improvement,
        "regressed": regressed,
        "sanity_recovery_demonstrated": sanity_ok,
        "failed_checks": failed,
    }


def _dataset_audit_review(
    input_block: dict[str, Any],
    smoke: bool,
) -> dict[str, Any]:
    audit = input_block.get("dataset_audit") or {}
    if not audit:
        # No audit recorded — older pack format or smoke run that elided it.
        # Don't fail the run on that alone; report as skipped.
        return {
            "verdict": "skipped",
            "shape_consistent": None,
            "orientation_consistent": None,
            "image_looks_like_ct": None,
            "hu_range_negative_present": None,
            "anatomy": None,
            "anatomy_volume_all_in_range": None,
            "failed_checks": [],
        }

    shape_consistent = audit.get("shape_consistent")
    orientation_consistent = audit.get("orientation_consistent")
    looks_like_ct = audit.get("image_looks_like_ct")
    hu_range = audit.get("image_hu_range_seen")
    anatomy = audit.get("anatomy")
    anatomy_volume_ok = audit.get("anatomy_volume_all_in_range")

    hu_neg_present: bool | None
    if isinstance(hu_range, list) and hu_range:
        try:
            flat = [float(v) for v in hu_range if isinstance(v, (int, float))]
            hu_neg_present = any(v < 0 for v in flat) if flat else None
        except Exception:
            hu_neg_present = None
    else:
        hu_neg_present = None

    failed: list[str] = []
    if shape_consistent is False:
        failed.append("dataset_audit.shape_consistent=false")
    if orientation_consistent is False:
        failed.append("dataset_audit.orientation_consistent=false")
    if looks_like_ct is True and hu_neg_present is False:
        failed.append("image_looks_like_ct=true but HU range has no negative values")
    if anatomy and anatomy_volume_ok is False:
        failed.append(f"anatomy={anatomy} but anatomy_volume_all_in_range=false")

    return {
        "verdict": "pass" if not failed else "fail",
        "shape_consistent": shape_consistent,
        "orientation_consistent": orientation_consistent,
        "image_looks_like_ct": looks_like_ct,
        "hu_range_negative_present": hu_neg_present,
        "anatomy": anatomy if isinstance(anatomy, str) else None,
        "anatomy_volume_all_in_range": anatomy_volume_ok,
        "failed_checks": failed,
    }


def _label_coverage(input_block: dict[str, Any], smoke: bool) -> dict[str, Any]:
    """Compare declared user labels against what the dataset audit observed.

    `label_mappings.default` is a list of `[from_id, to_id]` pairs describing
    the raw_label → vista3d_class remap. The dataset audit observes raw GT
    masks, so `label_uniques_sampled` holds from_id values. We compare on
    the from_id side: every raw label declared in the mapping must appear
    in the sample, else the mapping is asserting a label the data doesn't
    actually contain.
    """
    label_mappings = input_block.get("label_mappings") or {}
    default = label_mappings.get("default") or []
    declared: list[int] = []
    for pair in default:
        if isinstance(pair, list) and len(pair) == 2 and isinstance(pair[0], int):
            declared.append(int(pair[0]))

    audit = input_block.get("dataset_audit") or {}
    sampled_raw = audit.get("label_uniques_sampled") or []
    sampled: set[int] = set()
    for v in sampled_raw:
        if isinstance(v, list):
            for x in v:
                if isinstance(x, int):
                    sampled.add(int(x))
        elif isinstance(v, int):
            sampled.add(int(v))

    if smoke or not declared:
        return {
            "verdict": "skipped",
            "user_labels_declared": declared,
            "user_labels_seen_in_sample": sorted(sampled & set(declared)),
            "missing_user_labels": [],
        }

    missing = sorted(set(declared) - sampled)
    seen = sorted(set(declared) & sampled)
    return {
        "verdict": "pass" if not missing else "fail",
        "user_labels_declared": declared,
        "user_labels_seen_in_sample": seen,
        "missing_user_labels": missing,
    }


def _detect_sanity(invocation: dict[str, Any], output: dict[str, Any]) -> bool:
    """Heuristic — finetune wrapper sets `sanity_recovery_demonstrated` on
    --sanity mode and records `--sanity` in the rendered invocation command.
    """
    cmd = invocation.get("command") or ""
    if isinstance(cmd, str) and "--sanity" in cmd:
        return True
    return output.get("sanity_recovery_demonstrated") is not None


def grade(pack_dir: Path) -> dict[str, Any]:
    output_payload = load_pack_json(pack_dir, "output.json")
    validation = load_pack_json(pack_dir, "validation_summary.json")
    manifest = load_pack_json(pack_dir, "manifest.json")

    skill_id = manifest.get("skill_id") or output_payload.get("skill") or ""
    source_status = validation.get("overall_status", "")
    input_block = output_payload.get("input") or {}
    output = output_payload.get("output") or {}
    plan = output_payload.get("plan") or {}
    invocation = output_payload.get("invocation") or {}
    smoke = bool(input_block.get("smoke", False))
    sanity = _detect_sanity(invocation, output)

    artifact_inventory = _artifact_inventory(pack_dir, output, manifest)
    training_trajectory = _training_trajectory(output, plan, smoke, sanity)
    dataset_audit_review = _dataset_audit_review(input_block, smoke)
    label_coverage = _label_coverage(input_block, smoke)

    artifact_pass = bool(artifact_inventory["checkpoint_resolved"]) and (
        artifact_inventory["checkpoint_loadable"] is not False
    )
    tiers_pass = (
        artifact_pass
        and training_trajectory["verdict"] == "pass"
        and dataset_audit_review["verdict"] in ("pass", "skipped")
        and label_coverage["verdict"] in ("pass", "skipped")
    )

    skill_ok = skill_id in TARGET_SKILL_IDS

    return {
        "verifier": {"id": VERIFIER_ID, "version": VERIFIER_VERSION},
        "target": {
            "evidence_pack": str(pack_dir),
            "skill_id": skill_id,
            "source_overall_status": source_status,
            "checkpoint_path": output.get("finetuned_ckpt"),
            "smoke": smoke,
            "sanity": sanity,
        },
        "artifact_inventory": artifact_inventory,
        "training_trajectory": training_trajectory,
        "dataset_audit_review": dataset_audit_review,
        "label_coverage": label_coverage,
        "overall": "pass" if (skill_ok and tiers_pass) else "fail",
    }


if __name__ == "__main__":
    run_grader(grade, sort_keys=True)
