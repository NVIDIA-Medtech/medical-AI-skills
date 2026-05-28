from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


GRADE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "grade.py"
SPEC = importlib.util.spec_from_file_location("skill_completeness_grade", GRADE_PATH)
assert SPEC is not None and SPEC.loader is not None
grade = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(grade)


def _write_target_skill(
    base: Path,
    *,
    skill_md_body: str,
    entrypoint: str = "scripts/run_demo.py",
    env_required: tuple[str, ...] = (),
    env_optional: tuple[str, ...] = (),
    env_conditional: dict[str, object] | None = None,
    local_writes: tuple[str, ...] = (),
    home_writes: tuple[str, ...] = (),
    network_endpoints: tuple[str, ...] = (),
    requires_docker: bool = False,
    requires_gpu: str = "none",
    pip_packages: tuple[str, ...] = (),
    validation_env_pin: dict[str, str] | None = None,
    include_upstream_ref: bool = True,
    include_reproducibility: bool = True,
) -> Path:
    skill_dir = base / "target-skill"
    (skill_dir / "scripts").mkdir(parents=True)
    (skill_dir / "validators").mkdir()
    (skill_dir / "fixtures").mkdir()
    (skill_dir / entrypoint).write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        "print(json.dumps({'status': 'ok'}))\n"
    )
    (skill_dir / "validators" / "output_schema.json").write_text(
        '{"type": "object", "required": ["status"], "properties": {"status": {"type": "string"}}}\n'
    )
    (skill_dir / "fixtures" / "input.txt").write_text("fixture\n")
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: target-skill\n"
        "description: Runs a target fixture for verifier tests. Engineering verification only.\n"
        "---\n"
        "# Target Skill\n\n"
        + skill_md_body
    )
    env_required_yaml = "\n".join(f"    - {item}" for item in env_required)
    env_required_block = (
        "  env_required:\n" + env_required_yaml + "\n"
        if env_required
        else "  env_required: []\n"
    )
    env_optional_yaml = "\n".join(f"    - {item}" for item in env_optional)
    env_optional_block = (
        "  env_optional:\n" + env_optional_yaml + "\n"
        if env_optional
        else "  env_optional: []\n"
    )
    env_conditional = env_conditional or {}
    if env_conditional:
        conditional_lines = ["  env_conditional:"]
        for key, value in env_conditional.items():
            if isinstance(value, (list, tuple)):
                conditional_lines.append(f"    {key}:")
                conditional_lines.extend(f"      - {item}" for item in value)
            else:
                conditional_lines.append(f"    {key}: {value}")
        env_conditional_block = "\n".join(conditional_lines) + "\n"
    else:
        env_conditional_block = "  env_conditional: {}\n"
    local_writes_yaml = "\n".join(f"      - path: {item}" for item in local_writes)
    local_writes_block = (
        "    local_writes:\n" + local_writes_yaml + "\n"
        if local_writes
        else "    local_writes: []\n"
    )
    home_writes_yaml = "\n".join(f"      - path: {item}" for item in home_writes)
    home_writes_block = (
        "    home_writes:\n" + home_writes_yaml + "\n"
        if home_writes
        else "    home_writes: []\n"
    )
    network_yaml = "\n".join(f"      - {item}" for item in network_endpoints)
    network_block = (
        "    network_endpoints:\n" + network_yaml + "\n"
        if network_endpoints
        else "    network_endpoints: []\n"
    )
    pip_packages_yaml = "\n".join(f"      - {item}" for item in pip_packages)
    pip_packages_block = (
        "    pip_packages:\n" + pip_packages_yaml + "\n"
        if pip_packages
        else "    pip_packages: []\n"
    )
    upstream_ref_block = (
        "upstream_refs:\n"
        "  - kind: pypi_package\n"
        "    name: demo-runtime\n"
        "    version_constraint: '>=1.0'\n"
        if include_upstream_ref
        else ""
    )
    validation_env_pin = validation_env_pin or {}
    env_pin_block = ""
    if validation_env_pin:
        env_pin_block = "  env_pin:\n" + "".join(
            f"    {name}: {constraint!r}\n"
            for name, constraint in validation_env_pin.items()
        )
    reproducibility_block = (
        "  reproducibility:\n"
        "    mode: repeat\n"
        "    fixture: fixtures/input.txt\n"
        "    runs: 2\n"
        if include_reproducibility
        else ""
    )
    (skill_dir / "skill_manifest.yaml").write_text(
        "id: fixtures.target_skill\n"
        "version: 0.1.0\n"
        + upstream_ref_block +
        "license: Apache-2.0\n"
        "intended_use:\n"
        "  summary: Test fixture.\n"
        "inputs:\n"
        "  - name: input\n"
        "    type: file_path\n"
        "outputs:\n"
        "  - name: output\n"
        "    type: json\n"
        "    schema: validators/output_schema.json\n"
        "runtime:\n"
        "  language: python\n"
        f"  entrypoint: {entrypoint}\n"
        "  args:\n"
        "    - ${python}\n"
        "    - ${script}\n"
        "    - ${fixture}\n"
        "    - --output-dir\n"
        "    - ${out}\n"
        + env_required_block +
        env_optional_block +
        env_conditional_block +
        "  side_effects:\n"
        + pip_packages_block +
        local_writes_block +
        home_writes_block +
        network_block +
        f"    requires_docker: {str(requires_docker).lower()}\n"
        f"    requires_gpu: {requires_gpu}\n"
        "validation:\n"
        "  sanity_checks:\n"
        "    - path: status\n"
        "      eq: ok\n"
        + reproducibility_block
        + env_pin_block
    )
    return skill_dir


