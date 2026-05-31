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

import json
from dataclasses import replace
from pathlib import Path

from tools.with_vs_without import audit_nv_model_studies as audit
from tools.with_vs_without import run_nv_model_studies as studies


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def _safe_marker_for_arm(skill: str, arm: str) -> str:
    scenario = studies.SCENARIOS[skill]
    if arm == "with":
        return scenario.tier1[0]
    forbidden = studies._repair_feedback_forbidden_markers(scenario, "without")
    for marker in scenario.tier1:
        if marker and not any(hidden and hidden in marker for hidden in forbidden):
            return marker
    return scenario.tier1[0]


def _repeat_record(skill: str, mode: str, backend: str, arm: str, repeat: int) -> dict[str, object]:
    score = {"passed": True, "score": 5, "tiers": []}
    run_mode = "codex_opus" if mode == "codex-opus" else "nemotron_correction"
    out_dir = studies._repeat_out_dir(skill, run_mode, studies.BACKENDS[backend], arm, repeat)
    staged_input = studies._staged_input_path(studies.SCENARIOS[skill]).relative_to(
        studies.REPO_ROOT
    )
    command = (
        f"python {_safe_marker_for_arm(skill, arm)} {staged_input} "
        f"--output-dir {out_dir.relative_to(studies.REPO_ROOT)}"
    )
    attempt = {
        "backend": backend,
        "model": studies.BACKENDS[backend].model,
        "backend_protocol": studies._backend_protocol(studies.BACKENDS[backend]),
        "arm": arm,
        "step": 0,
        "messages": [
            {"role": "system", "content": studies.DIRECT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": studies._prompt(studies.SCENARIOS[skill], arm, out_dir, "minimal"),
            },
        ],
        "response": f"```bash\n{command}\n```",
        "command": command,
        "usage": {},
        "execution": {"executed": True, "exit_code": 0, "generated_files": []},
        "score": score,
    }
    return {
        "backend": backend,
        "backend_label": studies.BACKENDS[backend].label,
        "model": studies.BACKENDS[backend].model,
        "backend_protocol": studies._backend_protocol(studies.BACKENDS[backend]),
        "arm": arm,
        "repeat": repeat,
        "output_dir": str(out_dir.relative_to(studies.REPO_ROOT)),
        "staged_user_input": str(staged_input),
        "prompt_style": audit.DIRECT_PROMPT_STYLE,
        "max_correction_steps": studies.DIRECT_MAX_CORRECTION_STEPS,
        "steps_to_pass": 0,
        "command": command,
        "execution": {"executed": True, "exit_code": 0, "generated_files": []},
        "attempts": [attempt],
        "score": score,
    }


def _aggregate_record(
    skill: str,
    mode: str,
    backend: str,
    arm: str,
    repeats: int,
) -> dict[str, object]:
    repeat_rows = [
        _repeat_record(skill, mode, backend, arm, repeat) for repeat in range(1, repeats + 1)
    ]
    return {
        "backend": backend,
        "backend_label": studies.BACKENDS[backend].label,
        "model": studies.BACKENDS[backend].model,
        "backend_protocol": studies._backend_protocol(studies.BACKENDS[backend]),
        "arm": arm,
        "skill": skill,
        "mode": mode,
        "repeat_count": repeats,
        "max_correction_steps": studies.DIRECT_MAX_CORRECTION_STEPS,
        "prompt_style": audit.DIRECT_PROMPT_STYLE,
        "clean_environment": {key: True for key in audit.CLEAN_ENV_FLAGS},
        "summary": {
            "pass_count": repeats,
            "fail_count": 0,
            "mean_score": 5.0,
            "scores": [5] * repeats,
            "steps_to_pass": {
                "resolved_count": repeats,
                "unresolved_count": 0,
                "mean_resolved": 0.0,
                "min_resolved": 0,
                "max_resolved": 0,
                "values": [0] * repeats,
            },
        },
        "repeats": repeat_rows,
    }


def _write_complete_study(study_root: Path, skill: str, repeats: int) -> None:
    codex_dir = study_root / f"{skill}_codex_opus"
    nemotron_dir = study_root / f"{skill}_nemotron_correction"

    codex_rows: list[dict[str, object]] = []
    for backend in ("gpt55", "opus"):
        for arm in ("with", "without"):
            aggregate = _aggregate_record(skill, "codex-opus", backend, arm, repeats)
            codex_rows.append(aggregate)
            _write_json(codex_dir / f"{backend}_{arm}.json", aggregate)
            for repeat, row in enumerate(aggregate["repeats"], start=1):
                _write_json(codex_dir / "repeats" / f"{backend}_{arm}_repeat_{repeat}.json", row)
    (codex_dir / "comparison.md").parent.mkdir(parents=True, exist_ok=True)
    (codex_dir / "comparison.md").write_text(
        studies._comparison_markdown(f"{skill}: Codex/Opus with-vs-without", codex_rows)
    )

    nemotron_rows: list[dict[str, object]] = []
    for arm in ("with", "without"):
        aggregate = _aggregate_record(skill, "nemotron-correction", "nemotron", arm, repeats)
        nemotron_rows.append(aggregate)
        _write_json(nemotron_dir / f"{arm}.json", aggregate)
        for repeat, row in enumerate(aggregate["repeats"], start=1):
            _write_json(nemotron_dir / "repeats" / f"{arm}_repeat_{repeat}.json", row)
    (nemotron_dir / "comparison.md").parent.mkdir(parents=True, exist_ok=True)
    (nemotron_dir / "comparison.md").write_text(
        studies._comparison_markdown(f"{skill}: Nemotron baseline study", nemotron_rows)
    )


def _refresh_comparison(study_root: Path, skill: str, mode: str) -> None:
    study_dir = (
        study_root / f"{skill}_{'codex_opus' if mode == 'codex-opus' else 'nemotron_correction'}"
    )
    if mode == "codex-opus":
        rows = [
            json.loads((study_dir / f"{backend}_{arm}.json").read_text())
            for backend in ("gpt55", "opus")
            for arm in ("with", "without")
        ]
        title = f"{skill}: Codex/Opus with-vs-without"
    else:
        rows = [json.loads((study_dir / f"{arm}.json").read_text()) for arm in ("with", "without")]
        title = f"{skill}: Nemotron baseline study"
    (study_dir / "comparison.md").write_text(studies._comparison_markdown(title, rows))


