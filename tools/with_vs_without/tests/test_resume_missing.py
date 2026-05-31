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

from pathlib import Path

from tools.with_vs_without import run_nv_model_studies as studies


def _safe_marker_for_arm(skill: str, arm: str) -> str:
    scenario = studies.SCENARIOS[skill]
    if arm == "with":
        return scenario.tier1[0]
    forbidden = studies._repair_feedback_forbidden_markers(scenario, "without")
    for marker in scenario.tier1:
        if marker and not any(hidden and hidden in marker for hidden in forbidden):
            return marker
    return scenario.tier1[0]


def _fake_result(
    backend: studies.Backend, arm: str, repeat: int, out_dir: Path
) -> dict[str, object]:
    skill = "nv_segment_ct"
    staged_input = studies._staged_input_path(studies.SCENARIOS[skill]).relative_to(
        studies.REPO_ROOT
    )
    command = (
        f"python {_safe_marker_for_arm(skill, arm)} {staged_input} "
        f"--output-dir {out_dir.relative_to(studies.REPO_ROOT)}"
    )
    execution = {"executed": True, "exit_code": 0, "generated_files": []}
    score = {"passed": True, "score": 5, "tiers": []}
    return {
        "backend": backend.key,
        "backend_label": backend.label,
        "model": backend.model,
        "backend_protocol": studies._backend_protocol(backend),
        "arm": arm,
        "repeat": repeat,
        "output_dir": str(out_dir.relative_to(studies.REPO_ROOT)),
        "staged_user_input": str(
            studies._staged_input_path(studies.SCENARIOS[skill]).relative_to(studies.REPO_ROOT)
        ),
        "prompt_style": "minimal",
        "attempts": [
            {
                "backend": backend.key,
                "model": backend.model,
                "backend_protocol": studies._backend_protocol(backend),
                "arm": arm,
                "step": 0,
                "messages": [
                    {"role": "system", "content": studies.DIRECT_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": studies._prompt(
                            studies.SCENARIOS[skill], arm, out_dir, "minimal"
                        ),
                    },
                ],
                "response": f"```bash\n{command}\n```",
                "command": command,
                "usage": {},
                "execution": execution,
                "score": score,
            }
        ],
        "command": command,
        "execution": execution,
        "score": score,
        "steps_to_pass": 0,
        "max_correction_steps": studies.DIRECT_MAX_CORRECTION_STEPS,
    }


def test_codex_opus_resume_missing_reuses_valid_repeat_json(tmp_path, monkeypatch) -> None:
    study_root = tmp_path / "studies"
    monkeypatch.setattr(studies, "STUDY_ROOT", study_root)

    skill = "nv_segment_ct"
    backend = studies.BACKENDS["gpt55"]
    study = study_root / f"{skill}_codex_opus"
    existing_path = study / "repeats" / "gpt55_with_repeat_1.json"
    existing = _fake_result(
        backend,
        "with",
        1,
        studies._repeat_out_dir(skill, "codex_opus", backend, "with", 1),
    )
    studies._write_json(existing_path, existing)

    calls: list[tuple[str, str, int]] = []

    def fake_run_repair_loop(*, scenario, backend, arm, out_dir, prompt_style, max_steps):
        repeat = int(out_dir.name.rsplit("_", 1)[-1])
        calls.append((backend.key, arm, repeat))
        return [], _fake_result(backend, arm, repeat, out_dir)

    monkeypatch.setattr(studies, "_run_repair_loop", fake_run_repair_loop)

    studies.run_codex_opus(
        [skill],
        "minimal",
        max_steps=studies.DIRECT_MAX_CORRECTION_STEPS,
        repeats=1,
        resume_missing=True,
    )

    assert ("gpt55", "with", 1) not in calls
    assert ("gpt55", "without", 1) in calls
    assert ("opus", "with", 1) in calls
    assert ("opus", "without", 1) in calls
    aggregate = studies.json.loads((study / "gpt55_with.json").read_text())
    assert aggregate["repeat_count"] == 1
    assert aggregate["summary"]["pass_count"] == 1


