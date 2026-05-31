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

"""Tests for eval_engine.provenance."""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

from eval_engine.provenance import (  # noqa: E402
    _path_snapshot,
    _resolve_declared_path,
    capture_gpu_snapshot,
    capture_side_effects_snapshot,
    diff_side_effects,
)


def test_gpu_snapshot_shape():
    snap = capture_gpu_snapshot()
    assert isinstance(snap["available"], bool)
    assert isinstance(snap["have_nvidia_smi"], bool)
    assert isinstance(snap["have_nvcc"], bool)
    assert isinstance(snap["gpus"], list)


def test_resolves_home_path(tmp_path):
    resolved, reason = _resolve_declared_path("~/.cache/medical-AI-skills-test", skill_dir=tmp_path)
    assert reason is None
    assert resolved is not None
    assert str(resolved).startswith(str(Path.home()))


def test_skips_templated_path(tmp_path):
    resolved, reason = _resolve_declared_path("<caller-output>/result.nii.gz", skill_dir=tmp_path)
    assert resolved is None
    assert "templated" in reason


def test_resolves_repo_relative_path(tmp_path):
    resolved, reason = _resolve_declared_path("skills/dicom-metadata-extract", skill_dir=tmp_path)
    assert reason is None
    assert resolved is not None
    assert resolved == (REPO_ROOT / "skills/dicom-metadata-extract").resolve()


def test_resolves_out_token(tmp_path):
    out = tmp_path / "pack"
    resolved, reason = _resolve_declared_path("${out}/volume.nii.gz", skill_dir=tmp_path, out=out)
    assert reason is None
    assert resolved == (out / "volume.nii.gz").resolve()


def test_resolves_declared_env_var_path(tmp_path, monkeypatch):
    target = tmp_path / "env-target"
    monkeypatch.setenv("MEDICAL_AI_SKILLS_PROV_TEST_ROOT", str(target))

    resolved, reason = _resolve_declared_path(
        "$MEDICAL_AI_SKILLS_PROV_TEST_ROOT/output",
        skill_dir=tmp_path,
    )

    assert reason is None
    assert resolved == (target / "output").resolve()


def test_unset_declared_env_var_path_is_untracked(tmp_path, monkeypatch):
    monkeypatch.delenv("MEDICAL_AI_SKILLS_PROV_TEST_MISSING", raising=False)

    resolved, reason = _resolve_declared_path(
        "$MEDICAL_AI_SKILLS_PROV_TEST_MISSING/output",
        skill_dir=tmp_path,
    )

    assert resolved is None
    assert reason == "environment variable in path is unset"


def test_side_effect_snapshot_uses_public_repo_path():
    out = REPO_ROOT / "runs" / "prov-test"
    manifest = {"runtime": {"side_effects": {"local_writes": [{"path": "${out}/volume.nii.gz"}]}}}
    records = capture_side_effects_snapshot(manifest, skill_dir=REPO_ROOT, out=out)
    assert records[0]["resolved"] == "runs/prov-test/volume.nii.gz"


def test_path_snapshot_missing(tmp_path):
    snap = _path_snapshot(tmp_path / "nope")
    assert snap == {"exists": False}


def test_path_snapshot_file(tmp_path):
    f = tmp_path / "x.bin"
    f.write_bytes(b"hello")
    snap = _path_snapshot(f)
    assert snap["exists"] is True
    assert snap["is_file"] is True
    assert snap["size_bytes"] == 5


def test_diff_detects_creation(tmp_path):
    target = tmp_path / "new_file.txt"
    manifest = {"runtime": {"side_effects": {"local_writes": [{"path": str(target)}]}}}
    before = capture_side_effects_snapshot(manifest, skill_dir=tmp_path)
    assert before[0]["exists"] is False

    target.write_text("hi")

    after = capture_side_effects_snapshot(manifest, skill_dir=tmp_path)
    findings = diff_side_effects(before, after)
    assert len(findings) == 1
    assert findings[0]["change"] == "created"
    assert findings[0]["after_exists"] is True


def test_diff_marks_unchanged(tmp_path):
    target = tmp_path / "static.txt"
    target.write_text("constant")
    manifest = {"runtime": {"side_effects": {"local_writes": [{"path": str(target)}]}}}
    before = capture_side_effects_snapshot(manifest, skill_dir=tmp_path)
    after = capture_side_effects_snapshot(manifest, skill_dir=tmp_path)
    findings = diff_side_effects(before, after)
    assert findings[0]["change"] == "unchanged"


def test_templated_path_marked_untracked(tmp_path):
    manifest = {
        "runtime": {
            "side_effects": {"local_writes": [{"path": "<input-parent>/<input-name>.nii.gz"}]}
        }
    }
    before = capture_side_effects_snapshot(manifest, skill_dir=tmp_path)
    after = capture_side_effects_snapshot(manifest, skill_dir=tmp_path)
    findings = diff_side_effects(before, after)
    assert findings[0]["change"] == "untracked"


def test_full_run_writes_provenance(tmp_path):
    fixture = tmp_path / "fixture.txt"
    fixture.write_text("x")
    skill = tmp_path / "toy_skill"
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Toy\n")
    (skill / "skill_manifest.yaml").write_text(
        "\n".join(
            [
                "id: test.toy_prov",
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
        )
        + "\n"
    )
    (skill / "scripts" / "run.py").write_text(
        "import json\nprint(json.dumps({'output': {'ok': True}}))\n"
    )

    out = tmp_path / "pack"
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "eval_engine" / "run.py"),
            str(skill),
            "--fixture",
            str(fixture),
            "--out",
            str(out),
        ],
        cwd=REPO_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    prov_path = out / "provenance.json"
    assert prov_path.exists()
    payload = json.loads(prov_path.read_text())
    assert "gpu" in payload
    assert "side_effects" in payload
    assert payload["side_effects"]["findings"] == []  # no declared paths in this skill
