#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Without-skill baseline: upstream NeMo text-only redact, no policy/JSONL layer.

Mimics what an agent armed only with the upstream NeMo README would produce:
  - NeMo redact on text column(s) only
  - Wide CSV output; no structured-field policy, no DICOM JSONL, no audit.jsonl
  - Default upstream redact template [REDACTED_{label}] (not skill [{label}])
  - No strict GLiNER label set from medical-anonymization policy
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd
from anonymizer import Anonymizer, AnonymizerConfig, AnonymizerInput, Detect, Redact
from anonymizer.logging import LoggingConfig, configure_logging

SKILL_NAME = "without-skill-upstream-nemo"
RUN_REPORT = "run_report.json"


def run_text_csv(
    source: Path,
    output_dir: Path,
    text_column: str,
    id_column: str,
    *,
    num_records: int | None,
    model_providers: str | None,
    model_configs: str | None,
) -> dict:
    t0 = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    out_csv = output_dir / "anonymized_data.csv"

    detect = Detect(gliner_threshold=0.3)  # upstream default: no strict entity_labels
    config = AnonymizerConfig(
        detect=detect,
        replace=Redact(),  # default [REDACTED_{label}]
        emit_telemetry=False,
    )
    data = AnonymizerInput(
        source=str(source),
        text_column=text_column,
        data_summary="English clinical text with PHI.",
    )

    anon_kwargs: dict[str, str] = {}
    if model_providers:
        anon_kwargs["model_providers"] = str(Path(model_providers).resolve())
    if model_configs:
        anon_kwargs["model_configs"] = str(Path(model_configs).resolve())

    t_init = time.perf_counter()
    anonymizer = Anonymizer(**anon_kwargs)
    init_s = time.perf_counter() - t_init

    t_pipe = time.perf_counter()
    if num_records:
        result = anonymizer.preview(config=config, data=data, num_records=num_records)
    else:
        result = anonymizer.run(config=config, data=data)
    pipe_s = time.perf_counter() - t_pipe

    df_in = pd.read_csv(source, encoding="utf-8-sig")
    out_df = result.trace_dataframe
    replaced_col = f"{text_column}_replaced"
    if replaced_col not in out_df.columns:
        raise RuntimeError(f"Expected {replaced_col} in NeMo output")
    if id_column not in out_df.columns:
        raise RuntimeError(f"Expected {id_column} in NeMo trace output")

    nemo_out = out_df[[id_column, replaced_col]].rename(columns={replaced_col: "text_anonymized"})

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from nemo_text import merge_nemo_preview_into_column

    df_out = merge_nemo_preview_into_column(
        df_in, id_column=id_column, text_column=text_column, nemo_out=nemo_out
    )
    df_out.to_csv(out_csv, index=False, encoding="utf-8-sig")

    summary = {
        "skill": SKILL_NAME,
        "arm": "without",
        "input": str(source),
        "output_csv": str(out_csv),
        "text_column": text_column,
        "n_records": len(df_out),
        "n_nemo_preview": len(nemo_out),
        "telemetry": {
            "wall_seconds": {
                "init": round(init_s, 2),
                "pipeline": round(pipe_s, 2),
                "total": round(time.perf_counter() - t0, 2),
            },
        },
        "artifacts": {"anonymized_csv": str(out_csv)},
    }
    (output_dir / RUN_REPORT).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return summary


def run_dicom_passthrough(source: Path, output_dir: Path, id_column: str) -> dict:
    """Without-skill: no DICOM policy engine — copy wide CSV unchanged."""
    t0 = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    out_csv = output_dir / "metadata_passthrough.csv"
    df = pd.read_csv(source, encoding="utf-8-sig", low_memory=False)
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    summary = {
        "skill": SKILL_NAME,
        "arm": "without",
        "input": str(source),
        "input_kind": "dicom-metadata-csv",
        "note": "Upstream NeMo has no DICOM metadata policy; passthrough wide CSV only.",
        "n_records": len(df),
        "telemetry": {"wall_seconds": {"total": round(time.perf_counter() - t0, 2)}},
        "artifacts": {"metadata_passthrough_csv": str(out_csv)},
    }
    (output_dir / RUN_REPORT).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return summary


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--input-kind", choices=["csv", "dicom-metadata-csv"], default="csv")
    p.add_argument("--text-column", default="report_w_PHI")
    p.add_argument("--id-column", default="study_uid")
    p.add_argument("--num-records", type=int, default=None)
    p.add_argument("--model-providers", default=None)
    p.add_argument("--model-configs", default=None)
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    configure_logging(LoggingConfig.debug() if args.verbose else LoggingConfig.verbose())
    src = Path(args.input)
    out = Path(args.output_dir)

    if args.input_kind == "dicom-metadata-csv":
        run_dicom_passthrough(src, out, args.id_column)
    else:
        run_text_csv(
            src, out, args.text_column, args.id_column,
            num_records=args.num_records,
            model_providers=args.model_providers,
            model_configs=args.model_configs,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
