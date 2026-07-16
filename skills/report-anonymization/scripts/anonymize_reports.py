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
import re
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
    PrivacyGoal,
    Redact,
    Rewrite,
    RiskTolerance,
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
    "patient",  # patient full name       -> [PATIENT]
    "patient_mrn",  # medical record number   -> [PATIENT_MRN]
    "doctor",  # physician names         -> [DOCTOR]
    "date_of_birth",  # -> [DATE_OF_BIRTH]
    "age",  # -> [AGE]
    "sex",  # -> [SEX]
    "date",  # service/study/report    -> [DATE]
    "accession_number",  # -> [ACCESSION_NUMBER]
    "institution",  # facility/hospital name  -> [INSTITUTION]
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
def check_environment(local: bool = False) -> bool:
    has_key = bool(os.environ.get("NVIDIA_API_KEY"))
    if local:
        log("Local model providers configured - hosted build.nvidia.com is not required.")
        log(f"NVIDIA_API_KEY: {'set' if has_key else 'not set (fine for fully local serving)'}")
        return has_key
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
    if config.rewrite is not None:
        log(
            f"Strategy     : rewrite -> full-passage rewrite "
            f"(max_repair_iterations={config.rewrite.max_repair_iterations})"
        )
    else:
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
            "patient name, MRN, date of birth, age, sex, date of service, accession number, "
            "referring physician, signing physician, physician npi_number, physicianlicense_number, "
            "dicom_uid, study_id, device_serial_number, institution/facility name."
            "Do not anonymize clinical findings, treatment plans, and medical terminology. "
        ),
    )
    if getattr(args, "mode", "redact") == "rewrite":
        # Rewrite mode: an LLM rewrites the whole passage to remove PHI, with a
        # built-in evaluate->repair loop (max_repair_iterations). Output is prose,
        # NOT [TOKEN]s. All rewrite roles map (via the gpt-oss-120b /
        # nemotron-30b-thinking aliases) to the local model in models.local.yaml.
        privacy_goal = PrivacyGoal(
            protect=(
                "Direct and quasi identifiers in the report header and signature: patient "
                "name, medical record number, date of birth, age, sex, service and study "
                "dates, accession number, referring and signing physician names, and the "
                "institution or facility name."
            ),
            preserve=(
                "All clinical content: technique, findings, measurements, impressions, "
                "diagnoses, and medical terminology, so the de-identified report stays "
                "clinically faithful."
            ),
        )
        config = AnonymizerConfig(
            rewrite=Rewrite(
                privacy_goal=privacy_goal,
                risk_tolerance=RiskTolerance(args.risk_tolerance),
                max_repair_iterations=args.max_repair_iterations,
                strict_entity_protection=args.strict_entity_protection,
            ),
            emit_telemetry=not args.no_emit_telemetry,
        )
        return data, config

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
    out_col = next(
        (c for c in (f"{text_column}_replaced", f"{text_column}_rewritten") if c in df.columns),
        None,
    )
    if out_col is None:
        raise SystemExit(
            f"Expected anonymized column {text_column}_replaced or {text_column}_rewritten; "
            f"got {list(df.columns)}"
        )
    out = df[[out_col]].rename(columns={out_col: "report"})
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


