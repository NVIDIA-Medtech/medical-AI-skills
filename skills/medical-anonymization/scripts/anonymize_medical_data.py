#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""General-purpose medical data anonymization: text, CSV, and DICOM metadata.

NeMo Anonymizer text strategies (unstructured / text columns):
  redact | substitute | annotate | hash | rewrite

Structured / DICOM metadata actions (deterministic, no LLM):
  keep | drop | redact | hash | uid_remap | date_shift | bucket

Usage::

    # DICOM metadata CSV -> JSONL (local, no API key)
    python anonymize_medical_data.py fixtures/sample_dicom_metadata.csv \\
        --output-dir runs/dicom --input-kind dicom-metadata-csv

    # Mixed EHR CSV: hash MRN, NeMo-redact note column
    python anonymize_medical_data.py fixtures/sample_ehr.csv \\
        --output-dir runs/ehr --text-columns note_text --id-column record_id

    # Plain text file
    python anonymize_medical_data.py fixtures/sample_note.txt \\
        --output-dir runs/note --input-kind text --text-strategy redact
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

_SCRIPT_DIR = Path(__file__).resolve().parent
_SKILL_ROOT = _SCRIPT_DIR.parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from dicom_policy import (  # noqa: E402
    anonymize_dicom_metadata_csv,
    flatten_to_csv,
    write_audit_jsonl,
    write_jsonl,
)
from metadata_formats import (  # noqa: E402
    nested_records_to_kv,
    wide_csv_to_long,
    write_jsonl_rows,
)
from structured_policy import anonymize_structured_dataframe, resolve_column_action  # noqa: E402

SKILL_NAME = "medical-anonymization"
RUN_REPORT_NAME = "run_report.json"
PHI_SCOPE_DISCLAIMER = (
    "Applies NeMo Anonymizer for free-text PHI and deterministic policies for "
    "structured identifiers. NOT a regulatory de-identifier. Review output before "
    "sharing. Not for clinical use."
)

TEXT_STRATEGIES = ("redact", "substitute", "annotate", "hash", "rewrite")
STRUCTURED_ACTIONS = ("keep", "drop", "redact", "hash", "uid_remap", "date_shift", "bucket")


def log(msg: str) -> None:
    print(f"[medical-anonymization] {msg}", file=sys.stderr, flush=True)


def load_policy(path: Path | None) -> dict:
    default = _SKILL_ROOT / "policies" / "default-medical.yaml"
    policy_path = path or default
    if not policy_path.exists():
        raise SystemExit(f"Policy file not found: {policy_path}")
    with policy_path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def detect_input_kind(path: Path, explicit: str) -> str:
    if explicit != "auto":
        return explicit
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return "text"
    if suffix != ".csv":
        raise SystemExit(f"Cannot auto-detect input kind for {path}; pass --input-kind")
    df = pd.read_csv(path, nrows=5, encoding="utf-8-sig")
    cols = set(df.columns)
    dicom_markers = {"PatientID", "StudyInstanceUID", "SeriesInstanceUID", "Modality"}
    if len(cols & dicom_markers) >= 2:
        return "dicom-metadata-csv"
    if "report_w_PHI" in cols:
        return "csv"
    return "csv"


def text_file_to_csv(path: Path, out_csv: Path, id_column: str, text_column: str) -> None:
    text = path.read_text(encoding="utf-8")
    df = pd.DataFrame({id_column: [path.stem], text_column: [text]})
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")


def infer_structured_columns(df: pd.DataFrame, text_columns: list[str], policy: dict) -> list[str]:
    structured_cfg = policy.get("structured", {})
    known = set(structured_cfg.get("columns", {}))
    cols: list[str] = []
    for col in df.columns:
        if col in text_columns:
            continue
        if col in known or resolve_column_action(col, structured_cfg).get("action", "keep") != "keep":
            cols.append(col)
    return cols


def run_dicom_path(
    df: pd.DataFrame,
    out_dir: Path,
    policy: dict,
    id_column: str,
    metadata_format: str = "both",
) -> dict[str, Any]:
    t0 = time.perf_counter()
    records, audit = anonymize_dicom_metadata_csv(df, policy, id_column=id_column)
    kv_rows = nested_records_to_kv(records)
    audit_path = out_dir / "audit.jsonl"
    flat_path = out_dir / "deidentified_metadata_flat.csv"
    write_audit_jsonl(audit, audit_path)
    flatten_to_csv(records, flat_path)

    artifacts: dict[str, str] = {
        "audit_jsonl": str(audit_path),
        "deidentified_metadata_flat_csv": str(flat_path),
    }
    n_kv = len(kv_rows)

    if metadata_format in ("nested", "both"):
        nested_path = out_dir / "deidentified_metadata_nested.jsonl"
        write_jsonl(records, nested_path)
        artifacts["deidentified_metadata_nested_jsonl"] = str(nested_path)
        # backward-compatible alias
        legacy_path = out_dir / "deidentified_metadata.jsonl"
        write_jsonl(records, legacy_path)
        artifacts["deidentified_metadata_jsonl"] = str(legacy_path)

    if metadata_format in ("kv", "both"):
        kv_path = out_dir / "deidentified_metadata_kv.jsonl"
        write_jsonl_rows(nested_records_to_kv(records, compact=False), kv_path)
        artifacts["deidentified_metadata_kv_jsonl"] = str(kv_path)
        compact_path = out_dir / "deidentified_metadata_kv_compact.jsonl"
        write_jsonl_rows(nested_records_to_kv(records, compact=True), compact_path)
        artifacts["deidentified_metadata_kv_compact_jsonl"] = str(compact_path)

    long_df = wide_csv_to_long(df, id_column)
    return {
        "input_kind": "dicom-metadata-csv",
        "metadata_format": metadata_format,
        "timing_phases": {"policy_anonymize": round(time.perf_counter() - t0, 3)},
        "n_records": len(records),
        "n_kv_rows": n_kv,
        "n_input_populated_cells": len(long_df),
        "n_audit_events": len(audit),
        "artifacts": artifacts,
    }


