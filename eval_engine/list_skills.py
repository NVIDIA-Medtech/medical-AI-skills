#!/usr/bin/env python3
"""Generate a SKILL_INDEX of every skill and verifier.

Publishable skills are the primary catalog. Verifiers and repository utilities
are listed in separate sections. Each row links declared shape and curated
evidence packs where they exist.

Run as `python -m eval_engine.list_skills` or `make list-skills`.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import typer

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from eval_engine.gate_registry import gate_categories  # noqa: E402
from eval_engine.manifest import iter_spec_manifests, load_manifest  # noqa: E402

PACK_ROOTS = (
    REPO_ROOT / "examples" / "evidence_packs",
    REPO_ROOT / "examples" / "studies",
)

DISCOVERY_SKILL_DIRS = frozenset()

# Onboarding / flagship skills listed first in SKILL_INDEX (stable order).
FEATURED_PUBLISHABLE_IDS = (
    "medagent.dicom_series_preflight",
)

app = typer.Typer(add_completion=False)


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _collect_packs() -> dict[str, set[Path]]:
    """Group evidence packs by skill_id, collapsing nested aggregator packs."""
    by_skill: dict[str, set[Path]] = defaultdict(set)
    for root in PACK_ROOTS:
        if not root.exists():
            continue
        for pack_manifest in root.rglob("manifest.json"):
            data = _load_json(pack_manifest)
            skill_id = data.get("skill_id")
            if not skill_id:
                continue
            top = pack_manifest.parent
            while top.parent != root and top.parent != top:
                top = top.parent
            by_skill[skill_id].add(top)
    return by_skill


def _format_set(items: list[dict], key: str = "formats") -> str:
    formats = set()
    for item in items or []:
        for f in item.get(key) or []:
            formats.add(f)
    return ", ".join(sorted(formats)) or "—"


def _task_summary(manifest: dict, max_len: int = 80) -> str:
    summary = (manifest.get("intended_use") or {}).get("summary") or ""
    summary = " ".join(str(summary).split())
    if len(summary) <= max_len:
        return summary or "—"
    return summary[: max_len - 1].rstrip() + "…"


def _gpu_required(manifest: dict) -> str:
    side_effects = (manifest.get("runtime") or {}).get("side_effects") or {}
    val = side_effects.get("requires_gpu", "none")
    if val in (None, "none", False, ""):
        return "no"
    if val is True:
        return "yes"
    return f"yes ({val})"


def _network(manifest: dict) -> str:
    side_effects = (manifest.get("runtime") or {}).get("side_effects") or {}
    endpoints = side_effects.get("network_endpoints") or []
    return f"{len(endpoints)}" if endpoints else "0"


def _runtime_envelope(manifest: dict) -> str:
    val = (manifest.get("validation") or {}).get("expected_runtime_seconds") or {}
    parts = []
    if "min" in val:
        parts.append(f"≥{val['min']}s")
    if "max" in val:
        parts.append(f"≤{val['max']}s")
    return " / ".join(parts) or "—"


def _rel(target: Path, base_dir: Path) -> str:
    import os

    return os.path.relpath(target, base_dir)


def _pack_links(packs: set[Path], base_dir: Path) -> str:
    return (
        ", ".join(
            f"[`{p.name}`]({_rel(p, base_dir)}/)"
            for p in sorted(packs, key=lambda x: x.name)
        )
        or "—"
    )


def _categorize(manifest_path: Path) -> str:
    """Return publishable | verifier | discovery."""
    try:
        rel = manifest_path.parent.relative_to(REPO_ROOT)
    except ValueError:
        return "publishable"
    parts = rel.parts
    if parts and parts[0] == "verifiers":
        return "verifier"
    if parts and parts[0] == "skills" and len(parts) > 1:
        if parts[1] in DISCOVERY_SKILL_DIRS:
            return "discovery"
    return "publishable"


def _verifier_coverage(manifest: dict) -> str:
    paired = manifest.get("paired_verifiers") or []
    if not paired:
        return "—"
    implemented = sum(1 for v in paired if v.get("status") == "implemented")
    planned = sum(1 for v in paired if v.get("status") != "implemented")
    parts: list[str] = []
    if implemented:
        parts.append(f"{implemented} implemented")
    if planned:
        parts.append(f"{planned} planned")
    return ", ".join(parts) or "—"


def _publishable_row(
    manifest_path: Path, manifest: dict, packs: set[Path], base_dir: Path
) -> str:
    skill_id = manifest.get("id") or manifest_path.parent.name
    rel_path = _rel(manifest_path.parent, base_dir)
    task = _task_summary(manifest)
    inputs = _format_set(manifest.get("inputs") or [])
    outputs = _format_set(manifest.get("outputs") or [])
    gpu = _gpu_required(manifest)
    net = _network(manifest)
    verifier_cov = _verifier_coverage(manifest)
    pack_links = _pack_links(packs, base_dir)
    return (
        f"| `{skill_id}` | {task} | [`{rel_path}/`]({rel_path}/) | {inputs} | "
        f"{outputs} | {gpu} | {net} | {verifier_cov} | {pack_links} |"
    )


def _verifier_row(
    manifest_path: Path, manifest: dict, packs: set[Path], base_dir: Path
) -> str:
    skill_id = manifest.get("id") or manifest_path.parent.name
    rel_path = _rel(manifest_path.parent, base_dir)
    audits = _task_summary(manifest, max_len=100)
    inputs = _format_set(manifest.get("inputs") or [])
    outputs = _format_set(manifest.get("outputs") or [])
    gates = ", ".join(gate_categories(manifest)) or "—"
    pack_links = _pack_links(packs, base_dir)
    return (
        f"| `{skill_id}` | {audits} | [`{rel_path}/`]({rel_path}/) | {inputs} | "
        f"{outputs} | {gates} | {pack_links} |"
    )


def _discovery_row(
    manifest_path: Path, manifest: dict, packs: set[Path], base_dir: Path
) -> str:
    skill_id = manifest.get("id") or manifest_path.parent.name
    rel_path = _rel(manifest_path.parent, base_dir)
    purpose = _task_summary(manifest, max_len=100)
    caller = "agent or maintainer ranking local specs"
    pack_links = _pack_links(packs, base_dir)
    return (
        f"| `{skill_id}` | {purpose} | [`{rel_path}/`]({rel_path}/) | {caller} | "
        f"{pack_links} |"
    )


def _render_section(
    title: str,
    intro: str,
    header: str,
    separator: str,
    rows: list[str],
) -> list[str]:
    lines = [f"## {title}", "", intro, ""]
    if rows:
        lines.extend([header, separator, *rows, ""])
    else:
        lines.extend(["_No entries._", ""])
    return lines


@app.command()
def main(
    out: Path = typer.Option(
        None,
        "--out",
        help="Path to write SKILL_INDEX.md. If omitted, writes to stdout.",
    ),
):
    """Generate SKILL_INDEX.md with publishable skills, verifiers, and discovery utilities."""
    manifests = iter_spec_manifests()
    packs_by_skill = _collect_packs()
    base_dir = out.parent if out else REPO_ROOT

    publishable: list[str] = []
    verifiers: list[str] = []
    discovery: list[str] = []

    for manifest_path in sorted(manifests, key=lambda p: p.parent.name):
        manifest = load_manifest(manifest_path)
        skill_id = manifest.get("id") or manifest_path.parent.name
        packs = packs_by_skill.get(skill_id, set())
        category = _categorize(manifest_path)
        if category == "verifier":
            verifiers.append(_verifier_row(manifest_path, manifest, packs, base_dir))
        elif category == "discovery":
            discovery.append(_discovery_row(manifest_path, manifest, packs, base_dir))
        else:
            publishable.append(_publishable_row(manifest_path, manifest, packs, base_dir))

    def _featured_sort_key(row: str) -> tuple[int, int, str]:
        for idx, skill_id in enumerate(FEATURED_PUBLISHABLE_IDS):
            if row.startswith(f"| `{skill_id}` |"):
                return (0, idx, row)
        return (1, 0, row)

    publishable.sort(key=_featured_sort_key)

    lines = [
        "# SKILL_INDEX",
        "",
        "Auto-generated by `eval_engine/list_skills.py` (`make list-skills`).",
        "Do not edit by hand.",
        "",
        "Browse **publishable skills** first. Verifiers audit skills or evidence",
        "packs. Repository utilities help maintainers and agents navigate the",
        "catalog — they are not medtech capabilities for end-user data.",
        "",
        "**Start here:** `medagent.dicom_series_preflight` — GPU-free DICOM folder",
        "preflight (`make run-workflow` with `examples/workflows/dicom_preflight_gate.yaml`).",
        "",
    ]

    lines.extend(
        _render_section(
            "Publishable skills",
            "Agent-callable wrappers users run with their own data. See each "
            "`SKILL.md` for invocation.",
            "| Skill ID | Task | Path | Inputs | Outputs | GPU | Network | Paired verifiers | Trust evidence |",
            "|---|---|---|---|---|---|---|---|---|",
            publishable,
        )
    )
    lines.extend(
        _render_section(
            "Verifier skills",
            "Skill-shaped auditors for second-pass trust. Declared on target skills "
            "via `paired_verifiers[]`.",
            "| Verifier ID | Audits | Path | Inputs | Outputs | Declared gates | Evidence packs |",
            "|---|---|---|---|---|---|---|",
            verifiers,
        )
    )
    lines.extend(
        _render_section(
            "Repository and discovery",
            "Utilities for catalog navigation and repo maintenance.",
            "| Artifact ID | Purpose | Path | Intended caller | Evidence packs |",
            "|---|---|---|---|---|",
            discovery,
        )
    )

    lines.extend(["Regenerate with `make list-skills`.", ""])

    output = "\n".join(lines)
    if out:
        out.write_text(output)
        print(f"Wrote {out}", file=sys.stderr)
    else:
        sys.stdout.write(output)


if __name__ == "__main__":
    app()
