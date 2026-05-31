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

"""Tests for eval_engine.run_trusted."""

import json
from pathlib import Path


def _trusted_run(run_module, skill, fixture, out):
    return run_module(
        "eval_engine.run_trusted",
        str(skill),
        "--fixture",
        str(fixture),
        "--out",
        str(out),
    )


def test_no_paired_verifiers_yields_no_verifiers_verdict(tmp_path, write_toy_skill, run_module):
    fixture = tmp_path / "fixture.txt"
    fixture.write_text("x")
    skill = write_toy_skill("toy_skill", skill_id="test.toy_trusted")
    out = tmp_path / "trust"

    proc = _trusted_run(run_module, skill, fixture, out)
    assert proc.returncode == 0, proc.stdout + proc.stderr

    summary = json.loads((out / "trust_summary.json").read_text())
    assert summary["overall"] == "no_verifiers"
    assert summary["skill_overall"] == "passed"
    assert summary["verifiers"] == []
    assert summary["gaps"] == []
    assert summary["implemented_verifiers"] == []
    assert summary["planned_verifier_gaps"] == []
    assert summary["env_skipped_verifier_gaps"] == []
    assert summary["warning_findings"] == []
    assert summary["evidence_packs"][0]["role"] == "skill"
    assert summary["evidence_packs"][0]["pack"] == "skill_run"
    assert "manifest.json" in summary["evidence_packs"][0]["hashes"]
    assert (out / "skill_run" / "manifest.json").exists()


def test_trusted_run_passes_declared_default_sentinel_verbatim(tmp_path, run_module):
    skill = tmp_path / "sentinel_skill"
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Sentinel Skill\n")
    (skill / "skill_manifest.yaml").write_text(
        "\n".join(
            [
                "id: test.sentinel_trusted",
                "version: 0.1.0",
                "inputs:",
                "  - name: fixture",
                "    type: directory_path",
                "    formats: [default_sentinel]",
                "outputs:",
                "  - name: result_json",
                "    type: json",
                "runtime:",
                "  language: python",
                "  entrypoint: scripts/run.py",
                "validation:",
                "  sanity_checks:",
                "    - {path: output.fixture, eq: default}",
            ]
        )
    )
    (skill / "scripts" / "run.py").write_text(
        "import json, sys\n" "print(json.dumps({'output': {'fixture': sys.argv[1]}}))\n"
    )
    out = tmp_path / "trust"

    proc = _trusted_run(run_module, skill, Path("default"), out)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    skill_manifest = json.loads((out / "skill_run" / "manifest.json").read_text())
    summary = json.loads((out / "trust_summary.json").read_text())
    assert skill_manifest["fixture"]["path"] == "default"
    assert skill_manifest["command"][-1] == "default"
    assert summary["skill_overall"] == "passed"
    assert summary["overall"] == "no_verifiers"


def test_planned_only_paired_verifier_is_a_gap(tmp_path, write_toy_skill, run_module):
    fixture = tmp_path / "fixture.txt"
    fixture.write_text("x")
    skill = write_toy_skill(
        "toy_skill",
        skill_id="test.toy_trusted",
        paired_verifiers=(
            "paired_verifiers:\n"
            "  - id: medagent.verifiers.future_check\n"
            "    status: planned\n"
            "    checks: [bounding_box, dice]\n"
            "    notes: not yet implemented\n"
        ),
    )
    out = tmp_path / "trust"

    proc = _trusted_run(run_module, skill, fixture, out)
    assert proc.returncode == 0, proc.stdout + proc.stderr

    summary = json.loads((out / "trust_summary.json").read_text())
    assert summary["overall"] == "gap"
    assert len(summary["gaps"]) == 1
    gap = summary["gaps"][0]
    assert gap["id"] == "medagent.verifiers.future_check"
    assert gap["declared_status"] == "planned"
    assert gap["checks"] == ["bounding_box", "dice"]
    assert summary["planned_verifier_gaps"] == [gap]


def test_resolver_finds_real_verifier_dir():
    from eval_engine.run_trusted import _resolve_verifier_dir

    vdir = _resolve_verifier_dir("medagent.verifiers.ct_segmentation_quality_v1")
    assert vdir is not None
    assert vdir.name == "ct_segmentation_quality_v1"
    assert (vdir / "skill_manifest.yaml").exists()


def test_resolver_returns_none_for_unknown_id():
    from eval_engine.run_trusted import _resolve_verifier_dir

    assert _resolve_verifier_dir("medagent.verifiers.does_not_exist_xyz") is None