def run_csv_path(args: argparse.Namespace, policy: dict, out_dir: Path) -> dict[str, Any]:
    df = pd.read_csv(args.input, encoding="utf-8-sig")
    id_col = args.id_column
    if id_col not in df.columns:
        id_col = df.columns[0]

    text_cols = args.text_columns or (
        ["report_w_PHI"] if "report_w_PHI" in df.columns else []
    )
    structured_cols = args.structured_columns or infer_structured_columns(df, text_cols, policy)

    working = df.copy()
    audit_all: list[dict] = []

    if structured_cols:
        working, audit = anonymize_structured_dataframe(
            working, structured_cols, policy.get("structured", {}), id_col
        )
        audit_all.extend(audit)

    nemo_runs: list[dict] = []
    text_strategy = args.text_strategy or policy.get("text", {}).get("strategy", "redact")

    for tcol in text_cols:
        if tcol not in working.columns:
            raise SystemExit(f"Text column {tcol!r} not in input CSV")
        tmp_in = out_dir / f"_nemo_input_{tcol}.csv"
        tmp_out = out_dir / f"_nemo_output_{tcol}.csv"
        working[[id_col, tcol]].to_csv(tmp_in, index=False, encoding="utf-8-sig")

        if args.local_only:
            log(f"Skipping NeMo on {tcol} (--local-only); structured actions only")
            continue

        from nemo_text import run_nemo_text

        nemo_res = run_nemo_text(
            source_csv=tmp_in,
            output_csv=tmp_out,
            text_column=tcol,
            id_column=id_col,
            strategy=text_strategy,
            policy_text=policy.get("text", {}),
            full=args.full,
            num_records=args.num_records,
            gliner_threshold=args.gliner_threshold,
            model_providers=args.model_providers,
            model_configs=args.model_configs,
            risk_tolerance=args.risk_tolerance,
            max_repair_iterations=args.max_repair_iterations,
            strict_entity_protection=args.strict_entity_protection,
            emit_telemetry=not args.no_emit_telemetry,
            verbose=args.verbose,
        )
        from nemo_text import merge_nemo_preview_into_column

        nemo_out = pd.read_csv(tmp_out, encoding="utf-8-sig")
        working = merge_nemo_preview_into_column(
            working, id_column=id_col, text_column=tcol, nemo_out=nemo_out
        )
        nemo_runs.append({k: v for k, v in nemo_res.items() if k != "result"})

    out_csv = out_dir / "anonymized_data.csv"
    working.to_csv(out_csv, index=False, encoding="utf-8-sig")

    kv_rows = []
    for _, row in working.iterrows():
        rid = str(row[id_col])
        for col in working.columns:
            if col == id_col:
                continue
            val = row[col]
            if pd.isna(val) or str(val).strip() == "":
                continue
            kv_rows.append({"record_id": rid, "field": col, "value": str(val)})

    kv_path = out_dir / "anonymized_data_kv.jsonl"
    write_jsonl_rows(kv_rows, kv_path)

    return {
        "input_kind": "csv",
        "text_strategy": text_strategy,
        "text_columns": text_cols,
        "structured_columns": structured_cols,
        "n_records": len(working),
        "n_kv_rows": len(kv_rows),
        "nemo_runs": nemo_runs,
        "structured_audit_events": len(audit_all),
        "artifacts": {
            "anonymized_csv": str(out_csv),
            "anonymized_data_kv_jsonl": str(kv_path),
        },
    }


