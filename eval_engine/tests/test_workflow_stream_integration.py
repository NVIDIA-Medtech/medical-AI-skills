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

"""Integration: workflow summary includes stream block from flow-benchmark step."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_flow_echo_skill(tmp_path: Path) -> Path:
    """Minimal skill that prints holohub_flow_benchmark-shaped JSON (no GPU/HoloHub)."""
    from eval_engine.tests.test_workflow_stream import _flow_payload

    skill = tmp_path / "flow_echo"
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text("# flow echo\n")
    (skill / "skill_manifest.yaml").write_text(
        "\n".join(
            [
                "id: test.flow_echo",
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
                "    - {path: plan.app, eq: imaging_ai_segmentator}",
            ]
        )
        + "\n"
    )
    (skill / "scripts" / "run.py").write_text(
        "import json, sys\n"
        "payload = " + repr(_flow_payload()) + "\n"
        "print(json.dumps(payload))\n"
    )
    return skill


def _write_echo_skill(tmp_path: Path, name: str) -> Path:
    skill = tmp_path / name
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text(f"# {name}\n")
    (skill / "skill_manifest.yaml").write_text(
        f"id: test.{name}\nversion: 0.1.0\n"
        "inputs:\n  - name: fixture\n    type: file_path\n"
        "outputs:\n  - name: result_json\n    type: json\n"
        "runtime:\n  language: python\n  entrypoint: scripts/run.py\n"
        "validation:\n  sanity_checks:\n    - {path: output.ok, eq: true}\n"
    )
    (skill / "scripts" / "run.py").write_text(
        "import json, sys\nprint(json.dumps({'output': {'ok': True}}))\n"
    )
    return skill


def test_workflow_summary_stream_from_flow_benchmark_step(tmp_path: Path) -> None:
    echo = _write_echo_skill(tmp_path, "app_echo")
    flow_echo = _write_flow_echo_skill(tmp_path)
    fixture = tmp_path / "in.txt"
    fixture.write_text("x")

    workflow = tmp_path / "wf.yaml"
    workflow.write_text(
        yaml.dump(
            {
                "workflow_id": "stream_integration",
                "steps": [
                    {
                        "id": "holohub_app",
                        "skill": str(echo),
                        "inputs": {"fixture": "${input}"},
                    },
                    {
                        "id": "flow_benchmark",
                        "skill": str(flow_echo),
                        "inputs": {"fixture": "${input}"},
                    },
                ],
            }
        )
    )
    out = tmp_path / "wf_out"
    proc = subprocess.run(
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
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

    summary = json.loads((out / "workflow_summary.json").read_text())
    stream = summary.get("stream") or {}
    assert stream.get("present") is True
    assert stream.get("stream_format_version") == "1.0.0"
    assert stream.get("holohub_app") == "imaging_ai_segmentator"
    assert stream.get("holohub_commit") == "abc123"
    assert stream["primary_latency"]["p95_ms"] == 12.5

    flow_step = stream["steps"]["flow_benchmark"]["holoscan_flow"]
    assert flow_step["latency"]["paths_observed"] == 2
    assert flow_step["latency"]["total_latency_samples"] == 160
    assert flow_step["contract"]["all_assertions_passed"] is True
    assert flow_step["artifacts"]["logger"]["count"] == 2

    record = (out / "workflow_run_record.md").read_text()
    assert "## Stream (Holoscan flow benchmark)" in record
    assert "primary latency" in record