def _checks_by_name(checks: list[dict]) -> dict[str, dict]:
    return {item["check"]: item for item in checks}


def test_agent_usability_shape_passes_for_clear_skill_md(tmp_path: Path) -> None:
    skill_dir = _write_target_skill(
        tmp_path,
        skill_md_body=(
            "## Purpose\n\nRun the demo wrapper.\n\n"
            "## Instructions\n\n"
            'Use `run_script("scripts/run_demo.py", args=[...])` or run the Python command below.\n\n'
            "## Available Scripts\n\n"
            "| Script | Purpose | Arguments |\n"
            "|---|---|---|\n"
            "| `scripts/run_demo.py` | Runs the demo. | `INPUT --output-dir OUT` |\n\n"
            "## Prerequisites\n\nPython only.\n\n"
            "## Limitations\n\nEngineering fixture only.\n\n"
            "## Troubleshooting\n\nCheck stderr.\n"
        ),
    )

    checks = _checks_by_name(grade.grade_tier2(skill_dir))

    assert checks["skill_md_agent_usability_sections"]["pass"] is True
    assert checks["skill_md_available_scripts_table"]["pass"] is True
    assert checks["skill_md_available_scripts_resolve"]["pass"] is True
    assert checks["skill_md_available_scripts_arguments_specific"]["pass"] is True
    assert checks["skill_md_available_entrypoint_arguments_match_runtime"]["pass"] is True
    assert checks["skill_md_available_scripts_include_entrypoint"]["pass"] is True
    assert checks["skill_md_mentions_runtime_entrypoint"]["pass"] is True
    assert checks["skill_md_has_concrete_invocation"]["pass"] is True
    assert checks["skill_md_invocation_uses_entrypoint"]["pass"] is True
    assert checks["skill_md_mentions_runtime_literal_args"]["pass"] is True
    assert checks["skill_md_mentions_runtime_env_required"]["pass"] is True
    assert checks["skill_md_mentions_runtime_env_optional"]["pass"] is True
    assert checks["skill_md_mentions_runtime_env_conditional"]["pass"] is True
    assert checks["skill_md_mentions_runtime_side_effects"]["pass"] is True
    assert checks["skill_md_mentions_manifest_io"]["pass"] is True
    assert checks["reproducibility_anchor_declared"]["pass"] is True
    assert checks["reproducibility_check_declared"]["pass"] is True
    assert checks["env_pin_matches_exact_runtime_pins"]["pass"] is True


def test_reproducibility_anchor_is_blocking(tmp_path: Path) -> None:
    skill_dir = _write_target_skill(
        tmp_path,
        include_upstream_ref=False,
        skill_md_body=(
            "## Purpose\n\nRun the demo wrapper.\n\n"
            "## Instructions\n\n"
            'Use `run_script("scripts/run_demo.py", args=[...])`.\n\n'
            "## Available Scripts\n\n"
            "| Script | Purpose | Arguments |\n"
            "|---|---|---|\n"
            "| `scripts/run_demo.py` | Runs the demo. | `INPUT --output-dir OUT` |\n\n"
            "## Prerequisites\n\nPython only.\n\n"
            "## Limitations\n\nEngineering fixture only.\n\n"
            "## Troubleshooting\n\nCheck stderr.\n"
        ),
    )

    checks = _checks_by_name(grade.grade_tier2(skill_dir))
    summary = grade._summarise("tier2_spec_honesty", list(checks.values()))

    assert checks["reproducibility_anchor_declared"]["pass"] is False
    assert checks["reproducibility_anchor_declared"]["severity"] == "block"
    assert summary["verdict"] == "fail"