def test_env_skipped_verifier_is_gap_not_passed():
    from eval_engine.run_trusted import _verdict

    verdict = _verdict(
        "passed",
        [{"id": "v", "overall": "skipped (env_unavailable)"}],
        [],
    )
    assert verdict == "gap"


def test_warn_verifier_yields_warn_verdict():
    from eval_engine.run_trusted import _verdict

    verdict = _verdict("passed", [{"id": "v", "overall": "warn"}], [])
    assert verdict == "warn"


def test_read_verifier_overall_normalizes_pass_warn_fail(tmp_path):
    import json as _json

    from eval_engine.run_trusted import _read_verifier_overall

    for raw, expected in (("pass", "passed"), ("warn", "warn"), ("fail", "failed")):
        vpack = tmp_path / f"vpack_{raw}"
        vpack.mkdir()
        (vpack / "output.json").write_text(_json.dumps({"overall": raw}))
        assert _read_verifier_overall(vpack) == expected


def test_verifier_findings_counts_hard_and_warning_issues(tmp_path):
    import json as _json

    from eval_engine.run_trusted import _verifier_findings

    vpack = tmp_path / "vpack"
    vpack.mkdir()
    (vpack / "output.json").write_text(
        _json.dumps(
            {
                "overall": "warn",
                "blocking_issues_count": 1,
                "errors": ["hard"],
                "advisory_issues_count": 2,
                "warnings": ["warn-a", "warn-b"],
            }
        )
    )

    findings = _verifier_findings(vpack)

    assert findings["hard_failure_count"] == 2
    assert findings["warning_count"] == 5
    assert findings["semantic_failure_count"] == 0
    assert findings["semantic_warning_count"] == 1
    assert findings["warning_findings"] == ["warn-a", "warn-b", "overall=warn"]


def test_verifier_findings_counts_nested_semantic_checks(tmp_path):
    import json as _json

    from eval_engine.run_trusted import _verifier_findings

    vpack = tmp_path / "vpack"
    vpack.mkdir()
    (vpack / "output.json").write_text(
        _json.dumps(
            {
                "overall": "fail",
                "domain_floor": {
                    "verdict": "fail",
                    "checks": [
                        {
                            "name": "decoded_detection_artifact_present",
                            "status": "fail",
                            "reason": "detection_artifact_count=0",
                        },
                        {
                            "name": "recording_artifact_present",
                            "status": "pass",
                            "reason": "recording_file_count=2",
                        },
                    ],
                },
                "detection_metrics": {
                    "verdict": "skipped",
                    "checks": [
                        {
                            "name": "bbox_sanity",
                            "status": "warn",
                            "reason": "not enough decoded detections",
                        }
                    ],
                },
            }
        )
    )

    findings = _verifier_findings(vpack)

    assert findings["semantic_overall"] == "fail"
    assert findings["semantic_failure_count"] == 1
    assert findings["semantic_warning_count"] == 1
    assert findings["hard_failure_count"] == 1
    assert findings["warning_count"] == 1
    assert findings["failure_findings"] == [
        "domain_floor.decoded_detection_artifact_present: detection_artifact_count=0"
    ]
    assert findings["warning_findings"] == [
        "detection_metrics.bbox_sanity: not enough decoded detections"
    ]


def test_verifier_findings_deduplicates_top_level_and_semantic_warnings(tmp_path):
    import json as _json

    from eval_engine.run_trusted import _verifier_findings

    vpack = tmp_path / "vpack"
    vpack.mkdir()
    (vpack / "output.json").write_text(
        _json.dumps(
            {
                "overall": "warn",
                "warnings": ["same warning: with detail"],
                "checks": [
                    {
                        "name": "same_warning_check",
                        "status": "warn",
                        "reason": "same warning: with detail",
                    }
                ],
            }
        )
    )

    findings = _verifier_findings(vpack)

    assert findings["warning_count"] == 1
    assert findings["semantic_warning_count"] == 1
    assert findings["warning_findings"] == ["checks.same_warning_check: same warning: with detail"]


def test_summary_validates_against_schema(tmp_path, write_toy_skill, run_module, repo_root):
    fixture = tmp_path / "fixture.txt"
    fixture.write_text("x")
    skill = write_toy_skill("toy_skill", skill_id="test.toy_trusted")
    out = tmp_path / "trust"
    proc = _trusted_run(run_module, skill, fixture, out)
    assert proc.returncode == 0, proc.stdout + proc.stderr

    import jsonschema

    schema = json.loads(
        (repo_root / "spec" / "evidence_pack" / "trust_summary.schema.json").read_text()
    )
    summary = json.loads((out / "trust_summary.json").read_text())
    jsonschema.validate(summary, schema)
