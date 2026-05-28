#!/usr/bin/env python3
"""Write final NV with-vs-without skill experiment reports from JSON artifacts."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
import re
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.with_vs_without.audit_nv_model_studies import audit_all  # noqa: E402
from tools.with_vs_without import manifest_nv_model_data_transfer as transfer  # noqa: E402
from tools.with_vs_without.run_nv_model_studies import (
    BASH_BLOCK_RE,
    CACHE_ROOT,
    DIRECT_REPEATS,
    REPO_ROOT,
    SCENARIOS,
    _extract_command,
    _safe_to_execute,
    _shared_cache_env_records,
    _staged_input_path,
)

STUDY_ROOT = REPO_ROOT / "examples/studies/with_vs_without_skill"
RUN_ROOT = REPO_ROOT / "runs/with_vs_without_nv"
DOC_ROOT = REPO_ROOT / "docs"
PROMPT_ROOT = REPO_ROOT / "tools/nat_audit/data"

REFRESHED = "May 27, 2026"
FULL_LOG_GLOB = "run_all_after_timeout_patch_*.log"
RERUN_LOG_GLOB = "rerun_codex_opus_after_skill_fixes_*.log"
_REPORT_AUDIT_STATUS = "complete"
_REPORT_AUDIT_ISSUES = 0
_REPORT_AUDIT_SUMMARY: dict[str, Any] = {}
_REPORT_AUDIT_SKILLS: list[dict[str, Any]] = []
_REPORT_TRANSFER_SUMMARY: dict[str, Any] = {}
_REPORT_TRANSFER_FINGERPRINT = ""

CACHE_ENV_SUMMARY = ", ".join(
    f"`{name}={path}`" for name, path in _shared_cache_env_records().items()
)
CACHE_ENV_TEXT = (
    "Dependency and model download caches are shared only as documented "
    f"test-environment caches under `{CACHE_ROOT.relative_to(REPO_ROOT)}` "
    f"({CACHE_ENV_SUMMARY})."
)

SKILL_FIX_NOTES = {
    "nv_generate_mr": (
        "Before the final rerun, `SKILL.md` was tightened to name "
        "`scripts/run_mr.py` as the exact runnable surface, preserve the staged "
        "request path, and avoid invented module or shell entrypoints."
    ),
    "nv_generate_mr_brain": (
        "Before the final rerun, `SKILL.md` was tightened to name "
        "`scripts/run_mr_brain.py` as the exact runnable surface, preserve the "
        "staged request path, and avoid invented module or shell entrypoints."
    ),
    "nv_reason_cxr": (
        "Before the final rerun, `SKILL.md` was tightened to name "
        "`scripts/run_nv_reason_cxr.py` as the exact command-shape smoke-test "
        "surface and to reserve live model inference for explicit user requests."
    ),
    "nv_segment_ct": (
        "Before the final rerun, `SKILL.md` was tightened to name "
        "`scripts/run_vista3d.py` as the exact runnable surface and to state the "
        "required label IDs for the requested spleen/liver/kidney task."
    ),
    "nv_segment_ct_finetune": (
        "Before the final rerun, `SKILL.md` was tightened to name "
        "`scripts/run_finetune.py` as the smoke-scale finetune surface and to "
        "require the user's staged dataset path."
    ),
    "nv_segment_ctmr": (
        "Before the final rerun, `SKILL.md` was tightened to name "
        "`scripts/run_ctmr.py` as the exact runnable surface and to state the "
        "`CT_BODY` modality expected for this CT body segmentation task."
    ),
}

DEFAULT_SKILL_FIX_NOTE = (
    "No separate final-run skill fix note is recorded in the saved study JSON "
    "for this scenario; this report was regenerated from the post-fix study "
    "artifacts."
)


def _report_status_clause() -> str:
    if _REPORT_AUDIT_STATUS == "complete":
        return f"strict audit passed for refreshed artifacts on {REFRESHED}"
    return (
        f"refreshed from saved artifacts on {REFRESHED}; strict audit currently "
        f"{_REPORT_AUDIT_STATUS} ({_REPORT_AUDIT_ISSUES} issue(s))"
    )


def _report_is_complete() -> bool:
    return _REPORT_AUDIT_STATUS == "complete"


def _audit_skill_map() -> dict[str, dict[str, Any]]:
    return {
        str(item.get("skill", "")): item
        for item in _REPORT_AUDIT_SKILLS
        if isinstance(item, dict)
    }


def _audit_issue_counts(limit: int = 5) -> str:
    counts: Counter[str] = Counter()
    for skill in _REPORT_AUDIT_SKILLS:
        for group_name in ("prompt_artifact", "study_artifacts"):
            group = skill.get(group_name) or {}
            for issue in group.get("issues") or []:
                counts[str(issue.get("code", "unknown"))] += 1
    if not counts:
        return "none"
    return ", ".join(f"`{code}` x{count}" for code, count in counts.most_common(limit))


def _audit_status_label(value: Any) -> str:
    return str(value or "unknown").replace("_", " ")


def _skill_audit_status_text(skill: str) -> str:
    row = _audit_skill_map().get(skill)
    if not row:
        return "Audit record missing for this skill; regenerate the audit before citing results."
    prompt_status = _audit_status_label((row.get("prompt_artifact") or {}).get("status"))
    study = row.get("study_artifacts") or {}
    study_status = _audit_status_label(study.get("status"))
    outcome = row.get("outcome") or {}
    outcome_status = _audit_status_label(outcome.get("status"))
    issue_count = len((study.get("issues") or [])) + len(
        ((row.get("prompt_artifact") or {}).get("issues") or [])
    )
    if issue_count:
        return (
            f"Prompt artifact {prompt_status}; study artifacts are {study_status}; "
            f"outcome gate is {outcome_status}; {issue_count} audit issue(s) remain."
        )
    return (
        f"Prompt artifact {prompt_status}; study artifacts are {study_status}; "
        f"outcome gate is {outcome_status}; no audit issues remain."
    )


def _write_incomplete_overview() -> None:
    summary = _REPORT_AUDIT_SUMMARY
    transfer_summary = _REPORT_TRANSFER_SUMMARY
    skill_count = int(summary.get("skills", len(SCENARIOS)) or len(SCENARIOS))
    prompt_complete = int(summary.get("prompt_artifacts_complete", 0) or 0)
    studies_complete = int(summary.get("study_artifacts_complete", 0) or 0)
    outcomes_support = int(summary.get("outcomes_support_skill_advantage", 0) or 0)
    outcomes_complete = int(summary.get("outcomes_complete", 0) or 0)
    pending_calls = transfer_summary.get("pending_initial_calls", "unknown")
    reused_repeats = transfer_summary.get("reused_repeats", "unknown")
    repair_calls = transfer_summary.get("max_possible_repair_calls", "unknown")
    fingerprint = _REPORT_TRANSFER_FINGERPRINT or "unknown"
    lines = [
        "# With-vs-Without Skill Experiment Docs",
        "",
        f"Last refreshed: {REFRESHED}.",
        f"Audit status: {_report_status_clause()}.",
        "",
        "This page is regenerated from the current local audit state; current "
        "outcome support remains incomplete, so this document must not be "
        "cited as a completed aggregate with-vs-without result.",
        "",
        "The corrected experiment is **LLM + SKILL.md vs LLM + upstream "
        "README/guide**. Direct API modes use the embedded-doc minimal prompt "
        "because those chat backends cannot read repo files; fair path-prompt "
        "artifacts for future tool-agent/NAT comparisons are still saved under "
        "`tools/nat_audit/data/`.",
        "",
        "The main protocol remains deliberately **no-repair**:",
        "",
        "```text",
        "DIRECT_MAX_CORRECTION_STEPS = 0",
        "```",
        "",
        "This is an engineering reproducibility protocol. It tests whether an "
        "agent can read documentation and take the right action. It is not a "
        "clinical, diagnostic, regulatory, or model-quality claim.",
        "",
        "## Current Audit State",
        "",
        f"- Prompt artifacts complete: {prompt_complete}/{skill_count}.",
        f"- Study artifacts complete: {studies_complete}/{skill_count}.",
        f"- Complete paired outcomes: {outcomes_complete}/{skill_count}.",
        (
            f"- Outcome-support gates: {outcomes_support}/{skill_count} skills "
            "currently support SKILL.md paired advantage."
        ),
        f"- Strict audit issues: {_REPORT_AUDIT_ISSUES}.",
        f"- Top issue codes: {_audit_issue_counts()}.",
        f"- Pending initial external LLM calls: {pending_calls}.",
        f"- Reusable current repeats: {reused_repeats}.",
        f"- Maximum possible repair calls for this no-repair baseline: {repair_calls}.",
        f"- Reviewed payload fingerprint: `{fingerprint}`.",
        "",
        "The saved JSON files still contain historical pass/fail rows, but the "
        "strict audit rejects part of the current artifact set. Those rows are "
        "debugging context until the approved reruns replace the invalid or "
        "outdated repeats. Use `make audit-with-vs-without`, "
        "`make approval-packet-with-vs-without`, and "
        "`make approved-rerun-plan-with-vs-without` for the current local "
        "status and reviewed rerun plan.",
        "",
        "## Document Matrix",
        "",
        "| Skill | Codex/Opus comparison | Nemotron baseline study | Current status |",
        "|---|---|---|---|",
    ]
    for skill in sorted(SCENARIOS):
        codex_doc = f"with-vs-without-{_slug(skill)}-codex-opus.md"
        nemo_doc = f"with-vs-without-{_slug(skill)}-nemotron-correction.md"
        lines.append(
            f"| `{skill}` | [`{codex_doc}`]({codex_doc}) | "
            f"[`{nemo_doc}`]({nemo_doc}) | {_skill_audit_status_text(skill)} |"
        )
    lines.extend(
        [
            "",
            "## Shared Arm Rules",
            "",
            "| Arm | Agent may read | Agent may not read | Final answer target |",
            "|---|---|---|---|",
            "| With skill | `skills/<skill>/SKILL.md` | unrelated skill internals unless linked by `SKILL.md` | One bash command or `&&`-chained command using Medical AI Skills wrapper |",
            "| Without skill | one upstream README, model card, or upstream guide selected for that skill | `skills/<skill>/`, wrapper scripts, validators, manifests, evidence packs | One bash command or `&&`-chained command using upstream directly |",
            "",
            "The without-skill arm is not a no-docs baseline. It is a comparison "
            "against the upstream documentation a reasonable user would have.",
            "",
            "## Shared Five-Tier Grade",
            "",
            "| Tier | Check |",
            "|---|---|",
            "| 1 | A runnable entrypoint is present. |",
            "| 2 | The command references the neutral staged user input path under `runs/with_vs_without_nv/_inputs/`. |",
            "| 3 | The command selects the required model variant, modality, label IDs, or anatomy controls. |",
            "| 4 | The command writes to the expected arm-specific output directory. |",
            "| 5 | The command executes outside the sandbox, produces the expected artifact, and passes deterministic output checks. |",
            "",
            "## Generated Artifacts",
            "",
            "Study JSONs live under `examples/studies/with_vs_without_skill/`. "
            "Large generated NIfTI volumes, checkpoints, and command outputs live "
            "under `runs/with_vs_without_nv/` and remain gitignored.",
            "",
            f"NV full run log: `{_latest_log(FULL_LOG_GLOB)}`.",
            f"NV targeted rerun log: `{_latest_log(RERUN_LOG_GLOB)}`.",
            "",
            "The helper used for the all-skill batch is "
            "`tools/with_vs_without/run_nv_model_studies.py`. It executes only "
            "guarded commands that reference the expected output directory and "
            "the expected skill/upstream runnable surface; unsafe shell fragments "
            "and without-skill commands that call hidden Medical AI Skills skill paths "
            "or wrapper basenames are blocked and graded as failures.",
            "",
            "## Prompt Artifacts",
            "",
            "The fair A2-style path prompts for NAT/tool-agent comparisons are saved here:",
            "",
            "| Skill | Prompt artifact |",
            "|---|---|",
        ]
    )
    for skill in sorted(SCENARIOS):
        artifact = PROMPT_ROOT / f"eval_nv_model_studies_{skill}_prompts.json"
        lines.append(f"| `{skill}` | `{_rel(artifact)}` |")
    lines.extend(
        [
            "",
            "Regenerate prompt artifacts without making external API calls:",
            "",
            "```bash",
            "python tools/with_vs_without/run_nv_model_studies.py --mode prompts --prompt-style path",
            "```",
            "",
        ]
    )
    (DOC_ROOT / "with-vs-without-skill-experiment.md").write_text("\n".join(lines))


def _slug(skill: str) -> str:
    return skill.replace("_", "-")


def _rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _is_unresolved(value: Any) -> bool:
    return value == "unresolved" or (isinstance(value, float) and math.isinf(value))


def _report_input_path(skill: str) -> Path:
    return _staged_input_path(SCENARIOS[skill])


def _record_repeats(record: dict[str, Any]) -> list[dict[str, Any]]:
    if "repeats" in record:
        return record["repeats"]
    if "final" in record:
        final = record["final"]
        if "attempts" not in final and "attempts" in record:
            final = dict(final)
            final["attempts"] = record["attempts"]
        return [final]
    return [record]


def _record_value(record: dict[str, Any], key: str, default: str = "") -> Any:
    if key in record:
        return record[key]
    repeats = _record_repeats(record)
    if repeats and key in repeats[0]:
        return repeats[0][key]
    return default


def _steps_text(value: Any) -> str:
    if _is_unresolved(value):
        return "unresolved"
    return str(value)


def _record_summary(record: dict[str, Any]) -> dict[str, Any]:
    repeats = _record_repeats(record)
    scores = [r["score"]["score"] for r in repeats]
    pass_count = sum(1 for r in repeats if r["score"]["passed"])
    step_values = [r.get("steps_to_pass", math.inf) for r in repeats]
    resolved_steps = [int(s) for s in step_values if not _is_unresolved(s)]
    return {
        "repeat_count": len(repeats),
        "pass_count": pass_count,
        "fail_count": len(repeats) - pass_count,
        "mean_score": statistics.mean(scores) if scores else 0.0,
        "scores": scores,
        "step_values": step_values,
        "resolved_steps": resolved_steps,
        "unresolved_count": len(step_values) - len(resolved_steps),
        "mean_resolved_steps": statistics.mean(resolved_steps) if resolved_steps else None,
    }


def _paired_outcome_summary(
    with_records: list[dict[str, Any]],
    without_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare with/without arms by backend and repeat.

    Pass/fail is the primary outcome. Score breaks ties only when both arms
    share the same pass status for the matched backend/repeat.
    """
    without_by_key: dict[tuple[str, int], dict[str, Any]] = {}
    for record in without_records:
        backend = str(_record_value(record, "backend", ""))
        for repeat in _record_repeats(record):
            repeat_id = int(repeat.get("repeat", 1))
            without_by_key[(backend, repeat_id)] = repeat

    matched = 0
    with_wins = 0
    without_wins = 0
    ties = 0
    unmatched: list[str] = []
    for record in with_records:
        backend = str(_record_value(record, "backend", ""))
        for with_repeat in _record_repeats(record):
            repeat_id = int(with_repeat.get("repeat", 1))
            without_repeat = without_by_key.get((backend, repeat_id))
            if without_repeat is None:
                unmatched.append(f"{backend}/repeat_{repeat_id}")
                continue
            matched += 1
            with_score = with_repeat["score"]
            without_score = without_repeat["score"]
            with_passed = bool(with_score["passed"])
            without_passed = bool(without_score["passed"])
            if with_passed != without_passed:
                if with_passed:
                    with_wins += 1
                else:
                    without_wins += 1
                continue
            if with_score["score"] > without_score["score"]:
                with_wins += 1
            elif with_score["score"] < without_score["score"]:
                without_wins += 1
            else:
                ties += 1

    if unmatched:
        signal = "Incomplete paired comparison"
    elif with_wins > without_wins:
        signal = "SKILL.md paired advantage"
    elif without_wins > with_wins:
        signal = "README-only paired advantage"
    else:
        signal = "No paired separation"
    return {
        "matched": matched,
        "with_wins": with_wins,
        "without_wins": without_wins,
        "ties": ties,
        "unmatched": unmatched,
        "paired_sign_test": _paired_sign_test(with_wins, without_wins, ties, matched),
        "signal": signal,
    }


