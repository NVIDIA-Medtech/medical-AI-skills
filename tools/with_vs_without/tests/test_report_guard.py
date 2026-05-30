from tools.with_vs_without import write_nv_model_reports as reports


def test_checked_in_with_vs_without_reports_do_not_claim_complete_status() -> None:
    docs = sorted(reports.DOC_ROOT.glob("with-vs-without-*-*.md"))
    offenders = [
        str(path.relative_to(reports.REPO_ROOT))
        for path in docs
        if path.read_text().splitlines()[2].startswith("Status: complete")
    ]
    assert offenders == []


def test_incomplete_checked_in_overview_does_not_present_historical_rows_as_current() -> None:
    path = reports.DOC_ROOT / "with-vs-without-skill-experiment.md"
    if not path.exists():
        return

    text = path.read_text()
    if "strict audit currently incomplete" not in text:
        return

    assert "current outcome support remains incomplete" in text
    assert "The completed direct-API runs used" not in text
    matrix = text.split("## Document Matrix", 1)[1].split("## Shared Arm Rules", 1)[0]
    assert "Prompt artifact " in matrix
    assert "outcome gate is " in matrix
    assert " pass (avg " not in matrix


def _repeat(repeat: int, passed: bool, score: int) -> dict[str, object]:
    return {"repeat": repeat, "score": {"passed": passed, "score": score, "tiers": []}, "attempts": []}


def _aggregate(backend: str, arm: str, repeats: list[dict[str, object]]) -> dict[str, object]:
    return {"backend": backend, "arm": arm, "repeats": repeats}


def _report(status: str) -> dict[str, object]:
    issues = []
    if status != "complete":
        issues.append(
            {
                "code": "missing_file",
                "path": "runs/with_vs_without_nv/studies/example/with.json",
                "message": "file is missing",
            }
        )
    return {
        "status": status,
        "summary": {"issue_count": len(issues)},
        "skills": [
            {
                "skill": "example",
                "prompt_artifact": {"issues": []},
                "study_artifacts": {"issues": issues},
            }
        ],
    }


def test_report_generation_refuses_incomplete_artifacts(monkeypatch, capsys) -> None:
    called = {"codex": False, "nemotron": False, "overview": False}

    monkeypatch.setattr(reports, "audit_all", lambda repeats: _report("incomplete"))
    monkeypatch.setattr(reports, "write_codex", lambda skill: called.__setitem__("codex", True))
    monkeypatch.setattr(reports, "write_nemotron", lambda skill: called.__setitem__("nemotron", True))
    monkeypatch.setattr(reports, "write_overview", lambda codex, nemotron: called.__setitem__("overview", True))

    rc = reports.main([])

    assert rc == 1
    assert called == {"codex": False, "nemotron": False, "overview": False}
    assert "Refusing to regenerate" in capsys.readouterr().err


def test_report_generation_can_skip_guard_for_debugging(monkeypatch) -> None:
    monkeypatch.setattr(reports, "audit_all", lambda repeats: _report("incomplete"))
    monkeypatch.setattr(reports, "SCENARIOS", {"example": object()})
    monkeypatch.setattr(reports, "write_codex", lambda skill: {"skill": skill, "codex_with_pass": 1})
    monkeypatch.setattr(reports, "write_nemotron", lambda skill: {"skill": skill, "nemotron_with_pass": 1})
    overview_calls: list[tuple[list[dict[str, object]], list[dict[str, object]]]] = []
    monkeypatch.setattr(reports, "write_overview", lambda codex, nemotron: overview_calls.append((codex, nemotron)))
    snapshot_calls: list[dict[str, object]] = []
    monkeypatch.setattr(reports, "write_snapshot", lambda **kwargs: snapshot_calls.append(kwargs))

    rc = reports.main(["--allow-incomplete"])

    assert rc == 0
    assert overview_calls
    assert snapshot_calls == [{"repeats": reports.DIRECT_REPEATS}]


