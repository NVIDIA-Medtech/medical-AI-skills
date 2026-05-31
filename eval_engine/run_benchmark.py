#!/usr/bin/env python3
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

"""Benchmark-dataset runner for medagent skills.

Runs a skill once per benchmark case, computes reference segmentation
metrics against ground-truth label maps, and emits a benchmark evidence pack.

This is deliberately separate from eval_engine/run.py so single-fixture skills keep
their existing flow. Benchmarks are YAML manifests under `benchmarks/` with
`format: benchmark_dataset` and optional `cases[]` entries.
"""

from __future__ import annotations

import concurrent.futures
import json
import math
import platform
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import jsonschema
import numpy as np
import typer
import yaml

HARNESS_DIR = Path(__file__).resolve().parent
REPO_PARENT = HARNESS_DIR.parent
if str(REPO_PARENT) not in sys.path:
    sys.path.insert(0, str(REPO_PARENT))

from eval_engine.common import (  # noqa: E402
    FENCE,
    PACK_FORMAT_VERSION,
    REPO_ROOT,
    _env_lock_fingerprint,
    _now_iso,
    _path_size,
    _pip_freeze,
    _public_command,
    _public_path,
    _repo_git_sha,
    _runtime_summary,
    _sha256_path,
)
from eval_engine.evidence import PACK_KIND_BENCHMARK_RUN  # noqa: E402
from eval_engine.gates import _evaluate_sanity_checks, _resolve_path  # noqa: E402
from eval_engine.integrity import _integrity_scan  # noqa: E402
from eval_engine.skill_runtime import _load_skill  # noqa: E402
from eval_engine.trace import write_trace_jsonl  # noqa: E402

app = typer.Typer(add_completion=False)
BENCHMARK_SCHEMA = REPO_PARENT / "spec" / "benchmark_dataset.schema.json"


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    input_path: Path
    ground_truth_path: Path
    labels: tuple[int, ...] | None
    gt_labels: tuple[int, ...] | None = None  # if set, overrides `labels` for the GT mask


def _load_dataset(path: Path) -> dict:
    spec = yaml.safe_load(path.read_text()) or {}
    if spec.get("format") != "benchmark_dataset":
        raise ValueError("benchmark manifest must declare format: benchmark_dataset")
    if BENCHMARK_SCHEMA.exists():
        schema = json.loads(BENCHMARK_SCHEMA.read_text())
        jsonschema.validate(spec, schema)
    return spec


