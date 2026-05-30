import json
from pathlib import Path

import pytest

from tools.with_vs_without import approval_packet_nv_model_studies as packet
from tools.with_vs_without import run_nv_model_studies as studies


def _write_prompt_artifact(prompt_root: Path, skill: str, repeats: int = 1) -> None:
    prompt_root.mkdir(parents=True, exist_ok=True)
    rows = studies._prompt_artifact_records(
        skill,
        "path",
        max_steps=studies.DIRECT_MAX_CORRECTION_STEPS,
        repeats=repeats,
    )
    (prompt_root / f"eval_nv_model_studies_{skill}_prompts.json").write_text(
        json.dumps(rows, indent=2) + "\n"
    )


def test_approval_packet_summarizes_pending_external_scope(tmp_path: Path) -> None:
    skill = "nv_reason_cxr"
    prompt_root = tmp_path / "prompts"
    _write_prompt_artifact(prompt_root, skill)

    report = packet.build_packet(
        skills=[skill],
        mode="nemotron",
        repeats=1,
        prompt_root=prompt_root,
        study_root=tmp_path / "studies",
        environ={"NV_INFER_TOKEN": "secret-token"},
        bashrc=tmp_path / "missing_bashrc",
    )

    assert report["status"] == "ready_for_external_approval"
    assert report["network_calls_made"] is False
    assert report["external_transfer_required"] is True
    assert report["preflight"]["status"] == "pass"
    assert report["data_transfer"]["summary"]["pending_initial_calls"] == 2
    assert (
        report["data_transfer"]["summary"]["max_possible_repair_calls"]
        == 2 * studies.DIRECT_MAX_CORRECTION_STEPS
    )
    assert len(report["data_transfer"]["payload_fingerprint"]) == 64
    assert report["data_transfer"]["backend_protocols"][0]["backend"] == "nemotron"
    assert len(report["data_transfer"]["backend_protocols"][0]["protocol_sha256"]) == 64
    assert report["data_transfer"]["prompt_policy_issue_count"] == 0
    assert report["data_transfer"]["prompt_policy_issues"] == []
    assert report["approval_coverage"]["pending_direct_group_count"] == 1
    assert report["approval_coverage"]["planned_direct_group_count"] == 1
    assert report["approval_coverage"]["missing_direct_group_count"] == 0
    assert report["approval_coverage"]["invalid_direct_command_count"] == 0
    assert report["approval_coverage"]["pending_direct_groups"] == [
        {"skill": skill, "mode": "nemotron"}
    ]
    assert [command["mode"] for command in report["planned_commands"]] == ["nemotron"]
    assert studies.EXTERNAL_LLM_DATA_TRANSFER_FLAG in report["planned_commands"][0]["command"]

    text = packet._format_markdown(report)
    assert "No network calls were made" in text
    assert "Pending initial external LLM calls: 2" in text
    assert "Reviewed payload fingerprint:" in text
    assert "## Backend Protocols" in text
    assert "| nemotron |" in text
    assert "Direct remediation coverage: 1/1 pending skill/mode groups covered" in text
    assert "Direct remediation invalid commands: 0" in text
    assert "Pending prompt policy issues: 0" in text
    assert "Initial prompt guard:" in text
    assert "## Approval Commands" in text
    assert "secret-token" not in text
    assert "Documentation available to you:" not in json.dumps(report)


def test_approval_packet_reports_not_ready_when_preflight_fails(tmp_path: Path) -> None:
    skill = "nv_reason_cxr"
    prompt_root = tmp_path / "prompts"
    _write_prompt_artifact(prompt_root, skill)

    report = packet.build_packet(
        skills=[skill],
        mode="nemotron",
        repeats=1,
        prompt_root=prompt_root,
        study_root=tmp_path / "studies",
        environ={},
        bashrc=tmp_path / "missing_bashrc",
    )

    assert report["status"] == "not_ready"
    assert report["preflight"]["summary"]["errors"] == 1
    assert report["preflight"]["errors"][0]["scope"] == "credentials"
    assert report["data_transfer"]["summary"]["pending_initial_calls"] == 2
    assert "## Readiness Errors" in packet._format_markdown(report)


def test_approval_packet_not_ready_for_non_protocol_correction_budget(tmp_path: Path) -> None:
    skill = "nv_reason_cxr"
    prompt_root = tmp_path / "prompts"
    _write_prompt_artifact(prompt_root, skill)

    report = packet.build_packet(
        skills=[skill],
        mode="nemotron",
        repeats=1,
        max_correction_steps=3,
        prompt_root=prompt_root,
        study_root=tmp_path / "studies",
        environ={"NV_INFER_TOKEN": "secret-token"},
        bashrc=tmp_path / "missing_bashrc",
    )

    checks = {error["check"] for error in report["approval_errors"]}
    assert report["status"] == "not_ready"
    assert "direct_correction_budget" in checks
    assert report["data_transfer"]["max_correction_steps"] == 3
    assert report["approval_coverage"]["invalid_direct_command_count"] >= 1


