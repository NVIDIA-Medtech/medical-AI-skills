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

import json
from pathlib import Path

from eval_engine import reproducibility


def _write_skill(tmp_path: Path, *, nondeterministic_artifact: bool = False) -> Path:
    skill = tmp_path / "toy_skill"
    scripts = skill / "scripts"
    scripts.mkdir(parents=True)
    (skill / "fixtures").mkdir()
    (skill / "validators").mkdir()
    (skill / "SKILL.md").write_text("# Toy Skill\n")
    (skill / "fixtures" / "input.txt").write_text("fixture\n")
    artifact_expr = (
        "__import__('time').time_ns()" if nondeterministic_artifact else "'stable artifact'"
    )
    (scripts / "run.py").write_text(
        "import argparse, json\n"
        "from pathlib import Path\n"
        "parser = argparse.ArgumentParser()\n"
        "parser.add_argument('fixture')\n"
        "parser.add_argument('--output-dir', required=True)\n"
        "args = parser.parse_args()\n"
        "out = Path(args.output_dir)\n"
        "out.mkdir(parents=True, exist_ok=True)\n"
        "artifact = out / 'artifact.txt'\n"
        f"artifact.write_text(str({artifact_expr}))\n"
        "print(json.dumps({'status': 'ok', 'artifact_path': str(artifact)}))\n"
    )
    (skill / "validators" / "output_schema.json").write_text(
        json.dumps(
            {
                "type": "object",
                "required": ["status", "artifact_path"],
                "properties": {
                    "status": {"type": "string"},
                    "artifact_path": {"type": "string"},
                },
            }
        )
    )
    (skill / "skill_manifest.yaml").write_text(
        "\n".join(
            [
                "id: test.toy",
                "version: 0.1.0",
                "license: Apache-2.0",
                "intended_use: {summary: Test fixture.}",
                "upstream_refs:",
                "  - kind: pypi_package",
                "    name: demo",
                "    version_constraint: '>=1'",
                "inputs:",
                "  - name: fixture",
                "    type: file_path",
                "outputs:",
                "  - name: result_json",
                "    type: json",
                "    schema: validators/output_schema.json",
                "runtime:",
                "  language: python",
                "  entrypoint: scripts/run.py",
                "  args:",
                "    - ${python}",
                "    - ${script}",
                "    - ${fixture}",
                "    - --output-dir",
                "    - ${out}",
                "  side_effects:",
                "    pip_packages: []",
                "    local_writes: []",
                "    home_writes: []",
                "    network_endpoints: []",
                "    requires_docker: false",
                "    requires_gpu: none",
                "    env_required: []",
                "validation:",
                "  sanity_checks:",
                "    - {path: status, eq: ok}",
                "  reproducibility:",
                "    mode: repeat",
                "    fixture: fixtures/input.txt",
                "    runs: 2",
                "",
            ]
        )
    )
    return skill


def test_audit_one_passes_stable_repeat_and_hashes_artifact(tmp_path: Path) -> None:
    skill = _write_skill(tmp_path)

    row = reproducibility.audit_one(skill, tmp_path / "audit")

    assert row["status"] == "pass", row
    assert row["artifact_hashes_checked"] == 1
    assert row["payload_diff_count"] == 0
    assert row["artifact_diff_count"] == 0


def test_audit_one_fails_on_artifact_hash_drift(tmp_path: Path) -> None:
    skill = _write_skill(tmp_path, nondeterministic_artifact=True)

    row = reproducibility.audit_one(skill, tmp_path / "audit")

    assert row["status"] == "fail"
    assert row["artifact_diff_count"] == 1
    assert any("artifact hash drift" in issue for issue in row["issues"])


def test_audit_one_requires_reproducibility_declaration(tmp_path: Path) -> None:
    skill = _write_skill(tmp_path)
    text = (skill / "skill_manifest.yaml").read_text()
    text = text.split("  reproducibility:", 1)[0]
    (skill / "skill_manifest.yaml").write_text(text)

    row = reproducibility.audit_one(skill, tmp_path / "audit")

    assert row["status"] == "fail"
    assert row["issues"] == ["validation.reproducibility missing"]
