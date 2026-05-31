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

"""No-network status for agent-skill usability and with-vs-without proof."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.with_vs_without import approval_packet_nv_model_studies as approval  # noqa: E402
from tools.with_vs_without import run_nv_model_studies as studies  # noqa: E402

DEFAULT_REPEATS = studies.DIRECT_REPEATS
MAX_LIFECYCLE_BLOCKERS = 5


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text())


def _real_audit_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [row for row in summary.get("rows", []) if isinstance(row, dict)]
    return [
        row
        for row in rows
        if str(row.get("target")) != "negative_sloppy_skill"
        and str(row.get("target_path", "")).startswith(("skills/", "verifiers/"))
    ]


def _row_sort_key(row: dict[str, Any]) -> tuple[int, str]:
    target_path = str(row.get("target_path", ""))
    if target_path.startswith("skills/"):
        bucket = 0
    elif target_path.startswith("verifiers/"):
        bucket = 1
    else:
        bucket = 2
    return bucket, str(row.get("target", ""))


def _first_unmet_requirement(output: dict[str, Any]) -> dict[str, Any] | None:
    lifecycle = output.get("capability_lifecycle") or {}
    for requirement in lifecycle.get("requirements") or []:
        if isinstance(requirement, dict) and not requirement.get("met"):
            return requirement
    return None


def _lifecycle_blocker(row: dict[str, Any], *, audit_root: Path | None) -> dict[str, Any]:
    target = str(row.get("target") or "unknown")
    blocker = {
        "target": target,
        "target_path": str(row.get("target_path") or ""),
        "lifecycle": str(row.get("lifecycle") or "unknown"),
        "blocked_status": "unknown",
        "gaps": ["lifecycle detail unavailable; run make audit-skill for this target"],
    }
    if audit_root is None:
        return blocker
    output = _load_json(audit_root / target / "output.json")
    if not output:
        return blocker
    requirement = _first_unmet_requirement(output)
    if requirement is None:
        blocker["blocked_status"] = "none"
        blocker["gaps"] = []
        return blocker
    blocker["blocked_status"] = str(requirement.get("status") or "unknown")
    gaps = requirement.get("gaps") or []
    blocker["gaps"] = [str(gap) for gap in gaps] or ["no gap detail recorded"]
    return blocker


def _skill_audit_block(
    summary: dict[str, Any] | None,
    *,
    summary_path: Path | None = None,
) -> dict[str, Any]:
    if summary is None:
        return {
            "status": "missing",
            "reason": "run make verify-skills first",
            "real_runs": 0,
            "real_passed": 0,
            "real_failed": None,
            "real_advisory_issues": None,
            "lifecycle_counts": {},
            "published_targets": [],
            "lifecycle_blockers": [],
            "lifecycle_blocker_count": 0,
            "review_focus": "run make verify-skills first",
        }
    real_rows = _real_audit_rows(summary)
    lifecycle_counts: dict[str, int] = {}
    for row in real_rows:
        lifecycle = str(row.get("lifecycle") or "unknown")
        lifecycle_counts[lifecycle] = lifecycle_counts.get(lifecycle, 0) + 1
    published_targets = [
        str(row.get("target"))
        for row in real_rows
        if row.get("lifecycle") == "published" and row.get("target")
    ]
    gated_count = lifecycle_counts.get("gated", 0)
    audit_root = summary_path.parent if summary_path is not None else None
    blocked_rows = [
        row for row in sorted(real_rows, key=_row_sort_key) if row.get("lifecycle") != "published"
    ]
    lifecycle_blockers = [
        _lifecycle_blocker(row, audit_root=audit_root)
        for row in blocked_rows[:MAX_LIFECYCLE_BLOCKERS]
    ]
    return {
        "status": summary.get("audit_status", "unknown"),
        "real_runs": summary.get("real_runs"),
        "real_passed": summary.get("real_passed"),
        "real_failed": summary.get("real_failed"),
        "real_advisory_issues": summary.get("real_advisory_issues"),
        "lifecycle_counts": lifecycle_counts,
        "published_targets": published_targets,
        "lifecycle_blockers": lifecycle_blockers,
        "lifecycle_blocker_count": len(blocked_rows),
        "review_focus": (
            f"{gated_count} gated targets still need trusted-run/publication evidence"
            if gated_count
            else (
                "all real targets are published"
                if real_rows and lifecycle_counts.get("published") == len(real_rows)
                else "inspect lifecycle counts for next publication work"
            )
        ),
        "unexpected_failures": summary.get("unexpected_failures", []),
        "advisory_failures": summary.get("advisory_failures", []),
        "calibration_failures": summary.get("calibration_failures", []),
    }


def _overall_status(skill_audit: dict[str, Any], packet: dict[str, Any]) -> str:
    if skill_audit["status"] != "pass":
        return "not_ready"
    if packet["status"] == "already_proven":
        return "complete"
    if packet["status"] == "ready_for_external_approval":
        return "ready_for_external_approval"
    return "not_ready"


def build_report(
    *,
    skill_audit_summary_path: Path,
    mode: str = "all",
    repeats: int = DEFAULT_REPEATS,
    prompt_root: Path | None = None,
    study_root: Path | None = None,
) -> dict[str, Any]:
    skill_summary = _load_json(skill_audit_summary_path)
    packet_kwargs: dict[str, Any] = {"mode": mode, "repeats": repeats}
    if prompt_root is not None:
        packet_kwargs["prompt_root"] = prompt_root
    if study_root is not None:
        packet_kwargs["study_root"] = study_root
    packet = approval.build_packet(**packet_kwargs)
    skill_audit = _skill_audit_block(skill_summary, summary_path=skill_audit_summary_path)
    status = _overall_status(skill_audit, packet)
    audit_summary = packet["audit"]["summary"]
    transfer_summary = packet["data_transfer"]["summary"]
    approval_coverage = packet.get("approval_coverage", {})
    return {
        "status": status,
        "network_calls_made": False,
        "skill_usability": skill_audit,
        "with_vs_without": {
            "status": packet["status"],
            "preflight_status": packet["preflight"]["status"],
            "prompt_artifacts_complete": audit_summary["prompt_artifacts_complete"],
            "study_artifacts_complete": audit_summary["study_artifacts_complete"],
            "outcomes_support_skill_advantage": audit_summary["outcomes_support_skill_advantage"],
            "skills": audit_summary["skills"],
            "pending_initial_external_calls": transfer_summary["pending_initial_calls"],
            "max_possible_repair_calls": transfer_summary["max_possible_repair_calls"],
            "approval_flag": packet["approval_flag"],
            "payload_fingerprint": packet["data_transfer"].get("payload_fingerprint"),
            "direct_remediation_groups_covered": approval_coverage.get(
                "planned_direct_group_count"
            ),
            "pending_direct_remediation_groups": approval_coverage.get(
                "pending_direct_group_count"
            ),
            "duplicate_direct_remediation_groups": approval_coverage.get(
                "duplicate_direct_group_count"
            ),
            "invalid_direct_remediation_commands": approval_coverage.get(
                "invalid_direct_command_count"
            ),
            "prompt_payload_policy_issues": packet["data_transfer"].get(
                "prompt_policy_issue_count"
            ),
        },
        "next_gate": (
            "approved external reruns, then make prove-agent-skills"
            if status == "ready_for_external_approval"
            else (
                "none"
                if status == "complete"
                else "make verify-skills && make approval-packet-with-vs-without"
            )
        ),
    }


def format_markdown(report: dict[str, Any]) -> str:
    skill = report["skill_usability"]
    study = report["with_vs_without"]
    lifecycle_counts = skill.get("lifecycle_counts") or {}
    lifecycle_order = ("published", "verified", "gated", "runnable", "draft", "unknown")
    lifecycle_summary = ", ".join(
        f"{name}={lifecycle_counts[name]}" for name in lifecycle_order if name in lifecycle_counts
    )
    published_targets = ", ".join(skill.get("published_targets") or [])
    lifecycle_blockers = skill.get("lifecycle_blockers") or []
    lines = [
        "# Agent skill readiness",
        "",
        "No network calls were made while generating this status.",
        "",
        f"Status: `{report['status']}`",
        "",
        "## Skill Usability",
        "",
        f"Audit status: `{skill['status']}`",
        (
            (
                f"Real specs: {skill['real_passed']}/{skill['real_runs']} pass; "
                f"{skill['real_failed']} fail; "
                f"{skill['real_advisory_issues']} advisory issues"
            )
            if skill["status"] != "missing"
            else f"Reason: {skill['reason']}"
        ),
        (
            f"Lifecycle counts: `{lifecycle_summary or 'not available'}`"
            if skill["status"] != "missing"
            else ""
        ),
        (
            f"Published targets: `{published_targets or 'none'}`"
            if skill["status"] != "missing"
            else ""
        ),
        (
            f"Review focus: {skill.get('review_focus', 'not available')}"
            if skill["status"] != "missing"
            else ""
        ),
        "",
        "## With Vs Without",
        "",
        f"Experiment status: `{study['status']}`",
        f"Preflight: `{study['preflight_status']}`",
        (f"Prompt artifacts complete: {study['prompt_artifacts_complete']}/" f"{study['skills']}"),
        (f"Study artifacts complete: {study['study_artifacts_complete']}/" f"{study['skills']}"),
        (
            f"Outcomes supporting SKILL.md advantage: "
            f"{study['outcomes_support_skill_advantage']}/{study['skills']}"
        ),
        f"Pending initial external LLM calls: {study['pending_initial_external_calls']}",
        f"Maximum possible repair calls: {study['max_possible_repair_calls']}",
        (
            (
                "Direct remediation coverage: "
                f"{study['direct_remediation_groups_covered']}/"
                f"{study['pending_direct_remediation_groups']} "
                "pending skill/mode groups"
            )
            if study.get("direct_remediation_groups_covered") is not None
            else "Direct remediation coverage: `not available`"
        ),
        (
            (
                "Direct remediation duplicate groups: "
                f"{study['duplicate_direct_remediation_groups']}"
            )
            if study.get("duplicate_direct_remediation_groups") is not None
            else "Direct remediation duplicate groups: `not available`"
        ),
        (
            (
                "Direct remediation invalid commands: "
                f"{study['invalid_direct_remediation_commands']}"
            )
            if study.get("invalid_direct_remediation_commands") is not None
            else "Direct remediation invalid commands: `not available`"
        ),
        (
            ("Prompt payload policy issues: " f"{study['prompt_payload_policy_issues']}")
            if study.get("prompt_payload_policy_issues") is not None
            else "Prompt payload policy issues: `not available`"
        ),
        (
            f"Reviewed payload fingerprint: `{study['payload_fingerprint']}`"
            if study.get("payload_fingerprint")
            else "Reviewed payload fingerprint: `not available`"
        ),
        "",
        f"Next gate: `{report['next_gate']}`",
    ]
    if skill["status"] != "missing" and lifecycle_blockers:
        lines.extend(
            [
                "",
                f"## Lifecycle Blockers (first {len(lifecycle_blockers)})",
                "",
            ]
        )
        for blocker in lifecycle_blockers:
            gaps = "; ".join(blocker.get("gaps") or ["no gap detail recorded"])
            lines.append(f"- `{blocker['target']}` -> `{blocker['blocked_status']}`: {gaps}")
    if report["status"] == "ready_for_external_approval":
        lines.extend(
            [
                "",
                "The local repo is ready for explicit external-run approval, but "
                "the objective is not complete until refreshed study artifacts "
                "pass `make prove-agent-skills`.",
            ]
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skill-audit-summary",
        type=Path,
        default=REPO_ROOT / "runs" / "skill_audit" / "_summary.json",
    )
    parser.add_argument(
        "--mode", choices=["codex-opus", "nemotron", "all", "prompts"], default="all"
    )
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--prompt-root", type=Path, default=None)
    parser.add_argument("--study-root", type=Path, default=None)
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")

    report = build_report(
        skill_audit_summary_path=args.skill_audit_summary,
        mode=args.mode,
        repeats=args.repeats,
        prompt_root=args.prompt_root,
        study_root=args.study_root,
    )
    if args.format == "json":
        sys.stdout.write(json.dumps(report, indent=2) + "\n")
    else:
        sys.stdout.write(format_markdown(report))
    if args.strict and report["status"] != "complete":
        return 1
    if report["status"] == "not_ready":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
