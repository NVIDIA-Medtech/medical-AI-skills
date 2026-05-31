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

"""Describe pending NV direct-study external LLM data transfer without API calls."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.with_vs_without import run_nv_model_studies as studies  # noqa: E402

ARMS = ("with", "without")
DIRECT_PROMPT_STYLE = "minimal"
DEFAULT_MAX_CORRECTION_STEPS = studies.DIRECT_MAX_CORRECTION_STEPS
LOCAL_HOME_PATH_RE = re.compile(r"/(?:home|Users)/[^\s\"'`<>)]*")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        home = Path.home()
        try:
            return "<HOME>/" + str(path.relative_to(home))
        except ValueError:
            return str(path)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _mode_plan(mode: str) -> list[tuple[str, str, studies.Backend]]:
    if mode == "prompts":
        return []
    if mode == "codex-opus":
        return [
            ("codex-opus", "codex_opus", studies.BACKENDS["gpt55"]),
            ("codex-opus", "codex_opus", studies.BACKENDS["opus"]),
        ]
    if mode == "nemotron":
        return [("nemotron-correction", "nemotron_correction", studies.BACKENDS["nemotron"])]
    return [
        ("codex-opus", "codex_opus", studies.BACKENDS["gpt55"]),
        ("codex-opus", "codex_opus", studies.BACKENDS["opus"]),
        ("nemotron-correction", "nemotron_correction", studies.BACKENDS["nemotron"]),
    ]


def _study_dir(skill: str, run_mode: str, study_root: Path) -> Path:
    if run_mode == "codex_opus":
        return study_root / f"{skill}_codex_opus"
    return study_root / f"{skill}_nemotron_correction"


def _document_records(paths: tuple[str, ...]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in paths:
        p = REPO_ROOT / path
        if not p.is_file():
            records.append({"path": path, "exists": False, "byte_count": 0, "sha256": None})
            continue
        data = p.read_bytes()
        records.append(
            {
                "path": path,
                "exists": True,
                "byte_count": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return records


def _pending_transfer_summary(entries: list[dict[str, Any]]) -> dict[str, Any]:
    pending = [entry for entry in entries if entry["status"] == "pending"]
    by_endpoint: dict[tuple[str, str], dict[str, Any]] = {}
    by_skill: dict[str, dict[str, Any]] = {}

    total_system_bytes = 0
    total_user_bytes = 0
    total_doc_bytes = 0
    for entry in pending:
        system_bytes = int(entry["system_prompt_bytes"])
        user_bytes = int(entry["user_prompt_bytes"])
        doc_bytes = sum(int(doc.get("byte_count") or 0) for doc in entry["documentation"])
        total_system_bytes += system_bytes
        total_user_bytes += user_bytes
        total_doc_bytes += doc_bytes

        endpoint_key = (entry["endpoint"], entry["model"])
        endpoint_row = by_endpoint.setdefault(
            endpoint_key,
            {
                "endpoint": entry["endpoint"],
                "model": entry["model"],
                "pending_initial_calls": 0,
                "system_prompt_bytes": 0,
                "user_prompt_bytes": 0,
                "total_initial_bytes": 0,
                "embedded_document_bytes": 0,
            },
        )
        endpoint_row["pending_initial_calls"] += 1
        endpoint_row["system_prompt_bytes"] += system_bytes
        endpoint_row["user_prompt_bytes"] += user_bytes
        endpoint_row["total_initial_bytes"] += system_bytes + user_bytes
        endpoint_row["embedded_document_bytes"] += doc_bytes

        skill_row = by_skill.setdefault(
            entry["skill"],
            {
                "skill": entry["skill"],
                "pending_initial_calls": 0,
                "system_prompt_bytes": 0,
                "user_prompt_bytes": 0,
                "total_initial_bytes": 0,
                "embedded_document_bytes": 0,
            },
        )
        skill_row["pending_initial_calls"] += 1
        skill_row["system_prompt_bytes"] += system_bytes
        skill_row["user_prompt_bytes"] += user_bytes
        skill_row["total_initial_bytes"] += system_bytes + user_bytes
        skill_row["embedded_document_bytes"] += doc_bytes

    return {
        "pending_initial_calls": len(pending),
        "system_prompt_bytes": total_system_bytes,
        "user_prompt_bytes": total_user_bytes,
        "total_initial_bytes": total_system_bytes + total_user_bytes,
        "embedded_document_bytes": total_doc_bytes,
        "by_endpoint_model": sorted(
            by_endpoint.values(), key=lambda row: (row["endpoint"], row["model"])
        ),
        "by_skill": sorted(by_skill.values(), key=lambda row: row["skill"]),
    }


def _backend_protocol_summary(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    for entry in entries:
        protocol = entry["backend_protocol"]
        key = (entry["backend"], entry["endpoint"], entry["model"])
        rows.setdefault(
            key,
            {
                "backend": entry["backend"],
                "endpoint": entry["endpoint"],
                "model": entry["model"],
                "protocol_sha256": _sha256_json(protocol),
                "temperature": protocol.get("temperature"),
                "top_p": protocol.get("top_p"),
                "max_tokens": protocol.get("max_tokens"),
                "retry_attempts": protocol.get("retry_attempts"),
                "chat_attempt_timeout_seconds": protocol.get("chat_attempt_timeout_seconds"),
                "urlopen_timeout_seconds": protocol.get("urlopen_timeout_seconds"),
                "extra_body": protocol.get("extra_body") or {},
            },
        )
    return sorted(rows.values(), key=lambda row: (row["endpoint"], row["model"], row["backend"]))


def _prompt_policy_issues(
    *,
    status: str,
    skill: str,
    mode: str,
    backend: str,
    arm: str,
    repeat: int,
    system_prompt: str,
    user_prompt: str,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for prompt_name, prompt_text in (
        ("system", system_prompt),
        ("user", user_prompt),
    ):
        for match_index, match in enumerate(LOCAL_HOME_PATH_RE.finditer(prompt_text), start=1):
            issues.append(
                {
                    "status": status,
                    "skill": skill,
                    "mode": mode,
                    "backend": backend,
                    "arm": arm,
                    "repeat": repeat,
                    "prompt": prompt_name,
                    "issue": "local_absolute_home_path",
                    "match_index": match_index,
                    "match_sha256": _sha256_text(match.group(0)),
                    "detail": (
                        f"{prompt_name} prompt contains a local absolute home path; "
                        "matched text is redacted"
                    ),
                }
            )
    return issues


def transfer_payload_fingerprint(entries: list[dict[str, Any]]) -> str:
    payload_records = []
    for entry in entries:
        payload_records.append(
            {
                "arm": entry["arm"],
                "backend": entry["backend"],
                "backend_protocol": entry["backend_protocol"],
                "documentation": entry["documentation"],
                "endpoint": entry["endpoint"],
                "expected_output_dir": entry["expected_output_dir"],
                "max_correction_steps": entry["max_correction_steps"],
                "model": entry["model"],
                "mode": entry["mode"],
                "prompt_style": entry["prompt_style"],
                "repeat": entry["repeat"],
                "skill": entry["skill"],
                "source_fixture_used_only_for_staging": entry[
                    "source_fixture_used_only_for_staging"
                ],
                "staged_user_input": entry["staged_user_input"],
                "system_prompt_bytes": entry["system_prompt_bytes"],
                "system_prompt_sha256": entry["system_prompt_sha256"],
                "user_prompt_bytes": entry["user_prompt_bytes"],
                "user_prompt_sha256": entry["user_prompt_sha256"],
            }
        )
    payload_records.sort(
        key=lambda item: (
            item["skill"],
            item["mode"],
            item["backend"],
            item["arm"],
            item["repeat"],
        )
    )
    encoded = json.dumps(payload_records, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_manifest(
    *,
    skills: list[str] | None = None,
    mode: str = "all",
    repeats: int = studies.DIRECT_REPEATS,
    max_correction_steps: int = DEFAULT_MAX_CORRECTION_STEPS,
    resume_missing: bool = True,
    study_root: Path = studies.STUDY_ROOT,
    include_prompts: bool = False,
) -> dict[str, Any]:
    selected = skills or sorted(studies.SCENARIOS)
    entries: list[dict[str, Any]] = []
    pending_initial_calls = 0
    reused_repeats = 0

    for skill in selected:
        scenario = studies.SCENARIOS[skill]
        for mode_label, run_mode, backend in _mode_plan(mode):
            study = _study_dir(skill, run_mode, study_root)
            for arm in ARMS:
                docs = scenario.with_doc if arm == "with" else scenario.without_doc
                doc_records = _document_records(docs)
                for repeat in range(1, repeats + 1):
                    repeat_path = studies._repeat_artifact_path(
                        study, run_mode, backend, arm, repeat
                    )
                    existing = None
                    if resume_missing:
                        existing = studies._load_existing_repeat(
                            repeat_path,
                            skill=skill,
                            mode=run_mode,
                            backend=backend,
                            arm=arm,
                            repeat=repeat,
                            prompt_style=DIRECT_PROMPT_STYLE,
                            max_steps=max_correction_steps,
                        )
                    out_dir = studies._repeat_out_dir(skill, run_mode, backend, arm, repeat)
                    user_prompt = studies._prompt(scenario, arm, out_dir, DIRECT_PROMPT_STYLE)
                    status = "reused" if existing is not None else "pending"
                    if status == "pending":
                        pending_initial_calls += 1
                    else:
                        reused_repeats += 1
                    prompt_policy_issues = _prompt_policy_issues(
                        status=status,
                        skill=skill,
                        mode=mode_label,
                        backend=backend.key,
                        arm=arm,
                        repeat=repeat,
                        system_prompt=studies.DIRECT_SYSTEM_PROMPT,
                        user_prompt=user_prompt,
                    )
                    entry: dict[str, Any] = {
                        "status": status,
                        "skill": skill,
                        "mode": mode_label,
                        "backend": backend.key,
                        "backend_label": backend.label,
                        "backend_protocol": studies._backend_protocol(backend),
                        "endpoint": backend.base_url,
                        "model": backend.model,
                        "arm": arm,
                        "repeat": repeat,
                        "prompt_style": DIRECT_PROMPT_STYLE,
                        "max_correction_steps": max_correction_steps,
                        "system_prompt_sha256": _sha256_text(studies.DIRECT_SYSTEM_PROMPT),
                        "system_prompt_bytes": len(studies.DIRECT_SYSTEM_PROMPT.encode()),
                        "user_prompt_sha256": _sha256_text(user_prompt),
                        "user_prompt_bytes": len(user_prompt.encode()),
                        "documentation": doc_records,
                        "staged_user_input": str(
                            studies._staged_input_path(scenario).relative_to(REPO_ROOT)
                        ),
                        "source_fixture_used_only_for_staging": scenario.fixture,
                        "expected_output_dir": str(out_dir.relative_to(REPO_ROOT)),
                        "repeat_artifact": _rel(repeat_path),
                        "prompt_policy_issues": prompt_policy_issues,
                    }
                    if include_prompts:
                        entry["system_prompt"] = studies.DIRECT_SYSTEM_PROMPT
                        entry["user_prompt"] = user_prompt
                    entries.append(entry)

    pending_transfer = _pending_transfer_summary(entries)
    prompt_policy_issues = [
        issue
        for entry in entries
        if entry["status"] == "pending"
        for issue in entry["prompt_policy_issues"]
    ]
    if max_correction_steps:
        repair_policy = (
            "After failed attempts, may send previous backend response plus "
            "bounded verifier feedback containing failed tier names, exit code, "
            "generated file list, and stdout/stderr tails. Local home paths and "
            "hidden README-arm Medical AI Skills skill markers are redacted by the runner."
        )
    else:
        repair_policy = (
            "Disabled for the baseline comparison; failed first commands are "
            "recorded as pass/fail data without sending repair prompts."
        )
    return {
        "status": "ready",
        "network_calls_made": False,
        "payload_fingerprint": transfer_payload_fingerprint(entries),
        "prompt_style": DIRECT_PROMPT_STYLE,
        "resume_missing": resume_missing,
        "max_correction_steps": max_correction_steps,
        "expected_repeats": repeats,
        "data_transfer_policy": {
            "initial_call": (
                "Sends fixed system prompt plus direct minimal user prompt embedding "
                "the selected SKILL.md or upstream README text, neutral staged input "
                "path, and repeat-specific output directory."
            ),
            "repair_calls": repair_policy,
            "initial_prompt_guard": (
                "Pending initial system/user prompts are scanned for local absolute "
                "home paths; approval packets block external reruns if any are found."
            ),
            "does_not_send": [
                "API key values",
                "large generated NIfTI volumes",
                "DICOM pixel data",
                "local absolute home paths after runner redaction",
            ],
        },
        "summary": {
            "skills": len(selected),
            "entries": len(entries),
            "pending_initial_calls": pending_initial_calls,
            "reused_repeats": reused_repeats,
            "max_possible_repair_calls": pending_initial_calls * max_correction_steps,
            "pending_transfer": pending_transfer,
            "backend_protocols": _backend_protocol_summary(entries),
            "prompt_policy_issue_count": len(prompt_policy_issues),
        },
        "prompt_policy_issues": prompt_policy_issues,
        "entries": entries,
    }


def _format_markdown(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    lines = [
        "# NV model study data-transfer manifest",
        "",
        "No network calls were made while generating this manifest.",
        "",
        f"Prompt style: `{manifest['prompt_style']}`",
        f"Resume-missing behavior: `{manifest['resume_missing']}`",
        f"Expected repeats per backend/arm: {manifest['expected_repeats']}",
        f"Pending initial external LLM calls: {summary['pending_initial_calls']}",
        f"Reusable current repeats: {summary['reused_repeats']}",
        f"Maximum possible repair calls for pending repeats: {summary['max_possible_repair_calls']}",
        f"Reviewed payload fingerprint: `{manifest['payload_fingerprint']}`",
        f"Pending initial payload bytes: {summary['pending_transfer']['total_initial_bytes']}",
        f"Repeated embedded-document bytes inside initial prompts: {summary['pending_transfer']['embedded_document_bytes']}",
        f"Pending prompt policy issues: {summary.get('prompt_policy_issue_count', 0)}",
        "",
        "## Data Policy",
        "",
        f"- Initial call: {manifest['data_transfer_policy']['initial_call']}",
        f"- Repair calls: {manifest['data_transfer_policy']['repair_calls']}",
        f"- Initial prompt guard: {manifest['data_transfer_policy']['initial_prompt_guard']}",
        "- Does not send: " + "; ".join(manifest["data_transfer_policy"]["does_not_send"]),
    ]
    prompt_policy_issues = manifest.get("prompt_policy_issues", [])
    if prompt_policy_issues:
        lines.extend(
            [
                "",
                "## Prompt Payload Policy Issues",
                "",
                "| Skill | Mode | Backend | Arm | Repeat | Prompt | Issue | Detail |",
                "|---|---|---|---|---:|---|---|---|",
            ]
        )
        for issue in prompt_policy_issues:
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(issue["skill"]),
                        str(issue["mode"]),
                        str(issue["backend"]),
                        str(issue["arm"]),
                        str(issue["repeat"]),
                        str(issue["prompt"]),
                        str(issue["issue"]),
                        str(issue["detail"]),
                    ]
                )
                + " |"
            )
    lines.extend(
        [
            "",
            "## Backend Protocols",
            "",
            "| Backend | Endpoint | Model | Temperature | Top-p | Max tokens | Retry attempts | Timeouts | Extra body | Protocol hash |",
            "|---|---|---|---:|---:|---:|---:|---|---|---|",
        ]
    )
    protocol_rows = summary.get("backend_protocols", [])
    if not protocol_rows:
        lines.append("| none |  |  |  |  |  |  |  |  |  |")
    for row in protocol_rows:
        temperature = "n/a" if row["temperature"] is None else str(row["temperature"])
        top_p = "n/a" if row.get("top_p") is None else str(row["top_p"])
        max_tokens = "n/a" if row.get("max_tokens") is None else str(row["max_tokens"])
        timeouts = (
            f"chat {row['chat_attempt_timeout_seconds']}s; "
            f"urlopen {row['urlopen_timeout_seconds']}s"
        )
        extra_body = json.dumps(row["extra_body"], sort_keys=True, separators=(",", ":"))
        lines.append(
            "| "
            + " | ".join(
                [
                    row["backend"],
                    row["endpoint"],
                    row["model"],
                    temperature,
                    top_p,
                    max_tokens,
                    str(row["retry_attempts"]),
                    timeouts,
                    f"`{extra_body}`",
                    f"`{row['protocol_sha256']}`",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Aggregate Pending Transfer",
            "",
            "| Endpoint | Model | Pending calls | Initial bytes | Embedded doc bytes |",
            "|---|---|---:|---:|---:|",
        ]
    )
    by_endpoint = summary["pending_transfer"]["by_endpoint_model"]
    if not by_endpoint:
        lines.append("| none |  | 0 | 0 | 0 |")
    for row in by_endpoint:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["endpoint"],
                    row["model"],
                    str(row["pending_initial_calls"]),
                    str(row["total_initial_bytes"]),
                    str(row["embedded_document_bytes"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "| Skill | Pending calls | Initial bytes | Embedded doc bytes |",
            "|---|---:|---:|---:|",
        ]
    )
    by_skill = summary["pending_transfer"]["by_skill"]
    if not by_skill:
        lines.append("| none | 0 | 0 | 0 |")
    for row in by_skill:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["skill"],
                    str(row["pending_initial_calls"]),
                    str(row["total_initial_bytes"]),
                    str(row["embedded_document_bytes"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Pending Initial Calls",
            "",
            "Rows are grouped by skill/mode/backend/arm. Use `--format json` for exact per-repeat records and prompt hashes.",
            "",
            "| Skill | Mode | Backend | Arm | Pending repeats | Endpoint | Prompt bytes | Docs |",
            "|---|---|---|---|---:|---|---:|---|",
        ]
    )
    pending = [entry for entry in manifest["entries"] if entry["status"] == "pending"]
    if not pending:
        lines.append("| none |  |  |  |  |  |  |  |")
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for entry in pending:
        grouped[
            (
                entry["skill"],
                entry["mode"],
                entry["backend"],
                entry["arm"],
                entry["endpoint"],
            )
        ].append(entry)
    for key, rows in sorted(grouped.items()):
        skill, mode, backend, arm, endpoint = key
        repeats = sorted(int(row["repeat"]) for row in rows)
        prompt_sizes = sorted({int(row["user_prompt_bytes"]) for row in rows})
        if len(prompt_sizes) == 1:
            prompt_size = str(prompt_sizes[0])
        else:
            prompt_size = f"{prompt_sizes[0]}-{prompt_sizes[-1]}"
        docs = ", ".join(
            f"{doc['path']} ({doc['byte_count']} bytes)" for doc in rows[0]["documentation"]
        )
        repeat_text = f"{repeats[0]}-{repeats[-1]} ({len(repeats)})" if repeats else "0"
        lines.append(
            "| "
            + " | ".join(
                [
                    skill,
                    mode,
                    backend,
                    arm,
                    repeat_text,
                    endpoint,
                    prompt_size,
                    docs,
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills", nargs="*", default=None, choices=sorted(studies.SCENARIOS))
    parser.add_argument(
        "--mode", choices=["codex-opus", "nemotron", "all", "prompts"], default="all"
    )
    parser.add_argument("--repeats", type=int, default=studies.DIRECT_REPEATS)
    parser.add_argument("--max-correction-steps", type=int, default=DEFAULT_MAX_CORRECTION_STEPS)
    parser.add_argument("--study-root", type=Path, default=studies.STUDY_ROOT)
    parser.add_argument("--no-resume-missing", action="store_true")
    parser.add_argument("--include-prompts", action="store_true")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    args = parser.parse_args(argv)
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")
    if args.max_correction_steps < 0:
        parser.error("--max-correction-steps must be non-negative")

    manifest = build_manifest(
        skills=args.skills,
        mode=args.mode,
        repeats=args.repeats,
        max_correction_steps=args.max_correction_steps,
        resume_missing=not args.no_resume_missing,
        study_root=args.study_root,
        include_prompts=args.include_prompts,
    )
    if args.format == "json":
        sys.stdout.write(json.dumps(manifest, indent=2) + "\n")
    else:
        sys.stdout.write(_format_markdown(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
