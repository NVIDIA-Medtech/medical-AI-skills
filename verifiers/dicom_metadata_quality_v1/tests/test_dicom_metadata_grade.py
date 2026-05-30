"""Tests for dicom_metadata_quality_v1."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FIXTURE = REPO / "skills" / "dicom-metadata-extract" / "fixtures" / "sample_ct.dcm"
VERIFIER = REPO / "verifiers" / "dicom_metadata_quality_v1" / "scripts" / "grade.py"


def _run_skill_pack(out: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO / "eval_engine" / "run.py"),
            str(REPO / "skills" / "dicom-metadata-extract"),
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


def test_grade_warns_but_accepts_standard_phi_tags(tmp_path: Path) -> None:
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
    assert report["overall"] == "warn"
    assert report["metadata_quality"]["acceptable"] is True
    assert report["metadata_quality"]["n_fail"] == 0
    assert report["metadata_quality"]["n_warn"] == 1
    assert "standard PHI tags present" in report["warnings"][0]


def test_grade_fails_when_scope_disclaimer_is_missing(tmp_path: Path) -> None:
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "manifest.json").write_text('{"skill_id":"medagent.dicom_metadata_extract"}\n')
    (pack / "validation_summary.json").write_text('{"overall_status":"passed"}\n')
    (pack / "output.json").write_text(
        json.dumps(
            {
                "transfer_syntax": {"uid": "1", "name": "Explicit VR Little Endian"},
                "modality": "CT",
                "study": {"StudyInstanceUID": "1.2.3"},
                "image": {"Rows": 64, "Columns": 64},
                "phi_present": False,
                "phi_tags_found": [],
                "phi_scope_disclaimer": "standard tags only",
            }
        )
        + "\n"
    )

    proc = subprocess.run(
        [sys.executable, str(VERIFIER), str(pack)],
        cwd=REPO,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0
    report = json.loads(proc.stdout)
    assert report["overall"] == "fail"
    assert report["metadata_quality"]["acceptable"] is False
    assert "phi_scope_disclosed" in [check["name"] for check in report["checks"] if check["status"] == "fail"]
