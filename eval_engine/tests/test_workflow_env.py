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

"""Workflow runner passes per-step env to eval_engine subprocesses."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]


def test_run_step_merges_step_env(tmp_path: Path) -> None:
    from eval_engine.run_workflow import _run_step

    skill_dir = REPO / "skills" / "dicom-metadata-extract"
    fixture = skill_dir / "fixtures" / "sample_ct.dcm"
    step_out = tmp_path / "step"
    captured: dict = {}

    def fake_run(cmd, capture_output, text, cwd, env):
        captured["env"] = dict(env)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    with patch("eval_engine.run_workflow.subprocess.run", fake_run):
        _run_step(
            skill_dir,
            fixture,
            step_out,
            trusted=False,
            step_env={"CUSTOM_STEP_ENV": "enabled"},
        )

    assert captured["env"]["CUSTOM_STEP_ENV"] == "enabled"
