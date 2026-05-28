"""Sanity-check flagship workflow YAML specs load and declare expected steps."""
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO / "examples" / "workflows"


def _load(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text())


def test_holohub_imaging_workflow_mvp():
    spec = _load("holohub_imaging_evidence.yaml")
    assert spec["workflow_id"] == "holohub_imaging_evidence"
    steps = spec["steps"]
    assert len(steps) == 2
    assert steps[0]["skill"] == "skills/holohub-imaging-ai-segmentator"
    assert steps[0]["trusted"] is True
    assert steps[0]["inputs"]["fixture"] == "${input}"
    assert steps[1]["id"] == "flow_benchmark"
    assert steps[1]["env"]["HOLOHUB_BENCHMARK_APP"] == "imaging_ai_segmentator"


def test_holohub_endoscopy_workflow_trusted():
    spec = _load("holohub_endoscopy_evidence.yaml")
    assert spec["workflow_id"] == "holohub_endoscopy_evidence"
    assert len(spec["steps"]) == 2
    step = spec["steps"][0]
    assert step["trusted"] is True
    assert step["skill"] == "skills/holohub-endoscopy-tool-tracking"
    assert step["env"]["HOLOHUB_EXPORT_TOOL_DETECTIONS"] == "true"
    assert spec["steps"][1]["id"] == "flow_benchmark"
