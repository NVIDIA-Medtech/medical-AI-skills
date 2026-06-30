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

"""Deterministic verifier for report-translation evidence packs.

Audits a skill evidence pack produced from a Turkish->English radiology-report
translation run (e.g. MR-RATE reports_preprocessing stage 02 + 03 QC). It gates
on the LLM-judged translation QC pass rate, the residual non-English (Turkish
leftover) rate, and anonymization-token preservation through translation.

The QC pass rate and language-detection rate are computed upstream by the
pipeline's LLM QC/detection stages and recorded in ``output.json``; this
verifier deterministically grades the recorded metrics against fixed
thresholds. Token preservation is a deterministic string check recorded
upstream.

This is an engineering-quality auditor, not a clinical accuracy claim.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from verifiers._shared.verifier_kit import load_pack_json, make_check, run_grader  # noqa: E402

VERIFIER_ID = "medagent.verifiers.report_translation_quality_v1"
VERIFIER_VERSION = "0.1.0"
TARGET_SKILL_IDS = {
    "report-translation",
    "report_translation",
    "medagent.report_translation",
}

# LLM-judged QC pass rate thresholds (over reports with a decisive PASS/FAIL).
QC_PASS_RATE_PASS = 0.90
QC_PASS_RATE_WARN = 0.70
# Residual non-English / Turkish-leftover rate thresholds.
NON_ENGLISH_RATE_PASS = 0.0
NON_ENGLISH_RATE_FAIL = 0.10
# Fraction of QC verdicts that may be unparseable ("unknown") before it warns.
MAX_UNKNOWN_RATE = 0.10


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

    qc = output.get("qc") or {}
    qc_method = str(qc.get("method") or "not_evaluated")
    qc_evaluated = int(_num(qc.get("n_evaluated"), 0))
    qc_pass = int(_num(qc.get("n_pass"), 0))
    qc_fail = int(_num(qc.get("n_fail"), 0))
    qc_unknown = int(_num(qc.get("n_unknown"), 0))
    qc_pass_rate = _num(qc.get("pass_rate"), 0.0)
    decisive = qc_pass + qc_fail
    unknown_rate = (qc_unknown / qc_evaluated) if qc_evaluated else 0.0

    lang = output.get("language") or {}
    lang_method = str(lang.get("method") or "not_evaluated")
    lang_evaluated = int(_num(lang.get("n_evaluated"), 0))
    non_english = int(_num(lang.get("n_non_english"), 0))
    non_english_rate = _num(lang.get("non_english_rate"), 0.0)

    tok = output.get("token_preservation") or {}
    n_with_tokens = int(_num(tok.get("n_reports_with_tokens"), 0))
    n_dropped = int(_num(tok.get("n_reports_token_dropped"), 0))
    preservation_rate = _num(tok.get("preservation_rate"), 1.0)

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

    # Translation QC pass-rate gate (LLM-judged completeness / accuracy).
    if qc_method == "not_evaluated" or decisive == 0:
        checks.append(
            make_check(
                "translation_qc_evaluated",
                False,
                f"qc.method={qc_method!r}, decisive_verdicts={decisive}",
                level="warn",
            )
        )
    else:
        if qc_pass_rate >= QC_PASS_RATE_PASS:
            checks.append(
                make_check(
                    "translation_qc_pass_rate",
                    True,
                    f"pass_rate={qc_pass_rate:.4f} (>= {QC_PASS_RATE_PASS})",
                )
            )
        elif qc_pass_rate >= QC_PASS_RATE_WARN:
            checks.append(
                make_check(
                    "translation_qc_pass_rate",
                    False,
                    f"pass_rate={qc_pass_rate:.4f} in warn band "
                    f"[{QC_PASS_RATE_WARN}, {QC_PASS_RATE_PASS})",
                    level="warn",
                )
            )
        else:
            checks.append(
                make_check(
                    "translation_qc_pass_rate",
                    False,
                    f"pass_rate={qc_pass_rate:.4f} < warn floor {QC_PASS_RATE_WARN}",
                )
            )
        checks.append(
            make_check(
                "translation_qc_unknown_rate_acceptable",
                unknown_rate <= MAX_UNKNOWN_RATE,
                f"unknown_rate={unknown_rate:.4f} (max {MAX_UNKNOWN_RATE})",
                level="warn",
            )
        )

    # Residual non-English / Turkish-leftover gate.
    if lang_method == "not_evaluated" or lang_evaluated == 0:
        checks.append(
            make_check(
                "language_detection_evaluated",
                False,
                f"language.method={lang_method!r}, n_evaluated={lang_evaluated}",
                level="warn",
            )
        )
    elif non_english_rate <= NON_ENGLISH_RATE_PASS:
        checks.append(
            make_check(
                "residual_non_english_within_threshold",
                True,
                f"non_english_rate={non_english_rate:.4f} (<= {NON_ENGLISH_RATE_PASS})",
            )
        )
    elif non_english_rate < NON_ENGLISH_RATE_FAIL:
        checks.append(
            make_check(
                "residual_non_english_within_threshold",
                False,
                f"non_english_rate={non_english_rate:.4f} in warn band "
                f"(0, {NON_ENGLISH_RATE_FAIL}); {non_english} report(s) still non-English",
                level="warn",
            )
        )
    else:
        checks.append(
            make_check(
                "residual_non_english_within_threshold",
                False,
                f"non_english_rate={non_english_rate:.4f} >= fail threshold "
                f"{NON_ENGLISH_RATE_FAIL}; {non_english} report(s) still non-English",
            )
        )

    # Anonymization-token preservation gate (tokens must survive translation).
    checks.append(
        make_check(
            "anonymization_tokens_preserved",
            n_dropped == 0,
            f"n_reports_token_dropped={n_dropped}/{n_with_tokens}, "
            f"preservation_rate={preservation_rate:.4f}",
        )
    )

    warnings: list[str] = []
    if qc_method != "not_evaluated" and decisive:
        warnings.append(
            f"translation QC: {qc_pass}/{decisive} decisive verdicts passed "
            f"(method={qc_method}, {qc_unknown} unknown)"
        )
    if non_english > 0:
        warnings.append(f"{non_english}/{lang_evaluated} translation(s) still detected non-English")
    if n_dropped > 0:
        warnings.append(f"{n_dropped} translation(s) dropped an anonymization token")

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
        "translation_quality": {
            "n_fail": len(fail_checks),
            "n_warn": len(warn_checks),
            "verdict": overall,
            "acceptable": overall in {"pass", "warn"},
            "qc_pass_rate": qc_pass_rate,
            "qc_method": qc_method,
            "non_english_rate": non_english_rate,
            "token_preservation_rate": preservation_rate,
        },
        "checks": checks,
        "warnings": warnings,
        "overall": overall,
    }


if __name__ == "__main__":
    run_grader(grade)
