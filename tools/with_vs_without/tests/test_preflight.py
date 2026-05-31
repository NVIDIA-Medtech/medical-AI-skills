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
from pathlib import Path

from tools.with_vs_without import preflight_nv_model_studies as preflight
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


def _checks(report: dict, *, scope: str, name: str) -> list[dict]:
    return [item for item in report["checks"] if item["scope"] == scope and item["check"] == name]


def test_preflight_prompts_mode_accepts_ready_skill_without_credentials(tmp_path: Path) -> None:
    skill = "nv_reason_cxr"
    _write_prompt_artifact(tmp_path, skill)

    report = preflight.preflight(
        skills=[skill],
        mode="prompts",
        repeats=1,
        prompt_root=tmp_path,
        environ={},
        bashrc=tmp_path / "missing_bashrc",
    )

    assert report["status"] == "pass"
    assert report["summary"]["errors"] == 0
    assert not _checks(report, scope="credentials", name="NV_INFER_TOKEN")
    assert _checks(report, scope=skill, name="prompt_artifact")[0]["status"] == "pass"


def test_preflight_direct_mode_requires_backend_credentials(tmp_path: Path) -> None:
    skill = "nv_reason_cxr"
    _write_prompt_artifact(tmp_path, skill)

    missing = preflight.preflight(
        skills=[skill],
        mode="nemotron",
        repeats=1,
        prompt_root=tmp_path,
        environ={},
        bashrc=tmp_path / "missing_bashrc",
    )

    assert missing["status"] == "fail"
    credential_check = _checks(
        missing,
        scope="credentials",
        name="NV_INFER_TOKEN",
    )[0]
    assert credential_check["status"] == "error"
    assert "NV_INFER_TOKEN" in credential_check["detail"]

    present = preflight.preflight(
        skills=[skill],
        mode="nemotron",
        repeats=1,
        prompt_root=tmp_path,
        environ={"NV_INFER_TOKEN": "secret-token"},
        bashrc=tmp_path / "missing_bashrc",
    )

    assert present["status"] == "pass"
    credential_check = _checks(
        present,
        scope="credentials",
        name="NV_INFER_TOKEN",
    )[0]
    assert credential_check["status"] == "pass"
    assert "value not printed" in credential_check["detail"]
    assert "secret-token" not in preflight._format_markdown(present)


def test_preflight_rejects_stale_prompt_artifact(tmp_path: Path) -> None:
    skill = "nv_reason_cxr"
    _write_prompt_artifact(tmp_path, skill)
    path = tmp_path / f"eval_nv_model_studies_{skill}_prompts.json"
    rows = json.loads(path.read_text())
    rows[0]["system"] = "stale prompt"
    path.write_text(json.dumps(rows, indent=2) + "\n")

    report = preflight.preflight(
        skills=[skill],
        mode="prompts",
        repeats=1,
        prompt_root=tmp_path,
        environ={},
        bashrc=tmp_path / "missing_bashrc",
    )

    assert report["status"] == "fail"
    prompt_check = _checks(report, scope=skill, name="prompt_artifact")[0]
    assert prompt_check["status"] == "error"
    assert "wrong_system_prompt" in prompt_check["detail"]


def test_preflight_rejects_invalid_scenario_document_contract(
    monkeypatch,
    tmp_path: Path,
) -> None:
    skill = "bad_doc_contract"
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
    _write_prompt_artifact(tmp_path, skill)

    report = preflight.preflight(
        skills=[skill],
        mode="prompts",
        repeats=1,
        prompt_root=tmp_path,
        environ={},
        bashrc=tmp_path / "missing_bashrc",
    )

    assert report["status"] == "fail"
    with_location = _checks(report, scope=skill, name="with_doc_location")[0]
    without_location = _checks(report, scope=skill, name="without_doc_location")[0]
    assert with_location["status"] == "error"
    assert "skills/bad-doc-contract/SKILL.md" in with_location["detail"]
    assert without_location["status"] == "error"
    assert "tools/with_vs_without/upstream_docs/" in without_location["detail"]


def test_preflight_rejects_user_goal_without_required_placeholders(
    monkeypatch,
    tmp_path: Path,
) -> None:
    skill = "bad_goal_placeholders"
    scenario = studies.Scenario(
        skill=skill,
        title="Bad Goal Placeholders",
        fixture="skills/nv-segment-ct/fixtures/spleen_03.nii.gz",
        kind="segmentation",
        task="Run a segmentation command.",
        user_goal="Write outputs under {out_dir}.",
        with_doc=("skills/bad-goal-placeholders/SKILL.md",),
        without_doc=("tools/with_vs_without/upstream_docs/bad_goal_README.md",),
        tier1=(),
        tier2=(),
        tier3=(),
    )
    monkeypatch.setitem(studies.SCENARIOS, skill, scenario)
    _write_prompt_artifact(tmp_path, skill)

    report = preflight.preflight(
        skills=[skill],
        mode="prompts",
        repeats=1,
        prompt_root=tmp_path,
        environ={},
        bashrc=tmp_path / "missing_bashrc",
    )

    assert report["status"] == "fail"
    placeholder_check = _checks(report, scope=skill, name="user_goal_placeholders")[0]
    assert placeholder_check["status"] == "error"
    assert "{input_path}" in placeholder_check["detail"]
