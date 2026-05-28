"""Tests for find_skills_quality_v1."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FIXTURE = REPO / "skills" / "find-skills" / "fixtures" / "example_task.txt"
VERIFIER = REPO / "verifiers" / "find_skills_quality_v1" / "scripts" / "grade.py"
BAD_PATH_PACK = REPO / "verifiers" / "find_skills_quality_v1" / "fixtures" / "bad_path_pack"


def _run_skill_pack(out: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO / "eval_engine" / "run.py"),
            str(REPO / "skills" / "find-skills"),
            "--fixture",
            str(FIXTURE),
            "--out",
            str(out),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_grade_pass_on_ct_segmentation_fixture(tmp_path: Path) -> None:
    skill_out = tmp_path / "skill_pack"
    _run_skill_pack(skill_out)

    proc = subprocess.run(
        [sys.executable, str(VERIFIER), str(skill_out)],
        cwd=REPO,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0
    report = json.loads(proc.stdout)
    assert report["overall"] == "pass"
    assert report["selector_quality"]["n_fail"] == 0
    assert report["selector_quality"]["top_id"] == "medagent.nv_segment_ct"


def test_grade_fails_when_recommendation_path_is_missing() -> None:
    proc = subprocess.run(
        [sys.executable, str(VERIFIER), str(BAD_PATH_PACK)],
        cwd=REPO,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0
    report = json.loads(proc.stdout)
    assert report["overall"] == "fail"
    failing_checks = [check["name"] for check in report["checks"] if check["status"] == "fail"]
    assert "recommendation_0_manifest_exists" in failing_checks
