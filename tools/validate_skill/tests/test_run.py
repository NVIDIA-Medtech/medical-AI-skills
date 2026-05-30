from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SCENARIO = REPO_ROOT / "skills" / "dicom-metadata-extract" / "evals" / "baseline.yaml"


def _run_validate(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "tools.validate_skill.run", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def test_validate_skill_mock_happy_path_writes_pack(tmp_path: Path) -> None:
    proc = _run_validate(str(SCENARIO), "--out", str(tmp_path))
    assert proc.returncode == 0, proc.stderr
    assert "mock backend" in proc.stdout
    assert proc.stderr == ""

    pack = tmp_path / "extract-modality-and-phi-flag"
    assert (pack / "manifest.json").exists()
    assert (pack / "paired_eval.md").exists()
    assert (pack / "arms" / "with_skill.json").exists()
    assert (pack / "arms" / "without_skill.json").exists()

    with_arm = json.loads((pack / "arms" / "with_skill.json").read_text())
    without_arm = json.loads((pack / "arms" / "without_skill.json").read_text())
    assert with_arm["assertions_passed"] == 7
    assert with_arm["assertions_failed"] == 0
    assert without_arm["assertions_failed"] >= 1

    manifest = json.loads((pack / "manifest.json").read_text())
    assert manifest["pack_kind"] == "paired_eval"


def test_validate_skill_missing_scenario_exits_2(tmp_path: Path) -> None:
    proc = _run_validate(str(tmp_path / "missing.yaml"), "--out", str(tmp_path / "out"))
    assert proc.returncode == 2
    assert "scenario not found" in proc.stderr
    assert proc.stdout == ""


def test_validate_skill_bad_schema_reports_unknown_key(tmp_path: Path) -> None:
    scenario = yaml.safe_load(SCENARIO.read_text())
    scenario["assertios"] = scenario.pop("assertions")
    bad = tmp_path / "bad.yaml"
    bad.write_text(yaml.safe_dump(scenario))

    proc = _run_validate(str(bad), "--out", str(tmp_path / "out"))
    assert proc.returncode == 2
    assert "scenario schema validation failed" in proc.stderr
    assert "assertios" in proc.stderr
    assert proc.stdout == ""


def test_validate_skill_rejects_evidence_pack_manifest(tmp_path: Path) -> None:
    manifest = REPO_ROOT / "examples" / "evidence_packs" / "dicom_metadata_pass" / "manifest.json"
    proc = _run_validate(str(manifest), "--out", str(tmp_path / "out"))
    assert proc.returncode == 2
    assert "this looks like an evidence pack, not a scenario YAML" in proc.stderr
    assert proc.stdout == ""


def test_validate_skill_stdout_stderr_split(tmp_path: Path) -> None:
    ok = _run_validate(str(SCENARIO), "--out", str(tmp_path / "out"))
    assert ok.returncode == 0
    assert "# Paired Eval Report" in ok.stdout
    assert ok.stderr == ""

    err = _run_validate(str(tmp_path / "missing.yaml"), "--out", str(tmp_path / "err"))
    assert err.returncode == 2
    assert err.stdout == ""
    assert "scenario not found" in err.stderr


def test_validate_skill_rejects_unsupported_backend_without_pack(tmp_path: Path) -> None:
    out = tmp_path / "out"
    proc = _run_validate(str(SCENARIO), "--out", str(out), "--backend", "nvidia")
    assert proc.returncode == 2
    assert "live backends are out of scope for v0" in proc.stderr
    assert not (out / "extract-modality-and-phi-flag").exists()


def test_validate_skill_pack_validates(tmp_path: Path) -> None:
    proc = _run_validate(str(SCENARIO), "--out", str(tmp_path))
    assert proc.returncode == 0, proc.stderr
    pack = tmp_path / "extract-modality-and-phi-flag"

    validate = subprocess.run(
        [sys.executable, "-m", "eval_engine.validate_pack", str(pack)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert validate.returncode == 0, validate.stdout + validate.stderr