def _set_arm_score(
    study_root: Path,
    skill: str,
    mode: str,
    backend: str,
    arm: str,
    *,
    passed: bool,
    score_value: int,
    repeats: int,
) -> None:
    study_dir = (
        study_root / f"{skill}_{'codex_opus' if mode == 'codex-opus' else 'nemotron_correction'}"
    )
    aggregate_name = f"{backend}_{arm}.json" if mode == "codex-opus" else f"{arm}.json"
    aggregate_path = study_dir / aggregate_name
    aggregate = json.loads(aggregate_path.read_text())
    score = {"passed": passed, "score": score_value, "tiers": []}
    for repeat_index, repeat in enumerate(aggregate["repeats"], start=1):
        repeat["score"] = score
        repeat["attempts"][0]["score"] = score
        repeat["steps_to_pass"] = 0 if passed else "unresolved"
        repeat_name = (
            f"{backend}_{arm}_repeat_{repeat_index}.json"
            if mode == "codex-opus"
            else f"{arm}_repeat_{repeat_index}.json"
        )
        repeat_path = study_dir / "repeats" / repeat_name
        repeat_file = json.loads(repeat_path.read_text())
        repeat_file["score"] = score
        repeat_file["attempts"][0]["score"] = score
        repeat_file["steps_to_pass"] = 0 if passed else "unresolved"
        _write_json(repeat_path, repeat_file)

    aggregate["summary"] = {
        "pass_count": repeats if passed else 0,
        "fail_count": 0 if passed else repeats,
        "mean_score": float(score_value),
        "scores": [score_value] * repeats,
        "steps_to_pass": {
            "resolved_count": repeats if passed else 0,
            "unresolved_count": 0 if passed else repeats,
            "mean_resolved": 0.0 if passed else None,
            "min_resolved": 0 if passed else None,
            "max_resolved": 0 if passed else None,
            "values": [0 if passed else "unresolved"] * repeats,
        },
    }
    _write_json(aggregate_path, aggregate)
    _refresh_comparison(study_root, skill, mode)


