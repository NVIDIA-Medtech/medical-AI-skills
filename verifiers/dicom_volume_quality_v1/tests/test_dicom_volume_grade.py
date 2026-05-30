"""Tests for dicom_volume_quality_v1."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FIXTURE_GENERATOR = (
    REPO / "skills" / "dicom-series-to-volume" / "fixtures" / "generate_fixtures.py"
)
VERIFIER = REPO / "verifiers" / "dicom_volume_quality_v1" / "scripts" / "grade.py"
SHAPE_MISMATCH_PACK = REPO / "verifiers" / "dicom_volume_quality_v1" / "fixtures" / "shape_mismatch_pack"


def _clean_axial_fixture(tmp_path: Path) -> Path:
    spec = importlib.util.spec_from_file_location("dicom_fixture_generator", FIXTURE_GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fixture = tmp_path / "clean_axial"
    module.write_series(fixture, iop=[1, 0, 0, 0, 1, 0], series_label="clean")
    return fixture


def _run_skill_pack(fixture: Path, out: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO / "eval_engine" / "run.py"),
            str(REPO / "skills" / "dicom-series-to-volume"),
            "--fixture",
            str(fixture),
            "--out",
            str(out),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_grade_pass_on_clean_pack(tmp_path: Path) -> None:
    fixture = _clean_axial_fixture(tmp_path)
    skill_out = tmp_path / "skill_pack"
    _run_skill_pack(fixture, skill_out)

    proc = subprocess.run(
        [sys.executable, str(VERIFIER), str(skill_out)],
        cwd=REPO,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0
    report = json.loads(proc.stdout)
    assert report["overall"] == "pass"
    assert report["volume_quality"]["n_fail"] == 0
    assert report["volume_quality"]["axcodes"] == ["L", "P", "S"]
    assert report["volume_quality"]["shape"] == [64, 64, 32]


def test_grade_fails_on_shape_mismatch_fixture() -> None:
    proc = subprocess.run(
        [sys.executable, str(VERIFIER), str(SHAPE_MISMATCH_PACK)],
        cwd=REPO,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0
    report = json.loads(proc.stdout)
    assert report["overall"] == "fail"
    failing_checks = [check["name"] for check in report["checks"] if check["status"] == "fail"]
    assert "shape_matches_nifti" in failing_checks
    assert "n_slices_matches_shape" in failing_checks
