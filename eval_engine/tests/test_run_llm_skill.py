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

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_run_llm_skill_mock_backend(tmp_path):
    out = tmp_path / "llm_pack"
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "eval_engine" / "run_llm_skill.py"),
            str(REPO_ROOT / "skills" / "dicom-metadata-extract"),
            "--fixture",
            str(REPO_ROOT / "skills" / "dicom-metadata-extract" / "fixtures" / "sample_ct.dcm"),
            "--out",
            str(out),
            "--backend",
            "mock",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

    interaction = json.loads((out / "llm_interaction.json").read_text())
    validation = json.loads((out / "validation_summary.json").read_text())
    output = json.loads((out / "output.json").read_text())
    trace = [json.loads(line) for line in (out / "agent_run_trace.jsonl").read_text().splitlines()]

    assert interaction["backend"] == "mock"
    assert interaction["tool_call"]["name"] == "run_skill"
    assert validation["llm_status"] == "tool_called"
    assert validation["overall_status"] == "passed"
    assert (out / "skill_run" / "validation_summary.json").exists()
    assert output["skill_pack"] == "skill_run"
    tool_start = next(record for record in trace if record["event_type"] == "tool_call_start")
    assert tool_start["command"] == [
        "python3",
        "eval_engine/run.py",
        "skills/dicom-metadata-extract",
        "--fixture",
        "skills/dicom-metadata-extract/fixtures/sample_ct.dcm",
        "--out",
        str(out / "skill_run"),
    ]
    assert tool_start["cwd"] == "."

    validate = subprocess.run(
        [sys.executable, "-m", "eval_engine.validate_pack", str(out)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert validate.returncode == 0, validate.stdout + validate.stderr