def test_invalid_existing_repeat_is_rerun(tmp_path, monkeypatch) -> None:
    study_root = tmp_path / "studies"
    monkeypatch.setattr(studies, "STUDY_ROOT", study_root)

    skill = "nv_segment_ct"
    study = study_root / f"{skill}_nemotron_correction"
    invalid_path = study / "repeats" / "with_repeat_1.json"
    studies._write_json(invalid_path, {"backend": "nemotron", "arm": "with", "repeat": 999})

    calls: list[tuple[str, int]] = []

    def fake_run_repair_loop(*, scenario, backend, arm, out_dir, prompt_style, max_steps):
        repeat = int(out_dir.name.rsplit("_", 1)[-1])
        calls.append((arm, repeat))
        return [], _fake_result(backend, arm, repeat, out_dir)

    monkeypatch.setattr(studies, "_run_repair_loop", fake_run_repair_loop)

    studies.run_nemotron(
        [skill],
        max_steps=studies.DIRECT_MAX_CORRECTION_STEPS,
        prompt_style="minimal",
        repeats=1,
        resume_missing=True,
    )

    assert ("with", 1) in calls
    assert ("without", 1) in calls
    rewritten = studies.json.loads(invalid_path.read_text())
    assert rewritten["repeat"] == 1
    assert rewritten["output_dir"].endswith("/repeat_1")


