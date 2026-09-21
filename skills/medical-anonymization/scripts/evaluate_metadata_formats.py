#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Compare nested vs KV JSONL metadata formats on a DICOM metadata CSV."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from dicom_policy import anonymize_dicom_metadata_csv  # noqa: E402
from metadata_formats import (  # noqa: E402
    compare_formats,
    measure_file,
    nested_records_to_kv,
    wide_csv_to_long,
    write_jsonl_rows,
)

DEFAULT_DATASET = Path(
    "/home/marc/code/MRI_DICOM_HEAD_DATA_WITH_PHI/deidentified/metadata/dicom_metadata_full.csv"
)


def load_policy(skill_root: Path) -> dict:
    import yaml

    with (skill_root / "policies" / "default-medical.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def run_evaluation(
    input_csv: Path,
    output_dir: Path,
    id_column: str,
    policy: dict,
) -> dict:
    t0 = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_csv, encoding="utf-8-sig", low_memory=False)
    if id_column not in df.columns:
        id_column = "study_uid" if "study_uid" in df.columns else df.columns[0]

    long_df = wide_csv_to_long(df, id_column)
    records, audit = anonymize_dicom_metadata_csv(df, policy, id_column=id_column)
    kv_rows = nested_records_to_kv(records, compact=False)
    kv_compact_rows = nested_records_to_kv(records, compact=True)

    nested_path = output_dir / "deidentified_metadata_nested.jsonl"
    kv_path = output_dir / "deidentified_metadata_kv.jsonl"
    kv_compact_path = output_dir / "deidentified_metadata_kv_compact.jsonl"
    long_path = output_dir / "input_long_kv.jsonl"

    write_jsonl_rows(records, nested_path)
    write_jsonl_rows(kv_rows, kv_path)
    write_jsonl_rows(kv_compact_rows, kv_compact_path)
    write_jsonl_rows(
        [{"record_id": r["record_id"], "field": r["field"], "value": r["value"]} for _, r in long_df.iterrows()],
        long_path,
    )

    input_csv_measure = measure_file(input_csv)
    comparison = compare_formats(
        nested_path,
        kv_path,
        kv_compact_path,
        n_fields=len(kv_rows),
        n_records=len(records),
    )

    report = {
        "input": str(input_csv),
        "id_column": id_column,
        "input_wide_csv": {
            "n_rows": len(df),
            "n_columns": len(df.columns),
            "n_populated_cells": len(long_df),
            **{k: v for k, v in input_csv_measure.items() if k != "path"},
        },
        "formats": comparison,
        "audit_events": len(audit),
        "artifacts": {
            "nested_jsonl": str(nested_path),
            "kv_jsonl": str(kv_path),
            "kv_compact_jsonl": str(kv_compact_path),
            "input_long_jsonl": str(long_path),
        },
        "telemetry": {"wall_seconds": round(time.perf_counter() - t0, 2)},
    }
    report_path = output_dir / "format_evaluation.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["artifacts"]["format_evaluation_json"] = str(report_path)
    return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input_csv", nargs="?", default=str(DEFAULT_DATASET))
    p.add_argument("--output-dir", default="/tmp/metadata_format_eval")
    p.add_argument("--id-column", default="study_uid")
    args = p.parse_args()

    skill_root = _SCRIPT_DIR.parent
    policy = load_policy(skill_root)
    report = run_evaluation(Path(args.input_csv), Path(args.output_dir), args.id_column, policy)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
