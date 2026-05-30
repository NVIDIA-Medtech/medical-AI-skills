"""Tests for eval_engine.skill_runtime.render_runtime_args."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from eval_engine.skill_runtime import RuntimeArgsError, render_runtime_args

REPO_ROOT = Path(__file__).resolve().parents[2]


def _ctx(tmp_path):
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    script = skill_dir / "scripts" / "run.py"
    script.parent.mkdir()
    script.write_text("print('hi')")
    fixture = tmp_path / "fixture.bin"
    fixture.write_bytes(b"data")
    out = tmp_path / "out"
    out.mkdir()
    return skill_dir, script, fixture, out


def test_default_when_args_missing(tmp_path):
    skill_dir, script, fixture, out = _ctx(tmp_path)
    cmd = render_runtime_args(
        manifest={"runtime": {}},
        script=script,
        fixture=fixture,
        out=out,
        skill_dir=skill_dir,
        python_executable="/usr/bin/python3",
    )
    assert cmd == ["/usr/bin/python3", str(script), str(fixture)]


def test_explicit_default_args(tmp_path):
    skill_dir, script, fixture, out = _ctx(tmp_path)
    cmd = render_runtime_args(
        manifest={"runtime": {"args": ["${python}", "${script}", "${fixture}"]}},
        script=script,
        fixture=fixture,
        out=out,
        skill_dir=skill_dir,
        python_executable="/usr/bin/python3",
    )
    assert cmd == ["/usr/bin/python3", str(script), str(fixture)]


def test_out_token(tmp_path):
    skill_dir, script, fixture, out = _ctx(tmp_path)
    cmd = render_runtime_args(
        manifest={"runtime": {"args": ["${python}", "${script}", "${fixture}", "--output", "${out}/result.nii.gz"]}},
        script=script,
        fixture=fixture,
        out=out,
        skill_dir=skill_dir,
        python_executable="/usr/bin/python3",
    )
    assert cmd[-2:] == ["--output", f"{out}/result.nii.gz"]


def test_env_token_resolves(tmp_path):
    skill_dir, script, fixture, out = _ctx(tmp_path)
    cmd = render_runtime_args(
        manifest={"runtime": {"args": ["${python}", "${script}", "--token", "${env.FAKE_TOKEN}"]}},
        script=script,
        fixture=fixture,
        out=out,
        skill_dir=skill_dir,
        python_executable="/usr/bin/python3",
        env={"FAKE_TOKEN": "sk-xyz"},
    )
    assert cmd[-2:] == ["--token", "sk-xyz"]


def test_env_token_redacts_for_pack_metadata(tmp_path):
    skill_dir, script, fixture, out = _ctx(tmp_path)
    cmd = render_runtime_args(
        manifest={"runtime": {"args": ["${python}", "${script}", "--token", "${env.FAKE_TOKEN}"]}},
        script=script,
        fixture=fixture,
        out=out,
        skill_dir=skill_dir,
        python_executable="/usr/bin/python3",
        env={"FAKE_TOKEN": "sk-xyz"},
        redact_env=True,
    )
    assert "sk-xyz" not in cmd
    assert cmd[-2:] == ["--token", "${FAKE_TOKEN:?FAKE_TOKEN is required for replay}"]


def test_env_token_missing_raises(tmp_path):
    skill_dir, script, fixture, out = _ctx(tmp_path)
    with pytest.raises(RuntimeArgsError, match="env var MISSING is not set"):
        render_runtime_args(
            manifest={"runtime": {"args": ["${python}", "${env.MISSING}"]}},
            script=script,
            fixture=fixture,
            out=out,
            skill_dir=skill_dir,
            python_executable="/usr/bin/python3",
            env={},
        )


def test_unknown_token_raises(tmp_path):
    skill_dir, script, fixture, out = _ctx(tmp_path)
    with pytest.raises(RuntimeArgsError, match=r"unknown token: \$\{nope\}"):
        render_runtime_args(
            manifest={"runtime": {"args": ["${nope}"]}},
            script=script,
            fixture=fixture,
            out=out,
            skill_dir=skill_dir,
            python_executable="/usr/bin/python3",
        )


def test_skill_dir_token(tmp_path):
    skill_dir, script, fixture, out = _ctx(tmp_path)
    cmd = render_runtime_args(
        manifest={"runtime": {"args": ["bash", "${skill_dir}/run.sh"]}},
        script=script,
        fixture=fixture,
        out=out,
        skill_dir=skill_dir,
        python_executable="/usr/bin/python3",
    )
    assert cmd == ["bash", f"{skill_dir}/run.sh"]


def test_env_token_not_written_to_pack_metadata_or_replay(tmp_path):
    fixture = tmp_path / "fixture.txt"
    fixture.write_text("x")
    skill = tmp_path / "toy_secret_skill"
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Toy\n")
    (skill / "skill_manifest.yaml").write_text("\n".join([
        "id: test.toy_secret_args",
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
        "  args:",
        "    - \"${python}\"",
        "    - \"${script}\"",
        "    - \"${fixture}\"",
        "    - \"--token\"",
        "    - \"${env.FAKE_TOKEN}\"",
    ]) + "\n")
    (skill / "scripts" / "run.py").write_text(
        "import argparse, json\n"
        "p = argparse.ArgumentParser()\n"
        "p.add_argument('fixture')\n"
        "p.add_argument('--token', required=True)\n"
        "p.parse_args()\n"
        "print(json.dumps({'output': {'ok': True}}))\n"
    )

    out = tmp_path / "pack"
    env = os.environ.copy()
    env["FAKE_TOKEN"] = "sk-secret-value"
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "eval_engine" / "run.py"), str(skill),
         "--fixture", str(fixture), "--out", str(out)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

    manifest = json.loads((out / "manifest.json").read_text())
    replay = (out / "replay.sh").read_text()
    assert "sk-secret-value" not in json.dumps(manifest)
    assert "sk-secret-value" not in replay
    assert "${FAKE_TOKEN:?FAKE_TOKEN is required for replay}" in replay
