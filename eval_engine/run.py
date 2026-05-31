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

"""Minimal eval_engine runner for medagent skills.

Reads skill_manifest.yaml in the skill_dir to discover entrypoint, invokes
script via subprocess on the given fixture, validates output JSON against
the skill's output_schema.json, writes evidence pack.

Friction-discovery scaffolding. Not production.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import jsonschema
import typer

app = typer.Typer(add_completion=False)
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from eval_engine.common import _now_iso, _public_command, _public_path  # noqa: E402
from eval_engine.cost_capture import CostCapture, evaluate_cost_envelope  # noqa: E402
from eval_engine.evidence import (  # noqa: E402
    build_validation_summary,
    write_full_pack,
    write_preflight_pack,
)
from eval_engine.gates import (  # noqa: E402
    _evaluate_env_pin,
    _evaluate_factual_echo,
    _evaluate_model_identity,
    _evaluate_runtime_integrity,
    _evaluate_sanity_checks,
    _missing_output_sanity_results,
    _resolve_path,
    _sanity_status,
)
from eval_engine.integrity import _integrity_scan  # noqa: E402
from eval_engine.preflight import _environment_preflight, _preflight_checks  # noqa: E402
from eval_engine.provenance import (  # noqa: E402
    capture_side_effects_snapshot,
    enrich_provenance_from_skill_output,
    write_provenance,
)
from eval_engine.skill_runtime import (  # noqa: E402
    RuntimeArgsError,
    _first_input,
    _load_skill,
    render_runtime_args,
)


def _schema_status(output_payload: dict | None, schema_path: Path | None) -> tuple[str, list[str]]:
    validation_errors: list[str] = []
    if output_payload is not None and schema_path and schema_path.exists():
        schema = json.loads(schema_path.read_text())
        try:
            jsonschema.validate(output_payload, schema)
            return "passed", validation_errors
        except jsonschema.ValidationError as e:
            validation_errors.append(str(e))
            return "failed", validation_errors
    if schema_path is None or not schema_path.exists():
        return "skipped (no schema)", validation_errors
    return "skipped", validation_errors


def _evaluate_sanity(output_payload: dict | None, checks_decl: list) -> tuple[str, list]:
    if output_payload is None and checks_decl:
        results = _missing_output_sanity_results(checks_decl)
    elif output_payload is not None:
        results = _evaluate_sanity_checks(output_payload, checks_decl)
    else:
        results = []
    return _sanity_status(results), results


def _evaluate_factual_echo_gate(
    *,
    fixture: Path,
    output_payload: dict | None,
    decl: list,
) -> tuple[str, list]:
    if not decl or output_payload is None:
        return "skipped", []
    fixture_payload = None
    if fixture.is_file() and fixture.suffix.lower() == ".json":
        try:
            fixture_payload = json.loads(fixture.read_text())
        except Exception:
            fixture_payload = None
    if fixture_payload is None:
        return "skipped", [{"error": "factual_echo declared but fixture is not readable JSON"}]
    return _evaluate_factual_echo(fixture_payload, output_payload, decl)


def _runtime_envelope_status(
    manifest: dict, output_payload: dict | None, elapsed: float
) -> tuple[str, str | None]:
    rt_env = manifest.get("validation", {}).get("expected_runtime_seconds", {})
    rt_min = rt_env.get("min")
    rt_max = rt_env.get("max")
    rt_path = rt_env.get("inference_path")
    rt_value = elapsed
    rt_source = "subprocess_elapsed"
    if rt_path and output_payload:
        skill_reported = _resolve_path(output_payload, rt_path)
        if isinstance(skill_reported, (int, float)):
            rt_value = skill_reported
            rt_source = f"skill_reported({rt_path})"
    if rt_min is not None and rt_value < rt_min:
        return (
            "anomaly_too_fast",
            f"{rt_source}={rt_value:.3f}s < expected min {rt_min}s -- possible silent failure",
        )
    if rt_max is not None and rt_value > rt_max:
        return (
            "anomaly_too_slow",
            f"{rt_source}={rt_value:.3f}s > expected max {rt_max}s -- possible regression",
        )
    if rt_min is not None or rt_max is not None:
        return "within_envelope", None
    return "skipped", None


def _self_reported_cost(output_payload: dict | None) -> dict:
    if not output_payload:
        return {}
    runtime_blob = output_payload.get("runtime") or {}
    return {
        key: runtime_blob[key]
        for key in ("llm_tokens_input", "llm_tokens_output")
        if key in runtime_blob
    }


def _overall_status(
    *,
    proc_returncode: int,
    parse_error: str | None,
    schema_path: Path | None,
    output_payload: dict | None,
    validation_status: str,
    sanity_status: str,
    runtime_status: str,
    integrity_status: str,
    cost_status: str,
    env_pin_status: str,
    fe_status: str,
    mi_status: str,
    ri_status: str,
) -> str:
    if proc_returncode != 0:
        return "failed (execution)"
    if parse_error:
        return "failed (output_parse)"
    if schema_path and output_payload is None:
        return "failed (missing_output)"
    if validation_status == "failed":
        return "failed (schema)"
    gates = (
        ("sanity", sanity_status == "failed"),
        ("runtime", runtime_status.startswith("anomaly")),
        ("integrity", integrity_status == "flagged"),
        ("cost", cost_status == "failed"),
        ("env_pin", env_pin_status == "failed"),
        ("factual_echo", fe_status == "failed"),
        ("model_identity", mi_status == "failed"),
        ("runtime_integrity", ri_status == "flagged"),
    )
    failed = [name for name, bad in gates if bad]
    if failed:
        suffix = "gate" if len(failed) == 1 else "gates"
        return f"failed ({'/'.join(failed)} {suffix})"
    return "passed"


@app.command()
def main(
    skill_dir: Path = typer.Argument(..., exists=True, file_okay=False),
    fixture: Path = typer.Option(..., "--fixture"),
    out: Path = typer.Option(..., "--out", help="evidence pack output directory"),
) -> None:
    fixture_arg = fixture
    skill_dir = skill_dir.resolve()
    out = out.resolve()

    skill = _load_skill(skill_dir)
    script = skill["script"]
    schema_path = skill["schema_path"]
    manifest = skill["manifest"]
    first_input = _first_input(manifest)
    input_formats = set(first_input.get("formats", []) or [])
    if "default_sentinel" in input_formats and str(fixture_arg) == "default":
        fixture = fixture_arg
    else:
        fixture = fixture_arg.expanduser().resolve()

    run_id = uuid4().hex[:12]
    out.mkdir(parents=True, exist_ok=True)

    preflight_status, preflight = _preflight_checks(manifest, fixture)
    env_status, env_reason, env_checks = _environment_preflight(manifest)
    preflight = preflight + env_checks
    if preflight_status == "passed" and env_status == "skip":
        preflight_status = "env_skip"
    elif preflight_status == "passed" and env_status == "failed":
        preflight_status = "failed"

    if preflight_status in ("failed", "env_skip"):
        is_env_skip = preflight_status == "env_skip"
        started_at = _now_iso()
        finished_at = _now_iso()
        proc_returncode = 0 if is_env_skip else 2
        integrity, _, _ = write_preflight_pack(
            out=out,
            run_id=run_id,
            skill_dir=skill_dir,
            fixture=fixture,
            script=script,
            schema_path=schema_path,
            manifest=manifest,
            preflight_status=preflight_status,
            preflight=preflight,
            env_reason=env_reason,
            started_at=started_at,
            finished_at=finished_at,
            proc_returncode=proc_returncode,
            eval_engine_script=Path(__file__).resolve(),
        )
        typer.echo("evidence pack: " + str(out))
        typer.echo("  preflight: " + ("env_skip" if is_env_skip else "failed"))
        typer.echo("  schema: skipped")
        typer.echo("  sanity: skipped")
        typer.echo("  runtime: skipped")
        typer.echo(
            "  integrity: "
            + integrity["status"]
            + " ("
            + str(integrity["n_findings"])
            + " findings)"
        )
        typer.echo(
            "  overall: " + ("skipped (env_unavailable)" if is_env_skip else "preflight_failed")
        )
        typer.echo("  exit code: " + str(proc_returncode))
        if not is_env_skip:
            help_msg = (_first_input(manifest).get("fixture_help") or "").strip()
            if help_msg:
                typer.echo("")
                typer.echo("hint:")
                for line in help_msg.splitlines():
                    typer.echo("  " + line)
        raise typer.Exit(proc_returncode)

    try:
        cmd = render_runtime_args(
            manifest=manifest,
            script=script,
            fixture=fixture,
            out=out,
            skill_dir=skill_dir,
        )
        record_cmd = render_runtime_args(
            manifest=manifest,
            script=script,
            fixture=fixture,
            out=out,
            skill_dir=skill_dir,
            redact_env=True,
        )
    except RuntimeArgsError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(2)

    side_effects_before = capture_side_effects_snapshot(manifest, skill_dir, out=out)

    started_at = _now_iso()
    t0 = time.perf_counter()
    with CostCapture() as cost_cap:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.perf_counter() - t0
    cost_profile = cost_cap.profile()
    finished_at = _now_iso()

    write_provenance(
        out=out,
        manifest=manifest,
        skill_dir=skill_dir,
        side_effects_before=side_effects_before,
        run_out=out,
    )

    trace_records = [
        {
            "ts": started_at,
            "kind": "tool_call_start",
            "tool": script.name,
            "command": _public_command(record_cmd),
            "cwd": _public_path(Path.cwd()),
            "args": [_public_path(fixture)],
        },
        {
            "ts": finished_at,
            "kind": "tool_call_end",
            "exit_code": proc.returncode,
            "elapsed_s": elapsed,
            "stdout_bytes": len(proc.stdout),
            "stderr_bytes": len(proc.stderr),
        },
    ]

    output_payload = None
    parse_error = None
    if proc.returncode == 0 and proc.stdout.strip():
        try:
            output_payload = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            parse_error = str(e)

    validation_status, validation_errors = _schema_status(output_payload, schema_path)
    sanity_checks_decl = manifest.get("validation", {}).get("sanity_checks", [])
    sanity_status, sanity_results = _evaluate_sanity(output_payload, sanity_checks_decl)
    fe_decl = manifest.get("validation", {}).get("factual_echo", [])
    fe_status, fe_results = _evaluate_factual_echo_gate(
        fixture=fixture,
        output_payload=output_payload,
        decl=fe_decl,
    )
    mi_status, mi_results = _evaluate_model_identity(manifest, output_payload or {})
    ri_decl = manifest.get("validation", {}).get("runtime_integrity")
    ri_status, ri_findings = _evaluate_runtime_integrity(
        output_payload or {}, ri_decl or {}, skill_dir
    )
    runtime_status, runtime_reason = _runtime_envelope_status(manifest, output_payload, elapsed)

    integrity = _integrity_scan(skill_dir)
    integrity_status = integrity["status"]
    cost_decl = manifest.get("validation", {}).get("expected_cost", {}) or {}
    self_reported_cost = _self_reported_cost(output_payload)
    cost_eval = evaluate_cost_envelope(cost_decl, cost_profile, self_reported_cost)
    cost_status = cost_eval["status"]
    env_pin_eval = _evaluate_env_pin(
        manifest.get("validation", {}).get("env_pin") or {},
        output_payload,
    )
    env_pin_status = env_pin_eval["status"]

    overall = _overall_status(
        proc_returncode=proc.returncode,
        parse_error=parse_error,
        schema_path=schema_path,
        output_payload=output_payload,
        validation_status=validation_status,
        sanity_status=sanity_status,
        runtime_status=runtime_status,
        integrity_status=integrity_status,
        cost_status=cost_status,
        env_pin_status=env_pin_status,
        fe_status=fe_status,
        mi_status=mi_status,
        ri_status=ri_status,
    )

    validation_summary = build_validation_summary(
        schema_path=schema_path,
        preflight_status=preflight_status,
        preflight=preflight,
        schema_status=validation_status,
        sanity_status=sanity_status,
        sanity_results=sanity_results,
        runtime_status=runtime_status,
        runtime_reason=runtime_reason,
        cost_eval=cost_eval,
        env_pin_eval=env_pin_eval,
        fe_status=fe_status,
        fe_results=fe_results,
        mi_status=mi_status,
        mi_results=mi_results,
        ri_status=ri_status,
        ri_findings=ri_findings,
        overall=overall,
        integrity=integrity,
        validation_errors=validation_errors,
        parse_error=parse_error,
        proc_returncode=proc.returncode,
        proc_stderr=proc.stderr,
    )

    write_full_pack(
        out=out,
        run_id=run_id,
        skill_dir=skill_dir,
        fixture=fixture,
        integrity=integrity,
        script=script,
        manifest=manifest,
        cmd=record_cmd,
        trace_records=trace_records,
        started_at=started_at,
        finished_at=finished_at,
        elapsed=elapsed,
        proc_returncode=proc.returncode,
        output_payload=output_payload,
        cost_profile=cost_profile,
        self_reported_cost=self_reported_cost,
        cost_eval=cost_eval,
        validation_summary=validation_summary,
        eval_engine_script=Path(__file__).resolve(),
    )

    enrich_provenance_from_skill_output(out, output_payload)

    typer.echo("evidence pack: " + str(out))
    typer.echo("  schema: " + validation_status)
    typer.echo("  sanity: " + sanity_status)
    typer.echo("  runtime: " + runtime_status)
    typer.echo("  cost: " + cost_status)
    typer.echo("  env_pin: " + env_pin_status)
    typer.echo("  factual_echo: " + fe_status)
    typer.echo("  model_identity: " + mi_status)
    typer.echo(
        "  runtime_integrity: "
        + ri_status
        + (" (" + str(len(ri_findings)) + " findings)" if ri_findings else "")
    )
    typer.echo(
        "  integrity: " + integrity["status"] + " (" + str(integrity["n_findings"]) + " findings)"
    )
    typer.echo("  overall: " + overall)
    typer.echo("  exit code: " + str(proc.returncode))
    if overall != "passed":
        raise typer.Exit(proc.returncode if proc.returncode != 0 else 1)


if __name__ == "__main__":
    app()
