#!/usr/bin/env python3
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

"""Inventory agent_run_trace.jsonl field shapes across evidence packs."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
TRACE_NAME = "agent_run_trace.jsonl"
DEFAULT_ROOTS = (Path("examples"),)
MAX_EXAMPLES_PER_SHAPE = 3

CANDIDATE_FIELDS: dict[str, tuple[str, ...]] = {
    "event_type": ("event_type", "kind", "type"),
    "timestamp": ("timestamp", "ts"),
    "actor": ("actor",),
    "tool": ("tool",),
    "command": ("command",),
    "cwd": ("cwd",),
    "inputs": ("inputs", "args"),
    "outputs": ("outputs",),
    "status": ("status", "exit_code"),
    "duration_seconds": ("duration_seconds", "elapsed_s", "elapsed_seconds"),
    "files_read": ("files_read",),
    "files_written": ("files_written",),
    "approval_required": ("approval_required",),
    "approval_result": ("approval_result",),
    "model": ("model", "model_name"),
    "prompt_ref": ("prompt_ref",),
    "notes": ("notes",),
}


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    return value


def _iter_trace_files(roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        root_path = root if root.is_absolute() else REPO_ROOT / root
        if root_path.is_file() and root_path.name == TRACE_NAME:
            files.append(root_path)
            continue
        if root_path.is_dir():
            files.extend(root_path.rglob(TRACE_NAME))
    return sorted(set(files))


def _read_trace(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except Exception as exc:
            errors.append(
                {
                    "path": _repo_relative(path),
                    "line": line_number,
                    "error": str(exc),
                }
            )
            continue
        if not isinstance(payload, dict):
            errors.append(
                {
                    "path": _repo_relative(path),
                    "line": line_number,
                    "error": "record is not a JSON object",
                }
            )
            continue
        records.append(payload)
    return records, errors


def _event_value(record: dict[str, Any]) -> str:
    for key in CANDIDATE_FIELDS["event_type"]:
        if key in record:
            return str(record[key])
    return "<missing>"


def inventory_trace_shapes(roots: list[Path] | None = None) -> dict[str, Any]:
    scan_roots = roots or list(DEFAULT_ROOTS)
    trace_files = _iter_trace_files(scan_roots)
    field_counts: Counter[str] = Counter()
    event_counts: Counter[str] = Counter()
    shape_counts: Counter[tuple[str, ...]] = Counter()
    shape_examples: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    candidate_alias_counts: dict[str, Counter[str]] = {
        field: Counter() for field in CANDIDATE_FIELDS
    }
    candidate_present_counts: Counter[str] = Counter()
    parse_errors: list[dict[str, Any]] = []
    records_by_file: dict[str, int] = {}
    total_records = 0

    for path in trace_files:
        records, errors = _read_trace(path)
        rel = _repo_relative(path)
        records_by_file[rel] = len(records)
        parse_errors.extend(errors)
        for line_index, record in enumerate(records, start=1):
            total_records += 1
            fields = tuple(sorted(record))
            shape_counts[fields] += 1
            if len(shape_examples[fields]) < MAX_EXAMPLES_PER_SHAPE:
                shape_examples[fields].append(
                    {
                        "path": rel,
                        "line": line_index,
                        "record": record,
                    }
                )
            field_counts.update(record.keys())
            event_counts[_event_value(record)] += 1
            for stable_field, aliases in CANDIDATE_FIELDS.items():
                matched = [alias for alias in aliases if alias in record]
                if matched:
                    candidate_present_counts[stable_field] += 1
                    candidate_alias_counts[stable_field].update(matched)

    candidate_fields = []
    for stable_field, aliases in CANDIDATE_FIELDS.items():
        observed = candidate_present_counts[stable_field]
        candidate_fields.append(
            {
                "field": stable_field,
                "aliases": list(aliases),
                "observed_records": observed,
                "missing_records": total_records - observed,
                "alias_counts": dict(sorted(candidate_alias_counts[stable_field].items())),
            }
        )

    shapes = []
    for fields, count in shape_counts.most_common():
        shapes.append(
            {
                "fields": list(fields),
                "record_count": count,
                "examples": shape_examples[fields],
            }
        )

    return _json_safe(
        {
            "trace_inventory_version": "0.1.0",
            "roots": [
                _repo_relative((root if root.is_absolute() else REPO_ROOT / root))
                for root in scan_roots
            ],
            "files_scanned": len(trace_files),
            "records_scanned": total_records,
            "parse_errors": parse_errors,
            "records_by_file": records_by_file,
            "observed_fields": dict(field_counts.most_common()),
            "event_counts": dict(event_counts.most_common()),
            "record_shapes": shapes,
            "candidate_stable_fields": candidate_fields,
            "notes": [
                "This report inventories existing records only; it does not validate or migrate packs.",
                "Use observed aliases to design a future compatibility schema for agent_run_trace.jsonl.",
            ],
        }
    )


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Agent Trace Shape Inventory")
    lines.append("")
    lines.append(f"- Files scanned: `{report['files_scanned']}`")
    lines.append(f"- Records scanned: `{report['records_scanned']}`")
    lines.append(f"- Parse errors: `{len(report['parse_errors'])}`")
    lines.append("- Roots: " + ", ".join(f"`{root}`" for root in report["roots"]))
    lines.append("")

    lines.append("## Observed Events")
    lines.append("| Event | Records |")
    lines.append("|---|---:|")
    for event, count in report["event_counts"].items():
        lines.append(f"| `{event}` | {count} |")
    if not report["event_counts"]:
        lines.append("| _none_ | 0 |")
    lines.append("")

    lines.append("## Observed Fields")
    lines.append("| Field | Records |")
    lines.append("|---|---:|")
    for field, count in report["observed_fields"].items():
        lines.append(f"| `{field}` | {count} |")
    if not report["observed_fields"]:
        lines.append("| _none_ | 0 |")
    lines.append("")

    lines.append("## Candidate Stable Fields")
    lines.append("| Stable field | Observed | Missing | Aliases observed |")
    lines.append("|---|---:|---:|---|")
    for item in report["candidate_stable_fields"]:
        aliases = item["alias_counts"]
        aliases_text = ", ".join(f"`{name}`={count}" for name, count in aliases.items()) or "-"
        lines.append(
            f"| `{item['field']}` | {item['observed_records']} | "
            f"{item['missing_records']} | {aliases_text} |"
        )
    lines.append("")

    lines.append("## Record Shapes")
    lines.append("| Records | Fields | Example |")
    lines.append("|---:|---|---|")
    for shape in report["record_shapes"]:
        example = shape["examples"][0] if shape["examples"] else {}
        example_path = example.get("path", "-")
        example_line = example.get("line", "-")
        fields = ", ".join(f"`{field}`" for field in shape["fields"])
        lines.append(f"| {shape['record_count']} | {fields} | `{example_path}:{example_line}` |")
    if not report["record_shapes"]:
        lines.append("| 0 | _none_ | - |")
    lines.append("")

    if report["parse_errors"]:
        lines.append("## Parse Errors")
        for error in report["parse_errors"]:
            lines.append(f"- `{error['path']}:{error['line']}`: {error['error']}")
        lines.append("")

    lines.append("## Compatibility Notes")
    for note in report["notes"]:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "roots",
        nargs="*",
        type=Path,
        help="Directories or trace files to scan. Defaults to examples/.",
    )
    parser.add_argument("--out", type=Path, help="Write JSON report to this path.")
    parser.add_argument("--markdown-out", type=Path, help="Write Markdown report to this path.")
    parser.add_argument(
        "--format", choices=("json", "markdown"), default="json", help="Stdout format."
    )
    return parser.parse_args(argv)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    roots = args.roots or list(DEFAULT_ROOTS)
    report = inventory_trace_shapes(roots)
    json_text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    markdown_text = render_markdown(report)

    if args.out:
        _write(args.out, json_text)
    if args.markdown_out:
        _write(args.markdown_out, markdown_text)

    if args.format == "markdown":
        print(markdown_text)
    else:
        print(json_text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
