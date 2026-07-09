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

"""Anonymize radiology reports with NeMo Anonymizer (Replace mode).

Wraps the upstream ``nemo-anonymizer`` pipeline (GLiNER-PII detection + LLM
augmentation/validation, then a Replace strategy) through its documented
``Anonymizer`` Python API and packages it as an MR-RATE ``reports_preprocessing``
stage-01 skill.

Detected PHI entities are replaced in place. Default strategy ``redact`` maps
each entity to a bracketed role token, e.g.::

    "Patient: John A. Doe"  ->  "Patient: [PATIENT]"
    "MRN: 12345678"         ->  "MRN: [PATIENT_MRN]"
    "Dr. Emily S. Patel"    ->  "Dr. [DOCTOR]"

Progress/diagnostics go to STDERR. The single machine-readable JSON summary is
the only thing printed to STDOUT (Medical AI Skills invariant), so an agent or
grader can parse it directly.

Usage::

    # Preview a few rows (cheap; writes trace parquet)
    python anonymize_reports.py REPORTS_CSV --output-dir OUT --num-records 5

    # Full run on every row
    python anonymize_reports.py REPORTS_CSV --output-dir OUT --full

    # Contextual LLM substitutes instead of bracketed redaction
    python anonymize_reports.py REPORTS_CSV --output-dir OUT --full --strategy substitute
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd
from anonymizer import (
    Anonymizer,
    AnonymizerConfig,
    AnonymizerInput,
    Detect,
    Redact,
)
from anonymizer.logging import LoggingConfig, configure_logging

SKILL_NAME = "report-anonymization"
ANONYMIZED_CSV_NAME = "anonymized_reports.csv"
RUN_REPORT_NAME = "run_report.json"
PREVIEW_PARQUET_NAME = "preview.parquet"

OUTPUT_COLUMNS = ["study_uid", "report"]

PHI_SCOPE_DISCLAIMER = (
    "Replaces PHI entities detected by NeMo Anonymizer (GLiNER-PII + LLM "
    "augment/validate). It is NOT a regulatory de-identifier and does not "
    "guarantee removal of all PHI: entities the detector never proposes are not "
    "replaced, and residual-leak accounting only covers detected entities. "
    "Review output before sharing data. Not for clinical use."
)

# NeMo Replace-mode pipeline stages (mapped to trace_dataframe columns).
_PIPELINE_STAGES: tuple[tuple[int, str, str, str], ...] = (
    (1, "raw_gliner_detection", "_raw_detected_entities", "entities"),
    (2, "seed_validation", "_validated_entities", "decisions"),
    (3, "entity_augmentation", "_augmented_entities", "entities"),
    (4, "final_entity_merge", "final_entities", "entities"),
    (5, "replacement", "_replacement_map", "replacements"),
)

# Rough per-record detection time on build.nvidia.com (GLiNER + LLM validator).
# Used only for a startup ETA hint on stderr, never for accounting.
_EST_SECS_PER_RECORD = 6.0

# Role-based entity vocabulary. GLiNER is zero-shot, so these are natural-language
# CONCEPTS detected by context (e.g. "Patient: John Doe" -> patient). Passing
# entity_labels switches GLiNER to STRICT mode: only these labels are detected,
# so every PHI type to scrub MUST be listed or it leaks.
DEFAULT_ENTITY_LABELS = [
    "patient",             # patient full name       -> [PATIENT]
    "patient_mrn",         # medical record number   -> [PATIENT_MRN]
    "doctor",              # physician names         -> [DOCTOR]
    "date_of_birth",       # -> [DATE_OF_BIRTH]
    "age",                 # -> [AGE]
    "sex",                 # -> [SEX]
    "date",                # service/study/report    -> [DATE]
    "accession_number",    # -> [ACCESSION_NUMBER]
    "institution",         # facility/hospital name  -> [INSTITUTION]
]


# --------------------------------------------------------------------------- #
# Logging (stderr only; stdout is reserved for the JSON summary)
# --------------------------------------------------------------------------- #
def _ts() -> str:
    return time.strftime("%H:%M:%S")


def log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", file=sys.stderr, flush=True)


class Heartbeat:
    """Print periodic status to stderr while a long remote call is in flight."""

    def __init__(self, message: str, interval: float = 15.0) -> None:
        self.message = message
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._start = 0.0

    def __enter__(self) -> "Heartbeat":
        self._start = time.perf_counter()

        def loop() -> None:
            while not self._stop.wait(self.interval):
                elapsed = time.perf_counter() - self._start
                log(f"{self.message} ({elapsed:.0f}s elapsed...)")

        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_args: Any) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)


# --------------------------------------------------------------------------- #
# Environment / input inspection
# --------------------------------------------------------------------------- #
def check_environment() -> bool:
    has_key = bool(os.environ.get("NVIDIA_API_KEY"))
    if has_key:
        log("NVIDIA_API_KEY: set")
    else:
        log("NVIDIA_API_KEY: NOT SET - remote detection on build.nvidia.com will fail (401)")
        log("Export your key: export NVIDIA_API_KEY='nvapi-...'")
    return has_key


def inspect_input(source: str, text_column: str, num_records: int | None, full: bool) -> dict:
    """Load input CSV locally and return summary stats (no remote calls)."""
    t0 = time.perf_counter()
    try:
        df = pd.read_csv(source, encoding="utf-8-sig")
    except FileNotFoundError as exc:
        raise SystemExit(f"Input CSV not found: {source}") from exc
    except (pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise SystemExit(f"Could not parse input CSV {source}: {exc}") from exc
    elapsed = time.perf_counter() - t0

    if text_column not in df.columns:
        raise SystemExit(
            f"Text column {text_column!r} not in {source}; columns: {list(df.columns)}"
        )

    total_rows = len(df)
    if total_rows == 0:
        raise SystemExit(f"Input CSV {source} has no rows.")
    target_rows = total_rows if full else min(num_records or 4, total_rows)

    lengths = df[text_column].astype(str).str.len().iloc[:target_rows]
    return {
        "total_rows": total_rows,
        "target_rows": int(target_rows),
        "min_chars": int(lengths.min()),
        "max_chars": int(lengths.max()),
        "mean_chars": float(lengths.mean()),
        "load_secs": elapsed,
    }


def print_startup_summary(args: argparse.Namespace, config: AnonymizerConfig, stats: dict) -> None:
    mode = "full run" if args.full else f"preview ({stats['target_rows']} rows)"
    est_secs = stats["target_rows"] * _EST_SECS_PER_RECORD
    log("=" * 72)
    log(f"NeMo Anonymizer - {SKILL_NAME}")
    log("=" * 72)
    log(f"Mode         : {mode}")
    log(f"Source       : {args.source}")
    log(f"Output dir   : {args.output_dir}")
    log(f"Text column  : {args.text_column}")
    log("Strategy     : redact -> [LABEL] tokens")
    log(f"Labels       : {', '.join(config.detect.entity_labels or [])}")
    log(f"Threshold    : {config.detect.gliner_threshold}")
    log(f"Input rows   : {stats['total_rows']} total, processing {stats['target_rows']}")
    log(
        f"Report size  : {stats['min_chars']}-{stats['max_chars']} chars "
        f"(mean {stats['mean_chars']:.0f})"
    )
    log("Execution    : remote - build.nvidia.com (GLiNER detector + LLM validator/augmenter)")
    log(
        f"ETA (detect) : ~{est_secs:.0f}s for {stats['target_rows']} record(s) "
        f"(~{_EST_SECS_PER_RECORD:.0f}s/record; varies with length and rate limits)"
    )
    log("=" * 72)


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
def build_config(args: argparse.Namespace) -> tuple[AnonymizerInput, AnonymizerConfig]:
    """Single source of truth for what we anonymize and how."""
    data = AnonymizerInput(
        source=args.source,
        text_column=args.text_column,
        data_summary=(
            "English-language radiology reports written as clinical prose. "
            "Each row is one report. Explicit PHI in the header and signature includes "
            "patient name, patient full name (first, middle possible abbriviation, last),MRN, date of birth, age, sex, date of service, accession number, "
            "referring physician, signing physician, physician npi_number, physicianlicense_number, "
            "dicom_uid, study_id, device_serial_number, institution/facility name."
            "Do not anonymize clinical findings, treatment plans, and medical terminology. "
        ),
    )
    detect = Detect(
        entity_labels=list(DEFAULT_ENTITY_LABELS),
        # Lower gliner_threshold (e.g. 0.2) for recall, raise (0.5) to cut cost/FPs.
        gliner_threshold=args.gliner_threshold,
    )
    config = AnonymizerConfig(
        detect=detect,
        # Redact: each detected entity becomes "[LABEL]" (normalize_label uppercases it).
        replace=Redact(format_template="[{label}]"),
        emit_telemetry=not args.no_emit_telemetry,
    )
    return data, config


# --------------------------------------------------------------------------- #
# Output shaping
# --------------------------------------------------------------------------- #
def to_output_dataframe(result, text_column: str, id_column: str) -> pd.DataFrame:
    """Map anonymizer output to id,report schema using the trace dataframe.

    ``result.dataframe`` drops passthrough columns such as study_uid, whereas
    ``trace_dataframe`` retains them.
    """
    df = result.trace_dataframe
    replaced_col = f"{text_column}_replaced"
    if replaced_col not in df.columns:
        raise SystemExit(
            f"Expected anonymized column {replaced_col!r}; got {list(df.columns)}"
        )
    out = df[[replaced_col]].rename(columns={replaced_col: "report"})
    if id_column in df.columns:
        out.insert(0, "study_uid", df[id_column].values)
    else:
        out.insert(0, "study_uid", range(len(out)))
    return out


def write_output(result, text_column: str, id_column: str, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out = to_output_dataframe(result, text_column, id_column)
    out.to_csv(output_path, index=False, encoding="utf-8-sig")
    log(f"Wrote {len(out)} anonymized row(s) to {output_path}")
    return len(out)


# --------------------------------------------------------------------------- #
# Trace parsing helpers
# --------------------------------------------------------------------------- #
def _as_list(value: Any) -> list:
    if value is None:
        return []
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, list):
        return value
    return [value]


def _parse_trace_cell(raw: Any) -> dict | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return raw if isinstance(raw, dict) else None


def _entity_label(entity: dict) -> str:
    return str(entity.get("label") or entity.get("proposed_label") or "unknown")


def _summarize_stage(trace_df: pd.DataFrame, column: str, payload_key: str) -> dict[str, Any]:
    """Aggregate one pipeline stage across all records in the trace dataframe."""
    records_with_data = item_count = pass_count = fail_count = 0
    label_counts: Counter[str] = Counter()
    decision_counts: Counter[str] = Counter()

    for raw in (trace_df[column] if column in trace_df.columns else []):
        cell = _parse_trace_cell(raw) if column == "_raw_detected_entities" else raw
        if not isinstance(cell, dict):
            continue
        items = _as_list(cell.get(payload_key, []))
        if not items:
            continue
        records_with_data += 1
        item_count += len(items)
        if payload_key == "decisions":
            for decision in items:
                action = str(decision.get("decision", "unknown"))
                decision_counts[action] += 1
                label_counts[_entity_label(decision)] += 1
                if action == "keep":
                    pass_count += 1
                elif action == "drop":
                    fail_count += 1
        else:
            for item in items:
                label_counts[_entity_label(item)] += 1

    scored = pass_count + fail_count
    return {
        "records_with_data": records_with_data,
        "items_total": item_count,
        "pass_count": pass_count if payload_key == "decisions" else None,
        "fail_count": fail_count if payload_key == "decisions" else None,
        "pass_pct": round(100.0 * pass_count / scored, 1) if scored else None,
        "decision_counts": dict(sorted(decision_counts.items())) if decision_counts else None,
        "label_counts": dict(sorted(label_counts.items())) if label_counts else None,
    }


def _detect_residual_phi_leaks(trace_df: pd.DataFrame, text_column: str, id_column: str) -> dict[str, Any]:
    """Find replacement-map originals that still appear verbatim in the output.

    Deterministic, comparable across runs: for every entity the pipeline mapped,
    flag the record if the original value survives in the replaced text. This is
    an informational telemetry signal, NOT a pass/fail gate: it does not catch
    PHI the detector never proposed (see phi_scope_disclaimer), and originals
    shorter than 3 chars (e.g. sex "M", age "45") are skipped because a bare
    substring match on them yields spurious hits inside unrelated words/numbers.
    """
    replaced_col = f"{text_column}_replaced"
    id_col = id_column if id_column in trace_df.columns else None
    leak_label_counts: Counter[str] = Counter()
    records_with_leaks = 0
    per_record: list[dict[str, Any]] = []

    for idx, row in trace_df.iterrows():
        replaced = str(row.get(replaced_col, ""))
        rmap = row.get("_replacement_map")
        if not isinstance(rmap, dict):
            continue
        row_leaks: list[dict[str, str]] = []
        for rep in _as_list(rmap.get("replacements", [])):
            original = str(rep.get("original", "")).strip()
            synthetic = str(rep.get("synthetic", "")).strip()
            label = str(rep.get("label", "unknown"))
            if not original or original == synthetic or len(original) < 3:
                continue
            if original in replaced:
                row_leaks.append({"label": label, "value": original})
                leak_label_counts[label] += 1
        if row_leaks:
            records_with_leaks += 1
            per_record.append({
                "row_index": int(idx),
                "study_uid": str(row[id_col]) if id_col else None,
                "leak_count": len(row_leaks),
                "leaks": row_leaks,
            })

    n = len(trace_df)
    return {
        "method": "replacement_map_verbatim",
        "n_evaluated": n,
        "n_leaked": records_with_leaks,
        "leak_rate": round(records_with_leaks / n, 6) if n else 0.0,
        "by_label": dict(sorted(leak_label_counts.items())),
        "per_record": per_record,
    }


def _summarize_failed_records(failed_records: list) -> dict[str, Any]:
    by_step: Counter[str] = Counter()
    details: list[dict[str, str]] = []
    for fr in failed_records:
        by_step[fr.step] += 1
        details.append({"record_id": fr.record_id, "step": fr.step, "reason": fr.reason})
    return {
        "total_failed": len(failed_records),
        "failed_by_step": dict(sorted(by_step.items())),
        "records": details,
    }


# --------------------------------------------------------------------------- #
# Telemetry
# --------------------------------------------------------------------------- #
def estimate_input_tokens(source: str, text_column: str, n_rows: int) -> dict[str, int]:
    """Best-effort tiktoken (cl100k_base) count over the processed text column.

    NeMo Anonymizer does not surface exact provider token usage per call, so this
    is a consistent cross-run estimate of the *input* scale, not an exact bill.
    """
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        df = pd.read_csv(source, encoding="utf-8-sig")
        texts = df[text_column].astype(str).iloc[:n_rows]
        counts = [len(enc.encode(t, disallowed_special=())) for t in texts]
        total = int(sum(counts))
        mean = int(total / len(counts)) if counts else 0
        return {"input_tokens_estimate": total, "mean_input_tokens_per_record": mean}
    except Exception:  # noqa: BLE001 - telemetry is best-effort
        return {"input_tokens_estimate": -1, "mean_input_tokens_per_record": -1}


def _anonymizer_version() -> str:
    try:
        import anonymizer

        return str(getattr(anonymizer, "version", "unknown"))
    except Exception:  # noqa: BLE001
        return "unknown"


# --------------------------------------------------------------------------- #
# Run report / summary assembly
# --------------------------------------------------------------------------- #
def build_summary(
    result,
    args: argparse.Namespace,
    *,
    n_written: int,
    timings: dict[str, float | None],
    input_tokens: dict[str, int],
    evaluated: bool,
    artifacts: dict[str, str | None],
) -> tuple[dict[str, Any], dict[str, Any]]:
    trace_df = result.trace_dataframe
    records_processed = len(trace_df)
    failed_summary = _summarize_failed_records(result.failed_records)
    records_passed = records_processed - failed_summary["total_failed"]

    stages: list[dict[str, Any]] = []
    entity_total = 0
    entity_by_label: dict[str, int] = {}
    for iteration, name, column, payload_key in _PIPELINE_STAGES:
        stats = _summarize_stage(trace_df, column, payload_key)
        if name == "final_entity_merge":
            entity_total = stats["items_total"]
            entity_by_label = stats["label_counts"] or {}
        stages.append({
            "iteration": iteration,
            "stage": name,
            "trace_column": column,
            "records_in": records_processed,
            "records_out": records_passed,
            "records_with_data": stats["records_with_data"],
            "items_total": stats["items_total"],
            "pass_count": stats["pass_count"],
            "fail_count": stats["fail_count"],
            "pass_pct": stats["pass_pct"],
            "decision_counts": stats["decision_counts"],
            "label_counts": stats["label_counts"],
        })

    leak = _detect_residual_phi_leaks(trace_df, args.text_column, args.id_column)
    # Trim the verbose per-record leak list out of the stdout summary; it stays in
    # the on-disk run report for auditing.
    leak_stdout = {k: v for k, v in leak.items() if k != "per_record"}

    evaluation = None
    if evaluated and "detection_valid" in result.dataframe.columns:
        df = result.dataframe
        scored = int(df["detection_valid"].notna().sum())
        passed = int(df["detection_valid"].eq(True).sum())
        failed = int(df["detection_valid"].eq(False).sum())
        evaluation = {
            "records_scored": scored,
            "pass_count": passed,
            "fail_count": failed,
            "pass_rate": round(passed / scored, 6) if scored else None,
            "wall_seconds": timings.get("evaluate"),
        }

    pipeline_secs = timings.get("pipeline") or 0.0
    rps = round(records_processed / pipeline_secs, 4) if pipeline_secs else None

    summary = {
        "skill": SKILL_NAME,
        "mode": "full" if args.full else "preview",
        "strategy": "redact",
        "n_reports": records_processed,
        "n_written": n_written,
        "records_passed": records_passed,
        "records_failed": failed_summary["total_failed"],
        "pass_rate": round(records_passed / records_processed, 6) if records_processed else 0.0,
        "entities": {"total": entity_total, "by_label": entity_by_label},
        "residual_phi_leak": leak_stdout,
        "evaluation": evaluation,
        "pipeline_stages": stages,
        "failed_records": failed_summary,
        "telemetry": {
            "wall_seconds": timings,
            "records_per_second": rps,
            "input_tokens_estimate": input_tokens["input_tokens_estimate"],
            "mean_input_tokens_per_record": input_tokens["mean_input_tokens_per_record"],
            "tokenizer": "cl100k_base",
            "execution": "remote:build.nvidia.com (NeMo Anonymizer bundled providers)",
            "detector": "gliner-pii (bundled provider)",
            "nemo_anonymizer_version": _anonymizer_version(),
        },
        "artifacts": artifacts,
        "phi_scope_disclaimer": PHI_SCOPE_DISCLAIMER,
    }
    # The on-disk report keeps the full leak detail.
    disk_report = dict(summary)
    disk_report["residual_phi_leak"] = leak
    return summary, disk_report


def print_run_report(summary: dict[str, Any]) -> None:
    """Human-readable stderr digest of the pipeline iterations."""
    log("=" * 72)
    log(f"NeMo Anonymizer - {SKILL_NAME} run report")
    log("=" * 72)
    log(
        f"Records      : {summary['n_reports']} processed, "
        f"{summary['records_passed']} passed, {summary['records_failed']} failed "
        f"({summary['pass_rate'] * 100:.1f}% passing)"
    )
    wc = summary["telemetry"]["wall_seconds"]
    log(
        f"Wall clock   : init={wc.get('init', 0):.1f}s, pipeline={wc.get('pipeline', 0):.1f}s, "
        f"evaluate={wc.get('evaluate') if wc.get('evaluate') is not None else 'n/a'}, "
        f"total={wc.get('total', 0):.1f}s"
    )
    for stage in summary["pipeline_stages"]:
        log(f"Iteration {stage['iteration']}: {stage['stage']}")
        log(f"  items total    : {stage['items_total']} across {stage['records_with_data']} record(s)")
        if stage["pass_count"] is not None:
            log(f"  validation     : {stage['pass_count']} keep, {stage['fail_count']} drop")
        if stage["label_counts"]:
            labels = ", ".join(f"{k}={v}" for k, v in stage["label_counts"].items())
            log(f"  PHI labels     : {labels}")
    leak = summary["residual_phi_leak"]
    log(
        f"Residual PHI : {leak['n_leaked']}/{leak['n_evaluated']} record(s) "
        f"({leak['leak_rate'] * 100:.1f}%) with unreplaced detected values"
    )
    if leak.get("by_label"):
        log("  leak types     : " + ", ".join(f"{k}={v}" for k, v in leak["by_label"].items()))
    if summary["failed_records"]["total_failed"]:
        log(f"Failed records : {summary['failed_records']['failed_by_step']}")
    log("=" * 72)


def write_run_report(report: dict[str, Any], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log(f"Wrote run report to {report_path}")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("reports_csv", nargs="?", default=None,
                   help="Path to input CSV with PHI-containing reports (positional).")
    p.add_argument("--source", default=None,
                   help="Alias for the positional input CSV (backward compatible).")
    p.add_argument("--output-dir", default=None,
                   help="Directory for anonymized_reports.csv + run_report.json.")
    p.add_argument("--output-path", default=None,
                   help="Alias: explicit output CSV path (run report written alongside).")
    p.add_argument("--text-column", default="report_w_PHI",
                   help="Column holding report text (default: report_w_PHI).")
    p.add_argument("--id-column", default="study_uid",
                   help="Unique id column copied through (default: study_uid).")
    p.add_argument("--gliner-threshold", type=float, default=0.3,
                   help="GLiNER detection threshold; lower=recall, higher=precision (default 0.3).")
    p.add_argument("--full", action="store_true", help="Run on the full dataset (default: preview).")
    p.add_argument("--num-records", type=int, default=4, help="Rows to preview (ignored with --full).")
    p.add_argument("--evaluate", action="store_true",
                   help="Run LLM-as-judge detection-validity scoring on the output.")
    p.add_argument("--no-emit-telemetry", action="store_true",
                   help="Disable NeMo Anonymizer's own anonymous run telemetry.")
    p.add_argument("--verbose", action="store_true", help="Debug logging from the anonymizer library.")
    return p


def resolve_paths(args: argparse.Namespace) -> None:
    """Normalise positional/flag input and output aliases onto args.source/output_dir."""
    args.source = args.reports_csv or args.source
    if not args.source:
        raise SystemExit("No input CSV given. Pass it positionally or via --source.")

    if args.output_path and not args.output_dir:
        # Explicit output CSV path: write there, run report alongside.
        args.output_dir = str(Path(args.output_path).parent)
        args._explicit_output_csv = Path(args.output_path)
    else:
        if not args.output_dir:
            raise SystemExit("No output location given. Pass --output-dir OUT (or --output-path FILE).")
        args._explicit_output_csv = None


def main() -> int:
    args = build_parser().parse_args()
    resolve_paths(args)

    t_run = time.perf_counter()
    configure_logging(LoggingConfig.debug() if args.verbose else LoggingConfig.verbose())

    check_environment()
    data, config = build_config(args)
    stats = inspect_input(args.source, args.text_column, args.num_records, args.full)
    print_startup_summary(args, config, stats)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    anon_csv = args._explicit_output_csv or (out_dir / ANONYMIZED_CSV_NAME)
    run_report_path = out_dir / RUN_REPORT_NAME
    preview_parquet_path = out_dir / PREVIEW_PARQUET_NAME

    log("Initializing anonymizer (loading model configs)...")
    t_init = time.perf_counter()
    anonymizer = Anonymizer()
    init_secs = time.perf_counter() - t_init
    log(f"Anonymizer ready ({init_secs:.1f}s)")

    log(f"Starting entity detection on {stats['target_rows']} record(s) - remote API calls in flight...")
    t_pipeline = time.perf_counter()
    with Heartbeat("Entity detection still running"):
        if args.full:
            result = anonymizer.run(config=config, data=data)
        else:
            result = anonymizer.preview(config=config, data=data, num_records=args.num_records)
    pipeline_secs = time.perf_counter() - t_pipeline
    log(f"Pipeline finished in {pipeline_secs:.1f}s")

    preview_written: str | None = None
    if not args.full:
        result.trace_dataframe.to_parquet(preview_parquet_path)
        preview_written = str(preview_parquet_path)
        log(f"Saved trace parquet: {preview_parquet_path}")

    n_written = write_output(result, args.text_column, args.id_column, anon_csv)

    evaluated = False
    evaluate_secs: float | None = None
    if args.evaluate:
        log("Running LLM-as-judge detection-validity evaluation...")
        t_eval = time.perf_counter()
        result = anonymizer.evaluate(result)
        evaluate_secs = time.perf_counter() - t_eval
        evaluated = True

    timings = {
        "init": round(init_secs, 2),
        "pipeline": round(pipeline_secs, 2),
        "evaluate": round(evaluate_secs, 2) if evaluate_secs is not None else None,
        "total": round(time.perf_counter() - t_run, 2),
    }
    input_tokens = estimate_input_tokens(args.source, args.text_column, stats["target_rows"])
    artifacts = {
        "anonymized_csv": str(anon_csv),
        "run_report_json": str(run_report_path),
        "preview_parquet": preview_written,
        "input_csv": str(args.source),
    }

    summary, disk_report = build_summary(
        result, args,
        n_written=n_written, timings=timings, input_tokens=input_tokens,
        evaluated=evaluated, artifacts=artifacts,
    )
    write_run_report(disk_report, run_report_path)
    print_run_report(summary)

    # Failure-first protocol: dropped rows are infra issues (rate limits, auth),
    # not strategy issues. Emit the summary either way, then signal via exit code.
    if summary["records_failed"]:
        log(f"{summary['records_failed']} record(s) failed; see failed_records. "
            "Fix dropped rows (rate limits/auth) before tuning strategy.")

    # STDOUT: the single machine-readable JSON summary (Medical AI Skills invariant).
    print(json.dumps(summary, indent=2))
    return 1 if summary["records_failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
