#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""NeMo Anonymizer text runner — all replace strategies + rewrite mode."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
from anonymizer import (
    Anonymizer,
    AnonymizerConfig,
    AnonymizerInput,
    Annotate,
    Detect,
    Hash,
    PrivacyGoal,
    Redact,
    Rewrite,
    RiskTolerance,
    Substitute,
)
from anonymizer.logging import LoggingConfig, configure_logging

# Reuse logging from the report wrapper.
from anonymize_reports import Heartbeat, log

DEFAULT_ENTITY_LABELS = [
    "patient",
    "patient_mrn",
    "doctor",
    "date_of_birth",
    "age",
    "sex",
    "date",
    "accession_number",
    "institution",
    "phone",
    "email",
    "address",
]

_RISK_MAP = {
    "minimal": RiskTolerance.minimal,
    "low": RiskTolerance.low,
    "medium": RiskTolerance.moderate,
    "moderate": RiskTolerance.moderate,
    "high": RiskTolerance.high,
}


def build_nemo_config(
    *,
    source: str,
    text_column: str,
    data_summary: str,
    strategy: str,
    entity_labels: list[str] | None,
    gliner_threshold: float,
    redact_template: str,
    annotate_template: str,
    hash_template: str,
    risk_tolerance: str,
    max_repair_iterations: int,
    strict_entity_protection: bool,
    emit_telemetry: bool,
) -> tuple[AnonymizerInput, AnonymizerConfig]:
    data = AnonymizerInput(
        source=source,
        text_column=text_column,
        data_summary=data_summary,
    )
    labels = entity_labels or list(DEFAULT_ENTITY_LABELS)

    if strategy == "rewrite":
        privacy_goal = PrivacyGoal(
            protect=(
                "Direct and quasi identifiers: patient name, medical record number, "
                "date of birth, age, sex, service dates, accession number, physician "
                "names, institution names, phone numbers, email, and addresses."
            ),
            preserve=(
                "Clinical content: findings, diagnoses, measurements, impressions, "
                "and medical terminology."
            ),
        )
        config = AnonymizerConfig(
            rewrite=Rewrite(
                privacy_goal=privacy_goal,
                risk_tolerance=_RISK_MAP.get(risk_tolerance, RiskTolerance.low),
                max_repair_iterations=max_repair_iterations,
                strict_entity_protection=strict_entity_protection,
            ),
            emit_telemetry=emit_telemetry,
        )
        return data, config

    detect = Detect(entity_labels=labels, gliner_threshold=gliner_threshold)
    replace: Redact | Substitute | Annotate | Hash
    if strategy == "substitute":
        replace = Substitute()
    elif strategy == "annotate":
        replace = Annotate(format_template=annotate_template)
    elif strategy == "hash":
        replace = Hash(format_template=hash_template)
    else:
        replace = Redact(format_template=redact_template)

    config = AnonymizerConfig(
        detect=detect,
        replace=replace,
        emit_telemetry=emit_telemetry,
    )
    return data, config


def merge_nemo_preview_into_column(
    working: pd.DataFrame,
    *,
    id_column: str,
    text_column: str,
    nemo_out: pd.DataFrame,
) -> pd.DataFrame:
    """Apply preview/full NeMo output back onto a wide CSV by record id."""
    if "text_anonymized" not in nemo_out.columns:
        raise RuntimeError("Expected text_anonymized column in NeMo output")
    if id_column not in nemo_out.columns:
        raise RuntimeError(f"Expected {id_column} in NeMo output for merge")

    out = working.copy()
    mapped = nemo_out.set_index(id_column)["text_anonymized"]
    out[text_column] = out[id_column].map(mapped).fillna(out[text_column])
    return out


def to_output_dataframe(result, text_column: str, id_column: str) -> pd.DataFrame:
    df = result.trace_dataframe
    out_col = next(
        (c for c in (f"{text_column}_replaced", f"{text_column}_rewritten") if c in df.columns),
        None,
    )
    if out_col is None:
        raise RuntimeError(
            f"Expected {text_column}_replaced or {text_column}_rewritten; got {list(df.columns)}"
        )
    out = df[[out_col]].rename(columns={out_col: "text_anonymized"})
    if id_column in df.columns:
        out.insert(0, id_column, df[id_column].values)
    else:
        out.insert(0, "record_id", range(len(out)))
    return out


def run_nemo_text(
    *,
    source_csv: Path,
    output_csv: Path,
    text_column: str,
    id_column: str,
    strategy: str,
    policy_text: dict,
    full: bool,
    num_records: int,
    gliner_threshold: float,
    model_providers: str | None,
    model_configs: str | None,
    risk_tolerance: str,
    max_repair_iterations: int,
    strict_entity_protection: bool,
    emit_telemetry: bool,
    verbose: bool,
) -> dict[str, Any]:
    configure_logging(LoggingConfig.debug() if verbose else LoggingConfig.verbose())
    data, config = build_nemo_config(
        source=str(source_csv),
        text_column=text_column,
        data_summary=policy_text.get("data_summary", "English clinical text with PHI."),
        strategy=strategy,
        entity_labels=policy_text.get("entity_labels"),
        gliner_threshold=gliner_threshold,
        redact_template=policy_text.get("redact_template", "[{label}]"),
        annotate_template=policy_text.get("annotate_template", "<{text}, {label}>"),
        hash_template=policy_text.get("hash_template", "<HASH_{label}_{digest}>"),
        risk_tolerance=risk_tolerance,
        max_repair_iterations=max_repair_iterations,
        strict_entity_protection=strict_entity_protection,
        emit_telemetry=emit_telemetry,
    )

    anon_kwargs: dict[str, str] = {}
    if model_providers:
        anon_kwargs["model_providers"] = model_providers
    if model_configs:
        anon_kwargs["model_configs"] = model_configs

    t0 = time.perf_counter()
    anonymizer = Anonymizer(**anon_kwargs)
    init_secs = time.perf_counter() - t0

    t1 = time.perf_counter()
    with Heartbeat("NeMo anonymizer pipeline running"):
        if full:
            result = anonymizer.run(config=config, data=data)
        else:
            result = anonymizer.preview(config=config, data=data, num_records=num_records)
    pipe_secs = time.perf_counter() - t1

    out_df = to_output_dataframe(result, text_column, id_column)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(output_csv, index=False, encoding="utf-8-sig")

    return {
        "strategy": strategy,
        "n_written": len(out_df),
        "output_csv": str(output_csv),
        "init_seconds": round(init_secs, 2),
        "pipeline_seconds": round(pipe_secs, 2),
        "result": result,
        "text_column": text_column,
        "id_column": id_column,
    }
