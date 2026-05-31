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

"""Tests for container provenance capture."""

from __future__ import annotations

from unittest.mock import patch

from eval_engine.container_provenance import (
    capture_docker_image_inspect,
    merge_container_into_provenance,
    write_container_environment_lock,
)


def test_merge_uses_skill_capture_block() -> None:
    prov = {"container": {}}
    skill_block = {
        "inspect": {"status": "ok", "id": "sha256:abc", "repo_tags": ["img:main"]},
        "pip_freeze": {"status": "ok", "pip_freeze_lines": 2, "pip_freeze_text": "pkg==1\n"},
    }
    merge_container_into_provenance(
        prov,
        image_ref="img:main",
        image_id="sha256:old",
        skill_container_block=skill_block,
    )
    assert prov["container"]["image_digest_observed"] == "sha256:abc"
    assert prov["container"]["pip_freeze_lines"] == 2


def test_write_container_environment_lock(tmp_path) -> None:
    path = write_container_environment_lock(
        tmp_path,
        {"status": "ok", "pip_freeze_text": "numpy==1.0\n"},
    )
    assert path is not None
    assert path.read_text().startswith("numpy")


@patch("eval_engine.container_provenance._run")
def test_inspect_failed_when_docker_missing(mock_run) -> None:
    mock_run.return_value = (127, "", "not found")
    result = capture_docker_image_inspect("holohub-endoscopy_tool_tracking:main")
    assert result["status"] == "failed"
