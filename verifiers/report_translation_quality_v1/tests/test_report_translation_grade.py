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

"""Tests for report_translation_quality_v1."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
VERIFIER = REPO / "verifiers" / "report_translation_quality_v1" / "scripts" / "grade.py"
PASS_PACK = REPO / "verifiers" / "report_translation_quality_v1" / "fixtures" / "pass_pack"
FAIL_PACK = REPO / "verifiers" / "report_translation_quality_v1" / "fixtures" / "fail_pack"


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
    assert report["translation_quality"]["acceptable"] is True
    assert report["translation_quality"]["n_fail"] == 0


def test_poor_pack_fails_on_qc_language_and_tokens() -> None:
    report = _grade(FAIL_PACK)
    assert report["overall"] == "fail"
    assert report["translation_quality"]["acceptable"] is False
    failing = {c["name"] for c in report["checks"] if c["status"] == "fail"}
    assert "translation_qc_pass_rate" in failing
    assert "residual_non_english_within_threshold" in failing
    assert "anonymization_tokens_preserved" in failing


def test_warn_band_is_acceptable(tmp_path: Path) -> None:
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "manifest.json").write_text('{"skill_id":"report-translation"}\n')
    (pack / "validation_summary.json").write_text('{"overall_status":"passed"}\n')
    (pack / "output.json").write_text(
        json.dumps(
            {
                "skill": "report-translation",
                "n_reports": 10,
                "qc": {
                    "method": "llm_judge",
                    "n_evaluated": 10,
                    "n_pass": 8,
                    "n_fail": 2,
                    "n_unknown": 0,
                    "pass_rate": 0.8,
                },
                "language": {
                    "method": "llm_detect",
                    "n_evaluated": 10,
                    "n_non_english": 0,
                    "non_english_rate": 0.0,
                },
                "token_preservation": {
                    "n_reports_with_tokens": 6,
                    "n_reports_token_dropped": 0,
                    "preservation_rate": 1.0,
                },
            }
        )
        + "\n"
    )
    report = _grade(pack)
    assert report["overall"] == "warn"
    assert report["translation_quality"]["acceptable"] is True