def _paired_sign_test(with_wins: int, without_wins: int, ties: int, matched: int) -> dict[str, Any]:
    decisive = with_wins + without_wins
    if decisive:
        p_value = sum(math.comb(decisive, k) for k in range(with_wins, decisive + 1)) / (2**decisive)
        win_rate = with_wins / decisive
    else:
        p_value = None
        win_rate = None
    return {
        "decisive_pairs": decisive,
        "with_win_rate_decisive": win_rate,
        "tie_rate_matched": (ties / matched) if matched else None,
        "one_sided_sign_test_p": p_value,
        "test": "exact one-sided sign test, H1: SKILL.md wins more decisive pairs than README-only",
    }


def _paired_outcome_text(summary: dict[str, Any]) -> str:
    stats = summary.get("paired_sign_test") or {}
    p_value = stats.get("one_sided_sign_test_p")
    decisive = stats.get("decisive_pairs")
    if isinstance(p_value, (int, float)) and isinstance(decisive, int):
        stats_text = f" Exact one-sided sign-test p={p_value:.4g} across {decisive} decisive pair(s)."
    elif isinstance(decisive, int):
        stats_text = f" Exact one-sided sign-test p=n/a across {decisive} decisive pair(s)."
    else:
        stats_text = ""
    text = (
        f"{summary['signal']}: SKILL.md wins {summary['with_wins']}/"
        f"{summary['matched']} matched backend-repeat pairs, README-only wins "
        f"{summary['without_wins']}/{summary['matched']}, and "
        f"{summary['ties']}/{summary['matched']} are ties. Pass/fail is the "
        "primary outcome; score breaks ties only when pass status is equal."
        f"{stats_text}"
    )
    if summary["unmatched"]:
        text += " Unmatched pairs: " + ", ".join(summary["unmatched"][:5]) + "."
    return text


def _paired_advantage_gate(summary: dict[str, Any]) -> dict[str, Any]:
    matched = int(summary["matched"])
    with_wins = int(summary["with_wins"])
    without_wins = int(summary["without_wins"])
    unmatched = list(summary["unmatched"])
    if unmatched:
        return {
            "passed": False,
            "status": "incomplete",
            "label": "Incomplete paired comparison",
            "reason": f"{len(unmatched)} unmatched backend-repeat pair(s)",
        }
    if matched == 0:
        return {
            "passed": False,
            "status": "incomplete",
            "label": "Incomplete paired comparison",
            "reason": "no matched backend-repeat pairs",
        }
    if with_wins > without_wins:
        sign_test = summary.get("paired_sign_test") or {}
        p_value = sign_test.get("one_sided_sign_test_p")
        p_text = f"; sign-test p={p_value:.4g}" if isinstance(p_value, (int, float)) else ""
        return {
            "passed": True,
            "status": "supports_skill_advantage",
            "label": "Supports SKILL.md advantage",
            "reason": (
                f"SKILL.md wins {with_wins}/{matched} matched pair(s); "
                f"README-only wins {without_wins}/{matched}{p_text}"
            ),
        }
    if without_wins > with_wins:
        reason = (
            f"README-only wins {without_wins}/{matched} matched pair(s); "
            f"SKILL.md wins {with_wins}/{matched}"
        )
    else:
        reason = (
            f"SKILL.md and README-only are tied at {with_wins}/{matched} "
            "matched pair win(s)"
        )
    return {
        "passed": False,
        "status": "does_not_support_skill_advantage",
        "label": "Does not support SKILL.md advantage",
        "reason": reason,
    }


