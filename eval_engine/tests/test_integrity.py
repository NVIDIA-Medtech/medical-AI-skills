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

from eval_engine.integrity import _integrity_scan


def test_nvidia_disclosure_program_url_is_allowed(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    (skill_dir / "skill-card.md").write_text(
        "Please report NVIDIA AI Concerns "
        "at https://app.intigriti.com/programs/nvidia/nvidiavdp/detail.\n"
    )

    result = _integrity_scan(skill_dir)

    assert result == {"status": "clean", "findings": [], "n_findings": 0}
