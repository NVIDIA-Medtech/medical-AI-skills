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

"""Evidence-pack writers for single-skill eval_engine runs."""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

from eval_engine.common import (
    FENCE,
    PACK_FORMAT_VERSION,
    _env_lock_fingerprint,
    _path_size,
    _pip_freeze,
    _public_command,
    _public_path,
    _replay_script,
    _repo_git_sha,
    _runtime_summary,
    _sanitize_public_text,
    _sha256_path,
    _skill_dir_files,
)
from eval_engine.integrity import _integrity_scan
from eval_engine.skill_runtime import _first_input
from eval_engine.trace import write_trace_jsonl

PACK_KIND_SKILL_RUN = "skill_run"
PACK_KIND_BENCHMARK_RUN = "benchmark_run"
PACK_KIND_LLM_SKILL_RUN = "llm_skill_run"
PACK_KIND_PAIRED_EVAL = "paired_eval"
SKILL_RUN_SUBDIR = "skill_run"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2))


def _write_trace(out: Path, trace_records: list[dict]) -> None:
    write_trace_jsonl(out / "agent_run_trace.jsonl", trace_records)


def _write_replay(
    out: Path,
    script: Path,
    fixture: Path,
    manifest: dict,
    *,
    preflight_failed: bool = False,
    command: list[str] | None = None,
) -> None:
    replay_path = out / "replay.sh"
    replay_path.write_text(
        _replay_script(
            script,
            fixture,
            manifest,
            preflight_failed=preflight_failed,
            command=command,
        )
    )
    replay_path.chmod(0o755)