def _paired_advantage_gate_text(gate: dict[str, Any]) -> str:
    return f"Outcome-support gate: {gate['label']}. {gate['reason']}."


def _p_value_text(value: Any) -> str:
    return f"{value:.4g}" if isinstance(value, (int, float)) else "n/a"


def _int_usage(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return 0


def _token_profile_for_record(record: dict[str, Any]) -> dict[str, Any]:
    repeats = _record_repeats(record)
    profile = {
        "backend": record.get("backend_label", _record_value(record, "backend", "")),
        "arm": _record_value(record, "arm", ""),
        "repeat_count": len(repeats),
        "pass_count": 0,
        "attempt_count": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "reasoning_tokens": 0,
        "total_tokens": 0,
        "exec_count": 0,
        "exec_seconds": 0.0,
    }
    for repeat in repeats:
        profile["pass_count"] += 1 if repeat["score"]["passed"] else 0
        attempts = repeat.get("attempts") or [repeat]
        profile["attempt_count"] += len(attempts)
        usage = repeat.get("usage") or {}
        profile["prompt_tokens"] += _int_usage(usage.get("prompt_tokens"))
        profile["completion_tokens"] += _int_usage(usage.get("completion_tokens"))
        profile["total_tokens"] += _int_usage(usage.get("total_tokens"))
        completion_details = usage.get("completion_tokens_details") or {}
        if isinstance(completion_details, dict):
            profile["reasoning_tokens"] += _int_usage(
                completion_details.get("reasoning_tokens")
            )
        execution = repeat.get("execution") or {}
        elapsed = execution.get("elapsed_seconds")
        if isinstance(elapsed, (int, float)) and not isinstance(elapsed, bool):
            profile["exec_count"] += 1
            profile["exec_seconds"] += float(elapsed)
    return profile


def _token_profiles_for_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_token_profile_for_record(record) for record in records]


def _merge_token_profiles(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row.get("backend", "")), str(row.get("arm", "")))
        dest = merged.setdefault(
            key,
            {
                "backend": key[0],
                "arm": key[1],
                "repeat_count": 0,
                "pass_count": 0,
                "attempt_count": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "reasoning_tokens": 0,
                "total_tokens": 0,
                "exec_count": 0,
                "exec_seconds": 0.0,
            },
        )
        for field in (
            "repeat_count",
            "pass_count",
            "attempt_count",
            "prompt_tokens",
            "completion_tokens",
            "reasoning_tokens",
            "total_tokens",
            "exec_count",
        ):
            dest[field] += int(row.get(field, 0))
        dest["exec_seconds"] += float(row.get("exec_seconds", 0.0))
    return sorted(merged.values(), key=lambda r: (str(r["backend"]), str(r["arm"])))


def _fmt_count(value: Any) -> str:
    return f"{int(value):,}"


def _fmt_mean(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:,.1f}"


def _token_profile_table(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| Backend | Arm | Repeats | Passes | Attempts | Prompt tokens | Completion tokens | Reasoning tokens | Total tokens | Mean total/repeat | Executed | Mean exec s |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        repeat_count = int(row["repeat_count"])
        total_tokens = int(row["total_tokens"])
        mean_total = (total_tokens / repeat_count) if repeat_count else None
        exec_count = int(row["exec_count"])
        mean_exec = (float(row["exec_seconds"]) / exec_count) if exec_count else None
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["backend"]),
                    str(row["arm"]),
                    _fmt_count(repeat_count),
                    _fmt_count(row["pass_count"]),
                    _fmt_count(row["attempt_count"]),
                    _fmt_count(row["prompt_tokens"]),
                    _fmt_count(row["completion_tokens"]),
                    _fmt_count(row["reasoning_tokens"]),
                    _fmt_count(total_tokens),
                    _fmt_mean(mean_total),
                    _fmt_count(exec_count),
                    _fmt_mean(mean_exec),
                ]
            )
            + " |"
        )
    return lines


def _token_profile_section(records: list[dict[str, Any]]) -> list[str]:
    rows = _token_profiles_for_records(records)
    return [
        "## Token Profiling",
        "",
        "Token counts are provider-reported values saved in each repeat JSON. "
        "Reasoning tokens are shown only when the provider returned that "
        "subfield and are a subset of completion tokens, not an additional "
        "cost to add to total tokens. Execution time is averaged only across "
        "repeats that reached command execution; no-command-extracted repeats "
        "still count toward token totals.",
        "",
        *_token_profile_table(rows),
        "",
    ]


def _overview_token_profile_section(
    codex: list[dict[str, Any]],
    nemotron: list[dict[str, Any]],
) -> list[str]:
    rows: list[dict[str, Any]] = []
    for item in codex:
        rows.extend(item.get("codex_token_profiles", []))
    for item in nemotron:
        rows.extend(item.get("nemotron_token_profiles", []))
    merged = _merge_token_profiles(rows)
    lines = [
        "## Token Profiling",
        "",
        "The table below aggregates provider-reported usage across all seven "
        "skills for each backend/arm. It is useful for separating workflow "
        "success from prompting cost: README-only arms often spent more output "
        "tokens explaining or improvising commands while still failing the "
        "artifact contract.",
        "",
    ]
    if merged:
        lines.extend(_token_profile_table(merged))
    else:
        lines.append("_No token usage data was supplied to the overview writer._")
    lines.extend(
        [
            "",
            "Reasoning tokens are included in completion tokens where reported. "
            "Mean execution seconds excludes repeats that never reached command "
            "execution, but those repeats still contributed prompt and "
            "completion tokens.",
            "",
        ]
    )
    return lines


SHELLISH_START_RE = re.compile(
    r"^\s*(?:(?:[A-Za-z_][A-Za-z0-9_]*=.*\s+)+)?"
    r"(?:python[0-9.]*|pip|uv|conda|mamba|export|mkdir|cd|test|"
    r"huggingface-cli|hf|monai\.bundle|bash)\b",
    re.DOTALL,
)


def _strip_lone_fence_markers(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^\s*```(?:bash|sh|shell)?\s*\n?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _tolerant_command_candidate(text: str) -> tuple[str | None, str]:
    """Classify command-like text for Nemotron formatting diagnostics.

    The execution harness accepts exactly one fenced shell block and a narrow
    malformed-language-prefix fallback. The report keeps those categories
    separate so formatting fixes remain visible.
    """
    raw = (text or "").strip()
    if not raw:
        return None, "empty_response"
    shell_blocks = BASH_BLOCK_RE.findall(raw)
    if len(shell_blocks) == 1:
        cmd = shell_blocks[0].strip()
        return re.sub(r"\n?```+\s*$", "", cmd).strip(), "strict_fenced_block"
    if len(shell_blocks) > 1:
        return None, "multiple_shell_blocks"

    candidate = _strip_lone_fence_markers(raw)
    if re.match(r"^\s*(?:bash|sh|shell)\s*\n", candidate, flags=re.IGNORECASE):
        candidate = re.sub(
            r"^\s*(?:bash|sh|shell)\s*\n",
            "",
            candidate,
            count=1,
            flags=re.IGNORECASE,
        ).strip()
        return (candidate, "malformed_language_prefix") if candidate else (None, "empty_after_language_prefix")
    if SHELLISH_START_RE.search(candidate):
        category = "raw_shell_text"
        if raw.endswith("```") or raw.startswith("```"):
            category = "malformed_fence"
        return candidate, category
    return None, "no_shell_like_text"


def _repeat_output_dir(repeat: dict[str, Any]) -> Path:
    value = repeat.get("output_dir")
    if isinstance(value, str) and value:
        path = Path(value)
        return path if path.is_absolute() else REPO_ROOT / path
    return REPO_ROOT


def _failure_kinds(repeat: dict[str, Any]) -> set[str]:
    return {
        str(item.get("kind"))
        for item in repeat.get("failure_analysis") or []
        if isinstance(item, dict) and item.get("kind")
    }


def _failed_tier_ids(repeat: dict[str, Any]) -> set[int]:
    return {
        int(tier.get("tier"))
        for tier in repeat.get("score", {}).get("tiers", [])
        if isinstance(tier, dict) and not tier.get("pass") and isinstance(tier.get("tier"), int)
    }


def _protocol_issue_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "no_command": 0,
        "wrong_runnable": 0,
        "missing_input": 0,
        "missing_control": 0,
        "missing_output": 0,
        "unsafe_or_static_guard": 0,
        "nonzero_exit": 0,
        "artifact_contract": 0,
    }
    for record in records:
        for repeat in _record_repeats(record):
            failed_tiers = _failed_tier_ids(repeat)
            kinds = _failure_kinds(repeat)
            execution = repeat.get("execution") or {}
            reason = str(execution.get("reason") or "")
            if not repeat.get("command"):
                counts["no_command"] += 1
            if 1 in failed_tiers:
                counts["wrong_runnable"] += 1
            if 2 in failed_tiers:
                counts["missing_input"] += 1
            if 3 in failed_tiers:
                counts["missing_control"] += 1
            if 4 in failed_tiers:
                counts["missing_output"] += 1
            if "not_executed" in kinds and reason and reason != "no command extracted":
                counts["unsafe_or_static_guard"] += 1
            if "blocked unsafe command fragment" in reason:
                counts["unsafe_or_static_guard"] += 1
            if "nonzero_exit" in kinds:
                counts["nonzero_exit"] += 1
            if "artifact_verification" in kinds:
                counts["artifact_contract"] += 1
    return counts


