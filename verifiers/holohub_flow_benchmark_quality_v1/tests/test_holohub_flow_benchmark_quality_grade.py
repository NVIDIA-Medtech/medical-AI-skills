import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
VERIFIER = REPO_ROOT / "verifiers" / "holohub_flow_benchmark_quality_v1"
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


def test_pass_pack_passes_artifact_scheduler_and_contract_checks() -> None:
    payload = _run_script(VERIFIER / "fixtures" / "pass_pack")

    assert payload["overall"] == "pass"
    assert payload["target"]["skill_id"] == "medagent.holohub_flow_benchmark"
    assert payload["flow_quality"]["acceptable"] is True
    assert payload["flow_quality"]["logger_file_count"] >= 1
    assert payload["flow_quality"]["scheduler_coverage_complete"] is True
    assert payload["flow_quality"]["total_latency_samples"] > 0
    assert payload["flow_quality"]["contract_assertions_passed"] is True
    checks = {item["name"]: item for item in payload["checks"]}
    assert checks["logger_artifacts_hash_match"]["status"] == "pass"
    assert checks["latency_samples_present"]["status"] == "pass"
    assert checks["benchmark_log_completed"]["status"] == "pass"


def test_no_latency_pack_fails_latency_and_contract_checks() -> None:
    payload = _run_script(VERIFIER / "fixtures" / "no_latency_pack")

    assert payload["overall"] == "fail"
    assert payload["flow_quality"]["acceptable"] is False
    assert payload["flow_quality"]["total_latency_samples"] == 0
    checks = {item["name"]: item for item in payload["checks"]}
    assert checks["latency_samples_present"]["status"] == "fail"
    assert checks["contract_assertions_passed"]["status"] == "fail"


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
