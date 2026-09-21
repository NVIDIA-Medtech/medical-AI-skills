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

"""Deterministic verifier for report-pathology-classification evidence packs.

Audits a skill evidence pack produced from a pathology-classification run
(MR-RATE reports_preprocessing stage 06). It gates on label coverage (every
report receives a complete 0/1 label vector), JSON-extraction success rate, and
the absence of out-of-taxonomy labels. The label values are computed upstream
and recorded in ``output.json``; this verifier deterministically grades the
recorded metrics.

Engineering-quality auditor, not a clinical diagnostic claim.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from verifiers._shared.verifier_kit import load_pack_json, make_check, run_grader  # noqa: E402

VERIFIER_ID = "medagent.verifiers.report_pathology_quality_v1"
VERIFIER_VERSION = "0.1.0"
TARGET_SKILL_IDS = {
    "report-pathology-classification",
    "report_pathology_classification",
    "medagent.report_pathology_classification",
}

# Every report must receive a complete 0/1 vector over the pathology set;
# partial coverage means the classifier silently dropped reports.
MIN_LABEL_COVERAGE_RATE = 1.0
# JSON extraction (step 2 of the upstream pipeline) success after retries.
MIN_JSON_PARSE_SUCCESS_RATE = 0.98


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

    pathologies = output.get("pathologies") or {}
    n_labels = int(_num(pathologies.get("n_labels"), 0))

    labels = output.get("labels") or {}
    coverage = _num(labels.get("label_coverage_rate"), 0.0)
    n_present_total = int(_num(labels.get("n_present_total"), 0))

    val = output.get("validation") or {}
    json_method = str(val.get("method") or "not_evaluated")
    json_rate = _num(val.get("json_parse_success_rate"), 0.0)
    n_json_fail = int(_num(val.get("n_json_parse_failures"), 0))
    n_invalid = int(_num(val.get("n_invalid_labels"), 0))

    checks: list[dict[str, Any]] = [
        make_check("target_skill_matches", skill_id in TARGET_SKILL_IDS, f"skill_id={skill_id!r}"),
        make_check(
            "source_pack_passed",
            validation.get("overall_status") == "passed",
            f"source pack overall={validation.get('overall_status')!r}",
        ),
        make_check("reports_present", n_reports > 0, f"n_reports={n_reports}"),
        make_check(
            "pathology_set_present",
            n_labels > 0,
            f"n_labels={n_labels}",
            level="warn",
        ),
        make_check(
            "labels_fully_covered",
            coverage >= MIN_LABEL_COVERAGE_RATE,
            f"label_coverage_rate={coverage:.4f}, min={MIN_LABEL_COVERAGE_RATE}",
        ),
    ]

    if json_method == "not_evaluated":
        checks.append(
            make_check(
                "json_extraction_evaluated", False, "validation.method=not_evaluated", level="warn"
            )
        )
    else:
        checks.append(
            make_check(
                "json_parse_success_within_threshold",
                json_rate >= MIN_JSON_PARSE_SUCCESS_RATE,
                f"json_parse_success_rate={json_rate:.4f} (n_failures={n_json_fail}), min={MIN_JSON_PARSE_SUCCESS_RATE}",
            )
        )

    checks.append(
        make_check(
            "no_out_of_taxonomy_labels",
            n_invalid == 0,
            f"n_invalid_labels={n_invalid}",
        )
    )

    warnings: list[str] = []
    if json_method == "not_evaluated":
        warnings.append("JSON-extraction success was not measured for this pack")
    if n_labels == 0:
        warnings.append("no pathology set reported (pathologies.n_labels=0)")
    if n_invalid > 0:
        warnings.append(f"{n_invalid} label(s) outside the declared pathology taxonomy")

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
        "pathology_quality": {
            "n_fail": len(fail_checks),
            "n_warn": len(warn_checks),
            "verdict": overall,
            "acceptable": overall in {"pass", "warn"},
            "label_coverage_rate": coverage,
            "json_parse_success_rate": json_rate,
            "n_invalid_labels": n_invalid,
            "n_labels": n_labels,
            "n_present_total": n_present_total,
        },
        "checks": checks,
        "warnings": warnings,
        "overall": overall,
    }


if __name__ == "__main__":
    run_grader(grade)
