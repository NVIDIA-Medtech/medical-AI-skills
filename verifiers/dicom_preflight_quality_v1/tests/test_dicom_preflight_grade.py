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

"""Tests for dicom_preflight_quality_v1."""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FIXTURES = REPO / "skills" / "dicom-series-preflight" / "fixtures"


def test_grade_pass_on_clean_pack(tmp_path):
    from eval_engine.run import main as run_main  # noqa: F401 — ensure import path

    skill_out = tmp_path / "skill_pack"
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO / "eval_engine" / "run.py"),
            str(REPO / "skills" / "dicom-series-preflight"),
            "--fixture",
            str(FIXTURES / "clean_no_phi"),
            "--out",
            str(skill_out),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout

    grade_proc = subprocess.run(
        [
            sys.executable,
            str(REPO / "verifiers" / "dicom_preflight_quality_v1" / "scripts" / "grade.py"),
            str(skill_out),
        ],
        capture_output=True,
        text=True,
    )
    assert grade_proc.returncode == 0
    report = json.loads(grade_proc.stdout)
    assert report["overall"] == "pass"
    assert report["target"]["evidence_pack"] == str(skill_out.resolve())
