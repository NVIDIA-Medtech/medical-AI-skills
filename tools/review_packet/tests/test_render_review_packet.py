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

from __future__ import annotations

import json
from pathlib import Path

from tools.render_review_packet import render_review_packet

REPO_ROOT = Path(__file__).resolve().parents[3]


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2))


def _write_minimal_pack(
    pack: Path, *, skill_id: str = "medagent.test", overall: str = "passed"
) -> None:
    pack.mkdir(parents=True, exist_ok=True)
    _write_json(
        pack / "manifest.json",
        {
            "pack_format_version": "1.0.0",
            "pack_kind": "skill_run",
            "run_id": "test-run",
            "skill_id": skill_id,
            "skill_version": "0.1.0",
            "skill_dir": "skills/dicom-metadata-extract",
            "repo_git_sha": "abc123",
            "fixture": {
                "path": "fixture.json",
                "sha256": "fixture-sha",
                "size_bytes": 12,
            },
            "command": ["python", "script.py", "fixture.json"],
        },
    )
    _write_json(
        pack / "validation_summary.json",
        {
            "preflight_status": "passed",
            "schema_status": "passed",
            "sanity_status": "passed",
            "runtime_status": "within_envelope",
            "cost_status": "passed",
            "env_pin_status": "skipped",
            "overall_status": overall,
            "integrity_status": "clean",
            "integrity_n_findings": 0,
            "exit_code": 0,
            "errors": [],
        },
    )
    _write_json(pack / "runtime_profile.json", {"elapsed_seconds": 0.1, "exit_code": 0})
    _write_json(pack / "cost_profile.json", {"measured": {"wall_seconds": 0.1}})
    _write_json(pack / "integrity_check.json", {"status": "clean", "findings": [], "n_findings": 0})
    _write_json(pack / "output.json", {"output": {"path": "output.json"}})
    _write_json(
        pack / "provenance.json",
        {
            "captured_at": "2026-05-25T00:00:00+00:00",
            "gpu": {"available": False, "have_nvidia_smi": False, "have_nvcc": False, "gpus": []},
            "container": {"requires_docker": False, "image_digest_observed": None},
            "network": {"declared_endpoints": [], "observed_endpoints": None},
            "side_effects": {"before": [], "after": [], "findings": []},
        },
    )
    (pack / "agent_run_trace.jsonl").write_text(
        json.dumps({"kind": "tool_call_start", "tool": "script.py"})
        + "\n"
        + json.dumps({"kind": "tool_call_end", "tool": "script.py", "exit_code": 0})
        + "\n"
    )
    (pack / "environment.lock").write_text("example==1.0\n")
    (pack / "workflow_run_record.md").write_text("# Run\n")
    replay = pack / "replay.sh"
    replay.write_text("#!/usr/bin/env bash\n")
    replay.chmod(0o755)


def test_existing_paired_skill_pack_surfaces_verifier_gap() -> None:
    markdown = render_review_packet(REPO_ROOT / "examples/evidence_packs/nv_segment_ct_pass")

    assert "Review verdict: `gap`" in markdown
    assert "medagent.verifiers.ct_segmentation_quality_v1" in markdown
    assert "not bundled in a trusted-run summary" in markdown
    assert "## Gate Table" in markdown


def test_failed_pack_reports_preflight_failure() -> None:
    markdown = render_review_packet(REPO_ROOT / "examples/evidence_packs/dicom_invalid_input_fail")

    assert "Review verdict: `failed`" in markdown
    assert "preflight_status=failed" in markdown
    assert "overall_status=preflight_failed" in markdown
    assert "Verifier coverage skipped because the source pack did not pass" in markdown
    assert "not bundled in a trusted-run summary" not in markdown
    assert "Use `make run-trusted`" not in markdown


def test_trusted_run_reads_nested_verifier_pack(tmp_path: Path) -> None:
    root = tmp_path / "trusted"
    _write_minimal_pack(root / "skill_run")
    _write_minimal_pack(root / "verifiers" / "verifier_a", skill_id="medagent.verifiers.test")
    _write_json(
        root / "trust_summary.json",
        {
            "pack_format_version": "1.0.0",
            "trust_format_version": "1.0.0",
            "skill_id": "medagent.test",
            "skill_pack": "skill_run",
            "skill_overall": "passed",
            "verifiers": [
                {
                    "id": "medagent.verifiers.test",
                    "declared_status": "implemented",
                    "pack": "verifiers/verifier_a",
                    "overall": "warn",
                    "checks": ["shape"],
                    "hashes": {"manifest.json": "abcdef1234567890"},
                    "hard_failure_count": 0,
                    "warning_count": 1,
                    "warning_findings": ["advisory"],
                }
            ],
            "gaps": [],
            "warning_findings": [
                {
                    "id": "medagent.verifiers.test",
                    "pack": "verifiers/verifier_a",
                    "warning_count": 1,
                    "warnings": ["advisory"],
                }
            ],
            "evidence_packs": [
                {
                    "role": "skill",
                    "id": "medagent.test",
                    "pack": "skill_run",
                    "overall": "passed",
                    "hashes": {"manifest.json": "1111222233334444"},
                },
                {
                    "role": "verifier",
                    "id": "medagent.verifiers.test",
                    "pack": "verifiers/verifier_a",
                    "overall": "warn",
                    "hashes": {"manifest.json": "abcdef1234567890"},
                },
            ],
            "overall": "warn",
        },
    )

    markdown = render_review_packet(root)

    assert "Review verdict: `warn`" in markdown
    assert "Pack kind: `trusted_run`" in markdown
    assert "medagent.verifiers.test" in markdown
    assert "verifiers/verifier_a" in markdown
    assert "## Trust Evidence" in markdown
    assert "warning_count=1" in markdown
    assert "manifest.json=abcdef123456" in markdown


def test_trusted_run_summarizes_verifier_artifact_integrity(tmp_path: Path) -> None:
    root = tmp_path / "trusted"
    _write_minimal_pack(root / "skill_run")
    verifier_pack = root / "verifiers" / "ct_segmentation_quality"
    _write_minimal_pack(
        verifier_pack,
        skill_id="medagent.verifiers.ct_segmentation_quality_v1",
        overall="failed",
    )
    _write_json(
        verifier_pack / "output.json",
        {
            "verifier": {
                "id": "medagent.verifiers.ct_segmentation_quality_v1",
                "version": "0.1.0",
            },
            "artifact_inventory": {
                "label_map_count": 1,
                "usable_label_map_count": 0,
                "hash_mismatch_count": 2,
                "reference_artifact_count": 0,
            },
            "domain_floor": {"verdict": "fail", "checks": []},
            "dice_metrics": {"verdict": "skipped", "checks": []},
            "overall": "fail",
        },
    )
    _write_json(
        root / "trust_summary.json",
        {
            "trust_format_version": "1.0.0",
            "skill_id": "nv_segment_ct",
            "skill_pack": "skill_run",
            "skill_overall": "passed",
            "verifiers": [
                {
                    "id": "medagent.verifiers.ct_segmentation_quality_v1",
                    "declared_status": "implemented",
                    "pack": "verifiers/ct_segmentation_quality",
                    "overall": "failed",
                    "hard_failure_count": 1,
                    "warning_count": 0,
                }
            ],
            "gaps": [],
            "evidence_packs": [],
            "overall": "failed",
        },
    )

    markdown = render_review_packet(root)

    assert "hash_mismatch_count=2" in markdown
    assert "usable_label_map_count=0" in markdown
    assert "reference_artifact_count=0" in markdown
    assert "domain_floor=fail" in markdown
    assert "dice_metrics=skipped" in markdown
