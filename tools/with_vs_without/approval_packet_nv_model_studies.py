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

"""Compose a no-network approval packet for pending NV direct-study reruns."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.with_vs_without import audit_nv_model_studies as audit  # noqa: E402
from tools.with_vs_without import manifest_nv_model_data_transfer as transfer  # noqa: E402
from tools.with_vs_without import preflight_nv_model_studies as preflight  # noqa: E402
from tools.with_vs_without import run_nv_model_studies as studies  # noqa: E402

MODE_COMMANDS = {
    "all": {"prompts", "codex-opus", "nemotron"},
    "codex-opus": {"prompts", "codex-opus"},
    "nemotron": {"prompts", "nemotron"},
    "prompts": {"prompts"},
}
DIRECT_COMMAND_MODES = {"codex-opus", "nemotron"}
TRANSFER_MODE_TO_COMMAND_MODE = {
    "codex-opus": "codex-opus",
    "nemotron-correction": "nemotron",
}


def _issue_code_counts(issues: list[dict[str, str]], *, limit: int = 5) -> list[dict[str, Any]]:
    counts = Counter(issue.get("code", "unknown") for issue in issues)
    return [{"code": code, "count": count} for code, count in counts.most_common(limit)]


def _selected_remediation(commands: list[dict[str, str]], mode: str) -> list[dict[str, str]]:
    allowed = MODE_COMMANDS[mode]
    return [command for command in commands if command.get("mode") in allowed]


def _pending_direct_keys(transfer_manifest: dict[str, Any]) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for entry in transfer_manifest.get("entries", []):
        if entry.get("status") != "pending":
            continue
        command_mode = TRANSFER_MODE_TO_COMMAND_MODE.get(str(entry.get("mode")))
        skill = entry.get("skill")
        if command_mode and isinstance(skill, str):
            keys.add((skill, command_mode))
    return keys


def _planned_direct_keys(commands: list[dict[str, str]]) -> set[tuple[str, str]]:
    return set(_planned_direct_key_counts(commands))


def _planned_direct_key_counts(commands: list[dict[str, str]]) -> Counter[tuple[str, str]]:
    counts: Counter[tuple[str, str]] = Counter()
    for command in commands:
        mode = command.get("mode")
        skill = command.get("skill")
        if mode in DIRECT_COMMAND_MODES and isinstance(skill, str):
            counts[(skill, mode)] += 1
    return counts


def _duplicate_direct_keys(commands: list[dict[str, str]]) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for key, count in _planned_direct_key_counts(commands).items():
        if count > 1:
            keys.add(key)
    return keys


def _format_missing_direct_keys(keys: set[tuple[str, str]]) -> str:
    return ", ".join(f"{skill}:{mode}" for skill, mode in sorted(keys))


def _format_prompt_policy_issues(issues: list[dict[str, Any]], *, limit: int = 5) -> str:
    fragments = []
    for issue in issues[:limit]:
        fragments.append(
            (
                f"{issue.get('skill')}:{issue.get('mode')}:"
                f"{issue.get('backend')}:{issue.get('arm')} "
                f"repeat {issue.get('repeat')} {issue.get('prompt')} "
                f"{issue.get('issue')}"
            )
        )
    if len(issues) > limit:
        fragments.append(f"... {len(issues) - limit} more")
    return "; ".join(fragments)


def _direct_key_records(keys: set[tuple[str, str]]) -> list[dict[str, str]]:
    return [{"skill": skill, "mode": mode} for skill, mode in sorted(keys)]


def _command_values(argv: list[str], option: str) -> list[str]:
    if option not in argv:
        return []
    start = argv.index(option) + 1
    values = []
    while start < len(argv) and not argv[start].startswith("--"):
        values.append(argv[start])
        start += 1
    return values


def _direct_command_protocol_errors(
    commands: list[dict[str, str]],
    *,
    repeats: int,
    max_correction_steps: int,
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    value_options = {"--skills", "--mode", "--prompt-style", "--max-correction-steps", "--repeats"}
    flag_options = {"--resume-missing", studies.EXTERNAL_LLM_DATA_TRANSFER_FLAG}
    required_values = {
        "--prompt-style": "minimal",
        "--max-correction-steps": str(max_correction_steps),
        "--repeats": str(repeats),
    }
    for command in commands:
        if command.get("mode") not in DIRECT_COMMAND_MODES:
            continue
        command_text = command.get("command", "")
        try:
            argv = shlex.split(command_text)
        except ValueError as exc:
            errors.append(
                {
                    "skill": str(command.get("skill", "")),
                    "mode": str(command.get("mode", "")),
                    "detail": f"cannot parse command: {exc}",
                }
            )
            continue
        details = []
        if len(argv) < 2 or argv[:2] != ["python", "tools/with_vs_without/run_nv_model_studies.py"]:
            details.append("must call the NV study runner via repo-relative python")
        unexpected = [
            token
            for token in argv[2:]
            if token.startswith("--") and token not in value_options and token not in flag_options
        ]
        if unexpected:
            details.append(f"unexpected option(s): {', '.join(sorted(unexpected))}")
        for option in value_options:
            if argv.count(option) > 1:
                details.append(f"repeated option: {option}")
            values = _command_values(argv, option)
            if not values:
                details.append(
                    f"missing value for {option}" if option in argv else f"missing {option}"
                )
            elif option != "--skills" and len(values) != 1:
                details.append(f"{option} must have exactly one value")
        for flag in flag_options:
            if flag not in argv:
                details.append(f"missing {flag}")
            elif argv.count(flag) > 1:
                details.append(f"repeated flag: {flag}")
        skill_values = _command_values(argv, "--skills")
        mode_values = _command_values(argv, "--mode")
        if len(skill_values) != 1:
            details.append("--skills must target exactly one skill")
        elif command.get("skill") != skill_values[0]:
            details.append(f"metadata skill does not match --skills {skill_values[0]}")
        if len(mode_values) == 1:
            if mode_values[0] not in DIRECT_COMMAND_MODES:
                details.append(f"--mode must be one of {', '.join(sorted(DIRECT_COMMAND_MODES))}")
            elif command.get("mode") != mode_values[0]:
                details.append(f"metadata mode does not match --mode {mode_values[0]}")
        for option, expected in required_values.items():
            values = _command_values(argv, option)
            if len(values) == 1 and values[0] != expected:
                details.append(f"{option} must be {expected}")
        if details:
            errors.append(
                {
                    "skill": str(command.get("skill", "")),
                    "mode": str(command.get("mode", "")),
                    "detail": "; ".join(details),
                }
            )
    return errors


def _status(
    preflight_report: dict[str, Any],
    audit_report: dict[str, Any],
    pending_calls: int,
    approval_error_count: int,
) -> str:
    if preflight_report["status"] != "pass":
        return "not_ready"
    if audit_report["status"] == "complete":
        if (
            audit_report["summary"]["outcomes_support_skill_advantage"]
            == audit_report["summary"]["skills"]
        ):
            return "already_proven"
        return "complete_without_full_skill_advantage"
    if pending_calls > 0:
        if approval_error_count:
            return "not_ready"
        return "ready_for_external_approval"
    return "incomplete_without_external_work"


def build_packet(
    *,
    skills: list[str] | None = None,
    mode: str = "all",
    repeats: int = studies.DIRECT_REPEATS,
    max_correction_steps: int = transfer.DEFAULT_MAX_CORRECTION_STEPS,
    prompt_root: Path = studies.PROMPT_ARTIFACT_ROOT,
    study_root: Path = studies.STUDY_ROOT,
    environ: dict[str, str] | None = None,
    bashrc: Path | None = None,
) -> dict[str, Any]:
    """Build a compact review packet without touching any external API."""
    preflight_report = preflight.preflight(
        skills=skills,
        mode=mode,
        repeats=repeats,
        prompt_root=prompt_root,
        environ=environ,
        bashrc=bashrc,
    )
    transfer_manifest = transfer.build_manifest(
        skills=skills,
        mode=mode,
        repeats=repeats,
        max_correction_steps=max_correction_steps,
        resume_missing=True,
        study_root=study_root,
        include_prompts=False,
    )
    audit_report = audit.audit_all(
        skills=skills,
        prompt_root=prompt_root,
        study_root=study_root,
        repeats=repeats,
    )

    pending_calls = transfer_manifest["summary"]["pending_initial_calls"]
    selected_commands = _selected_remediation(audit_report.get("remediation", []), mode)
    pending_direct_keys = _pending_direct_keys(transfer_manifest)
    planned_direct_keys = _planned_direct_keys(selected_commands)
    missing_direct_keys = pending_direct_keys - planned_direct_keys
    duplicate_direct_keys = _duplicate_direct_keys(selected_commands)
    direct_command_protocol_errors = _direct_command_protocol_errors(
        selected_commands,
        repeats=repeats,
        max_correction_steps=max_correction_steps,
    )
    correction_budget_errors = []
    if max_correction_steps != studies.DIRECT_MAX_CORRECTION_STEPS:
        correction_budget_errors.append(
            {
                "skill": "*",
                "mode": str(mode),
                "detail": (
                    "current direct-study approval protocol requires "
                    f"max_correction_steps={studies.DIRECT_MAX_CORRECTION_STEPS}, "
                    f"got {max_correction_steps}"
                ),
            }
        )
    prompt_policy_issues = transfer_manifest.get("prompt_policy_issues", [])
    preflight_errors = [item for item in preflight_report["checks"] if item["status"] == "error"]
    approval_errors = []
    if prompt_policy_issues:
        approval_errors.append(
            {
                "scope": "data_transfer",
                "check": "prompt_payload_policy",
                "detail": (
                    "pending initial prompt policy issues: "
                    f"{_format_prompt_policy_issues(prompt_policy_issues)}"
                ),
            }
        )
    if preflight_report["status"] == "pass" and audit_report["status"] != "complete":
        if pending_calls > 0 and not pending_direct_keys:
            approval_errors.append(
                {
                    "scope": "approval",
                    "check": "direct_remediation_commands",
                    "detail": (
                        "pending external LLM calls exist, but the transfer "
                        "manifest has no pending direct skill/mode entries"
                    ),
                }
            )
        elif missing_direct_keys:
            approval_errors.append(
                {
                    "scope": "approval",
                    "check": "direct_remediation_commands",
                    "detail": (
                        "pending external LLM calls exist, but the audit produced "
                        "no matching direct remediation commands for: "
                        f"{_format_missing_direct_keys(missing_direct_keys)}"
                    ),
                }
            )
        if duplicate_direct_keys:
            approval_errors.append(
                {
                    "scope": "approval",
                    "check": "unique_direct_remediation_commands",
                    "detail": (
                        "audit produced duplicate direct remediation commands for: "
                        f"{_format_missing_direct_keys(duplicate_direct_keys)}"
                    ),
                }
            )
        if correction_budget_errors:
            approval_errors.append(
                {
                    "scope": "approval",
                    "check": "direct_correction_budget",
                    "detail": (
                        "direct study correction budget is not approval-ready: "
                        + "; ".join(
                            f"{item['skill']}:{item['mode']} {item['detail']}"
                            for item in correction_budget_errors
                        )
                    ),
                }
            )
        if direct_command_protocol_errors:
            approval_errors.append(
                {
                    "scope": "approval",
                    "check": "direct_command_protocol",
                    "detail": (
                        "direct remediation command protocol errors: "
                        + "; ".join(
                            f"{item['skill']}:{item['mode']} {item['detail']}"
                            for item in direct_command_protocol_errors
                        )
                    ),
                }
            )
    all_issues: list[dict[str, str]] = []
    for skill in audit_report["skills"]:
        all_issues.extend(skill["prompt_artifact"]["issues"])
        all_issues.extend(skill["study_artifacts"]["issues"])

    packet_status = _status(preflight_report, audit_report, pending_calls, len(approval_errors))
    return {
        "status": packet_status,
        "network_calls_made": False,
        "mode": mode,
        "expected_repeats": repeats,
        "approval_flag": studies.EXTERNAL_LLM_DATA_TRANSFER_FLAG,
        "external_transfer_required": pending_calls > 0,
        "preflight": {
            "status": preflight_report["status"],
            "summary": preflight_report["summary"],
            "errors": preflight_errors,
        },
        "approval_errors": approval_errors,
        "approval_coverage": {
            "pending_direct_groups": _direct_key_records(pending_direct_keys),
            "planned_direct_groups": _direct_key_records(planned_direct_keys),
            "missing_direct_groups": _direct_key_records(missing_direct_keys),
            "duplicate_direct_groups": _direct_key_records(duplicate_direct_keys),
            "invalid_direct_commands": correction_budget_errors + direct_command_protocol_errors,
            "pending_direct_group_count": len(pending_direct_keys),
            "planned_direct_group_count": len(planned_direct_keys),
            "planned_direct_command_count": sum(
                1 for command in selected_commands if command.get("mode") in DIRECT_COMMAND_MODES
            ),
            "missing_direct_group_count": len(missing_direct_keys),
            "duplicate_direct_group_count": len(duplicate_direct_keys),
            "invalid_direct_command_count": len(correction_budget_errors)
            + len(direct_command_protocol_errors),
        },
        "data_transfer": {
            "prompt_style": transfer_manifest["prompt_style"],
            "resume_missing": transfer_manifest["resume_missing"],
            "max_correction_steps": max_correction_steps,
            "payload_fingerprint": transfer_manifest["payload_fingerprint"],
            "summary": transfer_manifest["summary"],
            "backend_protocols": transfer_manifest["summary"].get("backend_protocols", []),
            "prompt_policy_issue_count": len(prompt_policy_issues),
            "prompt_policy_issues": prompt_policy_issues,
            "policy": transfer_manifest["data_transfer_policy"],
        },
        "audit": {
            "status": audit_report["status"],
            "summary": audit_report["summary"],
            "top_issue_codes": _issue_code_counts(all_issues),
        },
        "planned_commands": selected_commands,
    }


def _format_issue_counts(counts: list[dict[str, Any]]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"`{item['code']}` x{item['count']}" for item in counts)


def _format_markdown(packet: dict[str, Any]) -> str:
    transfer_summary = packet["data_transfer"]["summary"]
    pending = transfer_summary["pending_transfer"]
    preflight_summary = packet["preflight"]["summary"]
    audit_summary = packet["audit"]["summary"]
    lines = [
        "# NV model study approval packet",
        "",
        "No network calls were made while generating this packet.",
        "",
        f"Status: `{packet['status']}`",
        f"Mode: `{packet['mode']}`",
        f"Prompt style for direct API calls: `{packet['data_transfer']['prompt_style']}`",
        f"Expected repeats per backend/arm: {packet['expected_repeats']}",
        "",
        "## Local Readiness",
        "",
        (
            f"Preflight: `{packet['preflight']['status']}` "
            f"({preflight_summary['checks']} checks, "
            f"{preflight_summary['errors']} errors, "
            f"{preflight_summary['warnings']} warnings)"
        ),
        (
            f"Audit: `{packet['audit']['status']}` "
            f"({audit_summary['prompt_artifacts_complete']}/"
            f"{audit_summary['skills']} prompt artifacts complete, "
            f"{audit_summary['study_artifacts_complete']}/"
            f"{audit_summary['skills']} studies complete, "
            f"{audit_summary['outcomes_support_skill_advantage']}/"
            f"{audit_summary['skills']} outcomes support SKILL.md advantage)"
        ),
        f"Top audit issue codes: {_format_issue_counts(packet['audit']['top_issue_codes'])}",
        (
            "Direct remediation coverage: "
            f"{packet['approval_coverage']['planned_direct_group_count']}/"
            f"{packet['approval_coverage']['pending_direct_group_count']} "
            "pending skill/mode groups covered"
        ),
        (
            "Direct remediation duplicate groups: "
            f"{packet['approval_coverage']['duplicate_direct_group_count']}"
        ),
        (
            "Direct remediation invalid commands: "
            f"{packet['approval_coverage']['invalid_direct_command_count']}"
        ),
        (
            "Pending prompt policy issues: "
            f"{packet['data_transfer'].get('prompt_policy_issue_count', 0)}"
        ),
        "",
        "## External Transfer Scope",
        "",
        f"Pending initial external LLM calls: {transfer_summary['pending_initial_calls']}",
        f"Reusable current repeats: {transfer_summary['reused_repeats']}",
        f"Maximum possible repair calls: {transfer_summary['max_possible_repair_calls']}",
        f"Reviewed payload fingerprint: `{packet['data_transfer']['payload_fingerprint']}`",
        f"Pending initial payload bytes: {pending['total_initial_bytes']}",
        f"Repeated embedded-document bytes: {pending['embedded_document_bytes']}",
        "",
        "| Endpoint | Model | Pending calls | Initial bytes | Embedded doc bytes |",
        "|---|---|---:|---:|---:|",
    ]
    endpoint_rows = pending["by_endpoint_model"]
    if not endpoint_rows:
        lines.append("| none |  | 0 | 0 | 0 |")
    for row in endpoint_rows:
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
    skill_rows = pending["by_skill"]
    if not skill_rows:
        lines.append("| none | 0 | 0 | 0 |")
    for row in skill_rows:
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

    protocol_rows = packet["data_transfer"].get("backend_protocols", [])
    lines.extend(
        [
            "",
            "## Backend Protocols",
            "",
            "| Backend | Endpoint | Model | Temperature | Top-p | Max tokens | Retry attempts | Timeouts | Extra body | Protocol hash |",
            "|---|---|---|---:|---:|---:|---:|---|---|---|",
        ]
    )
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

    policy = packet["data_transfer"]["policy"]
    lines.extend(
        [
            "",
            "## Data Policy",
            "",
            f"- Initial call: {policy['initial_call']}",
            f"- Repair calls: {policy['repair_calls']}",
            f"- Initial prompt guard: {policy.get('initial_prompt_guard', 'not recorded')}",
            "- Does not send: " + "; ".join(policy["does_not_send"]),
        ]
    )

    if packet["preflight"]["errors"]:
        lines.extend(
            [
                "",
                "## Readiness Errors",
                "",
                "| Scope | Check | Detail |",
                "|---|---|---|",
            ]
        )
        for item in packet["preflight"]["errors"]:
            lines.append(f"| {item['scope']} | {item['check']} | {item['detail']} |")
        lines.extend(
            [
                "",
                "Fix readiness errors before running any direct-study command below.",
            ]
        )
    if packet.get("approval_errors"):
        lines.extend(
            [
                "",
                "## Approval Packet Errors",
                "",
                "| Scope | Check | Detail |",
                "|---|---|---|",
            ]
        )
        for item in packet["approval_errors"]:
            lines.append(f"| {item['scope']} | {item['check']} | {item['detail']} |")
        lines.extend(
            [
                "",
                "Regenerate or fix the audit remediation plan before approving external reruns.",
            ]
        )

    if packet["planned_commands"]:
        lines.extend(
            [
                "",
                "## Approval Commands",
                "",
                (
                    "The direct-study commands below include "
                    f"`{packet['approval_flag']}` and send the scoped prompt data "
                    "described above to external LLM APIs."
                ),
                "",
                "```bash",
            ]
        )
        lines.extend(command["command"] for command in packet["planned_commands"])
        lines.append("```")
    else:
        lines.extend(
            [
                "",
                "## Approval Commands",
                "",
                "No remediation commands are needed for the selected mode.",
            ]
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills", nargs="*", default=None, choices=sorted(studies.SCENARIOS))
    parser.add_argument(
        "--mode", choices=["codex-opus", "nemotron", "all", "prompts"], default="all"
    )
    parser.add_argument("--repeats", type=int, default=studies.DIRECT_REPEATS)
    parser.add_argument(
        "--max-correction-steps", type=int, default=transfer.DEFAULT_MAX_CORRECTION_STEPS
    )
    parser.add_argument("--prompt-root", type=Path, default=studies.PROMPT_ARTIFACT_ROOT)
    parser.add_argument("--study-root", type=Path, default=studies.STUDY_ROOT)
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    args = parser.parse_args(argv)
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")
    if args.repeats != studies.DIRECT_REPEATS:
        parser.error(
            "approval packet for direct external reruns currently requires "
            f"--repeats {studies.DIRECT_REPEATS}"
        )
    if args.max_correction_steps < 0:
        parser.error("--max-correction-steps must be non-negative")

    packet = build_packet(
        skills=args.skills,
        mode=args.mode,
        repeats=args.repeats,
        max_correction_steps=args.max_correction_steps,
        prompt_root=args.prompt_root,
        study_root=args.study_root,
    )
    if args.format == "json":
        sys.stdout.write(json.dumps(packet, indent=2) + "\n")
    else:
        sys.stdout.write(_format_markdown(packet))
    return 1 if packet["status"] == "not_ready" else 0


if __name__ == "__main__":
    raise SystemExit(main())
