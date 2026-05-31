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
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER = REPO_ROOT / "eval_engine" / "run.py"


def _write_skill(tmp_path, *, script_body: str, manifest_extra: str = "") -> Path:
    skill = tmp_path / "toy_skill"
    scripts = skill / "scripts"
    scripts.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Toy Skill\n")
    (skill / "skill_manifest.yaml").write_text(
        "\n".join(
            [
                "id: test.toy",
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
                manifest_extra,
            ]
        )
    )
    (scripts / "run.py").write_text(script_body)
    return skill


def _run_skill(
    skill: Path, fixture: Path, out: Path, *, env: dict | None = None
) -> subprocess.CompletedProcess:
    proc_env = os.environ.copy()
    if env:
        proc_env.update(env)
    return subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            str(skill),
            "--fixture",
            str(fixture),
            "--out",
            str(out),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        env=proc_env,
    )


def _read_trace(out: Path) -> list[dict]:
    return [json.loads(line) for line in (out / "agent_run_trace.jsonl").read_text().splitlines()]


def test_run_py_writes_successful_evidence_pack(tmp_path):
    fixture = tmp_path / "fixture.txt"
    fixture.write_text("hello\n")
    skill = _write_skill(
        tmp_path,
        script_body=(
            "import json, sys\n"
            "print(json.dumps({'output': {'ok': True, 'fixture': sys.argv[1]}}))\n"
        ),
        manifest_extra=("validation:\n" "  sanity_checks:\n" "    - {path: output.ok, eq: true}"),
    )
    out = tmp_path / "pack"

    proc = _run_skill(skill, fixture, out)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    validation = json.loads((out / "validation_summary.json").read_text())
    manifest = json.loads((out / "manifest.json").read_text())
    trace = _read_trace(out)
    assert validation["overall_status"] == "passed"
    assert validation["sanity_status"] == "passed"
    assert manifest["command"] == ["python3", str(skill / "scripts" / "run.py"), str(fixture)]
    assert trace[0]["event_type"] == "tool_call_start"
    assert trace[0]["command"] == manifest["command"]
    assert trace[0]["cwd"] == "."
    for name in (
        "agent_run_trace.jsonl",
        "cost_profile.json",
        "environment.lock",
        "integrity_check.json",
        "manifest.json",
        "output.json",
        "replay.sh",
        "runtime_profile.json",
        "validation_summary.json",
        "workflow_run_record.md",
    ):
        assert (out / name).exists()


def test_run_py_passes_declared_default_sentinel_verbatim(tmp_path):
    skill = tmp_path / "sentinel_skill"
    scripts = skill / "scripts"
    scripts.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Sentinel Skill\n")
    (skill / "skill_manifest.yaml").write_text(
        "\n".join(
            [
                "id: test.sentinel",
                "version: 0.1.0",
                "inputs:",
                "  - name: fixture",
                "    type: directory_path",
                "    formats: [default_sentinel]",
                "outputs:",
                "  - name: result_json",
                "    type: json",
                "runtime:",
                "  language: python",
                "  entrypoint: scripts/run.py",
                "validation:",
                "  sanity_checks:",
                "    - {path: output.fixture, eq: default}",
            ]
        )
    )
    (scripts / "run.py").write_text(
        "import json, sys\n" "print(json.dumps({'output': {'fixture': sys.argv[1]}}))\n"
    )
    out = tmp_path / "pack"

    proc = _run_skill(skill, Path("default"), out)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    validation = json.loads((out / "validation_summary.json").read_text())
    manifest = json.loads((out / "manifest.json").read_text())
    assert validation["preflight"][0]["name"] == "fixture_default_sentinel"
    assert validation["overall_status"] == "passed"
    assert manifest["fixture"]["path"] == "default"
    assert manifest["fixture"]["sha256"] == ""
    assert manifest["fixture"]["size_bytes"] == 0
    assert manifest["command"] == ["python3", str(skill / "scripts" / "run.py"), "default"]


