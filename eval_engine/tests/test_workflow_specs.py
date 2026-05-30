"""Sanity-check flagship workflow YAML specs load and declare expected steps."""
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO / "examples" / "workflows"


def _load(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text())


def test_ct_dicom_to_segmentation_workflow():
    spec = _load("ct_dicom_to_segmentation_evidence.yaml")
    assert spec["workflow_id"] == "ct_dicom_to_segmentation_evidence"
    steps = spec["steps"]
    assert len(steps) == 2
    assert steps[0]["skill"] == "skills/dicom-series-to-volume"
    assert steps[0]["inputs"]["fixture"] == "${input}"
    assert steps[1]["id"] == "segment"
    assert steps[1]["skill"] == "skills/nv-segment-ct"
    assert steps[1]["trusted"] is True
    assert steps[1]["inputs"]["fixture"] == "${convert.output.path}"


def test_dicom_preflight_workflow_trusted():
    spec = _load("dicom_preflight_gate.yaml")
    assert spec["workflow_id"] == "dicom_preflight_gate"
    assert len(spec["steps"]) == 1
    step = spec["steps"][0]
    assert step["skill"] == "skills/dicom-series-preflight"
    assert step["trusted"] is True
    assert step["inputs"]["fixture"] == "${input}"