def test_paired_outcome_summary_matches_backend_and_repeat() -> None:
    with_records = [
        _aggregate("gpt55", "with", [_repeat(1, True, 5), _repeat(2, False, 4)]),
        _aggregate("opus", "with", [_repeat(1, True, 5)]),
    ]
    without_records = [
        _aggregate("gpt55", "without", [_repeat(1, False, 4), _repeat(2, False, 4)]),
        _aggregate("opus", "without", [_repeat(1, True, 5)]),
    ]

    summary = reports._paired_outcome_summary(with_records, without_records)

    assert summary == {
        "matched": 3,
        "with_wins": 1,
        "without_wins": 0,
        "ties": 2,
        "unmatched": [],
        "paired_sign_test": {
            "decisive_pairs": 1,
            "with_win_rate_decisive": 1.0,
            "tie_rate_matched": 2 / 3,
            "one_sided_sign_test_p": 0.5,
            "test": "exact one-sided sign test, H1: SKILL.md wins more decisive pairs than README-only",
        },
        "signal": "SKILL.md paired advantage",
    }


def test_report_uses_neutral_staged_input_path() -> None:
    path = reports._report_input_path("nv_segment_ct")

    assert path.name == "input.nii.gz"
    assert "spleen_03.nii.gz" not in str(path)


def test_record_summary_accepts_string_unresolved_steps() -> None:
    record = _aggregate(
        "gpt55",
        "without",
        [
            {
                "repeat": 1,
                "score": {"passed": False, "score": 3, "tiers": []},
                "steps_to_pass": "unresolved",
                "attempts": [],
            }
        ],
    )

    summary = reports._record_summary(record)

    assert summary["unresolved_count"] == 1
    assert summary["resolved_steps"] == []
    assert reports._steps_summary_text(record) == "all unresolved; values [unresolved]"


def test_token_profile_for_record_sums_usage_attempts_and_execution() -> None:
    record = {
        "backend": "gpt55",
        "backend_label": "GPT-5.5 / Codex",
        "arm": "with",
        "repeats": [
            {
                "score": {"passed": True, "score": 5, "tiers": []},
                "attempts": [{"step": 0}],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 25,
                    "total_tokens": 125,
                    "completion_tokens_details": {"reasoning_tokens": 10},
                },
                "execution": {"elapsed_seconds": 2.5},
            },
            {
                "score": {"passed": False, "score": 2, "tiers": []},
                "attempts": [{"step": 0}, {"step": 1}],
                "usage": {
                    "prompt_tokens": 200,
                    "completion_tokens": 40,
                    "total_tokens": 240,
                    "completion_tokens_details": {"reasoning_tokens": 15},
                },
                "execution": {},
            },
        ],
    }

    profile = reports._token_profile_for_record(record)

    assert profile["repeat_count"] == 2
    assert profile["pass_count"] == 1
    assert profile["attempt_count"] == 3
    assert profile["prompt_tokens"] == 300
    assert profile["completion_tokens"] == 65
    assert profile["reasoning_tokens"] == 25
    assert profile["total_tokens"] == 365
    assert profile["exec_count"] == 1
    assert profile["exec_seconds"] == 2.5


def test_tolerant_command_candidate_is_diagnostic_only() -> None:
    assert reports._tolerant_command_candidate("```bash\npython ok.py\n```") == (
        "python ok.py",
        "strict_fenced_block",
    )
    assert reports._tolerant_command_candidate("bash\npython ok.py\n```") == (
        "python ok.py",
        "malformed_language_prefix",
    )
    assert reports._tolerant_command_candidate("export A=1 && python ok.py") == (
        "export A=1 && python ok.py",
        "raw_shell_text",
    )
    assert reports._tolerant_command_candidate("not a command") == (
        None,
        "no_shell_like_text",
    )


