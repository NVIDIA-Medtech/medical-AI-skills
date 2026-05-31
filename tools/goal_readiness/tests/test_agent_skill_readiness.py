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

import json
from pathlib import Path

from tools.goal_readiness import agent_skill_readiness as readiness


def _packet(status: str = "ready_for_external_approval") -> dict:
    return {
        "status": status,
        "preflight": {"status": "pass"},
        "approval_flag": "--confirm-external-llm-data-transfer",
        "approval_coverage": {
            "planned_direct_group_count": 4 if status != "already_proven" else 0,
            "pending_direct_group_count": 4 if status != "already_proven" else 0,
            "duplicate_direct_group_count": 0,
            "invalid_direct_command_count": 0,
        },
        "audit": {
            "summary": {
                "skills": 2,
                "prompt_artifacts_complete": 2,
                "study_artifacts_complete": 0 if status != "already_proven" else 2,
                "outcomes_support_skill_advantage": 0 if status != "already_proven" else 2,
            }
        },
        "data_transfer": {
            "payload_fingerprint": "reviewed-payload",
            "prompt_policy_issue_count": 0,
            "summary": {
                "pending_initial_calls": 12 if status != "already_proven" else 0,
                "max_possible_repair_calls": 60 if status != "already_proven" else 0,
            },
        },
    }


def _skill_summary(status: str = "pass", *, advisories: int = 0) -> dict:
    return {
        "audit_status": status,
        "real_runs": 3,
        "real_passed": 3 if status == "pass" else 2,
        "real_failed": 0 if status == "pass" else 1,
        "real_advisory_issues": advisories,
        "unexpected_failures": [],
        "advisory_failures": [],
        "calibration_failures": [],
    }


def _write_lifecycle_output(
    root: Path, target: str, *, blocked_status: str, gaps: list[str]
) -> None:
    out = root / target
    out.mkdir(parents=True)
    (out / "output.json").write_text(
        json.dumps(
            {
                "capability_lifecycle": {
                    "requirements": [
                        {"status": "draft", "met": True, "gaps": []},
                        {"status": blocked_status, "met": False, "gaps": gaps},
                    ]
                }
            }
        )
        + "\n"
    )


def test_build_report_marks_ready_for_external_approval(tmp_path: Path, monkeypatch) -> None:
    summary_path = tmp_path / "_summary.json"
    summary_path.write_text(
        '{"audit_status":"pass","real_runs":3,"real_passed":3,'
        '"real_failed":0,"real_advisory_issues":0}\n'
    )
    monkeypatch.setattr(readiness.approval, "build_packet", lambda **kwargs: _packet())

    report = readiness.build_report(skill_audit_summary_path=summary_path)

    assert report["status"] == "ready_for_external_approval"
    assert report["skill_usability"]["status"] == "pass"
    assert report["with_vs_without"]["pending_initial_external_calls"] == 12
    assert report["with_vs_without"]["payload_fingerprint"] == "reviewed-payload"
    assert report["with_vs_without"]["direct_remediation_groups_covered"] == 4
    assert report["with_vs_without"]["pending_direct_remediation_groups"] == 4
    assert report["with_vs_without"]["duplicate_direct_remediation_groups"] == 0
    assert report["with_vs_without"]["invalid_direct_remediation_commands"] == 0
    assert report["with_vs_without"]["prompt_payload_policy_issues"] == 0
    assert report["next_gate"] == "approved external reruns, then make prove-agent-skills"