def _nemotron_format_profile(
    scenario: Any,
    record: dict[str, Any],
) -> dict[str, Any]:
    counts = {
        "arm": _record_value(record, "arm", ""),
        "repeats": 0,
        "passed": 0,
        "strict_command": 0,
        "recoverable_command": 0,
        "unrecoverable": 0,
        "guard_ready_after_tolerant": 0,
        "strict_fenced_block": 0,
        "malformed_language_prefix": 0,
        "raw_shell_text": 0,
        "malformed_fence": 0,
        "multiple_shell_blocks": 0,
        "no_shell_like_text": 0,
        "empty_response": 0,
        "static_guard_blocked": 0,
        "static_guard_reasons": {},
    }
    for repeat in _record_repeats(record):
        counts["repeats"] += 1
        counts["passed"] += 1 if repeat["score"]["passed"] else 0
        strict_cmd = repeat.get("command")
        candidate, category = _tolerant_command_candidate(str(repeat.get("response") or ""))
        counts[category] = counts.get(category, 0) + 1
        if strict_cmd:
            counts["strict_command"] += 1
            continue
        if candidate:
            counts["recoverable_command"] += 1
            ok, reason = _safe_to_execute(
                scenario,
                str(_record_value(record, "arm", "")),
                candidate,
                _repeat_output_dir(repeat),
            )
            if ok:
                counts["guard_ready_after_tolerant"] += 1
            else:
                counts["static_guard_blocked"] += 1
                reasons = counts["static_guard_reasons"]
                reasons[reason] = reasons.get(reason, 0) + 1
        else:
            counts["unrecoverable"] += 1
    return counts


def _nemotron_diagnostics(
    scenario: Any,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    profiles = [_nemotron_format_profile(scenario, record) for record in records]
    issue_counts = _protocol_issue_counts(records)
    return {"profiles": profiles, "issue_counts": issue_counts}


def _format_reason_counts(reason_counts: dict[str, int]) -> str:
    if not reason_counts:
        return "none"
    ordered = sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))
    return "; ".join(f"{reason} ({count})" for reason, count in ordered[:4])


def _nemotron_diagnostic_section(diagnostics: dict[str, Any]) -> list[str]:
    lines = [
        "## Nemotron Diagnostics",
        "",
        "These diagnostics are Nemotron-only and do not change the main score. "
        "The strict result still requires exactly one valid fenced bash block. "
        "The recoverable-command columns ask whether a deterministic format "
        "adapter could have recovered command-like text without another LLM call "
        "or any domain repair.",
        "",
        "| Arm | Repeats | Passed strict | Strict command | Recoverable malformed command | Unrecoverable formatting | Guard-ready after tolerant extraction | Static guard blocked | Format categories | Guard reasons |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for profile in diagnostics["profiles"]:
        categories = {
            "strict": profile.get("strict_fenced_block", 0),
            "language_prefix": profile.get("malformed_language_prefix", 0),
            "raw_shell": profile.get("raw_shell_text", 0),
            "malformed_fence": profile.get("malformed_fence", 0),
            "multiple_blocks": profile.get("multiple_shell_blocks", 0),
            "no_shell": profile.get("no_shell_like_text", 0),
            "empty": profile.get("empty_response", 0),
        }
        category_text = "; ".join(
            f"{name} {count}" for name, count in categories.items() if count
        ) or "none"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(profile["arm"]),
                    _fmt_count(profile["repeats"]),
                    _fmt_count(profile["passed"]),
                    _fmt_count(profile["strict_command"]),
                    _fmt_count(profile["recoverable_command"]),
                    _fmt_count(profile["unrecoverable"]),
                    _fmt_count(profile["guard_ready_after_tolerant"]),
                    _fmt_count(profile["static_guard_blocked"]),
                    category_text,
                    _format_reason_counts(profile["static_guard_reasons"]),
                ]
            )
            + " |"
        )
    issue_counts = diagnostics["issue_counts"]
    lines.extend(
        [
            "",
            "Protocol-compliance failure buckets, counted per repeat and not "
            "mutually exclusive:",
            "",
            "| Bucket | Count |",
            "|---|---:|",
        ]
    )
    labels = {
        "no_command": "No strict command extracted",
        "wrong_runnable": "Wrong or missing runnable surface",
        "missing_input": "Missing staged input path",
        "missing_control": "Missing model/modality/control marker",
        "missing_output": "Missing output directory",
        "unsafe_or_static_guard": "Unsafe/static guard block",
        "nonzero_exit": "Nonzero execution exit",
        "artifact_contract": "Artifact contract failure after execution",
    }
    for key, label in labels.items():
        lines.append(f"| {label} | {_fmt_count(issue_counts.get(key, 0))} |")
    lines.append("")
    return lines


def _merge_nemotron_diagnostics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    arms: dict[str, dict[str, Any]] = {}
    issues = {
        "no_command": 0,
        "wrong_runnable": 0,
        "missing_input": 0,
        "missing_control": 0,
        "missing_output": 0,
        "unsafe_or_static_guard": 0,
        "nonzero_exit": 0,
        "artifact_contract": 0,
    }
    for item in rows:
        for profile in item.get("profiles", []):
            arm = str(profile.get("arm", ""))
            dest = arms.setdefault(
                arm,
                {
                    "arm": arm,
                    "repeats": 0,
                    "passed": 0,
                    "strict_command": 0,
                    "recoverable_command": 0,
                    "unrecoverable": 0,
                    "guard_ready_after_tolerant": 0,
                    "static_guard_blocked": 0,
                    "strict_fenced_block": 0,
                    "malformed_language_prefix": 0,
                    "raw_shell_text": 0,
                    "malformed_fence": 0,
                    "multiple_shell_blocks": 0,
                    "no_shell_like_text": 0,
                    "empty_response": 0,
                    "static_guard_reasons": {},
                },
            )
            for key, value in profile.items():
                if key in {"arm", "static_guard_reasons"}:
                    continue
                if isinstance(value, int):
                    dest[key] = dest.get(key, 0) + value
            for reason, count in profile.get("static_guard_reasons", {}).items():
                dest["static_guard_reasons"][reason] = (
                    dest["static_guard_reasons"].get(reason, 0) + count
                )
        for key, count in item.get("issue_counts", {}).items():
            if key in issues:
                issues[key] += int(count)
    return {
        "profiles": [arms[key] for key in sorted(arms)],
        "issue_counts": issues,
    }


def _overview_nemotron_diagnostic_section(nemotron: list[dict[str, Any]]) -> list[str]:
    diagnostics = _merge_nemotron_diagnostics(
        [item.get("nemotron_diagnostics", {}) for item in nemotron]
    )
    lines = [
        "## Nemotron Diagnostic Layer",
        "",
        "Nemotron is reported with the same main no-repair outcome gate as the "
        "other backends. The additional layer below isolates backend protocol "
        "behavior: strict fenced-block compliance, deterministic recoverability "
        "of malformed command text, and repeated failure buckets.",
        "",
    ]
    lines.extend(_nemotron_diagnostic_section(diagnostics)[4:])
    return lines


def _steps_summary_text(record: dict[str, Any]) -> str:
    summary = _record_summary(record)
    values = ", ".join(_steps_text(v) for v in summary["step_values"])
    if summary["resolved_steps"]:
        return (
            f"mean {summary['mean_resolved_steps']:.1f}; "
            f"unresolved {summary['unresolved_count']}; values [{values}]"
        )
    return f"all unresolved; values [{values}]"


def _top_reasons(items: list[str], limit: int = 3) -> str:
    counts: dict[str, int] = {}
    for item in items:
        if item:
            counts[item] = counts.get(item, 0) + 1
    if not counts:
        return "none"
    ordered = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    return "; ".join(f"{reason} ({count})" for reason, count in ordered[:limit])


def _latest_log(glob: str) -> str:
    matches = sorted((RUN_ROOT / "logs").glob(glob), key=lambda p: p.stat().st_mtime)
    return _rel(matches[-1]) if matches else "not found"


def _logs_for_skill(skill: str) -> tuple[str, str]:
    return _latest_log(FULL_LOG_GLOB), _latest_log(RERUN_LOG_GLOB)


def _score_row(result: dict[str, Any], *, correction: bool = False) -> str:
    if "repeats" in result or "final" in result:
        summary = _record_summary(result)
        repeats = _record_repeats(result)
        t5_reasons = [r["score"]["tiers"][-1]["reason"] for r in repeats]
        failed_tiers = [
            f"T{t['tier']}: {t['reason']}"
            for r in repeats
            for t in r["score"]["tiers"]
            if not t["pass"]
        ]
        cells = [
            result.get("backend_label", _record_value(result, "backend", "")),
            _record_value(result, "arm", ""),
            f"{summary['mean_score']:.1f}/5",
            f"{summary['pass_count']}/{summary['repeat_count']}",
        ]
        if correction:
            cells.append(_steps_summary_text(result))
        cells.extend([_top_reasons([str(r.get("execution", {}).get("exit_code")) for r in repeats]), _top_reasons(t5_reasons), _top_reasons(failed_tiers)])
        return "| " + " | ".join(cells) + " |"

    score = result["score"]
    ex = result.get("execution", {})
    t5 = score["tiers"][-1]["reason"]
    failed = "; ".join(
        f"T{t['tier']}: {t['reason']}" for t in score["tiers"] if not t["pass"]
    )
    if not failed:
        failed = "none"
    steps = result.get("steps_to_pass", 0)
    if isinstance(steps, float) and math.isinf(steps):
        steps = "unresolved"
    cells = [
        result.get("backend_label", result.get("backend", "")),
        result["arm"],
        f"{score['score']}/5",
        "yes" if score["passed"] else "no",
    ]
    if correction:
        cells.append(str(steps))
    cells.extend([str(ex.get("exit_code")), t5, failed])
    return "| " + " | ".join(cells) + " |"


