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

"""Deterministic verifier for report-structuring evidence packs.

Audits a skill evidence pack produced from a radiology-report structuring run
(MR-RATE reports_preprocessing stage 04 structuring + stage 05 structure QC).
It gates on section-parse success, structure-QC pass rate, and formatting-rule
violations (findings must not be bulleted, no section-header leakage), and warns
on low section completeness. The QC signal is computed upstream and recorded in
``output.json``; this verifier deterministically grades the recorded metrics.

Engineering-quality auditor, not a clinical accuracy claim.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from verifiers._shared.verifier_kit import load_pack_json, make_check, run_grader  # noqa: E402

VERIFIER_ID = "medagent.verifiers.report_structuring_quality_v1"
VERIFIER_VERSION = "0.1.0"
TARGET_SKILL_IDS = {
    "report-structuring",
    "report_structuring",
    "medagent.report_structuring",
}

# A section parse failure means the model never produced the 4 sections; high
# rates indicate the structuring pass is broken, so this is a hard threshold.
MIN_PARSE_SUCCESS_RATE = 0.98
# Structure-QC pass rate after the retry loop; README target is >98%, the gate
# is set a little lower to tolerate QC false positives.
MIN_QC_PASS_RATE = 0.95
# Section completeness is advisory: an empty impression can be correct when the
# original report had none (the pipeline never synthesizes one).
MIN_COMPLETENESS_RATE = 0.90


def _public_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def grade(pack_dir: Path) -> dict[str, Any]:
    pack_dir = pack_dir.resolve()
    output = load_pack_json(pack_dir, "output.json")
    validation = load_pack_json(pack_dir, "validation_summary.json")
    manifest = load_pack_json(pack_dir, "manifest.json")
    skill_id = str(manifest.get("skill_id") or output.get("skill") or "")

    n_reports = int(_num(output.get("n_reports"), 0))

    parse = output.get("parse") or {}
    parse_rate = _num(parse.get("parse_success_rate"), 0.0)
    n_parse_fail = int(_num(parse.get("n_parse_failures"), 0))

    sections = output.get("sections") or {}
    completeness = _num(sections.get("completeness_rate"), 0.0)

    qc = output.get("qc") or {}
    qc_method = str(qc.get("method") or "not_evaluated")
    qc_evaluated = int(_num(qc.get("n_evaluated"), 0))
    qc_rate = _num(qc.get("pass_rate"), 0.0)

    fmt = output.get("format") or {}
    n_format_violations = int(_num(fmt.get("n_format_violations"), 0))
    n_header_leaks = int(_num(fmt.get("n_header_leaks"), 0))

    checks: list[dict[str, Any]] = [
        make_check("target_skill_matches", skill_id in TARGET_SKILL_IDS, f"skill_id={skill_id!r}"),
        make_check(
            "source_pack_passed",
            validation.get("overall_status") == "passed",
            f"source pack overall={validation.get('overall_status')!r}",
        ),
        make_check("reports_present", n_reports > 0, f"n_reports={n_reports}"),
        make_check(
            "parse_success_rate_within_threshold",
            parse_rate >= MIN_PARSE_SUCCESS_RATE,
            f"parse_success_rate={parse_rate:.4f} (n_parse_failures={n_parse_fail}), min={MIN_PARSE_SUCCESS_RATE}",
        ),
    ]

    if qc_method == "not_evaluated":
        checks.append(
            make_check("structure_qc_evaluated", False, "qc.method=not_evaluated", level="warn")
        )
    else:
        checks.append(
            make_check(
                "structure_qc_evaluated",
                qc_evaluated > 0,
                f"qc.method={qc_method!r}, n_evaluated={qc_evaluated}",
            )
        )
        checks.append(
            make_check(
                "structure_qc_pass_rate_within_threshold",
                qc_rate >= MIN_QC_PASS_RATE,
                f"pass_rate={qc_rate:.4f}, min={MIN_QC_PASS_RATE}",
            )
        )

    checks.append(
        make_check(
            "formatting_rules_clean",
            n_format_violations == 0,
            f"n_format_violations={n_format_violations} (header_leaks={n_header_leaks})",
        )
    )
    checks.append(
        make_check(
            "sections_complete",
            completeness >= MIN_COMPLETENESS_RATE,
            f"completeness_rate={completeness:.4f}, min={MIN_COMPLETENESS_RATE}",
            level="warn",
        )
    )

    warnings: list[str] = []
    if qc_method == "not_evaluated":
        warnings.append("structure QC was not measured for this pack")
    if n_format_violations > 0:
        warnings.append(
            f"{n_format_violations} formatting-rule violation(s); header_leaks={n_header_leaks}"
        )
    if completeness < MIN_COMPLETENESS_RATE:
        warnings.append(f"section completeness {completeness:.2f} below {MIN_COMPLETENESS_RATE}")

    hard_fail = any(c["status"] == "fail" for c in checks)
    has_warn = any(c["status"] == "warn" for c in checks)
    overall = "fail" if hard_fail else ("warn" if has_warn else "pass")
    fail_checks = [c for c in checks if c["status"] == "fail"]
    warn_checks = [c for c in checks if c["status"] == "warn"]

    return {
        "verifier": {"id": VERIFIER_ID, "version": VERIFIER_VERSION},
        "target": {
            "evidence_pack": _public_path(pack_dir),
            "skill_id": skill_id,
            "source_overall_status": validation.get("overall_status"),
            "model": output.get("model"),
            "n_reports": n_reports,
        },
        "structuring_quality": {
            "n_fail": len(fail_checks),
            "n_warn": len(warn_checks),
            "verdict": overall,
            "acceptable": overall in {"pass", "warn"},
            "parse_success_rate": parse_rate,
            "qc_pass_rate": qc_rate,
            "n_format_violations": n_format_violations,
            "completeness_rate": completeness,
        },
        "checks": checks,
        "warnings": warnings,
        "overall": overall,
    }


if __name__ == "__main__":
    run_grader(grade)