def test_all_interleaved_rotates_backends_within_each_skill(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(studies, "STUDY_ROOT", tmp_path / "studies")

    calls: list[tuple[str, int, str, str, str]] = []

    def fake_load_or_run_repeat(
        *,
        scenario,
        skill,
        study,
        mode,
        backend,
        arm,
        repeat,
        repeats,
        prompt_style,
        max_steps,
        resume_missing,
    ):
        calls.append((skill, repeat, arm, backend.key, mode))
        out_dir = studies._repeat_out_dir(skill, mode, backend, arm, repeat)
        return _fake_result(backend, arm, repeat, out_dir)

    monkeypatch.setattr(studies, "_load_or_run_repeat", fake_load_or_run_repeat)

    studies.run_all_interleaved(
        ["nv_segment_ct"],
        "minimal",
        max_steps=studies.DIRECT_MAX_CORRECTION_STEPS,
        repeats=2,
    )

    assert calls == [
        ("nv_segment_ct", 1, "with", "gpt55", "codex_opus"),
        ("nv_segment_ct", 1, "with", "opus", "codex_opus"),
        ("nv_segment_ct", 1, "with", "nemotron", "nemotron_correction"),
        ("nv_segment_ct", 1, "without", "gpt55", "codex_opus"),
        ("nv_segment_ct", 1, "without", "opus", "codex_opus"),
        ("nv_segment_ct", 1, "without", "nemotron", "nemotron_correction"),
        ("nv_segment_ct", 2, "with", "gpt55", "codex_opus"),
        ("nv_segment_ct", 2, "with", "opus", "codex_opus"),
        ("nv_segment_ct", 2, "with", "nemotron", "nemotron_correction"),
        ("nv_segment_ct", 2, "without", "gpt55", "codex_opus"),
        ("nv_segment_ct", 2, "without", "opus", "codex_opus"),
        ("nv_segment_ct", 2, "without", "nemotron", "nemotron_correction"),
    ]


def test_resume_rejects_repeat_from_old_staged_input_protocol(tmp_path, monkeypatch) -> None:
    study_root = tmp_path / "studies"
    monkeypatch.setattr(studies, "STUDY_ROOT", study_root)

    skill = "nv_segment_ct"
    backend = studies.BACKENDS["gpt55"]
    study = study_root / f"{skill}_codex_opus"
    repeat_path = study / "repeats" / "gpt55_with_repeat_1.json"
    old = _fake_result(
        backend,
        "with",
        1,
        studies._repeat_out_dir(skill, "codex_opus", backend, "with", 1),
    )
    old["staged_user_input"] = "runs/with_vs_without_nv/_inputs/nv_segment_ct/spleen_03.nii.gz"
    studies._write_json(repeat_path, old)

    calls: list[tuple[str, str, int]] = []

    def fake_run_repair_loop(*, scenario, backend, arm, out_dir, prompt_style, max_steps):
        repeat = int(out_dir.name.rsplit("_", 1)[-1])
        calls.append((backend.key, arm, repeat))
        return [], _fake_result(backend, arm, repeat, out_dir)

    monkeypatch.setattr(studies, "_run_repair_loop", fake_run_repair_loop)

    studies.run_codex_opus(
        [skill],
        "minimal",
        max_steps=studies.DIRECT_MAX_CORRECTION_STEPS,
        repeats=1,
        resume_missing=True,
    )

    assert ("gpt55", "with", 1) in calls


def test_resume_rejects_repeat_from_wrong_prompt_style(tmp_path, monkeypatch) -> None:
    study_root = tmp_path / "studies"
    monkeypatch.setattr(studies, "STUDY_ROOT", study_root)

    skill = "nv_segment_ct"
    backend = studies.BACKENDS["gpt55"]
    study = study_root / f"{skill}_codex_opus"
    repeat_path = study / "repeats" / "gpt55_with_repeat_1.json"
    old = _fake_result(
        backend,
        "with",
        1,
        studies._repeat_out_dir(skill, "codex_opus", backend, "with", 1),
    )
    old["prompt_style"] = "guarded"
    studies._write_json(repeat_path, old)

    calls: list[tuple[str, str, int]] = []

    def fake_run_repair_loop(*, scenario, backend, arm, out_dir, prompt_style, max_steps):
        repeat = int(out_dir.name.rsplit("_", 1)[-1])
        calls.append((backend.key, arm, repeat))
        return [], _fake_result(backend, arm, repeat, out_dir)

    monkeypatch.setattr(studies, "_run_repair_loop", fake_run_repair_loop)

    studies.run_codex_opus(
        [skill],
        "minimal",
        max_steps=studies.DIRECT_MAX_CORRECTION_STEPS,
        repeats=1,
        resume_missing=True,
    )

    assert ("gpt55", "with", 1) in calls


def test_resume_rejects_repeat_from_wrong_initial_prompt(tmp_path, monkeypatch) -> None:
    study_root = tmp_path / "studies"
    monkeypatch.setattr(studies, "STUDY_ROOT", study_root)

    skill = "nv_segment_ct"
    backend = studies.BACKENDS["gpt55"]
    study = study_root / f"{skill}_codex_opus"
    repeat_path = study / "repeats" / "gpt55_with_repeat_1.json"
    old = _fake_result(
        backend,
        "with",
        1,
        studies._repeat_out_dir(skill, "codex_opus", backend, "with", 1),
    )
    old["attempts"][0]["messages"][1]["content"] += "\nExtra leaked hint."
    studies._write_json(repeat_path, old)

    calls: list[tuple[str, str, int]] = []

    def fake_run_repair_loop(*, scenario, backend, arm, out_dir, prompt_style, max_steps):
        repeat = int(out_dir.name.rsplit("_", 1)[-1])
        calls.append((backend.key, arm, repeat))
        return [], _fake_result(backend, arm, repeat, out_dir)

    monkeypatch.setattr(studies, "_run_repair_loop", fake_run_repair_loop)

    studies.run_codex_opus(
        [skill],
        "minimal",
        max_steps=studies.DIRECT_MAX_CORRECTION_STEPS,
        repeats=1,
        resume_missing=True,
    )

    assert ("gpt55", "with", 1) in calls


def test_resume_rejects_repeat_with_response_command_mismatch(tmp_path, monkeypatch) -> None:
    study_root = tmp_path / "studies"
    monkeypatch.setattr(studies, "STUDY_ROOT", study_root)

    skill = "nv_segment_ct"
    backend = studies.BACKENDS["gpt55"]
    study = study_root / f"{skill}_codex_opus"
    repeat_path = study / "repeats" / "gpt55_with_repeat_1.json"
    old = _fake_result(
        backend,
        "with",
        1,
        studies._repeat_out_dir(skill, "codex_opus", backend, "with", 1),
    )
    old["attempts"][0]["response"] = (
        f"```bash\n{old['command']}\n```\n" "```bash\npython different.py\n```"
    )
    studies._write_json(repeat_path, old)

    calls: list[tuple[str, str, int]] = []

    def fake_run_repair_loop(*, scenario, backend, arm, out_dir, prompt_style, max_steps):
        repeat = int(out_dir.name.rsplit("_", 1)[-1])
        calls.append((backend.key, arm, repeat))
        return [], _fake_result(backend, arm, repeat, out_dir)

    monkeypatch.setattr(studies, "_run_repair_loop", fake_run_repair_loop)

    studies.run_codex_opus(
        [skill],
        "minimal",
        max_steps=studies.DIRECT_MAX_CORRECTION_STEPS,
        repeats=1,
        resume_missing=True,
    )

    assert ("gpt55", "with", 1) in calls


def test_resume_rejects_repeat_with_stale_leaky_repair_prompt(tmp_path, monkeypatch) -> None:
    study_root = tmp_path / "studies"
    monkeypatch.setattr(studies, "STUDY_ROOT", study_root)

    skill = "nv_segment_ct"
    backend = studies.BACKENDS["gpt55"]
    study = study_root / f"{skill}_codex_opus"
    repeat_path = study / "repeats" / "gpt55_without_repeat_1.json"
    old = _fake_result(
        backend,
        "without",
        1,
        studies._repeat_out_dir(skill, "codex_opus", backend, "without", 1),
    )
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
    old["attempts"][0]["score"] = failed_score
    old["attempts"][0]["execution"] = {"exit_code": 1}
    old["attempts"].append(
        {
            "backend": backend.key,
            "arm": "without",
            "step": 1,
            "messages": [
                *old["attempts"][0]["messages"],
                {"role": "assistant", "content": "```bash\npython bad.py\n```"},
                {"role": "user", "content": repair_prompt},
            ],
            "command": "python bad.py",
            "execution": {"exit_code": 1},
            "score": failed_score,
        }
    )
    old["command"] = "python bad.py"
    old["execution"] = {"exit_code": 1}
    old["score"] = failed_score
    old["steps_to_pass"] = "unresolved"
    studies._write_json(repeat_path, old)

    calls: list[tuple[str, str, int]] = []

    def fake_run_repair_loop(*, scenario, backend, arm, out_dir, prompt_style, max_steps):
        repeat = int(out_dir.name.rsplit("_", 1)[-1])
        calls.append((backend.key, arm, repeat))
        return [], _fake_result(backend, arm, repeat, out_dir)

    monkeypatch.setattr(studies, "_run_repair_loop", fake_run_repair_loop)

    studies.run_codex_opus(
        [skill],
        "minimal",
        max_steps=studies.DIRECT_MAX_CORRECTION_STEPS,
        repeats=1,
        resume_missing=True,
    )

    assert ("gpt55", "without", 1) in calls


def test_resume_rejects_repeat_with_wrong_repair_message_roles(tmp_path, monkeypatch) -> None:
    study_root = tmp_path / "studies"
    monkeypatch.setattr(studies, "STUDY_ROOT", study_root)

    skill = "nv_segment_ct"
    backend = studies.BACKENDS["gpt55"]
    study = study_root / f"{skill}_codex_opus"
    repeat_path = study / "repeats" / "gpt55_with_repeat_1.json"
    old = _fake_result(
        backend,
        "with",
        1,
        studies._repeat_out_dir(skill, "codex_opus", backend, "with", 1),
    )
    failed_score = {
        "passed": False,
        "score": 1,
        "tiers": [{"tier": 5, "pass": False, "reason": "exit 1"}],
    }
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
    old["attempts"][0]["score"] = failed_score
    old["attempts"][0]["execution"] = {"exit_code": 1}
    old["attempts"].append(
        {
            "backend": backend.key,
            "arm": "with",
            "step": 1,
            "messages": [
                *old["attempts"][0]["messages"],
                {"role": "user", "content": "```bash\npython bad.py\n```"},
                {"role": "user", "content": repair_prompt},
            ],
            "command": old["command"],
            "execution": {"exit_code": 0},
            "score": old["score"],
        }
    )
    old["steps_to_pass"] = 1
    studies._write_json(repeat_path, old)

    calls: list[tuple[str, str, int]] = []

    def fake_run_repair_loop(*, scenario, backend, arm, out_dir, prompt_style, max_steps):
        repeat = int(out_dir.name.rsplit("_", 1)[-1])
        calls.append((backend.key, arm, repeat))
        return [], _fake_result(backend, arm, repeat, out_dir)

    monkeypatch.setattr(studies, "_run_repair_loop", fake_run_repair_loop)

    studies.run_codex_opus(
        [skill],
        "minimal",
        max_steps=studies.DIRECT_MAX_CORRECTION_STEPS,
        repeats=1,
        resume_missing=True,
    )

    assert ("gpt55", "with", 1) in calls


def test_resume_rejects_repeat_with_response_history_mismatch(tmp_path, monkeypatch) -> None:
    study_root = tmp_path / "studies"
    monkeypatch.setattr(studies, "STUDY_ROOT", study_root)

    skill = "nv_segment_ct"
    backend = studies.BACKENDS["gpt55"]
    study = study_root / f"{skill}_codex_opus"
    repeat_path = study / "repeats" / "gpt55_with_repeat_1.json"
    old = _fake_result(
        backend,
        "with",
        1,
        studies._repeat_out_dir(skill, "codex_opus", backend, "with", 1),
    )
    failed_score = {
        "passed": False,
        "score": 1,
        "tiers": [{"tier": 5, "pass": False, "reason": "exit 1"}],
    }
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
    old["attempts"][0]["score"] = failed_score
    old["attempts"][0]["execution"] = {"exit_code": 1}
    old["attempts"][0]["response"] = "```bash\npython bad.py\n```"
    old["attempts"].append(
        {
            "backend": backend.key,
            "arm": "with",
            "step": 1,
            "messages": [
                *old["attempts"][0]["messages"],
                {"role": "assistant", "content": "```bash\npython edited.py\n```"},
                {"role": "user", "content": repair_prompt},
            ],
            "command": old["command"],
            "execution": {"exit_code": 0},
            "score": old["score"],
        }
    )
    old["steps_to_pass"] = 1
    studies._write_json(repeat_path, old)

    calls: list[tuple[str, str, int]] = []

    def fake_run_repair_loop(*, scenario, backend, arm, out_dir, prompt_style, max_steps):
        repeat = int(out_dir.name.rsplit("_", 1)[-1])
        calls.append((backend.key, arm, repeat))
        return [], _fake_result(backend, arm, repeat, out_dir)

    monkeypatch.setattr(studies, "_run_repair_loop", fake_run_repair_loop)

    studies.run_codex_opus(
        [skill],
        "minimal",
        max_steps=studies.DIRECT_MAX_CORRECTION_STEPS,
        repeats=1,
        resume_missing=True,
    )

    assert ("gpt55", "with", 1) in calls


def test_resume_rejects_repeat_with_repair_prompt_mismatch(tmp_path, monkeypatch) -> None:
    study_root = tmp_path / "studies"
    monkeypatch.setattr(studies, "STUDY_ROOT", study_root)

    skill = "nv_segment_ct"
    backend = studies.BACKENDS["gpt55"]
    study = study_root / f"{skill}_codex_opus"
    repeat_path = study / "repeats" / "gpt55_with_repeat_1.json"
    old = _fake_result(
        backend,
        "with",
        1,
        studies._repeat_out_dir(skill, "codex_opus", backend, "with", 1),
    )
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
    old["attempts"][0]["score"] = failed_score
    old["attempts"][0]["execution"] = failed_execution
    old["attempts"][0]["response"] = first_response
    old["attempts"].append(
        {
            "backend": backend.key,
            "arm": "with",
            "step": 1,
            "messages": [
                *old["attempts"][0]["messages"],
                {"role": "assistant", "content": first_response},
                {"role": "user", "content": repair_prompt},
            ],
            "command": old["command"],
            "execution": {"exit_code": 0},
            "score": old["score"],
        }
    )
    old["steps_to_pass"] = 1
    studies._write_json(repeat_path, old)

    calls: list[tuple[str, str, int]] = []

    def fake_run_repair_loop(*, scenario, backend, arm, out_dir, prompt_style, max_steps):
        repeat = int(out_dir.name.rsplit("_", 1)[-1])
        calls.append((backend.key, arm, repeat))
        return [], _fake_result(backend, arm, repeat, out_dir)

    monkeypatch.setattr(studies, "_run_repair_loop", fake_run_repair_loop)

    studies.run_codex_opus(
        [skill],
        "minimal",
        max_steps=studies.DIRECT_MAX_CORRECTION_STEPS,
        repeats=1,
        resume_missing=True,
    )

    assert ("gpt55", "with", 1) in calls


def test_resume_rejects_repeat_with_stale_top_level_result(tmp_path, monkeypatch) -> None:
    study_root = tmp_path / "studies"
    monkeypatch.setattr(studies, "STUDY_ROOT", study_root)

    skill = "nv_segment_ct"
    backend = studies.BACKENDS["gpt55"]
    study = study_root / f"{skill}_codex_opus"
    repeat_path = study / "repeats" / "gpt55_with_repeat_1.json"
    old = _fake_result(
        backend,
        "with",
        1,
        studies._repeat_out_dir(skill, "codex_opus", backend, "with", 1),
    )
    old["score"] = {"passed": False, "score": 1, "tiers": []}
    studies._write_json(repeat_path, old)

    calls: list[tuple[str, str, int]] = []

    def fake_run_repair_loop(*, scenario, backend, arm, out_dir, prompt_style, max_steps):
        repeat = int(out_dir.name.rsplit("_", 1)[-1])
        calls.append((backend.key, arm, repeat))
        return [], _fake_result(backend, arm, repeat, out_dir)

    monkeypatch.setattr(studies, "_run_repair_loop", fake_run_repair_loop)

    studies.run_codex_opus(
        [skill],
        "minimal",
        max_steps=studies.DIRECT_MAX_CORRECTION_STEPS,
        repeats=1,
        resume_missing=True,
    )

    assert ("gpt55", "with", 1) in calls


def test_resume_rejects_repeat_without_attempt_response_usage_or_model(
    tmp_path, monkeypatch
) -> None:
    study_root = tmp_path / "studies"
    monkeypatch.setattr(studies, "STUDY_ROOT", study_root)

    skill = "nv_segment_ct"
    backend = studies.BACKENDS["gpt55"]
    study = study_root / f"{skill}_codex_opus"
    repeat_path = study / "repeats" / "gpt55_with_repeat_1.json"
    old = _fake_result(
        backend,
        "with",
        1,
        studies._repeat_out_dir(skill, "codex_opus", backend, "with", 1),
    )
    old["attempts"][0].pop("response")
    old["attempts"][0].pop("usage")
    old["attempts"][0]["model"] = "stale-model"
    old["attempts"][0]["backend_protocol"] = {"model": "stale-model"}
    old["backend_label"] = "stale backend"
    old["model"] = "stale-model"
    old["backend_protocol"] = {"model": "stale-model"}
    old["execution"] = {"exit_code": 999}
    studies._write_json(repeat_path, old)

    calls: list[tuple[str, str, int]] = []

    def fake_run_repair_loop(*, scenario, backend, arm, out_dir, prompt_style, max_steps):
        repeat = int(out_dir.name.rsplit("_", 1)[-1])
        calls.append((backend.key, arm, repeat))
        return [], _fake_result(backend, arm, repeat, out_dir)

    monkeypatch.setattr(studies, "_run_repair_loop", fake_run_repair_loop)

    studies.run_codex_opus(
        [skill],
        "minimal",
        max_steps=studies.DIRECT_MAX_CORRECTION_STEPS,
        repeats=1,
        resume_missing=True,
    )

    assert ("gpt55", "with", 1) in calls
