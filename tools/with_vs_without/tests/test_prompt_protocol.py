import json
import os
import re
from dataclasses import replace
from pathlib import Path

import pytest

from tools.with_vs_without import run_nv_model_studies as studies


LEAK_RE = re.compile(
    r"configs/|run_[a-z0-9_]+\.py|monai\.bundle|scripts\.|model-name|"
    r"label IDs are|required label IDs"
)


def test_path_prompts_are_a2_style_and_do_not_embed_docs() -> None:
    for skill, scenario in studies.SCENARIOS.items():
        for arm in ("with", "without"):
            out_dir = studies.RUN_ROOT / "_prompt_test" / skill / arm
            prompt = studies._prompt(scenario, arm, out_dir, "path")

            assert "Documentation available to you:" not in prompt
            assert "fresh per-arm Python environment" in prompt
            assert "SINGLE shell command" in prompt
            assert "Do not run the command yourself." in prompt
            assert "stage edited runtime files under the requested output directory" in prompt
            assert not LEAK_RE.search(prompt)
            assert "The only workflow document available to you is" in prompt
            assert "Read that document." in prompt

            skill_dir = studies._skill_doc_dir(scenario)
            if arm == "with":
                assert f"The only workflow document available to you is {scenario.with_doc[0]}" in prompt
                assert f"Do not inspect any other files under {skill_dir}/" in prompt
            else:
                assert f"Do not read or use any files under {skill_dir}/" in prompt
                assert scenario.without_doc[0] in prompt


def test_direct_minimal_prompt_prefix_does_not_leak_operational_markers() -> None:
    for scenario in studies.SCENARIOS.values():
        for arm in ("with", "without"):
            out_dir = studies.RUN_ROOT / "_prompt_test" / scenario.skill / arm
            prompt = studies._prompt(scenario, arm, out_dir, "minimal")
            prefix = prompt.split("Documentation available to you:", 1)[0]
            source_name = Path(scenario.fixture).name

            assert source_name not in prefix
            assert scenario.fixture not in prefix
            assert "Do not write to or modify .workbench_data/upstreams" in prefix
            for marker in scenario.tier1 + scenario.tier2:
                assert marker not in prefix


def test_direct_minimal_prompt_embeds_full_selected_document() -> None:
    scenario = studies.SCENARIOS["nv_segment_ct"]
    out_dir = studies.RUN_ROOT / "_prompt_test" / scenario.skill / "without"
    prompt = studies._prompt(scenario, "without", out_dir, "minimal")
    doc_text = (studies.REPO_ROOT / scenario.without_doc[0]).read_text(errors="replace")

    assert "[missing document:" not in prompt
    assert "[truncated]" not in prompt
    assert doc_text in prompt


def test_message_text_prefers_content_before_reasoning_fallback() -> None:
    assert studies._message_text({"content": "visible", "reasoning_content": "hidden"}) == "visible"
    assert studies._message_text({"content": "", "reasoning_content": "fallback"}) == "fallback"
    assert studies._message_text({"content": [{"text": "part one"}, {"text": "part two"}]}) == "part one\npart two"


def test_chat_payload_uses_provider_defaults(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "choices": [{"message": {"content": "ok"}}],
                    "usage": {"total_tokens": 1},
                }
            ).encode()

    def fake_urlopen(req, timeout):
        captured["payload"] = json.loads(req.data.decode())
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(studies, "_read_env_value", lambda name: "secret-token")
    monkeypatch.setattr(studies.urllib.request, "urlopen", fake_urlopen)

    text, usage = studies._chat(
        studies.BACKENDS["nemotron"],
        [{"role": "user", "content": "say ok"}],
    )

    assert text == "ok"
    assert usage == {"total_tokens": 1}
    assert captured["payload"] == {
        "model": "nvidia/nvidia/nemotron-3-super-v3",
        "messages": [{"role": "user", "content": "say ok"}],
    }
    assert captured["timeout"] == studies.CHAT_URLOPEN_TIMEOUT_S


def test_without_arm_docs_are_committed_upstream_snapshots() -> None:
    for scenario in studies.SCENARIOS.values():
        for doc in scenario.without_doc:
            assert doc.startswith("tools/with_vs_without/upstream_docs/")
            assert (studies.REPO_ROOT / doc).is_file()
            assert ".workbench_data/" not in doc


