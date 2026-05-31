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

"""Repeat-run reproducibility audit for skill and verifier specs.

The completeness verifier checks that a spec declares provenance anchors.
This audit checks the executable side: every spec must declare a
``validation.reproducibility`` policy, and specs marked ``mode: repeat`` are
run twice through ``eval_engine/run.py`` on the declared fixture. The two
packs must agree on gate statuses, semantic output payload, and hashes of
emitted artifact paths.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from eval_engine.manifest import iter_spec_dirs, load_manifest  # noqa: E402
from eval_engine.preflight import _environment_preflight, _preflight_checks  # noqa: E402

RUNNER = REPO_ROOT / "eval_engine" / "run.py"
OUT_ROOT_DEFAULT = REPO_ROOT / "runs" / "reproducibility_audit"
SUMMARY_NAME = "_summary.json"

VALID_MODES = {"repeat", "preflight"}
DEFAULT_EXPECTED_STATUS = {"repeat": "passed"}
STATUS_KEYS = (
    "preflight_status",
    "schema_status",
    "sanity_status",
    "runtime_status",
    "cost_status",
    "env_pin_status",
    "factual_echo_status",
    "model_identity_status",
    "runtime_integrity_status",
    "integrity_status",
    "overall_status",
)
DEFAULT_IGNORE_PATTERNS = (
    r"^runtime(\.|$)",
    r"^environment(\.|$)",
    r"^logs(\.|$)",
    r"(^|\.)command$",
    r"(^|\.)commands(\.|$)",
    r"(^|\.)cwd$",
    r"(^|\.)path$",
    r"(^|\.)input_dir$",
    r"(^|\.)output_dir$",
    r"(^|\.)recording_output_dir$",
    r"(^|\.)log_path$",
    r".*_path$",
    r".*_dir$",
    r"(^|\.)request_id$",
    r"(^|\.)system_fingerprint$",
)
ARTIFACT_PATH_KEY_RE = re.compile(
    r"(^|_)(path|file|ckpt|checkpoint)$|" r"(_path|_file|_ckpt|_checkpoint)$"
)
ARTIFACT_SKIP_PREFIXES = ("runtime.", "logs.")


def _target_label(spec_dir: Path) -> str:
    if spec_dir.parent.name == "verifiers":
        return "verifiers_" + spec_dir.name
    return spec_dir.name


def _public_rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def _compile_patterns(extra: list[str] | None = None) -> list[re.Pattern[str]]:
    return [re.compile(p) for p in (*DEFAULT_IGNORE_PATTERNS, *(extra or []))]


def _is_ignored(path: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(pattern.search(path) for pattern in patterns)


def _scrub_payload(
    value: Any,
    *,
    patterns: list[re.Pattern[str]],
    path: str = "",
) -> Any:
    if path and _is_ignored(path, patterns):
        return "<ignored>"
    if isinstance(value, dict):
        out = {}
        for key, child in sorted(value.items()):
            child_path = f"{path}.{key}" if path else str(key)
            scrubbed = _scrub_payload(child, patterns=patterns, path=child_path)
            if scrubbed != "<ignored>":
                out[str(key)] = scrubbed
        return out
    if isinstance(value, list):
        return [
            _scrub_payload(item, patterns=patterns, path=f"{path}[{idx}]")
            for idx, item in enumerate(value)
        ]
    return value


def _dotted_diffs(a: Any, b: Any, prefix: str = "") -> list[dict[str, Any]]:
    if isinstance(a, dict) and isinstance(b, dict):
        diffs: list[dict[str, Any]] = []
        for key in sorted(set(a) | set(b)):
            path = f"{prefix}.{key}" if prefix else str(key)
            diffs.extend(_dotted_diffs(a.get(key), b.get(key), path))
        return diffs
    if isinstance(a, list) and isinstance(b, list):
        diffs = []
        for idx in range(max(len(a), len(b))):
            path = f"{prefix}[{idx}]"
            left = a[idx] if idx < len(a) else "<missing>"
            right = b[idx] if idx < len(b) else "<missing>"
            diffs.extend(_dotted_diffs(left, right, path))
        return diffs
    if a != b:
        return [{"path": prefix, "run_1": a, "run_2": b}]
    return []


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _hash_artifact(path: Path) -> dict[str, Any]:
    if path.is_file():
        return {
            "kind": "file",
            "size_bytes": path.stat().st_size,
            "sha256": _sha256_file(path),
        }
    if path.is_dir():
        files = [p for p in sorted(path.rglob("*")) if p.is_file()]
        h = hashlib.sha256()
        for child in files:
            rel = child.relative_to(path).as_posix()
            h.update(rel.encode("utf-8"))
            h.update(b"\0")
            h.update(_sha256_file(child).encode("ascii"))
            h.update(b"\0")
        return {
            "kind": "directory",
            "file_count": len(files),
            "sha256": h.hexdigest(),
        }
    raise FileNotFoundError(path)


def _resolve_artifact(value: str, *, pack_dir: Path) -> Path | None:
    if not value or len(value) > 4096:
        return None
    candidates: list[Path] = []
    raw = Path(value)
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.extend([pack_dir / raw, REPO_ROOT / raw])
    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve()
        except OSError:
            continue
        if resolved.exists():
            return resolved
    return None


def _collect_artifacts(
    payload: Any,
    *,
    pack_dir: Path,
    path: str = "",
) -> dict[str, dict[str, Any]]:
    artifacts: dict[str, dict[str, Any]] = {}
    if path.startswith(ARTIFACT_SKIP_PREFIXES):
        return artifacts
    if isinstance(payload, dict):
        for key, value in payload.items():
            child_path = f"{path}.{key}" if path else str(key)
            artifacts.update(_collect_artifacts(value, pack_dir=pack_dir, path=child_path))
        return artifacts
    if isinstance(payload, list):
        for idx, value in enumerate(payload):
            artifacts.update(_collect_artifacts(value, pack_dir=pack_dir, path=f"{path}[{idx}]"))
        return artifacts
    if isinstance(payload, str):
        key_name = path.rsplit(".", 1)[-1].split("[", 1)[0]
        if not ARTIFACT_PATH_KEY_RE.search(key_name):
            return artifacts
        resolved = _resolve_artifact(payload, pack_dir=pack_dir)
        if resolved is not None:
            artifacts[path] = _hash_artifact(resolved)
    return artifacts


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _run_pack(
    *,
    spec_dir: Path,
    fixture: Path,
    out: Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        shutil.rmtree(out)
    cmd = [
        sys.executable,
        str(RUNNER),
        str(spec_dir),
        "--fixture",
        str(fixture),
        "--out",
        str(out),
    ]
    proc_env = os.environ.copy()
    proc_env.update(env)
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=1800,
        env=proc_env,
    )


def _run_preflight(manifest: dict[str, Any], fixture: Path) -> dict[str, Any]:
    preflight_status, preflight = _preflight_checks(manifest, fixture)
    env_status, env_reason, env_checks = _environment_preflight(manifest)
    preflight = preflight + env_checks
    if preflight_status == "passed" and env_status == "skip":
        preflight_status = "env_skip"
    elif preflight_status == "passed" and env_status == "failed":
        preflight_status = "failed"
    return {
        "preflight_status": preflight_status,
        "preflight": preflight,
        "env_status": env_status,
        "env_reason": env_reason,
    }


def _resolve_fixture(spec_dir: Path, fixture_decl: str | None) -> Path | None:
    if not fixture_decl:
        return None
    fixture = Path(fixture_decl)
    if not fixture.is_absolute():
        fixture = spec_dir / fixture
    return fixture.resolve()


def _resolve_fixture_builder(spec_dir: Path, builder_decl: str | None) -> Path | None:
    if not builder_decl:
        return None
    builder = Path(builder_decl)
    if builder.is_absolute():
        return None
    resolved = (spec_dir / builder).resolve()
    try:
        resolved.relative_to(spec_dir.resolve())
    except ValueError:
        return None
    return resolved


def _run_fixture_builder(builder: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(builder)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )


def audit_one(spec_dir: Path, out_root: Path) -> dict[str, Any]:
    label = _target_label(spec_dir)
    manifest_path = spec_dir / "skill_manifest.yaml"
    manifest = load_manifest(manifest_path)
    repro = (manifest.get("validation") or {}).get("reproducibility") or {}
    row: dict[str, Any] = {
        "target": label,
        "target_path": _public_rel(spec_dir),
        "status": "fail",
        "mode": repro.get("mode"),
        "runs": [],
        "issues": [],
    }

    if not isinstance(repro, dict) or not repro:
        row["issues"].append("validation.reproducibility missing")
        return row
    mode = str(repro.get("mode") or "")
    if mode not in VALID_MODES:
        row["issues"].append(f"invalid reproducibility mode {mode!r}")
        return row
    if mode == "preflight" and not str(repro.get("reason") or "").strip():
        row["issues"].append("preflight reproducibility mode requires reason")
        return row

    fixture = _resolve_fixture(spec_dir, repro.get("fixture"))
    row["fixture"] = _public_rel(fixture) if fixture else None
    if fixture is None:
        row["issues"].append("validation.reproducibility.fixture missing")
        return row
    builder_decl = repro.get("fixture_builder")
    if builder_decl:
        builder = _resolve_fixture_builder(spec_dir, builder_decl)
        if builder is None:
            row["issues"].append(
                "validation.reproducibility.fixture_builder must be relative and stay under the spec dir"
            )
            return row
        row["fixture_builder"] = _public_rel(builder)
        if not builder.is_file():
            row["issues"].append(f"fixture builder does not exist: {_public_rel(builder)}")
            return row
        proc = _run_fixture_builder(builder)
        row["fixture_builder_returncode"] = proc.returncode
        if proc.returncode != 0:
            stderr = (proc.stderr or proc.stdout or "").strip()
            row["issues"].append(
                f"fixture builder failed: {_public_rel(builder)}"
                + (f": {stderr[:300]}" if stderr else "")
            )
            return row
        if not fixture.exists():
            row["issues"].append(
                f"fixture builder did not create declared fixture: {_public_rel(fixture)}"
            )
            return row
    if not fixture.exists():
        row["issues"].append(f"fixture does not exist: {_public_rel(fixture)}")
        return row

    repeat = int(repro.get("runs") or 2)
    if repeat < 2:
        row["issues"].append("validation.reproducibility.runs must be >= 2")
        return row
    env = {str(k): str(v) for k, v in (repro.get("env") or {}).items()}

    if mode == "preflight":
        preflight_runs = [_run_preflight(manifest, fixture) for _ in range(repeat)]
        row["runs"] = [
            {
                "preflight_status": item["preflight_status"],
                "env_status": item["env_status"],
                "env_reason": item["env_reason"],
            }
            for item in preflight_runs
        ]
        patterns = _compile_patterns(repro.get("ignore_paths") or [])
        scrubbed_preflight = [_scrub_payload(item, patterns=patterns) for item in preflight_runs]
        preflight_diffs: list[dict[str, Any]] = []
        for idx, item in enumerate(scrubbed_preflight[1:], start=2):
            for diff in _dotted_diffs(scrubbed_preflight[0], item):
                diff["run"] = idx
                preflight_diffs.append(diff)
        row["preflight_diffs"] = preflight_diffs[:50]
        row["preflight_diff_count"] = len(preflight_diffs)
        if preflight_diffs:
            row["issues"].append(
                f"preflight reproducibility drift: {len(preflight_diffs)} field(s)"
            )
        row["status"] = "pass" if not row["issues"] else "fail"
        row["artifact_hashes_checked"] = 0
        return row

    expected_status = str(repro.get("expected_status") or DEFAULT_EXPECTED_STATUS[mode])

    target_out = out_root / label
    packs: list[Path] = []
    validations: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []
    for idx in range(repeat):
        pack = target_out / f"run_{idx + 1}"
        proc = _run_pack(spec_dir=spec_dir, fixture=fixture, out=pack, env=env)
        validation = _load_json(pack / "validation_summary.json")
        output_payload = _load_json(pack / "output.json")
        packs.append(pack)
        validations.append(validation)
        outputs.append(output_payload)
        overall = validation.get("overall_status")
        row["runs"].append(
            {
                "pack": _public_rel(pack),
                "returncode": proc.returncode,
                "overall_status": overall,
                "preflight_status": validation.get("preflight_status"),
            }
        )
        if not validation:
            row["issues"].append(f"run_{idx + 1} did not write validation_summary.json")
        elif overall != expected_status:
            row["issues"].append(
                f"run_{idx + 1} overall_status={overall!r}, expected {expected_status!r}"
            )

    if row["issues"]:
        return row

    status_diffs = []
    first_validation = validations[0]
    for idx, validation in enumerate(validations[1:], start=2):
        for key in STATUS_KEYS:
            if first_validation.get(key) != validation.get(key):
                status_diffs.append(
                    {
                        "run": idx,
                        "key": key,
                        "run_1": first_validation.get(key),
                        f"run_{idx}": validation.get(key),
                    }
                )
    row["status_diffs"] = status_diffs
    if status_diffs:
        row["issues"].append(f"validation status drift: {len(status_diffs)} field(s)")

    patterns = _compile_patterns(repro.get("ignore_paths") or [])
    scrubbed = [_scrub_payload(payload, patterns=patterns) for payload in outputs]
    payload_diffs: list[dict[str, Any]] = []
    for idx, payload in enumerate(scrubbed[1:], start=2):
        for diff in _dotted_diffs(scrubbed[0], payload):
            diff["run"] = idx
            payload_diffs.append(diff)
    row["payload_diffs"] = payload_diffs[:50]
    row["payload_diff_count"] = len(payload_diffs)
    if payload_diffs:
        row["issues"].append(f"output payload drift: {len(payload_diffs)} field(s)")

    artifact_sets = [
        _collect_artifacts(payload, pack_dir=pack) for payload, pack in zip(outputs, packs)
    ]
    artifact_diffs: list[dict[str, Any]] = []
    first_artifacts = artifact_sets[0]
    for idx, artifacts in enumerate(artifact_sets[1:], start=2):
        for key in sorted(set(first_artifacts) | set(artifacts)):
            if first_artifacts.get(key) != artifacts.get(key):
                artifact_diffs.append(
                    {
                        "run": idx,
                        "path": key,
                        "run_1": first_artifacts.get(key),
                        f"run_{idx}": artifacts.get(key),
                    }
                )
    row["artifact_hashes_checked"] = len(first_artifacts)
    row["artifact_diffs"] = artifact_diffs[:50]
    row["artifact_diff_count"] = len(artifact_diffs)
    if artifact_diffs:
        row["issues"].append(f"artifact hash drift: {len(artifact_diffs)} path(s)")

    row["status"] = "pass" if not row["issues"] else "fail"
    return row


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [row for row in rows if row.get("status") != "pass"]
    return {
        "audit_status": "pass" if not failed else "fail",
        "targets": len(rows),
        "passed": len(rows) - len(failed),
        "failed": len(failed),
        "failed_targets": failed,
        "rows": rows,
    }


def format_summary(summary: dict[str, Any]) -> str:
    lines = [
        "",
        "=== reproducibility audit summary ===",
        (f"  {summary['targets']} targets: " f"{summary['passed']} pass, {summary['failed']} fail"),
        f"  audit status: {summary['audit_status']}",
        "",
        f"  {'target':<48s} {'status':<6s} {'mode':<9s} artifacts  issues",
    ]
    for row in summary["rows"]:
        issues = "; ".join(row.get("issues") or [])
        lines.append(
            f"  {row['target']:<48s} {row['status']:<6s} "
            f"{str(row.get('mode') or ''):<9s} "
            f"{int(row.get('artifact_hashes_checked') or 0):<9d} "
            f"{issues[:120]}"
        )
    if summary["failed_targets"]:
        failed = ", ".join(row["target"] for row in summary["failed_targets"])
        lines.extend(["", f"Reproducibility failures: {failed}"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT_ROOT_DEFAULT)
    parser.add_argument(
        "--target",
        action="append",
        help="Optional spec directory name or label to audit; may be repeated.",
    )
    args = parser.parse_args(argv)

    out_root = args.out.resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    wanted = set(args.target or [])
    rows: list[dict[str, Any]] = []
    for spec_dir in iter_spec_dirs():
        label = _target_label(spec_dir)
        if wanted and label not in wanted and spec_dir.name not in wanted:
            continue
        rows.append(audit_one(spec_dir.resolve(), out_root))
    summary = summarize(rows)
    (out_root / SUMMARY_NAME).write_text(json.dumps(summary, indent=2) + "\n")
    sys.stdout.write(format_summary(summary))
    return 0 if summary["audit_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
