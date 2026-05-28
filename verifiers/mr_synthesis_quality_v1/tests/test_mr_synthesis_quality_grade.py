import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
VERIFIER = REPO_ROOT / "verifiers" / "mr_synthesis_quality_v1"
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


def test_pass_pack_passes_image_identity_and_scope_checks() -> None:
    payload = _run_script(VERIFIER / "fixtures" / "pass_pack")

    assert payload["overall"] == "pass"
    assert payload["target"]["skill_id"] == "medagent.nv_generate_mr"
    assert payload["mr_quality"]["acceptable"] is True
    assert payload["mr_quality"]["output_skill"] == "nv_generate_mr"
    assert payload["mr_quality"]["all_images_nonconstant"] is True
    checks = {item["name"]: item for item in payload["checks"]}
    assert checks["official_entrypoint_matches"]["status"] == "pass"
    assert checks["image_artifacts_readable"]["status"] == "pass"
    assert checks["aggregate_flags_match_recomputed"]["status"] == "pass"
    assert checks["scope_disclosed"]["status"] == "pass"


def test_brain_pass_pack_is_supported() -> None:
    payload = _run_script(VERIFIER / "fixtures" / "brain_pass_pack")

    assert payload["overall"] == "pass"
    assert payload["target"]["skill_id"] == "medagent.nv_generate_mr_brain"
    assert payload["mr_quality"]["output_skill"] == "nv_generate_mr_brain"
    assert payload["mr_quality"]["version"] == "rflow-mr-brain"


def test_constant_image_pack_fails_recomputed_signal_checks() -> None:
    payload = _run_script(VERIFIER / "fixtures" / "constant_image_pack")

    assert payload["overall"] == "fail"
    assert payload["mr_quality"]["acceptable"] is False
    assert payload["mr_quality"]["all_images_nonconstant"] is False
    checks = {item["name"]: item for item in payload["checks"]}
    assert checks["image_values_nonconstant"]["status"] == "fail"
    assert checks["aggregate_flags_match_recomputed"]["status"] == "fail"


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


def test_eval_engine_run_validates_brain_pass_pack(tmp_path: Path) -> None:
    out = tmp_path / "brain_verifier_pack"
    proc = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            str(VERIFIER),
            "--fixture",
            str(VERIFIER / "fixtures" / "brain_pass_pack"),
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
