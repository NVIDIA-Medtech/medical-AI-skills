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

"""Workflow-level Holoscan flow-benchmark stream aggregation for workflow_summary.json."""

from __future__ import annotations

from typing import Any

STREAM_FORMAT_VERSION = "1.0.0"

_LATENCY_KEYS = (
    "min_ms",
    "avg_ms",
    "median_ms",
    "p95_ms",
    "p99_ms",
    "tail_95_100_ms",
    "flatness_10_90_ms",
    "sample_count",
)


def _file_group_summary(blob: dict[str, Any] | None) -> dict[str, Any]:
    group = blob or {}
    files = group.get("files") or []
    return {
        "count": int(group.get("count") or 0),
        "total_bytes": int(group.get("total_bytes") or 0),
        "paths": [
            str(item.get("path")) for item in files if isinstance(item, dict) and item.get("path")
        ][:20],
    }


def _path_rows(scheduler_data: dict[str, Any]) -> list[dict[str, Any]]:
    paths = (scheduler_data or {}).get("paths") or {}
    if not isinstance(paths, dict):
        return []
    rows: list[dict[str, Any]] = []
    for flow_path, metrics in sorted(paths.items()):
        if not isinstance(metrics, dict):
            continue
        if int(metrics.get("sample_count") or 0) <= 0:
            continue
        row: dict[str, Any] = {"path": str(flow_path)}
        for key in _LATENCY_KEYS:
            if key in metrics:
                row[key] = metrics[key]
        rows.append(row)
    return rows


def _scheduler_latency_summary(analysis: dict[str, Any]) -> dict[str, Any]:
    schedulers = analysis.get("schedulers") or {}
    if not isinstance(schedulers, dict):
        return {}
    out: dict[str, Any] = {}
    for scheduler, data in sorted(schedulers.items()):
        if not isinstance(data, dict):
            continue
        rows = _path_rows(data)
        primary_p95 = None
        for row in rows:
            p95 = row.get("p95_ms")
            if isinstance(p95, (int, float)):
                primary_p95 = p95 if primary_p95 is None else min(primary_p95, p95)
        out[str(scheduler)] = {
            "path_count": int(data.get("path_count") or len(rows)),
            "paths": rows,
            "min_p95_ms": primary_p95,
        }
    return out


def _contract_summary(contract: dict[str, Any]) -> dict[str, Any]:
    if not contract:
        return {"present": False}
    assertions = contract.get("assertions") or {}
    budget_results = contract.get("latency_budget_results") or {}
    return {
        "present": bool(contract.get("present")),
        "path": str(contract.get("path") or ""),
        "all_assertions_passed": bool(assertions.get("all_required_assertions_passed", False)),
        "smoke_mode": bool(contract.get("smoke_mode")),
        "scheduler_coverage_complete": bool(assertions.get("scheduler_coverage_complete", False)),
        "latency_budgets_met": bool(assertions.get("latency_budgets_met", False)),
        "latency_budget_results": budget_results,
    }


