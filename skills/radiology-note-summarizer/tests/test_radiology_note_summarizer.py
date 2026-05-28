"""Smoke tests for radiology_note_summarizer.

These verify the script's wiring (fixture loading, mock-mode response
shape, missing-key behaviour). They do NOT call the real NIM endpoint.
"""
from __future__ import annotations

import json
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPT = SKILL_DIR / "scripts" / "summarize.py"
FIXTURE = SKILL_DIR / "fixtures" / "case_001_input.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("radiology_note_summarizer_script", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _run(env: dict, fixture: Path = FIXTURE) -> subprocess.CompletedProcess:
    full_env = os.environ.copy()
    full_env.update(env)
    full_env.pop("NV_INFER_TOKEN", None) if "NV_INFER_TOKEN" not in env else None
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(fixture)],
        capture_output=True, text=True, env=full_env, timeout=30,
    )


def test_missing_key_fails_clean():
    env = {k: v for k, v in os.environ.items() if k not in ("NV_INFER_TOKEN", "MOCK_LLM")}
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(FIXTURE)],
        capture_output=True, text=True, env=env, timeout=30,
    )
    assert proc.returncode == 2
    assert "NV_INFER_TOKEN is not set" in proc.stderr


def test_mock_mode_produces_valid_output():
    proc = _run({"MOCK_LLM": "1"})
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert "output" in payload and "runtime" in payload
    assert payload["runtime"]["model"] == "nvidia/openai/gpt-oss-20b"
    assert payload["runtime"]["mock"] is True
    assert payload["output"]["study_instance_uid"]
    assert isinstance(payload["output"]["findings"], list) and payload["output"]["findings"]
    assert isinstance(payload["output"]["impressions"], str) and payload["output"]["impressions"]


def test_live_shape_drift_is_normalized():
    module = _load_module()
    normalized = module._normalize_model_output({
        "study_instance_uid": "1.2.3",
        "findings": "single finding",
        "impressions": ["first", "second"],
        "flags_for_followup": None,
    })
    assert normalized["findings"] == ["single finding"]
    assert normalized["impressions"] == "first second"
    assert normalized["flags_for_followup"] == []


def test_mock_mode_factual_echo():
    """Mock response must echo StudyInstanceUID verbatim and mention CT/ABDOMEN."""
    proc = _run({"MOCK_LLM": "1"})
    payload = json.loads(proc.stdout)
    fixture = json.loads(FIXTURE.read_text())
    assert payload["output"]["study_instance_uid"] == fixture["dicom_metadata"]["StudyInstanceUID"]
    blob = " ".join(payload["output"]["findings"]) + " " + payload["output"]["impressions"]
    assert fixture["dicom_metadata"]["Modality"] in blob.upper() or fixture["dicom_metadata"]["Modality"].lower() in blob.lower()
    assert fixture["dicom_metadata"]["BodyPartExamined"].lower() in blob.lower()


def test_mock_fault_modes_are_available():
    factual = json.loads(_run({"MOCK_LLM": "fail_factual_echo"}).stdout)
    factual_blob = " ".join(factual["output"]["findings"]) + " " + factual["output"]["impressions"]
    assert "CT" not in factual_blob.upper()
    assert "ABDOMEN" not in factual_blob.upper()

    schema = json.loads(_run({"MOCK_LLM": "fail_schema"}).stdout)
    assert "study_instance_uid" not in schema["output"]

    identity = json.loads(_run({"MOCK_LLM": "fail_model_identity"}).stdout)
    assert identity["runtime"]["model"] != "nvidia/openai/gpt-oss-20b"


def test_missing_fixture():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "/no/such/fixture.json"],
        capture_output=True, text=True, env=os.environ.copy(), timeout=30,
    )
    assert proc.returncode == 2
    assert "fixture not found" in proc.stderr
