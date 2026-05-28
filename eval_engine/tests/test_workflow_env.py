"""Workflow runner passes per-step env to eval_engine subprocesses."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import yaml

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
            step_env={"HOLOHUB_BENCHMARK_APP": "imaging_ai_segmentator"},
        )

    assert captured["env"]["HOLOHUB_BENCHMARK_APP"] == "imaging_ai_segmentator"


def test_holohub_imaging_workflow_declares_flow_step() -> None:
    spec = yaml.safe_load(
        (REPO / "examples/workflows/holohub_imaging_evidence.yaml").read_text()
    )
    assert len(spec["steps"]) == 2
    flow = spec["steps"][1]
    assert flow["id"] == "flow_benchmark"
    assert flow["env"]["HOLOHUB_BENCHMARK_APP"] == "imaging_ai_segmentator"
