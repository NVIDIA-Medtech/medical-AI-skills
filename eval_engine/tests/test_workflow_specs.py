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

"""Sanity-check flagship workflow YAML specs load and declare expected steps."""

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO / "examples" / "workflows"


def _load(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text())


def test_ct_dicom_to_segmentation_workflow():
    spec = _load("ct_dicom_to_segmentation_evidence.yaml")
    assert spec["workflow_id"] == "ct_dicom_to_segmentation_evidence"
    steps = spec["steps"]
    assert len(steps) == 2
    assert steps[0]["skill"] == "skills/dicom-series-to-volume"
    assert steps[0]["inputs"]["fixture"] == "${input}"
    assert steps[1]["id"] == "segment"
    assert steps[1]["skill"] == "skills/nv-segment-ct"
    assert steps[1]["trusted"] is True
    assert steps[1]["inputs"]["fixture"] == "${convert.output.path}"


def test_dicom_preflight_workflow_trusted():
    spec = _load("dicom_preflight_gate.yaml")
    assert spec["workflow_id"] == "dicom_preflight_gate"
    assert len(spec["steps"]) == 1
    step = spec["steps"][0]
    assert step["skill"] == "skills/dicom-series-preflight"
    assert step["trusted"] is True
    assert step["inputs"]["fixture"] == "${input}"
