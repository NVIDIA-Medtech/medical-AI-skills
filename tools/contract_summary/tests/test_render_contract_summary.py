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

from pathlib import Path

from tools.render_contract_summary import render_contract_summary

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_dicom_preflight_contract_summary_surfaces_core_contract() -> None:
    markdown = render_contract_summary(REPO_ROOT / "skills" / "dicom-series-preflight")

    assert "# Contract Summary: dicom-series-preflight" in markdown
    assert "medagent.dicom_series_preflight" in markdown
    assert "scripts/preflight_series.py" in markdown
    assert "dicom_dir" in markdown
    assert "preflight_json" in markdown
    assert "medagent.verifiers.dicom_preflight_quality_v1" in markdown
    assert "examples/evidence_packs/dicom_series_preflight_trusted_pass" in markdown
    assert "Header-only; does not decode pixel data" in markdown


def test_contract_summary_handles_verifier_contract() -> None:
    markdown = render_contract_summary(REPO_ROOT / "verifiers" / "dicom_preflight_quality_v1")

    assert "# Contract Summary: dicom-preflight-quality-v1" in markdown
    assert "medagent.verifiers.dicom_preflight_quality_v1" in markdown
    assert "scripts/grade.py" in markdown
    assert "dicom_series_preflight_evidence_pack" in markdown
    assert "dicom_preflight_quality_report" in markdown