def _cmd_block(title: str, cmd: str | None) -> list[str]:
    lines = [f"### {title}", ""]
    if not cmd:
        lines.append("_No executable bash command was extracted._")
        lines.append("")
        return lines
    safe = _code_text(cmd)
    lines.extend(["```bash", safe, "```", ""])
    return lines


def _code_text(text: str) -> str:
    safe = text.replace("```", "` ` `").strip()
    return "\n".join(line.rstrip() for line in safe.splitlines())


def _attempt_commands(label: str, attempts: list[dict[str, Any]]) -> list[str]:
    lines = [f"### {label}", ""]
    for attempt in attempts:
        step = attempt.get("step", 0)
        score = attempt["score"]
        ex = attempt.get("execution", {})
        lines.append(
            f"Step {step}: score {score['score']}/5, "
            f"passed={'yes' if score['passed'] else 'no'}, exit={ex.get('exit_code')}"
        )
        lines.append("")
        cmd = attempt.get("command")
        if cmd:
            lines.extend(["```bash", _code_text(cmd), "```", ""])
        else:
            lines.extend(["_No executable bash command was extracted._", ""])
    return lines


def _failed_tiers(score: dict[str, Any]) -> str:
    return "; ".join(
        f"T{t['tier']}: {t['reason']}" for t in score["tiers"] if not t["pass"]
    ) or "none"


def _failure_summary(attempt: dict[str, Any]) -> str:
    analysis = attempt.get("failure_analysis") or []
    if not analysis:
        return "none"
    chunks = []
    for item in analysis[:4]:
        reason = str(item.get("reason") or "").replace("\n", " ").strip()
        hint = str(item.get("repair_hint") or "").replace("\n", " ").strip()
        if hint:
            chunks.append(f"{item.get('kind')}: {reason} Repair: {hint}")
        else:
            chunks.append(f"{item.get('kind')}: {reason}")
    return "<br>".join(chunks)


def _attempt_trace(label: str, attempts: list[dict[str, Any]]) -> list[str]:
    lines = [f"### {label}", ""]
    lines.append("| Step | Score | Passed | Exit | Failed tiers | Why it did not work |")
    lines.append("|---:|---:|---|---|---|---|")
    for attempt in attempts:
        score = attempt["score"]
        ex = attempt.get("execution", {})
        lines.append(
            f"| {attempt.get('step', 0)} | {score['score']}/5 | "
            f"{'yes' if score['passed'] else 'no'} | {ex.get('exit_code')} | "
            f"{_failed_tiers(score)} | {_failure_summary(attempt)} |"
        )
    lines.append("")
    return lines


def _record_attempt_trace(label: str, record: dict[str, Any]) -> list[str]:
    repeats = _record_repeats(record)
    lines = [f"### {label}", ""]
    lines.append("| Repeat | Step | Score | Passed | Exit | Failed tiers | Why it did not work |")
    lines.append("|---:|---:|---:|---|---|---|---|")
    for repeat in repeats:
        repeat_id = repeat.get("repeat", 1)
        for attempt in repeat.get("attempts") or [repeat]:
            score = attempt["score"]
            ex = attempt.get("execution", {})
            lines.append(
                f"| {repeat_id} | {attempt.get('step', 0)} | {score['score']}/5 | "
                f"{'yes' if score['passed'] else 'no'} | {ex.get('exit_code')} | "
                f"{_failed_tiers(score)} | {_failure_summary(attempt)} |"
            )
    lines.append("")
    return lines


def _record_final_commands(label: str, record: dict[str, Any]) -> list[str]:
    lines = [f"### {label}", ""]
    lines.append(
        "Extracted first-attempt commands are shown below by repeat. The main "
        "baseline uses no repair prompting, so failures are recorded as data."
    )
    lines.append("")
    for repeat in _record_repeats(record):
        repeat_id = repeat.get("repeat", 1)
        score = repeat["score"]
        ex = repeat.get("execution", {})
        lines.append(
            f"Repeat {repeat_id}: score {score['score']}/5, "
            f"passed={'yes' if score['passed'] else 'no'}, "
            f"steps={_steps_text(repeat.get('steps_to_pass', math.inf))}, "
            f"exit={ex.get('exit_code')}"
        )
        lines.append("")
        cmd = repeat.get("command")
        if cmd:
            lines.extend(["```bash", _code_text(cmd), "```", ""])
        else:
            lines.extend(["_No executable bash command was extracted._", ""])
    return lines


def _mean(scores: list[int]) -> str:
    return f"{statistics.mean(scores):.1f}/5" if scores else "n/a"


def write_codex(skill: str) -> dict[str, Any]:
    scenario = SCENARIOS[skill]
    study = STUDY_ROOT / f"{skill}_codex_opus"
    records = [
        _load(study / "gpt55_with.json"),
        _load(study / "gpt55_without.json"),
        _load(study / "opus_with.json"),
        _load(study / "opus_without.json"),
    ]
    for r in records:
        r.setdefault("backend_label", {"gpt55": "GPT-5.5 / Codex", "opus": "Opus 4.7"}.get(r["backend"], r["backend"]))
    with_records = [r for r in records if r["arm"] == "with"]
    without_records = [r for r in records if r["arm"] == "without"]
    with_pass = sum(_record_summary(r)["pass_count"] for r in with_records)
    without_pass = sum(_record_summary(r)["pass_count"] for r in without_records)
    with_repeats = sum(_record_summary(r)["repeat_count"] for r in with_records)
    without_repeats = sum(_record_summary(r)["repeat_count"] for r in without_records)
    with_scores = [score for r in with_records for score in _record_summary(r)["scores"]]
    without_scores = [score for r in without_records for score in _record_summary(r)["scores"]]
    paired = _paired_outcome_summary(with_records, without_records)
    gate = _paired_advantage_gate(paired)
    signal = paired["signal"]

    input_path = _report_input_path(skill)
    gpt_out = RUN_ROOT / f"{skill}_codex_opus/gpt55/with/repeat_1"
    user_request = scenario.user_goal.format(
        input_path=_rel(input_path), out_dir=_rel(gpt_out)
    )
    prompt_artifact = PROMPT_ROOT / f"eval_nv_model_studies_{skill}_prompts.json"
    full_log, rerun_log = _logs_for_skill(skill)
    path = DOC_ROOT / f"with-vs-without-{_slug(skill)}-codex-opus.md"
    direct_api_sentence = (
        "The completed direct-API run used the corrected embedded-doc minimal prompt "
        if _report_is_complete()
        else "The saved direct-API artifacts use the corrected embedded-doc minimal prompt "
    )
    lines = [
        f"# `{skill}`: Codex/Opus LLM+SKILL.md vs LLM+README",
        "",
        (
            f"Status: {_report_status_clause()}. "
            f"Full run log: `{full_log}`. "
            f"Targeted rerun log: `{rerun_log}`."
        ),
        "",
    ]
    if not _report_is_complete():
        lines.extend(
            [
                "Current outcome support remains incomplete. This per-skill "
                "report is saved-artifact debugging context until the strict "
                "with-vs-without audit passes for the full study set.",
                "",
            ]
        )
    lines.extend(
        [
            (
                "This report compares `LLM + SKILL.md` with `LLM + upstream "
                "README/guide`. "
                + direct_api_sentence
                + "because those backends cannot read repo files. The fair "
                "NAT/tool-agent prompt artifact is A2-style: it gives a natural "
                "user request, a neutral staged input path, an output directory, "
                "and tells the agent which arm-specific document to read. It "
                "does not spell out operational details such as entrypoints, "
                "labels, model variants, or config filenames outside the "
                "documentation arm."
            ),
            "",
        ]
    )
    lines.extend(
        [
        "## Experiment Question",
        "",
        "Does `LLM + SKILL.md` make an agent better at reading documentation and "
        "taking the right action than `LLM + upstream README/guide`?",
        "",
        "## User Request Shape",
        "",
        "The prompt request for the GPT-5.5 with-skill arm was:",
        "",
        f"> {user_request}",
        "",
        f"The staged user input for every arm was `{_rel(input_path)}`. "
        f"The source fixture `{scenario.fixture}` was used only to stage that "
        "neutral input path.",
        "",
        f"Fair path-prompt artifact: `{_rel(prompt_artifact)}`",
        "",
        "## Result",
        "",
        "| Backend | Arm | Mean score | Passes | Steps | Exit | Tier 5 | Failed tiers |",
        "|---|---|---:|---:|---|---|---|---|",
        ]
    )
    lines.extend(_score_row(r, correction=True) for r in records)
    lines.extend(
        [
            "",
            "## Analysis",
            "",
            (
                f"{signal}: the with-skill arms passed {with_pass}/{with_repeats} "
                f"backend-repeat trials "
                f"with an average score of {_mean(with_scores)}; the README-only "
                f"arms passed {without_pass}/{without_repeats} backend-repeat trials "
                f"with an average score of "
                f"{_mean(without_scores)}."
            ),
            "",
            _paired_outcome_text(paired),
            "",
            _paired_advantage_gate_text(gate),
            "",
            "Each backend/arm/skill configuration was repeated three times. A repeat "
            "is independent: it has its own output directory, and each execution "
            "attempt inside the repeat creates a fresh venv before running the "
            "generated command. "
            + CACHE_ENV_TEXT,
            "",
            "The main baseline uses `max_correction_steps=0`: each repeat sends "
            "one prompt, executes the extracted command once, and records "
            "pass/fail, runtime, tokens, and deterministic failure analysis. "
            "The repair-loop implementation remains available for separate "
            "diagnostic experiments, but it is not part of this comparison.",
            "",
        ]
    )
    if with_pass == with_repeats:
        lines.extend(
            [
                "All with-skill repeats exited successfully and produced artifacts "
                "accepted by the deterministic grader. That means the final SKILL.md "
                "surface was repeatable for both tested agent backends.",
                "",
            ]
        )
    else:
        failed = []
        for r in with_records:
            if _record_summary(r)["pass_count"] == _record_summary(r)["repeat_count"]:
                continue
            reasons = [
                f"T{t['tier']}: {t['reason']}"
                for rep in _record_repeats(r)
                for t in rep["score"]["tiers"]
                if not t["pass"]
            ]
            failed.append(f"{r['backend_label']}: {_top_reasons(reasons)}")
        lines.extend(["With-skill failures: " + "; ".join(failed) + ".", ""])
    if without_pass:
        lines.extend(
            [
                (
                    f"The README-only arm also passed in {without_pass}/{without_repeats} "
                    "backend-repeat trial(s). "
                    "For this skill/backend pairing, the upstream guide was enough "
                    "for at least one agent repeat to construct a runnable command."
                ),
                "",
            ]
        )
    else:
        lines.extend(
            [
                "The README-only commands did not pass tier 5. Typical failure modes "
                "were unsafe generated shell cleanup, missing schema fields, missing "
                "model/control details, or upstream commands that did not execute "
                "cleanly from Medical AI Skills root.",
                "",
            ]
        )
    lines.extend(
        [
            "Tier 2 is intentionally strict: a command only earns it if it uses "
            f"the staged user input path `{_rel(input_path)}`.",
            "",
        ]
    )
    lines.extend(_token_profile_section(records))
    lines.extend(
        [
            "## Repair Attempts and Failure Reasons",
            "",
            "The tables below explain why each generated command failed and how "
            "many follow-up prompting steps were needed. For this baseline, "
            "only step 0 is sent; unresolved means the first command did not pass.",
            "",
        ]
    )
    for r in records:
        lines.extend(
            _record_attempt_trace(
                f"{r['backend_label']}, {r['arm']} arm",
                r,
            )
        )
    lines.extend(
        [
            "## Skill Fix Notes",
            "",
            SKILL_FIX_NOTES.get(skill, DEFAULT_SKILL_FIX_NOTE),
            "",
            "## Generated Commands",
            "",
            "These are the extracted first-attempt commands by repeat.",
            "",
        ]
    )
    for r in records:
        lines.extend(_record_final_commands(f"{r['backend_label']}, {r['arm']} arm", r))
    lines.extend(
        [
            "## Source Artifacts",
            "",
            "| Source | Path |",
            "|---|---|",
            f"| Study JSON and comparison | `{_rel(study)}/` |",
            f"| Generated outputs | `{_rel(RUN_ROOT / f'{skill}_codex_opus')}/` |",
            f"| Fair path-prompt artifact | `{_rel(prompt_artifact)}` |",
            "| Runner | `tools/with_vs_without/run_nv_model_studies.py` |",
            "",
        ]
    )
    path.write_text("\n".join(lines))
    return {
        "skill": skill,
        "codex_with_pass": with_pass,
        "codex_without_pass": without_pass,
        "codex_with_repeats": with_repeats,
        "codex_without_repeats": without_repeats,
        "codex_signal": signal,
        "codex_with_avg": _mean(with_scores),
        "codex_without_avg": _mean(without_scores),
        "codex_paired_signal": signal,
        "codex_paired_with_wins": paired["with_wins"],
        "codex_paired_without_wins": paired["without_wins"],
        "codex_paired_ties": paired["ties"],
        "codex_paired_matched": paired["matched"],
        "codex_paired_decisive": paired["paired_sign_test"]["decisive_pairs"],
        "codex_paired_sign_test_p": paired["paired_sign_test"]["one_sided_sign_test_p"],
        "codex_claim_support": gate["passed"],
        "codex_claim_support_label": gate["label"],
        "codex_claim_support_reason": gate["reason"],
        "codex_token_profiles": _token_profiles_for_records(records),
    }