def _detect_residual_phi_leaks(
    trace_df: pd.DataFrame, text_column: str, id_column: str
) -> dict[str, Any]:
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
            per_record.append(
                {
                    "row_index": int(idx),
                    "study_uid": str(row[id_col]) if id_col else None,
                    "leak_count": len(row_leaks),
                    "leaks": row_leaks,
                }
            )

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

    is_rewrite = getattr(args, "mode", "redact") == "rewrite"
    stages: list[dict[str, Any]] = []
    entity_total = 0
    entity_by_label: dict[str, int] = {}
    if not is_rewrite:
        for iteration, name, column, payload_key in _PIPELINE_STAGES:
            stats = _summarize_stage(trace_df, column, payload_key)
            if name == "final_entity_merge":
                entity_total = stats["items_total"]
                entity_by_label = stats["label_counts"] or {}
            stages.append(
                {
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
                }
            )
        leak = _detect_residual_phi_leaks(trace_df, args.text_column, args.id_column)
    else:
        # Rewrite mode has a different trace (no GLiNER replacement map); the
        # verbatim replacement-map leak check does not apply. Residual PHI is
        # instead scored by the experiment's LLM judge downstream.
        leak = {
            "method": "rewrite mode: full-passage rewrite, no replacement map",
            "n_evaluated": records_processed,
            "n_leaked": None,
            "leak_rate": None,
            "by_label": {},
        }
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
        "strategy": "rewrite" if is_rewrite else "redact",
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
            "mean_seconds_per_report": (
                round(pipeline_secs / records_processed, 2)
                if records_processed and pipeline_secs
                else None
            ),
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
    aspr = summary["telemetry"].get("mean_seconds_per_report")
    log(
        f"Avg / report : {aspr:.2f}s per report (mean over {summary['n_reports']} reports)"
        if aspr is not None
        else "Avg / report : n/a"
    )
    for stage in summary["pipeline_stages"]:
        log(f"Iteration {stage['iteration']}: {stage['stage']}")
        log(
            f"  items total    : {stage['items_total']} across {stage['records_with_data']} record(s)"
        )
        if stage["pass_count"] is not None:
            log(f"  validation     : {stage['pass_count']} keep, {stage['fail_count']} drop")
        if stage["label_counts"]:
            labels = ", ".join(f"{k}={v}" for k, v in stage["label_counts"].items())
            log(f"  PHI labels     : {labels}")
    leak = summary["residual_phi_leak"]
    if leak.get("leak_rate") is None:
        log(f"Residual PHI : n/a ({leak.get('method', 'not computed')})")
    else:
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
# Iterative redaction (critic-hinted; precision via the anonymizer's validator)
# --------------------------------------------------------------------------- #
_CRITIC_PROMPT = """You are a PHI critic for radiology reports. You do NOT edit text — you review it and REPORT every span you suspect is Protected Health Information (PHI).

Report text:
\"\"\"
{text}
\"\"\"

Find ALL suspected PHI: personal identifiers such as patient or doctor name, MRN, date of birth, age, sex, service/study/report date, accession number, phone/fax number, institution/facility name, address, or any other unique identifier. Do NOT list clinical content (anatomy, findings, measurements, units, medical terminology, common words).

Text already contains redaction placeholders like [PATIENT], [DOCTOR], or [DATE] — these are NOT PHI; the identifier has already been removed. Do NOT report any span that contains a placeholder. In "exact_string" report ONLY the raw leaked identifier itself — never include placeholders, titles (Dr., Mr., MD, DO), or role/specialty words (ENT, radiology, referring physician).

Return ONLY a JSON array, one object per suspected PHI span:
[{{"category": "<e.g. patient|doctor|mrn|date_of_birth|date|age|sex|accession_number|institution|phone_number>", "value": "<the suspected PHI value, normalized>", "exact_string": "<the substring exactly as it appears verbatim in the report text>"}}]
Return [] if you find no PHI. Include an item only when you are confident it is a personal identifier, not clinical content."""


def _parse_json_list(raw: str) -> list:
    """Extract a JSON array from an LLM response; tolerant of code fences / preamble."""
    s = (raw or "").strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[-1]
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
    start, end = s.find("["), s.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return []
    try:
        val = json.loads(s[start : end + 1])
    except json.JSONDecodeError:
        return []
    return val if isinstance(val, list) else []


def _critic_review(client, model: str, text: str) -> list[dict]:
    """LLM critic: return [{category, value, exact_string}] suspected PHI. [] on failure."""
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": _CRITIC_PROMPT.format(text=text)}],
            temperature=0.0,
            max_tokens=1500,
        )
        items = _parse_json_list(resp.choices[0].message.content or "")
    except Exception as exc:  # noqa: BLE001
        log(f"  [critic] error (treated as no residual): {exc}")
        return []
    out: list[dict] = []
    for it in items:
        if not (isinstance(it, dict) and str(it.get("exact_string", "")).strip()):
            continue
        es = str(it["exact_string"]).strip()
        # Drop any span that overlaps an already-inserted redaction placeholder
        # (e.g. "[PATIENT]", "Dr. [DOCTOR] MD", "[DOCTOR], ENT"). The identifier has
        # already been removed; the remainder is only scaffolding (titles, specialties).
        # Without this, the critic re-flags redacted spans forever -> no convergence and
        # false human-review flags. A genuinely separate leak is reported as its own
        # atomic item (no placeholder in it) and is kept.
        _placeholder = re.compile(r"\[[A-Za-z0-9_]+\]")
        if _placeholder.search(es) or _placeholder.search(str(it.get("value", ""))):
            continue
        out.append(
            {
                "category": (str(it.get("category", "phi")).strip() or "phi"),
                "value": (str(it.get("value", es)).strip() or es),
                "exact_string": es,
            }
        )
    return out