def test_build_report_surfaces_lifecycle_counts(tmp_path: Path, monkeypatch) -> None:
    summary_path = tmp_path / "_summary.json"
    _write_lifecycle_output(
        tmp_path,
        "nv-segment-ct",
        blocked_status="verified",
        gaps=["no curated trusted-run summary found with passing verifier evidence"],
    )
    summary_path.write_text(
        json.dumps(
            {
                "audit_status": "pass",
                "real_runs": 3,
                "real_passed": 3,
                "real_failed": 0,
                "real_advisory_issues": 0,
                "rows": [
                    {
                        "target": "dicom-series-preflight",
                        "target_path": "skills/dicom-series-preflight/",
                        "lifecycle": "published",
                    },
                    {
                        "target": "nv-segment-ct",
                        "target_path": "skills/nv-segment-ct/",
                        "lifecycle": "gated",
                    },
                    {
                        "target": "negative_sloppy_skill",
                        "target_path": "verifiers/skill_completeness_v1/fixtures/negative_sloppy_skill",
                        "lifecycle": "draft",
                    },
                ],
            }
        )
        + "\n"
    )
    monkeypatch.setattr(readiness.approval, "build_packet", lambda **kwargs: _packet())

    report = readiness.build_report(skill_audit_summary_path=summary_path)

    skill = report["skill_usability"]
    assert skill["lifecycle_counts"] == {"published": 1, "gated": 1}
    assert skill["published_targets"] == ["dicom-series-preflight"]
    assert skill["lifecycle_blocker_count"] == 1
    assert skill["lifecycle_blockers"] == [
        {
            "target": "nv-segment-ct",
            "target_path": "skills/nv-segment-ct/",
            "lifecycle": "gated",
            "blocked_status": "verified",
            "gaps": ["no curated trusted-run summary found with passing verifier evidence"],
        }
    ]
    assert skill["review_focus"] == "1 gated targets still need trusted-run/publication evidence"


def test_build_report_defaults_to_current_direct_study_repeats(tmp_path: Path, monkeypatch) -> None:
    summary_path = tmp_path / "_summary.json"
    summary_path.write_text(
        '{"audit_status":"pass","real_runs":3,"real_passed":3,'
        '"real_failed":0,"real_advisory_issues":0}\n'
    )
    captured = {}

    def fake_build_packet(**kwargs):
        captured.update(kwargs)
        return _packet()

    monkeypatch.setattr(readiness.approval, "build_packet", fake_build_packet)

    readiness.build_report(skill_audit_summary_path=summary_path)

    assert captured["repeats"] == readiness.studies.DIRECT_REPEATS


def test_build_report_marks_complete_after_skill_and_study_proof(
    tmp_path: Path, monkeypatch
) -> None:
    summary_path = tmp_path / "_summary.json"
    summary_path.write_text(
        '{"audit_status":"pass","real_runs":3,"real_passed":3,'
        '"real_failed":0,"real_advisory_issues":0}\n'
    )
    monkeypatch.setattr(
        readiness.approval, "build_packet", lambda **kwargs: _packet("already_proven")
    )

    report = readiness.build_report(skill_audit_summary_path=summary_path)

    assert report["status"] == "complete"
    assert report["with_vs_without"]["outcomes_support_skill_advantage"] == 2
    assert report["next_gate"] == "none"


def test_build_report_marks_not_ready_without_skill_audit(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(readiness.approval, "build_packet", lambda **kwargs: _packet())

    report = readiness.build_report(skill_audit_summary_path=tmp_path / "missing.json")

    assert report["status"] == "not_ready"
    assert report["skill_usability"]["status"] == "missing"
    assert "make verify-skills" in report["next_gate"]


def test_format_markdown_reports_incomplete_proof(tmp_path: Path, monkeypatch) -> None:
    summary_path = tmp_path / "_summary.json"
    summary_path.write_text(
        '{"audit_status":"pass","real_runs":3,"real_passed":3,'
        '"real_failed":0,"real_advisory_issues":0}\n'
    )
    monkeypatch.setattr(readiness.approval, "build_packet", lambda **kwargs: _packet())

    text = readiness.format_markdown(readiness.build_report(skill_audit_summary_path=summary_path))

    assert "Status: `ready_for_external_approval`" in text
    assert "Pending initial external LLM calls: 12" in text
    assert "Direct remediation coverage: 4/4 pending skill/mode groups" in text
    assert "Direct remediation duplicate groups: 0" in text
    assert "Direct remediation invalid commands: 0" in text
    assert "Reviewed payload fingerprint: `reviewed-payload`" in text
    assert "not complete until refreshed study artifacts" in text
    assert "make prove-agent-skills" in text
