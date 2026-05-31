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

"""Smoke tests for spec/evidence_pack.schema.json and eval_engine.validate_pack."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER = REPO_ROOT / "eval_engine" / "run.py"
VALIDATOR = ["-m", "eval_engine.validate_pack"]
SKILL = REPO_ROOT / "skills" / "dicom-metadata-extract"
FIXTURE = SKILL / "fixtures" / "sample_ct.dcm"


def _run(args, cwd=None, env=None):
    proc_env = os.environ.copy()
    if env:
        proc_env.update(env)
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd or REPO_ROOT,
        env=proc_env,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def fresh_pack(tmp_path):
    out = tmp_path / "pack"
    proc = _run([str(RUNNER), str(SKILL), "--fixture", str(FIXTURE), "--out", str(out)])
    assert proc.returncode == 0, proc.stderr
    return out


def test_fresh_pack_stamps_version(fresh_pack):
    manifest = json.loads((fresh_pack / "manifest.json").read_text())
    assert manifest["pack_format_version"] == "1.0.0"
    assert manifest["pack_kind"] == "skill_run"


def test_fresh_pack_stamps_repo_git_sha(fresh_pack):
    """When HEAD exists, the pack records it as a 40-char SHA.

    `repo_git_sha` is a FUTURE-AI traceability requirement: it lets a pack be
    re-bound to the exact source state that produced it. A git checkout without
    an initial commit cannot resolve HEAD yet, so it should preserve the
    best-effort writer contract and stamp null.
    """
    manifest = json.loads((fresh_pack / "manifest.json").read_text())
    assert "repo_git_sha" in manifest
    sha = manifest["repo_git_sha"]
    head = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    if head.returncode != 0:
        assert sha is None
        return
    assert sha is not None and len(sha) == 40
    assert all(c in "0123456789abcdef" for c in sha)


def test_fresh_pack_validates(fresh_pack):
    proc = _run([*VALIDATOR, str(fresh_pack)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "pack validates" in proc.stdout


def test_fresh_pack_trace_has_v0_canonical_aliases(fresh_pack):
    records = [
        json.loads(line)
        for line in (fresh_pack / "agent_run_trace.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert records
    for record in records:
        assert record["trace_schema_version"] == "0.1.0"
        assert "event_type" in record
        assert "timestamp" in record
        # Legacy aliases are still present for current review tooling and
        # historical pack comparability.
        assert record["kind"] == record["event_type"]
        assert record["ts"] == record["timestamp"]


def test_legacy_trace_aliases_require_allow_legacy(fresh_pack):
    trace_path = fresh_pack / "agent_run_trace.jsonl"
    legacy_records = []
    for line in trace_path.read_text().splitlines():
        record = json.loads(line)
        record.pop("trace_schema_version", None)
        record.pop("event_type", None)
        record.pop("timestamp", None)
        record.pop("duration_seconds", None)
        record.pop("inputs", None)
        legacy_records.append(record)
    trace_path.write_text("\n".join(json.dumps(record) for record in legacy_records) + "\n")

    strict = _run([*VALIDATOR, str(fresh_pack)])
    assert strict.returncode == 2
    assert "agent_run_trace.jsonl line 1" in strict.stdout

    lenient = _run([*VALIDATOR, str(fresh_pack), "--allow-legacy"])
    assert lenient.returncode == 0, lenient.stdout + lenient.stderr
    assert "accepted legacy trace aliases" in lenient.stdout


def test_missing_version_fails_without_allow_legacy(fresh_pack):
    manifest_path = fresh_pack / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest.pop("pack_format_version", None)
    manifest_path.write_text(json.dumps(manifest, indent=2))

    strict = _run([*VALIDATOR, str(fresh_pack)])
    assert strict.returncode == 2
    assert "missing pack_format_version" in strict.stdout

    lenient = _run([*VALIDATOR, str(fresh_pack), "--allow-legacy"])
    assert lenient.returncode == 0
    assert "warnings:" in lenient.stdout


def test_required_file_missing_fails(fresh_pack):
    (fresh_pack / "validation_summary.json").unlink()
    proc = _run([*VALIDATOR, str(fresh_pack)])
    assert proc.returncode == 2
    assert "validation_summary.json: required file missing" in proc.stdout


def test_schema_violation_fails(fresh_pack):
    summary_path = fresh_pack / "validation_summary.json"
    summary = json.loads(summary_path.read_text())
    summary.pop("preflight_status")
    summary_path.write_text(json.dumps(summary, indent=2))

    proc = _run([*VALIDATOR, str(fresh_pack)])
    assert proc.returncode == 2
    assert "preflight_status" in proc.stdout


def test_trusted_run_root_validates_nested_packs(fresh_pack, tmp_path):
    root = tmp_path / "trusted"
    shutil.copytree(fresh_pack, root / "skill_run")
    shutil.copytree(fresh_pack, root / "verifiers" / "toy_verifier")
    (root / "trust_summary.json").write_text(
        json.dumps(
            {
                "pack_format_version": "1.0.0",
                "trust_format_version": "1.2.0",
                "skill_id": "test.skill",
                "skill_pack": "skill_run",
                "skill_overall": "passed",
                "verifiers": [
                    {
                        "id": "test.verifier",
                        "declared_status": "implemented",
                        "pack": "verifiers/toy_verifier",
                        "overall": "passed",
                    }
                ],
                "gaps": [],
                "overall": "passed",
            },
            indent=2,
        )
    )

    proc = _run([*VALIDATOR, str(root)])

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "trusted-run validates" in proc.stdout
    assert "validate-pack skill:" in proc.stdout
    assert "validate-pack verifier test.verifier:" in proc.stdout


def test_trusted_run_root_fails_when_linked_verifier_pack_missing(fresh_pack, tmp_path):
    root = tmp_path / "trusted"
    shutil.copytree(fresh_pack, root / "skill_run")
    (root / "trust_summary.json").write_text(
        json.dumps(
            {
                "pack_format_version": "1.0.0",
                "trust_format_version": "1.2.0",
                "skill_id": "test.skill",
                "skill_pack": "skill_run",
                "skill_overall": "passed",
                "verifiers": [
                    {
                        "id": "test.missing_verifier",
                        "declared_status": "implemented",
                        "pack": "verifiers/missing",
                        "overall": "passed",
                    }
                ],
                "gaps": [],
                "overall": "passed",
            },
            indent=2,
        )
    )

    proc = _run([*VALIDATOR, str(root)])

    assert proc.returncode == 2
    assert "nested pack missing" in proc.stdout