def _threshold_schedule(base: float, n: int) -> list[float]:
    """One descending GLiNER threshold per pass (more recall each pass); floor 0.1."""
    out, t = [], float(base)
    for _ in range(max(1, n)):
        out.append(round(max(t, 0.1), 3))
        t -= 0.1
    return out


def _aggregate_exemplars(residual: dict[str, list[dict]], cap: int = 60) -> list[dict]:
    """Distinct (category, value) suspected-PHI exemplars across all still-leaking rows."""
    seen: dict[tuple[str, str], dict] = {}
    for items in residual.values():
        for it in items:
            seen.setdefault((it["category"], it["value"]), it)
    return list(seen.values())[:cap]


def _hint_block(exemplars: list[dict]) -> str:
    if not exemplars:
        return ""
    listed = "; ".join(f"'{e['value']}' ({e['category']})" for e in exemplars)
    return (
        "\n\nPRIOR PASSES LEFT THESE SUSPECTED PHI VALUES UN-REDACTED — redact these and any "
        "similar personal identifiers, UNLESS they are clearly clinical content (anatomy, "
        f"findings, measurements, medical terms): {listed}"
    )


def run_iterative_redaction(
    anonymizer, args: argparse.Namespace, work_dir: Path, base_data_summary: str | None
) -> dict[str, Any]:
    """Loop: anonymizer redacts (its validator = precision) -> LLM critic lists suspected
    residual PHI -> that list becomes hints for the next pass. Redacted text feeds forward;
    only still-leaking rows are re-processed. A value the critic keeps flagging past
    ``--revert-flag-n`` passes is flagged for human review.
    """
    from openai import OpenAI

    df = pd.read_csv(args.source, encoding="utf-8-sig")
    id_col, text_col = args.id_column, args.text_column
    if id_col not in df.columns:
        df[id_col] = [str(i) for i in range(len(df))]
    if not args.full:
        df = df.head(max(1, args.num_records))
    current = {
        str(r[id_col]): (str(r[text_col]) if isinstance(r[text_col], str) else "")
        for _, r in df.iterrows()
    }
    order = list(current.keys())

    critic = OpenAI(base_url=args.critic_base_url, api_key=args.critic_api_key or "EMPTY")
    thresholds = _threshold_schedule(args.gliner_threshold, args.max_redaction_iterations)
    iter_work = work_dir / "iter_work"  # per-pass inputs (audit trail), off the main output dir
    iter_work.mkdir(parents=True, exist_ok=True)

    hint_counts: dict[tuple[str, str], int] = {}
    review_flags: dict[str, list[dict]] = {}
    iterations: list[dict] = []
    leaking = list(order)
    data_summary = base_data_summary or ""

    for i, threshold in enumerate(thresholds, start=1):
        if not leaking:
            break
        t_it = time.perf_counter()
        sub_path = iter_work / f"_iter{i}_input.csv"
        pd.DataFrame([{id_col: u, text_col: current[u]} for u in leaking]).to_csv(
            sub_path, index=False, encoding="utf-8-sig"
        )
        data = AnonymizerInput(
            source=str(sub_path), text_column=text_col, data_summary=data_summary
        )
        config = AnonymizerConfig(
            detect=Detect(entity_labels=list(DEFAULT_ENTITY_LABELS), gliner_threshold=threshold),
            replace=Redact(format_template="[{label}]"),
            emit_telemetry=not args.no_emit_telemetry,
        )
        log(
            f"[iter {i}/{len(thresholds)}] anonymizing {len(leaking)} row(s) @ gliner_threshold={threshold}"
        )
        with Heartbeat(f"iteration {i} anonymizing"):
            result = anonymizer.run(config=config, data=data)
        trace = result.trace_dataframe
        rep_col = f"{text_col}_replaced"
        if id_col in trace.columns and rep_col in trace.columns:
            for _, r in trace.iterrows():
                current[str(r[id_col])] = str(r[rep_col])

        # Critic reviews each redacted row -> suspected residual PHI (hints for the next pass).
        residual: dict[str, list[dict]] = {}
        for uid in leaking:
            items = _critic_review(critic, args.critic_model, current[uid])
            if items:
                residual[uid] = items
        for uid, items in residual.items():  # oscillation -> human review
            for it in items:
                key = (uid, it["value"])
                hint_counts[key] = hint_counts.get(key, 0) + 1
                if hint_counts[key] > args.revert_flag_n:
                    flagged = review_flags.setdefault(uid, [])
                    if it["value"] not in [f["value"] for f in flagged]:
                        flagged.append(it)

        exemplars = _aggregate_exemplars(residual)
        data_summary = (base_data_summary or "") + _hint_block(exemplars)
        secs = round(time.perf_counter() - t_it, 2)
        iterations.append(
            {
                "iteration": i,
                "gliner_threshold": threshold,
                "rows_processed": len(leaking),
                "rows_with_residual": len(residual),
                "residual_items": sum(len(v) for v in residual.values()),
                "residual_exemplars": exemplars[:12],
                "seconds": secs,
            }
        )
        log(
            f"[iter {i}] {len(residual)}/{len(leaking)} row(s) still have suspected PHI "
            f"({iterations[-1]['residual_items']} items) in {secs}s"
        )
        leaking = list(residual.keys())

    return {
        "records": [{"study_uid": u, "report": current[u]} for u in order],
        "review_flags": review_flags,
        "iterations": iterations,
        "converged": not leaking,
        "n_reports": len(order),
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "reports_csv",
        nargs="?",
        default=None,
        help="Path to input CSV with PHI-containing reports (positional).",
    )
    p.add_argument(
        "--source", default=None, help="Alias for the positional input CSV (backward compatible)."
    )
    p.add_argument(
        "--output-dir", default=None, help="Directory for anonymized_reports.csv + run_report.json."
    )
    p.add_argument(
        "--output-path",
        default=None,
        help="Alias: explicit output CSV path (run report written alongside).",
    )
    p.add_argument(
        "--text-column",
        default="report_w_PHI",
        help="Column holding report text (default: report_w_PHI).",
    )
    p.add_argument(
        "--id-column",
        default="study_uid",
        help="Unique id column copied through (default: study_uid).",
    )
    p.add_argument(
        "--gliner-threshold",
        type=float,
        default=0.3,
        help="GLiNER detection threshold; lower=recall, higher=precision (default 0.3).",
    )
    p.add_argument(
        "--full", action="store_true", help="Run on the full dataset (default: preview)."
    )
    p.add_argument(
        "--num-records", type=int, default=4, help="Rows to preview (ignored with --full)."
    )
    p.add_argument(
        "--evaluate",
        action="store_true",
        help="Run LLM-as-judge detection-validity scoring on the output.",
    )
    p.add_argument(
        "--no-emit-telemetry",
        action="store_true",
        help="Disable NeMo Anonymizer's own anonymous run telemetry.",
    )
    p.add_argument(
        "--verbose", action="store_true", help="Debug logging from the anonymizer library."
    )
    p.add_argument(
        "--model-providers",
        default=None,
        help="Path to a providers.yaml declaring model endpoints (e.g. local "
        "Ollama + self-hosted GLiNER). Omit to use hosted build.nvidia.com.",
    )
    p.add_argument(
        "--model-configs",
        default=None,
        help="Path to a models.yaml model pool. Required whenever --model-providers "
        "introduces provider names the default pool does not reference.",
    )
    p.add_argument(
        "--mode",
        choices=["redact", "rewrite"],
        default="redact",
        help="redact = replace PHI with [LABEL] tokens (default); "
        "rewrite = LLM rewrites the whole passage with an evaluate-repair loop "
        "(output is prose, not tokens).",
    )
    p.add_argument(
        "--max-repair-iterations",
        type=int,
        default=3,
        help="Rewrite mode only: max evaluate-repair rounds (0 disables repair).",
    )
    p.add_argument(
        "--strict-entity-protection",
        action="store_true",
        help="Rewrite mode only: require a protective disposition for every entity.",
    )
    p.add_argument(
        "--risk-tolerance",
        choices=["low", "medium", "high"],
        default="low",
        help="Rewrite mode only: repair/leakage threshold preset.",
    )
    # Iterative redaction (redact mode): re-run the anonymizer, using an LLM critic's
    # suspected-PHI list as hints each pass; the anonymizer's validator gates precision.
    p.add_argument(
        "--iterative-redaction",
        action="store_true",
        help="Redact mode: loop detect+redact, feeding an LLM critic's suspected-PHI "
        "list back as hints each pass, until the critic finds nothing or the cap.",
    )
    p.add_argument(
        "--max-redaction-iterations",
        type=int,
        default=3,
        help="Max iterative-redaction passes (default 3). Threshold descends 0.1/pass.",
    )
    p.add_argument(
        "--revert-flag-n",
        type=int,
        default=3,
        help="If the critic keeps flagging the same value past N passes, flag it for "
        "human review (default 3).",
    )
    p.add_argument(
        "--critic-base-url",
        default="http://localhost:11434/v1",
        help="OpenAI-compatible endpoint for the PHI critic LLM (default local Ollama).",
    )
    p.add_argument(
        "--critic-model",
        default="medgemma:27b",
        help="Model for the PHI critic (default medgemma:27b).",
    )
    p.add_argument(
        "--critic-api-key",
        default="ollama",
        help="API key for the critic endpoint (ignored by Ollama; any non-empty value).",
    )
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
            raise SystemExit(
                "No output location given. Pass --output-dir OUT (or --output-path FILE)."
            )
        args._explicit_output_csv = None


