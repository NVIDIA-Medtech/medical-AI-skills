import json
from pathlib import Path

from tools.with_vs_without import manifest_nv_model_data_transfer as transfer
from tools.with_vs_without import run_nv_model_studies as studies


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def _valid_repeat(skill: str, mode: str, backend: str, arm: str, repeat: int) -> dict[str, object]:
    run_mode = "codex_opus" if mode == "codex-opus" else "nemotron_correction"
    scenario = studies.SCENARIOS[skill]
    backend_obj = studies.BACKENDS[backend]
    out_dir = studies._repeat_out_dir(skill, run_mode, backend_obj, arm, repeat)
    staged_input = studies._staged_input_path(scenario).relative_to(studies.REPO_ROOT)
    command = f"python {scenario.tier1[0]} {staged_input} --output-dir {out_dir.relative_to(studies.REPO_ROOT)}"
    score = {"passed": True, "score": 5, "tiers": []}
    attempt = {
        "backend": backend,
        "model": backend_obj.model,
        "backend_protocol": studies._backend_protocol(backend_obj),
        "arm": arm,
        "step": 0,
        "messages": [
            {"role": "system", "content": studies.DIRECT_SYSTEM_PROMPT},
            {"role": "user", "content": studies._prompt(scenario, arm, out_dir, "minimal")},
        ],
        "response": f"```bash\n{command}\n```",
        "command": command,
        "usage": {},
        "execution": {"executed": True, "exit_code": 0, "generated_files": []},
        "score": score,
    }
    return {
        "backend": backend,
        "backend_label": backend_obj.label,
        "model": backend_obj.model,
        "backend_protocol": studies._backend_protocol(backend_obj),
        "arm": arm,
        "repeat": repeat,
        "output_dir": str(out_dir.relative_to(studies.REPO_ROOT)),
        "staged_user_input": str(staged_input),
        "prompt_style": "minimal",
        "max_correction_steps": studies.DIRECT_MAX_CORRECTION_STEPS,
        "steps_to_pass": 0,
        "command": command,
        "execution": {"executed": True, "exit_code": 0, "generated_files": []},
        "attempts": [attempt],
        "score": score,
    }


def test_manifest_lists_pending_initial_calls_without_full_prompts(tmp_path: Path) -> None:
    manifest = transfer.build_manifest(
        skills=["nv_reason_cxr"],
        mode="nemotron",
        repeats=1,
        study_root=tmp_path,
    )

    assert manifest["network_calls_made"] is False
    assert len(manifest["payload_fingerprint"]) == 64
    assert manifest["summary"]["pending_initial_calls"] == 2
    assert manifest["summary"]["max_possible_repair_calls"] == 2 * studies.DIRECT_MAX_CORRECTION_STEPS
    assert manifest["summary"]["reused_repeats"] == 0
    assert manifest["summary"]["prompt_policy_issue_count"] == 0
    assert manifest["prompt_policy_issues"] == []
    assert len(manifest["entries"]) == 2
    pending_transfer = manifest["summary"]["pending_transfer"]
    assert pending_transfer["pending_initial_calls"] == 2
    assert pending_transfer["total_initial_bytes"] == sum(
        entry["system_prompt_bytes"] + entry["user_prompt_bytes"]
        for entry in manifest["entries"]
    )
    assert pending_transfer["embedded_document_bytes"] == sum(
        sum(doc["byte_count"] for doc in entry["documentation"])
        for entry in manifest["entries"]
    )
    assert pending_transfer["by_endpoint_model"][0]["pending_initial_calls"] == 2
    assert pending_transfer["by_skill"][0]["skill"] == "nv_reason_cxr"
    protocols = manifest["summary"]["backend_protocols"]
    assert len(protocols) == 1
    assert protocols[0]["backend"] == "nemotron"
    assert protocols[0]["temperature"] is None
    assert protocols[0]["top_p"] is None
    assert protocols[0]["max_tokens"] is None
    assert protocols[0]["extra_body"] == {}
    assert protocols[0]["retry_attempts"] == studies.CHAT_RETRY_ATTEMPTS
    assert len(protocols[0]["protocol_sha256"]) == 64
    first = manifest["entries"][0]
    assert first["status"] == "pending"
    assert first["endpoint"] == studies.BACKENDS["nemotron"].base_url
    assert first["backend_protocol"] == studies._backend_protocol(studies.BACKENDS["nemotron"])
    assert first["prompt_style"] == "minimal"
    assert first["max_correction_steps"] == studies.DIRECT_MAX_CORRECTION_STEPS
    assert first["user_prompt_bytes"] > 1000
    assert first["documentation"][0]["exists"] is True
    assert "user_prompt" not in first

    text = transfer._format_markdown(manifest)
    assert "Pending initial external LLM calls: 2" in text
    assert "Reviewed payload fingerprint:" in text
    assert "Pending initial payload bytes:" in text
    assert "Pending prompt policy issues: 0" in text
    assert "Initial prompt guard:" in text
    assert "## Backend Protocols" in text
    assert "| nemotron |" in text
    assert "chat 420s; urlopen 300s" in text
    assert "## Aggregate Pending Transfer" in text
    assert "No network calls were made" in text
    assert "Rows are grouped" in text
    assert "| nv_reason_cxr | nemotron-correction | nemotron | with | 1-1 (1) |" in text


