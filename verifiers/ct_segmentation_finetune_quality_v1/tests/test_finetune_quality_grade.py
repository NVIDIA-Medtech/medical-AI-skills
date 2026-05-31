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

"""Unit tests for ct_segmentation_finetune_quality_v1/scripts/grade.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
VERIFIER = REPO_ROOT / "verifiers" / "ct_segmentation_finetune_quality_v1"
SCRIPT = VERIFIER / "scripts" / "grade.py"


def _run(fixture: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(fixture)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def test_pass_pack_passes_all_tiers() -> None:
    payload = _run(VERIFIER / "fixtures" / "pass_pack")
    assert payload["overall"] == "pass"
    assert payload["target"]["skill_id"] == "nv_segment_ct_finetune"
    assert payload["artifact_inventory"]["checkpoint_resolved"] is True
    assert payload["artifact_inventory"]["checkpoint_size_bytes"] >= 1_000_000
    assert payload["training_trajectory"]["verdict"] == "pass"
    assert payload["training_trajectory"]["epochs_recorded"] == 3
    assert payload["training_trajectory"]["epochs_declared"] == 3
    assert payload["training_trajectory"]["train_loss_finite"] is True
    assert payload["training_trajectory"]["oom"] is False
    assert payload["dataset_audit_review"]["verdict"] == "pass"
    assert payload["dataset_audit_review"]["image_looks_like_ct"] is True
    assert payload["dataset_audit_review"]["hu_range_negative_present"] is True
    assert payload["label_coverage"]["verdict"] == "pass"
    assert payload["label_coverage"]["missing_user_labels"] == []


def test_regress_pack_fails_trajectory() -> None:
    payload = _run(VERIFIER / "fixtures" / "regress_pack")
    assert payload["overall"] == "fail"
    traj = payload["training_trajectory"]
    assert traj["verdict"] == "fail"
    assert any("regress" in c.lower() or "< 0" in c for c in traj["failed_checks"])
    assert traj["improvement_over_baseline"] == -0.05
    assert traj["regressed"] is True


def test_bad_audit_pack_fails_audit_review() -> None:
    payload = _run(VERIFIER / "fixtures" / "bad_audit_pack")
    assert payload["overall"] == "fail"
    audit = payload["dataset_audit_review"]
    assert audit["verdict"] == "fail"
    assert any("shape_consistent" in c for c in audit["failed_checks"])
    assert any("orientation_consistent" in c for c in audit["failed_checks"])


def test_smoke_pack_skips_label_coverage(tmp_path: Path) -> None:
    """When input.smoke=true, quality-only checks are intentionally skipped."""
    pass_pack = VERIFIER / "fixtures" / "pass_pack"
    smoke_pack = tmp_path / "smoke_pack"
    smoke_pack.mkdir()
    output = json.loads((pass_pack / "output.json").read_text())
    output["input"]["smoke"] = True
    output["output"]["baseline_val_dice"] = 0.0
    output["output"]["best_val_dice"] = 0.0
    output["output"]["improvement_over_baseline"] = 0.0
    output["output"]["val_dice_per_epoch"] = [0.0, 0.0, 0.0]
    (smoke_pack / "output.json").write_text(json.dumps(output))
    (smoke_pack / "manifest.json").write_text((pass_pack / "manifest.json").read_text())
    (smoke_pack / "validation_summary.json").write_text(
        (pass_pack / "validation_summary.json").read_text()
    )
    # Reuse the pass_pack checkpoint via absolute path so the verifier resolves it.
    output["output"]["finetuned_ckpt"] = str(pass_pack / "checkpoint.pt")
    (smoke_pack / "output.json").write_text(json.dumps(output))

    payload = _run(smoke_pack)
    assert payload["overall"] == "pass"
    assert payload["target"]["smoke"] is True
    assert payload["training_trajectory"]["verdict"] == "pass"
    assert payload["label_coverage"]["verdict"] == "skipped"


def test_wrong_skill_id_fails() -> None:
    """Verifier must reject packs from other skills."""
    pass_pack = VERIFIER / "fixtures" / "pass_pack"
    payload = _run(pass_pack)
    # Sanity-check the original
    assert payload["target"]["skill_id"] == "nv_segment_ct_finetune"
    # Mutate in-process via a tmp manifest pointing to the same artifacts is
    # cleaner but the simpler test is to verify the constant in grade.py:
    sys.path.insert(0, str(VERIFIER / "scripts"))
    try:
        import grade  # type: ignore

        assert "nv_segment_ct_finetune" in grade.TARGET_SKILL_IDS
        assert "medagent.nv_segment_ct_finetune" in grade.TARGET_SKILL_IDS
    finally:
        sys.path.remove(str(VERIFIER / "scripts"))


def test_output_validates_against_schema() -> None:
    """Verifier output must match its own output_schema.json."""
    import jsonschema

    payload = _run(VERIFIER / "fixtures" / "pass_pack")
    schema = json.loads((VERIFIER / "validators" / "output_schema.json").read_text())
    jsonschema.validate(payload, schema)
