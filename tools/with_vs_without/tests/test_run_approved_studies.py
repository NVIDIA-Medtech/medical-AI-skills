import json
import subprocess
from pathlib import Path

import pytest

from tools.with_vs_without import run_approved_nv_model_studies as approved
from tools.with_vs_without import run_nv_model_studies as studies


def _packet() -> dict:
    return {
        "status": "ready_for_external_approval",
        "data_transfer": {
            "payload_fingerprint": "reviewed-payload",
            "summary": {
                "pending_initial_calls": 2,
                "max_possible_repair_calls": 2 * studies.DIRECT_MAX_CORRECTION_STEPS,
            }
        },
        "approval_errors": [],
        "approval_coverage": {
            "pending_direct_group_count": 1,
            "planned_direct_group_count": 1,
            "duplicate_direct_group_count": 0,
            "invalid_direct_command_count": 0,
        },
        "planned_commands": [
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
            }
        ],
    }


def test_build_plan_reuses_validated_approval_commands(monkeypatch) -> None:
    monkeypatch.setattr(approved.approval, "build_packet", lambda **kwargs: _packet())

    plan = approved.build_plan(mode="nemotron")

    assert plan["status"] == "ready_for_external_approval"
    assert plan["network_calls_made"] is False
    assert plan["payload_fingerprint"] == "reviewed-payload"
    assert plan["approval_errors"] == []
    assert plan["approval_coverage"]["planned_direct_group_count"] == 1
    assert plan["approval_coverage"]["duplicate_direct_group_count"] == 0
    assert plan["approval_coverage"]["invalid_direct_command_count"] == 0
    assert plan["command_count"] == 1
    assert plan["commands"][0]["argv"][:2] == [
        "python",
        "tools/with_vs_without/run_nv_model_studies.py",
    ]
    assert studies.EXTERNAL_LLM_DATA_TRANSFER_FLAG in plan["commands"][0]["argv"]


def test_format_markdown_includes_approval_coverage(monkeypatch) -> None:
    monkeypatch.setattr(approved.approval, "build_packet", lambda **kwargs: _packet())
    plan = approved.build_plan(mode="nemotron")

    text = approved._format_markdown(plan)

    assert "Direct remediation coverage: 1/1 pending skill/mode groups" in text
    assert "Direct remediation duplicate groups: 0" in text
    assert "Direct remediation invalid commands: 0" in text


def test_format_markdown_includes_approval_errors(monkeypatch) -> None:
    packet = _packet()
    packet["status"] = "not_ready"
    packet["approval_errors"] = [
        {
            "scope": "approval",
            "check": "direct_remediation_commands",
            "detail": "missing nv_reason_cxr:nemotron",
        }
    ]
    monkeypatch.setattr(approved.approval, "build_packet", lambda **kwargs: packet)
    plan = approved.build_plan(mode="nemotron")

    text = approved._format_markdown(plan)

    assert "## Approval Errors" in text
    assert "direct_remediation_commands" in text
    assert "missing nv_reason_cxr:nemotron" in text


def test_build_plan_rejects_command_without_approval_flag(monkeypatch) -> None:
    packet = _packet()
    packet["planned_commands"][0]["command"] = packet["planned_commands"][0]["command"].replace(
        f" {studies.EXTERNAL_LLM_DATA_TRANSFER_FLAG}",
        "",
    )
    monkeypatch.setattr(approved.approval, "build_packet", lambda **kwargs: packet)

    with pytest.raises(ValueError, match="missing required token"):
        approved.build_plan(mode="nemotron")


def test_build_plan_rejects_command_that_skips_local_preflight(monkeypatch) -> None:
    packet = _packet()
    packet["planned_commands"][0]["command"] += " --skip-local-preflight"
    monkeypatch.setattr(approved.approval, "build_packet", lambda **kwargs: packet)

    with pytest.raises(ValueError, match="unexpected option"):
        approved.build_plan(mode="nemotron")


def test_build_plan_rejects_duplicate_protocol_options(monkeypatch) -> None:
    packet = _packet()
    packet["planned_commands"][0]["command"] = packet["planned_commands"][0]["command"].replace(
        "--prompt-style minimal",
        "--prompt-style minimal --prompt-style path",
    )
    monkeypatch.setattr(approved.approval, "build_packet", lambda **kwargs: packet)

    with pytest.raises(ValueError, match="repeats option"):
        approved.build_plan(mode="nemotron")


def test_build_plan_rejects_multi_skill_command(monkeypatch) -> None:
    packet = _packet()
    packet["planned_commands"][0]["command"] = packet["planned_commands"][0]["command"].replace(
        "--skills nv_reason_cxr",
        "--skills nv_reason_cxr nv_segment_ct",
    )
    monkeypatch.setattr(approved.approval, "build_packet", lambda **kwargs: packet)

    with pytest.raises(ValueError, match="exactly one skill"):
        approved.build_plan(mode="nemotron")


