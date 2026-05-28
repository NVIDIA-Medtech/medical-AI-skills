#!/usr/bin/env python3
"""Render a cross-skill benchmark matrix from existing benchmark evidence packs.

Reads every benchmark evidence pack under a search root (default `runs/` and
`examples/evidence_packs/`), groups by benchmark dataset, and emits a markdown
table per benchmark: one row per skill, one column per declared axis, sorted by
the first higher_better axis.

This is the "matrix, not leaderboard" surface. It carries no single ranking score
and no aggregate across benchmarks; comparison is per-task-class only.

A benchmark pack is identified by:
  * `manifest.json` with `pack_kind == "benchmark_run"`
  * sibling `output.json` matching `spec/benchmark_result.schema.json`

The axes column set is taken from the benchmark manifest's optional `axes:` block
(see `benchmarks/ct_segmentation_spleen_msd09.benchmark.yaml` for the format). If
the benchmark manifest has no `axes:` block, the renderer falls back to a default
quartet for segmentation benchmarks: dice_mean, dice_p10, hd_mean_mm, coverage_pct.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import typer
import yaml

HARNESS_DIR = Path(__file__).resolve().parent
REPO_PARENT = HARNESS_DIR.parent
if str(REPO_PARENT) not in sys.path:
    sys.path.insert(0, str(REPO_PARENT))

from eval_engine.common import _read_json_or_empty  # noqa: E402
from eval_engine.evidence import PACK_KIND_BENCHMARK_RUN  # noqa: E402
from eval_engine.gates import _resolve_path  # noqa: E402

app = typer.Typer(add_completion=False)

DEFAULT_SEARCH_ROOTS = ("runs", "examples/evidence_packs", "examples/studies")
DEFAULT_AXES_FALLBACK = (
    {"name": "dice_mean", "field": "output.dice.mean", "direction": "higher_better", "unit": "ratio"},
    {"name": "dice_p10", "field": "output.dice.p10", "direction": "higher_better", "unit": "ratio"},
    {"name": "hd_mean_mm", "field": "output.hd.mean", "direction": "lower_better", "unit": "mm"},
    {"name": "coverage_pct", "field": "output.coverage_pct", "direction": "higher_better", "unit": "percent"},
)


@dataclass(frozen=True)
class BaselineRow:
    skill_id: str
    skill_version: str
    pack_path: Path
    values: tuple[tuple[str, float | None], ...]


def _scalar(value: object) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _benchmark_id(spec: dict, manifest_path: Path) -> str:
    return str(spec.get("dataset") or spec.get("name") or manifest_path.stem)


def _load_yaml_cached(path: Path, cache: dict[Path, dict]) -> dict:
    if path not in cache:
        try:
            cache[path] = yaml.safe_load(path.read_text()) or {}
        except Exception:
            cache[path] = {}
    return cache[path]


def _benchmark_axes(spec: dict) -> tuple[dict, ...]:
    raw = spec.get("axes")
    if isinstance(raw, list) and raw:
        return tuple(a for a in raw if isinstance(a, dict) and a.get("field"))
    return DEFAULT_AXES_FALLBACK


def _iter_benchmark_packs(roots: Iterable[Path]) -> Iterable[tuple[Path, dict, dict]]:
    """Yield (pack_dir, manifest_dict, output_dict) for each benchmark pack."""
    for root in roots:
        for manifest_path in root.rglob("manifest.json"):
            manifest = _read_json_or_empty(manifest_path)
            if not manifest or manifest.get("pack_kind") != PACK_KIND_BENCHMARK_RUN:
                continue
            output = _read_json_or_empty(manifest_path.parent / "output.json")
            if output is None:
                continue
            yield manifest_path.parent, manifest, output


def _group_by_benchmark(
    packs: Iterable[tuple[Path, dict, dict]],
    repo_root: Path,
    yaml_cache: dict[Path, dict],
) -> dict[str, list[tuple[Path, dict, dict, Path | None]]]:
    grouped: dict[str, list[tuple[Path, dict, dict, Path | None]]] = {}
    for pack_dir, manifest, output in packs:
        benchmark_block = output.get("benchmark") or {}
        benchmark_yaml_str = benchmark_block.get("manifest_path") or manifest.get(
            "benchmark_manifest", {}
        ).get("path")
        benchmark_yaml: Path | None = None
        if benchmark_yaml_str:
            candidate = Path(benchmark_yaml_str)
            if not candidate.is_absolute():
                candidate = repo_root / candidate
            benchmark_yaml = candidate.resolve() if candidate.exists() else None
        if benchmark_yaml:
            bid = _benchmark_id(_load_yaml_cached(benchmark_yaml, yaml_cache), benchmark_yaml)
        else:
            bid = benchmark_block.get("dataset") or "unknown"
        grouped.setdefault(bid, []).append((pack_dir, manifest, output, benchmark_yaml))
    return grouped


def _build_rows(
    packs: list[tuple[Path, dict, dict, Path | None]],
    axes: tuple[dict, ...],
) -> list[BaselineRow]:
    rows: list[BaselineRow] = []
    for pack_dir, manifest, output, _ in packs:
        skill = output.get("skill") or {}
        skill_id = str(skill.get("id") or manifest.get("skill_id") or "?")
        skill_version = str(skill.get("version") or manifest.get("skill_version") or "")
        values = tuple(
            (axis["name"], _scalar(_resolve_path(output, axis["field"])))
            for axis in axes
        )
        rows.append(
            BaselineRow(
                skill_id=skill_id,
                skill_version=skill_version,
                pack_path=pack_dir,
                values=values,
            )
        )
    return rows


def _sort_rows(rows: list[BaselineRow], axes: tuple[dict, ...]) -> list[BaselineRow]:
    """Sort by the first higher_better axis descending; ties by skill_id ascending."""
    sort_axis_idx = next(
        (i for i, a in enumerate(axes) if a.get("direction") == "higher_better"),
        0,
    )
    direction = axes[sort_axis_idx].get("direction", "higher_better")

    def key(row: BaselineRow) -> tuple[int, float, str]:
        v = row.values[sort_axis_idx][1] if sort_axis_idx < len(row.values) else None
        missing_rank = 1 if v is None else 0
        scalar = float("-inf") if v is None else float(v)
        if direction == "lower_better":
            scalar = -scalar
        return (missing_rank, -scalar, row.skill_id)

    return sorted(rows, key=key)


def _format_value(value: float | None, axis: dict) -> str:
    if value is None:
        return "—"
    if axis.get("unit") == "ratio":
        return f"{value:.3f}"
    if axis.get("unit") == "percent":
        return f"{value:.1f}%"
    if axis.get("unit") == "mm":
        return f"{value:.2f}"
    return f"{value:.4g}"


def _render_table(
    benchmark_id: str,
    rows: list[BaselineRow],
    axes: tuple[dict, ...],
) -> str:
    lines: list[str] = []
    lines.append(f"## Benchmark matrix — {benchmark_id}")
    lines.append("")
    if not rows:
        lines.append("_No baselines recorded yet. Run `make run-benchmark` for a participating skill._")
        lines.append("")
        return "\n".join(lines)
    header = ["skill", "version"] + [
        f"{a['name']} ({a.get('direction', '?')})" for a in axes
    ] + ["pack"]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")
    for row in rows:
        cells = [row.skill_id, row.skill_version or "?"]
        for axis, (_, value) in zip(axes, row.values):
            cells.append(_format_value(value, axis))
        cells.append(str(row.pack_path))
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)


@app.command()
def main(
    benchmark_id: str | None = typer.Argument(
        None,
        help="Render only this benchmark's matrix (dataset name). Omit to render all.",
    ),
    search_root: list[Path] = typer.Option(
        None,
        "--root",
        "-r",
        help="One or more roots to scan for benchmark packs. Default: runs/, examples/evidence_packs/, examples/studies/.",
    ),
    benchmarks_dir: Path = typer.Option(
        REPO_PARENT / "benchmarks",
        "--benchmarks-dir",
        help="Directory containing benchmark.yaml manifests (for axes lookup).",
    ),
    out: Path | None = typer.Option(
        None, "--out", help="Optional output markdown file; otherwise print to stdout."
    ),
) -> None:
    """Render cross-skill benchmark matrices from existing benchmark evidence packs."""
    repo_root = REPO_PARENT
    roots = [
        (repo_root / r if not r.is_absolute() else r)
        for r in (search_root or [Path(p) for p in DEFAULT_SEARCH_ROOTS])
        if (repo_root / r if not r.is_absolute() else r).exists()
    ]
    yaml_cache: dict[Path, dict] = {}
    packs = list(_iter_benchmark_packs(roots))
    grouped = _group_by_benchmark(packs, repo_root, yaml_cache)

    if benchmark_id:
        grouped = {k: v for k, v in grouped.items() if k == benchmark_id}

    chunks: list[str] = []
    if not grouped:
        chunks.append("# Benchmark Matrix")
        chunks.append("")
        chunks.append("_No benchmark evidence packs found under the configured search roots._")
        chunks.append("")
    else:
        chunks.append("# Benchmark Matrix")
        chunks.append("")
        chunks.append(
            "Per-task-class measurement of every skill that opted into a benchmark. "
            "Each row is one skill's run on the named benchmark; columns are the axes the "
            "benchmark declares. No single ranking score: compare on the axis you care about. "
            "Engineering verification only."
        )
        chunks.append("")
        for bid in sorted(grouped):
            benchmark_yaml = (benchmarks_dir / f"{bid}.benchmark.yaml").resolve()
            spec = _load_yaml_cached(benchmark_yaml, yaml_cache) if benchmark_yaml.exists() else {}
            axes = _benchmark_axes(spec)
            rows = _sort_rows(_build_rows(grouped[bid], axes), axes)
            chunks.append(_render_table(bid, rows, axes))

    rendered = "\n".join(chunks)
    if out is not None:
        out.write_text(rendered)
        typer.echo(f"matrix written to {out}")
    else:
        typer.echo(rendered)


if __name__ == "__main__":
    app()
