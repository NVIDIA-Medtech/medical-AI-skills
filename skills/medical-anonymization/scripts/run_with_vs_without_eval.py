#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""With-skill vs without-skill evaluation for medical-anonymization.

Compares:
  WITH:    medical-anonymization/SKILL.md contract (anonymize_medical_data.py)
  WITHOUT: upstream NeMo README baseline (without_skill_baseline.py)

Tasks (same staged inputs both arms):
  1. dicom-metadata — 85-study flat CSV
  2. ehr-csv         — mixed structured + text
  3. reports         — radiology reports preview

Writes: with_vs_without_report.json + markdown summary.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from metadata_formats import read_jsonl  # noqa: E402

PYTHON = Path("/home/marc/.conda/envs/reports-openai/bin/python")
WITH_ENTRY = SCRIPT_DIR / "anonymize_medical_data.py"
WITHOUT_ENTRY = SCRIPT_DIR / "without_skill_baseline.py"
PROVIDERS = SKILL_ROOT / "references" / "providers.local-phi.yaml"
MODELS = SKILL_ROOT / "references" / "models.local-phi.yaml"

DEFAULT_DICOM = Path(
    "/home/marc/code/MRI_DICOM_HEAD_DATA_WITH_PHI/deidentified/metadata/dicom_metadata_full.csv"
)

# Failure mode taxonomy (tracked per task x arm)
FAILURE_MODES = [
    "invocation_nonzero_exit",
    "missing_run_report",
    "missing_nested_jsonl",
    "missing_kv_compact_jsonl",
    "missing_audit_jsonl",
    "missing_anonymized_csv",
    "dicom_phi_field_leak",
    "dicom_uid_not_remapped",
    "structured_id_not_hashed",
    "kv_round_trip_failed",
    "nemo_pipeline_failed",
    "text_bracket_token_missing",
    "no_structured_policy_applied",
    "no_format_evaluation",
]

PHI_COL_PATTERNS = re.compile(
    r"(PatientName|PatientID|AccessionNumber|InstitutionName|Operators|ReferringPhysician)",
    re.I,
)
UID_COLS = {"StudyInstanceUID", "SeriesInstanceUID", "SOPInstanceUID", "study_uid", "patient_uid"}

# Expected failure modes on the without-skill arm (demonstrate skill value, not regressions)
EXPECTED_WITHOUT_FAILURES: dict[str, set[str]] = {
    "dicom-metadata": {"no_structured_policy_applied"},
    "ehr": {"structured_id_not_hashed"},
    "reports": set(),
}


@dataclass
class TaskSpec:
    key: str
    input_path: Path
    input_kind: str
    id_column: str
    text_column: str | None = None
    text_columns: list[str] | None = None
    num_records: int | None = None
    local_only: bool = False


@dataclass
class ArmResult:
    arm: str
    task: str
    returncode: int
    seconds: float
    failures: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)


def run_cmd(cmd: list[str], timeout: int = 3600) -> tuple[int, float, str, str]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, round(time.perf_counter() - t0, 2), proc.stdout, proc.stderr


def unexpected_failures(arm: str, task: str, failures: list[str]) -> list[str]:
    if arm != "without":
        return failures
    allowed = EXPECTED_WITHOUT_FAILURES.get(task, set())
    return [f for f in failures if f not in allowed]


def load_run_report_timing(out_dir: Path) -> dict[str, Any]:
    report_path = out_dir / "run_report.json"
    if not report_path.exists():
        return {}
    report = json.loads(report_path.read_text(encoding="utf-8"))
    timing: dict[str, Any] = {}
    if "telemetry" in report:
        timing["run_report_telemetry"] = report["telemetry"]
    if "timing" in report:
        timing["run_report_timing"] = report["timing"]
    if "nemo_runs" in report:
        timing["nemo_runs"] = report["nemo_runs"]
    elif report.get("n_nemo_preview") is not None:
        timing["n_nemo_preview"] = report["n_nemo_preview"]
    return timing
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, round(time.perf_counter() - t0, 2), proc.stdout, proc.stderr