def test_build_plan_rejects_command_metadata_skill_mismatch(monkeypatch) -> None:
    packet = _packet()
    packet["planned_commands"][0]["skill"] = "nv_segment_ct"
    monkeypatch.setattr(approved.approval, "build_packet", lambda **kwargs: packet)

    with pytest.raises(ValueError, match="metadata does not match --skills"):
        approved.build_plan(mode="nemotron")


def test_build_plan_rejects_command_metadata_mode_mismatch(monkeypatch) -> None:
    packet = _packet()
    packet["planned_commands"][0]["mode"] = "codex-opus"
    monkeypatch.setattr(approved.approval, "build_packet", lambda **kwargs: packet)

    with pytest.raises(ValueError, match="metadata does not match --mode"):
        approved.build_plan(mode="nemotron")


def test_build_plan_rejects_approval_ready_packet_without_commands(monkeypatch) -> None:
    packet = _packet()
    packet["planned_commands"] = []
    monkeypatch.setattr(approved.approval, "build_packet", lambda **kwargs: packet)

    with pytest.raises(ValueError, match="no direct remediation commands"):
        approved.build_plan(mode="nemotron")


def test_build_plan_rejects_duplicate_direct_command_groups(monkeypatch) -> None:
    packet = _packet()
    packet["planned_commands"].append(dict(packet["planned_commands"][0]))
    monkeypatch.setattr(approved.approval, "build_packet", lambda **kwargs: packet)

    with pytest.raises(ValueError, match="duplicate direct command group"):
        approved.build_plan(mode="nemotron")


def test_run_plan_dry_run_makes_no_network_calls(monkeypatch) -> None:
    monkeypatch.setattr(approved.approval, "build_packet", lambda **kwargs: _packet())
    plan = approved.build_plan(mode="nemotron")
    calls = []

    def fail_if_called(*args, **kwargs):
        calls.append(args)
        raise AssertionError("runner should not be called during dry-run")

    result = approved.run_plan(plan, execute=False, runner=fail_if_called)

    assert result["status"] == "dry_run"
    assert result["network_calls_made"] is False
    assert result["results"][0]["executed"] is False
    assert calls == []


def test_run_plan_dry_run_fails_closed_when_plan_not_ready(monkeypatch) -> None:
    packet = _packet()
    packet["status"] = "not_ready"
    packet["approval_errors"] = [{"check": "direct_remediation_commands"}]
    monkeypatch.setattr(approved.approval, "build_packet", lambda **kwargs: packet)
    plan = approved.build_plan(mode="nemotron")
    calls = []

    def fail_if_called(*args, **kwargs):
        calls.append(args)
        raise AssertionError("runner should not be called during not-ready dry-run")

    result = approved.run_plan(plan, execute=False, runner=fail_if_called)

    assert result["status"] == "not_ready"
    assert result["network_calls_made"] is False
    assert result["results"] == []
    assert calls == []


def test_run_plan_dry_run_succeeds_when_already_proven(monkeypatch) -> None:
    packet = _packet()
    packet["status"] = "already_proven"
    packet["planned_commands"] = []
    packet["data_transfer"]["summary"]["pending_initial_calls"] = 0
    packet["data_transfer"]["summary"]["max_possible_repair_calls"] = 0
    packet["approval_coverage"]["pending_direct_group_count"] = 0
    packet["approval_coverage"]["planned_direct_group_count"] = 0
    monkeypatch.setattr(approved.approval, "build_packet", lambda **kwargs: packet)
    plan = approved.build_plan(mode="nemotron")
    calls = []

    def fail_if_called(*args, **kwargs):
        calls.append(args)
        raise AssertionError("runner should not be called for an already-proven plan")

    result = approved.run_plan(plan, execute=False, runner=fail_if_called)

    assert result["status"] == "dry_run"
    assert result["network_calls_made"] is False
    assert result["results"] == []
    assert calls == []


def test_run_plan_execute_succeeds_without_network_when_already_proven(monkeypatch) -> None:
    packet = _packet()
    packet["status"] = "already_proven"
    packet["planned_commands"] = []
    packet["data_transfer"]["summary"]["pending_initial_calls"] = 0
    packet["data_transfer"]["summary"]["max_possible_repair_calls"] = 0
    packet["approval_coverage"]["pending_direct_group_count"] = 0
    packet["approval_coverage"]["planned_direct_group_count"] = 0
    monkeypatch.setattr(approved.approval, "build_packet", lambda **kwargs: packet)
    plan = approved.build_plan(mode="nemotron")
    calls = []

    def fail_if_called(*args, **kwargs):
        calls.append(args)
        raise AssertionError("runner should not be called for an already-proven plan")

    result = approved.run_plan(plan, execute=True, runner=fail_if_called)

    assert result["status"] == "executed"
    assert result["network_calls_made"] is False
    assert result["results"] == []
    assert calls == []


