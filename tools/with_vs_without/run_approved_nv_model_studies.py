#!/usr/bin/env python3
"""Run reviewed NV with-vs-without direct-study remediation commands."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.with_vs_without import approval_packet_nv_model_studies as approval  # noqa: E402
from tools.with_vs_without import run_nv_model_studies as studies  # noqa: E402


APPROVAL_FLAG = studies.EXTERNAL_LLM_DATA_TRANSFER_FLAG
DEFAULT_LOG = REPO_ROOT / "runs" / "with_vs_without_nv" / "approved_reruns.jsonl"


def _command_argv(command: str) -> list[str]:
    return shlex.split(command)


def _validate_approved_command(command: str) -> list[str]:
    argv = _command_argv(command)
    if len(argv) < 3 or argv[0] != "python" or argv[1] != "tools/with_vs_without/run_nv_model_studies.py":
        raise ValueError("approved rerun command must call the NV study runner via repo-relative python")
    value_options = {"--skills", "--mode", "--prompt-style", "--max-correction-steps", "--repeats"}
    flag_options = {"--resume-missing", APPROVAL_FLAG}
    values: dict[str, list[str]] = {}
    flags: set[str] = set()
    i = 2
    while i < len(argv):
        token = argv[i]
        if token in value_options:
            if token in values:
                raise ValueError(f"approved rerun command repeats option: {token}")
            i += 1
            option_values: list[str] = []
            while i < len(argv) and not argv[i].startswith("--"):
                option_values.append(argv[i])
                i += 1
            if not option_values:
                raise ValueError(f"approved rerun command option has no value: {token}")
            if token != "--skills" and len(option_values) != 1:
                raise ValueError(f"approved rerun command option must have exactly one value: {token}")
            values[token] = option_values
            continue
        if token in flag_options:
            if token in flags:
                raise ValueError(f"approved rerun command repeats flag: {token}")
            flags.add(token)
            i += 1
            continue
        if token.startswith("--"):
            raise ValueError(f"approved rerun command contains unexpected option: {token}")
        raise ValueError(f"approved rerun command contains unexpected positional token: {token}")

    required_values = {
        "--mode": {"codex-opus", "nemotron"},
        "--prompt-style": {"minimal"},
        "--max-correction-steps": {str(studies.DIRECT_MAX_CORRECTION_STEPS)},
        "--repeats": {str(studies.DIRECT_REPEATS)},
    }
    missing = sorted(
        [option for option in value_options if option not in values]
        + [flag for flag in flag_options if flag not in flags]
    )
    if missing:
        raise ValueError(f"approved rerun command is missing required token(s): {missing}")
    for option, allowed in required_values.items():
        actual = values[option][0]
        if actual not in allowed:
            expected = ", ".join(sorted(allowed))
            raise ValueError(f"approved rerun command has invalid {option}: expected {expected}, got {actual}")
    invalid_skills = sorted(skill for skill in values["--skills"] if skill not in studies.SCENARIOS)
    if invalid_skills:
        raise ValueError(f"approved rerun command has invalid skill(s): {invalid_skills}")
    if len(values["--skills"]) != 1:
        raise ValueError("approved rerun command must target exactly one skill")
    return argv


def _option_values(argv: list[str], option: str) -> list[str]:
    start = argv.index(option) + 1
    values = []
    while start < len(argv) and not argv[start].startswith("--"):
        values.append(argv[start])
        start += 1
    return values


def build_plan(*, mode: str = "all", repeats: int = studies.DIRECT_REPEATS) -> dict[str, Any]:
    packet = approval.build_packet(mode=mode, repeats=repeats)
    commands = []
    seen_direct_groups: set[tuple[str, str]] = set()
    for item in packet["planned_commands"]:
        argv = _validate_approved_command(item["command"])
        command_skill = _option_values(argv, "--skills")[0]
        command_mode = _option_values(argv, "--mode")[0]
        if item["skill"] != command_skill:
            raise ValueError(
                "approved rerun command metadata does not match --skills: "
                f"{item['skill']!r} != {command_skill!r}"
            )
        if item["mode"] != command_mode:
            raise ValueError(
                "approved rerun command metadata does not match --mode: "
                f"{item['mode']!r} != {command_mode!r}"
            )
        direct_group = (command_skill, command_mode)
        if direct_group in seen_direct_groups:
            raise ValueError(
                "approval-ready rerun plan has duplicate direct command group: "
                f"{command_skill}:{command_mode}"
            )
        seen_direct_groups.add(direct_group)
        commands.append(
            {
                "skill": item["skill"],
                "mode": item["mode"],
                "command": item["command"],
                "argv": argv,
            }
        )
    if packet["status"] == "ready_for_external_approval" and not commands:
        raise ValueError("approval-ready rerun plan has no direct remediation commands")
    return {
        "status": packet["status"],
        "network_calls_made": False,
        "mode": mode,
        "expected_repeats": repeats,
        "approval_flag": APPROVAL_FLAG,
        "payload_fingerprint": packet["data_transfer"]["payload_fingerprint"],
        "approval_errors": packet.get("approval_errors", []),
        "approval_coverage": packet.get("approval_coverage", {}),
        "command_count": len(commands),
        "pending_initial_external_calls": packet["data_transfer"]["summary"]["pending_initial_calls"],
        "max_possible_repair_calls": packet["data_transfer"]["summary"]["max_possible_repair_calls"],
        "commands": commands,
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_log(path: Path | None, event: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"ts": _now_iso(), **event}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


def _successful_commands_from_log(path: Path | None, *, payload_fingerprint: str) -> set[str]:
    if path is None or not path.is_file():
        return set()
    completed: set[str] = set()
    for line in path.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            event.get("event") == "command_end"
            and event.get("returncode") == 0
            and event.get("payload_fingerprint") == payload_fingerprint
            and isinstance(event.get("command"), str)
        ):
            completed.add(event["command"])
    return completed


def run_plan(
    plan: dict[str, Any],
    *,
    execute: bool,
    log_path: Path | None = None,
    resume_log: bool = False,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    if execute and plan["status"] != "ready_for_external_approval":
        raise ValueError(f"refusing to execute plan with status={plan['status']!r}")
    prior_successes = (
        _successful_commands_from_log(
            log_path,
            payload_fingerprint=plan["payload_fingerprint"],
        )
        if resume_log
        else set()
    )
    _write_log(
        log_path,
        {
            "event": "plan",
            "execute": execute,
            "resume_log": resume_log,
            "status": plan["status"],
            "command_count": plan["command_count"],
            "pending_initial_external_calls": plan["pending_initial_external_calls"],
            "max_possible_repair_calls": plan["max_possible_repair_calls"],
            "payload_fingerprint": plan["payload_fingerprint"],
            "approval_errors": plan.get("approval_errors", []),
            "approval_coverage": plan.get("approval_coverage", {}),
        },
    )
    if not execute and plan["status"] != "ready_for_external_approval":
        return {
            "status": "not_ready",
            "network_calls_made": False,
            "log_path": str(log_path) if log_path else None,
            "results": results,
        }
    for command in plan["commands"]:
        result: dict[str, Any] = {
            "skill": command["skill"],
            "mode": command["mode"],
            "command": command["command"],
            "executed": execute,
        }
        if command["command"] in prior_successes:
            result["prior_success_in_log"] = True
            result["reason"] = "current_audit_still_requires_command"
            _write_log(
                log_path,
                {
                    "event": "command_prior_success_ignored",
                    "skill": command["skill"],
                    "mode": command["mode"],
                    "command": command["command"],
                    "reason": result["reason"],
                    "payload_fingerprint": plan["payload_fingerprint"],
                },
            )
        if execute:
            _write_log(
                log_path,
                {
                    "event": "command_start",
                    "skill": command["skill"],
                    "mode": command["mode"],
                    "command": command["command"],
                    "payload_fingerprint": plan["payload_fingerprint"],
                },
            )
            proc = runner(
                command["argv"],
                cwd=REPO_ROOT,
                text=True,
            )
            result["returncode"] = proc.returncode
            _write_log(
                log_path,
                {
                    "event": "command_end",
                    "skill": command["skill"],
                    "mode": command["mode"],
                    "command": command["command"],
                    "returncode": proc.returncode,
                    "payload_fingerprint": plan["payload_fingerprint"],
                },
            )
            if proc.returncode != 0:
                results.append(result)
                return {
                    "status": "failed",
                    "network_calls_made": True,
                    "log_path": str(log_path) if log_path else None,
                    "results": results,
                }
        results.append(result)
    return {
        "status": "executed" if execute else "dry_run",
        "network_calls_made": execute,
        "log_path": str(log_path) if log_path else None,
        "results": results,
    }


def _format_markdown(plan: dict[str, Any], result: dict[str, Any] | None = None) -> str:
    lines = [
        "# Approved NV model study rerun plan",
        "",
        f"Plan status: `{plan['status']}`",
        f"Commands: {plan['command_count']}",
        f"Pending initial external LLM calls: {plan['pending_initial_external_calls']}",
        f"Maximum possible repair calls: {plan['max_possible_repair_calls']}",
        f"Reviewed payload fingerprint: `{plan['payload_fingerprint']}`",
        (
            "Direct remediation coverage: "
            f"{plan.get('approval_coverage', {}).get('planned_direct_group_count', 'n/a')}/"
            f"{plan.get('approval_coverage', {}).get('pending_direct_group_count', 'n/a')} "
            "pending skill/mode groups"
        ),
        (
            "Direct remediation duplicate groups: "
            f"{plan.get('approval_coverage', {}).get('duplicate_direct_group_count', 'n/a')}"
        ),
        (
            "Direct remediation invalid commands: "
            f"{plan.get('approval_coverage', {}).get('invalid_direct_command_count', 'n/a')}"
        ),
        "",
    ]
    if plan.get("approval_errors"):
        lines.extend(
            [
                "## Approval Errors",
                "",
                "| Scope | Check | Detail |",
                "|---|---|---|",
            ]
        )
        for item in plan["approval_errors"]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(item.get("scope", "approval")),
                        str(item.get("check", "unknown")),
                        str(item.get("detail", "")),
                    ]
                )
                + " |"
            )
        lines.append("")
    lines.extend(
        [
            "## Commands",
            "",
            "```bash",
        ]
    )
    lines.extend(command["command"] for command in plan["commands"])
    lines.append("```")
    if result is not None:
        lines.extend(
            [
                "",
                "## Execution",
                "",
                f"Status: `{result['status']}`",
                f"Network calls made: `{result['network_calls_made']}`",
                f"Log path: `{result.get('log_path') or 'none'}`",
                f"Commands processed: {len(result['results'])}",
            ]
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["codex-opus", "nemotron", "all"], default="all")
    parser.add_argument("--repeats", type=int, default=studies.DIRECT_REPEATS)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument(
        "--resume-log",
        action="store_true",
        help="Skip commands already recorded with returncode 0 in --log.",
    )
    parser.add_argument(
        APPROVAL_FLAG,
        action="store_true",
        help="Required with --execute. Confirms external LLM data transfer was explicitly approved.",
    )
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    args = parser.parse_args(argv)
    if args.repeats != studies.DIRECT_REPEATS:
        parser.error(
            "approved rerun orchestration currently requires "
            f"--repeats {studies.DIRECT_REPEATS}"
        )
    if args.execute and not args.confirm_external_llm_data_transfer:
        parser.error(f"--execute requires {APPROVAL_FLAG}")

    plan = build_plan(mode=args.mode, repeats=args.repeats)
    result = run_plan(
        plan,
        execute=args.execute,
        log_path=args.log,
        resume_log=args.resume_log,
    )
    if args.format == "json":
        sys.stdout.write(json.dumps({"plan": plan, "execution": result}, indent=2) + "\n")
    else:
        sys.stdout.write(_format_markdown(plan, result))
    return 0 if result["status"] in {"dry_run", "executed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
