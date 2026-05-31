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

from pathlib import Path

from eval_engine.common import REPO_ROOT
from eval_engine.preflight import _preflight_checks


def test_preflight_paths_are_repo_relative_for_committed_fixtures() -> None:
    manifest = {"inputs": [{"name": "input", "type": "file_path"}]}

    status, checks = _preflight_checks(manifest, REPO_ROOT / "README.md")

    assert status == "passed"
    assert {check["path"] for check in checks if "path" in check} == {"README.md"}


def test_preflight_keeps_external_paths_absolute(tmp_path: Path) -> None:
    fixture = tmp_path / "input.txt"
    fixture.write_text("fixture\n")
    manifest = {"inputs": [{"name": "input", "type": "file_path"}]}

    status, checks = _preflight_checks(manifest, fixture)

    assert status == "passed"
    assert {check["path"] for check in checks if "path" in check} == {str(fixture)}


def test_preflight_accepts_declared_default_sentinel() -> None:
    manifest = {
        "inputs": [
            {
                "name": "input",
                "type": "directory_path",
                "formats": ["gxf_replayer_dir", "default_sentinel"],
            }
        ]
    }

    status, checks = _preflight_checks(manifest, Path("default"))

    assert status == "passed"
    assert checks == [
        {
            "name": "fixture_default_sentinel",
            "path": "default",
            "status": "passed",
        }
    ]


def test_preflight_rejects_default_without_declared_sentinel() -> None:
    manifest = {"inputs": [{"name": "input", "type": "directory_path"}]}

    status, checks = _preflight_checks(manifest, Path("default"))

    assert status == "failed"
    assert checks[0]["name"] == "fixture_exists"
    assert checks[0]["status"] == "failed"