def _resolve_dataset_path(root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    p = Path(value).expanduser()
    if not p.is_absolute():
        p = root / p
    return p.resolve()


def _coerce_labels(raw, who: str) -> tuple[int, ...] | None:
    if raw is None:
        return None
    if isinstance(raw, int):
        return (raw,)
    if isinstance(raw, str):
        return tuple(int(x.strip()) for x in raw.split(",") if x.strip())
    if isinstance(raw, list):
        return tuple(int(x) for x in raw)
    raise ValueError(f"unsupported labels value for {who}: {raw!r}")


def _case_labels(case: dict, spec: dict) -> tuple[int, ...] | None:
    raw = case.get("labels", case.get("label", spec.get("labels", spec.get("metric_labels"))))
    return _coerce_labels(raw, who=f"case {case.get('id', '?')}")


def _case_gt_labels(case: dict, spec: dict) -> tuple[int, ...] | None:
    """Optional override applied to the ground-truth mask only. Useful when the
    skill's prediction uses a different label vocabulary than the GT (e.g.
    VISTA3D emits label_id=3 for spleen while Decathlon GT uses label_id=1)."""
    raw = case.get("gt_labels", spec.get("gt_labels"))
    return _coerce_labels(raw, who=f"case {case.get('id', '?')} gt_labels")


def _resolve_gt_path(root: Path, gt_root: Path | None, case: dict) -> Path:
    explicit = case.get("ground_truth", case.get("gt"))
    if explicit:
        return _resolve_dataset_path(root, str(explicit))
    if not gt_root:
        raise ValueError(
            f"case {case.get('id', '?')} has no ground_truth and dataset has no ground_truth root"
        )
    case_id = str(case.get("id"))
    for suffix in (".nii.gz", ".nii"):
        candidate = gt_root / f"{case_id}{suffix}"
        if candidate.exists():
            return candidate.resolve()
    return (gt_root / f"{case_id}.nii.gz").resolve()


def _cases_from_spec(path: Path, spec: dict, limit: int | None) -> list[BenchmarkCase]:
    root = path.parent.resolve()
    gt_root = _resolve_dataset_path(root, spec.get("ground_truth"))
    raw_cases = spec.get("cases") or []
    cases: list[BenchmarkCase] = []
    for idx, raw in enumerate(raw_cases):
        case_id = str(raw.get("id", f"case_{idx:04d}"))
        raw_input = raw.get("input", raw.get("fixture", raw.get("image")))
        if not raw_input:
            raise ValueError(f"case {case_id} has no input/fixture/image path")
        input_path = _resolve_dataset_path(root, str(raw_input))
        gt_path = _resolve_gt_path(root, gt_root, raw)
        cases.append(
            BenchmarkCase(
                case_id,
                input_path,
                gt_path,
                _case_labels(raw, spec),
                _case_gt_labels(raw, spec),
            )
        )
    if limit is not None:
        cases = cases[:limit]
    declared = spec.get("case_count")
    if raw_cases and declared is not None and int(declared) < len(raw_cases):
        raise ValueError("case_count is smaller than cases[] length")
    return cases


def _load_mask(path: Path, labels: tuple[int, ...] | None) -> tuple[np.ndarray, tuple[float, ...]]:
    import nibabel as nib

    img = nib.load(str(path))
    arr = np.asarray(img.get_fdata())
    if labels:
        mask = np.isin(np.rint(arr).astype(np.int64), labels)
    else:
        mask = arr > 0
    spacing = tuple(float(x) for x in img.header.get_zooms()[: mask.ndim])
    if len(spacing) != mask.ndim:
        spacing = tuple(1.0 for _ in range(mask.ndim))
    return mask.astype(bool), spacing


def _dice_iou(pred: np.ndarray, gt: np.ndarray) -> tuple[float, float]:
    pred_sum = int(pred.sum())
    gt_sum = int(gt.sum())
    intersection = int(np.logical_and(pred, gt).sum())
    union = int(np.logical_or(pred, gt).sum())
    dice = 1.0 if pred_sum + gt_sum == 0 else (2.0 * intersection) / (pred_sum + gt_sum)
    iou = 1.0 if union == 0 else intersection / union
    return float(dice), float(iou)


def _surface(mask: np.ndarray) -> np.ndarray:
    if not mask.any():
        return np.zeros_like(mask, dtype=bool)
    try:
        from scipy import ndimage as ndi

        structure = ndi.generate_binary_structure(mask.ndim, 1)
        eroded = ndi.binary_erosion(mask, structure=structure, border_value=0)
        return mask & ~eroded
    except Exception:
        # Fallback: use all foreground voxels as the surface. Exact enough for
        # tiny synthetic tests; large medical volumes should have scipy.
        return mask


def _nearest_distances(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    try:
        from scipy.spatial import cKDTree

        tree = cKDTree(b)
        distances, _ = tree.query(a, k=1)
        return np.asarray(distances, dtype=float)
    except Exception:
        if len(a) * len(b) > 25_000_000:
            raise RuntimeError("scipy is required for Hausdorff distance on large masks")
        mins: list[np.ndarray] = []
        chunk = 1024
        for start in range(0, len(a), chunk):
            aa = a[start : start + chunk]
            dist2 = ((aa[:, None, :] - b[None, :, :]) ** 2).sum(axis=2)
            mins.append(np.sqrt(dist2.min(axis=1)))
        return np.concatenate(mins) if mins else np.asarray([], dtype=float)


def _hausdorff(pred: np.ndarray, gt: np.ndarray, spacing: tuple[float, ...]) -> float | None:
    if not pred.any() and not gt.any():
        return 0.0
    if not pred.any() or not gt.any():
        return None

    pred_coords = np.argwhere(_surface(pred)).astype(float)
    gt_coords = np.argwhere(_surface(gt)).astype(float)
    scale = np.asarray(spacing, dtype=float)
    pred_coords *= scale
    gt_coords *= scale
    d_pg = _nearest_distances(pred_coords, gt_coords)
    d_gp = _nearest_distances(gt_coords, pred_coords)
    if len(d_pg) == 0 or len(d_gp) == 0:
        return None
    return float(max(float(d_pg.max()), float(d_gp.max())))


def _percentile(values: list[float], q: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=float), q))