def test_reproducibility_check_is_blocking(tmp_path: Path) -> None:
    skill_dir = _write_target_skill(
        tmp_path,
        include_reproducibility=False,
        skill_md_body=(
            "## Purpose\n\nRun the demo wrapper.\n\n"
            "## Instructions\n\n"
            'Use `run_script("scripts/run_demo.py", args=[...])`.\n\n'
            "## Available Scripts\n\n"
            "| Script | Purpose | Arguments |\n"
            "|---|---|---|\n"
            "| `scripts/run_demo.py` | Runs the demo. | `INPUT --output-dir OUT` |\n\n"
            "## Prerequisites\n\nPython only.\n\n"
            "## Limitations\n\nEngineering fixture only.\n\n"
            "## Troubleshooting\n\nCheck stderr.\n"
        ),
    )

    checks = _checks_by_name(grade.grade_tier2(skill_dir))
    summary = grade._summarise("tier2_spec_honesty", list(checks.values()))

    assert checks["reproducibility_check_declared"]["pass"] is False
    assert checks["reproducibility_check_declared"]["severity"] == "block"
    assert summary["verdict"] == "fail"


def test_lifecycle_derives_gated_status_without_pairing(tmp_path: Path) -> None:
    skill_dir = _write_target_skill(
        tmp_path,
        skill_md_body=(
            "## Purpose\n\nRun the demo wrapper.\n\n"
            "## Instructions\n\n"
            'Use `run_script("scripts/run_demo.py", args=[...])`.\n\n'
            "## Available Scripts\n\n"
            "| Script | Purpose | Arguments |\n"
            "|---|---|---|\n"
            "| `scripts/run_demo.py` | Runs the demo. | `INPUT --output-dir OUT` |\n\n"
            "## Prerequisites\n\nPython only.\n\n"
            "## Limitations\n\nEngineering fixture only.\n\n"
            "## Troubleshooting\n\nCheck stderr.\n"
        ),
    )
    tier1_summary = grade._summarise("tier1_structural", grade.grade_tier1(skill_dir))
    tier2_summary = grade._summarise("tier2_spec_honesty", grade.grade_tier2(skill_dir))

    lifecycle = grade.derive_capability_lifecycle(skill_dir, tier1_summary, tier2_summary)

    assert lifecycle["status"] == "gated"
    requirements = {item["status"]: item for item in lifecycle["requirements"]}
    assert requirements["gated"]["met"] is True
    assert requirements["verified"]["met"] is False
    assert "no implemented paired_verifiers[]" in requirements["verified"]["gaps"][0]


def test_lifecycle_requires_trusted_evidence_for_verified_status(tmp_path: Path) -> None:
    skill_dir = _write_target_skill(
        tmp_path,
        skill_md_body=(
            "## Purpose\n\nRun the demo wrapper.\n\n"
            "## Instructions\n\n"
            'Use `run_script("scripts/run_demo.py", args=[...])`.\n\n'
            "## Available Scripts\n\n"
            "| Script | Purpose | Arguments |\n"
            "|---|---|---|\n"
            "| `scripts/run_demo.py` | Runs the demo. | `INPUT --output-dir OUT` |\n\n"
            "## Prerequisites\n\nPython only.\n\n"
            "## Limitations\n\nEngineering fixture only.\n\n"
            "## Troubleshooting\n\nCheck stderr.\n"
        ),
    )
    manifest_path = skill_dir / "skill_manifest.yaml"
    manifest_path.write_text(
        manifest_path.read_text()
        + "paired_verifiers:\n"
        + "  - id: medagent.verifiers.skill_completeness_v1\n"
        + "    status: implemented\n"
    )
    tier1_summary = grade._summarise("tier1_structural", grade.grade_tier1(skill_dir))
    tier2_summary = grade._summarise("tier2_spec_honesty", grade.grade_tier2(skill_dir))

    lifecycle = grade.derive_capability_lifecycle(skill_dir, tier1_summary, tier2_summary)

    assert lifecycle["status"] == "gated"
    requirements = {item["status"]: item for item in lifecycle["requirements"]}
    assert requirements["verified"]["met"] is False
    assert "verifiers/skill_completeness_v1" in requirements["verified"]["evidence"]
    assert "no curated trusted-run summary" in requirements["verified"]["gaps"][0]
    assert requirements["published"]["met"] is False
    assert "verified lifecycle step is not met" in requirements["published"]["gaps"]