def test_audit_all_accepts_complete_synthetic_artifacts(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    repeats = 2
    prompt_root = tmp_path / "prompts"
    study_root = tmp_path / "studies"
    prompt_root.mkdir()
    _write_json(
        prompt_root / f"eval_nv_model_studies_{skill}_prompts.json",
        studies._prompt_artifact_records(
            skill, "path", max_steps=studies.DIRECT_MAX_CORRECTION_STEPS, repeats=repeats
        ),
    )
    _write_complete_study(study_root, skill, repeats)

    report = audit.audit_all(
        skills=[skill], prompt_root=prompt_root, study_root=study_root, repeats=repeats
    )

    assert report["status"] == "complete"
    assert report["summary"]["complete_skills"] == 1
    assert report["summary"]["issue_count"] == 0
    assert report["summary"]["outcomes_complete"] == 1
    assert report["summary"]["outcomes_support_skill_advantage"] == 0
    assert report["skills"][0]["outcome"]["status"] == "does_not_support_skill_advantage"
    codex_stats = report["skills"][0]["outcome"]["modes"][0]["paired_sign_test"]
    assert codex_stats["decisive_pairs"] == 0
    assert codex_stats["one_sided_sign_test_p"] is None
    assert report["remediation"] == []


def test_audit_all_reports_skill_advantage_outcome_when_with_arm_wins(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    repeats = 2
    prompt_root = tmp_path / "prompts"
    study_root = tmp_path / "studies"
    prompt_root.mkdir()
    _write_json(
        prompt_root / f"eval_nv_model_studies_{skill}_prompts.json",
        studies._prompt_artifact_records(
            skill, "path", max_steps=studies.DIRECT_MAX_CORRECTION_STEPS, repeats=repeats
        ),
    )
    _write_complete_study(study_root, skill, repeats)
    for backend in ("gpt55", "opus"):
        _set_arm_score(
            study_root,
            skill,
            "codex-opus",
            backend,
            "without",
            passed=False,
            score_value=3,
            repeats=repeats,
        )
    _set_arm_score(
        study_root,
        skill,
        "nemotron-correction",
        "nemotron",
        "without",
        passed=False,
        score_value=3,
        repeats=repeats,
    )

    report = audit.audit_all(
        skills=[skill], prompt_root=prompt_root, study_root=study_root, repeats=repeats
    )

    assert report["status"] == "complete"
    assert report["summary"]["issue_count"] == 0
    assert report["summary"]["outcomes_support_skill_advantage"] == 1
    assert report["skills"][0]["outcome"]["status"] == "supports_skill_advantage"
    assert all(mode["supports_skill_advantage"] for mode in report["skills"][0]["outcome"]["modes"])
    codex_stats = report["skills"][0]["outcome"]["modes"][0]["paired_sign_test"]
    assert codex_stats["decisive_pairs"] == 4
    assert codex_stats["with_win_rate_decisive"] == 1.0
    assert codex_stats["one_sided_sign_test_p"] == 0.0625
    nemo_stats = report["skills"][0]["outcome"]["modes"][1]["paired_sign_test"]
    assert nemo_stats["decisive_pairs"] == 2
    assert nemo_stats["one_sided_sign_test_p"] == 0.25


def test_outcome_support_requires_valid_study_artifacts(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    repeats = 2
    prompt_root = tmp_path / "prompts"
    study_root = tmp_path / "studies"
    prompt_root.mkdir()
    _write_json(
        prompt_root / f"eval_nv_model_studies_{skill}_prompts.json",
        studies._prompt_artifact_records(
            skill, "path", max_steps=studies.DIRECT_MAX_CORRECTION_STEPS, repeats=repeats
        ),
    )
    _write_complete_study(study_root, skill, repeats)
    for backend in ("gpt55", "opus"):
        _set_arm_score(
            study_root,
            skill,
            "codex-opus",
            backend,
            "without",
            passed=False,
            score_value=3,
            repeats=repeats,
        )
    _set_arm_score(
        study_root,
        skill,
        "nemotron-correction",
        "nemotron",
        "without",
        passed=False,
        score_value=3,
        repeats=repeats,
    )
    aggregate_path = study_root / f"{skill}_codex_opus" / "gpt55_with.json"
    aggregate = json.loads(aggregate_path.read_text())
    aggregate["summary"]["pass_count"] = 0
    _write_json(aggregate_path, aggregate)

    report = audit.audit_all(
        skills=[skill], prompt_root=prompt_root, study_root=study_root, repeats=repeats
    )

    assert report["status"] == "incomplete"
    assert report["summary"]["study_artifacts_complete"] == 0
    assert report["summary"]["outcomes_complete"] == 0
    assert report["summary"]["outcomes_support_skill_advantage"] == 0
    assert report["skills"][0]["outcome"]["status"] == "incomplete"


def test_audit_all_reports_missing_study_artifacts(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    repeats = 2
    prompt_root = tmp_path / "prompts"
    study_root = tmp_path / "studies"
    prompt_root.mkdir()
    _write_json(
        prompt_root / f"eval_nv_model_studies_{skill}_prompts.json",
        studies._prompt_artifact_records(
            skill, "path", max_steps=studies.DIRECT_MAX_CORRECTION_STEPS, repeats=repeats
        ),
    )

    report = audit.audit_all(
        skills=[skill], prompt_root=prompt_root, study_root=study_root, repeats=repeats
    )

    assert report["status"] == "incomplete"
    assert report["summary"]["prompt_artifacts_complete"] == 1
    assert report["summary"]["study_artifacts_complete"] == 0
    assert report["summary"]["outcomes_complete"] == 0
    assert report["summary"]["issue_count"] > 0
    assert [item["mode"] for item in report["remediation"]] == ["codex-opus", "nemotron"]
    assert all("--resume-missing" in item["command"] for item in report["remediation"])
    assert all(
        studies.EXTERNAL_LLM_DATA_TRANSFER_FLAG in item["command"] for item in report["remediation"]
    )

    text = audit._format_markdown(report)
    assert "## Issue Summary" in text
    assert "| all |" in text
    assert "`missing_file`" in text
    assert "sign-test" not in text.split("## Issue Summary", 1)[0]


def test_markdown_format_includes_outcome_support(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    repeats = 1
    prompt_root = tmp_path / "prompts"
    study_root = tmp_path / "studies"
    prompt_root.mkdir()
    _write_json(
        prompt_root / f"eval_nv_model_studies_{skill}_prompts.json",
        studies._prompt_artifact_records(
            skill, "path", max_steps=studies.DIRECT_MAX_CORRECTION_STEPS, repeats=repeats
        ),
    )
    _write_complete_study(study_root, skill, repeats)
    report = audit.audit_all(
        skills=[skill], prompt_root=prompt_root, study_root=study_root, repeats=repeats
    )

    text = audit._format_markdown(report)

    assert "Outcome support" in text
    assert "does_not_support_skill_advantage" in text
    assert "sign-test" in text
    assert "Outcome-support gates: 0/1" in text


def test_require_skill_advantage_exits_nonzero_when_outcome_does_not_support(
    monkeypatch, capsys
) -> None:
    monkeypatch.setattr(
        audit,
        "audit_all",
        lambda **kwargs: {
            "status": "complete",
            "expected_repeats": 1,
            "summary": {
                "skills": 1,
                "complete_skills": 1,
                "prompt_artifacts_complete": 1,
                "study_artifacts_complete": 1,
                "outcomes_complete": 1,
                "outcomes_support_skill_advantage": 0,
                "issue_count": 0,
            },
            "remediation": [],
            "skills": [
                {
                    "skill": "nv_segment_ct",
                    "prompt_artifact": {"status": "complete", "issues": []},
                    "study_artifacts": {"status": "complete", "issues": []},
                    "outcome": {"status": "does_not_support_skill_advantage"},
                }
            ],
        },
    )

    rc = audit.main(["--require-skill-advantage", "--format", "markdown"])

    assert rc == 1
    assert "does_not_support_skill_advantage" in capsys.readouterr().out


def test_prompt_audit_rejects_embedded_doc_prompts(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    prompt_root = tmp_path / "prompts"
    prompt_root.mkdir()
    _write_json(
        prompt_root / f"eval_nv_model_studies_{skill}_prompts.json",
        studies._prompt_artifact_records(
            skill, "minimal", max_steps=studies.DIRECT_MAX_CORRECTION_STEPS, repeats=1
        ),
    )

    result = audit.audit_prompt_artifact(skill, prompt_root=prompt_root, repeats=1)

    assert result["status"] == "incomplete"
    assert any(issue["code"] == "wrong_prompt_style" for issue in result["issues"])


def test_prompt_audit_rejects_wrong_protocol_metadata(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    prompt_root = tmp_path / "prompts"
    prompt_root.mkdir()
    rows = studies._prompt_artifact_records(
        skill, "path", max_steps=studies.DIRECT_MAX_CORRECTION_STEPS, repeats=1
    )
    rows[0]["system"] = "Use any command that seems plausible."
    rows[0]["answer"] = "A correct answer should call scripts/run_vista3d.py."
    rows[0]["prompt_source"] = "tools/with_vs_without/old_runner.py::_path_prompt"
    rows[0]["runner"] = "tools/with_vs_without/old_runner.py"
    rows[0]["backend_label"] = "different backend"
    rows[0]["backend_model"] = "different-model"
    rows[0]["backend_protocol"] = {"model": "different-model"}
    rows[0]["correction_budget_steps"] = 1
    _write_json(prompt_root / f"eval_nv_model_studies_{skill}_prompts.json", rows)

    result = audit.audit_prompt_artifact(skill, prompt_root=prompt_root, repeats=1)

    assert result["status"] == "incomplete"
    codes = {issue["code"] for issue in result["issues"]}
    assert "wrong_system_prompt" in codes
    assert "wrong_answer_template" in codes
    assert "wrong_prompt_source" in codes
    assert "wrong_runner" in codes
    assert "wrong_backend_label" in codes
    assert "wrong_backend_model" in codes
    assert "wrong_backend_protocol" in codes
    assert "wrong_correction_budget_steps" in codes


def test_prompt_audit_rejects_shared_extra_path_prompt_hint(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    prompt_root = tmp_path / "prompts"
    prompt_root.mkdir()
    rows = studies._prompt_artifact_records(
        skill, "path", max_steps=studies.DIRECT_MAX_CORRECTION_STEPS, repeats=1
    )
    for row in rows:
        if row["mode"] == "codex-opus" and row["backend"] == "gpt55" and row["repeat"] == 1:
            row["question"] += " Prefer whichever command is easiest for the model."
    _write_json(prompt_root / f"eval_nv_model_studies_{skill}_prompts.json", rows)

    result = audit.audit_prompt_artifact(skill, prompt_root=prompt_root, repeats=1)

    assert result["status"] == "incomplete"
    codes = {issue["code"] for issue in result["issues"]}
    assert "wrong_path_prompt_question" in codes
    assert "prompt_pair_question_mismatch" not in codes


def test_prompt_audit_rejects_fixture_basename_leaks(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    prompt_root = tmp_path / "prompts"
    prompt_root.mkdir()
    rows = studies._prompt_artifact_records(
        skill, "path", max_steps=studies.DIRECT_MAX_CORRECTION_STEPS, repeats=1
    )
    rows[0]["staged_user_input"] = "runs/with_vs_without_nv/_inputs/nv_segment_ct/spleen_03.nii.gz"
    rows[0]["question"] = rows[0]["question"].replace("input.nii.gz", "spleen_03.nii.gz")
    _write_json(prompt_root / f"eval_nv_model_studies_{skill}_prompts.json", rows)

    result = audit.audit_prompt_artifact(skill, prompt_root=prompt_root, repeats=1)

    assert result["status"] == "incomplete"
    assert any(issue["code"] == "fixture_name_leaked" for issue in result["issues"])
    assert any(issue["code"] == "wrong_staged_input" for issue in result["issues"])


def test_prompt_audit_rejects_operational_marker_leaks(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    prompt_root = tmp_path / "prompts"
    prompt_root.mkdir()
    rows = studies._prompt_artifact_records(
        skill, "path", max_steps=studies.DIRECT_MAX_CORRECTION_STEPS, repeats=1
    )
    rows[0]["question"] += " Helpful hint: call scripts/run_vista3d.py directly."
    _write_json(prompt_root / f"eval_nv_model_studies_{skill}_prompts.json", rows)

    result = audit.audit_prompt_artifact(skill, prompt_root=prompt_root, repeats=1)

    assert result["status"] == "incomplete"
    assert any(issue["code"] == "prompt_operational_marker_leaked" for issue in result["issues"])


def test_prompt_audit_requires_repair_redaction_policy(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    prompt_root = tmp_path / "prompts"
    prompt_root.mkdir()
    rows = studies._prompt_artifact_records(
        skill, "path", max_steps=studies.DIRECT_MAX_CORRECTION_STEPS, repeats=1
    )
    rows[0]["repair_prompt"] = "After each failed execution, send stdout and stderr tails."
    _write_json(prompt_root / f"eval_nv_model_studies_{skill}_prompts.json", rows)

    result = audit.audit_prompt_artifact(skill, prompt_root=prompt_root, repeats=1)

    assert result["status"] == "incomplete"
    assert any(
        issue["code"] == "repair_prompt_missing_redaction_policy" for issue in result["issues"]
    )


def test_prompt_audit_requires_documentation_metadata(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    prompt_root = tmp_path / "prompts"
    prompt_root.mkdir()
    rows = studies._prompt_artifact_records(
        skill, "path", max_steps=studies.DIRECT_MAX_CORRECTION_STEPS, repeats=1
    )
    rows[0].pop("documentation")
    _write_json(prompt_root / f"eval_nv_model_studies_{skill}_prompts.json", rows)

    result = audit.audit_prompt_artifact(skill, prompt_root=prompt_root, repeats=1)

    assert result["status"] == "incomplete"
    assert any(issue["code"] == "missing_documentation_metadata" for issue in result["issues"])


def test_prompt_audit_rejects_stale_documentation_metadata(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    prompt_root = tmp_path / "prompts"
    prompt_root.mkdir()
    rows = studies._prompt_artifact_records(
        skill, "path", max_steps=studies.DIRECT_MAX_CORRECTION_STEPS, repeats=1
    )
    rows[0]["documentation"][0]["sha256"] = "0" * 64
    _write_json(prompt_root / f"eval_nv_model_studies_{skill}_prompts.json", rows)

    result = audit.audit_prompt_artifact(skill, prompt_root=prompt_root, repeats=1)

    assert result["status"] == "incomplete"
    assert any(issue["code"] == "wrong_documentation_metadata" for issue in result["issues"])


def test_prompt_audit_rejects_missing_documentation_path_in_question(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    prompt_root = tmp_path / "prompts"
    prompt_root.mkdir()
    rows = studies._prompt_artifact_records(
        skill, "path", max_steps=studies.DIRECT_MAX_CORRECTION_STEPS, repeats=1
    )
    with_row = next(
        row
        for row in rows
        if row["mode"] == "codex-opus" and row["backend"] == "gpt55" and row["arm"] == "with"
    )
    doc_path = studies.SCENARIOS[skill].with_doc[0]
    with_row["question"] = with_row["question"].replace(doc_path, "<missing-doc>")
    _write_json(prompt_root / f"eval_nv_model_studies_{skill}_prompts.json", rows)

    result = audit.audit_prompt_artifact(skill, prompt_root=prompt_root, repeats=1)

    assert result["status"] == "incomplete"
    assert any(issue["code"] == "question_missing_documentation_path" for issue in result["issues"])


def test_prompt_audit_rejects_missing_document_read_instruction(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    prompt_root = tmp_path / "prompts"
    prompt_root.mkdir()
    rows = studies._prompt_artifact_records(
        skill, "path", max_steps=studies.DIRECT_MAX_CORRECTION_STEPS, repeats=1
    )
    with_row = next(
        row
        for row in rows
        if row["mode"] == "codex-opus" and row["backend"] == "gpt55" and row["arm"] == "with"
    )
    with_row["question"] = with_row["question"].replace("Read that document. ", "")
    _write_json(prompt_root / f"eval_nv_model_studies_{skill}_prompts.json", rows)

    result = audit.audit_prompt_artifact(skill, prompt_root=prompt_root, repeats=1)

    assert result["status"] == "incomplete"
    assert any(
        issue["code"] == "question_missing_document_read_instruction" for issue in result["issues"]
    )


def test_prompt_audit_rejects_missing_document_boundary(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    prompt_root = tmp_path / "prompts"
    prompt_root.mkdir()
    rows = studies._prompt_artifact_records(
        skill, "path", max_steps=studies.DIRECT_MAX_CORRECTION_STEPS, repeats=1
    )
    without_row = next(
        row for row in rows if row["mode"] == "nemotron-correction" and row["arm"] == "without"
    )
    boundary = audit._expected_documentation_boundary(skill, "without")
    without_row["question"] = without_row["question"].replace(boundary, "")
    _write_json(prompt_root / f"eval_nv_model_studies_{skill}_prompts.json", rows)

    result = audit.audit_prompt_artifact(skill, prompt_root=prompt_root, repeats=1)

    assert result["status"] == "incomplete"
    assert any(issue["code"] == "question_missing_document_boundary" for issue in result["issues"])


def test_prompt_audit_rejects_missing_selected_document(tmp_path: Path, monkeypatch) -> None:
    skill = "missing_doc_skill"
    prompt_root = tmp_path / "prompts"
    prompt_root.mkdir()
    scenario = studies.Scenario(
        skill=skill,
        title="Missing Doc Skill",
        fixture="skills/nv-segment-ct/fixtures/spleen_03.nii.gz",
        kind="segmentation",
        task="Run a segmentation command.",
        user_goal="Use the input at {input_path} and write outputs under {out_dir}.",
        with_doc=("skills/nv-segment-ct/SKILL.md",),
        without_doc=("tools/with_vs_without/upstream_docs/missing_README.md",),
        tier1=(),
        tier2=(),
        tier3=(),
    )
    monkeypatch.setitem(studies.SCENARIOS, skill, scenario)
    rows = studies._prompt_artifact_records(
        skill, "path", max_steps=studies.DIRECT_MAX_CORRECTION_STEPS, repeats=1
    )
    _write_json(prompt_root / f"eval_nv_model_studies_{skill}_prompts.json", rows)

    result = audit.audit_prompt_artifact(skill, prompt_root=prompt_root, repeats=1)

    assert result["status"] == "incomplete"
    codes = {issue["code"] for issue in result["issues"]}
    assert "documentation_file_missing" in codes
    assert "direct_minimal_document_unavailable_or_truncated" in codes


def test_prompt_audit_rejects_invalid_scenario_document_contract(
    tmp_path: Path,
    monkeypatch,
) -> None:
    skill = "bad_doc_contract"
    prompt_root = tmp_path / "prompts"
    prompt_root.mkdir()
    scenario = studies.Scenario(
        skill=skill,
        title="Bad Doc Contract",
        fixture="skills/nv-segment-ct/fixtures/spleen_03.nii.gz",
        kind="segmentation",
        task="Run a segmentation command.",
        user_goal="Use the input at {input_path} and write outputs under {out_dir}.",
        with_doc=("README.md",),
        without_doc=("docs/with-vs-without-authoring.md",),
        tier1=(),
        tier2=(),
        tier3=(),
    )
    monkeypatch.setitem(studies.SCENARIOS, skill, scenario)
    monkeypatch.setitem(audit.SCENARIOS, skill, scenario)
    rows = studies._prompt_artifact_records(
        skill, "path", max_steps=studies.DIRECT_MAX_CORRECTION_STEPS, repeats=1
    )
    _write_json(prompt_root / f"eval_nv_model_studies_{skill}_prompts.json", rows)

    result = audit.audit_prompt_artifact(skill, prompt_root=prompt_root, repeats=1)

    assert result["status"] == "incomplete"
    codes = {issue["code"] for issue in result["issues"]}
    assert "with_doc_contract_invalid" in codes
    assert "without_doc_contract_invalid" in codes


def test_prompt_audit_rejects_user_goal_without_staged_input(
    tmp_path: Path,
    monkeypatch,
) -> None:
    skill = "nv_segment_ct"
    prompt_root = tmp_path / "prompts"
    prompt_root.mkdir()
    scenario = replace(
        studies.SCENARIOS[skill],
        user_goal="Write the segmentation outputs under {out_dir}.",
    )
    monkeypatch.setitem(studies.SCENARIOS, skill, scenario)
    monkeypatch.setitem(audit.SCENARIOS, skill, scenario)
    rows = studies._prompt_artifact_records(
        skill, "path", max_steps=studies.DIRECT_MAX_CORRECTION_STEPS, repeats=1
    )
    _write_json(prompt_root / f"eval_nv_model_studies_{skill}_prompts.json", rows)

    result = audit.audit_prompt_artifact(skill, prompt_root=prompt_root, repeats=1)

    assert result["status"] == "incomplete"
    codes = {issue["code"] for issue in result["issues"]}
    assert "user_goal_missing_placeholders" in codes
    assert "question_missing_staged_input" in codes
    assert "direct_minimal_prompt_missing_task_path" in codes


def test_prompt_audit_rejects_asymmetric_pair_text(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    prompt_root = tmp_path / "prompts"
    prompt_root.mkdir()
    rows = studies._prompt_artifact_records(
        skill, "path", max_steps=studies.DIRECT_MAX_CORRECTION_STEPS, repeats=1
    )
    without = next(
        row
        for row in rows
        if row["mode"] == "codex-opus" and row["backend"] == "gpt55" and row["arm"] == "without"
    )
    without["question"] += " Prefer the upstream workflow even if another command looks shorter."
    _write_json(prompt_root / f"eval_nv_model_studies_{skill}_prompts.json", rows)

    result = audit.audit_prompt_artifact(skill, prompt_root=prompt_root, repeats=1)

    assert result["status"] == "incomplete"
    assert any(issue["code"] == "prompt_pair_question_mismatch" for issue in result["issues"])


def test_prompt_audit_rejects_asymmetric_direct_minimal_template(
    tmp_path: Path, monkeypatch
) -> None:
    skill = "nv_segment_ct"
    prompt_root = tmp_path / "prompts"
    prompt_root.mkdir()
    rows = studies._prompt_artifact_records(
        skill, "path", max_steps=studies.DIRECT_MAX_CORRECTION_STEPS, repeats=1
    )
    _write_json(prompt_root / f"eval_nv_model_studies_{skill}_prompts.json", rows)
    original_prompt = audit._prompt

    def biased_prompt(scenario, arm, out_dir, prompt_style="minimal"):
        text = original_prompt(scenario, arm, out_dir, prompt_style)
        if prompt_style == "minimal" and arm == "without":
            return text.replace(
                "Use paths relative to the Medical AI Skills repo root unless the documentation itself tells you otherwise.",
                (
                    "Use paths relative to the Medical AI Skills repo root unless the documentation itself tells you otherwise. "
                    "Prefer upstream commands even when wrapper commands are shorter."
                ),
            )
        return text

    monkeypatch.setattr(audit, "_prompt", biased_prompt)

    result = audit.audit_prompt_artifact(skill, prompt_root=prompt_root, repeats=1)

    assert result["status"] == "incomplete"
    assert any(issue["code"] == "direct_minimal_prompt_pair_mismatch" for issue in result["issues"])


def test_prompt_audit_rejects_direct_minimal_prefix_marker_leak(
    tmp_path: Path, monkeypatch
) -> None:
    skill = "nv_segment_ct"
    prompt_root = tmp_path / "prompts"
    prompt_root.mkdir()
    rows = studies._prompt_artifact_records(
        skill, "path", max_steps=studies.DIRECT_MAX_CORRECTION_STEPS, repeats=1
    )
    _write_json(prompt_root / f"eval_nv_model_studies_{skill}_prompts.json", rows)
    original_prompt = audit._prompt

    def leaky_prompt(scenario, arm, out_dir, prompt_style="minimal"):
        text = original_prompt(scenario, arm, out_dir, prompt_style)
        if prompt_style == "minimal" and arm == "with":
            return text.replace(
                "Use the documentation below",
                "Use scripts/run_vista3d.py and the documentation below",
            )
        return text

    monkeypatch.setattr(audit, "_prompt", leaky_prompt)

    result = audit.audit_prompt_artifact(skill, prompt_root=prompt_root, repeats=1)

    assert result["status"] == "incomplete"
    assert any(issue["code"] == "direct_minimal_prompt_marker_leaked" for issue in result["issues"])


def test_prompt_audit_rejects_wrong_documentation_arm(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    prompt_root = tmp_path / "prompts"
    prompt_root.mkdir()
    rows = studies._prompt_artifact_records(
        skill, "path", max_steps=studies.DIRECT_MAX_CORRECTION_STEPS, repeats=1
    )
    without = next(
        row for row in rows if row["mode"] == "nemotron-correction" and row["arm"] == "without"
    )
    without["documentation_arm"] = list(studies.SCENARIOS[skill].with_doc)
    _write_json(prompt_root / f"eval_nv_model_studies_{skill}_prompts.json", rows)

    result = audit.audit_prompt_artifact(skill, prompt_root=prompt_root, repeats=1)

    assert result["status"] == "incomplete"
    assert any(issue["code"] == "wrong_documentation_arm" for issue in result["issues"])


def test_commands_format_lists_resume_commands(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    repeats = 1
    prompt_root = tmp_path / "prompts"
    study_root = tmp_path / "studies"
    prompt_root.mkdir()
    _write_json(
        prompt_root / f"eval_nv_model_studies_{skill}_prompts.json",
        studies._prompt_artifact_records(
            skill, "path", max_steps=studies.DIRECT_MAX_CORRECTION_STEPS, repeats=repeats
        ),
    )
    report = audit.audit_all(
        skills=[skill], prompt_root=prompt_root, study_root=study_root, repeats=repeats
    )

    text = audit._format_commands(report)

    assert f"--skills {skill} --mode codex-opus" in text
    assert f"--skills {skill} --mode nemotron" in text
    assert "--resume-missing" in text
    assert studies.EXTERNAL_LLM_DATA_TRANSFER_FLAG in text
    assert "external LLM APIs" in text


def test_study_audit_rejects_broken_repair_protocol(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    repeats = 1
    study_root = tmp_path / "studies"
    _write_complete_study(study_root, skill, repeats)
    repeat_path = study_root / f"{skill}_codex_opus" / "repeats" / "gpt55_without_repeat_1.json"
    repeat = json.loads(repeat_path.read_text())
    repeat["attempts"][0]["score"] = {"passed": False, "score": 1, "tiers": []}
    repeat["attempts"].append(
        {
            "backend": "gpt55",
            "arm": "without",
            "step": 3,
            "messages": [{"role": "user", "content": "try again"}],
            "command": "python bad.py",
            "execution": {},
            "score": {"passed": False, "score": 1, "tiers": []},
        }
    )
    repeat["score"] = {"passed": False, "score": 1, "tiers": []}
    repeat["command"] = "python bad.py"
    repeat["steps_to_pass"] = 0
    _write_json(repeat_path, repeat)

    result = audit.audit_study_artifacts(skill, study_root=study_root, repeats=repeats)

    assert result["status"] == "incomplete"
    codes = {issue["code"] for issue in result["issues"]}
    assert "wrong_attempt_steps" in codes
    assert "wrong_attempt_message_count" in codes
    assert "repair_prompt_missing_failure_context" in codes
    assert "wrong_steps_to_pass" in codes


def test_study_audit_rejects_wrong_repair_message_roles(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    repeats = 1
    study_root = tmp_path / "studies"
    _write_complete_study(study_root, skill, repeats)
    repeat_path = study_root / f"{skill}_codex_opus" / "repeats" / "gpt55_with_repeat_1.json"
    aggregate_path = study_root / f"{skill}_codex_opus" / "gpt55_with.json"
    repeat = json.loads(repeat_path.read_text())
    aggregate = json.loads(aggregate_path.read_text())
    failed_score = {
        "passed": False,
        "score": 1,
        "tiers": [{"tier": 5, "pass": False, "reason": "exit 1"}],
    }
    passed_score = {"passed": True, "score": 5, "tiers": []}
    repair_prompt = (
        "The previous command did not pass verification. "
        "Use only the failure details below to repair the bash command. "
        "Return a replacement single bash code block.\n"
        "{\n"
        '  "failed_tiers": [],\n'
        '  "exit_code": 1,\n'
        '  "stderr_tail": "exit 1",\n'
        '  "stdout_tail": ""\n'
        "}"
    )
    repeat["attempts"][0]["score"] = failed_score
    repeat["attempts"][0]["execution"] = {"exit_code": 1}
    repeat["attempts"].append(
        {
            "backend": "gpt55",
            "arm": "with",
            "step": 1,
            "messages": [
                *repeat["attempts"][0]["messages"],
                {"role": "user", "content": "```bash\npython bad.py\n```"},
                {"role": "user", "content": repair_prompt},
            ],
            "command": repeat["command"],
            "execution": {"exit_code": 0},
            "score": passed_score,
        }
    )
    repeat["score"] = passed_score
    repeat["steps_to_pass"] = 1
    aggregate["repeats"][0] = repeat
    _write_json(repeat_path, repeat)
    _write_json(aggregate_path, aggregate)

    result = audit.audit_study_artifacts(skill, study_root=study_root, repeats=repeats)

    assert result["status"] == "incomplete"
    assert any(issue["code"] == "wrong_attempt_message_roles" for issue in result["issues"])


def test_study_audit_rejects_response_history_mismatch(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    repeats = 1
    study_root = tmp_path / "studies"
    _write_complete_study(study_root, skill, repeats)
    repeat_path = study_root / f"{skill}_codex_opus" / "repeats" / "gpt55_with_repeat_1.json"
    aggregate_path = study_root / f"{skill}_codex_opus" / "gpt55_with.json"
    repeat = json.loads(repeat_path.read_text())
    aggregate = json.loads(aggregate_path.read_text())
    failed_score = {
        "passed": False,
        "score": 1,
        "tiers": [{"tier": 5, "pass": False, "reason": "exit 1"}],
    }
    passed_score = {"passed": True, "score": 5, "tiers": []}
    first_response = "```bash\npython bad.py\n```"
    repair_prompt = (
        "The previous command did not pass verification. "
        "Use only the failure details below to repair the bash command. "
        "Return a replacement single bash code block.\n"
        "{\n"
        '  "failed_tiers": [],\n'
        '  "exit_code": 1,\n'
        '  "stderr_tail": "exit 1",\n'
        '  "stdout_tail": ""\n'
        "}"
    )
    repeat["attempts"][0]["score"] = failed_score
    repeat["attempts"][0]["execution"] = {"exit_code": 1}
    repeat["attempts"][0]["response"] = first_response
    repeat["attempts"].append(
        {
            "backend": "gpt55",
            "arm": "with",
            "step": 1,
            "messages": [
                *repeat["attempts"][0]["messages"],
                {"role": "assistant", "content": "```bash\npython edited.py\n```"},
                {"role": "user", "content": repair_prompt},
            ],
            "command": repeat["command"],
            "execution": {"exit_code": 0},
            "score": passed_score,
        }
    )
    repeat["score"] = passed_score
    repeat["steps_to_pass"] = 1
    aggregate["repeats"][0] = repeat
    _write_json(repeat_path, repeat)
    _write_json(aggregate_path, aggregate)

    result = audit.audit_study_artifacts(skill, study_root=study_root, repeats=repeats)

    assert result["status"] == "incomplete"
    assert any(issue["code"] == "attempt_response_history_mismatch" for issue in result["issues"])


def test_study_audit_rejects_repair_prompt_that_does_not_match_previous_attempt(
    tmp_path: Path,
) -> None:
    skill = "nv_segment_ct"
    repeats = 1
    study_root = tmp_path / "studies"
    _write_complete_study(study_root, skill, repeats)
    repeat_path = study_root / f"{skill}_codex_opus" / "repeats" / "gpt55_with_repeat_1.json"
    aggregate_path = study_root / f"{skill}_codex_opus" / "gpt55_with.json"
    repeat = json.loads(repeat_path.read_text())
    aggregate = json.loads(aggregate_path.read_text())
    failed_score = {
        "passed": False,
        "score": 1,
        "tiers": [{"tier": 5, "pass": False, "reason": "exit 1"}],
    }
    failed_execution = {
        "exit_code": 1,
        "stderr_tail": "exit 1",
        "stdout_tail": "",
        "generated_files": [],
    }
    passed_score = {"passed": True, "score": 5, "tiers": []}
    first_response = "```bash\npython bad.py\n```"
    repair_prompt = (
        studies._feedback(
            failed_score,
            failed_execution,
            scenario=studies.SCENARIOS[skill],
            arm="with",
        )
        + "\nExtra hint: prefer the wrapper."
    )
    repeat["attempts"][0]["score"] = failed_score
    repeat["attempts"][0]["execution"] = failed_execution
    repeat["attempts"][0]["response"] = first_response
    repeat["attempts"].append(
        {
            "backend": "gpt55",
            "arm": "with",
            "step": 1,
            "messages": [
                *repeat["attempts"][0]["messages"],
                {"role": "assistant", "content": first_response},
                {"role": "user", "content": repair_prompt},
            ],
            "command": repeat["command"],
            "execution": {"exit_code": 0},
            "score": passed_score,
        }
    )
    repeat["score"] = passed_score
    repeat["steps_to_pass"] = 1
    aggregate["repeats"][0] = repeat
    _write_json(repeat_path, repeat)
    _write_json(aggregate_path, aggregate)

    result = audit.audit_study_artifacts(skill, study_root=study_root, repeats=repeats)

    assert result["status"] == "incomplete"
    assert any(issue["code"] == "repair_prompt_mismatch" for issue in result["issues"])


def test_study_audit_rejects_leaky_readme_arm_repair_prompt(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    repeats = 1
    study_root = tmp_path / "studies"
    _write_complete_study(study_root, skill, repeats)
    repeat_path = study_root / f"{skill}_codex_opus" / "repeats" / "gpt55_without_repeat_1.json"
    aggregate_path = study_root / f"{skill}_codex_opus" / "gpt55_without.json"
    repeat = json.loads(repeat_path.read_text())
    aggregate = json.loads(aggregate_path.read_text())
    failed_score = {
        "passed": False,
        "score": 1,
        "tiers": [{"tier": 5, "pass": False, "reason": "exit 1"}],
    }
    local_path = "/" + "home/wenqil/private"
    repair_prompt = (
        "The previous command did not pass verification. "
        "Use only the failure details below to repair the bash command. "
        "Return a replacement single bash code block.\n"
        "{\n"
        '  "failed_tiers": [],\n'
        '  "exit_code": 1,\n'
        f'  "stderr_tail": "try {local_path} and skills/nv-segment-ct/scripts/run_vista3d.py",\n'
        '  "stdout_tail": ""\n'
        "}"
    )
    second_attempt = {
        "backend": "gpt55",
        "arm": "without",
        "step": 1,
        "messages": [
            *repeat["attempts"][0]["messages"],
            {"role": "assistant", "content": "```bash\npython bad.py\n```"},
            {"role": "user", "content": repair_prompt},
        ],
        "command": "python bad.py",
        "execution": {},
        "score": failed_score,
    }
    repeat["attempts"][0]["score"] = failed_score
    repeat["attempts"].append(second_attempt)
    repeat["score"] = failed_score
    repeat["command"] = "python bad.py"
    repeat["steps_to_pass"] = "unresolved"
    aggregate["repeats"][0] = repeat
    _write_json(repeat_path, repeat)
    _write_json(aggregate_path, aggregate)

    result = audit.audit_study_artifacts(skill, study_root=study_root, repeats=repeats)

    assert result["status"] == "incomplete"
    codes = {issue["code"] for issue in result["issues"]}
    assert "repair_prompt_leaks_local_home_path" in codes
    assert "repair_prompt_leaks_workbench_skill_marker" in codes


def test_study_audit_rejects_wrong_direct_prompt_style(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    repeats = 1
    study_root = tmp_path / "studies"
    _write_complete_study(study_root, skill, repeats)
    aggregate_path = study_root / f"{skill}_codex_opus" / "gpt55_with.json"
    aggregate = json.loads(aggregate_path.read_text())
    aggregate["prompt_style"] = "guarded"
    aggregate["repeats"][0]["prompt_style"] = "guarded"
    _write_json(aggregate_path, aggregate)
    repeat_path = study_root / f"{skill}_codex_opus" / "repeats" / "gpt55_with_repeat_1.json"
    repeat = json.loads(repeat_path.read_text())
    repeat["prompt_style"] = "guarded"
    _write_json(repeat_path, repeat)

    result = audit.audit_study_artifacts(skill, study_root=study_root, repeats=repeats)

    assert result["status"] == "incomplete"
    codes = {issue["code"] for issue in result["issues"]}
    assert "wrong_prompt_style" in codes
    assert "wrong_direct_prompt_style" in codes


def test_study_audit_rejects_aggregate_repeat_mismatch(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    repeats = 1
    study_root = tmp_path / "studies"
    _write_complete_study(study_root, skill, repeats)
    aggregate_path = study_root / f"{skill}_codex_opus" / "gpt55_with.json"
    aggregate = json.loads(aggregate_path.read_text())
    aggregate["repeats"][0]["extra_unverified_field"] = "edited aggregate only"
    _write_json(aggregate_path, aggregate)

    result = audit.audit_study_artifacts(skill, study_root=study_root, repeats=repeats)

    assert result["status"] == "incomplete"
    codes = {issue["code"] for issue in result["issues"]}
    assert "aggregate_repeat_mismatch" in codes


def test_study_audit_recomputes_aggregate_summary(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    repeats = 1
    study_root = tmp_path / "studies"
    _write_complete_study(study_root, skill, repeats)
    aggregate_path = study_root / f"{skill}_codex_opus" / "gpt55_with.json"
    aggregate = json.loads(aggregate_path.read_text())
    aggregate["summary"]["pass_count"] = 0
    aggregate["summary"]["steps_to_pass"]["values"] = ["unresolved"]
    _write_json(aggregate_path, aggregate)

    result = audit.audit_study_artifacts(skill, study_root=study_root, repeats=repeats)

    assert result["status"] == "incomplete"
    codes = {issue["code"] for issue in result["issues"]}
    assert "wrong_summary_pass_count" in codes
    assert "wrong_summary_steps_to_pass_values" in codes


def test_study_audit_rejects_stale_comparison_markdown(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    repeats = 1
    study_root = tmp_path / "studies"
    _write_complete_study(study_root, skill, repeats)
    comparison_path = study_root / f"{skill}_codex_opus" / "comparison.md"
    comparison_path.write_text("# stale comparison\n")

    result = audit.audit_study_artifacts(skill, study_root=study_root, repeats=repeats)

    assert result["status"] == "incomplete"
    codes = {issue["code"] for issue in result["issues"]}
    assert "stale_comparison" in codes


def test_study_audit_rejects_executed_command_missing_staged_input(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    repeats = 1
    study_root = tmp_path / "studies"
    _write_complete_study(study_root, skill, repeats)
    repeat_path = study_root / f"{skill}_codex_opus" / "repeats" / "gpt55_with_repeat_1.json"
    aggregate_path = study_root / f"{skill}_codex_opus" / "gpt55_with.json"
    repeat = json.loads(repeat_path.read_text())
    aggregate = json.loads(aggregate_path.read_text())
    out_dir = studies._repeat_out_dir(skill, "codex_opus", studies.BACKENDS["gpt55"], "with", 1)
    missing_input = f"python run_vista3d.py --output-dir {out_dir.relative_to(studies.REPO_ROOT)} --labels 1,3,5,14"
    repeat["command"] = missing_input
    repeat["attempts"][0]["command"] = missing_input
    repeat["execution"] = {"executed": True, "exit_code": 0, "generated_files": []}
    repeat["attempts"][0]["execution"] = {"executed": True, "exit_code": 0, "generated_files": []}
    aggregate["repeats"][0] = repeat
    _write_json(repeat_path, repeat)
    _write_json(aggregate_path, aggregate)
    _refresh_comparison(study_root, skill, "codex-opus")

    result = audit.audit_study_artifacts(skill, study_root=study_root, repeats=repeats)

    assert result["status"] == "incomplete"
    codes = {issue["code"] for issue in result["issues"]}
    assert "execution_guard_mismatch" in codes


def test_study_audit_rejects_readme_arm_that_executed_hidden_wrapper(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    repeats = 1
    study_root = tmp_path / "studies"
    _write_complete_study(study_root, skill, repeats)
    repeat_path = study_root / f"{skill}_codex_opus" / "repeats" / "gpt55_without_repeat_1.json"
    aggregate_path = study_root / f"{skill}_codex_opus" / "gpt55_without.json"
    repeat = json.loads(repeat_path.read_text())
    aggregate = json.loads(aggregate_path.read_text())
    out_dir = studies._repeat_out_dir(skill, "codex_opus", studies.BACKENDS["gpt55"], "without", 1)
    rel_input = studies._staged_input_path(studies.SCENARIOS[skill]).relative_to(studies.REPO_ROOT)
    hidden_wrapper = f"python run_vista3d.py {rel_input} --output-dir {out_dir.relative_to(studies.REPO_ROOT)} --labels 1,3,5,14"
    repeat["command"] = hidden_wrapper
    repeat["attempts"][0]["command"] = hidden_wrapper
    repeat["execution"] = {"executed": True, "exit_code": 0, "generated_files": []}
    repeat["attempts"][0]["execution"] = {"executed": True, "exit_code": 0, "generated_files": []}
    aggregate["repeats"][0] = repeat
    _write_json(repeat_path, repeat)
    _write_json(aggregate_path, aggregate)
    _refresh_comparison(study_root, skill, "codex-opus")

    result = audit.audit_study_artifacts(skill, study_root=study_root, repeats=repeats)

    assert result["status"] == "incomplete"
    codes = {issue["code"] for issue in result["issues"]}
    assert "execution_guard_mismatch" in codes


def test_study_audit_rejects_edited_initial_prompt(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    repeats = 1
    study_root = tmp_path / "studies"
    _write_complete_study(study_root, skill, repeats)
    repeat_path = study_root / f"{skill}_codex_opus" / "repeats" / "gpt55_with_repeat_1.json"
    repeat = json.loads(repeat_path.read_text())
    repeat["attempts"][0]["messages"][0]["content"] = "Different system prompt."
    repeat["attempts"][0]["messages"][1][
        "content"
    ] += "\nExtra hint: call the skill wrapper directly."
    _write_json(repeat_path, repeat)

    result = audit.audit_study_artifacts(skill, study_root=study_root, repeats=repeats)

    assert result["status"] == "incomplete"
    codes = {issue["code"] for issue in result["issues"]}
    assert "wrong_initial_system_prompt" in codes
    assert "wrong_initial_user_prompt" in codes


def test_study_audit_requires_attempt_response_usage_and_model(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    repeats = 1
    study_root = tmp_path / "studies"
    _write_complete_study(study_root, skill, repeats)
    repeat_path = study_root / f"{skill}_codex_opus" / "repeats" / "gpt55_with_repeat_1.json"
    aggregate_path = study_root / f"{skill}_codex_opus" / "gpt55_with.json"
    repeat = json.loads(repeat_path.read_text())
    aggregate = json.loads(aggregate_path.read_text())
    repeat["attempts"][0].pop("response")
    repeat["attempts"][0].pop("usage")
    repeat["attempts"][0]["model"] = "stale-model"
    repeat["attempts"][0]["backend_protocol"] = {"model": "stale-model"}
    repeat["backend_label"] = "stale backend"
    repeat["model"] = "stale-model"
    repeat["backend_protocol"] = {"model": "stale-model"}
    repeat["execution"] = {"exit_code": 999}
    aggregate["repeats"][0] = repeat
    _write_json(repeat_path, repeat)
    _write_json(aggregate_path, aggregate)

    result = audit.audit_study_artifacts(skill, study_root=study_root, repeats=repeats)

    assert result["status"] == "incomplete"
    codes = {issue["code"] for issue in result["issues"]}
    assert "missing_attempt_response" in codes
    assert "missing_attempt_usage" in codes
    assert "wrong_attempt_model" in codes
    assert "wrong_attempt_backend_protocol" in codes
    assert "wrong_backend_label" in codes
    assert "wrong_model" in codes
    assert "wrong_backend_protocol" in codes
    assert "final_execution_mismatch" in codes


def test_study_audit_rejects_command_not_extracted_from_stored_response(tmp_path: Path) -> None:
    skill = "nv_segment_ct"
    repeats = 1
    study_root = tmp_path / "studies"
    _write_complete_study(study_root, skill, repeats)
    repeat_path = study_root / f"{skill}_codex_opus" / "repeats" / "gpt55_with_repeat_1.json"
    aggregate_path = study_root / f"{skill}_codex_opus" / "gpt55_with.json"
    repeat = json.loads(repeat_path.read_text())
    aggregate = json.loads(aggregate_path.read_text())
    command = repeat["attempts"][0]["command"]
    repeat["attempts"][0]["response"] = (
        f"```bash\n{command}\n```\n" "```bash\npython different.py\n```"
    )
    aggregate["repeats"][0] = repeat
    _write_json(repeat_path, repeat)
    _write_json(aggregate_path, aggregate)
    _refresh_comparison(study_root, skill, "codex-opus")

    result = audit.audit_study_artifacts(skill, study_root=study_root, repeats=repeats)

    assert result["status"] == "incomplete"
    codes = {issue["code"] for issue in result["issues"]}
    assert "response_command_mismatch" in codes
