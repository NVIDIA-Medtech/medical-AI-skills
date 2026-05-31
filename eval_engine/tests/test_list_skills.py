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

import json
from pathlib import Path

from eval_engine import list_skills


def _write_pack_manifest(path: Path, skill_id: str) -> None:
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"skill_id": skill_id}))


def test_collect_packs_collapses_nested_trusted_run_roots(tmp_path, monkeypatch) -> None:
    evidence_root = tmp_path / "examples" / "evidence_packs"
    trusted_run = evidence_root / "dicom_series_preflight_trusted_pass"
    _write_pack_manifest(
        trusted_run / "skill_run" / "manifest.json",
        "medagent.dicom_series_preflight",
    )
    _write_pack_manifest(
        trusted_run / "verifiers" / "dicom_preflight_quality_v1" / "manifest.json",
        "medagent.verifiers.dicom_preflight_quality_v1",
    )
    monkeypatch.setattr(list_skills, "PACK_ROOTS", (evidence_root,))

    packs_by_skill = list_skills._collect_packs()

    assert packs_by_skill["medagent.dicom_series_preflight"] == {trusted_run}
    assert packs_by_skill["medagent.verifiers.dicom_preflight_quality_v1"] == {trusted_run}