def test_approval_packet_cli_rejects_non_protocol_repeat_count(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        packet.main(["--mode", "nemotron", "--repeats", "1"])

    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert f"--repeats {studies.DIRECT_REPEATS}" in captured.err


def test_approval_packet_not_ready_when_prompt_policy_issues(monkeypatch) -> None:
    monkeypatch.setattr(
        packet.preflight,
        "preflight",
        lambda **kwargs: {
            "status": "pass",
            "summary": {"checks": 1, "errors": 0, "warnings": 0},
            "checks": [],
        },
    )
    monkeypatch.setattr(
        packet.transfer,
        "build_manifest",
        lambda **kwargs: {
            "prompt_style": "minimal",
            "resume_missing": True,
            "payload_fingerprint": "f" * 64,
            "summary": {
                "pending_initial_calls": 2,
                "reused_repeats": 0,
                "max_possible_repair_calls": 2 * studies.DIRECT_MAX_CORRECTION_STEPS,
                "prompt_policy_issue_count": 1,
                "pending_transfer": {
                    "total_initial_bytes": 100,
                    "embedded_document_bytes": 50,
                    "by_endpoint_model": [],
                    "by_skill": [],
                },
            },
            "prompt_policy_issues": [
                {
                    "status": "pending",
                    "skill": "nv_reason_cxr",
                    "mode": "nemotron-correction",
                    "backend": "nemotron",
                    "arm": "with",
                    "repeat": 1,
                    "prompt": "user",
                    "issue": "local_absolute_home_path",
                    "detail": "user prompt contains a local absolute home path; matched text is redacted",
                }
            ],
            "data_transfer_policy": {
                "initial_call": "initial",
                "repair_calls": "repair",
                "initial_prompt_guard": "guard",
                "does_not_send": [],
            },
            "entries": [
                {
                    "status": "pending",
                    "skill": "nv_reason_cxr",
                    "mode": "nemotron-correction",
                }
            ],
        },
    )
    monkeypatch.setattr(
        packet.audit,
        "audit_all",
        lambda **kwargs: {
            "status": "incomplete",
            "summary": {
                "skills": 1,
                "prompt_artifacts_complete": 1,
                "study_artifacts_complete": 0,
                "outcomes_support_skill_advantage": 0,
            },
            "remediation": [
                {
                    "skill": "nv_reason_cxr",
                    "mode": "nemotron",
                    "command": (
                        "python tools/with_vs_without/run_nv_model_studies.py "
                        "--skills nv_reason_cxr --mode nemotron --prompt-style minimal "
                        f"--max-correction-steps {studies.DIRECT_MAX_CORRECTION_STEPS} "
                        f"--repeats {studies.DIRECT_REPEATS} --resume-missing "
                        f"{studies.EXTERNAL_LLM_DATA_TRANSFER_FLAG}"
                    ),
                },
            ],
            "skills": [],
        },
    )

    report = packet.build_packet(mode="nemotron")

    assert report["status"] == "not_ready"
    assert report["approval_errors"][0]["check"] == "prompt_payload_policy"
    assert "nv_reason_cxr:nemotron-correction:nemotron:with" in report["approval_errors"][0]["detail"]
    assert report["approval_coverage"]["pending_direct_group_count"] == 1
    assert report["approval_coverage"]["planned_direct_group_count"] == 1
    assert report["approval_coverage"]["invalid_direct_command_count"] == 0
    assert report["data_transfer"]["prompt_policy_issue_count"] == 1
    text = packet._format_markdown(report)
    assert "## Approval Packet Errors" in text
    assert "prompt_payload_policy" in text


def test_approval_packet_not_ready_when_pending_calls_have_no_direct_commands(monkeypatch) -> None:
    monkeypatch.setattr(
        packet.preflight,
        "preflight",
        lambda **kwargs: {
            "status": "pass",
            "summary": {"checks": 1, "errors": 0, "warnings": 0},
            "checks": [],
        },
    )
    monkeypatch.setattr(
        packet.transfer,
        "build_manifest",
        lambda **kwargs: {
            "prompt_style": "minimal",
            "resume_missing": True,
            "payload_fingerprint": "f" * 64,
            "summary": {
                "pending_initial_calls": 2,
                "reused_repeats": 0,
                "max_possible_repair_calls": 2 * studies.DIRECT_MAX_CORRECTION_STEPS,
                "pending_transfer": {
                    "total_initial_bytes": 100,
                    "embedded_document_bytes": 50,
                    "by_endpoint_model": [],
                    "by_skill": [],
                },
            },
            "data_transfer_policy": {
                "initial_call": "initial",
                "repair_calls": "repair",
                "does_not_send": [],
            },
            "entries": [
                {
                    "status": "pending",
                    "skill": "nv_reason_cxr",
                    "mode": "nemotron-correction",
                }
            ],
        },
    )
    monkeypatch.setattr(
        packet.audit,
        "audit_all",
        lambda **kwargs: {
            "status": "incomplete",
            "summary": {
                "skills": 1,
                "prompt_artifacts_complete": 1,
                "study_artifacts_complete": 0,
                "outcomes_support_skill_advantage": 0,
            },
            "remediation": [],
            "skills": [],
        },
    )

    report = packet.build_packet(mode="nemotron")

    assert report["status"] == "not_ready"
    assert report["approval_errors"][0]["check"] == "direct_remediation_commands"
    assert report["approval_coverage"]["pending_direct_group_count"] == 1
    assert report["approval_coverage"]["planned_direct_group_count"] == 0
    assert report["approval_coverage"]["missing_direct_groups"] == [
        {"skill": "nv_reason_cxr", "mode": "nemotron"}
    ]
    text = packet._format_markdown(report)
    assert "## Approval Packet Errors" in text
    assert "nv_reason_cxr:nemotron" in text


def test_approval_packet_not_ready_when_pending_groups_have_partial_command_coverage(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        packet.preflight,
        "preflight",
        lambda **kwargs: {
            "status": "pass",
            "summary": {"checks": 1, "errors": 0, "warnings": 0},
            "checks": [],
        },
    )
    monkeypatch.setattr(
        packet.transfer,
        "build_manifest",
        lambda **kwargs: {
            "prompt_style": "minimal",
            "resume_missing": True,
            "payload_fingerprint": "f" * 64,
            "summary": {
                "pending_initial_calls": 4,
                "reused_repeats": 0,
                "max_possible_repair_calls": 20,
                "pending_transfer": {
                    "total_initial_bytes": 200,
                    "embedded_document_bytes": 100,
                    "by_endpoint_model": [],
                    "by_skill": [],
                },
            },
            "data_transfer_policy": {
                "initial_call": "initial",
                "repair_calls": "repair",
                "does_not_send": [],
            },
            "entries": [
                {
                    "status": "pending",
                    "skill": "nv_reason_cxr",
                    "mode": "nemotron-correction",
                },
                {
                    "status": "pending",
                    "skill": "nv_segment_ct",
                    "mode": "nemotron-correction",
                },
            ],
        },
    )
    monkeypatch.setattr(
        packet.audit,
        "audit_all",
        lambda **kwargs: {
            "status": "incomplete",
            "summary": {
                "skills": 2,
                "prompt_artifacts_complete": 2,
                "study_artifacts_complete": 0,
                "outcomes_support_skill_advantage": 0,
            },
            "remediation": [
                {
                    "skill": "nv_reason_cxr",
                    "mode": "nemotron",
                    "command": "python tools/with_vs_without/run_nv_model_studies.py",
                }
            ],
            "skills": [],
        },
    )

    report = packet.build_packet(mode="nemotron")

    assert report["status"] == "not_ready"
    assert report["approval_errors"][0]["check"] == "direct_remediation_commands"
    assert "nv_segment_ct:nemotron" in report["approval_errors"][0]["detail"]
    assert report["approval_coverage"]["pending_direct_group_count"] == 2
    assert report["approval_coverage"]["planned_direct_group_count"] == 1
    assert report["approval_coverage"]["missing_direct_groups"] == [
        {"skill": "nv_segment_ct", "mode": "nemotron"}
    ]
    assert [command["skill"] for command in report["planned_commands"]] == ["nv_reason_cxr"]


def test_approval_packet_not_ready_when_direct_commands_are_duplicated(monkeypatch) -> None:
    monkeypatch.setattr(
        packet.preflight,
        "preflight",
        lambda **kwargs: {
            "status": "pass",
            "summary": {"checks": 1, "errors": 0, "warnings": 0},
            "checks": [],
        },
    )
    monkeypatch.setattr(
        packet.transfer,
        "build_manifest",
        lambda **kwargs: {
            "prompt_style": "minimal",
            "resume_missing": True,
            "payload_fingerprint": "f" * 64,
            "summary": {
                "pending_initial_calls": 2,
                "reused_repeats": 0,
                "max_possible_repair_calls": 2 * studies.DIRECT_MAX_CORRECTION_STEPS,
                "pending_transfer": {
                    "total_initial_bytes": 100,
                    "embedded_document_bytes": 50,
                    "by_endpoint_model": [],
                    "by_skill": [],
                },
            },
            "data_transfer_policy": {
                "initial_call": "initial",
                "repair_calls": "repair",
                "does_not_send": [],
            },
            "entries": [
                {
                    "status": "pending",
                    "skill": "nv_reason_cxr",
                    "mode": "nemotron-correction",
                },
            ],
        },
    )
    monkeypatch.setattr(
        packet.audit,
        "audit_all",
        lambda **kwargs: {
            "status": "incomplete",
            "summary": {
                "skills": 1,
                "prompt_artifacts_complete": 1,
                "study_artifacts_complete": 0,
                "outcomes_support_skill_advantage": 0,
            },
            "remediation": [
                {
                    "skill": "nv_reason_cxr",
                    "mode": "nemotron",
                    "command": "python tools/with_vs_without/run_nv_model_studies.py --first",
                },
                {
                    "skill": "nv_reason_cxr",
                    "mode": "nemotron",
                    "command": "python tools/with_vs_without/run_nv_model_studies.py --second",
                },
            ],
            "skills": [],
        },
    )

    report = packet.build_packet(mode="nemotron")

    assert report["status"] == "not_ready"
    assert report["approval_errors"][0]["check"] == "unique_direct_remediation_commands"
    assert report["approval_coverage"]["planned_direct_group_count"] == 1
    assert report["approval_coverage"]["planned_direct_command_count"] == 2
    assert report["approval_coverage"]["duplicate_direct_groups"] == [
        {"skill": "nv_reason_cxr", "mode": "nemotron"}
    ]
    assert "nv_reason_cxr:nemotron" in report["approval_errors"][0]["detail"]


def test_approval_packet_not_ready_when_direct_command_protocol_is_invalid(monkeypatch) -> None:
    monkeypatch.setattr(
        packet.preflight,
        "preflight",
        lambda **kwargs: {
            "status": "pass",
            "summary": {"checks": 1, "errors": 0, "warnings": 0},
            "checks": [],
        },
    )
    monkeypatch.setattr(
        packet.transfer,
        "build_manifest",
        lambda **kwargs: {
            "prompt_style": "minimal",
            "resume_missing": True,
            "payload_fingerprint": "f" * 64,
            "summary": {
                "pending_initial_calls": 2,
                "reused_repeats": 0,
                "max_possible_repair_calls": 2 * studies.DIRECT_MAX_CORRECTION_STEPS,
                "pending_transfer": {
                    "total_initial_bytes": 100,
                    "embedded_document_bytes": 50,
                    "by_endpoint_model": [],
                    "by_skill": [],
                },
            },
            "data_transfer_policy": {
                "initial_call": "initial",
                "repair_calls": "repair",
                "does_not_send": [],
            },
            "entries": [
                {
                    "status": "pending",
                    "skill": "nv_reason_cxr",
                    "mode": "nemotron-correction",
                },
            ],
        },
    )
    monkeypatch.setattr(
        packet.audit,
        "audit_all",
        lambda **kwargs: {
            "status": "incomplete",
            "summary": {
                "skills": 1,
                "prompt_artifacts_complete": 1,
                "study_artifacts_complete": 0,
                "outcomes_support_skill_advantage": 0,
            },
            "remediation": [
                {
                    "skill": "nv_reason_cxr",
                    "mode": "nemotron",
                    "command": (
                        "python tools/with_vs_without/run_nv_model_studies.py "
                        "--skills nv_reason_cxr --mode nemotron --prompt-style minimal "
                        f"--max-correction-steps {studies.DIRECT_MAX_CORRECTION_STEPS} "
                        f"--repeats {studies.DIRECT_REPEATS} --resume-missing"
                    ),
                },
            ],
            "skills": [],
        },
    )

    report = packet.build_packet(mode="nemotron")

    assert report["status"] == "not_ready"
    assert report["approval_errors"][0]["check"] == "direct_command_protocol"
    assert report["approval_coverage"]["pending_direct_group_count"] == 1
    assert report["approval_coverage"]["planned_direct_group_count"] == 1
    assert report["approval_coverage"]["missing_direct_group_count"] == 0
    assert report["approval_coverage"]["invalid_direct_command_count"] == 1
    assert studies.EXTERNAL_LLM_DATA_TRANSFER_FLAG in report["approval_errors"][0]["detail"]
