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

"""Deterministic verifier for report-anonymization evidence packs.

Audits a skill evidence pack produced from a radiology-report anonymization
run (e.g. MR-RATE reports_preprocessing stage 01). It gates on PHI leakage,
anonymization-token format validity, and token/mapping consistency. The PHI
leakage signal itself is computed upstream (deterministic mapping check or an
LLM judge) and recorded in ``output.json``; this verifier deterministically
grades the recorded metrics against fixed thresholds.

This is an engineering-quality auditor, not a regulatory de-identification
certification.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from verifiers._shared.verifier_kit import load_pack_json, make_check, run_grader  # noqa: E402

VERIFIER_ID = "medagent.verifiers.report_anonymization_quality_v1"
VERIFIER_VERSION = "0.1.0"
TARGET_SKILL_IDS = {
    "report-anonymization",
    "report_anonymization",
    "medagent.report_anonymization",
}

# Any confirmed PHI leak is a hard failure: anonymization must not let an
# original name/date/hospital/accession survive verbatim.
MAX_PHI_LEAK_RATE = 0.0
# Mapping extraction is best-effort; a low extraction rate is advisory because a
# missing token->original mapping does not by itself mean PHI leaked.
MIN_MAPPING_EXTRACTION_RATE = 0.80


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

    phi = output.get("phi_leak") or {}
    phi_method = str(phi.get("method") or "not_evaluated")
    phi_evaluated = int(_num(phi.get("n_evaluated"), 0))
    phi_leaked = int(_num(phi.get("n_leaked"), 0))
    phi_leak_rate = _num(phi.get("leak_rate"), 0.0)

    token_format = output.get("token_format") or {}
    n_malformed = int(_num(token_format.get("n_malformed_tokens"), 0))

    consistency = output.get("token_consistency") or {}
    n_inconsistent = int(_num(consistency.get("n_inconsistent"), 0))
    mapping_extraction_rate = _num(consistency.get("mapping_extraction_rate"), 1.0)

    checks: list[dict[str, Any]] = [
        make_check(
            "target_skill_matches",
            skill_id in TARGET_SKILL_IDS,
            f"skill_id={skill_id!r}",
        ),
        make_check(
            "source_pack_passed",
            validation.get("overall_status") == "passed",
            f"source pack overall={validation.get('overall_status')!r}",
        ),
        make_check(
            "reports_present",
            n_reports > 0,
            f"n_reports={n_reports}",
        ),
    ]

    # PHI leakage gate.
    if phi_method == "not_evaluated":
        checks.append(
            make_check(
                "phi_leak_evaluated",
                False,
                "phi_leak.method=not_evaluated; PHI leakage was not measured",
                level="warn",
            )
        )
    else:
        checks.append(
            make_check(
                "phi_leak_evaluated",
                phi_evaluated > 0,
                f"phi_leak.method={phi_method!r}, n_evaluated={phi_evaluated}",
            )
        )
        checks.append(
            make_check(
                "phi_leak_within_threshold",
                phi_leak_rate <= MAX_PHI_LEAK_RATE,
                f"leak_rate={phi_leak_rate:.4f} (n_leaked={phi_leaked}/{phi_evaluated}), "
                f"max allowed={MAX_PHI_LEAK_RATE}",
            )
        )

    # Token format gate.
    checks.append(
        make_check(
            "anonymization_tokens_well_formed",
            n_malformed == 0,
            f"n_malformed_tokens={n_malformed}",
            level="warn",
        )
    )

    # Token / mapping consistency gates.
    checks.append(
        make_check(
            "tokens_consistent_with_mapping",
            n_inconsistent == 0,
            f"n_inconsistent={n_inconsistent} reports have tokens missing from Token_Mapping",
        )
    )
    checks.append(
        make_check(
            "mapping_extraction_rate_acceptable",
            mapping_extraction_rate >= MIN_MAPPING_EXTRACTION_RATE,
            f"mapping_extraction_rate={mapping_extraction_rate:.4f}, "
            f"min={MIN_MAPPING_EXTRACTION_RATE}",
            level="warn",
        )
    )

    warnings: list[str] = []
    if phi_leaked > 0:
        warnings.append(
            f"{phi_leaked}/{phi_evaluated} report(s) flagged with residual PHI "
            f"(method={phi_method})"
        )
    if phi_method == "not_evaluated":
        warnings.append("PHI leakage was not measured for this pack")
    if n_malformed > 0:
        examples = token_format.get("malformed_examples") or []
        warnings.append(f"{n_malformed} malformed anonymization token(s); examples: {examples[:5]}")

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
        "anonymization_quality": {
            "n_fail": len(fail_checks),
            "n_warn": len(warn_checks),
            "verdict": overall,
            "acceptable": overall in {"pass", "warn"},
            "phi_leak_rate": phi_leak_rate,
            "phi_leak_method": phi_method,
            "mapping_extraction_rate": mapping_extraction_rate,
            "n_malformed_tokens": n_malformed,
        },
        "checks": checks,
        "warnings": warnings,
        "overall": overall,
    }


if __name__ == "__main__":
    run_grader(grade)