def grade_dicom_with(out_dir: Path, source_csv: Path) -> tuple[list[str], dict]:
    failures: list[str] = []
    metrics: dict[str, Any] = {}

    nested = out_dir / "deidentified_metadata_nested.jsonl"
    kv = out_dir / "deidentified_metadata_kv_compact.jsonl"
    audit = out_dir / "audit.jsonl"
    fmt_eval = out_dir / "format_evaluation.json"

    for p, mode in [(nested, "missing_nested_jsonl"), (kv, "missing_kv_compact_jsonl"), (audit, "missing_audit_jsonl")]:
        if not p.exists():
            failures.append(mode)

    if fmt_eval.exists():
        fe = json.loads(fmt_eval.read_text(encoding="utf-8"))
        metrics["format_evaluation"] = fe.get("formats", {})
        if not fe.get("formats", {}).get("round_trip_kv_to_nested"):
            failures.append("kv_round_trip_failed")
    else:
        failures.append("no_format_evaluation")

    # Spot-check: PatientID values should not match raw source
    if nested.exists() and source_csv.exists():
        src = pd.read_csv(source_csv, nrows=5, encoding="utf-8-sig", low_memory=False)
        recs = read_jsonl(nested)
        leaks = 0
        uid_unmapped = 0
        for rec in recs[:5]:
            attrs = rec.get("attributes", {})
            rid = rec["record_id"]
            src_row = src[src["study_uid"].astype(str) == str(rid)]
            if src_row.empty:
                continue
            for col in ("PatientID", "AccessionNumber", "InstitutionName"):
                if col not in attrs or col not in src_row.columns:
                    continue
                raw = str(src_row.iloc[0][col])
                new = str(attrs[col]["value"])
                if raw and raw == new:
                    leaks += 1
            for uid_col in ("study_uid", "patient_uid"):
                if uid_col in attrs and uid_col in src_row.columns:
                    raw_uid = str(src_row.iloc[0][uid_col])
                    new_uid = str(attrs[uid_col]["value"])
                    if raw_uid and raw_uid == new_uid:
                        uid_unmapped += 1
        metrics["phi_field_leaks_spotcheck"] = leaks
        metrics["uid_unmapped_spotcheck"] = uid_unmapped
        if leaks:
            failures.append("dicom_phi_field_leak")
        if uid_unmapped:
            failures.append("dicom_uid_not_remapped")

    return failures, metrics


def grade_dicom_without(out_dir: Path, source_csv: Path) -> tuple[list[str], dict]:
    failures: list[str] = []
    metrics: dict[str, Any] = {"expected_gaps": []}

    passthrough = out_dir / "metadata_passthrough.csv"
    if not passthrough.exists():
        failures.append("missing_anonymized_csv")
        return failures, metrics

    # Without-skill should NOT produce JSONL (expected gap)
    if not (out_dir / "deidentified_metadata_nested.jsonl").exists():
        metrics["expected_gaps"].append("missing_nested_jsonl")
    if not (out_dir / "audit.jsonl").exists():
        metrics["expected_gaps"].append("missing_audit_jsonl")

    # PHI should remain in passthrough
    src = pd.read_csv(source_csv, nrows=10, encoding="utf-8-sig", low_memory=False)
    out = pd.read_csv(passthrough, nrows=10, encoding="utf-8-sig", low_memory=False)
    phi_unchanged = 0
    for col in src.columns:
        if PHI_COL_PATTERNS.search(col) and col in out.columns:
            if src[col].astype(str).equals(out[col].astype(str)):
                phi_unchanged += 1
    metrics["phi_columns_unchanged"] = phi_unchanged
    metrics["no_structured_policy_applied"] = True
    failures.append("no_structured_policy_applied")  # expected failure mode for without arm

    return failures, metrics


def grade_csv_with(out_dir: Path, *, expect_nemo: bool) -> tuple[list[str], dict]:
    failures: list[str] = []
    metrics: dict[str, Any] = {}
    csv_out = out_dir / "anonymized_data.csv"
    kv = out_dir / "anonymized_data_kv.jsonl"
    if not csv_out.exists():
        failures.append("missing_anonymized_csv")
    if not kv.exists():
        failures.append("missing_kv_compact_jsonl")
    if csv_out.exists():
        text = csv_out.read_text(encoding="utf-8")
        metrics["has_kv_jsonl"] = kv.exists()
        if expect_nemo and "[" not in text:
            failures.append("text_bracket_token_missing")
        if "patient_mrn" in text.lower() or "MRN-" in text:
            # check hashing happened for structured cols
            if "MRN-99887766" in text or "MRN-44556677" in text:
                failures.append("structured_id_not_hashed")
    return failures, metrics


