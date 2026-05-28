import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL = REPO_ROOT / "verifiers" / "endoscopy_tool_detection_quality_v1"
SCRIPT = SKILL / "scripts" / "grade.py"
RUNNER = REPO_ROOT / "eval_engine" / "run.py"


def _run_script(fixture: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(fixture)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def test_pass_pack_has_detection_metrics() -> None:
    payload = _run_script(SKILL / "fixtures" / "pass_pack")

    assert payload["overall"] == "pass"
    assert payload["domain_floor"]["verdict"] == "pass"
    assert payload["detection_metrics"]["verdict"] == "pass"
    assert payload["detection_metrics"]["tools_detected_count"] == 4
    assert payload["detection_metrics"]["frame_coverage"] == 1.0
    assert payload["detection_metrics"]["bbox_sanity"] == {"checked": 4, "invalid": 0}
    assert payload["detection_metrics"]["tool_class_distribution"] == {
        "grasper": 3,
        "scissors": 1,
    }


def test_pack_without_decoded_detections_fails() -> None:
    payload = _run_script(SKILL / "fixtures" / "no_detections_pack")

    assert payload["overall"] == "fail"
    assert payload["domain_floor"]["verdict"] == "fail"
    assert payload["detection_metrics"]["verdict"] == "skipped"
    checks = {c["name"]: c for c in payload["domain_floor"]["checks"]}
    assert checks["decoded_detection_artifact_present"]["status"] == "fail"


def test_repo_placeholder_artifacts_with_hash_mismatch_are_not_usable(tmp_path: Path) -> None:
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "manifest.json").write_text(json.dumps({
        "skill_id": "holohub_endoscopy_tool_tracking",
    }))
    (pack / "validation_summary.json").write_text(json.dumps({
        "overall_status": "passed",
    }))
    recordings = "<repo>/verifiers/endoscopy_tool_detection_quality_v1/fixtures/pass_pack/recordings"
    zero_hash = "0" * 64
    (pack / "output.json").write_text(json.dumps({
        "invocation": {
            "record_type": "visualizer",
            "recording_output_dir": recordings,
        },
        "output": {
            "gxf": {
                "files": [
                    {"path": "clip.gxf_index", "bytes": 14, "sha256": zero_hash},
                    {"path": "clip.gxf_entities", "bytes": 17, "sha256": zero_hash},
                ],
            },
            "video": {"files": []},
            "other": {
                "files": [
                    {"path": "tool_detections.jsonl", "bytes": 434, "sha256": zero_hash},
                ],
            },
        },
    }))

    payload = _run_script(pack)

    assert payload["overall"] == "fail"
    assert payload["artifact_inventory"]["recording_file_count"] == 3
    assert payload["artifact_inventory"]["usable_recording_file_count"] == 0
    assert payload["artifact_inventory"]["hash_mismatch_count"] == 3
    checks = {c["name"]: c for c in payload["domain_floor"]["checks"]}
    assert checks["declared_artifact_hashes_match"]["status"] == "fail"
    assert checks["recording_artifact_present"]["status"] == "fail"


def test_eval_engine_run_validates_pass_pack(tmp_path: Path) -> None:
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
    assert validation["sanity_status"] == "passed"
