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

"""Run one paired with-skill / without-skill validation scenario."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shlex
import shutil
import sys
import time
from pathlib import Path
from uuid import uuid4

import jsonschema
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from eval_engine.common import (  # noqa: E402
    PACK_FORMAT_VERSION,
    _env_lock_fingerprint,
    _now_iso,
    _path_size,
    _pip_freeze,
    _public_command,
    _public_path,
    _repo_git_sha,
    _runtime_summary,
    _sha256_path,
    _skill_dir_files,
)
from eval_engine.evidence import PACK_KIND_PAIRED_EVAL  # noqa: E402
from eval_engine.trace import write_trace_jsonl  # noqa: E402
from tools.validate_skill.grader import grade_assertions  # noqa: E402

SCHEMA_PATH = REPO_ROOT / "spec" / "scenario.schema.json"


class ScenarioError(Exception):
    """Framework error that should exit 2."""


def _eprint(message: str) -> None:
    print(message, file=sys.stderr)


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        raise ScenarioError(f"scenario not found: {_public_path(path)}")
    if not path.is_file():
        raise ScenarioError(f"scenario is not a file: {_public_path(path)}")
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        raise ScenarioError(f"scenario YAML parse error: {e}") from e
    if not isinstance(data, dict):
        raise ScenarioError("scenario YAML must be a mapping")
    return data


def _looks_like_evidence_pack(payload: dict) -> bool:
    return any(key in payload for key in ("pack_kind", "run_id", "pack_format_version"))


def _validate_schema(payload: dict) -> None:
    schema = json.loads(SCHEMA_PATH.read_text())
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
    if errors:
        lines = ["scenario schema validation failed:"]
        for err in errors:
            where = ".".join(str(part) for part in err.absolute_path) or "<root>"
            lines.append(f"- {where}: {err.message}")
        raise ScenarioError("\n".join(lines))


def _resolve_repo_path(raw: str, *, field: str) -> Path:
    candidate = (REPO_ROOT / raw).resolve()
    try:
        candidate.relative_to(REPO_ROOT)
    except ValueError as e:
        raise ScenarioError(f"{field} must stay inside the repo: {raw}") from e
    return candidate


def _semantic_checks(
    scenario_path: Path, scenario: dict, backend_override: str | None
) -> tuple[Path, Path, list[Path], list[Path], str]:
    skill = scenario["skill"]
    expected_dir = (REPO_ROOT / "skills" / skill / "evals").resolve()
    try:
        scenario_path.resolve().relative_to(expected_dir)
    except ValueError as e:
        raise ScenarioError(
            f"scenario path must live under skills/{skill}/evals/: {_public_path(scenario_path)}"
        ) from e

    fixture = _resolve_repo_path(scenario["fixture"], field="fixture")
    if not fixture.exists():
        raise ScenarioError(f"fixture not found: {scenario['fixture']}")

    with_docs = [
        _resolve_repo_path(p, field="with_skill_docs") for p in scenario["with_skill_docs"]
    ]
    without_docs = [
        _resolve_repo_path(p, field="without_skill_docs") for p in scenario["without_skill_docs"]
    ]
    for doc in with_docs + without_docs:
        if not doc.is_file():
            raise ScenarioError(f"doc path not found: {_public_path(doc)}")

    scenario_backend = (scenario.get("backend") or {}).get("name")
    effective_backend = backend_override or os.environ.get("LLM_BACKEND") or scenario_backend
    if effective_backend != "mock":
        raise ScenarioError(f"live backends are out of scope for v0: {effective_backend}")

    return REPO_ROOT / "skills" / skill, fixture, with_docs, without_docs, effective_backend


def _read_doc_bundle(paths: list[Path]) -> tuple[str, list[str], str]:
    chunks = []
    public_paths = []
    for path in paths:
        public = _public_path(path)
        public_paths.append(public)
        chunks.append(f"--- {public} ---\n{path.read_text()}")
    text = "\n\n".join(chunks)
    digest = hashlib.sha256(text.encode()).hexdigest()
    return text, public_paths, digest


def _mock_response(scenario_id: str, arm: str, fixture: Path) -> tuple[str, dict]:
    if scenario_id != "extract-modality-and-phi-flag":
        raise ScenarioError(f"mock response not defined for scenario: {scenario_id}")

    if arm == "with_skill":
        payload = {
            "path": _public_path(fixture),
            "transfer_syntax": {
                "uid": "1.2.840.10008.1.2.1",
                "name": "Explicit VR Little Endian",
            },
            "modality": "CT",
            "study": {
                "StudyInstanceUID": "1.2.826.0.1.3680043.8.498.2026052401",
                "StudyDate": "20260524",
                "StudyTime": "101010",
                "StudyDescription": "Synthetic CT",
                "AccessionNumber": "SYNTHETIC",
            },
            "series": {
                "SeriesInstanceUID": "1.2.826.0.1.3680043.8.498.2026052402",
                "SeriesNumber": "1",
                "SeriesDescription": "Synthetic abdomen",
                "Modality": "CT",
                "BodyPartExamined": "ABDOMEN",
            },
            "image": {
                "SOPInstanceUID": "1.2.826.0.1.3680043.8.498.2026052403",
                "InstanceNumber": "1",
                "Rows": 16,
                "Columns": 16,
                "BitsAllocated": 16,
                "PixelRepresentation": 1,
                "PhotometricInterpretation": "MONOCHROME2",
                "NumberOfFrames": None,
            },
            "phi_present": True,
            "phi_tags_found": ["PatientName", "PatientID"],
            "phi_scope_disclaimer": (
                "Standard DICOM PS3.15 basic-profile tags only. "
                "Private tags (odd group) NOT checked. "
                "Burnt-in pixel text NOT detected. "
                "Use a proper de-identifier for clinical or regulatory work."
            ),
        }
        return json.dumps(payload, indent=2), {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    if arm == "without_skill":
        text = (
            "The file appears to be a CT DICOM. I would inspect the header for "
            "the study UID and patient fields before sharing it externally."
        )
        return text, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    raise ScenarioError(f"unknown arm: {arm}")


def _parse_json_response(text: str) -> tuple[dict | None, str | None]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as e:
        return None, str(e)
    return payload if isinstance(payload, dict) else None, None


def _run_arm(scenario: dict, arm: str, fixture: Path, doc_paths: list[Path]) -> dict:
    started = time.perf_counter()
    doc_bundle, public_docs, doc_digest = _read_doc_bundle(doc_paths)
    response_text, usage = _mock_response(scenario["scenario_id"], arm, fixture)
    parsed_json, parse_error = _parse_json_response(response_text)
    assertion_results = grade_assertions(
        scenario["assertions"],
        response_text=response_text,
        parsed_json=parsed_json,
    )
    elapsed = time.perf_counter() - started
    return {
        "arm": arm,
        "task": scenario["task"],
        "fixture": _public_path(fixture),
        "doc_paths": public_docs,
        "doc_bundle_sha256": doc_digest,
        "doc_bundle_chars": len(doc_bundle),
        "response_text": response_text,
        "parsed_json": parsed_json,
        "parse_error": parse_error,
        "assertions": assertion_results,
        "assertions_passed": sum(1 for item in assertion_results if item["pass"]),
        "assertions_failed": sum(1 for item in assertion_results if not item["pass"]),
        "usage": usage,
        "elapsed_seconds": round(elapsed, 6),
    }


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2))


def _write_jsonl(path: Path, records: list[dict]) -> None:
    write_trace_jsonl(path, records)


def _render_table(results: list[dict]) -> list[str]:
    lines = ["| Assertion | Kind | Result | Detail |", "|---|---|---|---|"]
    for result in results:
        status = "pass" if result["pass"] else "fail"
        detail = str(result["detail"]).replace("\n", " ")
        lines.append(f"| `{result['id']}` | `{result['kind']}` | {status} | {detail} |")
    return lines


def _excerpt(text: str, limit: int = 1200) -> str:
    return text if len(text) <= limit else text[:limit].rstrip() + "\n..."


def _render_report(
    scenario: dict, backend: str, with_arm: dict, without_arm: dict, overall: str
) -> str:
    lines = [
        "# Paired Eval Report (mock backend; runner mechanics only, not behavioral validation)",
        "",
        f"- scenario: `{scenario['scenario_id']}`",
        f"- skill: `{scenario['skill']}`",
        f"- backend: `{backend}`",
        f"- overall: `{overall}`",
        "",
        "## With Skill Assertions",
        *_render_table(with_arm["assertions"]),
        "",
        "## Without Skill Assertions",
        *_render_table(without_arm["assertions"]),
        "",
        "## With Skill Response Excerpt",
        "```json",
        _excerpt(with_arm["response_text"]),
        "```",
        "",
        "## Without Skill Response Excerpt",
        "```text",
        _excerpt(without_arm["response_text"]),
        "```",
    ]
    return "\n".join(lines) + "\n"


def _replay_text(scenario_path: Path, out_root: Path, backend: str) -> str:
    cmd = [
        "python3",
        "-m",
        "tools.validate_skill.run",
        _public_path(scenario_path),
        "--out",
        _public_path(out_root),
        "--backend",
        backend,
    ]
    return (
        "#!/usr/bin/env bash\n"
        "# Auto-generated paired-eval replay. Best-effort; compare environment.lock.\n"
        "set -euo pipefail\n"
        'SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"\n'
        'REPO_ROOT="$SCRIPT_DIR"\n'
        'while [ ! -e "$REPO_ROOT/Makefile" ] && [ "$REPO_ROOT" != "/" ]; do\n'
        '  REPO_ROOT="$(dirname "$REPO_ROOT")"\n'
        "done\n"
        '[ -e "$REPO_ROOT/Makefile" ] || { echo "could not find repo root (looked for Makefile)"; exit 1; }\n'
        'cd "$REPO_ROOT"\n' + " ".join(shlex.quote(part) for part in cmd) + "\n"
    )


def _write_pack(
    *,
    scenario_path: Path,
    scenario: dict,
    skill_dir: Path,
    fixture: Path,
    out_root: Path,
    backend: str,
    started_at: str,
    finished_at: str,
    elapsed: float,
    with_arm: dict,
    without_arm: dict,
    report: str,
    command: list[str],
) -> Path:
    pack_dir = out_root / scenario["scenario_id"]
    if pack_dir.exists():
        shutil.rmtree(pack_dir)
    (pack_dir / "arms").mkdir(parents=True, exist_ok=True)

    with_pass = with_arm["assertions_failed"] == 0
    without_lift = without_arm["assertions_failed"] > 0
    paired_status = "passed" if with_pass and without_lift else "failed"
    overall = "passed" if paired_status == "passed" else "failed (paired_eval)"

    pip_freeze_text = _pip_freeze()
    (pack_dir / "environment.lock").write_text(pip_freeze_text)

    manifest = {
        "pack_format_version": PACK_FORMAT_VERSION,
        "pack_kind": PACK_KIND_PAIRED_EVAL,
        "run_id": uuid4().hex[:12],
        "skill_id": f"medagent.{scenario['skill'].replace('-', '_')}",
        "skill_version": None,
        "skill_dir": _public_path(skill_dir),
        "repo_git_sha": _repo_git_sha(),
        "environment": {
            "fingerprint": _env_lock_fingerprint(pip_freeze_text),
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
        "scenario": {
            "path": _public_path(scenario_path),
            "id": scenario["scenario_id"],
            "schema_version": scenario["schema_version"],
        },
        "backend": {"name": backend},
        "command": _public_command(command),
        "eval_engine_script": _public_path(Path(__file__).resolve()),
    }
    _write_json(pack_dir / "manifest.json", manifest)

    validation_summary = {
        "schema": _public_path(SCHEMA_PATH),
        "preflight_status": "passed",
        "preflight": [],
        "schema_status": "passed",
        "sanity_status": "passed" if paired_status == "passed" else "failed",
        "sanity_results": with_arm["assertions"] + without_arm["assertions"],
        "runtime_status": "completed",
        "runtime_reason": None,
        "cost_status": "skipped",
        "cost_results": [],
        "env_pin_status": "skipped",
        "env_pin_results": [],
        "factual_echo_status": "skipped",
        "factual_echo_results": [],
        "model_identity_status": "skipped",
        "model_identity_results": [],
        "runtime_integrity_status": "skipped",
        "runtime_integrity_findings": [],
        "overall_status": overall,
        "integrity_status": "skipped",
        "integrity_n_findings": 0,
        "errors": [],
        "parse_error": None,
        "exit_code": 0,
        "stderr_excerpt": "",
        "paired_eval_status": paired_status,
        "with_skill_assertions_passed": with_arm["assertions_passed"],
        "with_skill_assertions_failed": with_arm["assertions_failed"],
        "without_skill_assertions_passed": without_arm["assertions_passed"],
        "without_skill_assertions_failed": without_arm["assertions_failed"],
    }
    _write_json(pack_dir / "validation_summary.json", validation_summary)

    _write_json(
        pack_dir / "runtime_profile.json",
        {
            "started_at": started_at,
            "finished_at": finished_at,
            "elapsed_seconds": elapsed,
            "exit_code": 0,
            "environment": _runtime_summary(),
        },
    )
    _write_json(
        pack_dir / "cost_profile.json",
        {
            "measured": {
                "wall_seconds": elapsed,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            "self_reported": {},
            "evaluation": {"status": "skipped", "results": []},
        },
    )
    _write_json(
        pack_dir / "integrity_check.json", {"status": "skipped", "findings": [], "n_findings": 0}
    )
    _write_json(pack_dir / "arms" / "with_skill.json", with_arm)
    _write_json(pack_dir / "arms" / "without_skill.json", without_arm)

    trace = [
        {"ts": started_at, "kind": "scenario_start", "scenario_id": scenario["scenario_id"]},
        {"ts": started_at, "kind": "arm_start", "arm": "with_skill"},
        {
            "ts": finished_at,
            "kind": "arm_end",
            "arm": "with_skill",
            "assertions_failed": with_arm["assertions_failed"],
        },
        {"ts": started_at, "kind": "arm_start", "arm": "without_skill"},
        {
            "ts": finished_at,
            "kind": "arm_end",
            "arm": "without_skill",
            "assertions_failed": without_arm["assertions_failed"],
        },
        {"ts": finished_at, "kind": "scenario_end", "overall_status": overall},
    ]
    _write_jsonl(pack_dir / "agent_run_trace.jsonl", trace)

    workflow_lines = [
        "# Workflow Run Record",
        "",
        "- run id: " + manifest["run_id"],
        "- scenario: " + scenario["scenario_id"],
        "- skill: " + scenario["skill"],
        "- started: " + started_at,
        "- finished: " + finished_at,
        "- elapsed: " + str(round(elapsed, 3)) + "s",
        "- backend: " + backend,
        "- overall: " + overall,
        "",
        "## Caveats",
        "- Mock backend validates runner mechanics only, not live agent capability.",
        "- Engineering-time evidence; not clinical or regulatory artefact.",
    ]
    (pack_dir / "workflow_run_record.md").write_text("\n".join(workflow_lines) + "\n")
    (pack_dir / "paired_eval.md").write_text(report)
    replay = pack_dir / "replay.sh"
    replay.write_text(_replay_text(scenario_path, out_root, backend))
    replay.chmod(0o755)
    return pack_dir


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m tools.validate_skill.run",
        description="Run one paired with-skill / without-skill validation scenario.",
    )
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "runs" / "validate_skill")
    parser.add_argument("--backend", default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    scenario_path = args.scenario
    if not scenario_path.is_absolute():
        scenario_path = (REPO_ROOT / scenario_path).resolve()
    out_root = args.out if args.out.is_absolute() else (REPO_ROOT / args.out).resolve()

    try:
        scenario = _load_yaml(scenario_path)
        if _looks_like_evidence_pack(scenario):
            raise ScenarioError("this looks like an evidence pack, not a scenario YAML")
        _validate_schema(scenario)
        skill_dir, fixture, with_docs, without_docs, backend = _semantic_checks(
            scenario_path,
            scenario,
            args.backend,
        )

        started_at = _now_iso()
        start = time.perf_counter()
        with_arm = _run_arm(scenario, "with_skill", fixture, with_docs)
        without_arm = _run_arm(scenario, "without_skill", fixture, without_docs)
        elapsed = time.perf_counter() - start
        finished_at = _now_iso()

        with_pass = with_arm["assertions_failed"] == 0
        without_lift = without_arm["assertions_failed"] > 0
        overall = "passed" if with_pass and without_lift else "failed (paired_eval)"
        report = _render_report(scenario, backend, with_arm, without_arm, overall)
        command = [
            sys.executable,
            "-m",
            "tools.validate_skill.run",
            str(scenario_path),
            "--out",
            str(out_root),
            "--backend",
            backend,
        ]
        _write_pack(
            scenario_path=scenario_path,
            scenario=scenario,
            skill_dir=skill_dir,
            fixture=fixture,
            out_root=out_root,
            backend=backend,
            started_at=started_at,
            finished_at=finished_at,
            elapsed=round(elapsed, 6),
            with_arm=with_arm,
            without_arm=without_arm,
            report=report,
            command=command,
        )
        print(report, end="")
        return 0
    except ScenarioError as e:
        _eprint(str(e))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
