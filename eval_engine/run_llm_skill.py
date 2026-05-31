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

"""LLM-mediated skill runner.

This runner simulates the deployment shape where a user-owned LLM backend
reads `skills/<name>/SKILL.md` and decides to call a local skill tool. The
tool execution is still delegated to `eval_engine/run.py`, so single-skill gates
remain the source of truth for schema/sanity/runtime/cost validation.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4

import typer

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from eval_engine.common import (  # noqa: E402
    FENCE,
    PACK_FORMAT_VERSION,
    _env_lock_fingerprint,
    _now_iso,
    _pip_freeze,
    _public_command,
    _public_path,
    _repo_git_sha,
    _runtime_summary,
    _sha256_path,
)
from eval_engine.evidence import (  # noqa: E402
    PACK_KIND_LLM_SKILL_RUN,
    SKILL_RUN_SUBDIR,
)
from eval_engine.manifest import load_manifest  # noqa: E402
from eval_engine.trace import write_trace_jsonl  # noqa: E402

app = typer.Typer(add_completion=False)

# NVIDIA AI Inference Hub (sk-... keys minted at
# https://inference.nvidia.com/key-management). Default model is
# meta/llama-3.3-70b-instruct because it handles `tool_choice: "required"`
# reliably; gpt-oss-* are reasoning models that behave inconsistently when
# forced to call tools.
NVIDIA_BASE_URL = "https://inference-api.nvidia.com/v1"
NVIDIA_MODEL = "nvidia/meta/llama-3.3-70b-instruct"
NVIDIA_API_KEY_ENV = "NV_INFER_TOKEN"


def _tool_schema() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "run_skill",
                "description": (
                    "Run exactly one local Medical AI Skills skill on the "
                    "provided fixture and write an evidence pack."
                ),
                "parameters": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "skill_dir": {
                            "type": "string",
                            "description": "Path to the approved skill directory.",
                        },
                        "fixture": {
                            "type": "string",
                            "description": "Path to the approved input fixture.",
                        },
                    },
                    "required": ["skill_dir", "fixture"],
                },
            },
        }
    ]


def _build_messages(
    skill_dir: Path, fixture: Path, skill_md: str, manifest_text: str
) -> list[dict]:
    return [
        {
            "role": "system",
            "content": (
                "You are an LLM backend embedded in a medical-imaging agent. "
                "You receive a Markdown skill definition and its manifest. "
                "If the request matches the skill spec, call the run_skill "
                "tool exactly once. Do not make clinical claims, do not invent "
                "inputs, and do not choose paths other than the ones supplied."
            ),
        },
        {
            "role": "user",
            "content": (
                "Evaluate this skill fixture through the local Medical AI Skills tool.\n\n"
                f"Approved skill_dir: {_public_path(skill_dir)}\n"
                f"Approved fixture: {_public_path(fixture)}\n\n"
                "SKILL.md:\n"
                f"{FENCE}markdown\n{skill_md}\n{FENCE}\n\n"
                "skill_manifest.yaml:\n"
                f"{FENCE}yaml\n{manifest_text}\n{FENCE}\n\n"
                "Call run_skill with those exact paths."
            ),
        },
    ]


def _mock_response(skill_dir: Path, fixture: Path, model: str) -> dict:
    return {
        "id": "mock-llm-" + uuid4().hex[:12],
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "index": 0,
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_mock_run_skill",
                            "type": "function",
                            "function": {
                                "name": "run_skill",
                                "arguments": json.dumps(
                                    {
                                        "skill_dir": _public_path(skill_dir),
                                        "fixture": _public_path(fixture),
                                    }
                                ),
                            },
                        }
                    ],
                },
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def _chat_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return base + "/chat/completions"


def _call_openai_compatible(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict],
    tools: list[dict],
    temperature: float,
    max_tokens: int,
    timeout_seconds: int,
) -> dict:
    body = {
        "model": model,
        "messages": messages,
        "tools": tools,
        # NVIDIA's model reference exposes `tool_choice` as an enum. Because
        # there is only one tool, `required` is enough to force a tool call
        # while staying compatible with stricter OpenAI-compatible servers.
        "tool_choice": "required",
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        _chat_url(base_url),
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        excerpt = e.read()[:1000].decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM backend HTTP {e.code} {e.reason}: {excerpt}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"LLM backend network error: {e.reason}") from e


def _extract_tool_call(resp: dict) -> dict:
    try:
        msg = resp["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as e:
        raise ValueError("LLM response has no choices[0].message") from e

    tool_calls = msg.get("tool_calls") or []
    if tool_calls:
        call = tool_calls[0]
        fn = call.get("function") or {}
        name = fn.get("name")
        raw_args = fn.get("arguments") or "{}"
        if isinstance(raw_args, str):
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError as e:
                raise ValueError(f"tool call arguments are not JSON: {e}") from e
        elif isinstance(raw_args, dict):
            args = raw_args
        else:
            raise ValueError("tool call arguments are neither JSON string nor object")
        return {
            "id": call.get("id"),
            "type": call.get("type", "function"),
            "name": name,
            "arguments": args,
            "raw_arguments": raw_args,
        }

    content = msg.get("content")
    if isinstance(content, str) and content.strip():
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict) and payload.get("name") == "run_skill":
            return {
                "id": None,
                "type": "function",
                "name": payload.get("name"),
                "arguments": payload.get("arguments") or {},
                "raw_arguments": payload,
            }

    raise ValueError("LLM did not return a run_skill tool call")


def _resolve_tool_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def _validate_tool_call(tool_call: dict, skill_dir: Path, fixture: Path) -> list[str]:
    errors = []
    if tool_call.get("name") != "run_skill":
        errors.append(f"expected tool name run_skill, got {tool_call.get('name')!r}")
    args = tool_call.get("arguments") or {}
    if _resolve_tool_path(str(args.get("skill_dir") or "")) != skill_dir:
        errors.append("tool call used a skill_dir other than the approved path")
    if _resolve_tool_path(str(args.get("fixture") or "")) != fixture:
        errors.append("tool call used a fixture other than the approved path")
    return errors


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


@app.command()
def main(
    skill_dir: Path = typer.Argument(..., exists=True, file_okay=False),
    fixture: Path = typer.Option(..., "--fixture"),
    out: Path = typer.Option(..., "--out", help="LLM-mediated evidence-pack output directory"),
    backend: str = typer.Option(
        "mock",
        "--backend",
        help="mock, nvidia, or openai-compatible",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help=(
            "Model id. Defaults to nvidia/meta/llama-3.3-70b-instruct for "
            "--backend nvidia (see NVIDIA_MODEL)."
        ),
    ),
    base_url: str | None = typer.Option(
        None,
        "--base-url",
        help="OpenAI-compatible base URL. Defaults to https://inference-api.nvidia.com/v1 for nvidia.",
    ),
    api_key_env: str | None = typer.Option(
        None,
        "--api-key-env",
        help="Environment variable that stores the backend API key.",
    ),
    temperature: float = typer.Option(0.0, "--temperature"),
    max_tokens: int = typer.Option(512, "--max-tokens"),
    timeout_seconds: int = typer.Option(60, "--timeout-seconds"),
) -> None:
    skill_dir = skill_dir.resolve()
    fixture = fixture.resolve()
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    backend = backend.strip().lower()
    if backend not in {"mock", "nvidia", "openai-compatible"}:
        raise typer.BadParameter("backend must be one of: mock, nvidia, openai-compatible")

    if backend == "nvidia":
        resolved_model = model or os.environ.get("NVIDIA_MODEL") or NVIDIA_MODEL
        resolved_base_url = base_url or os.environ.get("NVIDIA_BASE_URL") or NVIDIA_BASE_URL
        resolved_api_key_env = api_key_env or NVIDIA_API_KEY_ENV
    elif backend == "openai-compatible":
        resolved_model = model or os.environ.get("LLM_MODEL")
        resolved_base_url = base_url or os.environ.get("LLM_BASE_URL")
        resolved_api_key_env = api_key_env or "LLM_API_KEY"
    else:
        resolved_model = model or "mock-skill-caller"
        resolved_base_url = base_url or "mock://local"
        resolved_api_key_env = api_key_env or ""

    if not resolved_model:
        raise typer.BadParameter(
            "--model is required for openai-compatible unless LLM_MODEL is set"
        )
    if backend != "mock" and not resolved_base_url:
        raise typer.BadParameter(
            "--base-url is required for openai-compatible unless LLM_BASE_URL is set"
        )

    pack_command = [
        sys.executable,
        str(Path(__file__).resolve()),
        str(skill_dir),
        "--fixture",
        str(fixture),
        "--out",
        str(out),
        "--backend",
        backend,
        "--model",
        resolved_model,
        "--base-url",
        resolved_base_url,
    ]
    if resolved_api_key_env:
        pack_command.extend(["--api-key-env", resolved_api_key_env])

    manifest_path = skill_dir / "skill_manifest.yaml"
    manifest = load_manifest(manifest_path)
    skill_md_path = skill_dir / "SKILL.md"
    skill_md = skill_md_path.read_text()
    manifest_text = manifest_path.read_text()
    tools = _tool_schema()
    messages = _build_messages(skill_dir, fixture, skill_md, manifest_text)

    run_id = uuid4().hex[:12]
    llm_started_at = _now_iso()
    t0 = time.perf_counter()
    error = None
    raw_response = None
    tool_call = None
    validation_errors: list[str] = []

    trace_records = [
        {
            "ts": llm_started_at,
            "kind": "llm_call_start",
            "backend": backend,
            "model": resolved_model,
            "base_url": resolved_base_url,
            "skill_markdown": _public_path(skill_md_path),
        }
    ]

    try:
        if backend == "mock":
            raw_response = _mock_response(skill_dir, fixture, resolved_model)
        else:
            api_key = os.environ.get(resolved_api_key_env, "")
            if not api_key:
                raise RuntimeError(f"{resolved_api_key_env} is not set")
            raw_response = _call_openai_compatible(
                base_url=resolved_base_url,
                api_key=api_key,
                model=resolved_model,
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout_seconds=timeout_seconds,
            )
        tool_call = _extract_tool_call(raw_response)
        validation_errors = _validate_tool_call(tool_call, skill_dir, fixture)
    except Exception as e:
        error = str(e)

    llm_elapsed = time.perf_counter() - t0
    llm_finished_at = _now_iso()
    usage = (raw_response or {}).get("usage") or {}
    trace_records.append(
        {
            "ts": llm_finished_at,
            "kind": "llm_call_end",
            "backend": backend,
            "model": resolved_model,
            "elapsed_s": llm_elapsed,
            "tool_call_present": tool_call is not None,
            "usage": usage,
            "error": error,
        }
    )

    skill_out = out / SKILL_RUN_SUBDIR
    proc = None
    if tool_call is not None and not validation_errors and error is None:
        cmd = [
            sys.executable,
            str(REPO_ROOT / "eval_engine" / "run.py"),
            str(skill_dir),
            "--fixture",
            str(fixture),
            "--out",
            str(skill_out),
        ]
        tool_started_at = _now_iso()
        trace_records.append(
            {
                "ts": tool_started_at,
                "kind": "tool_call_start",
                "tool": "run_skill",
                "command": _public_command(cmd),
                "cwd": _public_path(REPO_ROOT),
                "args": tool_call.get("arguments"),
            }
        )
        tool_t0 = time.perf_counter()
        proc = subprocess.run(cmd, capture_output=True, text=True)
        tool_elapsed = time.perf_counter() - tool_t0
        trace_records.append(
            {
                "ts": _now_iso(),
                "kind": "tool_call_end",
                "tool": "run_skill",
                "exit_code": proc.returncode,
                "elapsed_s": tool_elapsed,
                "stdout_bytes": len(proc.stdout),
                "stderr_bytes": len(proc.stderr),
            }
        )

    write_trace_jsonl(out / "agent_run_trace.jsonl", trace_records)

    llm_interaction = {
        "backend": backend,
        "model": resolved_model,
        "base_url": resolved_base_url,
        "api_key_env": resolved_api_key_env or None,
        "skill_markdown": {
            "path": _public_path(skill_md_path),
            "sha256": _sha256_path(skill_md_path),
            "chars": len(skill_md),
        },
        "manifest": {
            "path": _public_path(manifest_path),
            "sha256": _sha256_path(manifest_path),
        },
        "messages": messages,
        "tools": tools,
        "tool_call": tool_call,
        "raw_response": raw_response,
        "usage": usage,
        "error": error,
        "validation_errors": validation_errors,
    }
    _write_json(out / "llm_interaction.json", llm_interaction)

    pip_freeze_text = _pip_freeze()
    (out / "environment.lock").write_text(pip_freeze_text)
    env_fingerprint = _env_lock_fingerprint(pip_freeze_text)

    skill_validation = (
        _read_json(skill_out / "validation_summary.json") if skill_out.exists() else None
    )
    skill_output = _read_json(skill_out / "output.json") if skill_out.exists() else None
    skill_overall = (skill_validation or {}).get("overall_status")

    if error:
        overall = "failed (llm_backend)"
    elif validation_errors:
        overall = "failed (llm_tool_call)"
    elif proc is None:
        overall = "failed (tool_not_executed)"
    elif proc.returncode != 0:
        overall = "failed (skill_run)"
    elif skill_overall != "passed":
        overall = "failed (skill_validation)"
    else:
        overall = "passed"

    validation_summary = {
        "preflight_status": "skipped",
        "preflight": [],
        "schema_status": "skipped",
        "sanity_status": "skipped",
        "sanity_results": [],
        "llm_status": "failed" if error else "tool_called" if tool_call else "no_tool_call",
        "llm_backend": backend,
        "llm_model": resolved_model,
        "llm_base_url": resolved_base_url,
        "tool_call_status": "passed" if tool_call and not validation_errors else "failed",
        "tool_call_errors": validation_errors,
        "skill_pack": SKILL_RUN_SUBDIR if skill_out.exists() else None,
        "skill_overall_status": skill_overall,
        "overall_status": overall,
        "integrity_status": "skipped",
        "integrity_n_findings": 0,
        "errors": ([error] if error else []) + validation_errors,
        "exit_code": proc.returncode if proc is not None else 2,
    }
    _write_json(out / "validation_summary.json", validation_summary)

    _write_json(
        out / "cost_profile.json",
        {
            "measured": {
                "llm_wall_seconds": llm_elapsed,
                "llm_tokens_input": usage.get("prompt_tokens", 0),
                "llm_tokens_output": usage.get("completion_tokens", 0),
                "llm_tokens_total": usage.get("total_tokens", 0),
            },
            "self_reported": usage,
            "evaluation": {"status": "skipped", "results": []},
        },
    )

    _write_json(
        out / "runtime_profile.json",
        {
            "started_at": llm_started_at,
            "finished_at": _now_iso(),
            "elapsed_seconds": llm_elapsed,
            "exit_code": validation_summary["exit_code"],
            "environment": _runtime_summary(),
        },
    )

    _write_json(
        out / "integrity_check.json",
        {
            "status": "delegated",
            "findings": [],
            "n_findings": 0,
            "nested_path": "skill_run/integrity_check.json" if skill_out.exists() else None,
        },
    )

    runtime_env = _runtime_summary()
    _write_json(
        out / "manifest.json",
        {
            "pack_format_version": PACK_FORMAT_VERSION,
            "pack_kind": PACK_KIND_LLM_SKILL_RUN,
            "run_id": run_id,
            "runner": "eval_engine/run_llm_skill.py",
            "skill_id": manifest.get("id"),
            "skill_version": manifest.get("version"),
            "skill_dir": _public_path(skill_dir),
            "repo_git_sha": _repo_git_sha(),
            "fixture": {
                "path": _public_path(fixture),
                "sha256": _sha256_path(fixture),
                "is_dir": fixture.is_dir(),
            },
            "llm": {
                "backend": backend,
                "model": resolved_model,
                "base_url": resolved_base_url,
                "api_key_env": resolved_api_key_env or None,
                "skill_markdown_path": _public_path(skill_md_path),
                "skill_markdown_sha256": _sha256_path(skill_md_path),
            },
            "environment": {
                "fingerprint": env_fingerprint,
                "pip_freeze_lines": pip_freeze_text.count("\n"),
                "pip_freeze_path": "environment.lock",
                "python_version": runtime_env["python_version"],
                "platform": runtime_env["platform"],
            },
            "nested_skill_pack": SKILL_RUN_SUBDIR if skill_out.exists() else None,
            "command": _public_command(pack_command),
            "eval_engine_script": _public_path(Path(__file__).resolve()),
        },
    )

    _write_json(
        out / "output.json",
        {
            "llm": {
                "backend": backend,
                "model": resolved_model,
                "tool_call": tool_call,
                "usage": usage,
            },
            "skill_pack": SKILL_RUN_SUBDIR if skill_out.exists() else None,
            "skill_output": skill_output,
        },
    )

    replay_cmd = [
        "python3",
        "eval_engine/run_llm_skill.py",
        shlex.quote(_public_path(skill_dir)),
        "--fixture",
        shlex.quote(_public_path(fixture)),
        "--out",
        shlex.quote(_public_path(out)),
        "--backend",
        shlex.quote(backend),
        "--model",
        shlex.quote(resolved_model),
        "--base-url",
        shlex.quote(resolved_base_url),
    ]
    if resolved_api_key_env:
        replay_cmd.extend(["--api-key-env", shlex.quote(resolved_api_key_env)])
    replay = (
        "#!/usr/bin/env bash\n"
        "# Auto-generated LLM-mediated replay. Requires the same backend env vars.\n"
        "set -euo pipefail\n"
        'SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"\n'
        'REPO_ROOT="$SCRIPT_DIR"\n'
        'while [ ! -e "$REPO_ROOT/Makefile" ] && [ "$REPO_ROOT" != "/" ]; do\n'
        '  REPO_ROOT="$(dirname "$REPO_ROOT")"\n'
        "done\n"
        '[ -e "$REPO_ROOT/Makefile" ] || { echo "could not find repo root"; exit 1; }\n'
        'cd "$REPO_ROOT"\n' + " ".join(replay_cmd) + "\n"
    )
    replay_path = out / "replay.sh"
    replay_path.write_text(replay)
    replay_path.chmod(0o755)

    lines = [
        "# Workflow Run Record",
        "",
        "- run id: " + run_id,
        "- runner: LLM-mediated skill runner",
        "- backend: " + backend,
        "- model: " + resolved_model,
        "- skill: " + str(manifest.get("id", "?")) + " v" + str(manifest.get("version", "?")),
        "- fixture: " + _public_path(fixture),
        "- overall: " + overall,
        "",
        "## LLM Interaction",
        "- skill markdown: " + _public_path(skill_md_path),
        "- tool call: " + ("run_skill" if tool_call else "none"),
        "- interaction record: llm_interaction.json",
        "",
        "## Nested Skill Pack",
        "- path: " + (SKILL_RUN_SUBDIR if skill_out.exists() else "not produced"),
        "- nested overall: " + str(skill_overall),
        "",
        "## Caveats",
        "- Engineering-time evidence; not clinical or regulatory artefact.",
        "- Cursor-style interactive backends are represented by the recorded prompt/tool spec, not driven directly.",
    ]
    (out / "workflow_run_record.md").write_text("\n".join(lines) + "\n")

    typer.echo("llm evidence pack: " + str(out))
    typer.echo("  backend: " + backend)
    typer.echo("  model: " + resolved_model)
    typer.echo("  llm_status: " + validation_summary["llm_status"])
    typer.echo("  tool_call: " + validation_summary["tool_call_status"])
    typer.echo("  nested_skill: " + str(skill_overall))
    typer.echo("  overall: " + overall)
    if overall != "passed":
        raise typer.Exit(validation_summary["exit_code"] or 1)


if __name__ == "__main__":
    app()