def _wilson_score_pct(successes: int, n: int, z: float = 1.959963984540054) -> dict:
    """95% Wilson score interval for a binomial proportion, in percent.

    The Wilson interval is the standard small-sample-friendly CI for pass/fail
    coverage. z=1.96 (95%) is the field default per CheXpert conventions and
    nnU-Net Revisited. Returns lower / upper as percentages (0–100). When n=0
    the interval is undefined; both bounds are None.
    """
    if n <= 0:
        return {"level": 0.95, "method": "wilson", "lower_pct": None, "upper_pct": None}
    p = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denom
    margin = z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * n)) / n) / denom
    lower = max(0.0, center - margin) * 100.0
    upper = min(1.0, center + margin) * 100.0
    return {
        "level": 0.95,
        "method": "wilson",
        "lower_pct": round(lower, 6),
        "upper_pct": round(upper, 6),
    }


def _summary(values: list[float | None]) -> dict:
    vals = [float(v) for v in values if isinstance(v, (int, float)) and math.isfinite(float(v))]
    if not vals:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "p10": None,
            "min": None,
            "max": None,
        }
    return {
        "count": len(vals),
        "mean": float(np.mean(vals)),
        "median": _percentile(vals, 50),
        "p10": _percentile(vals, 10),
        "min": float(np.min(vals)),
        "max": float(np.max(vals)),
    }


def _prediction_path(payload: dict, spec: dict) -> Path | None:
    prediction = spec.get("prediction") or {}
    dotted = prediction.get("path") or spec.get("prediction_path") or "output.path"
    value = _resolve_path(payload, dotted)
    if not value:
        return None
    p = Path(str(value)).expanduser()
    return p.resolve() if p.is_absolute() else (REPO_ROOT / p).resolve()


def _run_case(
    case: BenchmarkCase,
    script: Path,
    schema: dict | None,
    spec: dict,
) -> dict:
    started_at = _now_iso()
    t0 = time.perf_counter()

    record = {
        "case_id": case.case_id,
        "input_path": _public_path(case.input_path),
        "ground_truth_path": _public_path(case.ground_truth_path),
        "labels": list(case.labels) if case.labels else None,
        "status": "failed",
        "skill_exit_code": None,
        "elapsed_seconds": None,
        "prediction_path": None,
        "metrics": {"dice": None, "iou": None, "hd": None},
        "error": None,
    }

    try:
        if not case.input_path.exists():
            raise FileNotFoundError(f"input missing: {_public_path(case.input_path)}")
        if not case.ground_truth_path.exists():
            raise FileNotFoundError(f"ground truth missing: {_public_path(case.ground_truth_path)}")

        proc = subprocess.run(
            [sys.executable, str(script), str(case.input_path)],
            capture_output=True,
            text=True,
        )
        record["skill_exit_code"] = proc.returncode
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr[:500] or f"skill exited {proc.returncode}")
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"skill stdout was not JSON: {e}") from e

        if schema is not None:
            jsonschema.validate(payload, schema)

        pred_path = _prediction_path(payload, spec)
        if pred_path is None:
            raise RuntimeError("could not resolve prediction path from skill output")
        if not pred_path.exists():
            raise FileNotFoundError(f"prediction missing: {_public_path(pred_path)}")
        record["prediction_path"] = _public_path(pred_path)

        pred_mask, pred_spacing = _load_mask(pred_path, case.labels)
        gt_mask, gt_spacing = _load_mask(case.ground_truth_path, case.gt_labels or case.labels)
        if pred_mask.shape != gt_mask.shape:
            raise ValueError(
                f"shape mismatch: prediction {pred_mask.shape}, ground truth {gt_mask.shape}"
            )

        dice, iou = _dice_iou(pred_mask, gt_mask)
        hd = _hausdorff(pred_mask, gt_mask, pred_spacing or gt_spacing)
        record["metrics"] = {"dice": dice, "iou": iou, "hd": hd}
        record["status"] = "passed" if hd is not None else "metric_failed"
        if hd is None:
            record["error"] = "Hausdorff distance undefined because one mask is empty"
    except Exception as e:
        record["error"] = str(e)
    finally:
        record["elapsed_seconds"] = round(time.perf_counter() - t0, 6)
        record["started_at"] = started_at
        record["finished_at"] = _now_iso()

    return record