def grade_csv_without(out_dir: Path, fixture_name: str) -> tuple[list[str], dict]:
    failures: list[str] = []
    metrics: dict[str, Any] = {}
    csv_out = out_dir / "anonymized_data.csv"
    if not csv_out.exists():
        failures.append("missing_anonymized_csv")
        return failures, metrics
    text = csv_out.read_text(encoding="utf-8")
    if "MRN-99887766" in text or "MRN-44556677" in text:
        failures.append("structured_id_not_hashed")
        metrics["structured_leak"] = True
    if not (out_dir / "anonymized_data_kv.jsonl").exists():
        metrics["expected_gaps"] = ["missing_kv_compact_jsonl"]
    if fixture_name == "ehr" and "patient_mrn" in text:
        metrics["no_structured_policy_applied"] = True
    return failures, metrics


def run_task(task: TaskSpec, arm: str, out_root: Path) -> ArmResult:
    out_dir = out_root / arm / task.key
    out_dir.mkdir(parents=True, exist_ok=True)

    if arm == "with":
        cmd = [str(PYTHON), str(WITH_ENTRY), str(task.input_path), "--output-dir", str(out_dir)]
        if task.input_kind != "auto":
            cmd += ["--input-kind", task.input_kind]
        cmd += ["--id-column", task.id_column]
        if task.local_only:
            cmd.append("--local-only")
        if task.text_columns:
            cmd += ["--text-columns", *task.text_columns]
        elif task.text_column:
            cmd += ["--text-column", task.text_column]
        if task.num_records:
            cmd += ["--num-records", str(task.num_records)]
        if not task.local_only and task.text_column or task.text_columns:
            cmd += ["--model-providers", str(PROVIDERS), "--model-configs", str(MODELS)]
        if task.key == "dicom-metadata":
            # run format eval inside output
            rc, secs, stdout, stderr = run_cmd(cmd, timeout=120)
            if rc == 0:
                fe_cmd = [
                    str(PYTHON), str(SCRIPT_DIR / "evaluate_metadata_formats.py"),
                    str(task.input_path), "--output-dir", str(out_dir),
                    "--id-column", task.id_column,
                ]
                rc2, secs2, _, _ = run_cmd(fe_cmd, timeout=300)
                secs += secs2
                if rc2 != 0:
                    rc = rc2
        else:
            rc, secs, stdout, stderr = run_cmd(cmd, timeout=1800)
    else:
        cmd = [
            str(PYTHON), str(WITHOUT_ENTRY), str(task.input_path),
            "--output-dir", str(out_dir),
            "--input-kind", task.input_kind if task.input_kind != "auto" else "csv",
            "--id-column", task.id_column,
        ]
        if task.text_columns:
            cmd += ["--text-column", task.text_columns[0]]
        elif task.text_column:
            cmd += ["--text-column", task.text_column]
        if task.num_records:
            cmd += ["--num-records", str(task.num_records)]
        if task.input_kind == "csv" and (task.text_column or task.text_columns):
            cmd += ["--model-providers", str(PROVIDERS), "--model-configs", str(MODELS)]
        rc, secs, stdout, stderr = run_cmd(cmd, timeout=1800)

    failures: list[str] = []
    metrics: dict[str, Any] = {}
    if rc != 0:
        failures.append("invocation_nonzero_exit")
    if not (out_dir / "run_report.json").exists():
        failures.append("missing_run_report")

    if arm == "with":
        if task.key == "dicom-metadata":
            f2, m2 = grade_dicom_with(out_dir, task.input_path)
        else:
            f2, m2 = grade_csv_with(out_dir, expect_nemo=not task.local_only and bool(task.text_columns or task.text_column))
    else:
        if task.key == "dicom-metadata":
            f2, m2 = grade_dicom_without(out_dir, task.input_path)
        else:
            f2, m2 = grade_csv_without(out_dir, task.key)

    failures.extend(f2)
    metrics.update(m2)
    metrics.update(load_run_report_timing(out_dir))
    metrics["stderr_tail"] = stderr[-500:] if stderr else ""
    metrics["stdout_tail"] = stdout[-500:] if stdout else ""

    unexpected = unexpected_failures(arm, task.key, failures)

    return ArmResult(
        arm=arm, task=task.key, returncode=rc, seconds=secs,
        failures=sorted(set(failures)), metrics=metrics,
        artifacts={"output_dir": str(out_dir), "unexpected_failures": unexpected},
    )


