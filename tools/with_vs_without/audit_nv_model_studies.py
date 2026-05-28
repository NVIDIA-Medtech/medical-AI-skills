#!/usr/bin/env python3
"""Audit NV with-vs-without study artifacts for protocol completeness."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.with_vs_without.run_nv_model_studies import (  # noqa: E402
    BACKENDS,
    DIRECT_REPEATS,
    DIRECT_MAX_CORRECTION_STEPS,
    DIRECT_SYSTEM_PROMPT,
    EXTERNAL_LLM_DATA_TRANSFER_FLAG,
    PROMPT_ARTIFACT_ROOT,
    PROMPT_ARTIFACT_ANSWER,
    SCENARIOS,
    _documentation_records,
    _backend_protocol,
    _comparison_markdown,
    _extract_command,
    _feedback,
    _prompt,
    _repair_feedback_forbidden_markers,
    _safe_to_execute,
    STUDY_ROOT,
    _repeat_out_dir,
    _skill_doc_dir,
    _staged_input_path,
)

CODEX_OPUS_BACKENDS = ("gpt55", "opus")
ARMS = ("with", "without")
DIRECT_PROMPT_STYLE = "minimal"
PATH_PROMPT_SOURCE = "tools/with_vs_without/run_nv_model_studies.py::_path_prompt"
RUNNER_SOURCE = "tools/with_vs_without/run_nv_model_studies.py"
PROMPT_OPERATIONAL_LEAK_RE = re.compile(
    r"configs/|run_[a-z0-9_]+\.py|monai\.bundle|scripts\.|model-name|"
    r"label IDs are|required label IDs"
)
LOCAL_HOME_PATH_RE = re.compile(r"/(?:home|Users)/[^\s\"']+")
CLEAN_ENV_FLAGS = (
    "per_repeat_output_dir",
    "per_attempt_fresh_venv",
    "python_user_site_disabled",
    "host_pythonpath_removed",
    "output_dir_cleaned_before_each_attempt",
    "dependency_and_model_caches_may_be_shared",
)


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _read_json(path: Path) -> tuple[Any | None, list[dict[str, str]]]:
    if not path.exists():
        return None, [{"code": "missing_file", "path": _rel(path), "message": "file is missing"}]
    try:
        return json.loads(path.read_text()), []
    except json.JSONDecodeError as exc:
        return None, [
            {
                "code": "invalid_json",
                "path": _rel(path),
                "message": f"could not parse JSON: {exc}",
            }
        ]


def _issue(code: str, path: Path, message: str) -> dict[str, str]:
    return {"code": code, "path": _rel(path), "message": message}


def _expected_prompt_key_set(repeats: int) -> set[tuple[str, str, str, int]]:
    keys: set[tuple[str, str, str, int]] = set()
    for mode, backends in (
        ("codex-opus", CODEX_OPUS_BACKENDS),
        ("nemotron-correction", ("nemotron",)),
    ):
        for backend in backends:
            for arm in ARMS:
                for repeat in range(1, repeats + 1):
                    keys.add((mode, backend, arm, repeat))
    return keys


def _expected_skill_doc(skill: str) -> str:
    return f"skills/{skill.replace('_', '-')}/SKILL.md"


def _audit_scenario_document_contract(skill: str, path: Path) -> list[dict[str, str]]:
    scenario = SCENARIOS[skill]
    issues: list[dict[str, str]] = []
    missing_placeholders = [
        placeholder
        for placeholder in ("{input_path}", "{out_dir}")
        if placeholder not in scenario.user_goal
    ]
    if missing_placeholders:
        issues.append(
            _issue(
                "user_goal_missing_placeholders",
                path,
                (
                    "scenario.user_goal must include neutral staged input and "
                    f"output placeholders; missing {', '.join(missing_placeholders)}"
                ),
            )
        )
    expected_with_doc = _expected_skill_doc(skill)
    if scenario.with_doc != (expected_with_doc,):
        issues.append(
            _issue(
                "with_doc_contract_invalid",
                path,
                (
                    "with-skill arm must expose exactly the skill wrapper "
                    f"{expected_with_doc!r}, got {list(scenario.with_doc)!r}"
                ),
            )
        )
    if not (
        len(scenario.without_doc) == 1
        and scenario.without_doc[0].startswith("tools/with_vs_without/upstream_docs/")
    ):
        issues.append(
            _issue(
                "without_doc_contract_invalid",
                path,
                (
                    "README baseline must expose exactly one repo-local upstream "
                    "snapshot under tools/with_vs_without/upstream_docs/, got "
                    f"{list(scenario.without_doc)!r}"
                ),
            )
        )
    return issues


def _expected_prompt_out_dir(skill: str, mode: str, backend: str, arm: str, repeat: int) -> str:
    run_mode = "codex_opus" if mode == "codex-opus" else "nemotron_correction"
    return str(_repeat_out_dir(skill, run_mode, BACKENDS[backend], arm, repeat).relative_to(REPO_ROOT))


def _expected_documentation_arm(skill: str, arm: str) -> list[str]:
    scenario = SCENARIOS[skill]
    return list(scenario.with_doc if arm == "with" else scenario.without_doc)


def _expected_documentation_records(skill: str, arm: str) -> list[dict[str, Any]]:
    scenario = SCENARIOS[skill]
    return _documentation_records(scenario.with_doc if arm == "with" else scenario.without_doc)


def _expected_documentation_boundary(skill: str, arm: str) -> str:
    scenario = SCENARIOS[skill]
    if arm == "with":
        return f"Do not inspect any other files under {_skill_doc_dir(scenario)}/."
    return f"Do not read or use any files under {_skill_doc_dir(scenario)}/."


def _audit_path_prompt_question_documentation(
    skill: str,
    *,
    path: Path,
    arm: str,
    question: str,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for doc_path in _expected_documentation_arm(skill, arm):
        if doc_path not in question:
            issues.append(
                _issue(
                    "question_missing_documentation_path",
                    path,
                    f"question must name selected {arm}-arm workflow document: {doc_path}",
                )
            )
    if "Read that document." not in question:
        issues.append(
            _issue(
                "question_missing_document_read_instruction",
                path,
                "question must explicitly instruct the agent to read the selected workflow document",
            )
        )
    expected_boundary = _expected_documentation_boundary(skill, arm)
    if expected_boundary not in question:
        issues.append(
            _issue(
                "question_missing_document_boundary",
                path,
                f"question must include the {arm}-arm document boundary: {expected_boundary}",
            )
        )
    return issues


def _normalize_pair_question(skill: str, mode: str, backend: str, arm: str, repeat: int, question: str) -> str:
    """Remove the intentional arm-specific prompt differences before comparing pairs."""
    scenario = SCENARIOS[skill]
    doc_path = (scenario.with_doc if arm == "with" else scenario.without_doc)[0]
    out_dir = _expected_prompt_out_dir(skill, mode, backend, arm, repeat)
    forbidden = _expected_documentation_boundary(skill, arm)
    return (
        question.replace(doc_path, "<DOC_PATH>")
        .replace(out_dir, "<OUTPUT_DIR>")
        .replace(forbidden, "<FORBIDDEN_DOC_BOUNDARY>")
    )


def _normalize_direct_minimal_prompt(skill: str, mode: str, backend: str, arm: str, repeat: int) -> str:
    """Normalize intentional arm differences from the direct embedded-doc prompt."""
    scenario = SCENARIOS[skill]
    out_dir = _repeat_out_dir(
        skill,
        "codex_opus" if mode == "codex-opus" else "nemotron_correction",
        BACKENDS[backend],
        arm,
        repeat,
    )
    prompt = _prompt(scenario, arm, out_dir, DIRECT_PROMPT_STYLE)
    marker = "\n\nDocumentation available to you:\n"
    if marker in prompt:
        prefix, _docs = prompt.split(marker, 1)
        prompt = prefix + marker + "<DOC_TEXT>"
    out_dir_text = str(out_dir.relative_to(REPO_ROOT))
    if arm == "with":
        boundary = (
            f"Use Medical AI Skills skill documentation for {skill}; "
            "do not inspect unrelated skill internals."
        )
    else:
        boundary = (
            "Use only the upstream documentation below; do not use or mention "
            f"files under {_skill_doc_dir(scenario)}/."
        )
    return prompt.replace(out_dir_text, "<OUTPUT_DIR>").replace(boundary, "<DOC_BOUNDARY>")


def _audit_direct_minimal_prompt_pair(
    skill: str,
    *,
    path: Path,
    mode: str,
    backend: str,
    repeat: int,
) -> list[dict[str, str]]:
    pair_path = Path(f"{path}#direct_minimal/{mode}/{backend}/repeat_{repeat}")
    normalized_with = _normalize_direct_minimal_prompt(skill, mode, backend, "with", repeat)
    normalized_without = _normalize_direct_minimal_prompt(skill, mode, backend, "without", repeat)
    if normalized_with == normalized_without:
        return []
    return [
        _issue(
            "direct_minimal_prompt_pair_mismatch",
            pair_path,
            (
                "generated direct minimal with/without prompts differ outside the "
                "allowed documentation text, arm-specific documentation-boundary "
                "instruction, and output directory"
            ),
        )
    ]


def _audit_direct_minimal_prompt_prefix(
    skill: str,
    *,
    path: Path,
    mode: str,
    backend: str,
    arm: str,
    repeat: int,
) -> list[dict[str, str]]:
    scenario = SCENARIOS[skill]
    out_dir = _repeat_out_dir(
        skill,
        "codex_opus" if mode == "codex-opus" else "nemotron_correction",
        BACKENDS[backend],
        arm,
        repeat,
    )
    prompt = _prompt(scenario, arm, out_dir, DIRECT_PROMPT_STYLE)
    integrity_issues: list[dict[str, str]] = []
    for marker in ("[missing document:", "[truncated]"):
        if marker in prompt:
            integrity_issues.append(
                _issue(
                    "direct_minimal_document_unavailable_or_truncated",
                    Path(f"{path}#direct_minimal/{mode}/{backend}/{arm}/repeat_{repeat}"),
                    "direct minimal prompt must embed the full selected documentation, not a missing or truncated placeholder",
                )
            )
            break
    prefix = prompt.split("\n\nDocumentation available to you:", 1)[0]
    leaked: list[str] = []
    missing_required_paths: list[str] = []
    expected_input = str(_staged_input_path(scenario).relative_to(REPO_ROOT))
    expected_output = str(out_dir.relative_to(REPO_ROOT))
    if expected_input not in prefix:
        missing_required_paths.append("staged input")
    if expected_output not in prefix:
        missing_required_paths.append("output directory")
    source_name = Path(scenario.fixture).name
    if source_name and source_name in prefix:
        leaked.append(source_name)
    if scenario.fixture in prefix:
        leaked.append(scenario.fixture)
    for marker in scenario.tier1 + scenario.tier2:
        if marker in prefix:
            leaked.append(marker)
    marker_match = PROMPT_OPERATIONAL_LEAK_RE.search(prefix)
    if marker_match:
        leaked.append(marker_match.group(0))
    if leaked:
        integrity_issues.append(
            _issue(
                "direct_minimal_prompt_marker_leaked",
                Path(f"{path}#direct_minimal/{mode}/{backend}/{arm}/repeat_{repeat}"),
                f"direct minimal prompt prefix leaks operational markers outside documentation: {sorted(set(leaked))[:5]}",
            )
        )
    if missing_required_paths:
        integrity_issues.append(
            _issue(
                "direct_minimal_prompt_missing_task_path",
                Path(f"{path}#direct_minimal/{mode}/{backend}/{arm}/repeat_{repeat}"),
                "direct minimal prompt prefix is missing required task path(s): "
                + ", ".join(missing_required_paths),
            )
        )
    return integrity_issues


def _audit_prompt_pair(
    skill: str,
    *,
    path: Path,
    mode: str,
    backend: str,
    repeat: int,
    with_index: int,
    with_row: dict[str, Any],
    without_index: int,
    without_row: dict[str, Any],
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    invariant_fields = (
        "prompt_style",
        "system",
        "prompt_source",
        "runner",
        "staged_user_input",
        "source_fixture_used_only_for_staging",
        "correction_budget_steps",
        "repeat_count",
    )
    pair_path = Path(f"{path}#{with_index}/{without_index}")
    for field in invariant_fields:
        if with_row.get(field) != without_row.get(field):
            issues.append(
                _issue(
                    "prompt_pair_field_mismatch",
                    pair_path,
                    f"{field} differs between with and without arms for {mode}/{backend}/repeat_{repeat}",
                )
            )

    for arm, index, row in (("with", with_index, with_row), ("without", without_index, without_row)):
        expected_docs = _expected_documentation_arm(skill, arm)
        if row.get("documentation_arm") != expected_docs:
            issues.append(
                _issue(
                    "wrong_documentation_arm",
                    Path(f"{path}#{index}"),
                    f"expected documentation_arm={expected_docs!r}",
                )
            )
        expected_doc_records = _expected_documentation_records(skill, arm)
        doc_records = row.get("documentation")
        if not isinstance(doc_records, list):
            issues.append(
                _issue(
                    "missing_documentation_metadata",
                    Path(f"{path}#{index}"),
                    "prompt record must include documentation path/size/hash metadata",
                )
            )
        elif doc_records != expected_doc_records:
            issues.append(
                _issue(
                    "wrong_documentation_metadata",
                    Path(f"{path}#{index}"),
                    "documentation metadata does not match current selected workflow document files",
                )
            )
        for doc in expected_doc_records:
            if not doc.get("exists"):
                issues.append(
                    _issue(
                        "documentation_file_missing",
                        Path(f"{path}#{index}"),
                        f"selected {arm}-arm documentation is missing: {doc.get('path')}",
                    )
                )
            elif int(doc.get("byte_count") or 0) == 0:
                issues.append(
                    _issue(
                        "documentation_file_empty",
                        Path(f"{path}#{index}"),
                        f"selected {arm}-arm documentation is empty: {doc.get('path')}",
                    )
                )

    with_question = with_row.get("question")
    without_question = without_row.get("question")
    if isinstance(with_question, str) and isinstance(without_question, str):
        normalized_with = _normalize_pair_question(skill, mode, backend, "with", repeat, with_question)
        normalized_without = _normalize_pair_question(skill, mode, backend, "without", repeat, without_question)
        if normalized_with != normalized_without:
            issues.append(
                _issue(
                    "prompt_pair_question_mismatch",
                    pair_path,
                    (
                        "with/without questions differ outside the allowed documentation path, "
                        "documentation-boundary instruction, and output directory"
                    ),
                )
            )
    return issues


def audit_prompt_artifact(skill: str, *, prompt_root: Path, repeats: int) -> dict[str, Any]:
    path = prompt_root / f"eval_nv_model_studies_{skill}_prompts.json"
    contract_issues = _audit_scenario_document_contract(skill, path)
    rows, issues = _read_json(path)
    issues = contract_issues + issues
    if rows is None:
        return {"status": "incomplete", "path": _rel(path), "record_count": 0, "issues": issues}
    if not isinstance(rows, list):
        return {
            "status": "incomplete",
            "path": _rel(path),
            "record_count": 0,
            "issues": issues + [_issue("invalid_shape", path, "artifact root must be a JSON list")],
        }

    expected_keys = _expected_prompt_key_set(repeats)
    actual_keys: set[tuple[str, str, str, int]] = set()
    records_by_key: dict[tuple[str, str, str, int], tuple[int, dict[str, Any]]] = {}
    duplicate_keys: list[tuple[str, str, str, int]] = []
    ids: list[str] = []
    for index, row in enumerate(rows):
        row_path = Path(f"{path}#{index}")
        if not isinstance(row, dict):
            issues.append(_issue("invalid_record", row_path, "prompt record must be an object"))
            continue
        record_id = row.get("id")
        if isinstance(record_id, str):
            ids.append(record_id)
        key = (row.get("mode"), row.get("backend"), row.get("arm"), row.get("repeat"))
        if all(isinstance(item, str) for item in key[:3]) and isinstance(key[3], int):
            actual_keys.add(key)  # type: ignore[arg-type]
            if key in records_by_key:
                duplicate_keys.append(key)  # type: ignore[arg-type]
            else:
                records_by_key[key] = (index, row)  # type: ignore[index]
            if key in expected_keys:
                expected_out_dir = _expected_prompt_out_dir(skill, key[0], key[1], key[2], key[3])  # type: ignore[arg-type]
            else:
                expected_out_dir = None
        else:
            expected_out_dir = None
            issues.append(_issue("invalid_record_key", row_path, "mode/backend/arm/repeat are missing or invalid"))

        if row.get("skill") != skill:
            issues.append(_issue("wrong_skill", row_path, f"expected skill={skill!r}"))
        if row.get("prompt_style") != "path":
            issues.append(_issue("wrong_prompt_style", row_path, "fair tool-agent prompts must use prompt_style='path'"))
        if row.get("system") != DIRECT_SYSTEM_PROMPT:
            issues.append(_issue("wrong_system_prompt", row_path, "system prompt must match the fixed direct-study system prompt"))
        if row.get("answer") != PROMPT_ARTIFACT_ANSWER:
            issues.append(_issue("wrong_answer_template", row_path, "answer must be the fixed generic response-shape template"))
        if row.get("prompt_source") != PATH_PROMPT_SOURCE:
            issues.append(_issue("wrong_prompt_source", row_path, f"expected prompt_source={PATH_PROMPT_SOURCE!r}"))
        if row.get("runner") != RUNNER_SOURCE:
            issues.append(_issue("wrong_runner", row_path, f"expected runner={RUNNER_SOURCE!r}"))
        if row.get("correction_budget_steps") != DIRECT_MAX_CORRECTION_STEPS:
            issues.append(
                _issue(
                    "wrong_correction_budget_steps",
                    row_path,
                    f"expected correction_budget_steps={DIRECT_MAX_CORRECTION_STEPS}",
                )
            )
        backend = row.get("backend")
        if isinstance(backend, str) and backend in BACKENDS:
            expected_backend = BACKENDS[backend]
            if row.get("backend_label") != expected_backend.label:
                issues.append(_issue("wrong_backend_label", row_path, f"expected backend_label={expected_backend.label!r}"))
            if row.get("backend_model") != expected_backend.model:
                issues.append(_issue("wrong_backend_model", row_path, f"expected backend_model={expected_backend.model!r}"))
            if row.get("backend_protocol") != _backend_protocol(expected_backend):
                issues.append(
                    _issue(
                        "wrong_backend_protocol",
                        row_path,
                        "backend_protocol must match the runner backend model, endpoint, request-parameter, and retry settings",
                    )
                )
        if row.get("repeat_count") != repeats:
            issues.append(_issue("wrong_repeat_count", row_path, f"expected repeat_count={repeats}"))
        if expected_out_dir is not None and row.get("expected_output_dir") != expected_out_dir:
            issues.append(
                _issue(
                    "wrong_output_dir",
                    row_path,
                    f"expected expected_output_dir={expected_out_dir!r}",
                )
            )
        expected_staged_input = str(_staged_input_path(SCENARIOS[skill]).relative_to(REPO_ROOT))
        if row.get("staged_user_input") != expected_staged_input:
            issues.append(
                _issue(
                    "wrong_staged_input",
                    row_path,
                    f"expected staged_user_input={expected_staged_input!r}",
                )
            )
        out_dir = row.get("expected_output_dir")
        question = row.get("question")
        if not isinstance(out_dir, str) or "/repeat_" not in out_dir:
            issues.append(_issue("missing_repeat_output_dir", row_path, "expected_output_dir must include /repeat_N"))
        if not isinstance(question, str) or not isinstance(out_dir, str) or out_dir not in question:
            issues.append(_issue("question_missing_output_dir", row_path, "question must include expected_output_dir"))
        if isinstance(question, str) and expected_out_dir is not None:
            if expected_staged_input not in question:
                issues.append(
                    _issue(
                        "question_missing_staged_input",
                        row_path,
                        "question must include the neutral staged input path",
                    )
                )
            expected_question = _prompt(SCENARIOS[skill], str(key[2]), REPO_ROOT / expected_out_dir, "path")
            if question != expected_question:
                issues.append(
                    _issue(
                        "wrong_path_prompt_question",
                        row_path,
                        "question must exactly match the runner-generated path prompt for this skill/arm/repeat",
                    )
                )
            issues.extend(
                _audit_path_prompt_question_documentation(
                    skill,
                    path=row_path,
                    arm=str(key[2]),
                    question=question,
                )
            )
        if isinstance(question, str):
            marker_match = PROMPT_OPERATIONAL_LEAK_RE.search(question)
            if marker_match:
                issues.append(
                    _issue(
                        "prompt_operational_marker_leaked",
                        row_path,
                        f"question leaks operational marker {marker_match.group(0)!r} outside allowed documentation",
                    )
                )
        source_name = Path(SCENARIOS[skill].fixture).name
        staged_input = row.get("staged_user_input")
        if isinstance(question, str) and source_name in question:
            issues.append(_issue("fixture_name_leaked", row_path, "question must use the neutral staged input path"))
        if isinstance(staged_input, str) and source_name in staged_input:
            issues.append(_issue("fixture_name_leaked", row_path, "staged_user_input must use a neutral filename"))
        if row.get("source_fixture_used_only_for_staging") != SCENARIOS[skill].fixture:
            issues.append(_issue("wrong_source_fixture", row_path, "source fixture metadata does not match scenario"))
        repair_prompt = row.get("repair_prompt")
        expected_repair_fragment = (
            "Repair prompts are disabled"
            if DIRECT_MAX_CORRECTION_STEPS == 0
            else "hidden Medical AI Skills skill markers are redacted"
        )
        if not isinstance(repair_prompt, str) or expected_repair_fragment not in repair_prompt:
            issues.append(
                _issue(
                    "repair_prompt_missing_redaction_policy",
                    row_path,
                    "repair_prompt metadata must match the current baseline/repair protocol",
                )
            )

    expected_count = len(expected_keys)
    if len(rows) != expected_count:
        issues.append(_issue("wrong_record_count", path, f"expected {expected_count} records, found {len(rows)}"))
    duplicate_ids = sorted({item for item in ids if ids.count(item) > 1})
    if duplicate_ids:
        issues.append(_issue("duplicate_ids", path, f"duplicate ids: {', '.join(duplicate_ids[:5])}"))
    if duplicate_keys:
        sample = ", ".join(str(item) for item in sorted(set(duplicate_keys))[:5])
        issues.append(_issue("duplicate_prompt_keys", path, f"duplicate prompt keys: {sample}"))
    missing_keys = expected_keys - actual_keys
    extra_keys = actual_keys - expected_keys
    if missing_keys:
        sample = ", ".join(str(item) for item in sorted(missing_keys)[:5])
        issues.append(_issue("missing_prompt_records", path, f"missing prompt records: {sample}"))
    if extra_keys:
        sample = ", ".join(str(item) for item in sorted(extra_keys)[:5])
        issues.append(_issue("extra_prompt_records", path, f"unexpected prompt records: {sample}"))
    for mode, backends in (
        ("codex-opus", CODEX_OPUS_BACKENDS),
        ("nemotron-correction", ("nemotron",)),
    ):
        for backend in backends:
            for repeat in range(1, repeats + 1):
                with_key = (mode, backend, "with", repeat)
                without_key = (mode, backend, "without", repeat)
                with_entry = records_by_key.get(with_key)
                without_entry = records_by_key.get(without_key)
                if with_entry is None or without_entry is None:
                    continue
                with_index, with_row = with_entry
                without_index, without_row = without_entry
                issues.extend(
                    _audit_prompt_pair(
                        skill,
                        path=path,
                        mode=mode,
                        backend=backend,
                        repeat=repeat,
                        with_index=with_index,
                        with_row=with_row,
                        without_index=without_index,
                        without_row=without_row,
                    )
                )
                issues.extend(
                    _audit_direct_minimal_prompt_pair(
                        skill,
                        path=path,
                        mode=mode,
                        backend=backend,
                        repeat=repeat,
                    )
                )
                for arm in ARMS:
                    issues.extend(
                        _audit_direct_minimal_prompt_prefix(
                            skill,
                            path=path,
                            mode=mode,
                            backend=backend,
                            arm=arm,
                            repeat=repeat,
                        )
                    )

    return {
        "status": "complete" if not issues else "incomplete",
        "path": _rel(path),
        "record_count": len(rows),
        "expected_record_count": expected_count,
        "issues": issues,
    }


def _repeat_output_dir(skill: str, mode: str, backend: str, arm: str, repeat: int) -> str:
    run_mode = "codex_opus" if mode == "codex-opus" else "nemotron_correction"
    return str(_repeat_out_dir(skill, run_mode, BACKENDS[backend], arm, repeat).relative_to(REPO_ROOT))


def _scores_match(left: Any, right: Any) -> bool:
    if not isinstance(left, dict) or not isinstance(right, dict):
        return False
    return left.get("passed") == right.get("passed") and left.get("score") == right.get("score")


def _record_repeats(record: dict[str, Any]) -> list[dict[str, Any]]:
    repeats = record.get("repeats")
    if isinstance(repeats, list):
        return [repeat for repeat in repeats if isinstance(repeat, dict)]
    return []


def _records_by_backend_repeat(records: list[dict[str, Any]]) -> dict[tuple[str, int], dict[str, Any]]:
    indexed: dict[tuple[str, int], dict[str, Any]] = {}
    for record in records:
        backend = str(record.get("backend") or "")
        for repeat in _record_repeats(record):
            repeat_id = repeat.get("repeat")
            if isinstance(repeat_id, int):
                indexed[(backend, repeat_id)] = repeat
    return indexed


def _score_passed_and_value(repeat: dict[str, Any]) -> tuple[bool, float] | None:
    score = repeat.get("score")
    if not isinstance(score, dict):
        return None
    value = score.get("score")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return bool(score.get("passed")), float(value)


def _paired_sign_test(with_wins: int, without_wins: int, ties: int, matched: int) -> dict[str, Any]:
    """Descriptive exact paired sign-test summary for the with-skill advantage."""
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


def _paired_outcome_summary_for_mode(
    *,
    mode: str,
    with_records: list[dict[str, Any]],
    without_records: list[dict[str, Any]],
    repeats: int,
) -> dict[str, Any]:
    backends = CODEX_OPUS_BACKENDS if mode == "codex-opus" else ("nemotron",)
    with_by_key = _records_by_backend_repeat(with_records)
    without_by_key = _records_by_backend_repeat(without_records)
    matched = 0
    with_wins = 0
    without_wins = 0
    ties = 0
    unmatched: list[str] = []
    for backend in backends:
        for repeat in range(1, repeats + 1):
            key = (backend, repeat)
            with_repeat = with_by_key.get(key)
            without_repeat = without_by_key.get(key)
            label = f"{backend}/repeat_{repeat}"
            if with_repeat is None:
                unmatched.append(f"{label}/with")
                continue
            if without_repeat is None:
                unmatched.append(f"{label}/without")
                continue
            with_score = _score_passed_and_value(with_repeat)
            without_score = _score_passed_and_value(without_repeat)
            if with_score is None or without_score is None:
                unmatched.append(f"{label}/score")
                continue

            matched += 1
            with_passed, with_value = with_score
            without_passed, without_value = without_score
            if with_passed != without_passed:
                if with_passed:
                    with_wins += 1
                else:
                    without_wins += 1
                continue
            if with_value > without_value:
                with_wins += 1
            elif with_value < without_value:
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
        "mode": mode,
        "expected_pairs": len(backends) * repeats,
        "matched": matched,
        "with_wins": with_wins,
        "without_wins": without_wins,
        "ties": ties,
        "unmatched": unmatched,
        "paired_sign_test": _paired_sign_test(with_wins, without_wins, ties, matched),
        "signal": signal,
    }


def _paired_advantage_gate(summary: dict[str, Any]) -> dict[str, Any]:
    unmatched = list(summary["unmatched"])
    matched = int(summary["matched"])
    with_wins = int(summary["with_wins"])
    without_wins = int(summary["without_wins"])
    if unmatched:
        return {
            "supports_skill_advantage": False,
            "status": "incomplete",
            "label": "Incomplete paired comparison",
            "reason": f"{len(unmatched)} unmatched backend-repeat pair(s)",
        }
    if matched == 0:
        return {
            "supports_skill_advantage": False,
            "status": "incomplete",
            "label": "Incomplete paired comparison",
            "reason": "no matched backend-repeat pairs",
        }
    if with_wins > without_wins:
        sign_test = summary.get("paired_sign_test") or {}
        p_value = sign_test.get("one_sided_sign_test_p")
        p_text = f"; sign-test p={p_value:.4g}" if isinstance(p_value, (int, float)) else ""
        return {
            "supports_skill_advantage": True,
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
        "supports_skill_advantage": False,
        "status": "does_not_support_skill_advantage",
        "label": "Does not support SKILL.md advantage",
        "reason": reason,
    }


def _is_unresolved(value: Any) -> bool:
    return isinstance(value, float) and math.isinf(value) or value == "unresolved"


def _summary_from_repeats(repeat_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    scores: list[float] = []
    passed: list[bool] = []
    step_values: list[int | str] = []
    resolved_steps: list[int] = []
    for repeat in repeat_rows:
        score = repeat.get("score")
        if not isinstance(score, dict):
            return None
        value = score.get("score")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        scores.append(float(value))
        passed.append(score.get("passed") is True)
        steps = repeat.get("steps_to_pass")
        if _is_unresolved(steps):
            step_values.append("unresolved")
        elif isinstance(steps, bool) or not isinstance(steps, (int, float)):
            return None
        else:
            step = int(steps)
            step_values.append(step)
            resolved_steps.append(step)
    return {
        "pass_count": sum(1 for item in passed if item),
        "fail_count": sum(1 for item in passed if not item),
        "mean_score": (sum(scores) / len(scores)) if scores else None,
        "scores": [int(score) if float(score).is_integer() else score for score in scores],
        "steps_to_pass": {
            "resolved_count": len(resolved_steps),
            "unresolved_count": len(step_values) - len(resolved_steps),
            "mean_resolved": (sum(resolved_steps) / len(resolved_steps)) if resolved_steps else None,
            "min_resolved": min(resolved_steps) if resolved_steps else None,
            "max_resolved": max(resolved_steps) if resolved_steps else None,
            "values": step_values,
        },
    }


def _values_equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(float(left), float(right), rel_tol=1e-9, abs_tol=1e-9)
    return left == right


def _validate_aggregate_summary(summary: dict[str, Any], expected: dict[str, Any], path: Path) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for key in ("pass_count", "fail_count", "mean_score", "scores"):
        if not _values_equal(summary.get(key), expected.get(key)):
            issues.append(
                _issue(
                    f"wrong_summary_{key}",
                    path,
                    f"summary.{key} must match the aggregate repeats",
                )
            )
    steps = summary.get("steps_to_pass")
    expected_steps = expected["steps_to_pass"]
    if not isinstance(steps, dict):
        issues.append(_issue("wrong_summary_steps_to_pass", path, "summary.steps_to_pass must be an object"))
        return issues
    for key in ("resolved_count", "unresolved_count", "values"):
        if not _values_equal(steps.get(key), expected_steps.get(key)):
            issues.append(
                _issue(
                    f"wrong_summary_steps_to_pass_{key}",
                    path,
                    f"summary.steps_to_pass.{key} must match the aggregate repeats",
                )
            )
    for key in ("mean_resolved", "min_resolved", "max_resolved"):
        if key in steps and not _values_equal(steps.get(key), expected_steps.get(key)):
            issues.append(
                _issue(
                    f"wrong_summary_steps_to_pass_{key}",
                    path,
                    f"summary.steps_to_pass.{key} must match the aggregate repeats",
                )
            )
    return issues


def _validate_repair_protocol(
    record: dict[str, Any],
    *,
    path: Path,
    skill: str,
    mode: str,
    backend: str,
    arm: str,
    repeat: int,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    attempts = record.get("attempts")
    if not isinstance(attempts, list):
        return issues
    if not attempts:
        issues.append(_issue("empty_attempts", path, "repeat artifact must include at least one attempt"))
        return issues

    max_steps = record.get("max_correction_steps")
    if not isinstance(max_steps, int) or max_steps < 0:
        issues.append(_issue("missing_max_correction_steps", path, "max_correction_steps must be a non-negative integer"))
    elif len(attempts) > max_steps + 1:
        issues.append(
            _issue(
                "too_many_attempts",
                path,
                f"attempts length {len(attempts)} exceeds max_correction_steps+1 ({max_steps + 1})",
            )
        )

    expected_steps = list(range(len(attempts)))
    actual_steps = [attempt.get("step") if isinstance(attempt, dict) else None for attempt in attempts]
    if actual_steps != expected_steps:
        issues.append(_issue("wrong_attempt_steps", path, f"expected attempt step sequence {expected_steps}, got {actual_steps}"))

    for index, attempt in enumerate(attempts):
        attempt_path = Path(f"{path}#attempts[{index}]")
        if not isinstance(attempt, dict):
            issues.append(_issue("invalid_attempt_shape", attempt_path, "attempt must be an object"))
            continue
        if attempt.get("backend") != backend:
            issues.append(_issue("wrong_attempt_backend", attempt_path, f"expected backend={backend!r}"))
        expected_model = BACKENDS[backend].model
        if attempt.get("model") != expected_model:
            issues.append(_issue("wrong_attempt_model", attempt_path, f"expected model={expected_model!r}"))
        if attempt.get("backend_protocol") != _backend_protocol(BACKENDS[backend]):
            issues.append(
                _issue(
                    "wrong_attempt_backend_protocol",
                    attempt_path,
                    "attempt.backend_protocol must match the runner backend protocol settings",
                )
            )
        if attempt.get("arm") != arm:
            issues.append(_issue("wrong_attempt_arm", attempt_path, f"expected arm={arm!r}"))
        if "command" not in attempt:
            issues.append(_issue("missing_attempt_command", attempt_path, "attempt.command is missing"))
        response = attempt.get("response")
        if not isinstance(response, str):
            issues.append(_issue("missing_attempt_response", attempt_path, "attempt.response must preserve the backend response text"))
        elif attempt.get("command") != _extract_command(response):
            issues.append(
                _issue(
                    "response_command_mismatch",
                    attempt_path,
                    "attempt.command must equal the command extracted from the stored backend response",
                )
            )
        if not isinstance(attempt.get("usage"), dict):
            issues.append(_issue("missing_attempt_usage", attempt_path, "attempt.usage must preserve backend usage metadata"))
        if not isinstance(attempt.get("score"), dict):
            issues.append(_issue("missing_attempt_score", attempt_path, "attempt.score is missing"))
        execution = attempt.get("execution")
        if not isinstance(execution, dict):
            issues.append(_issue("missing_attempt_execution", attempt_path, "attempt.execution is missing"))
        else:
            expected_out_dir = _repeat_out_dir(
                skill,
                "codex_opus" if mode == "codex-opus" else "nemotron_correction",
                BACKENDS[backend],
                arm,
                repeat,
            )
            safe, reason = _safe_to_execute(SCENARIOS[skill], arm, attempt.get("command"), expected_out_dir)
            if not safe:
                if execution.get("executed") is not False or execution.get("reason") != reason:
                    issues.append(
                        _issue(
                            "execution_guard_mismatch",
                            attempt_path,
                            f"unsafe command must be recorded as not executed with reason: {reason}",
                        )
                    )
            elif execution.get("executed") is False:
                issues.append(
                    _issue(
                        "execution_guard_mismatch",
                        attempt_path,
                        "command satisfies the current execution guard but artifact records it as not executed",
                    )
                )
        messages = attempt.get("messages")
        if not isinstance(messages, list):
            issues.append(_issue("missing_attempt_messages", attempt_path, "attempt.messages must preserve the prompt history"))
            continue
        expected_message_count = 2 + 2 * index
        if len(messages) != expected_message_count:
            issues.append(
                _issue(
                    "wrong_attempt_message_count",
                    attempt_path,
                    f"expected {expected_message_count} messages for repair step {index}, got {len(messages)}",
                )
            )
        roles = [msg.get("role") if isinstance(msg, dict) else None for msg in messages]
        expected_roles = ["system", "user"] + ["assistant", "user"] * index
        if roles != expected_roles:
            issues.append(
                _issue(
                    "wrong_attempt_message_roles",
                    attempt_path,
                    f"expected message roles {expected_roles}, got {roles}",
                )
            )
        if index == 0:
            if roles[:2] != ["system", "user"]:
                issues.append(_issue("wrong_initial_message_roles", attempt_path, "initial attempt must start with system,user messages"))
            else:
                system_msg = messages[0]
                user_msg = messages[1]
                expected_out_dir = _repeat_out_dir(
                    skill,
                    "codex_opus" if mode == "codex-opus" else "nemotron_correction",
                    BACKENDS[backend],
                    arm,
                    repeat,
                )
                expected_user = _prompt(SCENARIOS[skill], arm, expected_out_dir, DIRECT_PROMPT_STYLE)
                if system_msg.get("content") != DIRECT_SYSTEM_PROMPT:
                    issues.append(
                        _issue(
                            "wrong_initial_system_prompt",
                            attempt_path,
                            "initial system prompt must match the direct-study system prompt",
                        )
                    )
                if user_msg.get("content") != expected_user:
                    issues.append(
                        _issue(
                            "wrong_initial_user_prompt",
                            attempt_path,
                            "initial user prompt must match the runner-generated minimal prompt for this skill/arm/repeat",
                        )
                    )
        else:
            previous_attempt = attempts[index - 1] if index - 1 < len(attempts) else None
            assistant_msg = messages[-2] if len(messages) >= 2 else None
            previous_response = previous_attempt.get("response") if isinstance(previous_attempt, dict) else None
            if not isinstance(previous_response, str):
                issues.append(
                    _issue(
                        "missing_attempt_response",
                        Path(f"{path}#attempts[{index - 1}]"),
                        "previous attempt must preserve the backend response used as the next assistant message",
                    )
                )
            elif not isinstance(assistant_msg, dict) or assistant_msg.get("content") != previous_response:
                issues.append(
                    _issue(
                        "attempt_response_history_mismatch",
                        attempt_path,
                        "repair attempt assistant message must equal the previous attempt response",
                    )
                )
            last_msg = messages[-1] if messages else None
            if not isinstance(last_msg, dict) or last_msg.get("role") != "user":
                issues.append(_issue("missing_repair_user_prompt", attempt_path, "repair attempt must end with a user feedback prompt"))
            else:
                content = str(last_msg.get("content") or "")
                previous_score = previous_attempt.get("score") if isinstance(previous_attempt, dict) else None
                previous_execution = previous_attempt.get("execution") if isinstance(previous_attempt, dict) else None
                if isinstance(previous_score, dict) and isinstance(previous_execution, dict):
                    try:
                        expected_feedback = _feedback(
                            previous_score,
                            previous_execution,
                            scenario=SCENARIOS[skill],
                            arm=arm,
                        )
                    except Exception as exc:  # noqa: BLE001
                        issues.append(
                            _issue(
                                "repair_prompt_uncomputable",
                                attempt_path,
                                f"could not recompute repair prompt from previous attempt: {exc}",
                            )
                        )
                    else:
                        if content != expected_feedback:
                            issues.append(
                                _issue(
                                    "repair_prompt_mismatch",
                                    attempt_path,
                                    "repair prompt must exactly match runner-generated feedback for the previous attempt",
                                )
                            )
                required_fragments = (
                    "The previous command did not pass verification",
                    "failed_tiers",
                    "exit_code",
                    "stderr_tail",
                    "stdout_tail",
                    "replacement single bash code block",
                )
                missing = [fragment for fragment in required_fragments if fragment not in content]
                if missing:
                    issues.append(
                        _issue(
                            "repair_prompt_missing_failure_context",
                            attempt_path,
                            f"repair prompt missing required failure-context fragments: {missing}",
                        )
                    )
                home_match = LOCAL_HOME_PATH_RE.search(content)
                if home_match:
                    issues.append(
                        _issue(
                            "repair_prompt_leaks_local_home_path",
                            attempt_path,
                            f"repair prompt contains unredacted local path {home_match.group(0)!r}",
                        )
                    )
                leaked = [
                    marker
                    for marker in _repair_feedback_forbidden_markers(SCENARIOS[skill], arm)
                    if marker and marker in content
                ]
                if leaked:
                    issues.append(
                        _issue(
                            "repair_prompt_leaks_workbench_skill_marker",
                            attempt_path,
                            "repair prompt leaks hidden Medical AI Skills skill marker(s) to README-only arm: "
                            f"{leaked[:5]}",
                        )
                    )

    final_attempt = attempts[-1]
    if isinstance(final_attempt, dict):
        if not _scores_match(record.get("score"), final_attempt.get("score")):
            issues.append(_issue("final_score_mismatch", path, "top-level score must match the final attempt score"))
        if record.get("command") != final_attempt.get("command"):
            issues.append(_issue("final_command_mismatch", path, "top-level command must match the final attempt command"))
        if record.get("execution") != final_attempt.get("execution"):
            issues.append(_issue("final_execution_mismatch", path, "top-level execution must match the final attempt execution"))

    pass_steps = [
        attempt.get("step")
        for attempt in attempts
        if isinstance(attempt, dict)
        and isinstance(attempt.get("score"), dict)
        and attempt["score"].get("passed") is True
    ]
    steps_to_pass = record.get("steps_to_pass")
    if pass_steps:
        if steps_to_pass != min(pass_steps):
            issues.append(_issue("wrong_steps_to_pass", path, f"expected steps_to_pass={min(pass_steps)}"))
    elif not _is_unresolved(steps_to_pass):
        issues.append(_issue("wrong_steps_to_pass", path, "unresolved repeat must record infinite or 'unresolved' steps_to_pass"))
    return issues


def _validate_repeat_record(
    record: Any,
    *,
    path: Path,
    skill: str,
    mode: str,
    backend: str,
    arm: str,
    repeat: int,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if not isinstance(record, dict):
        return [_issue("invalid_shape", path, "repeat artifact must be a JSON object")]
    if record.get("backend") != backend:
        issues.append(_issue("wrong_backend", path, f"expected backend={backend!r}"))
    expected_backend = BACKENDS[backend]
    if record.get("backend_label") != expected_backend.label:
        issues.append(_issue("wrong_backend_label", path, f"expected backend_label={expected_backend.label!r}"))
    if record.get("model") != expected_backend.model:
        issues.append(_issue("wrong_model", path, f"expected model={expected_backend.model!r}"))
    if record.get("backend_protocol") != _backend_protocol(expected_backend):
        issues.append(
            _issue(
                "wrong_backend_protocol",
                path,
                "backend_protocol must match the runner backend model, endpoint, request-parameter, and retry settings",
            )
        )
    if record.get("arm") != arm:
        issues.append(_issue("wrong_arm", path, f"expected arm={arm!r}"))
    if record.get("repeat") != repeat:
        issues.append(_issue("wrong_repeat", path, f"expected repeat={repeat}"))
    expected_out_dir = _repeat_output_dir(skill, mode, backend, arm, repeat)
    if record.get("output_dir") != expected_out_dir:
        issues.append(_issue("wrong_output_dir", path, f"expected output_dir={expected_out_dir!r}"))
    if record.get("prompt_style") != DIRECT_PROMPT_STYLE:
        issues.append(_issue("wrong_direct_prompt_style", path, f"expected prompt_style={DIRECT_PROMPT_STYLE!r}"))
    if record.get("max_correction_steps") != DIRECT_MAX_CORRECTION_STEPS:
        issues.append(_issue("wrong_max_correction_steps", path, f"expected max_correction_steps={DIRECT_MAX_CORRECTION_STEPS}"))
    expected_input = str(_staged_input_path(SCENARIOS[skill]).relative_to(REPO_ROOT))
    if record.get("staged_user_input") != expected_input:
        issues.append(_issue("wrong_staged_input", path, f"expected staged_user_input={expected_input!r}"))
    if not isinstance(record.get("attempts"), list):
        issues.append(_issue("missing_attempts", path, "repeat artifact must include attempts list"))
    else:
        issues.extend(
            _validate_repair_protocol(
                record,
                path=path,
                skill=skill,
                mode=mode,
                backend=backend,
                arm=arm,
                repeat=repeat,
            )
        )
    score = record.get("score")
    if not isinstance(score, dict):
        issues.append(_issue("missing_score", path, "repeat artifact must include score object"))
    else:
        if "passed" not in score:
            issues.append(_issue("missing_score_passed", path, "score.passed is missing"))
        if "score" not in score:
            issues.append(_issue("missing_score_value", path, "score.score is missing"))
    return issues


def _validate_aggregate_record(
    record: Any,
    *,
    path: Path,
    skill: str,
    mode: str,
    backend: str,
    arm: str,
    repeats: int,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if not isinstance(record, dict):
        return [_issue("invalid_shape", path, "aggregate artifact must be a JSON object")]

    expected_mode = "codex-opus" if mode == "codex-opus" else "nemotron-correction"
    expected_fields = {
        "skill": skill,
        "backend": backend,
        "arm": arm,
        "mode": expected_mode,
        "repeat_count": repeats,
        "prompt_style": DIRECT_PROMPT_STYLE,
        "max_correction_steps": DIRECT_MAX_CORRECTION_STEPS,
        "backend_protocol": _backend_protocol(BACKENDS[backend]),
    }
    for key, expected in expected_fields.items():
        if record.get(key) != expected:
            issues.append(_issue(f"wrong_{key}", path, f"expected {key}={expected!r}"))

    clean_env = record.get("clean_environment")
    if not isinstance(clean_env, dict):
        issues.append(_issue("missing_clean_environment", path, "clean_environment object is missing"))
    else:
        for key in CLEAN_ENV_FLAGS:
            if clean_env.get(key) is not True:
                issues.append(_issue("wrong_clean_environment", path, f"clean_environment.{key} must be true"))

    summary = record.get("summary")
    if not isinstance(summary, dict):
        issues.append(_issue("missing_summary", path, "summary object is missing"))
    else:
        scores = summary.get("scores")
        if not isinstance(scores, list) or len(scores) != repeats:
            issues.append(_issue("wrong_summary_scores", path, f"summary.scores must contain {repeats} scores"))
        for key in ("pass_count", "fail_count", "mean_score", "steps_to_pass"):
            if key not in summary:
                issues.append(_issue("missing_summary_key", path, f"summary.{key} is missing"))

    repeat_rows = record.get("repeats")
    if not isinstance(repeat_rows, list) or len(repeat_rows) != repeats:
        issues.append(_issue("wrong_repeats", path, f"repeats must contain {repeats} records"))
        return issues
    for repeat, repeat_record in enumerate(repeat_rows, start=1):
        issues.extend(
            _validate_repeat_record(
                repeat_record,
                path=Path(f"{path}#repeats[{repeat - 1}]"),
                skill=skill,
                mode=mode,
                backend=backend,
                arm=arm,
                repeat=repeat,
            )
        )
    if isinstance(summary, dict):
        expected_summary = _summary_from_repeats(repeat_rows)
        if expected_summary is None:
            issues.append(
                _issue(
                    "aggregate_summary_uncomputable",
                    path,
                    "could not recompute summary from aggregate repeats because repeat score or steps_to_pass fields are invalid",
                )
            )
        else:
            issues.extend(_validate_aggregate_summary(summary, expected_summary, path))
    return issues


def _study_checks_for_mode(mode: str) -> list[tuple[str, str, str]]:
    if mode == "codex-opus":
        return [
            (backend, arm, f"{backend}_{arm}.json")
            for backend in CODEX_OPUS_BACKENDS
            for arm in ARMS
        ]
    return [("nemotron", arm, f"{arm}.json") for arm in ARMS]


def _study_dir_for_mode(study_root: Path, skill: str, mode: str) -> Path:
    if mode == "codex-opus":
        return study_root / f"{skill}_codex_opus"
    return study_root / f"{skill}_nemotron_correction"


def _comparison_title(skill: str, mode: str) -> str:
    if mode == "codex-opus":
        return f"{skill}: Codex/Opus with-vs-without"
    return f"{skill}: Nemotron baseline study"


def audit_study_artifacts(skill: str, *, study_root: Path, repeats: int) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    mode_records: list[dict[str, Any]] = []
    for mode in ("codex-opus", "nemotron-correction"):
        mode_issues: list[dict[str, str]] = []
        checks = _study_checks_for_mode(mode)
        study_dir = _study_dir_for_mode(study_root, skill, mode)
        mode_paths: list[str] = []
        aggregate_rows: list[dict[str, Any]] = []
        comparison = study_dir / "comparison.md"
        if not comparison.exists():
            mode_issues.append(_issue("missing_comparison", comparison, "comparison.md is missing"))
        else:
            mode_paths.append(_rel(comparison))

        for backend, arm, filename in checks:
            aggregate_path = study_dir / filename
            mode_paths.append(_rel(aggregate_path))
            aggregate, read_issues = _read_json(aggregate_path)
            mode_issues.extend(read_issues)
            aggregate_repeats = aggregate.get("repeats") if isinstance(aggregate, dict) else None
            if aggregate is not None:
                if isinstance(aggregate, dict):
                    aggregate_rows.append(aggregate)
                mode_issues.extend(
                    _validate_aggregate_record(
                        aggregate,
                        path=aggregate_path,
                        skill=skill,
                        mode=mode,
                        backend=backend,
                        arm=arm,
                        repeats=repeats,
                    )
                )

            for repeat in range(1, repeats + 1):
                if mode == "codex-opus":
                    repeat_name = f"{backend}_{arm}_repeat_{repeat}.json"
                else:
                    repeat_name = f"{arm}_repeat_{repeat}.json"
                repeat_path = study_dir / "repeats" / repeat_name
                mode_paths.append(_rel(repeat_path))
                repeat_record, read_issues = _read_json(repeat_path)
                mode_issues.extend(read_issues)
                if repeat_record is not None:
                    mode_issues.extend(
                        _validate_repeat_record(
                            repeat_record,
                            path=repeat_path,
                            skill=skill,
                            mode=mode,
                            backend=backend,
                            arm=arm,
                            repeat=repeat,
                        )
                    )
                if (
                    isinstance(aggregate_repeats, list)
                    and repeat - 1 < len(aggregate_repeats)
                    and isinstance(aggregate_repeats[repeat - 1], dict)
                    and isinstance(repeat_record, dict)
                    and aggregate_repeats[repeat - 1] != repeat_record
                ):
                    mode_issues.append(
                        _issue(
                            "aggregate_repeat_mismatch",
                            repeat_path,
                            "aggregate repeats entry must exactly match the corresponding per-repeat artifact",
                        )
                    )

        if comparison.exists() and len(aggregate_rows) == len(checks):
            try:
                expected_comparison = _comparison_markdown(_comparison_title(skill, mode), aggregate_rows)
            except Exception as exc:  # noqa: BLE001
                mode_issues.append(
                    _issue(
                        "comparison_uncomputable",
                        comparison,
                        f"could not recompute comparison.md from aggregate JSON: {exc}",
                    )
                )
            else:
                if comparison.read_text() != expected_comparison:
                    mode_issues.append(
                        _issue(
                            "stale_comparison",
                            comparison,
                            "comparison.md must exactly match the markdown regenerated from current aggregate JSON",
                        )
                    )

        issues.extend(mode_issues)
        mode_records.append(
            {
                "mode": mode,
                "status": "complete" if not mode_issues else "incomplete",
                "study_dir": _rel(study_dir),
                "expected_files": len(mode_paths),
                "issue_count": len(mode_issues),
            }
        )

    return {"status": "complete" if not issues else "incomplete", "modes": mode_records, "issues": issues}


def audit_outcome_support(skill: str, *, study_root: Path, repeats: int) -> dict[str, Any]:
    """Report whether complete artifacts support the SKILL.md advantage claim."""
    study_audit = audit_study_artifacts(skill, study_root=study_root, repeats=repeats)
    study_mode_status = {
        mode.get("mode"): mode
        for mode in study_audit.get("modes", [])
        if isinstance(mode, dict)
    }
    modes: list[dict[str, Any]] = []
    for mode in ("codex-opus", "nemotron-correction"):
        study_dir = _study_dir_for_mode(study_root, skill, mode)
        with_records: list[dict[str, Any]] = []
        without_records: list[dict[str, Any]] = []
        load_problems: list[str] = []
        for backend, arm, filename in _study_checks_for_mode(mode):
            aggregate_path = study_dir / filename
            aggregate, read_issues = _read_json(aggregate_path)
            if read_issues:
                load_problems.extend(issue["message"] for issue in read_issues)
                continue
            if not isinstance(aggregate, dict):
                load_problems.append(f"{_rel(aggregate_path)} is not a JSON object")
                continue
            if arm == "with":
                with_records.append(aggregate)
            else:
                without_records.append(aggregate)

        summary = _paired_outcome_summary_for_mode(
            mode=mode,
            with_records=with_records,
            without_records=without_records,
            repeats=repeats,
        )
        gate = _paired_advantage_gate(summary)
        if load_problems and gate["status"] != "incomplete":
            gate = {
                "supports_skill_advantage": False,
                "status": "incomplete",
                "label": "Incomplete paired comparison",
                "reason": "; ".join(load_problems[:3]),
            }
        mode_status = study_mode_status.get(mode)
        if isinstance(mode_status, dict) and mode_status.get("status") != "complete":
            gate = {
                "supports_skill_advantage": False,
                "status": "incomplete",
                "label": "Incomplete paired comparison",
                "reason": (
                    f"study artifact audit for {mode} has "
                    f"{mode_status.get('issue_count', 'unknown')} issue(s)"
                ),
            }
        modes.append({**summary, **gate})

    if any(mode["status"] == "incomplete" for mode in modes):
        status = "incomplete"
    elif all(mode["supports_skill_advantage"] for mode in modes):
        status = "supports_skill_advantage"
    else:
        status = "does_not_support_skill_advantage"
    return {
        "status": status,
        "modes": modes,
        "supporting_modes": sum(1 for mode in modes if mode["supports_skill_advantage"]),
        "mode_count": len(modes),
    }


def audit_skill(skill: str, *, prompt_root: Path, study_root: Path, repeats: int) -> dict[str, Any]:
    prompt = audit_prompt_artifact(skill, prompt_root=prompt_root, repeats=repeats)
    study = audit_study_artifacts(skill, study_root=study_root, repeats=repeats)
    outcome = audit_outcome_support(skill, study_root=study_root, repeats=repeats)
    complete = prompt["status"] == "complete" and study["status"] == "complete"
    return {
        "skill": skill,
        "status": "complete" if complete else "incomplete",
        "prompt_artifact": prompt,
        "study_artifacts": study,
        "outcome": outcome,
    }


def audit_all(
    *,
    skills: list[str] | None = None,
    prompt_root: Path = PROMPT_ARTIFACT_ROOT,
    study_root: Path = STUDY_ROOT,
    repeats: int = DIRECT_REPEATS,
) -> dict[str, Any]:
    selected = skills or sorted(SCENARIOS)
    skill_records = [
        audit_skill(skill, prompt_root=prompt_root, study_root=study_root, repeats=repeats)
        for skill in selected
    ]
    complete_skills = sum(1 for item in skill_records if item["status"] == "complete")
    complete_prompts = sum(1 for item in skill_records if item["prompt_artifact"]["status"] == "complete")
    complete_studies = sum(1 for item in skill_records if item["study_artifacts"]["status"] == "complete")
    outcome_support = sum(1 for item in skill_records if item["outcome"]["status"] == "supports_skill_advantage")
    outcome_complete = sum(1 for item in skill_records if item["outcome"]["status"] != "incomplete")
    status = "complete" if complete_skills == len(skill_records) else "incomplete"
    issue_count = sum(
        len(item["prompt_artifact"]["issues"]) + len(item["study_artifacts"]["issues"])
        for item in skill_records
    )
    remediation = _remediation_commands(skill_records, repeats)
    return {
        "status": status,
        "expected_repeats": repeats,
        "summary": {
            "skills": len(skill_records),
            "complete_skills": complete_skills,
            "prompt_artifacts_complete": complete_prompts,
            "study_artifacts_complete": complete_studies,
            "outcomes_complete": outcome_complete,
            "outcomes_support_skill_advantage": outcome_support,
            "issue_count": issue_count,
        },
        "remediation": remediation,
        "skills": skill_records,
    }


def _remediation_commands(skill_records: list[dict[str, Any]], repeats: int) -> list[dict[str, str]]:
    commands: list[dict[str, str]] = []
    for skill in skill_records:
        if skill["prompt_artifact"]["status"] != "complete":
            commands.append(
                {
                    "skill": skill["skill"],
                    "mode": "prompts",
                    "command": (
                        "python tools/with_vs_without/run_nv_model_studies.py "
                        f"--skills {skill['skill']} --mode prompts --prompt-style path "
                        f"--repeats {repeats}"
                    ),
                }
            )
        for mode_record in skill["study_artifacts"]["modes"]:
            if mode_record["status"] == "complete":
                continue
            mode = "codex-opus" if mode_record["mode"] == "codex-opus" else "nemotron"
            commands.append(
                {
                    "skill": skill["skill"],
                    "mode": mode,
                    "command": (
                        "python tools/with_vs_without/run_nv_model_studies.py "
                        f"--skills {skill['skill']} --mode {mode} "
                        f"--prompt-style minimal --max-correction-steps {DIRECT_MAX_CORRECTION_STEPS} "
                        f"--repeats {repeats} --resume-missing "
                        f"{EXTERNAL_LLM_DATA_TRANSFER_FLAG}"
                    ),
                }
            )
    return commands


def _issue_code_counts(issues: list[dict[str, str]], *, limit: int = 5) -> str:
    counts = Counter(issue.get("code", "unknown") for issue in issues)
    if not counts:
        return "none"
    return ", ".join(f"`{code}` x{count}" for code, count in counts.most_common(limit))


def _format_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# NV model study audit: {report['status']}",
        "",
        f"Expected repeats per backend/arm: {report['expected_repeats']}",
        "",
        "| Skill | Prompt artifact | Study artifacts | Outcome support | Issues |",
        "|---|---|---|---|---:|",
    ]
    for skill in report["skills"]:
        issues = len(skill["prompt_artifact"]["issues"]) + len(skill["study_artifacts"]["issues"])
        outcome = skill["outcome"]["status"]
        if skill["outcome"].get("status") != "incomplete" and skill["outcome"].get("modes"):
            sign_tests = []
            for mode in skill["outcome"]["modes"]:
                stats = mode.get("paired_sign_test") or {}
                p_value = stats.get("one_sided_sign_test_p")
                decisive = stats.get("decisive_pairs")
                if isinstance(p_value, (int, float)) and isinstance(decisive, int):
                    sign_tests.append(f"{mode['mode']} sign-test p={p_value:.4g}, decisive={decisive}")
                elif isinstance(decisive, int):
                    sign_tests.append(f"{mode['mode']} sign-test p=n/a, decisive={decisive}")
            if sign_tests:
                outcome += " (" + "; ".join(sign_tests) + ")"
        lines.append(
            "| "
            + " | ".join(
                [
                    skill["skill"],
                    skill["prompt_artifact"]["status"],
                    skill["study_artifacts"]["status"],
                    outcome,
                    str(issues),
                ]
            )
            + " |"
        )
    all_issues: list[dict[str, str]] = []
    for skill in report["skills"]:
        all_issues.extend(skill["prompt_artifact"]["issues"])
        all_issues.extend(skill["study_artifacts"]["issues"])
    if all_issues:
        lines.extend(
            [
                "",
                "## Issue Summary",
                "",
                "| Scope | Top issue codes |",
                "|---|---|",
                f"| all | {_issue_code_counts(all_issues)} |",
            ]
        )
        for skill in report["skills"]:
            skill_issues = skill["prompt_artifact"]["issues"] + skill["study_artifacts"]["issues"]
            if skill_issues:
                lines.append(f"| {skill['skill']} | {_issue_code_counts(skill_issues)} |")
    lines.extend(
        [
            "",
            "Outcome support is separate from artifact completeness. It supports "
            "`SKILL.md` only when the study-artifact audit is complete, "
            "every expected backend-repeat pair is present, "
            "and the with-skill arm wins more matched pairs than the README-only arm.",
            "",
            (
                f"Outcome-support gates: {report['summary']['outcomes_support_skill_advantage']}/"
                f"{report['summary']['skills']} skills support SKILL.md paired advantage; "
                f"{report['summary']['outcomes_complete']}/{report['summary']['skills']} "
                "skills have complete paired outcomes."
            ),
        ]
    )
    if report.get("remediation"):
        lines.extend(
            [
                "",
                "## Remediation Commands",
                "",
                "These commands reuse valid per-repeat JSON and run only missing or invalid repeats.",
                f"They include `{EXTERNAL_LLM_DATA_TRANSFER_FLAG}` because direct API modes send study prompts and fixture-derived task context to external LLM APIs.",
                "",
                "```bash",
            ]
        )
        lines.extend(item["command"] for item in report["remediation"])
        lines.append("```")
    return "\n".join(lines) + "\n"


def _format_commands(report: dict[str, Any]) -> str:
    commands = [item["command"] for item in report.get("remediation", [])]
    if not commands:
        return "# No remediation commands needed; study artifacts are complete.\n"
    return (
        f"# Direct API remediation commands include {EXTERNAL_LLM_DATA_TRANSFER_FLAG} "
        "because they send study prompts and fixture-derived task context to external LLM APIs.\n"
        + "\n".join(commands)
        + "\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills", nargs="*", default=None, choices=sorted(SCENARIOS))
    parser.add_argument("--repeats", type=int, default=DIRECT_REPEATS)
    parser.add_argument("--prompt-root", type=Path, default=PROMPT_ARTIFACT_ROOT)
    parser.add_argument("--study-root", type=Path, default=STUDY_ROOT)
    parser.add_argument("--strict", action="store_true", help="exit nonzero when any artifact is missing or invalid")
    parser.add_argument(
        "--require-skill-advantage",
        action="store_true",
        help="exit nonzero unless complete artifacts also support SKILL.md paired advantage for every skill",
    )
    parser.add_argument("--format", choices=["json", "markdown", "commands"], default="json")
    args = parser.parse_args(argv)
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")

    report = audit_all(
        skills=args.skills,
        prompt_root=args.prompt_root,
        study_root=args.study_root,
        repeats=args.repeats,
    )
    if args.format == "markdown":
        sys.stdout.write(_format_markdown(report))
    elif args.format == "commands":
        sys.stdout.write(_format_commands(report))
    else:
        sys.stdout.write(json.dumps(report, indent=2) + "\n")
    if args.require_skill_advantage:
        if (
            report["status"] != "complete"
            or report["summary"]["outcomes_support_skill_advantage"] != report["summary"]["skills"]
        ):
            return 1
    return 1 if args.strict and report["status"] != "complete" else 0


if __name__ == "__main__":
    raise SystemExit(main())
