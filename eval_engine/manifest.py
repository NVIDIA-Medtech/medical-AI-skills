"""Canonical helpers for loading and validating skill/verifier specs."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_ROOT = REPO_ROOT / "skills"
VERIFIERS_ROOT = REPO_ROOT / "verifiers"
SPEC_ROOTS = (SKILLS_ROOT, VERIFIERS_ROOT)
MANIFEST_SCHEMA_PATH = REPO_ROOT / "spec" / "skill_manifest.schema.json"


def load_manifest(path: Path) -> dict:
    """Load a YAML skill manifest and require a mapping at the root."""
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"invalid YAML in {path}: {e}") from e
    if not isinstance(data, dict):
        raise ValueError(f"manifest root must be a mapping: {path}")
    return data


def manifest_path_for_skill(skill_dir: Path) -> Path:
    return skill_dir / "skill_manifest.yaml"


def iter_skill_dirs(root: Path = SKILLS_ROOT) -> list[Path]:
    """Return committed wrapper-skill dirs, excluding fixtures."""
    if not root.is_dir():
        return []
    dirs: list[Path] = []
    for manifest_path in sorted(root.rglob("skill_manifest.yaml")):
        if "fixtures" in manifest_path.relative_to(root).parts:
            continue
        dirs.append(manifest_path.parent)
    return dirs


def iter_spec_dirs(roots: tuple[Path, ...] = SPEC_ROOTS) -> list[Path]:
    """Return committed skill and verifier dirs, excluding fixture specs."""
    dirs: list[Path] = []
    for root in roots:
        dirs.extend(iter_skill_dirs(root))
    return sorted(dirs)


def iter_skill_manifests(root: Path = SKILLS_ROOT) -> list[Path]:
    return [manifest_path_for_skill(skill_dir) for skill_dir in iter_skill_dirs(root)]


def iter_spec_manifests(roots: tuple[Path, ...] = SPEC_ROOTS) -> list[Path]:
    return [manifest_path_for_skill(spec_dir) for spec_dir in iter_spec_dirs(roots)]


def first_input(manifest: dict) -> dict:
    inputs = manifest.get("inputs", []) or []
    return inputs[0] if inputs and isinstance(inputs[0], dict) else {}


def resolve_entrypoint(skill_dir: Path, manifest: dict) -> Path:
    runtime = manifest.get("runtime", {}) or {}
    entry = runtime.get("entrypoint")
    if not entry:
        raise ValueError(
            f"manifest has no runtime.entrypoint: {manifest_path_for_skill(skill_dir)}"
        )
    return (skill_dir / entry).resolve()


def json_output_schema_path(skill_dir: Path, manifest: dict) -> Path | None:
    for out in manifest.get("outputs", []) or []:
        if isinstance(out, dict) and out.get("type") == "json" and out.get("schema"):
            return (skill_dir / out["schema"]).resolve()
    return None


def validate_manifest_schema(
    manifest: dict,
    *,
    schema_path: Path = MANIFEST_SCHEMA_PATH,
) -> list[str]:
    """Validate a manifest against the current schema and return errors."""
    if not schema_path.exists():
        return [f"manifest schema missing: {schema_path}"]
    schema = json.loads(schema_path.read_text())
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(manifest), key=lambda e: list(e.path))
    messages: list[str] = []
    for error in errors:
        loc = ".".join(str(part) for part in error.path) or "<root>"
        messages.append(f"{loc}: {error.message}")
    return messages


def paired_verifier_dir(
    verifier_id: str,
    *,
    verifiers_root: Path = VERIFIERS_ROOT,
) -> Path:
    return verifiers_root / verifier_id.split(".")[-1]


def paired_verifier_resolution_errors(
    manifest: dict,
    *,
    verifiers_root: Path = VERIFIERS_ROOT,
) -> list[str]:
    """Return missing verifier errors for implemented paired_verifiers."""
    errors: list[str] = []
    for idx, decl in enumerate(manifest.get("paired_verifiers") or []):
        if not isinstance(decl, dict):
            errors.append(f"paired_verifiers[{idx}] must be a mapping")
            continue
        if decl.get("status") != "implemented":
            continue
        verifier_id = str(decl.get("id") or "")
        verifier_manifest = (
            paired_verifier_dir(verifier_id, verifiers_root=verifiers_root)
            / "skill_manifest.yaml"
        )
        if not verifier_manifest.exists():
            errors.append(f"implemented paired verifier not found: {verifier_id}")
    return errors
