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

"""Workflow runner — orchestrates multi-skill pipelines through the eval_engine.

Reads a workflow YAML spec, executes each step via run.py or run_trusted (when
``trusted: true``), resolves output references between steps, and writes a
workflow-level summary including trust linkage for trusted steps.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import typer
import yaml

app = typer.Typer(add_completion=False)

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from eval_engine.common import (  # noqa: E402
    PACK_FORMAT_VERSION,
    _now_iso,
    _public_path,
    _read_json_or_empty,
)
from eval_engine.evidence import SKILL_RUN_SUBDIR  # noqa: E402
from eval_engine.status import is_failed, is_passed  # noqa: E402
from eval_engine.workflow_stream import build_workflow_stream_block  # noqa: E402

WORKFLOW_FORMAT_VERSION = "1.0.0"
REF_RE = re.compile(r"\$\{([\w.]+)\}")


def _resolve(value, context):
    if not isinstance(value, str):
        return value
    m = REF_RE.fullmatch(value)
    if not m:
        return value
    parts = m.group(1).split(".")
    cur = context
    for p in parts:
        if isinstance(cur, dict):
            cur = cur.get(p)
        else:
            return None
        if cur is None:
            return None
    return cur


def _resolve_deep(value, context):
    """Recursively resolve ${step.path} references inside nested dicts and lists."""
    if isinstance(value, str):
        return _resolve(value, context)
    if isinstance(value, dict):
        return {k: _resolve_deep(v, context) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_deep(v, context) for v in value]
    return value


def _step_pack_dir(step_out: Path, *, trusted: bool) -> Path:
    return step_out / SKILL_RUN_SUBDIR if trusted else step_out


def _step_failed(
    proc_rc: int,
    overall_str: str,
    inner_exit: int,
    *,
    trusted: bool,
    trust_overall: str | None,
) -> bool:
    if proc_rc != 0:
        return True
    if trusted and trust_overall == "failed":
        return True
    return is_failed(overall_str) or overall_str == "skipped" or inner_exit != 0


def _workflow_overall(step_results: list[dict], halted: bool) -> str:
    if halted or any(r.get("overall_status") in ("fixture_unresolved",) for r in step_results):
        return "failed"
    if any(
        is_failed(r.get("overall_status")) or r.get("trust_overall") == "failed"
        for r in step_results
    ):
        return "failed"
    if any(r.get("trust_overall") == "gap" for r in step_results):
        return "gap"
    if any(r.get("trust_overall") == "warn" for r in step_results):
        return "warn"
    if all(is_passed(r.get("overall_status")) for r in step_results):
        return "passed"
    return "failed"


def _run_step(
    skill_dir: Path,
    fixture: Path,
    step_out: Path,
    *,
    trusted: bool,
    step_env: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess, dict, dict | None]:
    step_out.mkdir(parents=True, exist_ok=True)
    module = "eval_engine.run_trusted" if trusted else "eval_engine.run"
    cmd = [
        sys.executable,
        "-m",
        module,
        str(skill_dir),
        "--fixture",
        str(fixture),
        "--out",
        str(step_out),
    ]
    env = os.environ.copy()
    if step_env:
        env.update({k: str(v) for k, v in step_env.items()})
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT, env=env)
    pack_dir = _step_pack_dir(step_out, trusted=trusted)
    step_val = _read_json_or_empty(pack_dir / "validation_summary.json") or {}
    trust_summary = _read_json_or_empty(step_out / "trust_summary.json") if trusted else None
    return proc, step_val, trust_summary


def _build_step_record(
    *,
    step_id: str,
    skill: str,
    fixture: Path,
    step_out: Path,
    out: Path,
    proc: subprocess.CompletedProcess,
    step_val: dict,
    trust_summary: dict | None,
    trusted: bool,
) -> dict:
    overall_str = step_val.get("overall_status", "")
    if trusted and trust_summary:
        overall_str = trust_summary.get("skill_overall", overall_str)

    record: dict = {
        "id": step_id,
        "skill": skill,
        "mode": "trusted" if trusted else "skill",
        "fixture": _public_path(fixture),
        "exit_code": proc.returncode,
        "schema_status": step_val.get("schema_status"),
        "sanity_status": step_val.get("sanity_status"),
        "runtime_status": step_val.get("runtime_status"),
        "integrity_status": step_val.get("integrity_status"),
        "overall_status": overall_str,
        "evidence_pack": str(step_out.relative_to(out)),
    }
    if trusted:
        record["skill_pack"] = str((step_out / SKILL_RUN_SUBDIR).relative_to(out))
        if trust_summary:
            record["trust_summary"] = str((step_out / "trust_summary.json").relative_to(out))
            record["trust_overall"] = trust_summary.get("overall")
            record["verifiers"] = trust_summary.get("verifiers") or []
            record["trust_gaps"] = trust_summary.get("gaps") or []
    return record


def _build_trust_block(step_results: list[dict]) -> dict:
    """At-a-glance trust index. Full verifier and gap detail stays in step_results."""
    steps: dict = {}
    for r in step_results:
        entry = {"mode": r.get("mode", "skill"), "overall": r.get("overall_status")}
        if r.get("mode") == "trusted":
            entry["trust_overall"] = r.get("trust_overall")
            entry["n_verifiers"] = len(r.get("verifiers") or [])
            entry["n_gaps"] = len(r.get("trust_gaps") or [])
        steps[r["id"]] = entry
    return {"steps": steps}


def _render_workflow_record(
    *,
    workflow_id: str,
    run_id: str,
    started_at: str,
    elapsed: float,
    overall_status: str,
    n_completed: int,
    n_steps: int,
    step_results: list[dict],
    trust_block: dict,
    stream_block: dict,
    initial_input: str | None,
) -> str:
    lines = [
        "# Workflow Run Record",
        "",
        "- workflow_id: " + workflow_id,
        "- run_id: " + run_id,
        "- started: " + started_at,
        "- elapsed: " + str(round(elapsed, 3)) + "s",
        "- overall: **" + overall_status + "**",
        "- steps: " + str(n_completed) + " / " + str(n_steps) + " completed",
    ]
    if initial_input:
        lines.append("- input: `" + _public_path(initial_input) + "`")
    lines.extend(
        [
            "",
            "## Steps",
            "",
            "| id | skill | mode | schema | sanity | runtime | integrity | overall | trust |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for r in step_results:
        trust_col = str(r.get("trust_overall", "-")) if r.get("mode") == "trusted" else "-"
        row = "| " + r["id"] + " | " + r["skill"] + " | " + str(r.get("mode", "skill")) + " | "
        row += str(r.get("schema_status", "-")) + " | "
        row += str(r.get("sanity_status", "-")) + " | "
        row += str(r.get("runtime_status", "-")) + " | "
        row += str(r.get("integrity_status", "-")) + " | "
        row += "**" + str(r.get("overall_status", "-")) + "** | "
        row += str(trust_col) + " |"
        lines.append(row)

    trusted_steps = [r for r in step_results if r.get("mode") == "trusted"]
    if trusted_steps:
        lines.extend(["", "## Trust", ""])
        for r in trusted_steps:
            lines.append(
                "- step `"
                + r["id"]
                + "`: skill **"
                + str(r.get("overall_status", "-"))
                + "**, trust **"
                + str(r.get("trust_overall", "-"))
                + "**"
            )
            for v in r.get("verifiers") or []:
                lines.append(
                    "  - verifier `"
                    + str(v.get("id", "?"))
                    + "`: "
                    + str(v.get("overall", "-"))
                    + " (`"
                    + str(v.get("pack", ""))
                    + "`)"
                )
            for g in r.get("trust_gaps") or []:
                lines.append("  - gap `" + str(g.get("id", "?")) + "`: " + str(g.get("reason", "")))

    lines.extend(["", "## Per-step evidence packs", ""])
    for r in step_results:
        lines.append("- `" + r["evidence_pack"] + "/` -- step `" + r["id"] + "`")
        if r.get("skill_pack"):
            lines.append("  - skill pack: `" + r["skill_pack"] + "/`")
        if r.get("trust_summary"):
            lines.append("  - trust summary: `" + r["trust_summary"] + "`")
    lines.append("")
    lines.append("## Trust linkage (machine)")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(trust_block, indent=2))
    lines.append("```")

    if stream_block.get("present"):
        lines.extend(["", "## Stream (Holoscan flow benchmark)", ""])
        if stream_block.get("holohub_app"):
            lines.append("- app: `" + str(stream_block["holohub_app"]) + "`")
        if stream_block.get("holohub_commit"):
            lines.append("- holohub_commit: `" + str(stream_block["holohub_commit"]) + "`")
        primary = stream_block.get("primary_latency") or {}
        if primary:
            lines.append(
                "- primary latency: scheduler `"
                + str(primary.get("scheduler", "?"))
                + "`, p95="
                + str(primary.get("p95_ms", "?"))
                + " ms, samples="
                + str(primary.get("sample_count", "?"))
            )
        for step_id, entry in (stream_block.get("steps") or {}).items():
            holoscan = entry.get("holoscan_flow") or {}
            latency = holoscan.get("latency") or {}
            lines.append(
                f"- step `{step_id}`: "
                + str(latency.get("paths_observed", 0))
                + " paths, "
                + str(latency.get("total_latency_samples", 0))
                + " samples"
            )
        lines.extend(["", "### Stream linkage (machine)", "", "```json"])
        lines.append(json.dumps(stream_block, indent=2))
        lines.append("```")

    return "\n".join(lines)


@app.command()
def main(
    workflow: Path = typer.Argument(..., exists=True, dir_okay=False),
    out: Path = typer.Option(..., "--out"),
    initial_input: str = typer.Option(None, "--input"),
) -> None:
    spec = yaml.safe_load(workflow.read_text())
    workflow_id = spec.get("workflow_id", workflow.stem)
    steps = spec.get("steps", [])

    run_id = uuid4().hex[:12]
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    started_at = _now_iso()
    t0 = time.perf_counter()
    context: dict = {"input": initial_input}

    step_results: list[dict] = []
    halted = False
    for step in steps:
        step_id = step["id"]
        skill_path = Path(step["skill"])
        skill_dir = skill_path if skill_path.is_absolute() else REPO_ROOT / step["skill"]
        trusted = bool(step.get("trusted"))
        step_inputs = step.get("inputs", {}) or {}
        raw_fixture = step_inputs.get("fixture")
        raw_fixture_template = step_inputs.get("fixture_template")
        step_out = out / step_id
        step_out.mkdir(parents=True, exist_ok=True)

        if raw_fixture is None and raw_fixture_template is not None:
            resolved_template = _resolve_deep(raw_fixture_template, context)
            composed_path = step_out / "composed_fixture.json"
            composed_path.write_text(json.dumps(resolved_template, indent=2))
            fixture = composed_path
        else:
            fixture = _resolve(raw_fixture, context)

        if fixture is None:
            typer.echo(
                "step " + step_id + ": cannot resolve fixture " + repr(raw_fixture),
                err=True,
            )
            step_results.append(
                {
                    "id": step_id,
                    "skill": step["skill"],
                    "mode": "trusted" if trusted else "skill",
                    "overall_status": "fixture_unresolved",
                    "fixture_raw": str(raw_fixture),
                }
            )
            halted = True
            break

        step_env = step.get("env") or {}
        proc, step_val, trust_summary = _run_step(
            skill_dir, Path(fixture), step_out, trusted=trusted, step_env=step_env
        )
        step_payload = _read_json_or_empty(
            _step_pack_dir(step_out, trusted=trusted) / "output.json"
        )
        if step_payload:
            context[step_id] = step_payload

        trust_overall = trust_summary.get("overall") if trust_summary else None
        overall_str = step_val.get("overall_status", "")
        inner_exit = step_val.get("exit_code", 0)
        step_failed = _step_failed(
            proc.returncode,
            overall_str,
            inner_exit,
            trusted=trusted,
            trust_overall=trust_overall,
        )
        if step_failed:
            halted = True

        record = _build_step_record(
            step_id=step_id,
            skill=step["skill"],
            fixture=Path(fixture),
            step_out=step_out,
            out=out,
            proc=proc,
            step_val=step_val,
            trust_summary=trust_summary,
            trusted=trusted,
        )
        step_results.append(record)

        if step_failed:
            msg = (
                "step "
                + step_id
                + ": FAILED (overall="
                + record["overall_status"]
                + (", trust=" + str(trust_overall) if trusted else "")
                + "); halting"
            )
            typer.echo(msg, err=True)
            break

    elapsed = time.perf_counter() - t0
    finished_at = _now_iso()

    n_completed = sum(1 for r in step_results if is_passed(r.get("overall_status")))
    overall_status = _workflow_overall(step_results, halted)
    trust_block = _build_trust_block(step_results)
    stream_block = build_workflow_stream_block(context, step_results)

    workflow_summary = {
        "pack_format_version": PACK_FORMAT_VERSION,
        "workflow_format_version": WORKFLOW_FORMAT_VERSION,
        "workflow_id": workflow_id,
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "elapsed_seconds": round(elapsed, 3),
        "input": _public_path(initial_input) if initial_input else None,
        "n_steps_total": len(steps),
        "n_steps_completed": n_completed,
        "overall_status": overall_status,
        "steps": step_results,
        "trust": trust_block,
        "stream": stream_block,
    }
    (out / "workflow_summary.json").write_text(json.dumps(workflow_summary, indent=2))

    (out / "workflow_run_record.md").write_text(
        _render_workflow_record(
            workflow_id=workflow_id,
            run_id=run_id,
            started_at=started_at,
            elapsed=elapsed,
            overall_status=overall_status,
            n_completed=n_completed,
            n_steps=len(steps),
            step_results=step_results,
            trust_block=trust_block,
            stream_block=stream_block,
            initial_input=initial_input,
        )
    )

    typer.echo("workflow run: " + str(out))
    typer.echo("  overall: " + overall_status)
    typer.echo("  steps completed: " + str(n_completed) + "/" + str(len(steps)))
    if overall_status == "failed":
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
