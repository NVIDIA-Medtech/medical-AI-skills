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

"""Shared pytest helpers for eval_engine tests."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_SCRIPT = "import json\n" "print(json.dumps({'output': {'ok': True}}))\n"


@pytest.fixture(scope="session", autouse=True)
def _ensure_dicom_metadata_extract_fixture() -> None:
    """Regenerate `skills/dicom-metadata-extract/fixtures/sample_ct.dcm` on demand.

    The .dcm fixture is gitignored synthetic data — local devs generate it once
    via the skill's `generate_sample.py`. Several eval_engine tests run the
    dicom_metadata_extract skill end-to-end against this fixture, so on a fresh
    CI checkout the file must be created before those tests run.
    """
    fixture = REPO_ROOT / "skills" / "dicom-metadata-extract" / "fixtures" / "sample_ct.dcm"
    if fixture.exists():
        return
    generator = fixture.parent / "generate_sample.py"
    subprocess.run([sys.executable, str(generator)], check=True, cwd=REPO_ROOT)


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def write_toy_skill(tmp_path):
    """Factory: returns a callable that creates a minimal skill under tmp_path.

    Each call writes ``<tmp_path>/<name>/`` with a manifest, a trivial Python
    entrypoint, and an optional ``paired_verifiers`` block. The default script
    prints ``{"output": {"ok": true}}`` so the eval_engine sanity gate passes.
    """

    def _factory(
        name: str = "toy_skill",
        *,
        skill_id: str | None = None,
        script_body: str = DEFAULT_SCRIPT,
        paired_verifiers: str = "",
        manifest_extra: str = "",
    ) -> Path:
        skill = tmp_path / name
        (skill / "scripts").mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"# {name}\n")
        body = [
            f"id: {skill_id or 'test.' + name}",
            "version: 0.1.0",
            "inputs:",
            "  - name: fixture",
            "    type: file_path",
            "outputs:",
            "  - name: result_json",
            "    type: json",
            "runtime:",
            "  language: python",
            "  entrypoint: scripts/run.py",
        ]
        if paired_verifiers:
            body.append(paired_verifiers)
        if manifest_extra:
            body.append(manifest_extra)
        (skill / "skill_manifest.yaml").write_text("\n".join(body) + "\n")
        (skill / "scripts" / "run.py").write_text(script_body)
        return skill

    return _factory


@pytest.fixture
def run_module():
    """Factory: spawn `python -m <module>` from REPO_ROOT and return CompletedProcess."""

    def _run(module: str, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", module, *args],
            cwd=REPO_ROOT,
            env=os.environ.copy(),
            capture_output=True,
            text=True,
        )

    return _run
