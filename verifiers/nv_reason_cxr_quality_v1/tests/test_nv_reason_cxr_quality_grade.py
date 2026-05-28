import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
VERIFIER = REPO_ROOT / "verifiers" / "nv_reason_cxr_quality_v1"
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


def test_pass_pack_passes_image_runtime_and_guardrail_checks() -> None:
    payload = _run_script(VERIFIER / "fixtures" / "pass_pack")

    assert payload["overall"] == "pass"
    assert payload["target"]["skill_id"] == "medagent.nv_reason_cxr"
    assert payload["cxr_quality"]["acceptable"] is True
    assert payload["cxr_quality"]["mock_mode"] is True
    assert payload["cxr_quality"]["forbidden_finding_count"] == 0
    checks = {item["name"]: item for item in payload["checks"]}
    assert checks["case_id_matches_fixture"]["status"] == "pass"
    assert checks["prompt_matches_fixture"]["status"] == "pass"
    assert checks["image_file_readable"]["status"] == "pass"
    assert checks["image_sha256_matches"]["status"] == "pass"
    assert checks["model_identity_matches"]["status"] == "pass"
    assert checks["mock_flag_consistent"]["status"] == "pass"
    assert checks["limitations_disclose_scope"]["status"] == "pass"


def test_forbidden_phrase_pack_fails() -> None:
    payload = _run_script(VERIFIER / "fixtures" / "forbidden_phrase_pack")

    assert payload["overall"] == "fail"
    assert payload["cxr_quality"]["acceptable"] is False
    assert payload["cxr_quality"]["forbidden_finding_count"] >= 1
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
