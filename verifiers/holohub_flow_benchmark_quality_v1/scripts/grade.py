#!/usr/bin/env python3
"""Verify holohub_flow_benchmark evidence packs."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from verifiers._shared.verifier_kit import (  # noqa: E402
    load_pack_json,
    make_check,
    resolve_pack_artifact,
    run_grader,
)

VERIFIER_ID = "medagent.verifiers.holohub_flow_benchmark_quality_v1"
VERIFIER_VERSION = "0.1.0"
TARGET_SKILL_IDS = {"medagent.holohub_flow_benchmark", "holohub_flow_benchmark"}


def _public_path(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        resolved = path.resolve()
    except (OSError, ValueError):
        return str(path)
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def _sha256_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        return h.hexdigest()
    except OSError:
        return None


def _resolve_output_dir(pack_dir: Path, output_payload: dict[str, Any]) -> Path | None:
    invocation = output_payload.get("invocation") or {}
    value = invocation.get("output_dir")
    if not isinstance(value, str) or not value:
        return None
    return resolve_pack_artifact(pack_dir, value, REPO_ROOT)


def _resolve_artifact(pack_dir: Path, output_dir: Path | None, raw: Any) -> Path | None:
    if not isinstance(raw, str) or not raw:
        return None
    bases = [REPO_ROOT]
    if output_dir is not None:
        bases.insert(0, output_dir)
    return resolve_pack_artifact(pack_dir, raw, *bases)


def _artifact_rows(
    pack_dir: Path,
    output_payload: dict[str, Any],
    group_name: str,
) -> list[dict[str, Any]]:
    output = output_payload.get("output") or {}
    group = output.get(group_name) or {}
    output_dir = _resolve_output_dir(pack_dir, output_payload)
    rows: list[dict[str, Any]] = []
    for item in group.get("files") or []:
        if not isinstance(item, dict):
            continue
        raw = item.get("path")
        path = _resolve_artifact(pack_dir, output_dir, raw)
        actual_sha = _sha256_file(path) if path is not None and path.is_file() else None
        declared_sha = item.get("sha256")
        actual_bytes = path.stat().st_size if path is not None and path.is_file() else None
        declared_bytes = item.get("bytes")
        rows.append(
            {
                "declared_path": raw,
                "resolved_path": _public_path(path) if path is not None else None,
                "exists": bool(path is not None and path.is_file()),
                "declared_bytes": declared_bytes,
                "actual_bytes": actual_bytes,
                "bytes_match": (
                    isinstance(declared_bytes, int)
                    and isinstance(actual_bytes, int)
                    and declared_bytes == actual_bytes
                ),
                "declared_sha256": declared_sha if isinstance(declared_sha, str) else None,
                "actual_sha256": actual_sha,
                "sha256_match": (
                    isinstance(declared_sha, str)
                    and actual_sha is not None
                    and declared_sha == actual_sha
                ),
            }
        )
    return rows


def _all_artifacts_ok(rows: list[dict[str, Any]]) -> bool:
    return bool(rows) and all(
        row["exists"] and row["bytes_match"] and row["sha256_match"] for row in rows
    )


def _sample_counts(analysis: dict[str, Any]) -> list[int]:
    counts: list[int] = []
    schedulers = analysis.get("schedulers") or {}
    if not isinstance(schedulers, dict):
        return counts
    for scheduler in schedulers.values():
        if not isinstance(scheduler, dict):
            continue
        paths = scheduler.get("paths") or {}
        if not isinstance(paths, dict):
            continue
        for metrics in paths.values():
            if isinstance(metrics, dict):
                counts.append(int(metrics.get("sample_count") or 0))
    return counts


def _contract_assertions_passed(contract: dict[str, Any]) -> bool:
    assertions = contract.get("assertions") or {}
    return bool(assertions.get("all_required_assertions_passed"))


def _scope_disclosed(output_payload: dict[str, Any]) -> bool:
    text = str(output_payload.get("intended_use_disclaimer") or "").lower()
    return "engineering" in text and "not for clinical" in text


def _gpu_utilization_ok(output_payload: dict[str, Any]) -> bool:
    plan = output_payload.get("plan") or {}
    if not bool(plan.get("monitor_gpu")):
        return True
    output = output_payload.get("output") or {}
    gpu_group = output.get("gpu_utilization") or {}
    analysis = output_payload.get("analysis") or {}
    gpu = analysis.get("gpu_utilization") or {}
    max_percent = gpu.get("max_percent")
    return (
        int(gpu_group.get("count") or 0) >= 1
        and isinstance(max_percent, (int, float))
        and 0.0 <= float(max_percent) <= 100.0
    )


def grade(pack_dir: Path) -> dict[str, Any]:
    pack_dir = pack_dir.resolve()
    output_payload = load_pack_json(pack_dir, "output.json")
    validation = load_pack_json(pack_dir, "validation_summary.json")
    manifest = load_pack_json(pack_dir, "manifest.json")

    skill_id = str(manifest.get("skill_id") or output_payload.get("skill") or "")
    plan = output_payload.get("plan") or {}
    invocation = output_payload.get("invocation") or {}
    output = output_payload.get("output") or {}
    analysis = output_payload.get("analysis") or {}
    domain = output_payload.get("domain") or {}
    contract = output_payload.get("contract") or {}
    logger_rows = _artifact_rows(pack_dir, output_payload, "logger")
    gpu_rows = _artifact_rows(pack_dir, output_payload, "gpu_utilization")
    other_rows = _artifact_rows(pack_dir, output_payload, "other")
    counts = _sample_counts(analysis)
    requested_schedulers = [str(item) for item in plan.get("schedulers") or []]
    observed_schedulers = set(domain.get("observed_schedulers") or [])
    benchmark_log = domain.get("benchmark_log") or {}

    checks = [
        make_check("target_skill_matches", skill_id in TARGET_SKILL_IDS, f"skill_id={skill_id!r}"),
        make_check(
            "source_pack_passed",
            validation.get("overall_status") == "passed",
            f"source pack overall={validation.get('overall_status')!r}",
        ),
        make_check(
            "output_skill_matches",
            output_payload.get("skill") == "holohub_flow_benchmark",
            f"output.skill={output_payload.get('skill')!r}",
        ),
        make_check(
            "benchmark_exit_code_zero",
            invocation.get("benchmark_exit_code") == 0,
            f"benchmark_exit_code={invocation.get('benchmark_exit_code')!r}",
        ),
        make_check(
            "holohub_commit_present",
            isinstance(invocation.get("holohub_commit"), str)
            and invocation.get("holohub_commit").strip() != "",
            f"holohub_commit={invocation.get('holohub_commit')!r}",
        ),
        make_check(
            "logger_artifacts_hash_match",
            _all_artifacts_ok(logger_rows),
            f"logger_files={len(logger_rows)}",
            artifacts=logger_rows,
        ),
        make_check(
            "latency_samples_present",
            int(analysis.get("paths_observed") or 0) > 0
            and int(analysis.get("total_latency_samples") or 0) > 0
            and bool(counts)
            and min(counts) > 0,
            (
                f"paths={analysis.get('paths_observed')!r}, "
                f"total_samples={analysis.get('total_latency_samples')!r}, "
                f"min_path_samples={min(counts) if counts else 0}"
            ),
        ),
        make_check(
            "scheduler_coverage_complete",
            bool(requested_schedulers)
            and set(requested_schedulers).issubset(observed_schedulers)
            and bool(domain.get("scheduler_coverage_complete")),
            f"requested={requested_schedulers!r}, observed={sorted(observed_schedulers)!r}",
        ),
        make_check(
            "logger_count_matches_plan",
            bool(domain.get("logger_count_matches_plan"))
            and int(output.get("logger", {}).get("count") or 0)
            == int(domain.get("expected_logger_count") or 0),
            (
                f"observed={output.get('logger', {}).get('count')!r}, "
                f"expected={domain.get('expected_logger_count')!r}"
            ),
        ),
        make_check(
            "benchmark_log_completed",
            bool(benchmark_log.get("present"))
            and bool(benchmark_log.get("evaluation_completed"))
            and not bool(benchmark_log.get("missing_log_errors")),
            f"benchmark_log={benchmark_log!r}",
        ),
        make_check(
            "contract_assertions_passed",
            _contract_assertions_passed(contract),
            f"contract.present={contract.get('present')!r}, assertions={contract.get('assertions')!r}",
        ),
        make_check(
            "gpu_utilization_consistent",
            _gpu_utilization_ok(output_payload),
            f"monitor_gpu={plan.get('monitor_gpu')!r}, gpu_files={len(gpu_rows)}",
            artifacts=gpu_rows,
        ),
        make_check(
            "benchmark_log_hash_match",
            _all_artifacts_ok(other_rows),
            f"other_files={len(other_rows)}",
            artifacts=other_rows,
        ),
        make_check(
            "scope_disclosed",
            _scope_disclosed(output_payload),
            "intended_use_disclaimer must disclose engineering-only and non-clinical scope",
        ),
    ]

    hard_fail = any(check["status"] == "fail" for check in checks)
    overall = "fail" if hard_fail else "pass"

    return {
        "verifier": {"id": VERIFIER_ID, "version": VERIFIER_VERSION},
        "target": {
            "evidence_pack": _public_path(pack_dir),
            "skill_id": skill_id,
            "source_overall_status": validation.get("overall_status"),
        },
        "flow_quality": {
            "verdict": overall,
            "acceptable": overall == "pass",
            "app": plan.get("app"),
            "run_mode": plan.get("run_mode"),
            "logger_file_count": len(logger_rows),
            "gpu_file_count": len(gpu_rows),
            "requested_schedulers": requested_schedulers,
            "observed_schedulers": sorted(observed_schedulers),
            "scheduler_coverage_complete": bool(domain.get("scheduler_coverage_complete")),
            "paths_observed": int(analysis.get("paths_observed") or 0),
            "total_latency_samples": int(analysis.get("total_latency_samples") or 0),
            "min_path_sample_count": min(counts) if counts else 0,
            "contract_present": bool(contract.get("present")),
            "contract_assertions_passed": _contract_assertions_passed(contract),
        },
        "checks": checks,
        "overall": overall,
    }


if __name__ == "__main__":
    run_grader(grade, sort_keys=True)
