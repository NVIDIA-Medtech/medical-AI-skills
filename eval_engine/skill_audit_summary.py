#!/usr/bin/env python3
"""Summarize skill_completeness_v1 batch audits with expected-negative handling."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

EXPECTED_NEGATIVE_TARGET = "negative_sloppy_skill"


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def row_from_output(path: Path, *, target: str | None = None) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    target_name = target or Path(str(payload.get("target_skill") or path.parent.name)).name
    tier1 = payload.get("tier1_structural") or {}
    tier2 = payload.get("tier2_spec_honesty") or {}
    lifecycle = payload.get("capability_lifecycle") or {}
    return {
        "target": target_name,
        "target_path": str(payload.get("target_skill") or path),
        "overall": payload.get("overall"),
        "lifecycle": lifecycle.get("status") or "unknown",
        "tier1_passed": tier1.get("checks_passed", 0),
        "tier1_total": tier1.get("checks_total", 0),
        "tier2_passed": tier2.get("checks_passed", 0),
        "tier2_total": tier2.get("checks_total", 0),
        "blocking": int(payload.get("blocking_issues_count") or 0),
        "advisory": int(payload.get("advisory_issues_count") or 0),
    }


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    real_rows = [row for row in rows if row.get("target") != EXPECTED_NEGATIVE_TARGET]
    negative_rows = [row for row in rows if row.get("target") == EXPECTED_NEGATIVE_TARGET]
    unexpected_failures = [
        row
        for row in real_rows
        if row.get("overall") != "pass"
    ]
    advisory_failures = [
        row
        for row in real_rows
        if int(row.get("advisory") or 0) > 0
    ]
    calibration_failures: list[dict[str, Any]] = []
    if len(negative_rows) != 1:
        calibration_failures.append(
            {
                "target": EXPECTED_NEGATIVE_TARGET,
                "reason": f"expected exactly one calibration fixture row, got {len(negative_rows)}",
            }
        )
    elif negative_rows[0].get("overall") != "fail":
        calibration_failures.append(
            {
                "target": EXPECTED_NEGATIVE_TARGET,
                "reason": "expected calibration fixture to fail skill_completeness_v1",
                "overall": negative_rows[0].get("overall"),
            }
        )

    audit_status = (
        "pass"
        if not unexpected_failures and not advisory_failures and not calibration_failures
        else "fail"
    )
    return {
        "audit_status": audit_status,
        "skill_audit_runs": len(rows),
        "passed": sum(1 for row in rows if row.get("overall") == "pass"),
        "failed": sum(1 for row in rows if row.get("overall") == "fail"),
        "real_runs": len(real_rows),
        "real_passed": sum(1 for row in real_rows if row.get("overall") == "pass"),
        "real_failed": sum(1 for row in real_rows if row.get("overall") == "fail"),
        "real_advisory_issues": sum(int(row.get("advisory") or 0) for row in real_rows),
        "expected_negative_fixture": negative_rows[0] if negative_rows else None,
        "unexpected_failures": unexpected_failures,
        "advisory_failures": advisory_failures,
        "calibration_failures": calibration_failures,
        "rows": rows,
    }


def summarize_single_output(path: Path, *, target: str | None = None) -> dict[str, Any]:
    row = row_from_output(path, target=target)
    issues: list[str] = []
    if row.get("overall") != "pass":
        issues.append(f"overall={row.get('overall')}")
    if int(row.get("advisory") or 0) > 0:
        issues.append(f"advisory={row.get('advisory')}")
    return {
        "audit_status": "pass" if not issues else "fail",
        "row": row,
        "issues": issues,
    }


def format_single_summary(summary: dict[str, Any]) -> str:
    row = summary["row"]
    t1 = f"{row['tier1_passed']}/{row['tier1_total']}"
    t2 = f"{row['tier2_passed']}/{row['tier2_total']}"
    lines = [
        "",
        "=== skill_completeness_v1 single audit ===",
        f"  target: {row['target']}",
        f"  overall: {row['overall']}",
        f"  lifecycle: {row['lifecycle']}",
        f"  tier1: {t1}",
        f"  tier2: {t2}",
        f"  blocking issues: {row['blocking']}",
        f"  advisory issues: {row['advisory']}",
        f"  audit status: {summary['audit_status']}",
    ]
    if summary["issues"]:
        lines.append("  strict failures: " + ", ".join(summary["issues"]))
    return "\n".join(lines) + "\n"


def format_summary(summary: dict[str, Any]) -> str:
    lines = [
        "",
        "=== skill_completeness_v1 audit summary ===",
        (
            f"  {summary['skill_audit_runs']} runs: "
            f"{summary['passed']} pass, {summary['failed']} fail"
        ),
        (
            f"  real specs: {summary['real_passed']}/{summary['real_runs']} pass, "
            f"{summary['real_failed']} fail, "
            f"{summary['real_advisory_issues']} advisory issues"
        ),
    ]
    negative = summary.get("expected_negative_fixture")
    if negative:
        lines.append(
            "  calibration fixture "
            f"{EXPECTED_NEGATIVE_TARGET}: {negative.get('overall')} "
            "(expected fail)"
        )
    else:
        lines.append(f"  calibration fixture {EXPECTED_NEGATIVE_TARGET}: missing")
    lines.extend(
        [
            f"  audit status: {summary['audit_status']}",
            "",
            f"  {'target':<48s} {'overall':<8s} {'life':<10s}  tier1   tier2   blk  adv",
        ]
    )
    for row in summary["rows"]:
        t1 = f"{row['tier1_passed']}/{row['tier1_total']}"
        t2 = f"{row['tier2_passed']}/{row['tier2_total']}"
        lines.append(
            f"  {row['target']:<48s} {row['overall']:<8s} "
            f"{row.get('lifecycle', 'unknown'):<10s}  "
            f"{t1:<6s}  {t2:<6s}  {row['blocking']:<3d}  {row['advisory']:<3d}"
        )
    if summary["unexpected_failures"]:
        failed = ", ".join(row["target"] for row in summary["unexpected_failures"])
        lines.extend(["", f"Unexpected real-spec failures: {failed}"])
    if summary["advisory_failures"]:
        failed = ", ".join(
            f"{row['target']} ({row['advisory']})"
            for row in summary["advisory_failures"]
        )
        lines.extend(["", f"Real-spec advisory issues must be resolved: {failed}"])
    if summary["calibration_failures"]:
        reasons = "; ".join(item["reason"] for item in summary["calibration_failures"])
        lines.extend(["", f"Calibration failure: {reasons}"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        sys.stderr.write(
            "Usage: python -m eval_engine.skill_audit_summary "
            "<out_root|output.json>\n"
        )
        return 2
    path = Path(args[0])
    if path.is_file():
        summary = summarize_single_output(path)
        sys.stdout.write(format_single_summary(summary))
        return 0 if summary["audit_status"] == "pass" else 1

    out_root = path
    rows = load_rows(out_root / "_rows.jsonl")
    summary = summarize_rows(rows)
    (out_root / "_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    sys.stdout.write(format_summary(summary))
    return 0 if summary["audit_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