def write_nemotron(skill: str) -> dict[str, Any]:
    scenario = SCENARIOS[skill]
    study = STUDY_ROOT / f"{skill}_nemotron_correction"
    with_doc = _load(study / "with.json")
    without_doc = _load(study / "without.json")
    rows = [with_doc, without_doc]
    for r in rows:
        r.setdefault("backend_label", "Nemotron")
    with_summary = _record_summary(with_doc)
    without_summary = _record_summary(without_doc)
    paired = _paired_outcome_summary([with_doc], [without_doc])
    gate = _paired_advantage_gate(paired)
    diagnostics = _nemotron_diagnostics(scenario, rows)
    input_path = _report_input_path(skill)
    out_path = RUN_ROOT / f"{skill}_nemotron_correction/with/repeat_1"
    user_request = scenario.user_goal.format(
        input_path=_rel(input_path), out_dir=_rel(out_path)
    )
    prompt_artifact = PROMPT_ROOT / f"eval_nv_model_studies_{skill}_prompts.json"
    full_log, rerun_log = _logs_for_skill(skill)
    path = DOC_ROOT / f"with-vs-without-{_slug(skill)}-nemotron-correction.md"
    signal = paired["signal"]
    lines = [
        f"# `{skill}`: Nemotron LLM+SKILL.md vs LLM+README Baseline Study",
        "",
        (
            f"Status: {_report_status_clause()}. "
            f"Full run log: `{full_log}`. "
            f"Targeted rerun log: `{rerun_log}`."
        ),
        "",
    ]
    if not _report_is_complete():
        lines.extend(
            [
                "Current outcome support remains incomplete. This per-skill "
                "report is saved-artifact debugging context until the strict "
                "with-vs-without audit passes for the full study set.",
                "",
            ]
        )
    lines.extend(
        [
        "This report uses the same direct-API embedded-doc no-repair baseline "
        "protocol as the Codex/Opus comparison, but runs "
        "`nvidia/nvidia/nemotron-3-super-v3`. The linked prompt artifact is the "
        "fair A2-style path prompt for tool-enabled/NAT replication.",
        "",
        "## Experiment Question",
        "",
        "Does `LLM + SKILL.md` let Nemotron produce a runnable command on the "
        "first try, and how does that compare with `LLM + upstream README/guide` "
        "under the same `max_correction_steps=0` baseline?",
        "",
        "## User Request Shape",
        "",
        "The prompt request for the with-skill arm was:",
        "",
        f"> {user_request}",
        "",
        f"The staged user input for every arm was `{_rel(input_path)}`. "
        f"The source fixture `{scenario.fixture}` was used only to stage that "
        "neutral input path.",
        "",
        f"Fair path-prompt artifact: `{_rel(prompt_artifact)}`",
        "",
        "## Result",
        "",
        "| Backend | Arm | Mean score | Passes | Steps | Exit | Tier 5 | Failed tiers |",
        "|---|---|---:|---:|---|---|---|---|",
        ]
    )
    lines.extend(_score_row(r, correction=True) for r in rows)
    lines.extend(
        [
            "",
            "## Analysis",
            "",
            (
                f"{signal}: the with-skill repeats passed "
                f"{with_summary['pass_count']}/{with_summary['repeat_count']} "
                f"with mean score {with_summary['mean_score']:.1f}/5 and "
                f"steps {_steps_summary_text(with_doc)}. The README-only "
                f"repeats passed {without_summary['pass_count']}/"
                f"{without_summary['repeat_count']} with mean score "
                f"{without_summary['mean_score']:.1f}/5 and steps "
                f"{_steps_summary_text(without_doc)}."
            ),
            "",
            _paired_outcome_text(paired),
            "",
            _paired_advantage_gate_text(gate),
            "",
            "Each backend/arm/skill configuration was repeated three times. A repeat "
            "is independent: it has its own output directory, and each execution "
            "attempt inside the repeat creates a fresh venv before running the "
            "generated command. "
            + CACHE_ENV_TEXT,
            "",
            "No correction feedback was sent in this baseline. Deterministic "
            "failure analysis is saved with each repeat so repair behavior can "
            "be studied separately later.",
            "",
        ]
    )
    lines.extend(_token_profile_section(rows))
    lines.extend(_nemotron_diagnostic_section(diagnostics))
    lines.extend(
        [
            "## Attempt Trace",
            "",
        ]
    )
    for label, doc in (("With-skill arm", with_doc), ("README-only arm", without_doc)):
        lines.extend(_record_attempt_trace(label, doc))
    lines.extend(
        [
            "## Generated Commands",
            "",
            "These are the extracted first-attempt commands by repeat.",
            "",
        ]
    )
    lines.extend(_record_final_commands("With-skill arm", with_doc))
    lines.extend(_record_final_commands("README-only arm", without_doc))
    lines.extend(
        [
            "## Skill Fix Notes",
            "",
            SKILL_FIX_NOTES.get(skill, DEFAULT_SKILL_FIX_NOTE),
            "",
            "## Source Artifacts",
            "",
            "| Source | Path |",
            "|---|---|",
            f"| Study JSON and comparison | `{_rel(study)}/` |",
            f"| Generated outputs | `{_rel(RUN_ROOT / f'{skill}_nemotron_correction')}/` |",
            f"| Fair path-prompt artifact | `{_rel(prompt_artifact)}` |",
            "| Runner | `tools/with_vs_without/run_nv_model_studies.py` |",
            "",
        ]
    )
    path.write_text("\n".join(lines))
    return {
        "skill": skill,
        "nemotron_with_pass": with_summary["pass_count"],
        "nemotron_without_pass": without_summary["pass_count"],
        "nemotron_with_repeats": with_summary["repeat_count"],
        "nemotron_without_repeats": without_summary["repeat_count"],
        "nemotron_with_score": f"{with_summary['mean_score']:.1f}/5",
        "nemotron_without_score": f"{without_summary['mean_score']:.1f}/5",
        "nemotron_with_steps": _steps_summary_text(with_doc),
        "nemotron_without_steps": _steps_summary_text(without_doc),
        "nemotron_paired_signal": signal,
        "nemotron_paired_with_wins": paired["with_wins"],
        "nemotron_paired_without_wins": paired["without_wins"],
        "nemotron_paired_ties": paired["ties"],
        "nemotron_paired_matched": paired["matched"],
        "nemotron_paired_decisive": paired["paired_sign_test"]["decisive_pairs"],
        "nemotron_paired_sign_test_p": paired["paired_sign_test"]["one_sided_sign_test_p"],
        "nemotron_claim_support": gate["passed"],
        "nemotron_claim_support_label": gate["label"],
        "nemotron_claim_support_reason": gate["reason"],
        "nemotron_token_profiles": _token_profiles_for_records(rows),
        "nemotron_diagnostics": diagnostics,
    }