def _benchmark_checks(manifest: dict, spec: dict) -> list:
    validation = manifest.get("validation", {}) or {}
    return (
        spec.get("sanity_checks")
        or validation.get("benchmark_sanity_checks")
        or (validation.get("benchmark", {}) or {}).get("sanity_checks")
        or []
    )


def _write_replay(
    out: Path, skill_dir: Path, benchmark: Path, jobs: int, limit: int | None
) -> None:
    limit_arg = "" if limit is None else " --limit " + shlex.quote(str(limit))
    text = (
        "#!/usr/bin/env bash\n"
        "# Auto-generated benchmark replay. Best-effort; case data must still exist locally.\n"
        "set -euo pipefail\n"
        'SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"\n'
        'REPO_ROOT="$SCRIPT_DIR"\n'
        'while [ ! -e "$REPO_ROOT/Makefile" ] && [ "$REPO_ROOT" != "/" ]; do\n'
        '  REPO_ROOT="$(dirname "$REPO_ROOT")"\n'
        "done\n"
        '[ -e "$REPO_ROOT/Makefile" ] || { echo "could not find repo root"; exit 1; }\n'
        'cd "$REPO_ROOT"\n'
        + "python3 "
        + shlex.quote(_public_path(Path(__file__)))
        + " "
        + shlex.quote(_public_path(skill_dir))
        + " --benchmark "
        + shlex.quote(_public_path(benchmark))
        + " --out "
        + shlex.quote(_public_path(out))
        + " --jobs "
        + shlex.quote(str(jobs))
        + limit_arg
        + "\n"
    )
    replay = out / "replay.sh"
    replay.write_text(text)
    replay.chmod(0o755)


