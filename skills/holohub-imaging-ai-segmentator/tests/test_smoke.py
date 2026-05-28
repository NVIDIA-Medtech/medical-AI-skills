"""Smoke tests for holohub_imaging_ai_segmentator skill.

These tests run on CPU, require no GPU, no Docker, and no network.  They
verify that the static artefacts (manifest, output schema) are well-formed
and that the entrypoint script is syntactically valid Python.  Full
integration testing requires Docker and an NVIDIA GPU — see SKILL.md.
"""
import ast
import json
from pathlib import Path

import yaml

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPT = SKILL_DIR / "scripts" / "run_holohub_app.py"
MANIFEST = SKILL_DIR / "skill_manifest.yaml"
SCHEMA = SKILL_DIR / "validators" / "output_schema.json"

# Required top-level keys defined by the skill manifest schema.
_MANIFEST_REQUIRED_KEYS = {"id", "version", "inputs", "outputs", "runtime"}


def test_manifest_is_valid_yaml_and_has_required_keys() -> None:
    """skill_manifest.yaml must parse cleanly and contain the required keys."""
    assert MANIFEST.exists(), f"manifest not found: {MANIFEST}"
    data = yaml.safe_load(MANIFEST.read_text())
    assert isinstance(data, dict), "manifest must be a YAML mapping"
    missing = _MANIFEST_REQUIRED_KEYS - data.keys()
    assert not missing, f"manifest missing required keys: {sorted(missing)}"


def test_manifest_entrypoint_points_to_existing_script() -> None:
    """The entrypoint declared in the manifest must resolve to a real file."""
    data = yaml.safe_load(MANIFEST.read_text())
    entrypoint = data.get("runtime", {}).get("entrypoint", "")
    assert entrypoint, "runtime.entrypoint must not be empty"
    resolved = SKILL_DIR / entrypoint
    assert resolved.exists(), f"entrypoint {entrypoint!r} not found at {resolved}"


def test_output_schema_is_valid_json() -> None:
    """validators/output_schema.json must parse as valid JSON."""
    assert SCHEMA.exists(), f"output schema not found: {SCHEMA}"
    data = json.loads(SCHEMA.read_text())
    assert isinstance(data, dict), "output schema must be a JSON object"


def test_output_schema_has_required_top_level_keys() -> None:
    """The output schema must declare the top-level envelope keys."""
    data = json.loads(SCHEMA.read_text())
    required = set(data.get("required", []))
    for key in ("invocation", "output", "runtime", "logs"):
        assert key in required, f"output schema missing required key: {key!r}"


def test_entrypoint_script_is_valid_python() -> None:
    """The entrypoint script must be syntactically valid Python (AST parse only).

    A full import is skipped here because the script performs top-level
    sys.path manipulation and imports GPU/Docker helper modules
    (_shared.docker_capture, _shared.wrapper_utils) that are absent in a
    CPU-only environment.
    """
    assert SCRIPT.exists(), f"entrypoint script not found: {SCRIPT}"
    source = SCRIPT.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(SCRIPT))
    except SyntaxError as exc:
        raise AssertionError(f"syntax error in {SCRIPT}: {exc}") from exc
    assert isinstance(tree, ast.Module)
