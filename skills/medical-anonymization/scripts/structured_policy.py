#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Deterministic structured-field anonymization for CSV / flat metadata columns."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

UID_NAMESPACE = "medical-anonymization-v1"


def _hash_value(value: str, digest_length: int = 12) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:digest_length]


def _remap_uid(value: str, record_key: str) -> str:
    """Deterministic pseudonym UID (not a real DICOM UID root)."""
    seed = f"{UID_NAMESPACE}:{record_key}:{value}"
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    # 2.25.<decimal> style placeholder
    num = int(h[:16], 16)
    return f"2.25.{num}"


def _shift_date(value: str, offset_days: int) -> str:
    value = str(value).strip()
    if not value:
        return value
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value[:10].replace("-", "") if fmt == "%Y%m%d" else value[:10], fmt)
            return (dt + timedelta(days=offset_days)).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return value


def _redact(template: str, field: str, value: str) -> str:
    return template.replace("{field}", field).replace("{value}", value)


def resolve_column_action(col: str, policy: dict) -> dict:
    cols = policy.get("columns", {})
    if col in cols:
        return dict(cols[col])
    return {"action": policy.get("default_action", "keep")}


def apply_structured_column(
    series: pd.Series,
    col: str,
    action_cfg: dict,
    record_keys: pd.Series,
    date_offsets: dict[str, int],
) -> tuple[pd.Series, list[dict]]:
    action = action_cfg.get("action", "keep")
    audit: list[dict] = []
    out = series.copy()

    for idx, raw in series.items():
        if pd.isna(raw) or str(raw).strip() == "":
            continue
        val = str(raw)
        rec = str(record_keys.iloc[idx]) if idx in record_keys.index else str(idx)
        entry = {"column": col, "action": action, "record_key": rec}

        if action == "keep":
            pass
        elif action == "drop":
            out.iloc[idx] = ""
            entry["new_value"] = ""
        elif action == "redact":
            new = _redact(action_cfg.get("template", "[{field}]"), col, val)
            out.iloc[idx] = new
            entry["new_value"] = new
        elif action == "hash":
            new = _hash_value(val)
            out.iloc[idx] = new
            entry["new_value"] = new
        elif action == "uid_remap":
            new = _remap_uid(val, rec)
            out.iloc[idx] = new
            entry["new_value"] = new
        elif action == "date_shift":
            off = date_offsets.get(rec, 0)
            new = _shift_date(val, off)
            out.iloc[idx] = new
            entry["new_value"] = new
        elif action == "bucket":
            # Simple age bucketing: "045Y" -> "40-49"
            m = re.match(r"^(\d+)", val)
            if m:
                age = int(m.group(1))
                bucket = f"{(age // 10) * 10}-{(age // 10) * 10 + 9}"
                out.iloc[idx] = bucket
                entry["new_value"] = bucket
        else:
            entry["action"] = "keep"
        audit.append(entry)

    return out, audit


def build_date_offsets(df: pd.DataFrame, id_col: str) -> dict[str, int]:
    """Stable per-record date offset (days) for date_shift actions."""
    offsets: dict[str, int] = {}
    for i, rid in enumerate(df[id_col].astype(str)):
        h = int(hashlib.sha256(rid.encode()).hexdigest()[:4], 16)
        offsets[rid] = (h % 365) - 180
        offsets[str(i)] = offsets[rid]
    return offsets


def anonymize_structured_dataframe(
    df: pd.DataFrame,
    structured_columns: list[str],
    policy: dict,
    id_column: str,
) -> tuple[pd.DataFrame, list[dict]]:
    out = df.copy()
    audit: list[dict] = []
    record_keys = out[id_column] if id_column in out.columns else pd.Series(range(len(out)))
    date_offsets = build_date_offsets(out, id_column) if id_column in out.columns else {}

    for col in structured_columns:
        if col not in out.columns:
            continue
        action_cfg = resolve_column_action(col, policy)
        out[col], col_audit = apply_structured_column(
            out[col], col, action_cfg, record_keys, date_offsets
        )
        audit.extend(col_audit)

    return out, audit
