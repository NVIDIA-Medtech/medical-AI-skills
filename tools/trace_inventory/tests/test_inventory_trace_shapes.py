# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import json
from pathlib import Path

from tools.inventory_trace_shapes import inventory_trace_shapes, render_markdown


def _append_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(record) for record in records) + "\n")


def test_inventory_reports_shapes_and_candidate_aliases(tmp_path: Path) -> None:
    trace = tmp_path / "pack" / "agent_run_trace.jsonl"
    _append_jsonl(
        trace,
        [
            {
                "ts": "2026-05-25T00:00:00+00:00",
                "kind": "tool_call_start",
                "tool": "run.py",
                "args": ["x"],
            },
            {
                "ts": "2026-05-25T00:00:01+00:00",
                "kind": "tool_call_end",
                "exit_code": 0,
                "elapsed_s": 1.0,
            },
        ],
    )

    report = inventory_trace_shapes([tmp_path])

    assert report["files_scanned"] == 1
    assert report["records_scanned"] == 2
    assert report["parse_errors"] == []
    assert report["event_counts"] == {"tool_call_start": 1, "tool_call_end": 1}
    assert report["observed_fields"]["kind"] == 2
    candidates = {item["field"]: item for item in report["candidate_stable_fields"]}
    assert candidates["event_type"]["alias_counts"] == {"kind": 2}
    assert candidates["timestamp"]["alias_counts"] == {"ts": 2}
    assert candidates["duration_seconds"]["alias_counts"] == {"elapsed_s": 1}
    assert candidates["command"]["missing_records"] == 2


def test_inventory_records_parse_errors(tmp_path: Path) -> None:
    trace = tmp_path / "agent_run_trace.jsonl"
    trace.write_text('{"kind": "ok"}\nnot-json\n[]\n')

    report = inventory_trace_shapes([trace])

    assert report["files_scanned"] == 1
    assert report["records_scanned"] == 1
    assert len(report["parse_errors"]) == 2
    assert "not a JSON object" in report["parse_errors"][1]["error"]


def test_markdown_includes_candidate_table(tmp_path: Path) -> None:
    trace = tmp_path / "agent_run_trace.jsonl"
    _append_jsonl(trace, [{"timestamp": "now", "event_type": "tool", "model": "mock"}])

    report = inventory_trace_shapes([trace])
    markdown = render_markdown(report)

    assert "# Agent Trace Shape Inventory" in markdown
    assert "## Candidate Stable Fields" in markdown
    assert "`event_type`=1" in markdown
    assert "`model`=1" in markdown
