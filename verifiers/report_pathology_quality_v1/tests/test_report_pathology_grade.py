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

"""Tests for report_pathology_quality_v1."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
VERIFIER = REPO / "verifiers" / "report_pathology_quality_v1" / "scripts" / "grade.py"
PASS_PACK = REPO / "verifiers" / "report_pathology_quality_v1" / "fixtures" / "pass_pack"
FAIL_PACK = REPO / "verifiers" / "report_pathology_quality_v1" / "fixtures" / "fail_pack"


def _grade(pack: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(VERIFIER), str(pack)],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return json.loads(proc.stdout)


def test_clean_pack_passes() -> None:
    report = _grade(PASS_PACK)
    assert report["overall"] == "pass"
    assert report["pathology_quality"]["acceptable"] is True
    assert report["pathology_quality"]["n_fail"] == 0


def test_broken_pack_fails_on_coverage_parse_and_taxonomy() -> None:
    report = _grade(FAIL_PACK)
    assert report["overall"] == "fail"
    assert report["pathology_quality"]["acceptable"] is False
    failing = {c["name"] for c in report["checks"] if c["status"] == "fail"}
    assert "labels_fully_covered" in failing
    assert "json_parse_success_within_threshold" in failing
    assert "no_out_of_taxonomy_labels" in failing


def test_not_evaluated_json_warns_but_is_acceptable(tmp_path: Path) -> None:
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "manifest.json").write_text('{"skill_id":"report-pathology-classification"}\n')
    (pack / "validation_summary.json").write_text('{"overall_status":"passed"}\n')
    (pack / "output.json").write_text(
        json.dumps(
            {
                "skill": "report-pathology-classification",
                "n_reports": 5,
                "pathologies": {"n_labels": 10},
                "labels": {"label_coverage_rate": 1.0, "n_present_total": 7},
                "validation": {"method": "not_evaluated", "n_invalid_labels": 0},
            }
        )
        + "\n"
    )
    report = _grade(pack)
    assert report["overall"] == "warn"
    assert report["pathology_quality"]["acceptable"] is True
    warned = {c["name"] for c in report["checks"] if c["status"] == "warn"}
    assert "json_extraction_evaluated" in warned