@app.command()
def main(
    skill_dir: Path = typer.Argument(..., exists=True, file_okay=False),
    benchmark: Path = typer.Option(
        ..., "--benchmark", "--fixture", help="benchmark_dataset YAML manifest"
    ),
    out: Path = typer.Option(..., "--out", help="benchmark evidence pack output directory"),
    jobs: int = typer.Option(1, "--jobs", min=1, help="parallel case subprocesses"),
    limit: int | None = typer.Option(None, "--limit", min=1, help="optional first-N case limit"),
) -> None:
    skill_dir = skill_dir.resolve()
    benchmark = benchmark.resolve()
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    skill = _load_skill(skill_dir)
    script = skill["script"]
    schema_path = skill["schema_path"]
    manifest = skill["manifest"]

    run_id = uuid4().hex[:12]
    started_at = _now_iso()
    t0 = time.perf_counter()

    preflight = [
        {
            "name": "benchmark_manifest_exists",
            "path": _public_path(benchmark),
            "status": "passed" if benchmark.exists() else "failed",
        },
        {
            "name": "benchmark_manifest_is_file",
            "path": _public_path(benchmark),
            "status": "passed" if benchmark.is_file() else "failed",
        },
    ]
    spec: dict = {}
    cases: list[BenchmarkCase] = []
    preflight_error = None
    if all(c["status"] == "passed" for c in preflight):
        try:
            spec = _load_dataset(benchmark)
            cases = _cases_from_spec(benchmark, spec, limit)
            preflight.append(
                {
                    "name": "benchmark_manifest_format",
                    "status": "passed",
                    "format": spec.get("format"),
                }
            )
            preflight.append(
                {
                    "name": "case_count",
                    "status": "passed" if cases else "failed",
                    "count": len(cases),
                }
            )
        except Exception as e:
            preflight_error = str(e)
            preflight.append(
                {
                    "name": "benchmark_manifest_parse",
                    "status": "failed",
                    "error": preflight_error,
                }
            )
    preflight_status = "failed" if any(c.get("status") == "failed" for c in preflight) else "passed"

    records: list[dict] = []
    trace_records: list[dict] = [
        {"ts": started_at, "kind": "benchmark_start", "cases": len(cases), "jobs": jobs}
    ]
    if preflight_status == "passed":
        schema = (
            json.loads(schema_path.read_text()) if schema_path and schema_path.exists() else None
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
            futures = [pool.submit(_run_case, case, script, schema, spec) for case in cases]
            for fut in concurrent.futures.as_completed(futures):
                records.append(fut.result())
        records.sort(key=lambda r: r["case_id"])

    dataset_run = out / "dataset_run.jsonl"
    dataset_run.write_text(
        "\n".join(json.dumps(r, sort_keys=True) for r in records) + ("\n" if records else "")
    )

    fail_count = sum(1 for r in records if r.get("status") != "passed")
    pass_count = len(records) - fail_count
    coverage_pct = (100.0 * pass_count / len(cases)) if cases else 0.0
    coverage_ci = _wilson_score_pct(pass_count, len(cases))
    output_payload = {
        "skill": {
            "id": manifest.get("id"),
            "version": manifest.get("version"),
            "entrypoint": str(script.relative_to(skill_dir)),
        },
        "benchmark": {
            "manifest_path": _public_path(benchmark),
            "source": spec.get("source"),
            "dataset": spec.get("dataset", spec.get("name")),
            "license": spec.get("license"),
            "inclusion": spec.get("inclusion", {}),
            "case_count_declared": spec.get("case_count"),
            "case_count_run": len(cases),
        },
        "output": {
            "case_count": len(records),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "coverage_pct": round(coverage_pct, 6),
            "coverage_pct_ci_95": coverage_ci,
            "dice": _summary([r.get("metrics", {}).get("dice") for r in records]),
            "iou": _summary([r.get("metrics", {}).get("iou") for r in records]),
            "hd": _summary([r.get("metrics", {}).get("hd") for r in records]),
        },
    }
    (out / "output.json").write_text(json.dumps(output_payload, indent=2, allow_nan=False))

    sanity_checks = _benchmark_checks(manifest, spec)
    sanity_results = _evaluate_sanity_checks(output_payload, sanity_checks) if sanity_checks else []
    sanity_status = (
        "passed"
        if sanity_results and all(r["ok"] for r in sanity_results)
        else ("failed" if any(not r["ok"] for r in sanity_results) else "skipped")
    )

    integrity = _integrity_scan(skill_dir)
    integrity_status = integrity["status"]
    (out / "integrity_check.json").write_text(json.dumps(integrity, indent=2))

    elapsed = time.perf_counter() - t0
    finished_at = _now_iso()
    trace_records.append(
        {
            "ts": finished_at,
            "kind": "benchmark_end",
            "elapsed_s": elapsed,
            "pass_count": pass_count,
            "fail_count": fail_count,
        }
    )
    write_trace_jsonl(out / "agent_run_trace.jsonl", trace_records)

    pip_freeze_text = _pip_freeze()
    (out / "environment.lock").write_text(pip_freeze_text)
    env_fingerprint = _env_lock_fingerprint(pip_freeze_text)

    (out / "runtime_profile.json").write_text(
        json.dumps(
            {
                "started_at": started_at,
                "finished_at": finished_at,
                "elapsed_seconds": elapsed,
                "case_count": len(cases),
                "jobs": jobs,
                "environment": _runtime_summary(),
            },
            indent=2,
        )
    )
    (out / "cost_profile.json").write_text(
        json.dumps(
            {
                "measured": {},
                "self_reported": {},
                "evaluation": {
                    "status": "skipped",
                    "results": [],
                    "reason": "benchmark runner does not yet capture per-run cost; per-case timing is in dataset_run.jsonl",
                },
            },
            indent=2,
        )
    )

    bundle_manifest = {
        "pack_format_version": PACK_FORMAT_VERSION,
        "pack_kind": PACK_KIND_BENCHMARK_RUN,
        "run_id": run_id,
        "skill_id": manifest.get("id"),
        "skill_version": manifest.get("version"),
        "skill_dir": _public_path(skill_dir),
        "repo_git_sha": _repo_git_sha(),
        "benchmark_manifest": {
            "path": _public_path(benchmark),
            "sha256": _sha256_path(benchmark),
            "size_bytes": _path_size(benchmark),
            "format": spec.get("format", "benchmark_dataset") if spec else None,
        },
        "environment": {
            "fingerprint": env_fingerprint,
            "pip_freeze_lines": pip_freeze_text.count("\n"),
            "pip_freeze_path": "environment.lock",
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
        "case_count": len(cases),
        "command": _public_command(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                str(skill_dir),
                "--benchmark",
                str(benchmark),
                "--out",
                str(out),
            ]
        ),
        "eval_engine_script": _public_path(Path(__file__).resolve()),
    }
    (out / "manifest.json").write_text(json.dumps(bundle_manifest, indent=2))
    _write_replay(out, skill_dir, benchmark, jobs, limit)

    if preflight_status == "failed":
        overall = "preflight_failed"
    elif fail_count > 0:
        overall = "failed (case execution/metrics)"
    elif sanity_status == "failed" or integrity_status == "flagged":
        overall = "failed (sanity/integrity gate)"
    else:
        overall = "passed"

    (out / "validation_summary.json").write_text(
        json.dumps(
            {
                "preflight_status": preflight_status,
                "preflight": preflight,
                "sanity_status": sanity_status,
                "sanity_results": sanity_results,
                "overall_status": overall,
                "integrity_status": integrity_status,
                "integrity_n_findings": integrity["n_findings"],
                "case_count": len(cases),
                "pass_count": pass_count,
                "fail_count": fail_count,
                "coverage_pct": round(coverage_pct, 6),
                "coverage_pct_ci_95": coverage_ci,
                "errors": [preflight_error] if preflight_error else [],
            },
            indent=2,
        )
    )

    lines = [
        "# Benchmark Run Record",
        "",
        "- run id: " + run_id,
        "- skill: " + str(manifest.get("id", "?")) + " v" + str(manifest.get("version", "?")),
        "- benchmark manifest: " + _public_path(benchmark),
        "- started: " + started_at,
        "- finished: " + finished_at,
        "- elapsed: " + str(round(elapsed, 3)) + "s",
        "- cases: " + str(pass_count) + " / " + str(len(cases)) + " passed",
        "- overall: " + overall,
        "",
        "## Aggregate Output",
        FENCE + "json",
        json.dumps(output_payload["output"], indent=2)[:1800],
        FENCE,
        "",
        "## Files",
        "- dataset_run.jsonl: one line per case with metrics and paths",
        "- output.json: aggregate benchmark summary",
        "",
        "## Caveats",
        "- Metrics are engineering-time checks, not clinical performance claims.",
        "- Benchmark replay requires the same local case data and ground-truth paths.",
    ]
    (out / "workflow_run_record.md").write_text("\n".join(lines))

    typer.echo("benchmark pack: " + str(out))
    typer.echo("  preflight: " + preflight_status)
    typer.echo("  cases: " + str(pass_count) + "/" + str(len(cases)) + " passed")
    typer.echo("  sanity: " + sanity_status)
    typer.echo(
        "  integrity: " + integrity_status + " (" + str(integrity["n_findings"]) + " findings)"
    )
    typer.echo("  overall: " + overall)
    if overall != "passed":
        raise typer.Exit(2 if preflight_status == "failed" else 1)


if __name__ == "__main__":
    app()