def _bundle_manifest(
    *,
    run_id: str,
    manifest: dict,
    skill_dir: Path,
    fixture: Path,
    script: Path,
    command: list[str],
    pip_freeze_text: str,
    eval_engine_script: Path,
    pack_kind: str = PACK_KIND_SKILL_RUN,
) -> dict:
    env_fingerprint = _env_lock_fingerprint(pip_freeze_text)
    return {
        "pack_format_version": PACK_FORMAT_VERSION,
        "pack_kind": pack_kind,
        "run_id": run_id,
        "skill_id": manifest.get("id"),
        "skill_version": manifest.get("version"),
        "skill_dir": _public_path(skill_dir),
        "repo_git_sha": _repo_git_sha(),
        "environment": {
            "fingerprint": env_fingerprint,
            "pip_freeze_lines": pip_freeze_text.count("\n"),
            "pip_freeze_path": "environment.lock",
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
        "skill_dir_files": _skill_dir_files(skill_dir),
        "fixture": {
            "path": _public_path(fixture),
            "sha256": _sha256_path(fixture),
            "size_bytes": _path_size(fixture),
            "is_dir": fixture.is_dir(),
        },
        "command": _public_command(command),
        "eval_engine_script": _public_path(eval_engine_script),
    }


def write_preflight_pack(
    *,
    out: Path,
    run_id: str,
    skill_dir: Path,
    fixture: Path,
    script: Path,
    schema_path: Path | None,
    manifest: dict,
    preflight_status: str,
    preflight: list[dict],
    env_reason: str,
    started_at: str,
    finished_at: str,
    proc_returncode: int,
    eval_engine_script: Path,
) -> tuple[dict, dict, dict]:
    is_env_skip = preflight_status == "env_skip"
    command = [sys.executable, str(script), str(fixture)]
    trace_records = [
        {
            "ts": started_at,
            "kind": "preflight_start",
            "tool": script.name,
            "command": _public_command(command),
            "cwd": _public_path(Path.cwd()),
            "args": [_public_path(fixture)],
        },
        {"ts": finished_at, "kind": "preflight_end", "status": preflight_status},
    ]
    _write_trace(out, trace_records)

    integrity = _integrity_scan(skill_dir)
    _write_json(out / "integrity_check.json", integrity)
    cost_eval = {"status": "skipped", "results": []}
    _write_json(
        out / "cost_profile.json",
        {
            "measured": {},
            "self_reported": {},
            "evaluation": cost_eval,
        },
    )
    _write_json(
        out / "runtime_profile.json",
        {
            "started_at": started_at,
            "finished_at": finished_at,
            "elapsed_seconds": 0.0,
            "exit_code": proc_returncode,
            "environment": _runtime_summary(),
        },
    )

    pip_freeze_text = _pip_freeze()
    (out / "environment.lock").write_text(pip_freeze_text)
    bundle_manifest = _bundle_manifest(
        run_id=run_id,
        manifest=manifest,
        skill_dir=skill_dir,
        fixture=fixture,
        script=script,
        command=command,
        pip_freeze_text=pip_freeze_text,
        eval_engine_script=eval_engine_script,
    )
    _write_json(out / "manifest.json", bundle_manifest)
    _write_replay(
        out,
        script,
        fixture,
        manifest,
        preflight_failed=True,
        command=command,
    )

    validation_summary = {
        "schema": _public_path(schema_path) if schema_path else None,
        "preflight_status": preflight_status,
        "preflight": preflight,
        "schema_status": "skipped",
        "sanity_status": "skipped",
        "sanity_results": [],
        "runtime_status": "skipped",
        "runtime_reason": None,
        "cost_status": cost_eval["status"],
        "cost_results": cost_eval["results"],
        "env_pin_status": "skipped",
        "env_pin_results": [],
        "factual_echo_status": "skipped",
        "factual_echo_results": [],
        "model_identity_status": "skipped",
        "model_identity_results": [],
        "runtime_integrity_status": "skipped",
        "runtime_integrity_findings": [],
        "overall_status": "skipped (env_unavailable)" if is_env_skip else "preflight_failed",
        "integrity_status": integrity["status"],
        "integrity_n_findings": integrity["n_findings"],
        "errors": [],
        "parse_error": None,
        "exit_code": proc_returncode,
        "stderr_excerpt": (
            f"environment preflight skipped execution: {env_reason}"
            if is_env_skip
            else (
                "preflight failed; skill was not executed.\n\n"
                + (_first_input(manifest).get("fixture_help") or "").strip()
            ).rstrip()
        ),
    }
    _write_json(out / "validation_summary.json", validation_summary)

    lines = [
        "# Workflow Run Record",
        "",
        "- run id: " + run_id,
        "- skill: " + str(manifest.get("id", "?")) + " v" + str(manifest.get("version", "?")),
        "- started: " + started_at,
        "- finished: " + finished_at,
        "- elapsed: 0.0s",
        "- exit code: " + str(proc_returncode),
        "",
        "## Skill",
        "- dir: " + _public_path(skill_dir),
        "- entrypoint: " + str(script.relative_to(skill_dir)),
        "",
        "## Fixture",
        "- path: " + _public_path(fixture),
        "- sha256: " + bundle_manifest["fixture"]["sha256"],
        "- size: " + str(bundle_manifest["fixture"]["size_bytes"]) + " bytes",
        "",
        "## Validation",
        "- status: " + ("skipped (env_unavailable)" if is_env_skip else "preflight_failed"),
        "- cost: skipped",
        "",
        "## Caveats",
        (
            (
                "- Skill was skipped because the host environment did not satisfy "
                "the manifest's declared requirements: " + env_reason
            )
            if is_env_skip
            else ("- Skill was not executed because preflight failed.")
        ),
        "- Engineering-time evidence; not clinical or regulatory artefact.",
    ]
    (out / "workflow_run_record.md").write_text("\n".join(lines))
    return integrity, validation_summary, bundle_manifest


def build_validation_summary(
    *,
    schema_path: Path | None,
    preflight_status: str,
    preflight: list[dict],
    schema_status: str,
    sanity_status: str,
    sanity_results: list,
    runtime_status: str,
    runtime_reason: str | None,
    cost_eval: dict,
    env_pin_eval: dict,
    fe_status: str,
    fe_results: list,
    mi_status: str,
    mi_results: list,
    ri_status: str,
    ri_findings: list,
    overall: str,
    integrity: dict,
    validation_errors: list[str],
    parse_error: str | None,
    proc_returncode: int,
    proc_stderr: str,
) -> dict:
    return {
        "schema": _public_path(schema_path) if schema_path else None,
        "preflight_status": preflight_status,
        "preflight": preflight,
        "schema_status": schema_status,
        "sanity_status": sanity_status,
        "sanity_results": sanity_results,
        "runtime_status": runtime_status,
        "runtime_reason": runtime_reason,
        "cost_status": cost_eval["status"],
        "cost_results": cost_eval["results"],
        "env_pin_status": env_pin_eval["status"],
        "env_pin_results": env_pin_eval["results"],
        "factual_echo_status": fe_status,
        "factual_echo_results": fe_results,
        "model_identity_status": mi_status,
        "model_identity_results": mi_results,
        "runtime_integrity_status": ri_status,
        "runtime_integrity_findings": ri_findings,
        "overall_status": overall,
        "integrity_status": integrity["status"],
        "integrity_n_findings": integrity["n_findings"],
        "errors": validation_errors,
        "parse_error": parse_error,
        "exit_code": proc_returncode,
        "stderr_excerpt": _sanitize_public_text(proc_stderr)[:500] if proc_stderr else "",
    }


def write_full_pack(
    *,
    out: Path,
    run_id: str,
    skill_dir: Path,
    fixture: Path,
    integrity: dict,
    script: Path,
    manifest: dict,
    cmd: list[str],
    trace_records: list[dict],
    started_at: str,
    finished_at: str,
    elapsed: float,
    proc_returncode: int,
    output_payload: dict | None,
    cost_profile: dict,
    self_reported_cost: dict,
    cost_eval: dict,
    validation_summary: dict,
    eval_engine_script: Path,
) -> tuple[dict, dict, dict]:
    _write_trace(out, trace_records)
    _write_json(out / "integrity_check.json", integrity)
    _write_json(
        out / "cost_profile.json",
        {
            "measured": cost_profile,
            "self_reported": self_reported_cost,
            "evaluation": cost_eval,
        },
    )

    _write_json(out / "validation_summary.json", validation_summary)
    _write_json(
        out / "runtime_profile.json",
        {
            "started_at": started_at,
            "finished_at": finished_at,
            "elapsed_seconds": elapsed,
            "exit_code": proc_returncode,
            "environment": _runtime_summary(),
        },
    )

    pip_freeze_text = _pip_freeze()
    (out / "environment.lock").write_text(pip_freeze_text)
    bundle_manifest = _bundle_manifest(
        run_id=run_id,
        manifest=manifest,
        skill_dir=skill_dir,
        fixture=fixture,
        script=script,
        command=cmd,
        pip_freeze_text=pip_freeze_text,
        eval_engine_script=eval_engine_script,
    )
    _write_json(out / "manifest.json", bundle_manifest)
    _write_replay(out, script, fixture, manifest, command=cmd)

    if output_payload is not None:
        _write_json(out / "output.json", output_payload)

    lines = [
        "# Workflow Run Record",
        "",
        "- run id: " + run_id,
        "- skill: " + str(manifest.get("id", "?")) + " v" + str(manifest.get("version", "?")),
        "- started: " + started_at,
        "- finished: " + finished_at,
        "- elapsed: " + str(round(elapsed, 3)) + "s",
        "- exit code: " + str(proc_returncode),
        "",
        "## Skill",
        "- dir: " + _public_path(skill_dir),
        "- entrypoint: " + str(script.relative_to(skill_dir)),
        "",
        "## Fixture",
        "- path: " + _public_path(fixture),
        "- sha256: " + bundle_manifest["fixture"]["sha256"],
        "- size: " + str(bundle_manifest["fixture"]["size_bytes"]) + " bytes",
        "",
        "## Validation",
        "- overall: " + validation_summary["overall_status"],
        "- schema: " + validation_summary["schema_status"],
        "- sanity: " + validation_summary["sanity_status"],
        "- runtime: " + validation_summary["runtime_status"],
        "- cost: " + validation_summary["cost_status"],
        "- env_pin: " + validation_summary["env_pin_status"],
        "- integrity: " + validation_summary["integrity_status"],
    ]
    if validation_summary["errors"]:
        lines.append("- errors:")
        for e in validation_summary["errors"]:
            lines.append("  - " + e)
    lines.extend(["", "## Output (excerpt)"])
    if output_payload is not None:
        lines.append(FENCE + "json")
        lines.append(json.dumps(output_payload, indent=2)[:1500])
        lines.append(FENCE)
    elif validation_summary["parse_error"]:
        lines.append("Could not parse skill output: " + validation_summary["parse_error"])
    lines.extend(
        [
            "",
            "## Caveats",
            "- Best-effort replay only; not deterministic across env changes.",
            "- Engineering-time evidence; not clinical or regulatory artefact.",
        ]
    )
    (out / "workflow_run_record.md").write_text("\n".join(lines))
    return integrity, validation_summary, bundle_manifest
