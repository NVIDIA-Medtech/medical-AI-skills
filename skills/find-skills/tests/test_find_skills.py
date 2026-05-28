from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SCRIPT = SKILL / "scripts" / "find_skills.py"
SCHEMA = SKILL / "validators" / "output_schema.json"
FIXTURE = SKILL / "fixtures" / "example_task.txt"


def test_find_skills_json_shortlist_matches_ct_segmentation() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(FIXTURE)],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    jsonschema.validate(payload, json.loads(SCHEMA.read_text()))
    assert payload["skill"] == "find_skills"
    assert payload["recommendations"][0]["id"] == "medagent.nv_segment_ct"
    assert payload["no_fit"] is False


def test_find_skills_markdown_mode_is_human_readable() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "audit a skill manifest", "--markdown"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 0, proc.stderr
    assert "`medagent.verifiers.skill_completeness_v1`" in proc.stdout
