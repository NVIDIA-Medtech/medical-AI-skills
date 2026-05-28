"""Tests for holohub_imaging_segmentation_quality_v1."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL = REPO_ROOT / "verifiers" / "holohub_imaging_segmentation_quality_v1"
SCRIPT = SKILL / "scripts" / "grade.py"
RUNNER = REPO_ROOT / "eval_engine" / "run.py"


def _grade(fixture: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(fixture)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def test_pass_pack() -> None:
    payload = _grade(SKILL / "fixtures" / "pass_pack")
    assert payload["overall"] == "pass"
    assert payload["domain_floor"]["verdict"] == "pass"
    assert payload["artifact_inventory"]["seg_signals"]["seg_pixel_max_value"] == 103


def test_empty_segmentation_fails() -> None:
    payload = _grade(SKILL / "fixtures" / "empty_seg_pack")
    assert payload["overall"] == "fail"
    assert payload["domain_floor"]["verdict"] == "fail"
    names = {c["name"] for c in payload["domain_floor"]["checks"] if c["status"] == "fail"}
    assert "seg_pixel_max_gt_zero" in names


def test_eval_engine_run_pass_pack(tmp_path: Path) -> None:
    out = tmp_path / "verifier_pack"
    proc = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            str(SKILL),
            "--fixture",
            str(SKILL / "fixtures" / "pass_pack"),
            "--out",
            str(out),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    validation = json.loads((out / "validation_summary.json").read_text())
    assert validation["overall_status"] == "passed"
