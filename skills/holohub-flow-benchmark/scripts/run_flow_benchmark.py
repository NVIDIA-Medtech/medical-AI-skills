#!/usr/bin/env python3
"""Run HoloHub's official Holoscan flow benchmark for one HoloHub app.

The wrapper intentionally delegates instrumentation to HoloHub's
`benchmarks/holoscan_flow_benchmarking` tools. By default it launches the
HoloHub benchmarking container, runs the benchmark build and `benchmark.py`
inside that container, parses the host-visible generated data-flow tracking
logs, inventories artifacts, optionally checks an app-specific YAML contract,
and prints one JSON payload for the eval_engine.

It does not reimplement HoloHub apps, postprocessors, or the Holoscan
data-flow tracker.
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import shlex
import subprocess
import sys
import time
from pathlib import Path
from statistics import mean, median
from typing import Any

import yaml

_SCRIPT_DIR = Path(__file__).resolve().parent
_SKILLS_DIR = _SCRIPT_DIR.parent.parent
if str(_SKILLS_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILLS_DIR))
from _shared.wrapper_utils import (  # noqa: E402
    collect_group as _collect,
    docker_image_id as _docker_image_id,
    emit as _emit,
    fail_with as _fail,
    file_record as _file_record,
    file_sha256_safe,
    git_commit as _git_commit,
    sha256_file as _sha256_file,
    tail as _tail,
)

APP_DEFAULT = "endoscopy_tool_tracking"
SKILL_ID = "holohub_flow_benchmark"

SCHEDULERS = ("greedy", "multithread", "eventbased")
LANGUAGES = ("cpp", "python")
RUN_MODES = ("container", "local")


def _bool_env(name: str, default: bool) -> bool:
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return default
    return value in ("1", "true", "yes", "on")


def _int_env(name: str, default: int, minimum: int = 1) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(minimum, int(raw))
    except ValueError:
        return default


def _float_env(name: str, default: float, minimum: float = 0.0) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(minimum, float(raw))
    except ValueError:
        return default


def _csv_env(name: str, default: list[str], allowed: tuple[str, ...] | None = None) -> list[str]:
    raw = os.environ.get(name, "").strip()
    values = [x.strip() for x in raw.split(",") if x.strip()] if raw else default
    if allowed is None:
        return values
    return [x for x in values if x in allowed] or default


def _enum_env(name: str, default: str, allowed: tuple[str, ...]) -> str:
    value = os.environ.get(name, "").strip() or default
    return value if value in allowed else default


def _run(cmd: list[str], cwd: Path, timeout_s: float, env: dict[str, str]) -> tuple[int, str, str, float]:
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return proc.returncode, proc.stdout, proc.stderr, time.monotonic() - t0
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
        return int("124"), stdout, stderr + f"\n[TIMEOUT after {timeout_s}s]", time.monotonic() - t0
    except FileNotFoundError as e:
        return int("127"), "", f"command not found: {e}", time.monotonic() - t0


def _shell_join(cmd: list[str]) -> str:
    return " ".join(shlex.quote(str(part)) for part in cmd)


def _inventory(output_dir: Path) -> dict[str, Any]:
    if not output_dir.exists():
        empty = {"count": 0, "total_bytes": 0, "files": []}
        return {"logger": empty, "gpu_utilization": empty, "other": empty}

    logger_files: list[Path] = []
    gpu_files: list[Path] = []
    other_files: list[Path] = []
    for p in sorted(output_dir.rglob("*")):
        if not p.is_file():
            continue
        name = p.name
        if name.startswith("logger_") and name.endswith(".log"):
            logger_files.append(p)
        elif name.startswith("gpu_utilization_") and name.endswith(".csv"):
            gpu_files.append(p)
        else:
            other_files.append(p)

    return {
        "logger": _collect(logger_files, output_dir),
        "gpu_utilization": _collect(gpu_files, output_dir),
        "other": _collect(other_files, output_dir),
    }


def _optional_file_sha256(root: Path, rel_path: str | None) -> str:
    if not rel_path:
        return ""
    return file_sha256_safe(root / rel_path)


_LOG_LINE = re.compile(r"\(([^()]*)\)")


def _parse_flow_line(line: str) -> tuple[str, float] | None:
    if not line.startswith("("):
        return None
    pieces = _LOG_LINE.findall(line)
    if not pieces:
        return None
    rows: list[tuple[str, int, int]] = []
    for piece in pieces:
        cols = [x.strip() for x in piece.split(",")]
        if len(cols) < int("3"):
            return None
        try:
            rows.append((cols[0], int(cols[1]), int(cols[2])))
        except ValueError:
            return None
    latency_ms = (rows[-1][2] - rows[0][1]) / float("1000.0")
    return " -> ".join(row[0] for row in rows), latency_ms


def _trim(samples: list[float], skip_begin: int, discard_last: int) -> list[float]:
    if len(samples) <= skip_begin + discard_last:
        return []
    end = None if discard_last == 0 else -discard_last
    return samples[skip_begin:end]


def _percentile(samples: list[float], pct: float) -> float:
    ordered = sorted(samples)
    if pct >= int("100"):
        return ordered[-1]
    idx = min(len(ordered) - 1, max(0, int(len(ordered) * pct / float("100.0"))))
    return ordered[idx]


def _metric(samples: list[float]) -> dict[str, Any]:
    if not samples:
        return {
            "sample_count": 0,
            "min_ms": None,
            "avg_ms": None,
            "median_ms": None,
            "max_ms": None,
            "p95_ms": None,
            "p99_ms": None,
            "tail_95_100_ms": None,
            "flatness_10_90_ms": None,
        }
    p95 = _percentile(samples, int("95"))
    p99 = _percentile(samples, int("99"))
    p100 = _percentile(samples, int("100"))
    p10 = _percentile(samples, int("10"))
    p90 = _percentile(samples, int("90"))
    return {
        "sample_count": len(samples),
        "min_ms": round(min(samples), int("4")),
        "avg_ms": round(mean(samples), int("4")),
        "median_ms": round(median(samples), int("4")),
        "max_ms": round(max(samples), int("4")),
        "p95_ms": round(p95, int("4")),
        "p99_ms": round(p99, int("4")),
        "tail_95_100_ms": round(p100 - p95, int("4")),
        "flatness_10_90_ms": round(p90 - p10, int("4")),
    }


def _parse_logger_file(path: Path, skip_begin: int, discard_last: int) -> dict[str, list[float]]:
    path_latencies: dict[str, list[float]] = {}
    try:
        for line in path.read_text(errors="replace").splitlines():
            parsed = _parse_flow_line(line.strip())
            if parsed is None:
                continue
            flow_path, latency_ms = parsed
            if math.isfinite(latency_ms) and latency_ms >= 0:
                path_latencies.setdefault(flow_path, []).append(latency_ms)
    except OSError:
        return {}
    return {
        flow_path: _trim(samples, skip_begin, discard_last)
        for flow_path, samples in path_latencies.items()
    }


def _scheduler_from_logger_name(path: Path) -> str:
    # logger_<scheduler>_<run>_<instance>.log
    parts = path.name.split("_")
    if len(parts) >= int("4") and parts[0] == "logger":
        return parts[1]
    return "unknown"


def _analyze_logs(output_dir: Path, skip_begin: int, discard_last: int) -> dict[str, Any]:
    grouped: dict[str, dict[str, list[float]]] = {}
    for log_path in sorted(output_dir.glob("logger_*.log")):
        scheduler = _scheduler_from_logger_name(log_path)
        parsed = _parse_logger_file(log_path, skip_begin, discard_last)
        bucket = grouped.setdefault(scheduler, {})
        for flow_path, samples in parsed.items():
            bucket.setdefault(flow_path, []).extend(samples)

    scheduler_metrics: dict[str, Any] = {}
    first_path: dict[str, Any] | None = None
    total_samples = 0
    paths_observed = 0
    for scheduler, by_path in sorted(grouped.items()):
        paths: dict[str, Any] = {}
        for flow_path, samples in sorted(by_path.items()):
            metrics = _metric(samples)
            paths[flow_path] = metrics
            total_samples += int(metrics["sample_count"])
            if int(metrics["sample_count"]) > 0:
                paths_observed += 1
                if first_path is None:
                    first_path = {"scheduler": scheduler, "path": flow_path, **metrics}
        scheduler_metrics[scheduler] = {
            "path_count": sum(1 for m in paths.values() if int(m["sample_count"]) > 0),
            "paths": paths,
        }

    return {
        "skip_begin_messages": skip_begin,
        "discard_last_messages": discard_last,
        "schedulers": scheduler_metrics,
        "paths_observed": paths_observed,
        "total_latency_samples": total_samples,
        "first_path": first_path or {
            "scheduler": "",
            "path": "",
            **_metric([]),
        },
    }


def _analyze_gpu(output_dir: Path) -> dict[str, Any]:
    values: list[float] = []
    for path in sorted(output_dir.glob("gpu_utilization_*.csv")):
        try:
            raw = path.read_text().strip().strip(",")
        except OSError:
            continue
        for piece in raw.split(","):
            piece = piece.strip()
            if not piece:
                continue
            try:
                value = float(piece)
            except ValueError:
                continue
            if math.isfinite(value):
                values.append(value)
    if not values:
        return {"sample_count": 0, "avg_percent": None, "max_percent": None}
    return {
        "sample_count": len(values),
        "avg_percent": round(mean(values), int("4")),
        "max_percent": round(max(values), int("4")),
    }


def _operator_sequence_present(path: str, expected: tuple[str, ...]) -> bool:
    operators = [piece.strip() for piece in path.split(" -> ") if piece.strip()]
    if len(operators) < len(expected):
        return False
    idx = 0
    for operator in operators:
        if operator == expected[idx]:
            idx += 1
            if idx == len(expected):
                return True
    return False


def _exact_operator_path_present(path: str, expected: tuple[str, ...]) -> bool:
    operators = tuple(piece.strip() for piece in path.split(" -> ") if piece.strip())
    return operators == expected


def _observed_flow_paths(analysis: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    paths: list[tuple[str, str, dict[str, Any]]] = []
    schedulers = analysis.get("schedulers", {})
    if not isinstance(schedulers, dict):
        return paths
    for scheduler, scheduler_data in schedulers.items():
        if not isinstance(scheduler_data, dict):
            continue
        by_path = scheduler_data.get("paths", {})
        if not isinstance(by_path, dict):
            continue
        for flow_path, metrics in by_path.items():
            if isinstance(metrics, dict) and int(metrics.get("sample_count") or 0) > 0:
                paths.append((str(scheduler), str(flow_path), metrics))
    return paths


def _benchmark_log_status(output_dir: Path, app: str) -> dict[str, Any]:
    path = output_dir / "benchmark.log"
    try:
        text = path.read_text(errors="replace")
    except OSError:
        text = ""
    return {
        "present": bool(text),
        "evaluation_completed": "Evaluation completed" in text,
        "missing_log_errors": (
            "Log files are missing" in text or "Some log files are missing" in text
        ),
        "mentions_app": app in text if app else False,
    }


def _load_contract(path_text: str, holohub_root: Path) -> dict[str, Any]:
    if not path_text:
        return {"present": False, "path": "", "error": ""}
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except Exception as exc:
        return {"present": True, "path": str(path), "error": str(exc)}
    if not isinstance(data, dict):
        return {"present": True, "path": str(path), "error": "contract root must be a mapping"}
    data = dict(data)
    data["present"] = True
    data["path"] = str(path)
    data["error"] = ""
    data["holohub_root"] = str(holohub_root)
    return data


def _operators(flow_path: str) -> list[str]:
    return [piece.strip() for piece in flow_path.split(" -> ") if piece.strip()]


def _sequence_present(flow_path: str, expected: list[str]) -> bool:
    if not expected:
        return True
    observed = _operators(flow_path)
    if len(observed) < len(expected):
        return False
    for idx in range(0, len(observed) - len(expected) + 1):
        if observed[idx : idx + len(expected)] == expected:
            return True
    return False


def _direct_path_present(flow_path: str, expected: list[str]) -> bool:
    return _operators(flow_path) == expected


def _scheduler_path_metrics(
    flow_paths: list[tuple[str, str, dict[str, Any]]],
    requested_schedulers: list[str],
    primary_sequence: list[str],
    direct_paths: list[list[str]],
) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for scheduler in requested_schedulers:
        scheduler_paths = [
            (flow_path, metrics)
            for observed_scheduler, flow_path, metrics in flow_paths
            if observed_scheduler == scheduler
        ]
        primary = next(
            (
                (flow_path, metrics)
                for flow_path, metrics in scheduler_paths
                if _sequence_present(flow_path, primary_sequence)
            ),
            None,
        )
        direct_status = {
            " -> ".join(path): any(
                _direct_path_present(flow_path, path) for flow_path, _ in scheduler_paths
            )
            for path in direct_paths
        }
        metrics = primary[1] if primary else _metric([])
        results[scheduler] = {
            "path_count": len(scheduler_paths),
            "primary_path_present": primary is not None,
            "direct_paths_present": direct_status,
            "all_direct_paths_present": all(direct_status.values()) if direct_status else True,
            "primary_path": primary[0] if primary else "",
            "sample_count": int(metrics.get("sample_count") or 0),
            "avg_ms": metrics.get("avg_ms"),
            "median_ms": metrics.get("median_ms"),
            "p95_ms": metrics.get("p95_ms"),
            "p99_ms": metrics.get("p99_ms"),
            "tail_95_100_ms": metrics.get("tail_95_100_ms"),
            "flatness_10_90_ms": metrics.get("flatness_10_90_ms"),
            "min_ms": metrics.get("min_ms"),
            "max_ms": metrics.get("max_ms"),
        }
    return results


def _path_record(root: Path, rel_path: str, expected_sha: str | None = None) -> dict[str, Any]:
    path = root / rel_path
    exists = path.is_file()
    size = path.stat().st_size if exists else 0
    sha = _sha256_file(path) if exists and size > 0 else ""
    return {
        "path": rel_path,
        "exists": exists,
        "bytes": size,
        "sha256": sha,
        "expected_sha256": expected_sha,
        "sha256_matches": bool(not expected_sha or sha == expected_sha),
    }


def _budget_met(value: Any, maximum: Any) -> bool:
    if maximum is None:
        return True
    return isinstance(value, (int, float)) and value <= float(maximum)


def _contract_checks(
    *,
    contract: dict[str, Any],
    app: str,
    holohub_root: Path,
    analysis: dict[str, Any],
    schedulers: list[str],
    smoke_mode: bool = False,
) -> dict[str, Any]:
    flow_paths = _observed_flow_paths(analysis)
    observed_operators = sorted(
        {
            operator
            for _, flow_path, _ in flow_paths
            for operator in _operators(flow_path)
        }
    )
    base = {
        "present": bool(contract.get("present")),
        "path": str(contract.get("path") or ""),
        "error": str(contract.get("error") or ""),
        "app": str(contract.get("app") or ""),
        "notes": str(contract.get("notes") or ""),
        "observed_operators": observed_operators,
        "scheduler_results": {},
        "required_data_files": [],
        "latency_budget_results": {},
        "assertions": {
            "contract_loaded": not bool(contract.get("error")),
            "all_required_assertions_passed": True,
        },
    }
    if not contract.get("present"):
        base["assertions"]["measure_mode_no_contract"] = True
        return base
    if contract.get("error"):
        base["assertions"]["all_required_assertions_passed"] = False
        return base

    flow_assertions = contract.get("flow_assertions") or {}
    if not isinstance(flow_assertions, dict):
        flow_assertions = {}
    primary_sequence = [str(x) for x in flow_assertions.get("primary_sequence") or []]
    direct_paths = [
        [str(piece) for piece in path]
        for path in (flow_assertions.get("direct_paths") or [])
        if isinstance(path, list)
    ]
    scheduler_results = _scheduler_path_metrics(
        flow_paths, schedulers, primary_sequence, direct_paths
    )

    required_files = []
    for item in contract.get("required_data_files") or []:
        if isinstance(item, dict) and item.get("path"):
            required_files.append(
                _path_record(holohub_root, str(item["path"]), item.get("sha256"))
            )

    source_file = str(contract.get("source_file") or "")
    model_file = str(contract.get("model_file") or "")
    model_sha = _optional_file_sha256(holohub_root, model_file)
    budgets = contract.get("latency_budgets") or {}
    if not isinstance(budgets, dict):
        budgets = {}

    budget_results: dict[str, Any] = {}
    for scheduler, result in scheduler_results.items():
        budget_results[scheduler] = {
            "p50_ms_max": _budget_met(result.get("median_ms"), budgets.get("p50_ms_max")),
            "p95_ms_max": _budget_met(result.get("p95_ms"), budgets.get("p95_ms_max")),
            "p99_ms_max": _budget_met(result.get("p99_ms"), budgets.get("p99_ms_max")),
            "tail_95_100_ms_max": _budget_met(
                result.get("tail_95_100_ms"), budgets.get("tail_95_100_ms_max")
            ),
            "flatness_10_90_ms_max": _budget_met(
                result.get("flatness_10_90_ms"), budgets.get("flatness_10_90_ms_max")
            ),
            "min_sample_count": (
                True
                if budgets.get("min_sample_count") is None
                else result.get("sample_count", 0) >= int(budgets["min_sample_count"])
            ),
        }

    assertions = {
        "contract_loaded": True,
        "app_matches_contract": (not contract.get("app")) or str(contract.get("app")) == app,
        "source_file_present": (not source_file) or (holohub_root / source_file).is_file(),
        "required_data_files_present": all(
            bool(record["exists"] and record["bytes"] > 0) for record in required_files
        )
        if required_files
        else True,
        "required_data_files_hash_match": all(
            bool(record["sha256_matches"]) for record in required_files
        )
        if required_files
        else True,
        "scheduler_coverage_complete": set(schedulers).issubset(
            {scheduler for scheduler, _, _ in flow_paths}
        ),
        "primary_sequence_present": all(
            result["primary_path_present"] for result in scheduler_results.values()
        )
        if primary_sequence and scheduler_results
        else bool(not primary_sequence),
        "direct_paths_present": all(
            result["all_direct_paths_present"] for result in scheduler_results.values()
        )
        if direct_paths and scheduler_results
        else bool(not direct_paths),
        "latency_budgets_met": True if smoke_mode else (
            all(all(statuses.values()) for statuses in budget_results.values())
            if budget_results
            else True
        ),
        "smoke_mode_skipped_budgets": bool(smoke_mode),
    }
    assertions["all_required_assertions_passed"] = all(
        v for k, v in assertions.items() if k != "smoke_mode_skipped_budgets"
    )

    target_hardware_raw = contract.get("target_hardware") or []
    target_hardware = [
        item for item in target_hardware_raw if isinstance(item, dict)
    ] if isinstance(target_hardware_raw, list) else []
    calibration_hardware = contract.get("calibration_hardware")
    if not isinstance(calibration_hardware, str):
        calibration_hardware = None

    base.update(
        {
            "source_file": source_file,
            "source_file_present": assertions["source_file_present"],
            "model_file": model_file,
            "model_sha256": model_sha,
            "target_hardware": target_hardware,
            "calibration_hardware": calibration_hardware,
            "flow_assertions": {
                "primary_sequence": primary_sequence,
                "direct_paths": direct_paths,
            },
            "required_data_files": required_files,
            "latency_budgets": budgets,
            "latency_budget_results": budget_results,
            "scheduler_results": scheduler_results,
            "assertions": assertions,
            "smoke_mode": bool(smoke_mode),
        }
    )
    return base


def _domain_checks(
    *,
    app: str,
    output_dir: Path,
    inventory: dict[str, Any],
    analysis: dict[str, Any],
    schedulers: list[str],
    runs: int,
    instances: int,
    messages: int,
    skip_begin: int,
    discard_last: int,
) -> dict[str, Any]:
    flow_paths = _observed_flow_paths(analysis)
    observed_schedulers = sorted({scheduler for scheduler, _, _ in flow_paths})
    sample_counts = [int(metrics.get("sample_count") or 0) for _, _, metrics in flow_paths]
    expected_logger_count = len(schedulers) * runs * instances
    expected_effective_samples = max(0, messages - skip_begin - discard_last)
    return {
        "app": app,
        "expected_logger_count": expected_logger_count,
        "observed_logger_count": int(inventory.get("logger", {}).get("count") or 0),
        "logger_count_matches_plan": (
            int(inventory.get("logger", {}).get("count") or 0) == expected_logger_count
        ),
        "requested_schedulers": schedulers,
        "observed_schedulers": observed_schedulers,
        "scheduler_coverage_complete": set(schedulers).issubset(set(observed_schedulers)),
        "paths_with_samples": len(flow_paths),
        "expected_effective_samples_per_path": expected_effective_samples,
        "min_path_sample_count": min(sample_counts) if sample_counts else 0,
        "sample_count_matches_messages": (
            bool(sample_counts)
            and all(count >= expected_effective_samples for count in sample_counts)
        ),
        "benchmark_log": _benchmark_log_status(output_dir, app),
    }

def _safe_clean_output_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _container_workspace() -> str:
    return os.environ.get("HOLOSCAN_CLI_WORKSPACE_NAME", "holohub").strip() or "holohub"


def _container_path_for(host_path: Path, holohub_root: Path) -> tuple[str, list[Path]]:
    """Return the path visible inside the HoloHub container.

    The CLI always mounts HOLOHUB_ROOT at /workspace/<workspace_name>. If the
    caller chooses an output directory outside that tree, mount the output
    directory itself with --add-volume and write to /workspace/volumes/<base>.
    """
    host_path = host_path.resolve()
    holohub_root = holohub_root.resolve()
    workspace = _container_workspace()
    try:
        rel = host_path.relative_to(holohub_root)
        return str(Path("/workspace") / workspace / rel), []
    except ValueError:
        return str(Path("/workspace") / "volumes" / host_path.name), [host_path]


def _read_status_file(path: Path) -> int | None:
    try:
        raw = path.read_text().strip()
        if raw:
            return int(raw)
    except (OSError, ValueError):
        pass
    return None


def main() -> int:
    fixture_arg = sys.argv[1] if len(sys.argv) > 1 else ""

    holohub_root_str = os.environ.get("HOLOHUB_ROOT", "").strip()
    if not holohub_root_str:
        return _fail("HOLOHUB_ROOT env var is required")
    holohub_root = Path(holohub_root_str).expanduser().resolve()
    if not (holohub_root / "holohub").exists():
        return _fail(f"HOLOHUB_ROOT={holohub_root} has no ./holohub script")

    benchmark_script = holohub_root / "benchmarks" / "holoscan_flow_benchmarking" / "benchmark.py"
    if not benchmark_script.is_file():
        return _fail(f"HoloHub flow benchmark script not found: {benchmark_script}")

    app = os.environ.get("HOLOHUB_BENCHMARK_APP", APP_DEFAULT).strip() or APP_DEFAULT
    run_mode = _enum_env("HOLOHUB_BENCHMARK_RUN_MODE", "container", RUN_MODES)
    language = os.environ.get("HOLOHUB_BENCHMARK_LANGUAGE", "python").strip() or "python"
    if language not in LANGUAGES:
        return _fail(f"HOLOHUB_BENCHMARK_LANGUAGE must be one of {'|'.join(LANGUAGES)}")

    schedulers = _csv_env("HOLOHUB_BENCHMARK_SCHEDULERS", ["greedy"], SCHEDULERS)
    runs = _int_env("HOLOHUB_BENCHMARK_RUNS", 1)
    instances = _int_env("HOLOHUB_BENCHMARK_INSTANCES", 1)
    smoke_mode = _bool_env("HOLOHUB_BENCHMARK_SMOKE", False)
    messages = _int_env("HOLOHUB_BENCHMARK_MESSAGES", int("5") if smoke_mode else int("100"))
    worker_threads = _int_env("HOLOHUB_BENCHMARK_WORKER_THREADS", 1)
    monitor_gpu = _bool_env("HOLOHUB_BENCHMARK_MONITOR_GPU", False)
    build_requested = _bool_env("HOLOHUB_BENCHMARK_BUILD", True)
    no_docker_build = _bool_env("HOLOHUB_BENCHMARK_NO_DOCKER_BUILD", False)
    clean_output = _bool_env("HOLOHUB_BENCHMARK_CLEAN_OUTPUT", True)
    timeout_s = _float_env("HOLOHUB_BENCHMARK_TIMEOUT_SECONDS", float("3600.0"), minimum=1.0)
    skip_begin = _int_env("HOLOHUB_BENCHMARK_SKIP_BEGIN_MESSAGES", 0 if smoke_mode else int("10"), minimum=0)
    discard_last = _int_env("HOLOHUB_BENCHMARK_DISCARD_LAST_MESSAGES", 0 if smoke_mode else int("10"), minimum=0)
    gpu = os.environ.get("HOLOHUB_BENCHMARK_GPU", "all").strip() or "all"
    run_command = os.environ.get("HOLOHUB_BENCHMARK_RUN_COMMAND", "").strip()

    output_dir_env = os.environ.get("HOLOHUB_BENCHMARK_OUTPUT_DIR", "").strip()
    if output_dir_env:
        output_dir = Path(output_dir_env).expanduser().resolve()
    else:
        output_dir = (
            holohub_root
            / "build"
            / app
            / "flow_benchmark_output"
        ).resolve()
    if clean_output:
        _safe_clean_output_dir(output_dir)
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
    container_output_dir, extra_volume_mounts = _container_path_for(output_dir, holohub_root)

    contract = _load_contract(
        os.environ.get("HOLOHUB_BENCHMARK_CONTRACT", "").strip(),
        holohub_root,
    )
    holohub_commit = _git_commit(holohub_root)
    container_image = f"holohub-{app}:main"
    container_image_id = _docker_image_id(container_image)
    model_file = str(contract.get("model_file") or "")
    model_sha = _optional_file_sha256(holohub_root, model_file)

    build_cmd: list[str] | None = None
    build_rc: int | None = None
    build_stdout = ""
    build_stderr = ""
    build_seconds: float | None = None
    env = os.environ.copy()

    benchmark_cmd = [
        "python3",
        "benchmarks/holoscan_flow_benchmarking/benchmark.py",
        "-a",
        app,
        "--language",
        language,
        "-r",
        str(runs),
        "-i",
        str(instances),
        "-m",
        str(messages),
        "-d",
        container_output_dir if run_mode == "container" else str(output_dir),
        "--sched",
        *schedulers,
    ]
    if worker_threads != 1:
        benchmark_cmd.extend(["-w", str(worker_threads)])
    if monitor_gpu:
        benchmark_cmd.append("-u")
    if gpu != "all":
        benchmark_cmd.extend(["-g", gpu])
    if run_command:
        benchmark_cmd.extend(["--run-command", run_command])

    container_cmd: list[str] | None = None
    container_rc: int | None = None
    container_stdout = ""
    container_stderr = ""
    container_seconds: float | None = None
    benchmark_rc: int | None = None
    benchmark_stdout = ""
    benchmark_stderr = ""
    benchmark_seconds = 0.0

    if run_mode == "local":
        if build_requested:
            build_cmd = ["./holohub", "build", app, "--local", "--benchmark", "--language", language]
            extra_build_args = os.environ.get("HOLOHUB_BENCHMARK_BUILD_ARGS", "").strip()
            if extra_build_args:
                build_cmd.extend(shlex.split(extra_build_args))
            build_rc, build_stdout, build_stderr, build_seconds = _run(
                build_cmd, holohub_root, timeout_s, env
            )

        if build_rc in (None, 0):
            host_benchmark_cmd = [sys.executable, str(benchmark_script)] + benchmark_cmd[2:]
            benchmark_cmd = host_benchmark_cmd
            benchmark_rc, benchmark_stdout, benchmark_stderr, benchmark_seconds = _run(
                benchmark_cmd, holohub_root, timeout_s, env
            )
        else:
            benchmark_rc = int("125")
            benchmark_stderr = "benchmark skipped because local benchmark build failed"
    else:
        inner_parts: list[str] = ["set -euo pipefail", _shell_join(["mkdir", "-p", container_output_dir])]
        if build_requested:
            build_status = str(Path(container_output_dir) / ".build_exit_code")
            build_cmd = [
                "./holohub",
                "build",
                app,
                "--local",
                "--benchmark",
                "--language",
                language,
            ]
            extra_build_args = os.environ.get("HOLOHUB_BENCHMARK_BUILD_ARGS", "").strip()
            if extra_build_args:
                build_cmd.extend(shlex.split(extra_build_args))
            build_shell = _shell_join(build_cmd)
            inner_parts.append(
                f"if {build_shell}; then echo 0 > {shlex.quote(build_status)}; "
                f"else rc=$?; echo $rc > {shlex.quote(build_status)}; exit $rc; fi"
            )
        benchmark_status = str(Path(container_output_dir) / ".benchmark_exit_code")
        benchmark_shell = _shell_join(benchmark_cmd)
        inner_parts.append(
            f"if {benchmark_shell}; then echo 0 > {shlex.quote(benchmark_status)}; "
            f"else rc=$?; echo $rc > {shlex.quote(benchmark_status)}; exit $rc; fi"
        )
        inner_command = " && ".join(inner_parts)
        container_cmd = [
            "./holohub",
            "run-container",
            app,
            "--language",
            language,
            "--extra-scripts",
            "benchmarking",
        ]
        if no_docker_build:
            container_cmd.append("--no-docker-build")
        for volume in extra_volume_mounts:
            container_cmd.extend(["--add-volume", str(volume)])
        extra_container_args = os.environ.get("HOLOHUB_BENCHMARK_CONTAINER_ARGS", "").strip()
        if extra_container_args:
            container_cmd.extend(shlex.split(extra_container_args))
        container_cmd.extend(["--", inner_command])
        container_rc, container_stdout, container_stderr, container_seconds = _run(
            container_cmd, holohub_root, timeout_s, env
        )
        build_rc = _read_status_file(output_dir / ".build_exit_code")
        if not build_requested:
            build_rc = None
        benchmark_rc = _read_status_file(output_dir / ".benchmark_exit_code")
        if benchmark_rc is None:
            benchmark_rc = container_rc
        benchmark_stdout = container_stdout
        benchmark_stderr = container_stderr
        benchmark_seconds = container_seconds
        build_seconds = None

    if run_mode == "local" and build_rc in (None, 0) and benchmark_rc is None:
        benchmark_rc, benchmark_stdout, benchmark_stderr, benchmark_seconds = _run(
            benchmark_cmd, holohub_root, timeout_s, env
        )

    inventory = _inventory(output_dir)
    analysis = _analyze_logs(output_dir, skip_begin, discard_last)
    analysis["gpu_utilization"] = _analyze_gpu(output_dir)
    domain = _domain_checks(
        app=app,
        output_dir=output_dir,
        inventory=inventory,
        analysis=analysis,
        schedulers=schedulers,
        runs=runs,
        instances=instances,
        messages=messages,
        skip_begin=skip_begin,
        discard_last=discard_last,
    )
    contract_report = _contract_checks(
        contract=contract,
        app=app,
        holohub_root=holohub_root,
        analysis=analysis,
        schedulers=schedulers,
        smoke_mode=smoke_mode,
    )
    total_seconds = (build_seconds or 0.0) + benchmark_seconds

    payload: dict[str, Any] = {
        "skill": SKILL_ID,
        "input": {
            "fixture": fixture_arg,
        },
        "environment": {
            "python_executable": sys.executable,
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "nvidia_visible_devices": os.environ.get("NVIDIA_VISIBLE_DEVICES"),
            "display": os.environ.get("DISPLAY"),
            "display_configured": bool(os.environ.get("DISPLAY")),
        },
        "plan": {
            "app": app,
            "language": language,
            "schedulers": schedulers,
            "runs": runs,
            "instances": instances,
            "messages": messages,
            "worker_threads": worker_threads,
            "monitor_gpu": monitor_gpu,
            "run_mode": run_mode,
            "skip_begin_messages": skip_begin,
            "discard_last_messages": discard_last,
            "build_requested": build_requested,
            "no_docker_build": no_docker_build,
            "clean_output": clean_output,
            "mode": (
                "smoke"
                if smoke_mode
                else ("verify" if contract.get("present") else "measure")
            ),
            "smoke_mode": bool(smoke_mode),
            "rationale": [
                "run HoloHub benchmarking inside the HoloHub container by default",
                "delegate instrumentation to HoloHub holoscan_flow_benchmarking",
                "parse host-visible data-flow tracking logs into evidence-pack latency metrics",
                *(["smoke mode: 5-message contract-lint, latency budgets vacuously pass"] if smoke_mode else []),
            ],
        },
        "invocation": {
            "holohub_root": str(holohub_root),
            "holohub_commit": holohub_commit,
            "benchmark_script": str(benchmark_script),
            "output_dir": str(output_dir),
            "container_output_dir": container_output_dir,
            "run_mode": run_mode,
            "container_workspace": _container_workspace(),
            "container_command": container_cmd,
            "container_exit_code": container_rc,
            "build_command": build_cmd,
            "build_exit_code": build_rc,
            "benchmark_command": benchmark_cmd,
            "benchmark_exit_code": benchmark_rc,
            "custom_run_command": run_command or None,
            "gpu": gpu,
            "container_image": container_image,
            "container_image_id": container_image_id,
            "model_path": str(holohub_root / model_file) if model_file else "",
            "model_sha256": model_sha,
        },
        "output": inventory,
        "analysis": analysis,
        "domain": domain,
        "contract": contract_report,
        "runtime": {
            "build_seconds": build_seconds,
            "benchmark_seconds": benchmark_seconds,
            "container_seconds": container_seconds,
            "total_seconds": total_seconds,
        },
        "logs": {
            "build_stdout_tail": _tail(build_stdout),
            "build_stderr_tail": _tail(build_stderr),
            "container_stdout_tail": _tail(container_stdout),
            "container_stderr_tail": _tail(container_stderr),
            "benchmark_stdout_tail": _tail(benchmark_stdout),
            "benchmark_stderr_tail": _tail(benchmark_stderr),
        },
        "intended_use_disclaimer": (
            "Engineering performance benchmarking only. Not for clinical "
            "interpretation, intra-operative guidance, or regulatory claims."
        ),
    }

    _emit(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