def main() -> int:
    args = build_parser().parse_args()
    resolve_paths(args)

    t_run = time.perf_counter()
    configure_logging(LoggingConfig.debug() if args.verbose else LoggingConfig.verbose())

    check_environment(local=bool(args.model_providers))
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
    anon_kwargs: dict[str, str] = {}
    if args.model_providers:
        anon_kwargs["model_providers"] = args.model_providers
    if args.model_configs:
        anon_kwargs["model_configs"] = args.model_configs
    anonymizer = Anonymizer(**anon_kwargs)
    if anon_kwargs:
        log("Custom model config: " + ", ".join(f"{k}={v}" for k, v in anon_kwargs.items()))
    init_secs = time.perf_counter() - t_init
    log(f"Anonymizer ready ({init_secs:.1f}s)")

    if args.iterative_redaction:
        log(
            f"Iterative redaction: up to {args.max_redaction_iterations} pass(es); "
            f"critic={args.critic_model} @ {args.critic_base_url}"
        )
        it_res = run_iterative_redaction(anonymizer, args, out_dir, data.data_summary)
        out_df = pd.DataFrame(it_res["records"], columns=OUTPUT_COLUMNS)
        anon_csv.parent.mkdir(parents=True, exist_ok=True)
        out_df.to_csv(anon_csv, index=False, encoding="utf-8-sig")
        pipe_secs = round(sum(x["seconds"] for x in it_res["iterations"]), 2)
        n = it_res["n_reports"]
        summary = {
            "skill": SKILL_NAME,
            "mode": "iterative-redaction",
            "strategy": "redact-iterative",
            "n_reports": n,
            "n_written": len(out_df),
            "converged": it_res["converged"],
            "n_iterations": len(it_res["iterations"]),
            "iterations": it_res["iterations"],
            "human_review": {
                "n_flagged_reports": len(it_res["review_flags"]),
                "flags": it_res["review_flags"],
            },
            "telemetry": {
                "wall_seconds": {
                    "init": round(init_secs, 2),
                    "pipeline": pipe_secs,
                    "total": round(time.perf_counter() - t_run, 2),
                },
                "mean_seconds_per_report": round(pipe_secs / n, 2) if n and pipe_secs else None,
                "critic_model": args.critic_model,
            },
            "artifacts": {
                "anonymized_csv": str(anon_csv),
                "run_report_json": str(run_report_path),
                "input_csv": str(args.source),
            },
            "phi_scope_disclaimer": PHI_SCOPE_DISCLAIMER,
        }
        write_run_report(summary, run_report_path)
        log("=" * 72)
        log(
            f"Iterative redaction done: {n} report(s), {summary['n_iterations']} pass(es), "
            f"converged={summary['converged']}, "
            f"{summary['human_review']['n_flagged_reports']} flagged for human review"
        )
        log(f"Avg / report : {summary['telemetry']['mean_seconds_per_report']}s")
        log("=" * 72)
        print(json.dumps(summary, indent=2))
        return 0

    detect_where = "local endpoints" if args.model_providers else "remote build.nvidia.com"
    log(
        f"Starting entity detection on {stats['target_rows']} record(s) - {detect_where} in flight..."
    )
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
        result,
        args,
        n_written=n_written,
        timings=timings,
        input_tokens=input_tokens,
        evaluated=evaluated,
        artifacts=artifacts,
    )
    write_run_report(disk_report, run_report_path)
    print_run_report(summary)

    # Failure-first protocol: dropped rows are infra issues (rate limits, auth),
    # not strategy issues. Emit the summary either way, then signal via exit code.
    if summary["records_failed"]:
        log(
            f"{summary['records_failed']} record(s) failed; see failed_records. "
            "Fix dropped rows (rate limits/auth) before tuning strategy."
        )

    # STDOUT: the single machine-readable JSON summary (Medical AI Skills invariant).
    print(json.dumps(summary, indent=2))
    return 1 if summary["records_failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
