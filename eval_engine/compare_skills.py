#!/usr/bin/env python3
"""Compare two skill evidence packs by declared shape.

This is a sibling to `eval_engine/diff_runs.py`. `diff_runs.py` compares
two runs of the SAME skill (drift detection). `compare_skills.py`
compares two DIFFERENT skills on a comparable
fixture.

Output is NOT a metric race. The report does not rank skills by Dice,
runtime, or any other metric. It surfaces whether the two skills'
declared specs are comparable in shape — gate-set, sanity-check
coverage, side-effects, runtime envelope, cost envelope.

Run:
    python -m eval_engine.compare_skills <pack_a> <pack_b> [--out path]
or:
    make compare-skills A=<pack_a> B=<pack_b>
"""
from __future__ import annotations

import json
from pathlib import Path

import typer

REPO_ROOT = Path(__file__).resolve().parent.parent

app = typer.Typer(add_completion=False)

GATE_CATEGORIES = (
    "preflight",
    "schema",
    "sanity",
    "runtime",
    "cost",
    "integrity",
)


def _load_json(pack: Path, name: str) -> dict:
    p = pack / name
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return {}


def _gate_status_map(summary: dict) -> dict[str, str | None]:
    """Map gate category -> declared status from validation_summary.json."""
    return {c: summary.get(f"{c}_status") for c in GATE_CATEGORIES}


def _sanity_paths(summary: dict) -> set[str]:
    paths = set()
    for r in summary.get("sanity_results", []) or []:
        check = r.get("check") or {}
        if "path" in check:
            paths.add(check["path"])
    return paths


def _side_effects(manifest_yaml: dict) -> dict:
    return ((manifest_yaml.get("runtime") or {}).get("side_effects")) or {}


def _runtime_envelope(manifest_yaml: dict) -> dict:
    return ((manifest_yaml.get("validation") or {}).get("expected_runtime_seconds")) or {}


def _cost_envelope(manifest_yaml: dict) -> dict:
    return ((manifest_yaml.get("validation") or {}).get("expected_cost")) or {}


def _emoji(status: str | None) -> str:
    if status is None:
        return "—"
    return {"passed": "✓", "failed": "✗", "skipped": "○"}.get(status, status)


def _resolve_skill_manifest(pack: Path) -> dict:
    """Find the source skill_manifest.yaml referenced by this evidence pack.

    Pack manifests use `<repo>` as a portable placeholder for the repo root.
    """
    import yaml

    pack_manifest = _load_json(pack, "manifest.json")
    skill_dir_str = pack_manifest.get("skill_dir") or pack_manifest.get("skill_path")
    if not skill_dir_str:
        return {}
    expanded = skill_dir_str.replace("<repo>", str(REPO_ROOT))
    candidate = Path(expanded) / "skill_manifest.yaml"
    if candidate.exists():
        try:
            return yaml.safe_load(candidate.read_text()) or {}
        except yaml.YAMLError:
            pass
    return {}


def _format_envelope(env: dict) -> str:
    if not env:
        return "—"
    parts = []
    if "min" in env:
        parts.append(f"≥{env['min']}")
    if "max" in env:
        parts.append(f"≤{env['max']}")
    return " / ".join(parts) or "—"


def _format_cost(cost: dict) -> str:
    if not cost:
        return "—"
    keys = sorted(cost.keys())
    return ", ".join(f"{k}: {cost[k]}" for k in keys)