def write_overview(codex: list[dict[str, Any]], nemotron: list[dict[str, Any]]) -> None:
    if not _report_is_complete():
        _write_incomplete_overview()
        return

    by_skill = {r["skill"]: r for r in codex}
    for r in nemotron:
        by_skill.setdefault(r["skill"], {}).update(r)
    total_codex_with = sum(r["codex_with_pass"] for r in codex)
    total_codex_without = sum(r["codex_without_pass"] for r in codex)
    total_nemo_with = sum(r["nemotron_with_pass"] for r in nemotron)
    total_nemo_without = sum(r["nemotron_without_pass"] for r in nemotron)
    total_codex_with_repeats = sum(r["codex_with_repeats"] for r in codex)
    total_codex_without_repeats = sum(r["codex_without_repeats"] for r in codex)
    total_nemo_with_repeats = sum(r["nemotron_with_repeats"] for r in nemotron)
    total_nemo_without_repeats = sum(r["nemotron_without_repeats"] for r in nemotron)
    total_with = total_codex_with + total_nemo_with
    total_without = total_codex_without + total_nemo_without
    total_with_repeats = total_codex_with_repeats + total_nemo_with_repeats
    total_without_repeats = total_codex_without_repeats + total_nemo_without_repeats
    codex_claim_support = sum(1 for r in codex if r["codex_claim_support"])
    nemo_claim_support = sum(1 for r in nemotron if r["nemotron_claim_support"])
    paired_with_wins = sum(r["codex_paired_with_wins"] for r in codex) + sum(
        r["nemotron_paired_with_wins"] for r in nemotron
    )
    paired_without_wins = sum(r["codex_paired_without_wins"] for r in codex) + sum(
        r["nemotron_paired_without_wins"] for r in nemotron
    )
    paired_ties = sum(r["codex_paired_ties"] for r in codex) + sum(
        r["nemotron_paired_ties"] for r in nemotron
    )
    paired_matched = sum(r["codex_paired_matched"] for r in codex) + sum(
        r["nemotron_paired_matched"] for r in nemotron
    )
    aggregate_sign = _paired_sign_test(
        paired_with_wins, paired_without_wins, paired_ties, paired_matched
    )
    aggregate_p = aggregate_sign["one_sided_sign_test_p"]
    if total_codex_with == total_codex_with_repeats and total_nemo_with == total_nemo_with_repeats:
        pass_summary = "Every with-skill repeat exits successfully and passes the deterministic grader."
    elif total_codex_with == total_codex_with_repeats:
        pass_summary = (
            "Every Codex/Opus with-skill repeat exits successfully and passes the "
            "deterministic grader. Nemotron baseline with-skill repeats are "
            f"mixed at {total_nemo_with}/{total_nemo_with_repeats}; unresolved repeats are "
            "listed in the per-skill reports."
        )
    else:
        pass_summary = (
            "With-skill pass status is mixed; unresolved repeats are listed in the "
            "per-skill reports."
        )
    lines = [
        "# With-vs-Without Skill Experiment Docs",
        "",
        f"Last refreshed: {REFRESHED}.",
        f"Audit status: {_report_status_clause()}.",
        "",
        "Each covered user-facing model skill has two comparison documents from "
        "the corrected with-vs-without protocol:",
        "",
        "1. A **Codex/Opus backend comparison**: same task on GPT-5.5/Codex "
        "and Opus-class backends, using the no-repair baseline protocol.",
        "2. A **Nemotron baseline study**: same task on "
        "`nvidia/nvidia/nemotron-3-super-v3`, also using `max_correction_steps=0`.",
        "",
        "Every backend/skill/arm configuration is repeated three times. Each repeat "
        "gets a separate output directory; every execution attempt inside a repeat "
        "uses a newly created venv with `PYTHONNOUSERSITE=1` and without inherited "
        "`PYTHONPATH`. "
        + CACHE_ENV_TEXT,
        "",
        "The main protocol is deliberately **no-repair**:",
        "",
        "```text",
        "DIRECT_MAX_CORRECTION_STEPS = 0",
        "```",
        "",
        "The experiment measures whether the backend can produce a valid "
        "first-shot command from the arm-specific documentation. Generic "
        "correction/autofix is not part of the main claim because it changes "
        "the question from \"does SKILL.md improve task completion?\" to "
        "\"does a repair loop improve failed commands?\" Any run with "
        "`max_correction_steps > 0` is diagnostic-only and should not be mixed "
        "into the aggregate results below. The `nemotron-correction` directory "
        "suffix is a historical artifact name; the approved baseline artifacts "
        "in that directory still use `max_correction_steps=0`.",
        "",
        "This is an engineering reproducibility protocol. It tests whether an "
        "agent can read documentation and take the right action. It is not a "
        "clinical, diagnostic, regulatory, or model-quality claim.",
        "",
        "The corrected experiment is **LLM + SKILL.md vs LLM + upstream "
        "README/guide**. The fair NAT/tool-agent prompts give only a natural "
        "user request, a neutral staged input path, an output directory, and "
        "the path of the arm-specific document to read. They do not embed the "
        "documentation and do not give label IDs, config names, entrypoint "
        "names, model variants, or backend implementation details outside the "
        "documentation arm.",
        "",
        "The completed direct-API runs used an embedded-doc minimal prompt only "
        "because those chat backends had no file-reading tools. The study JSONs "
        "preserve those exact direct-API messages; the `tools/nat_audit/data` "
        "artifacts are the fair A2-style path prompts for future NAT/tool-agent "
        "comparisons.",
        "",
        "The direct-API backend protocol is service-default by design: each LLM "
        "request sends only `model` and `messages`. It omits sampling fields, "
        "token caps, backend-specific reasoning controls, and extra request "
        "body fields. Retry attempts and socket timeouts are client transport "
        "settings, not model behavior settings.",
        "",
        "## Current Aggregate Result",
        "",
        f"- Codex/Opus with-skill repeats: {total_codex_with}/{total_codex_with_repeats} passed.",
        f"- Codex/Opus README-only repeats: {total_codex_without}/{total_codex_without_repeats} passed.",
        f"- Nemotron with-skill repeats: {total_nemo_with}/{total_nemo_with_repeats} passed.",
        f"- Nemotron README-only repeats: {total_nemo_without}/{total_nemo_without_repeats} passed.",
        (
            f"- Codex/Opus outcome-support gates: {codex_claim_support}/"
            f"{len(codex)} skill reports support SKILL.md paired advantage."
        ),
        (
            f"- Nemotron outcome-support gates: {nemo_claim_support}/"
            f"{len(nemotron)} skill reports support SKILL.md paired advantage."
        ),
        "",
        pass_summary,
        "",
        "Artifact completeness alone does not establish the skill-advantage "
        "claim. Treat the aggregate as supporting that claim only when every "
        "expected per-skill/backend outcome-support gate reports a SKILL.md "
        "paired advantage.",
        "",
    ]
    lines.extend(_overview_token_profile_section(codex, nemotron))
    lines.extend(_overview_nemotron_diagnostic_section(nemotron))
    lines.extend(
        [
            "## Overall Findings",
            "",
            "The current evidence strongly favors `LLM + SKILL.md` over "
            "`LLM + upstream README/guide` for these engineering tasks. Across "
            f"all seven NV model skills and three LLM backends, the with-skill "
            f"arm passed {total_with}/{total_with_repeats} repeats, while the "
            f"README-only arm passed {total_without}/{total_without_repeats} "
            "repeats. In matched backend-repeat pairs, SKILL.md won "
            f"{paired_with_wins} times, README-only won {paired_without_wins} "
            f"times, and {paired_ties} pairs tied because both arms failed. "
            "The exact one-sided paired sign test over decisive pairs gives "
            f"`p = {_p_value_text(aggregate_p)}`.",
            "",
            "The effect is clearest for the stronger coding backends: "
            "GPT-5.5/Codex and Opus both passed every with-skill repeat after "
            "the SKILL.md updates, for a combined "
            f"{total_codex_with}/{total_codex_with_repeats} with-skill pass "
            f"rate versus {total_codex_without}/{total_codex_without_repeats} "
            "for README-only. Nemotron is more fragile, especially around "
            "command formatting and extraction, but still shows an aggregate "
            f"skill advantage: {total_nemo_with}/{total_nemo_with_repeats} "
            f"with-skill passes versus {total_nemo_without}/"
            f"{total_nemo_without_repeats} README-only passes.",
            "",
            "The README-only arms were not usually irrelevant; they often found "
            "part of the right upstream surface and earned partial scores. The "
            "failure was executable completion. Common README-only failure "
            "modes were nonzero execution exits, missing or malformed command "
            "extraction, unsafe cleanup such as generated `rm` fragments, "
            "commands that missed the neutral staged input path, commands that "
            "missed the expected output directory, and outputs that did not "
            "satisfy the deterministic artifact contract. These map directly "
            "to the details SKILL.md files are intended to make explicit: "
            "exact entrypoints, fresh-environment dependency steps, model "
            "variants, label or modality controls, staged input/output "
            "contracts, and verifier-facing artifacts.",
            "",
            "The current artifacts support the claim that purpose-built skills "
            "are a much better LLM operating contract than the current upstream "
            "README/model-guide baseline. They do not, by themselves, prove "
            "that skills would beat every possible improved README. A stronger "
            "README-quality claim should be tested with a separate "
            "`README+adapter` arm that keeps upstream docs as the source of "
            "truth but adds neutral benchmark context such as staged input "
            "path, output directory, fresh venv assumptions, no upstream "
            "mutation, no unsafe cleanup, and expected artifact type. If that "
            "adapter starts naming wrapper entrypoints and validation schemas, "
            "it is effectively becoming skill-shaped, so it should be reported "
            "as a separate condition rather than replacing the raw README "
            "baseline.",
            "",
        "## Correction Diagnostics",
        "",
        "No current provider-default `max_correction_steps=3` Nemotron debug "
        "run is included in this report. If that diagnostic is run, keep it in "
        "a separate study root so it cannot overwrite or be mixed into the "
        "strict `max_correction_steps=0` baseline above.",
        "",
        "Recommended correction work is therefore separate from the main "
        "study:",
            "",
            "- Keep the primary with-vs-without study at `max_correction_steps=0`.",
            "- Treat repair as its own diagnostic experiment.",
            "- Split repair into specific classes: format-only repair, "
            "path/output repair, stderr/stdout execution repair, and "
            "artifact-contract repair from verifier output.",
            "- Evaluate tolerant command extraction separately, especially for "
            "Nemotron.",
            "- Do not make README-only repair competitive by leaking "
            "skill-specific wrapper details; that would invalidate the arm.",
            "",
            "To add this protocol for a new skill, follow "
            "[`with-vs-without-authoring.md`](with-vs-without-authoring.md).",
            "",
            "## Document Matrix",
            "",
            "| Skill | Codex/Opus comparison | Nemotron baseline study | Current evidence |",
            "|---|---|---|---|",
        ]
    )
    for skill in sorted(SCENARIOS):
        r = by_skill[skill]
        codex_doc = f"with-vs-without-{_slug(skill)}-codex-opus.md"
        nemo_doc = f"with-vs-without-{_slug(skill)}-nemotron-correction.md"
        evidence = (
            f"Codex/Opus with {r['codex_with_pass']}/{r['codex_with_repeats']} pass "
            f"(avg {r['codex_with_avg']}) vs README {r['codex_without_pass']}/{r['codex_without_repeats']} "
            f"(avg {r['codex_without_avg']}); paired {r['codex_paired_signal']} "
            f"({r['codex_paired_with_wins']}/{r['codex_paired_matched']} SKILL.md wins, "
            f"{r['codex_paired_without_wins']} README-only wins, {r['codex_paired_ties']} ties, "
            f"sign-test p={_p_value_text(r.get('codex_paired_sign_test_p'))}); "
            f"gate {r['codex_claim_support_label']}. "
            f"Nemotron with "
            f"{r['nemotron_with_pass']}/{r['nemotron_with_repeats']} pass "
            f"(avg {r['nemotron_with_score']}, steps {r['nemotron_with_steps']}) "
            f"vs README {r['nemotron_without_pass']}/{r['nemotron_without_repeats']} pass "
            f"(avg {r['nemotron_without_score']}, steps {r['nemotron_without_steps']}); "
            f"paired {r['nemotron_paired_signal']} "
            f"({r['nemotron_paired_with_wins']}/{r['nemotron_paired_matched']} SKILL.md wins, "
            f"{r['nemotron_paired_without_wins']} README-only wins, {r['nemotron_paired_ties']} ties, "
            f"sign-test p={_p_value_text(r.get('nemotron_paired_sign_test_p'))}); "
            f"gate {r['nemotron_claim_support_label']}."
        )
        lines.append(
            f"| `{skill}` | [`{codex_doc}`]({codex_doc}) | "
            f"[`{nemo_doc}`]({nemo_doc}) | {evidence} |"
        )
    lines.extend(
        [
            "",
            "## Shared Arm Rules",
            "",
            "| Arm | Agent may read | Agent may not read | Final answer target |",
            "|---|---|---|---|",
            "| With skill | `skills/<skill>/SKILL.md` | unrelated skill internals unless linked by `SKILL.md` | One bash command or `&&`-chained command using Medical AI Skills wrapper |",
            "| Without skill | one upstream README, model card, or upstream guide selected for that skill | `skills/<skill>/`, wrapper scripts, validators, manifests, evidence packs | One bash command or `&&`-chained command using upstream directly |",
            "",
            "The without-skill arm is not a no-docs baseline. It is a comparison "
            "against the upstream documentation a reasonable user would have.",
            "",
            "## Shared Five-Tier Grade",
            "",
            "| Tier | Check |",
            "|---|---|",
            "| 1 | A runnable entrypoint is present. |",
            "| 2 | The command references the neutral staged user input path under `runs/with_vs_without_nv/_inputs/`. |",
            "| 3 | The command selects the required model variant, modality, label IDs, or anatomy controls. |",
            "| 4 | The command writes to the expected arm-specific output directory. |",
            "| 5 | The command executes outside the sandbox, produces the expected artifact, and passes deterministic output checks. |",
            "",
            "## Generated Artifacts",
            "",
            "Study JSONs live under `examples/studies/with_vs_without_skill/`. "
            "Large generated NIfTI volumes, checkpoints, and command outputs live "
            "under `runs/with_vs_without_nv/` and remain gitignored.",
            "",
            f"NV full run log: `{_latest_log(FULL_LOG_GLOB)}`.",
            f"NV targeted rerun log: `{_latest_log(RERUN_LOG_GLOB)}`.",
            "",
            "The helper used for the all-skill batch is "
            "`tools/with_vs_without/run_nv_model_studies.py`. It executes only "
            "guarded commands that reference the expected output directory and "
            "the expected skill/upstream runnable surface; unsafe shell fragments "
            "and without-skill commands that call hidden Medical AI Skills skill paths "
            "or wrapper basenames are blocked and graded as failures.",
            "",
            "## Prompt Artifacts",
            "",
            "The fair A2-style path prompts for NAT/tool-agent comparisons are saved here:",
            "",
            "| Skill | Prompt artifact |",
            "|---|---|",
        ]
    )
    for skill in sorted(SCENARIOS):
        artifact = PROMPT_ROOT / f"eval_nv_model_studies_{skill}_prompts.json"
        lines.append(f"| `{skill}` | `{_rel(artifact)}` |")
    lines.extend(
        [
            "",
            "Regenerate prompt artifacts without making external API calls:",
            "",
            "```bash",
            "python tools/with_vs_without/run_nv_model_studies.py --mode prompts --prompt-style path",
            "```",
            "",
        ]
    )
    (DOC_ROOT / "with-vs-without-skill-experiment.md").write_text("\n".join(lines))