def test_lifecycle_derives_verified_status_from_curated_trusted_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    skill_dir = _write_target_skill(
        tmp_path,
        skill_md_body=(
            "## Purpose\n\nRun the demo wrapper.\n\n"
            "## Instructions\n\n"
            'Use `run_script("scripts/run_demo.py", args=[...])`.\n\n'
            "## Available Scripts\n\n"
            "| Script | Purpose | Arguments |\n"
            "|---|---|---|\n"
            "| `scripts/run_demo.py` | Runs the demo. | `INPUT --output-dir OUT` |\n\n"
            "## Prerequisites\n\nPython only.\n\n"
            "## Limitations\n\nEngineering fixture only.\n\n"
            "## Troubleshooting\n\nCheck stderr.\n"
        ),
    )
    manifest_path = skill_dir / "skill_manifest.yaml"
    manifest_path.write_text(
        manifest_path.read_text()
        + "paired_verifiers:\n"
        + "  - id: medagent.verifiers.skill_completeness_v1\n"
        + "    status: implemented\n"
    )
    trusted_dir = tmp_path / "examples" / "studies" / "trusted_target"
    trusted_dir.mkdir(parents=True)
    (trusted_dir / "trust_summary.json").write_text(
        "{"
        '"skill_id": "fixtures.target_skill",'
        '"overall": "passed",'
        '"planned_verifier_gaps": [],'
        '"env_skipped_verifier_gaps": []'
        "}\n"
    )
    monkeypatch.setattr(grade, "REPO_ROOT", tmp_path)
    tier1_summary = grade._summarise("tier1_structural", grade.grade_tier1(skill_dir))
    tier2_summary = grade._summarise("tier2_spec_honesty", grade.grade_tier2(skill_dir))

    lifecycle = grade.derive_capability_lifecycle(skill_dir, tier1_summary, tier2_summary)

    assert lifecycle["status"] == "verified"
    requirements = {item["status"]: item for item in lifecycle["requirements"]}
    assert requirements["verified"]["met"] is True
    assert "examples/studies/trusted_target" in requirements["verified"]["evidence"]
    assert requirements["published"]["met"] is False
    assert "missing BENCHMARK.md" in requirements["published"]["gaps"]


