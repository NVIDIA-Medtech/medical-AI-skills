"""Tests for tool_detections.jsonl export helper."""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from export_tool_detections import export_tool_detections as export_fn  # noqa: E402


def test_existing_sidecar_is_reused(tmp_path: Path) -> None:
    rec = tmp_path / "rec"
    rec.mkdir()
    sidecar = rec / "tool_detections.jsonl"
    sidecar.write_text('{"frame": 0, "detections": []}\n')
    path, meta = export_fn(rec, "", "", enabled=True)
    assert path == sidecar
    assert meta["method"] == "existing_sidecar"


def test_log_parse_writes_jsonl(tmp_path: Path) -> None:
    rec = tmp_path / "rec"
    rec.mkdir()
    logs = "frame 0 tool Grasper bbox [100, 120, 80, 50]\nframe 1 detected Scissors\n"
    path, meta = export_fn(rec, logs, "", enabled=True)
    assert meta["method"] == "log_parse"
    assert path is not None and path.is_file()
    lines = path.read_text().strip().splitlines()
    assert len(lines) >= 2
    frame0 = json.loads(lines[0])
    assert frame0["detections"][0]["class"] == "Grasper"