def test_nemotron_format_profile_counts_recoverable_guard_ready_command() -> None:
    scenario = reports.SCENARIOS["nv_generate_mr"]
    output_dir = (
        "runs/with_vs_without_nv/"
        "nv_generate_mr_nemotron_correction/with/repeat_1"
    )
    record = {
        "backend": "nemotron",
        "backend_label": "Nemotron",
        "arm": "with",
        "repeats": [
            {
                "repeat": 1,
                "output_dir": output_dir,
                "response": (
                    "export NV_GENERATE_ROOT=\"${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}\" && "
                    "python skills/nv-generate-mr/scripts/run_mr.py "
                    "runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json "
                    f"--output-dir {output_dir} --version rflow-mr"
                ),
                "command": None,
                "score": {"passed": False, "score": 0, "tiers": []},
                "failure_analysis": [{"kind": "no_command"}],
            }
        ],
    }

    profile = reports._nemotron_format_profile(scenario, record)

    assert profile["strict_command"] == 0
    assert profile["recoverable_command"] == 1
    assert profile["guard_ready_after_tolerant"] == 1
    assert profile["raw_shell_text"] == 1


def test_paired_outcome_summary_does_not_overstate_readme_win() -> None:
    with_records = [_aggregate("nemotron", "with", [_repeat(1, False, 3), _repeat(2, True, 5)])]
    without_records = [_aggregate("nemotron", "without", [_repeat(1, True, 5), _repeat(2, True, 5)])]

    summary = reports._paired_outcome_summary(with_records, without_records)

    assert summary["signal"] == "README-only paired advantage"
    assert summary["with_wins"] == 0
    assert summary["without_wins"] == 1
    assert summary["ties"] == 1


def test_paired_outcome_summary_flags_unmatched_pairs() -> None:
    with_records = [_aggregate("gpt55", "with", [_repeat(1, True, 5)])]
    without_records = [_aggregate("gpt55", "without", [])]

    summary = reports._paired_outcome_summary(with_records, without_records)

    assert summary["signal"] == "Incomplete paired comparison"
    assert summary["unmatched"] == ["gpt55/repeat_1"]


def test_paired_advantage_gate_passes_only_for_skill_pair_advantage() -> None:
    gate = reports._paired_advantage_gate(
        {
            "matched": 5,
            "with_wins": 3,
            "without_wins": 1,
            "ties": 1,
            "unmatched": [],
            "signal": "SKILL.md paired advantage",
        }
    )

    assert gate["passed"] is True
    assert gate["status"] == "supports_skill_advantage"
    assert gate["label"] == "Supports SKILL.md advantage"


def test_paired_advantage_gate_rejects_ties_and_readme_wins() -> None:
    tied = reports._paired_advantage_gate(
        {
            "matched": 5,
            "with_wins": 2,
            "without_wins": 2,
            "ties": 1,
            "unmatched": [],
            "signal": "No paired separation",
        }
    )
    readme_win = reports._paired_advantage_gate(
        {
            "matched": 5,
            "with_wins": 1,
            "without_wins": 3,
            "ties": 1,
            "unmatched": [],
            "signal": "README-only paired advantage",
        }
    )

    assert tied["passed"] is False
    assert tied["status"] == "does_not_support_skill_advantage"
    assert readme_win["passed"] is False
    assert readme_win["status"] == "does_not_support_skill_advantage"


def test_paired_advantage_gate_rejects_incomplete_pairs() -> None:
    gate = reports._paired_advantage_gate(
        {
            "matched": 0,
            "with_wins": 0,
            "without_wins": 0,
            "ties": 0,
            "unmatched": ["gpt55/repeat_1"],
            "signal": "Incomplete paired comparison",
        }
    )

    assert gate["passed"] is False
    assert gate["status"] == "incomplete"
    assert gate["label"] == "Incomplete paired comparison"


def _overview_row(skill: str, prefix: str, supports: bool) -> dict[str, object]:
    label = "Supports SKILL.md advantage" if supports else "Does not support SKILL.md advantage"
    return {
        "skill": skill,
        f"{prefix}_with_pass": 5,
        f"{prefix}_without_pass": 0,
        f"{prefix}_with_repeats": 5,
        f"{prefix}_without_repeats": 5,
        f"{prefix}_paired_signal": "SKILL.md paired advantage" if supports else "No paired separation",
        f"{prefix}_paired_with_wins": 5 if supports else 0,
        f"{prefix}_paired_without_wins": 0,
        f"{prefix}_paired_ties": 0 if supports else 5,
        f"{prefix}_paired_matched": 5,
        f"{prefix}_paired_decisive": 5 if supports else 0,
        f"{prefix}_paired_sign_test_p": 1 / 32 if supports else None,
        f"{prefix}_claim_support": supports,
        f"{prefix}_claim_support_label": label,
        f"{prefix}_claim_support_reason": "test",
    }


