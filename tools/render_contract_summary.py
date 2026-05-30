#!/usr/bin/env python3
"""Render a read-only Markdown contract summary for one skill or verifier."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
MAX_LIST_ITEMS = 12


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text())
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _display_path(path: Path, *, base: Path = REPO_ROOT) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _scalar(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        if not value:
            return "[]"
        return ", ".join(_scalar(item) for item in value[:MAX_LIST_ITEMS])
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    text = str(value).replace("\n", " ")
    return text if len(text) <= 180 else text[:177] + "..."


def _md_cell(value: Any) -> str:
    return _scalar(value).replace("|", "\\|")


def _table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    if not rows:
        return ["_None._"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_md_cell(item) for item in row) + " |")
    return lines


def _parse_frontmatter(skill_md: Path) -> tuple[dict[str, Any], str]:
    if not skill_md.exists():
        return {}, ""
    text = skill_md.read_text()
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    try:
        frontmatter = yaml.safe_load(text[4:end]) or {}
    except Exception:
        frontmatter = {}
    body = text[end + len("\n---\n") :]
    return (frontmatter if isinstance(frontmatter, dict) else {}), body


def _section_items(body: str, section: str) -> list[str]:
    if not body:
        return []
    pattern = re.compile(rf"^## {re.escape(section)}\s*$", re.MULTILINE)
    match = pattern.search(body)
    if not match:
        return []
    start = match.end()
    next_match = re.search(r"^##\s+", body[start:], re.MULTILINE)
    chunk = body[start : start + next_match.start()] if next_match else body[start:]
    items: list[str] = []
    for raw in chunk.splitlines():
        line = raw.strip()
        if line.startswith("- "):
            items.append(line[2:].strip())
    return items


def _schema_summary(skill_dir: Path, output: dict[str, Any]) -> str:
    schema_rel = output.get("schema")
    if not isinstance(schema_rel, str) or not schema_rel:
        return "-"
    schema = _load_json(skill_dir / schema_rel)
    required = schema.get("required")
    if isinstance(required, list) and required:
        return ", ".join(str(item) for item in required[:MAX_LIST_ITEMS])
    return "schema declared"


def _input_rows(manifest: dict[str, Any]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for item in manifest.get("inputs") or []:
        if isinstance(item, dict):
            rows.append([
                item.get("name"),
                item.get("type"),
                item.get("formats") or "-",
                item.get("max_size_bytes") or "-",
            ])
    return rows


def _output_rows(skill_dir: Path, manifest: dict[str, Any]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for item in manifest.get("outputs") or []:
        if isinstance(item, dict):
            rows.append([
                item.get("name"),
                item.get("type"),
                item.get("schema") or "-",
                _schema_summary(skill_dir, item),
            ])
    return rows


def _runtime_rows(manifest: dict[str, Any]) -> list[list[Any]]:
    runtime = manifest.get("runtime") if isinstance(manifest.get("runtime"), dict) else {}
    assert isinstance(runtime, dict)
    args = runtime.get("args")
    return [
        ["language", runtime.get("language")],
        ["python", runtime.get("python")],
        ["entrypoint", runtime.get("entrypoint")],
        ["args", args if args else "[python, entrypoint, fixture]"],
        ["env_required", runtime.get("env_required") or []],
        ["env_optional", runtime.get("env_optional") or []],
        ["env_conditional", runtime.get("env_conditional") or {}],
    ]


def _side_effect_rows(manifest: dict[str, Any]) -> list[list[Any]]:
    runtime = manifest.get("runtime") if isinstance(manifest.get("runtime"), dict) else {}
    side_effects = runtime.get("side_effects") if isinstance(runtime, dict) else {}
    if not isinstance(side_effects, dict):
        return []
    return [
        ["pip_packages", side_effects.get("pip_packages") or []],
        ["local_writes", side_effects.get("local_writes") or []],
        ["home_writes", side_effects.get("home_writes") or []],
        ["network_endpoints", side_effects.get("network_endpoints") or []],
        ["requires_docker", side_effects.get("requires_docker")],
        ["requires_gpu", side_effects.get("requires_gpu")],
        ["gpu_fallback", side_effects.get("gpu_fallback")],
    ]


def _validation_rows(manifest: dict[str, Any]) -> list[list[Any]]:
    validation = manifest.get("validation") if isinstance(manifest.get("validation"), dict) else {}
    assert isinstance(validation, dict)
    rows: list[list[Any]] = []
    if validation.get("expected_runtime_seconds"):
        rows.append(["expected_runtime_seconds", validation.get("expected_runtime_seconds")])
    sanity = validation.get("sanity_checks") or []
    rows.append(["sanity_checks", f"{len(sanity)} declared"])
    if validation.get("expected_cost"):
        rows.append(["expected_cost", validation.get("expected_cost")])
    if validation.get("env_pin"):
        rows.append(["env_pin", validation.get("env_pin")])
    if validation.get("factual_echo"):
        rows.append(["factual_echo", validation.get("factual_echo")])
    if validation.get("runtime_integrity"):
        rows.append(["runtime_integrity", validation.get("runtime_integrity")])
    if validation.get("model_identity"):
        rows.append(["model_identity", validation.get("model_identity")])
    if validation.get("expected_axcodes"):
        rows.append(["expected_axcodes", validation.get("expected_axcodes")])
    if validation.get("reproducibility"):
        rows.append(["reproducibility", validation.get("reproducibility")])
    return rows


def _paired_verifier_rows(manifest: dict[str, Any]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for item in manifest.get("paired_verifiers") or []:
        if isinstance(item, dict):
            rows.append([
                item.get("id"),
                item.get("status"),
                item.get("consumes") or "-",
                item.get("purpose") or "-",
            ])
    return rows


def _evidence_anchor_rows(skill_id: str) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for root in (REPO_ROOT / "examples" / "evidence_packs", REPO_ROOT / "examples" / "studies"):
        if not root.is_dir():
            continue
        for manifest_path in sorted(root.rglob("manifest.json")):
            manifest = _load_json(manifest_path)
            if manifest.get("skill_id") == skill_id:
                rows.append([
                    _display_path(manifest_path.parent),
                    manifest.get("pack_kind") or "legacy",
                    manifest.get("run_id") or "-",
                ])
        for trust_path in sorted(root.rglob("trust_summary.json")):
            trust = _load_json(trust_path)
            if trust.get("skill_id") == skill_id:
                rows.append([
                    _display_path(trust_path.parent),
                    "trusted_run",
                    trust.get("overall") or "-",
                ])
    return rows


def render_contract_summary(skill_dir: Path) -> str:
    skill_dir = skill_dir.resolve()
    manifest_path = skill_dir / "skill_manifest.yaml"
    skill_md = skill_dir / "SKILL.md"
    manifest = _load_yaml(manifest_path)
    frontmatter, body = _parse_frontmatter(skill_md)
    title = frontmatter.get("name") or manifest.get("id") or skill_dir.name
    skill_id = str(manifest.get("id") or "")
    limitations = manifest.get("limitations") or _section_items(body, "Limitations")

    lines: list[str] = [
        f"# Contract Summary: {title}",
        "",
        "## Identity",
    ]
    lines.extend(_table(["Field", "Value"], [
        ["path", _display_path(skill_dir)],
        ["manifest_id", manifest.get("id")],
        ["version", manifest.get("version")],
        ["frontmatter_name", frontmatter.get("name")],
        ["description", frontmatter.get("description")],
        ["license", manifest.get("license") or frontmatter.get("license")],
        ["intended_use", (manifest.get("intended_use") or {}).get("summary") if isinstance(manifest.get("intended_use"), dict) else manifest.get("intended_use")],
    ]))

    lines.extend(["", "## Inputs"])
    lines.extend(_table(["Name", "Type", "Formats", "Max Size"], _input_rows(manifest)))
    lines.extend(["", "## Outputs"])
    lines.extend(_table(["Name", "Type", "Schema", "Required Fields"], _output_rows(skill_dir, manifest)))
    lines.extend(["", "## Invocation"])
    lines.extend(_table(["Field", "Value"], _runtime_rows(manifest)))
    lines.extend(["", "## Gates And Reproducibility"])
    lines.extend(_table(["Gate", "Declaration"], _validation_rows(manifest)))
    lines.extend(["", "## Side Effects"])
    lines.extend(_table(["Field", "Declaration"], _side_effect_rows(manifest)))
    lines.extend(["", "## Paired Verifiers"])
    lines.extend(_table(["Verifier", "Status", "Consumes", "Purpose"], _paired_verifier_rows(manifest)))
    lines.extend(["", "## Evidence Anchors"])
    lines.extend(_table(["Path", "Kind", "Run/Verdict"], _evidence_anchor_rows(skill_id)))
    lines.extend(["", "## Limitations"])
    if limitations:
        lines.extend(f"- {_scalar(item)}" for item in limitations[:MAX_LIST_ITEMS])
    else:
        lines.append("_None declared._")
    lines.extend([
        "",
        "## Reviewer Next Steps",
        "- Run the direct script from `SKILL.md` for user data.",
        "- Run `make run-skill` or `make run-trusted` when evidence is needed.",
        "- Render a review packet for any pack before opening individual JSON files.",
    ])
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_dir", type=Path, help="Path to skills/<name> or verifiers/<name>")
    parser.add_argument("--out", type=Path, help="Optional markdown output path")
    args = parser.parse_args(argv)

    if not args.skill_dir.is_dir():
        parser.error(f"not a directory: {args.skill_dir}")
    markdown = render_contract_summary(args.skill_dir)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(markdown)
    else:
        sys.stdout.write(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
