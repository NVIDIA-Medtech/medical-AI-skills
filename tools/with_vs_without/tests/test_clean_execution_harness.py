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


def test_study_artifact_sanitizer_removes_local_absolute_paths() -> None:
    repo_path = studies.REPO_ROOT / "runs/with_vs_without_nv/example/out.json"
    home_path = Path.home() / ".cache/example/model.bin"
    artifact = {
        "exec_python": repo_path,
        "stderr_tail": f"Traceback from {repo_path}\ncache at {home_path}",
        "nested": [{"path": str(repo_path)}],
    }

    sanitized = studies._sanitize_artifact(artifact)

    assert sanitized["exec_python"] == "runs/with_vs_without_nv/example/out.json"
    assert "runs/with_vs_without_nv/example/out.json" in sanitized["stderr_tail"]
    assert "<HOME>/.cache/example/model.bin" in sanitized["stderr_tail"]
    assert "/home/" not in str(sanitized)
    assert "/Users/" not in str(sanitized)


def test_extract_command_requires_exactly_one_shell_block() -> None:
    assert studies._extract_command("```bash\npython ok.py\n```") == "python ok.py"
    assert studies._extract_command("```sh\npython ok.py\n```") == "python ok.py"
    assert studies._extract_command("bash\npython ok.py\n```") == "python ok.py"
    assert studies._extract_command("python ok.py") is None
    assert studies._extract_command("```bash\npython a.py\n```\n```bash\npython b.py\n```") is None


def test_repair_feedback_redacts_local_paths_and_readme_arm_skill_markers() -> None:
    scenario = studies.SCENARIOS["nv_segment_ct"]
    repo_path = studies.REPO_ROOT / "runs/with_vs_without_nv/example/out.json"
    home_path = Path.home() / ".cache/example/model.bin"
    score = {
        "tiers": [{"tier": 5, "pass": False, "reason": "exit 1"}],
    }
    exec_result = {
        "exit_code": 1,
        "reason": None,
        "generated_files": [str(repo_path)],
        "stderr_tail": (
            f"Traceback from {repo_path}\n"
            f"cache at {home_path}\n"
            "hidden wrapper skills/nv-segment-ct/scripts/run_vista3d.py"
        ),
        "stdout_tail": "",
    }

    prompt = studies._feedback(score, exec_result, scenario=scenario, arm="without")

    assert "runs/with_vs_without_nv/example/out.json" in prompt
    assert "<HOME>/.cache/example/model.bin" in prompt
    assert "<REDACTED_WORKBENCH_SKILL_MARKER>" in prompt
    assert str(studies.REPO_ROOT) not in prompt
    assert str(Path.home()) not in prompt
    assert "skills/nv-segment-ct" not in prompt
    assert "run_vista3d.py" not in prompt


def test_execution_guard_requires_neutral_staged_input_path() -> None:
    scenario = studies.SCENARIOS["nv_segment_ct"]
    backend = studies.BACKENDS["gpt55"]
    out_dir = studies._repeat_out_dir("nv_segment_ct", "codex_opus", backend, "with", 1)
    rel_out = out_dir.relative_to(studies.REPO_ROOT)
    rel_input = studies._staged_input_path(scenario).relative_to(studies.REPO_ROOT)
    missing_input = f"python run_vista3d.py --output-dir {rel_out} --labels 1,3,5,14"

    ok, reason = studies._safe_to_execute(scenario, "with", missing_input, out_dir)

    assert ok is False
    assert reason == "command does not reference the neutral staged input path"

    with_input = f"python run_vista3d.py {rel_input} --output-dir {rel_out} --labels 1,3,5,14"
    ok, reason = studies._safe_to_execute(scenario, "with", with_input, out_dir)

    assert ok is True
    assert reason == "ok"


def test_execution_guard_blocks_protected_upstream_config_writes() -> None:
    scenario = studies.SCENARIOS["nv_generate_ct_rflow"]
    backend = studies.BACKENDS["gpt55"]
    out_dir = studies._repeat_out_dir("nv_generate_ct_rflow", "codex_opus", backend, "with", 1)
    rel_out = out_dir.relative_to(studies.REPO_ROOT)
    rel_input = studies._staged_input_path(scenario).relative_to(studies.REPO_ROOT)
    mutating_cmd = (
        f"mkdir -p {rel_out}/_staged_configs && "
        f"cp {rel_input} {rel_out}/request.json && "
        f"cp {rel_out}/_staged_configs/config_infer.json "
        '"$NV_GENERATE_ROOT/configs/config_infer.json" && '
        'cd "$NV_GENERATE_ROOT" && python -m scripts.inference '
        "-i configs/config_infer.json -e configs/environment_rflow-ct.json "
        "--version rflow-ct --random-seed 1"
    )

    ok, reason = studies._safe_to_execute(scenario, "with", mutating_cmd, out_dir)

    assert ok is False
    assert reason == "command attempts to write to protected upstream checkout via cp"