def build_report(results: list[ArmResult]) -> dict:
    by_task: dict[str, dict] = {}
    for r in results:
        unexpected = r.artifacts.get("unexpected_failures", r.failures)
        by_task.setdefault(r.task, {})[r.arm] = {
            "returncode": r.returncode,
            "seconds": r.seconds,
            "failures": r.failures,
            "unexpected_failures": unexpected,
            "metrics": r.metrics,
            "pass": len(unexpected) == 0,
        }

    timing_with = sum(r.seconds for r in results if r.arm == "with")
    timing_without = sum(r.seconds for r in results if r.arm == "without")
    with_passes = sum(1 for r in results if r.arm == "with" and not r.failures)
    without_passes = sum(
        1 for r in results
        if r.arm == "without" and not r.artifacts.get("unexpected_failures", r.failures)
    )

    per_task_timing: dict[str, dict[str, float]] = {}
    for r in results:
        per_task_timing.setdefault(r.task, {})[r.arm] = r.seconds

    return {
        "evaluation": "medical-anonymization-with-vs-without",
        "failure_modes_tracked": FAILURE_MODES,
        "expected_without_failures": {k: sorted(v) for k, v in EXPECTED_WITHOUT_FAILURES.items()},
        "tasks": by_task,
        "summary": {
            "with_total_seconds": timing_with,
            "without_total_seconds": timing_without,
            "with_task_passes": with_passes,
            "without_task_passes": without_passes,
            "with_failures_by_mode": _count_modes(results, "with"),
            "without_failures_by_mode": _count_modes(results, "without"),
            "per_task_seconds": per_task_timing,
        },
        "telemetry": {
            "wall_seconds_total": round(timing_with + timing_without, 2),
            "wall_seconds_with": round(timing_with, 2),
            "wall_seconds_without": round(timing_without, 2),
        },
    }


def _count_modes(results: list[ArmResult], arm: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in results:
        if r.arm != arm:
            continue
        for f in r.failures:
            counts[f] = counts.get(f, 0) + 1
    return counts


def write_markdown(report: dict, path: Path) -> None:
    lines = [
        "# Medical Anonymization — With vs Without Skill",
        "",
        "## Failure modes tracked",
        "",
    ]
    for m in report["failure_modes_tracked"]:
        lines.append(f"- `{m}`")
    lines.extend([
        "",
        "## Timing summary",
        "",
        f"| Arm | Total seconds |",
        f"|-----|--------------:|",
        f"| with skill | {report['summary']['with_total_seconds']:.1f} |",
        f"| without skill | {report['summary']['without_total_seconds']:.1f} |",
        "",
        "### Per-task seconds",
        "",
        "| Task | with | without |",
        "|------|-----:|--------:|",
    ])
    for task, secs in report["summary"].get("per_task_seconds", {}).items():
        lines.append(
            f"| {task} | {secs.get('with', 0):.1f} | {secs.get('without', 0):.1f} |"
        )
    lines.extend([
        "",
        "## Per-task results",
        "",
    ])
    for task, arms in report["tasks"].items():
        lines.append(f"### {task}")
        lines.append("")
        lines.append("| Arm | Seconds | Pass | Failures |")
        lines.append("|-----|--------:|:----:|----------|")
        for arm in ("with", "without"):
            if arm in arms:
                a = arms[arm]
                fail_display = ", ".join(a["failures"]) or "—"
                if arm == "without" and a.get("unexpected_failures") != a["failures"]:
                    expected = set(a["failures"]) - set(a["unexpected_failures"])
                    if expected:
                        fail_display += f" (expected: {', '.join(sorted(expected))})"
                lines.append(
                    f"| {arm} | {a['seconds']:.1f} | {'yes' if a['pass'] else 'no'} | {fail_display} |"
                )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", default="/tmp/medical_anon_with_vs_without")
    p.add_argument("--dicom-dataset", default=str(DEFAULT_DICOM))
    p.add_argument("--report-num-records", type=int, default=3)
    args = p.parse_args()

    out_root = Path(args.output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    tasks = [
        TaskSpec(
            key="dicom-metadata",
            input_path=Path(args.dicom_dataset),
            input_kind="dicom-metadata-csv",
            id_column="study_uid",
            local_only=True,
        ),
        TaskSpec(
            key="ehr",
            input_path=SKILL_ROOT / "fixtures" / "sample_ehr.csv",
            input_kind="csv",
            id_column="record_id",
            text_columns=["note_text"],
            num_records=2,
        ),
        TaskSpec(
            key="reports",
            input_path=SKILL_ROOT / "fixtures" / "batch00_reports_w_PHI.csv",
            input_kind="csv",
            id_column="study_uid",
            text_columns=["report_w_PHI"],
            num_records=args.report_num_records,
        ),
    ]

    results: list[ArmResult] = []
    for task in tasks:
        for arm in ("with", "without"):
            results.append(run_task(task, arm, out_root))

    report = build_report(results)
    json_path = out_root / "with_vs_without_report.json"
    md_path = out_root / "with_vs_without_report.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, md_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
