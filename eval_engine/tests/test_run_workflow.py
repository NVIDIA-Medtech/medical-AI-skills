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

"""Tests for eval_engine.run_workflow."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_workflow(workflow: Path, fixture: Path, out: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "eval_engine" / "run_workflow.py"),
            str(workflow),
            "--input",
            str(fixture),
            "--out",
            str(out),
        ],
        cwd=REPO_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
    )


def _write_echo_skill(tmp_path: Path, skill_name: str, *, paired_verifiers: str = "") -> Path:
    skill = tmp_path / skill_name
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text("# " + skill_name + "\n")
    body = [
        "id: test." + skill_name,
        "version: 0.1.0",
        "inputs:",
        "  - name: fixture",
        "    type: file_path",
        "outputs:",
        "  - name: result_json",
        "    type: json",
        "runtime:",
        "  language: python",
        "  entrypoint: scripts/run.py",
    ]
    if paired_verifiers:
        body.append(paired_verifiers)
    (skill / "skill_manifest.yaml").write_text("\n".join(body) + "\n")
    (skill / "scripts" / "run.py").write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        "p = Path(sys.argv[1])\n"
        "payload = {'output': {'path': str(p), 'ok': True}}\n"
        "print(json.dumps(payload))\n"
    )
    return skill


def _write_fail_skill(tmp_path: Path) -> Path:
    skill = tmp_path / "fail_skill"
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text("# fail\n")
    (skill / "skill_manifest.yaml").write_text(
        "\n".join(
            [
                "id: test.fail_skill",
                "version: 0.1.0",
                "inputs:",
                "  - name: fixture",
                "    type: file_path",
                "outputs:",
                "  - name: result_json",
                "    type: json",
                "runtime:",
                "  language: python",
                "  entrypoint: scripts/run.py",
                "validation:",
                "  sanity_checks:",
                "    - {path: output.ok, eq: true}",
            ]
        )
        + "\n"
    )
    (skill / "scripts" / "run.py").write_text(
        "import json, sys\nprint(json.dumps({'output': {'ok': False}}))\n"
    )
    return skill


def test_workflow_chains_output_between_steps(tmp_path):
    step_a = _write_echo_skill(tmp_path, "step_a")
    step_b = _write_echo_skill(tmp_path, "step_b")
    fixture = tmp_path / "input.txt"
    fixture.write_text("hello")

    workflow = tmp_path / "chain.yaml"
    workflow.write_text(
        yaml.dump(
            {
                "workflow_id": "chain_test",
                "steps": [
                    {
                        "id": "first",
                        "skill": str(step_a),
                        "inputs": {"fixture": "${input}"},
                    },
                    {
                        "id": "second",
                        "skill": str(step_b),
                        "inputs": {"fixture": "${first.output.path}"},
                    },
                ],
            }
        )
    )
    out = tmp_path / "wf_out"
    proc = _run_workflow(workflow, fixture, out)
    assert proc.returncode == 0, proc.stdout + proc.stderr

    summary = json.loads((out / "workflow_summary.json").read_text())
    assert summary["overall_status"] == "passed"
    assert summary["n_steps_completed"] == 2
    assert (out / "second" / "output.json").exists()


def test_workflow_halts_when_convert_fails(tmp_path):
    ok_skill = _write_echo_skill(tmp_path, "ok_skill")
    fail_skill = _write_fail_skill(tmp_path)
    fixture = tmp_path / "input.txt"
    fixture.write_text("x")

    workflow = tmp_path / "halt.yaml"
    workflow.write_text(
        yaml.dump(
            {
                "workflow_id": "halt_test",
                "steps": [
                    {
                        "id": "convert",
                        "skill": str(fail_skill),
                        "inputs": {"fixture": "${input}"},
                    },
                    {
                        "id": "segment",
                        "skill": str(ok_skill),
                        "inputs": {"fixture": "${convert.output.path}"},
                    },
                ],
            }
        )
    )
    out = tmp_path / "wf_halt"
    proc = _run_workflow(workflow, fixture, out)
    assert proc.returncode == 1, proc.stdout + proc.stderr

    summary = json.loads((out / "workflow_summary.json").read_text())
    assert summary["overall_status"] == "failed"
    assert summary["n_steps_completed"] == 0
    assert len(summary["steps"]) == 1
    assert not (out / "segment").exists()


def test_workflow_trusted_step_writes_trust_summary(tmp_path):
    """Trusted segment step produces skill_run/ and trust_summary.json."""
    convert = _write_echo_skill(tmp_path, "convert_skill")
    segment = _write_echo_skill(tmp_path, "segment_skill")
    nifti = tmp_path / "volume.nii.gz"
    nifti.write_bytes(b"\x00")
    fixture = nifti

    (convert / "scripts" / "run.py").write_text(
        "import json\n" f"print(json.dumps({{'output': {{'path': {str(nifti)!r}}}}}))\n"
    )

    workflow = tmp_path / "trusted.yaml"
    workflow.write_text(
        yaml.dump(
            {
                "workflow_id": "trusted_test",
                "steps": [
                    {
                        "id": "convert",
                        "skill": str(convert),
                        "inputs": {"fixture": "${input}"},
                    },
                    {
                        "id": "segment",
                        "skill": str(segment),
                        "trusted": True,
                        "inputs": {"fixture": "${convert.output.path}"},
                    },
                ],
            }
        )
    )

    out = tmp_path / "wf_trusted"
    proc = _run_workflow(workflow, fixture, out)
    assert proc.returncode == 0, proc.stdout + proc.stderr

    summary = json.loads((out / "workflow_summary.json").read_text())
    assert summary["overall_status"] == "passed"
    seg = next(s for s in summary["steps"] if s["id"] == "segment")
    assert seg["mode"] == "trusted"
    assert seg["trust_overall"] == "no_verifiers"
    assert (out / "segment" / "trust_summary.json").exists()
    assert (out / "segment" / "skill_run" / "output.json").exists()
    assert summary["trust"]["steps"]["segment"]["trust_overall"] == "no_verifiers"


def test_orientation_gate_halts_before_segmentation():
    """LR-flipped DICOM series fails convert sanity; segment never runs."""
    workflow = REPO_ROOT / "examples/workflows/ct_dicom_to_segmentation_evidence.yaml"
    fixture = REPO_ROOT / "skills/dicom-series-to-volume/fixtures/flipped_lr"
    if not fixture.is_dir():
        return  # fixtures not generated in this checkout

    out = REPO_ROOT / "runs" / "test_workflow_flipped_lr"
    if out.exists():
        import shutil

        shutil.rmtree(out)
    proc = _run_workflow(workflow, fixture, out)
    assert proc.returncode == 1, proc.stdout + proc.stderr

    summary = json.loads((out / "workflow_summary.json").read_text())
    assert summary["overall_status"] == "failed"
    assert summary["n_steps_completed"] == 0
    assert len(summary["steps"]) == 1
    assert summary["steps"][0]["id"] == "convert"
    assert summary["steps"][0]["sanity_status"] == "failed"
    assert not (out / "segment").exists()


def test_workflow_summary_helpers():
    from eval_engine.run_workflow import _workflow_overall

    steps = [{"overall_status": "passed"}, {"overall_status": "passed", "trust_overall": "passed"}]
    assert _workflow_overall(steps, halted=False) == "passed"

    steps_gap = [{"overall_status": "passed"}, {"overall_status": "passed", "trust_overall": "gap"}]
    assert _workflow_overall(steps_gap, halted=False) == "gap"

    steps_fail = [{"overall_status": "failed"}]
    assert _workflow_overall(steps_fail, halted=True) == "failed"
