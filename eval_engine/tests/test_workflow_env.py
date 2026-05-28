"""Workflow runner passes per-step env to eval_engine subprocesses."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]


def test_run_step_merges_step_env(tmp_path: Path) -> None:
    from eval_engine.run_workflow import _run_step

    skill_dir = REPO / "skills" / "dicom-metadata-extract"
    fixture = skill_dir / "fixtures" / "sample_ct.dcm"
    step_out = tmp_path / "step"
    captured: dict = {}

    def fake_run(cmd, capture_output, text, cwd, env):
        captured["env"] = dict(env)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    with patch("eval_engine.run_workflow.subprocess.run", fake_run):
        _run_step(
            skill_dir,
            fixture,
            step_out,
            trusted=False,
            step_env={"CUSTOM_STEP_ENV": "enabled"},
        )

    assert captured["env"]["CUSTOM_STEP_ENV"] == "enabled"