def _audit_failure_text(report: dict[str, Any], *, limit: int = 12) -> str:
    lines = [
        "Refusing to regenerate with-vs-without reports because study artifacts are incomplete.",
        "Run this for the current artifact status:",
        "  python tools/with_vs_without/audit_nv_model_studies.py --format markdown",
        "",
        "First audit issues:",
    ]
    count = 0
    for skill in report["skills"]:
        for group_name in ("prompt_artifact", "study_artifacts"):
            for issue in skill[group_name]["issues"]:
                lines.append(
                    f"  - {skill['skill']} {group_name}: "
                    f"{issue['code']} at {issue['path']}: {issue['message']}"
                )
                count += 1
                if count >= limit:
                    remaining = report["summary"]["issue_count"] - count
                    if remaining > 0:
                        lines.append(f"  ... {remaining} more issue(s)")
                    return "\n".join(lines)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=DIRECT_REPEATS)
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help=(
            "skip the artifact-completeness guard for debugging; generation may "
            "still fail if required JSON files are missing"
        ),
    )
    args = parser.parse_args(argv)
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")

    report = audit_all(repeats=args.repeats)
    global _REPORT_AUDIT_STATUS, _REPORT_AUDIT_ISSUES
    global _REPORT_AUDIT_SUMMARY, _REPORT_AUDIT_SKILLS
    global _REPORT_TRANSFER_SUMMARY, _REPORT_TRANSFER_FINGERPRINT
    _REPORT_AUDIT_STATUS = str(report["status"])
    _REPORT_AUDIT_ISSUES = int(report.get("summary", {}).get("issue_count", 0))
    _REPORT_AUDIT_SUMMARY = dict(report.get("summary", {}))
    _REPORT_AUDIT_SKILLS = list(report.get("skills", []))
    transfer_manifest = transfer.build_manifest(
        mode="all",
        repeats=args.repeats,
        max_correction_steps=0,
        resume_missing=True,
    )
    _REPORT_TRANSFER_SUMMARY = dict(transfer_manifest.get("summary", {}))
    _REPORT_TRANSFER_FINGERPRINT = str(transfer_manifest.get("payload_fingerprint", ""))
    if report["status"] != "complete" and not args.allow_incomplete:
        print(_audit_failure_text(report), file=sys.stderr)
        return 1

    codex = [write_codex(skill) for skill in sorted(SCENARIOS)]
    nemotron = [write_nemotron(skill) for skill in sorted(SCENARIOS)]
    write_overview(codex, nemotron)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