def test_declared_sanity_fails_when_output_is_unparseable(tmp_path):
    fixture = tmp_path / "fixture.txt"
    fixture.write_text("hello\n")
    skill = _write_skill(
        tmp_path,
        script_body="print('not json')\n",
        manifest_extra=("validation:\n" "  sanity_checks:\n" "    - {path: output.ok, eq: true}"),
    )
    out = tmp_path / "pack"

    proc = _run_skill(skill, fixture, out)

    assert proc.returncode == 1
    validation = json.loads((out / "validation_summary.json").read_text())
    assert validation["parse_error"]
    assert validation["sanity_status"] == "failed"
    assert validation["sanity_results"] == [
        {
            "check": {"path": "output.ok", "eq": True},
            "actual": None,
            "ok": False,
            "reason": "sanity_checks declared but output JSON was not available",
        }
    ]


def test_env_pin_uses_skill_reported_runtime_packages(tmp_path):
    fixture = tmp_path / "fixture.txt"
    fixture.write_text("hello\n")
    skill = _write_skill(
        tmp_path,
        script_body=(
            "import json\n"
            "print(json.dumps({'environment': {'packages': {'demo_pkg': '1.2.3'}}}))\n"
        ),
        manifest_extra=("validation:\n" "  env_pin:\n" "    demo-pkg: '>=1,<2'"),
    )
    out = tmp_path / "pack"

    proc = _run_skill(skill, fixture, out)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    validation = json.loads((out / "validation_summary.json").read_text())
    assert validation["env_pin_status"] == "passed"
    assert validation["env_pin_results"][0]["source"] == "output.environment.packages"


def test_preflight_replay_redacts_declared_secret_env_vars(tmp_path):
    fixture = tmp_path / "fixture.txt"
    fixture.write_text("hello\n")
    skill = _write_skill(
        tmp_path,
        script_body="print('{}')\n",
        manifest_extra=(
            "runtime:\n"
            "  language: python\n"
            "  entrypoint: scripts/run.py\n"
            "  env_required: [NV_INFER_TOKEN, PLAIN_VAR]\n"
            "inputs:\n"
            "  - name: fixture\n"
            "    type: file_path\n"
            "    max_size_bytes: 1"
        ),
    )
    out = tmp_path / "pack"

    proc = _run_skill(
        skill,
        fixture,
        out,
        env={"NV_INFER_TOKEN": "super-secret-token", "PLAIN_VAR": "plain-value"},
    )

    assert proc.returncode == 2
    replay = (out / "replay.sh").read_text()
    manifest = json.loads((out / "manifest.json").read_text())
    trace = _read_trace(out)
    assert "super-secret-token" not in replay
    assert (
        'export NV_INFER_TOKEN="${NV_INFER_TOKEN:?NV_INFER_TOKEN is required for replay}"' in replay
    )
    assert "export PLAIN_VAR=plain-value" in replay
    assert trace[0]["event_type"] == "preflight_start"
    assert trace[0]["command"] == manifest["command"]
    assert trace[0]["cwd"] == "."


def test_manifest_file_listing_excludes_bundle_directories(tmp_path):
    fixture = tmp_path / "fixture.txt"
    fixture.write_text("hello\n")
    skill = _write_skill(
        tmp_path, script_body="import json\nprint(json.dumps({'output': {'ok': True}}))\n"
    )
    (skill / "bundle").mkdir()
    (skill / "bundle" / "ignored.py").write_text("print('ignore me')\n")
    (skill / "bundles").mkdir()
    (skill / "bundles" / "ignored.py").write_text("print('ignore me too')\n")
    out = tmp_path / "pack"

    proc = _run_skill(skill, fixture, out)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    manifest = json.loads((out / "manifest.json").read_text())
    assert "bundle/ignored.py" not in manifest["skill_dir_files"]
    assert "bundles/ignored.py" not in manifest["skill_dir_files"]