def test_manifest_flags_pending_prompt_home_path_without_echoing_secret(
    monkeypatch,
    tmp_path: Path,
) -> None:
    secret_path = "/" + "home" + "/alice/private/token.txt"
    original_read_doc = studies._read_doc

    def read_doc_with_home_path(path: str) -> str:
        return original_read_doc(path) + f"\nLocal setup example: {secret_path}\n"

    monkeypatch.setattr(studies, "_read_doc", read_doc_with_home_path)

    manifest = transfer.build_manifest(
        skills=["nv_reason_cxr"],
        mode="nemotron",
        repeats=1,
        study_root=tmp_path,
    )

    issues = manifest["prompt_policy_issues"]
    assert manifest["summary"]["prompt_policy_issue_count"] == 2
    assert len(issues) == 2
    assert {issue["prompt"] for issue in issues} == {"user"}
    assert {issue["issue"] for issue in issues} == {"local_absolute_home_path"}
    assert {issue["match_sha256"] for issue in issues} == {transfer._sha256_text(secret_path)}
    assert secret_path not in json.dumps(manifest)

    text = transfer._format_markdown(manifest)
    assert "## Prompt Payload Policy Issues" in text
    assert "local_absolute_home_path" in text
    assert "matched text is redacted" in text
    assert secret_path not in text


def test_manifest_can_include_full_prompts_for_local_review(tmp_path: Path) -> None:
    manifest = transfer.build_manifest(
        skills=["nv_reason_cxr"],
        mode="nemotron",
        repeats=1,
        study_root=tmp_path,
        include_prompts=True,
    )

    first = manifest["entries"][0]
    assert first["system_prompt"] == studies.DIRECT_SYSTEM_PROMPT
    assert "Documentation available to you:" in first["user_prompt"]
    assert "skills/nv-reason-cxr/SKILL.md" in first["user_prompt"]


def test_manifest_respects_resume_missing_for_valid_repeats(tmp_path: Path) -> None:
    skill = "nv_reason_cxr"
    repeat_path = (
        tmp_path
        / f"{skill}_nemotron_correction"
        / "repeats"
        / "with_repeat_1.json"
    )
    _write_json(repeat_path, _valid_repeat(skill, "nemotron-correction", "nemotron", "with", 1))

    manifest = transfer.build_manifest(
        skills=[skill],
        mode="nemotron",
        repeats=1,
        study_root=tmp_path,
    )

    assert manifest["summary"]["pending_initial_calls"] == 1
    assert manifest["summary"]["reused_repeats"] == 1
    statuses = {(entry["arm"], entry["status"]) for entry in manifest["entries"]}
    assert statuses == {("with", "reused"), ("without", "pending")}


def test_payload_fingerprint_includes_backend_protocol_and_repair_budget(tmp_path: Path) -> None:
    manifest = transfer.build_manifest(
        skills=["nv_reason_cxr"],
        mode="nemotron",
        repeats=1,
        study_root=tmp_path,
    )
    entries = manifest["entries"]
    original = transfer.transfer_payload_fingerprint(entries)

    changed_protocol = [dict(entry) for entry in entries]
    changed_protocol[0] = {
        **changed_protocol[0],
        "backend_protocol": {
            **changed_protocol[0]["backend_protocol"],
            "provider_defaults": False,
        },
    }
    changed_budget = [dict(entry) for entry in entries]
    changed_budget[0] = {
        **changed_budget[0],
        "max_correction_steps": 1,
    }

    assert transfer.transfer_payload_fingerprint(changed_protocol) != original
    assert transfer.transfer_payload_fingerprint(changed_budget) != original
