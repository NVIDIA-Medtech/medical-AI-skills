"""Skill manifest loading helpers for eval_engine runners."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from eval_engine.manifest import (
    first_input,
    json_output_schema_path,
    load_manifest,
    manifest_path_for_skill,
    resolve_entrypoint,
)


def _load_skill(skill_dir: Path) -> dict:
    """Read skill_manifest.yaml; return {entrypoint, schema_path, manifest}."""
    manifest_path = manifest_path_for_skill(skill_dir)
    if not manifest_path.exists():
        raise FileNotFoundError(f"missing skill_manifest.yaml: {manifest_path}")
    manifest = load_manifest(manifest_path)
    script = resolve_entrypoint(skill_dir, manifest)
    if not script.exists():
        raise FileNotFoundError(f"entrypoint missing: {script}")
    schema_path = json_output_schema_path(skill_dir, manifest)
    return {"script": script, "schema_path": schema_path, "manifest": manifest}


def _first_input(manifest: dict) -> dict:
    return first_input(manifest)


_TOKEN_RE = re.compile(r"\$\{([^}]+)\}")


class RuntimeArgsError(RuntimeError):
    """Raised when runtime.args references an unknown token or missing env var."""


def render_runtime_args(
    *,
    manifest: dict,
    script: Path,
    fixture: Path,
    out: Path,
    skill_dir: Path,
    python_executable: str | None = None,
    env: dict | None = None,
    redact_env: bool = False,
) -> list[str]:
    """Render runtime.args into a concrete command list.

    Tokens: ${python}, ${script}, ${fixture}, ${out}, ${skill_dir}, ${env.VAR}.
    When manifest.runtime.args is absent, falls back to the historical default
    ``[python, script, fixture]`` so unmigrated skills keep working.
    If redact_env is true, env tokens render as shell env references for pack
    metadata/replay instead of raw secret values.
    """
    args_template = (manifest.get("runtime") or {}).get("args")
    python_bin = python_executable or sys.executable
    env_map = env if env is not None else os.environ

    if not args_template:
        return [python_bin, str(script), str(fixture)]

    bindings = {
        "python": python_bin,
        "script": str(script),
        "fixture": str(fixture),
        "out": str(out),
        "skill_dir": str(skill_dir),
    }

    def _resolve(token: str) -> str:
        if token.startswith("env."):
            var = token[4:]
            value = env_map.get(var)
            if value is None:
                raise RuntimeArgsError(
                    f"runtime.args references ${{{token}}} but env var {var} is not set"
                )
            if redact_env:
                return f"${{{var}:?{var} is required for replay}}"
            return value
        if token in bindings:
            return bindings[token]
        raise RuntimeArgsError(f"runtime.args has unknown token: ${{{token}}}")

    rendered = []
    for entry in args_template:
        if not isinstance(entry, str):
            raise RuntimeArgsError(f"runtime.args entries must be strings, got {type(entry).__name__}")
        rendered.append(_TOKEN_RE.sub(lambda m: _resolve(m.group(1)), entry))
    return rendered