def test_direct_runner_builds_clean_exec_env(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(studies, "RUN_ROOT", tmp_path / "runs")
    monkeypatch.setenv("PYTHONPATH", "leaky-host-path")
    out_dir = studies.RUN_ROOT / "skill_codex_opus" / "backend" / "with"

    env, venv_dir, python_bin, fresh_env_created = studies._build_isolated_exec_env(out_dir)

    assert env["PATH"].split(os.pathsep)[0] == str(venv_dir / "bin")
    assert env["VIRTUAL_ENV"] == str(venv_dir)
    assert env["PYTHONNOUSERSITE"] == "1"
    assert "PYTHONPATH" not in env
    assert python_bin.is_file()
    assert fresh_env_created is True


def test_direct_api_cli_requires_external_data_transfer_confirmation(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        studies.main(["--skills", "nv_reason_cxr", "--mode", "nemotron"])

    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert studies.EXTERNAL_LLM_DATA_TRANSFER_FLAG in captured.err
    assert "external LLM API" in captured.err


def test_prompt_artifact_cli_rejects_embedded_doc_prompt_style(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        studies.main(
            [
                "--skills",
                "nv_reason_cxr",
                "--mode",
                "prompts",
                "--prompt-style",
                "minimal",
            ]
        )

    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "--mode prompts" in captured.err
    assert "--prompt-style path" in captured.err


def test_direct_api_cli_rejects_legacy_guarded_prompt_style(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        studies.main(
            [
                "--skills",
                "nv_reason_cxr",
                "--mode",
                "nemotron",
                "--prompt-style",
                "guarded",
                studies.EXTERNAL_LLM_DATA_TRANSFER_FLAG,
            ]
        )

    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "--prompt-style minimal" in captured.err
    assert "fair comparison protocol" in captured.err


def test_cli_rejects_non_protocol_correction_budget_before_transfer(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        studies.main(
            [
                "--skills",
                "nv_reason_cxr",
                "--mode",
                "nemotron",
                "--prompt-style",
                "minimal",
                "--max-correction-steps",
                "3",
                studies.EXTERNAL_LLM_DATA_TRANSFER_FLAG,
                "--skip-local-preflight",
            ]
        )

    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert f"--max-correction-steps {studies.DIRECT_MAX_CORRECTION_STEPS}" in captured.err


def test_direct_cli_rejects_non_protocol_repeat_count_before_transfer(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        studies.main(
            [
                "--skills",
                "nv_reason_cxr",
                "--mode",
                "nemotron",
                "--prompt-style",
                "minimal",
                "--repeats",
                "1",
                studies.EXTERNAL_LLM_DATA_TRANSFER_FLAG,
                "--skip-local-preflight",
            ]
        )

    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert f"--repeats {studies.DIRECT_REPEATS}" in captured.err


def test_direct_cli_allows_explicit_debug_budget(tmp_path, monkeypatch, capsys) -> None:
    calls: list[tuple[int, str, int]] = []

    def fake_run_nemotron(skills, max_steps, prompt_style, repeats, *, resume_missing=False):
        calls.append((max_steps, prompt_style, repeats))

    monkeypatch.setattr(studies, "_stage_input", lambda scenario: tmp_path / scenario.skill)
    monkeypatch.setattr(studies, "run_nemotron", fake_run_nemotron)

    studies.main(
        [
            "--skills",
            "nv_reason_cxr",
            "--mode",
            "nemotron",
            "--prompt-style",
            "minimal",
            "--max-correction-steps",
            "1",
            "--repeats",
            "1",
            "--allow-debug-budget",
            studies.EXTERNAL_LLM_DATA_TRANSFER_FLAG,
            "--skip-local-preflight",
        ]
    )

    assert calls == [(1, "minimal", 1)]
    captured = capsys.readouterr()
    assert "debug budget enabled" in captured.err


def test_prompt_artifact_cli_does_not_require_external_data_transfer_confirmation(
    tmp_path,
    monkeypatch,
) -> None:
    calls: list[tuple[list[str], str, Path, int, int]] = []

    def fake_write_prompt_artifacts(skills, prompt_style, artifact_dir, *, max_steps, repeats):
        calls.append((list(skills), prompt_style, artifact_dir, max_steps, repeats))

    monkeypatch.setattr(studies, "_stage_input", lambda scenario: tmp_path / scenario.skill)
    monkeypatch.setattr(studies, "write_prompt_artifacts", fake_write_prompt_artifacts)

    studies.main(
        [
            "--skills",
            "nv_reason_cxr",
            "--mode",
            "prompts",
            "--prompt-style",
            "path",
            "--repeats",
            "1",
            "--prompt-artifact-dir",
            str(tmp_path),
        ]
    )

    assert calls == [(["nv_reason_cxr"], "path", tmp_path, studies.DIRECT_MAX_CORRECTION_STEPS, 1)]


def test_direct_cli_write_prompt_artifacts_uses_path_style(
    tmp_path,
    monkeypatch,
) -> None:
    calls: list[tuple[list[str], str, Path, int, int]] = []

    def fake_write_prompt_artifacts(skills, prompt_style, artifact_dir, *, max_steps, repeats):
        calls.append((list(skills), prompt_style, artifact_dir, max_steps, repeats))

    monkeypatch.setattr(studies, "_stage_input", lambda scenario: tmp_path / scenario.skill)
    monkeypatch.setattr(studies, "write_prompt_artifacts", fake_write_prompt_artifacts)
    monkeypatch.setattr(studies, "run_nemotron", lambda *args, **kwargs: None)

    studies.main(
        [
            "--skills",
            "nv_reason_cxr",
            "--mode",
            "nemotron",
            "--prompt-style",
            "minimal",
            "--write-prompt-artifacts",
            "--prompt-artifact-dir",
            str(tmp_path),
            studies.EXTERNAL_LLM_DATA_TRANSFER_FLAG,
            "--skip-local-preflight",
        ]
    )

    assert calls == [
        (["nv_reason_cxr"], "path", tmp_path, studies.DIRECT_MAX_CORRECTION_STEPS, studies.DIRECT_REPEATS)
    ]


def test_direct_cli_runs_local_preflight_before_external_modes(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(studies, "_stage_input", lambda scenario: tmp_path / scenario.skill)
    monkeypatch.setattr(studies, "run_nemotron", lambda *args, **kwargs: None)

    with pytest.raises(SystemExit) as exc:
        studies.main(
            [
                "--skills",
                "nv_reason_cxr",
                "--mode",
                "nemotron",
                "--prompt-style",
                "minimal",
                "--prompt-artifact-dir",
                str(tmp_path),
                studies.EXTERNAL_LLM_DATA_TRANSFER_FLAG,
            ]
        )

    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "local preflight failed" in captured.err
    assert "prompt artifact is missing" in captured.err


def test_direct_cli_preflight_enforces_scenario_contract(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    skill = "nv_reason_cxr"
    scenario = replace(
        studies.SCENARIOS[skill],
        user_goal="Write outputs under {out_dir}.",
    )
    monkeypatch.setitem(studies.SCENARIOS, skill, scenario)
    monkeypatch.setattr(studies, "_read_env_value", lambda name: "secret-token")
    monkeypatch.setattr(studies, "_stage_input", lambda scenario: tmp_path / scenario.skill)
    monkeypatch.setattr(studies, "run_nemotron", lambda *args, **kwargs: None)

    with pytest.raises(SystemExit) as exc:
        studies.main(
            [
                "--skills",
                skill,
                "--mode",
                "nemotron",
                "--prompt-style",
                "minimal",
                "--prompt-artifact-dir",
                str(tmp_path),
                studies.EXTERNAL_LLM_DATA_TRANSFER_FLAG,
            ]
        )

    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "local preflight failed" in captured.err
    assert "user_goal is missing required placeholder(s): {input_path}" in captured.err


def test_direct_cli_preflight_can_be_skipped_for_debugging(tmp_path, monkeypatch) -> None:
    calls = 0
    subprocess_calls = 0

    def fake_run_nemotron(*args, **kwargs):
        nonlocal calls
        calls += 1

    def fail_subprocess_run(*args, **kwargs):
        nonlocal subprocess_calls
        subprocess_calls += 1
        raise AssertionError("direct CLI should not fetch or clone upstream documentation")

    monkeypatch.setattr(studies.subprocess, "run", fail_subprocess_run)
    monkeypatch.setattr(studies, "_stage_input", lambda scenario: tmp_path / scenario.skill)
    monkeypatch.setattr(studies, "run_nemotron", fake_run_nemotron)

    studies.main(
        [
            "--skills",
            "nv_reason_cxr",
            "--mode",
            "nemotron",
            "--prompt-style",
            "minimal",
            "--prompt-artifact-dir",
            str(tmp_path),
            studies.EXTERNAL_LLM_DATA_TRANSFER_FLAG,
            "--skip-local-preflight",
        ]
    )

    assert calls == 1
    assert subprocess_calls == 0


def test_all_mode_uses_interleaved_runner(tmp_path, monkeypatch) -> None:
    calls: list[tuple[list[str], str, int, int, bool]] = []

    def fake_run_all_interleaved(skills, prompt_style, max_steps, repeats, *, resume_missing=False):
        calls.append((list(skills), prompt_style, max_steps, repeats, resume_missing))

    def fail_serial_runner(*args, **kwargs):
        raise AssertionError("--mode all should use run_all_interleaved")

    monkeypatch.setattr(studies, "_stage_input", lambda scenario: tmp_path / scenario.skill)
    monkeypatch.setattr(studies, "run_all_interleaved", fake_run_all_interleaved)
    monkeypatch.setattr(studies, "run_codex_opus", fail_serial_runner)
    monkeypatch.setattr(studies, "run_nemotron", fail_serial_runner)

    studies.main(
        [
            "--skills",
            "nv_reason_cxr",
            "--mode",
            "all",
            "--prompt-style",
            "minimal",
            studies.EXTERNAL_LLM_DATA_TRANSFER_FLAG,
            "--skip-local-preflight",
        ]
    )

    assert calls == [
        (
            ["nv_reason_cxr"],
            "minimal",
            studies.DIRECT_MAX_CORRECTION_STEPS,
            studies.DIRECT_REPEATS,
            False,
        )
    ]


def test_prompt_artifacts_are_repeat_specific() -> None:
    records = studies._prompt_artifact_records(
        "nv_segment_ct",
        "path",
        max_steps=studies.DIRECT_MAX_CORRECTION_STEPS,
        repeats=3,
    )

    assert len(records) == 18
    assert {record["repeat"] for record in records} == {1, 2, 3}
    assert len({record["id"] for record in records}) == len(records)
    for record in records:
        assert record["repeat_count"] == 3
        assert "/repeat_" in record["expected_output_dir"]
        assert record["expected_output_dir"] in record["question"]


def test_nv_model_prompt_artifacts_are_generated_per_repeat() -> None:
    import json
    from pathlib import Path

    files = sorted(Path("tools/nat_audit/data").glob("eval_nv_model_studies_*_prompts.json"))
    assert files
    for path in files:
        rows = json.loads(path.read_text())
        assert len(rows) == 6 * studies.DIRECT_REPEATS
        assert {row["repeat"] for row in rows} == set(range(1, studies.DIRECT_REPEATS + 1))
        assert len({row["id"] for row in rows}) == len(rows)
        for row in rows:
            assert "/repeat_" in row["expected_output_dir"]
            assert row["expected_output_dir"] in row["question"]
            assert row["repeat_count"] == studies.DIRECT_REPEATS
            backend = studies.BACKENDS[row["backend"]]
            assert row["backend_model"] == backend.model
            assert row["backend_protocol"] == studies._backend_protocol(backend)


def test_nv_model_path_prompts_use_neutral_staged_input_names() -> None:
    for skill, scenario in studies.SCENARIOS.items():
        records = studies._prompt_artifact_records(skill, "path", max_steps=studies.DIRECT_MAX_CORRECTION_STEPS, repeats=1)
        source_name = Path(scenario.fixture).name
        for record in records:
            staged = record["staged_user_input"]
            assert Path(staged).name in {"input.nii.gz", "request.json", "input_dataset"}
            assert staged in record["question"]
            assert source_name not in record["question"]
            assert source_name not in staged