def run_text_path(args: argparse.Namespace, policy: dict, out_dir: Path) -> dict[str, Any]:
    id_col = args.id_column
    text_col = args.text_column
    tmp_in = out_dir / "_text_input.csv"
    text_file_to_csv(Path(args.input), tmp_in, id_col, text_col)

    if args.local_only:
        raise SystemExit("Text anonymization requires NeMo; omit --local-only")

    from nemo_text import run_nemo_text

    text_strategy = args.text_strategy or policy.get("text", {}).get("strategy", "redact")
    out_csv = out_dir / "anonymized_text.csv"
    nemo_res = run_nemo_text(
        source_csv=tmp_in,
        output_csv=out_csv,
        text_column=text_col,
        id_column=id_col,
        strategy=text_strategy,
        policy_text=policy.get("text", {}),
        full=True,
        num_records=1,
        gliner_threshold=args.gliner_threshold,
        model_providers=args.model_providers,
        model_configs=args.model_configs,
        risk_tolerance=args.risk_tolerance,
        max_repair_iterations=args.max_repair_iterations,
        strict_entity_protection=args.strict_entity_protection,
        emit_telemetry=not args.no_emit_telemetry,
        verbose=args.verbose,
    )
    out_txt = out_dir / "anonymized_text.txt"
    out_df = pd.read_csv(out_csv, encoding="utf-8-sig")
    out_txt.write_text(str(out_df["text_anonymized"].iloc[0]), encoding="utf-8")

    return {
        "input_kind": "text",
        "text_strategy": text_strategy,
        "nemo": {k: v for k, v in nemo_res.items() if k != "result"},
        "artifacts": {
            "anonymized_text_txt": str(out_txt),
            "anonymized_text_csv": str(out_csv),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", help="Input file: .txt, .csv (mixed or DICOM metadata flat export)")
    p.add_argument("--output-dir", required=True, help="Output directory for artifacts + run_report.json")
    p.add_argument(
        "--input-kind",
        choices=["auto", "text", "csv", "dicom-metadata-csv"],
        default="auto",
        help="Input lane (default: auto-detect)",
    )
    p.add_argument("--policy", default=None, help="YAML policy (default: policies/default-medical.yaml)")
    p.add_argument("--id-column", default="record_id", help="Record id column (default: record_id)")
    p.add_argument("--text-column", default="text", help="Text column for --input-kind text temp CSV")
    p.add_argument("--text-columns", nargs="*", default=None, help="CSV columns to run through NeMo")
    p.add_argument("--structured-columns", nargs="*", default=None, help="CSV columns for deterministic policy")
    p.add_argument(
        "--text-strategy",
        choices=TEXT_STRATEGIES,
        default=None,
        help="NeMo strategy: redact|substitute|annotate|hash|rewrite",
    )
    p.add_argument(
        "--metadata-format",
        choices=["nested", "kv", "both"],
        default="both",
        help="DICOM metadata output: nested (fool-proof), kv (token-efficient), or both",
    )
    p.add_argument("--full", action="store_true", help="Process all CSV rows through NeMo (default: preview)")
    p.add_argument("--num-records", type=int, default=4, help="NeMo preview row count")
    p.add_argument("--local-only", action="store_true", help="Structured/DICOM only; skip NeMo text passes")
    p.add_argument("--gliner-threshold", type=float, default=0.3)
    p.add_argument("--model-providers", default=None)
    p.add_argument("--model-configs", default=None)
    p.add_argument("--risk-tolerance", choices=["minimal", "low", "moderate", "medium", "high"], default="low")
    p.add_argument("--max-repair-iterations", type=int, default=3)
    p.add_argument("--strict-entity-protection", action="store_true")
    p.add_argument("--no-emit-telemetry", action="store_true")
    p.add_argument("--verbose", action="store_true")
    return p


def main() -> int:
    args = build_parser().parse_args()
    t0 = time.perf_counter()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    policy = load_policy(Path(args.policy) if args.policy else None)
    input_path = Path(args.input)
    kind = detect_input_kind(input_path, args.input_kind)

    if kind == "dicom-metadata-csv":
        df = pd.read_csv(input_path, encoding="utf-8-sig")
        id_col = args.id_column if args.id_column in df.columns else "study_uid"
        if id_col not in df.columns:
            id_col = df.columns[0]
        body = run_dicom_path(df, out_dir, policy, id_col, metadata_format=args.metadata_format)
    elif kind == "text":
        body = run_text_path(args, policy, out_dir)
    else:
        body = run_csv_path(args, policy, out_dir)

    summary = {
        "skill": SKILL_NAME,
        "input": str(input_path),
        "input_kind": body.get("input_kind", kind),
        "metadata_format": getattr(args, "metadata_format", None),
        "text_strategies_available": list(TEXT_STRATEGIES),
        "structured_actions_available": list(STRUCTURED_ACTIONS),
        "policy": str(Path(args.policy) if args.policy else _SKILL_ROOT / "policies" / "default-medical.yaml"),
        "phi_scope_disclaimer": PHI_SCOPE_DISCLAIMER,
        "timing": {
            "wall_seconds_total": round(time.perf_counter() - t0, 3),
            "phases": body.get("timing_phases", {}),
        },
        "telemetry": {"wall_seconds": {"total": round(time.perf_counter() - t0, 2)}},
        **body,
        "artifacts": {
            "run_report_json": str(out_dir / RUN_REPORT_NAME),
            **body.get("artifacts", {}),
        },
    }
    report_path = out_dir / RUN_REPORT_NAME
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