def test_overview_reports_outcome_support_gate_counts(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(reports, "DOC_ROOT", tmp_path)
    monkeypatch.setattr(reports, "SCENARIOS", {"alpha": object(), "beta": object()})
    monkeypatch.setattr(reports, "_latest_log", lambda glob: "not found")
    monkeypatch.setattr(reports, "_REPORT_AUDIT_STATUS", "complete")
    monkeypatch.setattr(reports, "_REPORT_AUDIT_ISSUES", 0)
    codex = []
    nemotron = []
    for skill, supports in (("alpha", True), ("beta", False)):
        codex_row = _overview_row(skill, "codex", supports)
        codex_row.update({"codex_with_avg": "5.0/5", "codex_without_avg": "0.0/5"})
        codex.append(codex_row)
        nemo_row = _overview_row(skill, "nemotron", supports)
        nemo_row.update(
            {
                "nemotron_with_score": "5.0/5",
                "nemotron_without_score": "0.0/5",
                "nemotron_with_steps": "mean 0.0; unresolved 0; values [0]",
                "nemotron_without_steps": "all unresolved; values [unresolved]",
            }
        )
        nemotron.append(nemo_row)

    reports.write_overview(codex, nemotron)

    text = (tmp_path / "with-vs-without-skill-experiment.md").read_text()
    assert "Codex/Opus outcome-support gates: 1/2" in text
    assert "Nemotron outcome-support gates: 1/2" in text
    assert "Artifact completeness alone does not establish" in text


def test_incomplete_overview_reports_audit_state_not_saved_aggregate(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(reports, "DOC_ROOT", tmp_path)
    monkeypatch.setattr(reports, "SCENARIOS", {"alpha": object()})
    monkeypatch.setattr(reports, "_latest_log", lambda glob: "not found")
    monkeypatch.setattr(reports, "_REPORT_AUDIT_STATUS", "incomplete")
    monkeypatch.setattr(reports, "_REPORT_AUDIT_ISSUES", 2)
    monkeypatch.setattr(
        reports,
        "_REPORT_AUDIT_SUMMARY",
        {
            "skills": 1,
            "prompt_artifacts_complete": 1,
            "study_artifacts_complete": 0,
            "outcomes_complete": 0,
            "outcomes_support_skill_advantage": 0,
        },
    )
    monkeypatch.setattr(
        reports,
        "_REPORT_AUDIT_SKILLS",
        [
            {
                "skill": "alpha",
                "prompt_artifact": {"status": "complete", "issues": []},
                "study_artifacts": {
                    "status": "incomplete",
                    "issues": [{"code": "wrong_initial_user_prompt"}],
                },
                "outcome": {"status": "incomplete"},
            }
        ],
    )
    monkeypatch.setattr(
        reports,
        "_REPORT_TRANSFER_SUMMARY",
        {
            "pending_initial_calls": 2,
            "reused_repeats": 4,
            "max_possible_repair_calls": 0,
        },
    )
    monkeypatch.setattr(reports, "_REPORT_TRANSFER_FINGERPRINT", "abc123")

    reports.write_overview([], [])

    text = (tmp_path / "with-vs-without-skill-experiment.md").read_text()
    assert "current outcome support remains incomplete" in text
    assert "## Current Audit State" in text
    assert "Pending initial external LLM calls: 2" in text
    assert "Reviewed payload fingerprint: `abc123`" in text
    assert "Prompt artifact complete; study artifacts are incomplete" in text
    assert "## Current Aggregate Result" not in text
    assert "The completed direct-API runs used" not in text