def test_execution_guard_allows_reading_upstream_configs_without_mutating_them() -> None:
    scenario = studies.SCENARIOS["nv_generate_ct_rflow"]
    backend = studies.BACKENDS["gpt55"]
    out_dir = studies._repeat_out_dir("nv_generate_ct_rflow", "codex_opus", backend, "with", 1)
    rel_out = out_dir.relative_to(studies.REPO_ROOT)
    rel_input = studies._staged_input_path(scenario).relative_to(studies.REPO_ROOT)
    read_only_cmd = (
        f"mkdir -p {rel_out} && "
        f"cp {rel_input} {rel_out}/request.json && "
        'cd "$NV_GENERATE_ROOT" && python -m scripts.inference '
        "-i configs/config_infer.json -e configs/environment_rflow-ct.json "
        f"--version rflow-ct --random-seed 1 --output-dir {rel_out}"
    )

    ok, reason = studies._safe_to_execute(scenario, "with", read_only_cmd, out_dir)

    assert ok is True
    assert reason == "ok"


def test_protected_upstream_config_snapshot_restores_generated_mutations(tmp_path: Path) -> None:
    root = tmp_path / "upstream"
    configs = root / "configs"
    configs.mkdir(parents=True)
    config = configs / "config_infer.json"
    config.write_text('{"output_dir": "original"}\n')
    scenario = studies.Scenario(
        skill="example",
        title="Example",
        fixture="fixture.json",
        kind="json",
        task="task",
        user_goal="Use {input_path} and write {out_dir}.",
        with_doc=(),
        without_doc=(),
        tier1=("python",),
        tier2=(),
        tier3=(),
        env={"NV_GENERATE_ROOT": str(root)},
    )
    snapshot = studies._snapshot_protected_upstream_configs(scenario)
    config.write_text('{"output_dir": "mutated"}\n')
    added = configs / "generated.json"
    added.write_text("{}\n")

    changed = studies._restore_protected_upstream_configs(scenario, snapshot)

    assert config.read_text() == '{"output_dir": "original"}\n'
    assert not added.exists()
    assert str(config) in changed
    assert str(added) in changed


def test_ct_pair_candidates_accept_suffix_and_prefix_naming(tmp_path: Path) -> None:
    suffix_image = tmp_path / "sample_0_image.nii.gz"
    suffix_label = tmp_path / "sample_0_label.nii.gz"
    prefix_image = tmp_path / "nested" / "image_0000.nii.gz"
    prefix_label = tmp_path / "nested" / "label_0000.nii.gz"
    unpaired = tmp_path / "image_0001.nii.gz"
    for path in (suffix_image, suffix_label, prefix_image, prefix_label, unpaired):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("nifti-placeholder")

    pairs = studies._ct_pair_candidates(tmp_path)

    assert (suffix_image, suffix_label) in pairs
    assert (prefix_image, prefix_label) in pairs
    assert all(unpaired not in pair for pair in pairs)


def test_ct_rflow_tier3_accepts_wrapper_json_evidence_without_command_marker() -> None:
    scenario = studies.SCENARIOS["nv_generate_ct_rflow"]
    exec_result = {
        "json": {
            "input": {
                "version": "rflow-ct",
                "body_region_requested": ["chest"],
                "anatomy_list_requested": ["lung tumor"],
            }
        }
    }

    assert studies._tier3_pass(scenario, "python run_rflow_ct.py request.json", exec_result)


def test_ct_rflow_tier3_rejects_wrong_wrapper_json_evidence_without_command_marker() -> None:
    scenario = studies.SCENARIOS["nv_generate_ct_rflow"]
    exec_result = {
        "json": {
            "input": {
                "version": "rflow-ct",
                "body_region_requested": ["abdomen"],
                "anatomy_list_requested": ["liver"],
            }
        }
    }

    assert not studies._tier3_pass(scenario, "python run_rflow_ct.py request.json", exec_result)


def test_readme_arm_execution_guard_blocks_hidden_wrapper_basename() -> None:
    scenario = studies.SCENARIOS["nv_segment_ct"]
    backend = studies.BACKENDS["gpt55"]
    out_dir = studies._repeat_out_dir("nv_segment_ct", "codex_opus", backend, "without", 1)
    rel_out = out_dir.relative_to(studies.REPO_ROOT)
    rel_input = studies._staged_input_path(scenario).relative_to(studies.REPO_ROOT)
    cmd = f"python run_vista3d.py {rel_input} --output-dir {rel_out} --labels 1,3,5,14"

    ok, reason = studies._safe_to_execute(scenario, "without", cmd, out_dir)

    assert ok is False
    assert reason == "without-skill command references forbidden Medical AI Skills skill marker"

    upstream_style = f"python -m monai.bundle {rel_input} --output-dir {rel_out} --labels 1,3,5,14"
    ok, reason = studies._safe_to_execute(scenario, "without", upstream_style, out_dir)

    assert ok is True
    assert reason == "ok"