def _build_report(pack_a: Path, pack_b: Path) -> str:
    summary_a = _load_json(pack_a, "validation_summary.json")
    summary_b = _load_json(pack_b, "validation_summary.json")
    pack_manifest_a = _load_json(pack_a, "manifest.json")
    pack_manifest_b = _load_json(pack_b, "manifest.json")
    skill_manifest_a = _resolve_skill_manifest(pack_a)
    skill_manifest_b = _resolve_skill_manifest(pack_b)

    skill_id_a = pack_manifest_a.get("skill_id") or pack_a.name
    skill_id_b = pack_manifest_b.get("skill_id") or pack_b.name

    gates_a = _gate_status_map(summary_a)
    gates_b = _gate_status_map(summary_b)
    declared_a = {c for c, v in gates_a.items() if v is not None}
    declared_b = {c for c, v in gates_b.items() if v is not None}

    sanity_a = _sanity_paths(summary_a)
    sanity_b = _sanity_paths(summary_b)

    se_a = _side_effects(skill_manifest_a)
    se_b = _side_effects(skill_manifest_b)
    rt_a = _runtime_envelope(skill_manifest_a)
    rt_b = _runtime_envelope(skill_manifest_b)
    cost_a = _cost_envelope(skill_manifest_a)
    cost_b = _cost_envelope(skill_manifest_b)

    lines: list[str] = []
    lines += [
        "# Skill Shape Comparison",
        "",
        f"- **Skill A:** `{skill_id_a}` (pack: `{pack_a}`)",
        f"- **Skill B:** `{skill_id_b}` (pack: `{pack_b}`)",
        "",
        "This is a declared-shape comparison, not a metric race. It",
        "surfaces whether the two skills' declared specs are comparable",
        "in shape — gate set, sanity-check coverage, side-effects, runtime",
        "and cost envelopes. It does NOT rank skills.",
        "",
        "## Gate-set verdicts",
        "",
        "| Gate | A | B | Both declared? |",
        "|---|---|---|---|",
    ]
    for c in GATE_CATEGORIES:
        a_st = _emoji(gates_a[c])
        b_st = _emoji(gates_b[c])
        both = "yes" if (c in declared_a and c in declared_b) else (
            "A only" if c in declared_a else "B only" if c in declared_b else "neither"
        )
        lines.append(f"| {c} | {a_st} | {b_st} | {both} |")

    only_a = declared_a - declared_b
    only_b = declared_b - declared_a
    lines += [
        "",
        "## Gate-set differences",
        "",
    ]
    if only_a or only_b:
        if only_a:
            lines.append(
                f"- A declares gate categories B does not: {sorted(only_a)}"
            )
        if only_b:
            lines.append(
                f"- B declares gate categories A does not: {sorted(only_b)}"
            )
    else:
        lines.append("- Both skills declare the same gate categories.")

    lines += [
        "",
        "## Sanity-check coverage",
        "",
        f"- A: {len(sanity_a)} declared sanity-check paths",
        f"- B: {len(sanity_b)} declared sanity-check paths",
    ]
    if sanity_a:
        lines.append(
            "- A paths: " + ", ".join(f"`{p}`" for p in sorted(sanity_a))
        )
    if sanity_b:
        lines.append(
            "- B paths: " + ", ".join(f"`{p}`" for p in sorted(sanity_b))
        )

    lines += [
        "",
        "## Side-effects",
        "",
        "| Field | A | B |",
        "|---|---|---|",
        f"| `requires_gpu` | {se_a.get('requires_gpu', 'none')} | {se_b.get('requires_gpu', 'none')} |",
        f"| `requires_docker` | {se_a.get('requires_docker', False)} | {se_b.get('requires_docker', False)} |",
        f"| `network_endpoints` | {len(se_a.get('network_endpoints') or [])} | {len(se_b.get('network_endpoints') or [])} |",
        f"| `pip_packages` | {len(se_a.get('pip_packages') or [])} | {len(se_b.get('pip_packages') or [])} |",
        "",
        "## Runtime envelope",
        "",
        f"- A: {_format_envelope(rt_a)}",
        f"- B: {_format_envelope(rt_b)}",
        "",
        "## Cost envelope",
        "",
        f"- A: {_format_cost(cost_a)}",
        f"- B: {_format_cost(cost_b)}",
        "",
        "## Reading this report",
        "",
        "A skill that declares more gate categories has a tighter spec.",
        "A skill that declares the same categories with more sanity-check",
        "paths covers more failure modes. Neither is universally better —",
        "the right choice depends on your task's risk profile, side-effects",
        "budget, and runtime/cost envelope.",
        "",
    ]
    return "\n".join(lines)


@app.command()
def main(
    pack_a: Path = typer.Argument(..., help="First evidence pack."),
    pack_b: Path = typer.Argument(..., help="Second evidence pack."),
    out: Path = typer.Option(
        None,
        "--out",
        help="Output report path. Default: <pack_b>/conformance_report.md",
    ),
):
    """Compare two skill evidence packs by declared shape."""
    if not pack_a.is_dir() or not pack_b.is_dir():
        raise typer.BadParameter("Both arguments must be evidence pack directories.")

    report = _build_report(pack_a, pack_b)
    out_path = out or (pack_b / "conformance_report.md")
    out_path.write_text(report)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    app()
