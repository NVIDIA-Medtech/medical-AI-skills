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

from eval_engine.common import REPO_ROOT, _sanitize_pip_freeze, _sanitize_public_text


def test_sanitize_pip_freeze_redacts_host_local_file_urls() -> None:
    text = "demo @ file:///build/task_123/conda-bld/demo/work\n" "numpy==2.3.5\n"

    assert _sanitize_pip_freeze(text) == (
        "demo @ file://<local-build-path-redacted>\n" "numpy==2.3.5\n"
    )


def test_sanitize_public_text_redacts_repo_and_home_paths() -> None:
    text = (
        f"loaded {REPO_ROOT / 'skills/demo/output.json'}\n" f"{Path.home() / '.cache/model.bin'}\n"
    )

    sanitized = _sanitize_public_text(text)

    assert "skills/demo/output.json" in sanitized
    assert "<HOME>/" in sanitized
    assert "/home/" not in sanitized