def test_verifier_lifecycle_uses_curated_passing_evidence_not_paired_verifiers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifiers_root = tmp_path / "verifiers"
    verifier_dir = _write_target_skill(
        verifiers_root,
        skill_md_body=(
            "## Purpose\n\nAudit a target evidence pack.\n\n"
            "## Instructions\n\n"
            'Use `run_script("scripts/run_demo.py", args=[...])`.\n\n'
            "## Available Scripts\n\n"
            "| Script | Purpose | Arguments |\n"
            "|---|---|---|\n"
            "| `scripts/run_demo.py` | Runs the verifier. | `INPUT --output-dir OUT` |\n\n"
            "## Prerequisites\n\nPython only.\n\n"
            "## Limitations\n\nEngineering fixture only.\n\n"
            "## Troubleshooting\n\nCheck stderr.\n"
        ),
    )
    manifest_path = verifier_dir / "skill_manifest.yaml"
    manifest_path.write_text(
        manifest_path.read_text().replace(
            "id: fixtures.target_skill",
            "id: medagent.verifiers.target_skill",
        )
    )
    evidence_dir = tmp_path / "examples" / "evidence_packs" / "target_skill_verifier_pass"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "manifest.json").write_text(
        '{"skill_id": "medagent.verifiers.target_skill"}\n'
    )
    (evidence_dir / "validation_summary.json").write_text(
        '{"overall_status": "passed"}\n'
    )
    monkeypatch.setattr(grade, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(grade, "VERIFIERS_ROOT", verifiers_root)

    tier1_summary = grade._summarise("tier1_structural", grade.grade_tier1(verifier_dir))
    tier2_summary = grade._summarise("tier2_spec_honesty", grade.grade_tier2(verifier_dir))

    lifecycle = grade.derive_capability_lifecycle(verifier_dir, tier1_summary, tier2_summary)

    assert lifecycle["target_type"] == "verifier"
    assert lifecycle["status"] == "published"
    requirements = {item["status"]: item for item in lifecycle["requirements"]}
    assert requirements["verified"]["met"] is True
    assert "examples/evidence_packs/target_skill_verifier_pass" in requirements["verified"]["evidence"]
    assert not any(
        "paired_verifiers" in gap
        for requirement in lifecycle["requirements"]
        for gap in requirement["gaps"]
    )


def test_verifier_lifecycle_stays_gated_without_curated_passing_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifiers_root = tmp_path / "verifiers"
    verifier_dir = _write_target_skill(
        verifiers_root,
        skill_md_body=(
            "## Purpose\n\nAudit a target evidence pack.\n\n"
            "## Instructions\n\n"
            'Use `run_script("scripts/run_demo.py", args=[...])`.\n\n'
            "## Available Scripts\n\n"
            "| Script | Purpose | Arguments |\n"
            "|---|---|---|\n"
            "| `scripts/run_demo.py` | Runs the verifier. | `INPUT --output-dir OUT` |\n\n"
            "## Prerequisites\n\nPython only.\n\n"
            "## Limitations\n\nEngineering fixture only.\n\n"
            "## Troubleshooting\n\nCheck stderr.\n"
        ),
    )
    manifest_path = verifier_dir / "skill_manifest.yaml"
    manifest_path.write_text(
        manifest_path.read_text().replace(
            "id: fixtures.target_skill",
            "id: medagent.verifiers.target_skill",
        )
    )
    monkeypatch.setattr(grade, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(grade, "VERIFIERS_ROOT", verifiers_root)

    tier1_summary = grade._summarise("tier1_structural", grade.grade_tier1(verifier_dir))
    tier2_summary = grade._summarise("tier2_spec_honesty", grade.grade_tier2(verifier_dir))

    lifecycle = grade.derive_capability_lifecycle(verifier_dir, tier1_summary, tier2_summary)

    assert lifecycle["target_type"] == "verifier"
    assert lifecycle["status"] == "gated"
    requirements = {item["status"]: item for item in lifecycle["requirements"]}
    assert requirements["verified"]["met"] is False
    assert "no curated verifier evidence pack" in requirements["verified"]["gaps"][0]
    assert not any(
        "paired_verifiers" in gap
        for requirement in lifecycle["requirements"]
        for gap in requirement["gaps"]
    )


def test_env_pin_must_match_exact_runtime_pins(tmp_path: Path) -> None:
    skill_dir = _write_target_skill(
        tmp_path,
        pip_packages=("monai==1.4.0",),
        validation_env_pin={"monai": ">=1.5,<1.6"},
        skill_md_body=(
            "## Purpose\n\nRun the demo wrapper.\n\n"
            "## Instructions\n\n"
            'Use `run_script("scripts/run_demo.py", args=[...])`.\n\n'
            "## Available Scripts\n\n"
            "| Script | Purpose | Arguments |\n"
            "|---|---|---|\n"
            "| `scripts/run_demo.py` | Runs the demo. | `INPUT --output-dir OUT` |\n\n"
            "## Prerequisites\n\nPython only.\n\n"
            "## Limitations\n\nEngineering fixture only.\n\n"
            "## Troubleshooting\n\nCheck stderr.\n"
        ),
    )

    checks = _checks_by_name(grade.grade_tier2(skill_dir))

    assert checks["env_pin_matches_exact_runtime_pins"]["pass"] is False
    assert "monai" in checks["env_pin_matches_exact_runtime_pins"]["msg"]


def test_agent_usability_shape_reports_advisory_gaps(tmp_path: Path) -> None:
    skill_dir = _write_target_skill(
        tmp_path,
        skill_md_body=(
            "A vague guide that does not tell an agent which wrapper to run.\n"
        ),
    )

    checks = _checks_by_name(grade.grade_tier2(skill_dir))
    summary = grade._summarise("tier2_spec_honesty", list(checks.values()))

    for name in (
        "skill_md_agent_usability_sections",
        "skill_md_available_scripts_table",
        "skill_md_available_scripts_resolve",
        "skill_md_available_scripts_arguments_specific",
        "skill_md_available_entrypoint_arguments_match_runtime",
        "skill_md_available_scripts_include_entrypoint",
        "skill_md_mentions_runtime_entrypoint",
        "skill_md_has_concrete_invocation",
        "skill_md_invocation_uses_entrypoint",
        "skill_md_mentions_runtime_literal_args",
        "skill_md_mentions_manifest_io",
    ):
        assert checks[name]["pass"] is False
        assert checks[name]["severity"] == "advisory"
    assert summary["verdict"] == "pass"


def test_available_scripts_table_rejects_missing_paths(tmp_path: Path) -> None:
    skill_dir = _write_target_skill(
        tmp_path,
        skill_md_body=(
            "## Purpose\n\nRun the demo wrapper.\n\n"
            "## Instructions\n\n"
            'Use `run_script("scripts/run_demo.py", args=[...])`.\n\n'
            "## Available Scripts\n\n"
            "| Script | Purpose | Arguments |\n"
            "|---|---|---|\n"
            "| `scripts/missing.py` | Missing wrapper. | `INPUT --output-dir OUT` |\n\n"
            "## Prerequisites\n\nPython only.\n\n"
            "## Limitations\n\nEngineering fixture only.\n\n"
            "## Troubleshooting\n\nCheck stderr.\n"
        ),
    )

    checks = _checks_by_name(grade.grade_tier2(skill_dir))

    assert checks["skill_md_available_scripts_resolve"]["pass"] is False
    assert checks["skill_md_available_scripts_include_entrypoint"]["pass"] is False


def test_available_scripts_table_rejects_vague_argument_references(tmp_path: Path) -> None:
    skill_dir = _write_target_skill(
        tmp_path,
        skill_md_body=(
            "## Purpose\n\nRun the demo wrapper.\n\n"
            "## Instructions\n\n"
            'Use `run_script("scripts/run_demo.py", args=[...])`.\n\n'
            "## Available Scripts\n\n"
            "| Script | Purpose | Arguments |\n"
            "|---|---|---|\n"
            "| `scripts/run_demo.py` | Runs the demo. | See Usage below or runtime.args in skill_manifest.yaml. |\n\n"
            "## Prerequisites\n\nPython only.\n\n"
            "## Limitations\n\nEngineering fixture only.\n\n"
            "## Troubleshooting\n\nCheck stderr.\n"
        ),
    )

    checks = _checks_by_name(grade.grade_tier2(skill_dir))

    assert checks["skill_md_available_scripts_arguments_specific"]["pass"] is False
    assert checks["skill_md_available_scripts_arguments_specific"]["severity"] == "advisory"
    assert "scripts/run_demo.py" in checks["skill_md_available_scripts_arguments_specific"]["msg"]


def test_available_scripts_entrypoint_row_must_include_runtime_literal_args(tmp_path: Path) -> None:
    skill_dir = _write_target_skill(
        tmp_path,
        skill_md_body=(
            "## Purpose\n\nRun the demo wrapper.\n\n"
            "## Instructions\n\n"
            'Use `run_script("scripts/run_demo.py", args=[...])`.\n\n'
            "## Available Scripts\n\n"
            "| Script | Purpose | Arguments |\n"
            "|---|---|---|\n"
            "| `scripts/run_demo.py` | Runs the demo. | `INPUT OUT` |\n\n"
            "## Prerequisites\n\nPython only.\n\n"
            "## Limitations\n\nEngineering fixture only.\n\n"
            "## Troubleshooting\n\nCheck stderr.\n"
            "\nUsage: `python scripts/run_demo.py input.txt --output-dir runs/demo`.\n"
        ),
    )

    checks = _checks_by_name(grade.grade_tier2(skill_dir))

    assert checks["skill_md_available_entrypoint_arguments_match_runtime"]["pass"] is False
    assert checks["skill_md_available_entrypoint_arguments_match_runtime"]["severity"] == "advisory"
    assert "--output-dir" in checks["skill_md_available_entrypoint_arguments_match_runtime"]["msg"]


def test_skill_md_must_name_manifest_input_output_hints(tmp_path: Path) -> None:
    skill_dir = _write_target_skill(
        tmp_path,
        skill_md_body=(
            "## Purpose\n\nRun the demo wrapper.\n\n"
            "## Instructions\n\n"
            'Use `run_script("scripts/run_demo.py", args=[...])`.\n\n'
            "## Available Scripts\n\n"
            "| Script | Purpose | Arguments |\n"
            "|---|---|---|\n"
            "| `scripts/run_demo.py` | Runs the demo. | `INPUT --output-dir OUT` |\n\n"
            "## Prerequisites\n\nPython only.\n\n"
            "## Limitations\n\nEngineering fixture only.\n\n"
            "## Troubleshooting\n\nCheck stderr.\n"
            "\nUsage: `python scripts/run_demo.py sample --output-dir runs/demo`.\n"
        ),
    )
    manifest_path = skill_dir / "skill_manifest.yaml"
    manifest_text = manifest_path.read_text()
    manifest_text = manifest_text.replace("name: input", "name: source_artifact")
    manifest_text = manifest_text.replace("type: file_path", "type: artifact_path", 1)
    manifest_text = manifest_text.replace("name: output", "name: quality_summary")
    manifest_text = manifest_text.replace("type: json", "type: artifact_json", 1)
    manifest_path.write_text(manifest_text)

    checks = _checks_by_name(grade.grade_tier2(skill_dir))

    assert checks["skill_md_mentions_manifest_io"]["pass"] is False
    assert checks["skill_md_mentions_manifest_io"]["severity"] == "advisory"
    assert "inputs:source_artifact" in checks["skill_md_mentions_manifest_io"]["msg"]
    assert "outputs:quality_summary" in checks["skill_md_mentions_manifest_io"]["msg"]


def test_skill_md_must_name_required_runtime_env_vars(tmp_path: Path) -> None:
    skill_dir = _write_target_skill(
        tmp_path,
        env_required=("DEMO_ROOT",),
        skill_md_body=(
            "## Purpose\n\nRun the demo wrapper.\n\n"
            "## Instructions\n\n"
            'Use `run_script("scripts/run_demo.py", args=[...])`.\n\n'
            "## Available Scripts\n\n"
            "| Script | Purpose | Arguments |\n"
            "|---|---|---|\n"
            "| `scripts/run_demo.py` | Runs the demo. | `INPUT --output-dir OUT` |\n\n"
            "## Prerequisites\n\nPython only.\n\n"
            "## Limitations\n\nEngineering fixture only.\n\n"
            "## Troubleshooting\n\nCheck stderr.\n"
            "\nUsage: `python scripts/run_demo.py input.txt --output-dir runs/demo`.\n"
        ),
    )

    checks = _checks_by_name(grade.grade_tier2(skill_dir))

    assert checks["skill_md_mentions_runtime_env_required"]["pass"] is False
    assert checks["skill_md_mentions_runtime_env_required"]["severity"] == "advisory"
    assert "DEMO_ROOT" in checks["skill_md_mentions_runtime_env_required"]["msg"]


def test_skill_md_passes_when_required_runtime_env_vars_are_documented(tmp_path: Path) -> None:
    skill_dir = _write_target_skill(
        tmp_path,
        env_required=("DEMO_ROOT",),
        skill_md_body=(
            "## Purpose\n\nRun the demo wrapper.\n\n"
            "## Instructions\n\n"
            'Use `run_script("scripts/run_demo.py", args=[...])`.\n\n'
            "## Available Scripts\n\n"
            "| Script | Purpose | Arguments |\n"
            "|---|---|---|\n"
            "| `scripts/run_demo.py` | Runs the demo. | `INPUT --output-dir OUT` |\n\n"
            "## Prerequisites\n\nSet `DEMO_ROOT` to the demo checkout.\n\n"
            "## Limitations\n\nEngineering fixture only.\n\n"
            "## Troubleshooting\n\nCheck stderr.\n"
            "\nUsage: `DEMO_ROOT=/tmp/demo python scripts/run_demo.py input.txt --output-dir runs/demo`.\n"
        ),
    )

    checks = _checks_by_name(grade.grade_tier2(skill_dir))

    assert checks["skill_md_mentions_runtime_env_required"]["pass"] is True


def test_skill_md_must_name_runtime_optional_and_conditional_env_vars(tmp_path: Path) -> None:
    skill_dir = _write_target_skill(
        tmp_path,
        env_optional=("DEMO_CACHE",),
        env_conditional={"mock_call": "DEMO_MOCK", "live_call_any_of": ["DEMO_TOKEN"]},
        skill_md_body=(
            "## Purpose\n\nRun the demo wrapper.\n\n"
            "## Instructions\n\n"
            'Use `run_script("scripts/run_demo.py", args=[...])`.\n\n'
            "## Available Scripts\n\n"
            "| Script | Purpose | Arguments |\n"
            "|---|---|---|\n"
            "| `scripts/run_demo.py` | Runs the demo. | `INPUT --output-dir OUT` |\n\n"
            "## Prerequisites\n\nPython only.\n\n"
            "## Limitations\n\nEngineering fixture only.\n\n"
            "## Troubleshooting\n\nCheck stderr.\n"
            "\nUsage: `python scripts/run_demo.py input.txt --output-dir runs/demo`.\n"
        ),
    )

    checks = _checks_by_name(grade.grade_tier2(skill_dir))

    assert checks["skill_md_mentions_runtime_env_optional"]["pass"] is False
    assert checks["skill_md_mentions_runtime_env_optional"]["severity"] == "advisory"
    assert "DEMO_CACHE" in checks["skill_md_mentions_runtime_env_optional"]["msg"]
    assert checks["skill_md_mentions_runtime_env_conditional"]["pass"] is False
    assert checks["skill_md_mentions_runtime_env_conditional"]["severity"] == "advisory"
    assert "DEMO_MOCK" in checks["skill_md_mentions_runtime_env_conditional"]["msg"]
    assert "DEMO_TOKEN" in checks["skill_md_mentions_runtime_env_conditional"]["msg"]


def test_skill_md_passes_when_runtime_optional_and_conditional_env_vars_are_documented(tmp_path: Path) -> None:
    skill_dir = _write_target_skill(
        tmp_path,
        env_optional=("DEMO_CACHE",),
        env_conditional={"mock_call": "DEMO_MOCK", "live_call_any_of": ["DEMO_TOKEN"]},
        skill_md_body=(
            "## Purpose\n\nRun the demo wrapper.\n\n"
            "## Instructions\n\n"
            'Use `run_script("scripts/run_demo.py", args=[...])`.\n\n'
            "## Available Scripts\n\n"
            "| Script | Purpose | Arguments |\n"
            "|---|---|---|\n"
            "| `scripts/run_demo.py` | Runs the demo. | `INPUT --output-dir OUT` |\n\n"
            "## Prerequisites\n\n"
            "Set `DEMO_CACHE` to reuse downloads, `DEMO_MOCK=1` for offline "
            "runs, or `DEMO_TOKEN` for live runs.\n\n"
            "## Limitations\n\nEngineering fixture only.\n\n"
            "## Troubleshooting\n\nCheck stderr.\n"
            "\nUsage: `DEMO_MOCK=1 python scripts/run_demo.py input.txt --output-dir runs/demo`.\n"
        ),
    )

    checks = _checks_by_name(grade.grade_tier2(skill_dir))

    assert checks["skill_md_mentions_runtime_env_optional"]["pass"] is True
    assert checks["skill_md_mentions_runtime_env_conditional"]["pass"] is True


def test_skill_md_must_name_runtime_side_effects(tmp_path: Path) -> None:
    skill_dir = _write_target_skill(
        tmp_path,
        local_writes=("<caller-provided --output-dir>",),
        home_writes=("~/.cache/demo/",),
        network_endpoints=("https://example.test",),
        requires_docker=True,
        requires_gpu="cuda",
        skill_md_body=(
            "## Purpose\n\nRun the demo wrapper.\n\n"
            "## Instructions\n\n"
            'Use `run_script("scripts/run_demo.py", args=[...])`.\n\n'
            "## Available Scripts\n\n"
            "| Script | Purpose | Arguments |\n"
            "|---|---|---|\n"
            "| `scripts/run_demo.py` | Runs the demo. | `INPUT --output-dir OUT` |\n\n"
            "## Prerequisites\n\nPython only.\n\n"
            "## Limitations\n\nEngineering fixture only.\n\n"
            "## Troubleshooting\n\nCheck stderr.\n"
        ),
    )

    checks = _checks_by_name(grade.grade_tier2(skill_dir))

    assert checks["skill_md_mentions_runtime_side_effects"]["pass"] is False
    assert checks["skill_md_mentions_runtime_side_effects"]["severity"] == "advisory"
    msg = checks["skill_md_mentions_runtime_side_effects"]["msg"]
    assert "~/.cache/demo/" in msg
    assert "https://example.test" in msg
    assert "requires_docker:true" in msg
    assert "requires_gpu:cuda" in msg


def test_skill_md_passes_when_runtime_side_effects_are_documented(tmp_path: Path) -> None:
    skill_dir = _write_target_skill(
        tmp_path,
        local_writes=("<caller-provided --output-dir>",),
        home_writes=("~/.cache/demo/",),
        network_endpoints=("https://example.test",),
        requires_docker=True,
        requires_gpu="cuda",
        skill_md_body=(
            "## Purpose\n\nRun the demo wrapper.\n\n"
            "## Instructions\n\n"
            'Use `run_script("scripts/run_demo.py", args=[...])`.\n\n'
            "## Available Scripts\n\n"
            "| Script | Purpose | Arguments |\n"
            "|---|---|---|\n"
            "| `scripts/run_demo.py` | Runs the demo. | `INPUT --output-dir OUT` |\n\n"
            "## Prerequisites\n\n"
            "Writes caller outputs under `--output-dir`, may cache files under "
            "`~/.cache/demo/`, may contact `example.test`, and requires "
            "Docker plus CUDA GPU access.\n\n"
            "## Limitations\n\nEngineering fixture only.\n\n"
            "## Troubleshooting\n\nCheck stderr.\n"
        ),
    )

    checks = _checks_by_name(grade.grade_tier2(skill_dir))

    assert checks["skill_md_mentions_runtime_side_effects"]["pass"] is True


def test_import_scan_uses_python_ast_not_docstring_lines(tmp_path: Path) -> None:
    skill_dir = _write_target_skill(
        tmp_path,
        skill_md_body="## Purpose\n\nRun demo.\n",
    )
    script_path = skill_dir / "scripts" / "run_demo.py"
    script_path.write_text(
        '"""Reads facts from the recorded input and checks them."""\n'
        "import json\n"
        "print(json.dumps({'status': 'ok'}))\n"
    )

    assert grade._scan_imports(skill_dir / "scripts", skill_dir) == {"json"}


def test_import_scan_treats_verifier_shared_package_as_local(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    verifier_root = tmp_path / "verifiers"
    verifier_dir = verifier_root / "target_verifier"
    (verifier_root / "_shared").mkdir(parents=True)
    (verifier_root / "_shared" / "verifier_kit.py").write_text("def run_grader(): pass\n")
    (verifier_dir / "scripts").mkdir(parents=True)
    (verifier_dir / "scripts" / "grade.py").write_text(
        "from verifiers._shared.verifier_kit import run_grader\n"
        "import json\n"
        "print(json.dumps({'status': 'ok'}))\n"
    )
    monkeypatch.setattr(grade, "VERIFIERS_ROOT", verifier_root)

    assert grade._scan_imports(verifier_dir / "scripts", verifier_dir) == {"json"}
