import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
VERIFIER = REPO_ROOT / "verifiers" / "radiology_note_summary_quality_v1"
SCRIPT = VERIFIER / "scripts" / "grade.py"
RUNNER = REPO_ROOT / "eval_engine" / "run.py"


def _run_script(fixture: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(fixture)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def test_pass_pack_passes_fact_and_prompt_checks() -> None:
    payload = _run_script(VERIFIER / "fixtures" / "pass_pack")

    assert payload["overall"] == "pass"
    assert payload["target"]["skill_id"] == "radiology_note_summarizer"
    assert payload["summary_quality"]["acceptable"] is True
    assert payload["summary_quality"]["mock_mode"] is True
    assert payload["summary_quality"]["forbidden_finding_count"] == 0
    checks = {item["name"]: item for item in payload["checks"]}
    assert checks["study_uid_echoed"]["status"] == "pass"
    assert checks["modality_echoed_in_prose"]["status"] == "pass"
    assert checks["body_part_echoed_in_prose"]["status"] == "pass"
    assert checks["prompt_template_hash_matches"]["status"] == "pass"
    assert checks["system_prompt_hash_matches"]["status"] == "pass"


def test_forbidden_phrase_pack_fails() -> None:
    payload = _run_script(VERIFIER / "fixtures" / "forbidden_phrase_pack")

    assert payload["overall"] == "fail"
    assert payload["summary_quality"]["acceptable"] is False
    assert payload["summary_quality"]["forbidden_finding_count"] >= 1
    checks = {item["name"]: item for item in payload["checks"]}
    assert checks["forbidden_phrases_absent"]["status"] == "fail"


def test_eval_engine_run_validates_pass_pack(tmp_path: Path) -> None:
    out = tmp_path / "verifier_pack"
    proc = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            str(VERIFIER),
            "--fixture",
            str(VERIFIER / "fixtures" / "pass_pack"),
            "--out",
            str(out),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    validation = json.loads((out / "validation_summary.json").read_text())
    assert validation["overall_status"] == "passed"
    assert validation["sanity_status"] == "passed"