def test_run_plan_logs_approval_errors_for_not_ready_dry_run(monkeypatch, tmp_path: Path) -> None:
    packet = _packet()
    packet["status"] = "not_ready"
    packet["approval_errors"] = [
        {
            "scope": "approval",
            "check": "direct_remediation_commands",
            "detail": "missing nv_reason_cxr:nemotron",
        }
    ]
    monkeypatch.setattr(approved.approval, "build_packet", lambda **kwargs: packet)
    plan = approved.build_plan(mode="nemotron")
    log_path = tmp_path / "approved.jsonl"

    result = approved.run_plan(plan, execute=False, log_path=log_path)

    assert result["status"] == "not_ready"
    events = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert events[0]["event"] == "plan"
    assert events[0]["approval_errors"] == packet["approval_errors"]


def test_run_plan_execute_calls_runner(monkeypatch) -> None:
    monkeypatch.setattr(approved.approval, "build_packet", lambda **kwargs: _packet())
    plan = approved.build_plan(mode="nemotron")
    calls = []

    def fake_runner(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0)

    result = approved.run_plan(plan, execute=True, runner=fake_runner)

    assert result["status"] == "executed"
    assert result["network_calls_made"] is True
    assert result["results"][0]["returncode"] == 0
    assert calls[0][0][1] == "tools/with_vs_without/run_nv_model_studies.py"


def test_run_plan_writes_execution_log(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(approved.approval, "build_packet", lambda **kwargs: _packet())
    plan = approved.build_plan(mode="nemotron")
    log_path = tmp_path / "approved.jsonl"

    def fake_runner(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 0)

    result = approved.run_plan(plan, execute=True, log_path=log_path, runner=fake_runner)

    assert result["status"] == "executed"
    assert result["log_path"] == str(log_path)
    events = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert [event["event"] for event in events] == ["plan", "command_start", "command_end"]
    assert events[-1]["returncode"] == 0
    assert events[-1]["command"] == plan["commands"][0]["command"]
    assert events[-1]["payload_fingerprint"] == plan["payload_fingerprint"]


def test_resume_log_rechecks_commands_still_required_by_current_audit(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(approved.approval, "build_packet", lambda **kwargs: _packet())
    plan = approved.build_plan(mode="nemotron")
    log_path = tmp_path / "approved.jsonl"
    log_path.write_text(
        json.dumps(
            {
                "event": "command_end",
                "command": plan["commands"][0]["command"],
                "returncode": 0,
                "payload_fingerprint": plan["payload_fingerprint"],
            }
        )
        + "\n"
    )
    calls = []

    def fake_runner(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0)

    result = approved.run_plan(
        plan,
        execute=True,
        log_path=log_path,
        resume_log=True,
        runner=fake_runner,
    )

    assert result["status"] == "executed"
    assert result["results"][0]["prior_success_in_log"] is True
    assert result["results"][0]["reason"] == "current_audit_still_requires_command"
    assert result["results"][0]["returncode"] == 0
    assert len(calls) == 1
    events = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert "command_prior_success_ignored" in [event["event"] for event in events]


def test_resume_log_does_not_skip_different_review_payload(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(approved.approval, "build_packet", lambda **kwargs: _packet())
    plan = approved.build_plan(mode="nemotron")
    log_path = tmp_path / "approved.jsonl"
    log_path.write_text(
        json.dumps(
            {
                "event": "command_end",
                "command": plan["commands"][0]["command"],
                "returncode": 0,
                "payload_fingerprint": "old-payload",
            }
        )
        + "\n"
    )
    calls = []

    def fake_runner(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0)

    result = approved.run_plan(
        plan,
        execute=True,
        log_path=log_path,
        resume_log=True,
        runner=fake_runner,
    )

    assert result["status"] == "executed"
    assert result["results"][0]["returncode"] == 0
    assert len(calls) == 1


def test_cli_execute_requires_explicit_confirmation() -> None:
    with pytest.raises(SystemExit) as excinfo:
        approved.main(["--execute", "--mode", "nemotron"])

    assert excinfo.value.code == 2


def test_cli_dry_run_returns_nonzero_for_not_ready_plan(
    monkeypatch,
    tmp_path: Path,
) -> None:
    packet = _packet()
    packet["status"] = "not_ready"
    packet["approval_errors"] = [{"check": "direct_remediation_commands"}]
    monkeypatch.setattr(approved.approval, "build_packet", lambda **kwargs: packet)

    rc = approved.main(
        ["--mode", "nemotron", "--format", "json", "--log", str(tmp_path / "none.jsonl")]
    )

    assert rc == 1