def _workflow_primary_latency(analysis: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    first = analysis.get("first_path") or {}
    if isinstance(first, dict) and int(first.get("sample_count") or 0) > 0:
        return {
            "scheduler": first.get("scheduler"),
            "path": first.get("path"),
            "p95_ms": first.get("p95_ms"),
            "p99_ms": first.get("p99_ms"),
            "sample_count": first.get("sample_count"),
            "source": "analysis.first_path",
        }
    scheduler_results = contract.get("scheduler_results") or {}
    if isinstance(scheduler_results, dict):
        for scheduler, result in sorted(scheduler_results.items()):
            if not isinstance(result, dict):
                continue
            if int(result.get("sample_count") or 0) > 0:
                return {
                    "scheduler": scheduler,
                    "path": result.get("primary_path"),
                    "p95_ms": result.get("p95_ms"),
                    "p99_ms": result.get("p99_ms"),
                    "sample_count": result.get("sample_count"),
                    "source": "contract.scheduler_results",
                }
    return {}


def extract_flow_benchmark_stream(
    step_id: str,
    payload: dict[str, Any],
    *,
    step_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize one holohub_flow_benchmark output.json into stream-native fields."""
    plan = payload.get("plan") or {}
    invocation = payload.get("invocation") or {}
    analysis = payload.get("analysis") or {}
    domain = payload.get("domain") or {}
    contract = payload.get("contract") or {}
    output = payload.get("output") or {}

    return {
        "step_id": step_id,
        "skill": (step_record or {}).get("skill") or payload.get("skill"),
        "step_overall": (step_record or {}).get("overall_status"),
        "holohub_app": plan.get("app"),
        "holohub_commit": invocation.get("holohub_commit"),
        "holoscan_flow": {
            "plan": {
                "app": plan.get("app"),
                "language": plan.get("language"),
                "schedulers": plan.get("schedulers"),
                "messages": plan.get("messages"),
                "mode": plan.get("mode"),
                "smoke_mode": plan.get("smoke_mode"),
                "run_mode": plan.get("run_mode"),
            },
            "invocation": {
                "benchmark_exit_code": invocation.get("benchmark_exit_code"),
                "container_exit_code": invocation.get("container_exit_code"),
                "build_exit_code": invocation.get("build_exit_code"),
                "output_dir": invocation.get("output_dir"),
            },
            "artifacts": {
                "logger": _file_group_summary(output.get("logger")),
                "gpu_utilization": _file_group_summary(output.get("gpu_utilization")),
            },
            "latency": {
                "paths_observed": analysis.get("paths_observed"),
                "total_latency_samples": analysis.get("total_latency_samples"),
                "trim": {
                    "skip_begin_messages": analysis.get("skip_begin_messages"),
                    "discard_last_messages": analysis.get("discard_last_messages"),
                },
                "first_path": analysis.get("first_path"),
                "by_scheduler": _scheduler_latency_summary(analysis),
                "gpu_utilization": analysis.get("gpu_utilization"),
            },
            "domain": {
                "scheduler_coverage_complete": domain.get("scheduler_coverage_complete"),
                "logger_count_matches_plan": domain.get("logger_count_matches_plan"),
                "benchmark_log": domain.get("benchmark_log"),
            },
            "contract": _contract_summary(contract),
        },
    }


def build_workflow_stream_block(
    context: dict[str, Any],
    step_results: list[dict],
) -> dict[str, Any]:
    """Build workflow_summary ``stream`` from per-step skill output payloads."""
    steps: dict[str, Any] = {}
    primary_latency: dict[str, Any] = {}
    holohub_app: str | None = None
    holohub_commit: str | None = None

    for record in step_results:
        step_id = record["id"]
        payload = context.get(step_id) or {}
        if not isinstance(payload, dict):
            continue
        analysis = payload.get("analysis")
        is_flow_benchmark = payload.get("skill") == "holohub_flow_benchmark" or (
            isinstance(analysis, dict) and "schedulers" in analysis
        )
        if not is_flow_benchmark:
            continue

        entry = extract_flow_benchmark_stream(step_id, payload, step_record=record)
        steps[step_id] = entry

        plan = payload.get("plan") or {}
        inv = payload.get("invocation") or {}
        if plan.get("app"):
            holohub_app = str(plan.get("app"))
        if inv.get("holohub_commit"):
            holohub_commit = str(inv.get("holohub_commit"))

        candidate = _workflow_primary_latency(
            payload.get("analysis") or {},
            payload.get("contract") or {},
        )
        if candidate and not primary_latency:
            primary_latency = candidate

    return {
        "stream_format_version": STREAM_FORMAT_VERSION,
        "present": bool(steps),
        "holohub_app": holohub_app,
        "holohub_commit": holohub_commit,
        "primary_latency": primary_latency,
        "steps": steps,
    }
