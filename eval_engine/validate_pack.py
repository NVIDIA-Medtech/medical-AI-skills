#!/usr/bin/env python3
"""Validate an evidence pack directory against spec/evidence_pack.schema.json.

Reads the pack-level descriptor, walks each declared file, validates JSON files
against their per-file JSON Schema, and checks pack_format_version against the
descriptor's supported_pack_format_versions list.

Usage:
    python -m eval_engine.validate_pack <pack_dir>

Exits 0 on pass, 2 on contract violation.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import jsonschema
import typer

from eval_engine.common import REPO_ROOT
from eval_engine.trace import normalize_legacy_trace_record

SPEC_DIR = REPO_ROOT / "spec"
DESCRIPTOR_PATH = SPEC_DIR / "evidence_pack.schema.json"

app = typer.Typer(add_completion=False)


@lru_cache(maxsize=1)
def _load_descriptor() -> dict:
    return json.loads(DESCRIPTOR_PATH.read_text())


@lru_cache(maxsize=32)
def _load_schema(rel_path: str) -> dict:
    return json.loads((SPEC_DIR / rel_path).read_text())


def _validate_jsonl(
    path: Path,
    *,
    schema_rel: str | None = None,
    allow_legacy: bool = False,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    schema = _load_schema(schema_rel) if schema_rel else None
    text = path.read_text()
    if not text.strip():
        return errors, warnings
    for i, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"{path.name} line {i}: {e}")
            continue
        if not isinstance(payload, dict):
            errors.append(f"{path.name} line {i}: record is not a JSON object")
            continue
        if schema is None:
            continue
        try:
            jsonschema.validate(payload, schema)
            continue
        except jsonschema.ValidationError as e:
            if not allow_legacy:
                errors.append(f"{path.name} line {i}: {e.message} at {list(e.absolute_path)}")
                continue
        normalized = normalize_legacy_trace_record(payload)
        try:
            jsonschema.validate(normalized, schema)
        except jsonschema.ValidationError as e:
            errors.append(f"{path.name} line {i}: {e.message} at {list(e.absolute_path)}")
            continue
        warnings.append(
            f"{path.name} line {i}: accepted legacy trace aliases under --allow-legacy"
        )
    return errors, warnings


def _validate_file(
    pack_dir: Path,
    name: str,
    decl: dict,
    *,
    allow_legacy: bool = False,
) -> tuple[str, list[str], list[str]]:
    target = pack_dir / name
    required = decl.get("required", False)
    ftype = decl.get("type")

    if name.endswith("/"):
        if target.exists() and not target.is_dir():
            return "fail", [f"{name}: expected directory, found file"], []
        if required and not target.exists():
            return "fail", [f"{name}: required subdirectory missing"], []
        return ("ok" if target.exists() else "absent"), [], []

    if not target.exists():
        if required:
            return "fail", [f"{name}: required file missing"], []
        return "absent", [], []

    if ftype == "json":
        try:
            payload = json.loads(target.read_text())
        except json.JSONDecodeError as e:
            return "fail", [f"{name}: invalid JSON ({e})"], []
        schema_rel = decl.get("schema")
        if schema_rel:
            schema = _load_schema(schema_rel)
            try:
                jsonschema.validate(payload, schema)
            except jsonschema.ValidationError as e:
                return "fail", [f"{name}: {e.message} at {list(e.absolute_path)}"], []
        return "ok", [], []

    if ftype == "jsonl":
        errs, warns = _validate_jsonl(
            target,
            schema_rel=decl.get("schema"),
            allow_legacy=allow_legacy,
        )
        return ("ok" if not errs else "fail"), errs, warns

    if ftype in ("text", "markdown", "shell"):
        if not target.is_file():
            return "fail", [f"{name}: expected file"], []
        return "ok", [], []

    return "ok", [], []


def _check_pack_version(pack_dir: Path, descriptor: dict, allow_legacy: bool) -> tuple[list[str], list[str]]:
    """Return (errors, warnings)."""
    manifest_path = pack_dir / "manifest.json"
    if not manifest_path.exists():
        return [], []
    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError:
        return [], []
    version = manifest.get("pack_format_version")
    supported = descriptor.get("supported_pack_format_versions", [])
    if version is None:
        msg = (
            "manifest.json: missing pack_format_version "
            "(pre-1.0 pack; rerun the skill to stamp the current contract)"
        )
        if allow_legacy:
            return [], [msg]
        return [msg], []
    if supported and version not in supported:
        return [
            f"manifest.json: pack_format_version {version} not in supported "
            f"versions {supported}"
        ], []
    return [], []


def _validate_single_pack(
    pack_dir: Path,
    descriptor: dict,
    *,
    allow_legacy: bool,
    label: str | None = None,
) -> tuple[list[str], list[str], list[str]]:
    all_errors: list[str] = []
    all_warnings: list[str] = []
    errs, warns = _check_pack_version(pack_dir, descriptor, allow_legacy)
    all_errors.extend(errs)
    all_warnings.extend(warns)

    heading = f"validate-pack: {pack_dir}" if label is None else f"validate-pack {label}: {pack_dir}"
    lines: list[str] = [heading]
    for name, decl in descriptor["files"].items():
        status, errs, warns = _validate_file(
            pack_dir,
            name,
            decl,
            allow_legacy=allow_legacy,
        )
        marker = {"ok": "ok", "absent": "--", "fail": "FAIL"}.get(status, status)
        lines.append(f"  [{marker}] {name}")
        all_errors.extend(errs)
        all_warnings.extend(warns)
    return lines, all_errors, all_warnings


def _read_json_object(path: Path) -> tuple[dict | None, str | None]:
    if not path.exists():
        return None, f"{path.name}: required file missing"
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return None, f"{path.name}: invalid JSON ({e})"
    if not isinstance(payload, dict):
        return None, f"{path.name}: expected JSON object"
    return payload, None


def _looks_like_trusted_run(pack_dir: Path) -> bool:
    return (pack_dir / "trust_summary.json").exists() and not (pack_dir / "manifest.json").exists()


def _validate_trusted_run(
    pack_dir: Path,
    descriptor: dict,
    *,
    allow_legacy: bool,
) -> tuple[list[str], list[str], list[str]]:
    lines: list[str] = [f"validate-pack trusted-run: {pack_dir}"]
    all_errors: list[str] = []
    all_warnings: list[str] = []

    trust_decl = descriptor["files"]["trust_summary.json"]
    status, errs, warns = _validate_file(
        pack_dir,
        "trust_summary.json",
        {**trust_decl, "required": True},
        allow_legacy=allow_legacy,
    )
    marker = {"ok": "ok", "absent": "--", "fail": "FAIL"}.get(status, status)
    lines.append(f"  [{marker}] trust_summary.json")
    all_errors.extend(errs)
    all_warnings.extend(warns)

    trust_summary, trust_err = _read_json_object(pack_dir / "trust_summary.json")
    if trust_err:
        all_errors.append(trust_err)
        return lines, all_errors, all_warnings

    skill_pack_rel = str(trust_summary.get("skill_pack") or "skill_run")
    nested: list[tuple[str, Path]] = [("skill", pack_dir / skill_pack_rel)]
    for verifier in trust_summary.get("verifiers") or []:
        if not isinstance(verifier, dict):
            continue
        pack_rel = verifier.get("pack")
        verifier_id = verifier.get("id") or "verifier"
        if not isinstance(pack_rel, str) or not pack_rel:
            all_errors.append(f"verifier {verifier_id}: missing pack path")
            continue
        nested.append((f"verifier {verifier_id}", pack_dir / pack_rel))

    for label, nested_pack in nested:
        if not nested_pack.is_dir():
            all_errors.append(f"{label}: nested pack missing: {nested_pack}")
            lines.append(f"  [FAIL] {label} -> {nested_pack}")
            continue
        sub_lines, errs, warns = _validate_single_pack(
            nested_pack,
            descriptor,
            allow_legacy=allow_legacy,
            label=label,
        )
        lines.extend(sub_lines)
        all_errors.extend(f"{label}: {err}" for err in errs)
        all_warnings.extend(f"{label}: {warn}" for warn in warns)
    return lines, all_errors, all_warnings


@app.command()
def main(
    pack_dir: Path = typer.Argument(..., exists=True, file_okay=False),
    allow_legacy: bool = typer.Option(
        False,
        "--allow-legacy",
        help="Demote 'missing pack_format_version' to a warning so pre-1.0 reference packs still validate.",
    ),
) -> None:
    pack_dir = pack_dir.resolve()
    descriptor = _load_descriptor()
    if _looks_like_trusted_run(pack_dir):
        lines, all_errors, all_warnings = _validate_trusted_run(
            pack_dir,
            descriptor,
            allow_legacy=allow_legacy,
        )
        success_message = "trusted-run validates against spec/evidence_pack.schema.json"
    else:
        lines, all_errors, all_warnings = _validate_single_pack(
            pack_dir,
            descriptor,
            allow_legacy=allow_legacy,
        )
        success_message = "pack validates against spec/evidence_pack.schema.json"

    for line in lines:
        typer.echo(line)

    if all_warnings:
        typer.echo("")
        typer.echo("warnings:")
        for w in all_warnings:
            typer.echo("  - " + w)

    if all_errors:
        typer.echo("")
        typer.echo("errors:")
        for e in all_errors:
            typer.echo("  - " + e)
        raise typer.Exit(2)

    typer.echo("")
    typer.echo(success_message)


if __name__ == "__main__":
    app()
