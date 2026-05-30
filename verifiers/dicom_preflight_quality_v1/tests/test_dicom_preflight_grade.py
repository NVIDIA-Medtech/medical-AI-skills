"""Tests for dicom_preflight_quality_v1."""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FIXTURES = REPO / "skills" / "dicom-series-preflight" / "fixtures"


def test_grade_pass_on_clean_pack(tmp_path):
    from eval_engine.run import main as run_main  # noqa: F401 — ensure import path

    skill_out = tmp_path / "skill_pack"
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO / "eval_engine" / "run.py"),
            str(REPO / "skills" / "dicom-series-preflight"),
            "--fixture",
            str(FIXTURES / "clean_no_phi"),
            "--out",
            str(skill_out),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout

    grade_proc = subprocess.run(
        [
            sys.executable,
            str(REPO / "verifiers" / "dicom_preflight_quality_v1" / "scripts" / "grade.py"),
            str(skill_out),
        ],
        capture_output=True,
        text=True,
    )
    assert grade_proc.returncode == 0
    report = json.loads(grade_proc.stdout)
    assert report["overall"] == "pass"
    assert report["target"]["evidence_pack"] == str(skill_out.resolve())
