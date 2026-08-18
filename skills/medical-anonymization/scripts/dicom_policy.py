#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""DICOM flat-metadata (CSV) → JSONL anonymization with policy-driven field actions."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from structured_policy import _hash_value, _redact, _remap_uid, build_date_offsets


def _field_action(field: str, policy: dict) -> tuple[str, str, dict]:
    """Return (action, phi_class, extra_cfg) for a DICOM field name."""
    meta = policy.get("dicom_metadata", policy)
    default = meta.get("default_action", "keep")
    private_action = meta.get("private_tags_action", "drop")
    prefixes = meta.get("private_tag_prefixes", [])

    for prefix in prefixes:
        if field.startswith(prefix) or field.lower().startswith("private"):
            return private_action, "private", {}

    for cls_name, cls_cfg in meta.get("field_classes", {}).items():
        if field in cls_cfg.get("fields", []):
            return cls_cfg.get("action", default), cls_name, cls_cfg

    return default, "technical", {}


def _apply_field_value(
    field: str,
    value: str,
    action: str,
    cfg: dict,
    record_key: str,
    date_offset: int,
) -> tuple[str, bool]:
    """Return (new_value, dropped)."""
    if action == "keep":
        return value, False
    if action == "drop":
        return "", True
    if action == "redact":
        return _redact(cfg.get("template", "[{field}]"), field, value), False
    if action == "hash":
        return _hash_value(value), False
    if action == "uid_remap":
        return _remap_uid(value, record_key), False
    if action == "date_shift":
        return _shift_date(value, date_offset), False
    return value, False


def _shift_date(value: str, offset_days: int) -> str:
    value = str(value).strip()
    if not value:
        return value
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            raw = value[:10].replace("-", "") if fmt == "%Y%m%d" else value[:10]
            dt = datetime.strptime(raw, fmt)
            return (dt + timedelta(days=offset_days)).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return value


def row_to_attributes(
    row: pd.Series,
    policy: dict,
    record_key: str,
    date_offset: int,
    skip_columns: set[str] | None = None,
) -> tuple[dict[str, dict], list[dict]]:
    skip = skip_columns or set()
    attributes: dict[str, dict] = {}
    audit: list[dict] = []

    for field, raw in row.items():
        if field in skip:
            continue
        if pd.isna(raw) or str(raw).strip() == "":
            continue
        value = str(raw)
        action, phi_class, cfg = _field_action(field, policy)
        new_val, dropped = _apply_field_value(field, value, action, cfg, record_key, date_offset)

        if dropped:
            audit.append({"field": field, "action": "drop", "phi_class": phi_class, "record_key": record_key})
            continue

        attributes[field] = {
            "keyword": field,
            "value": new_val,
            "action": action,
            "phi_class": phi_class,
        }
        if new_val != value:
            audit.append({
                "field": field,
                "action": action,
                "phi_class": phi_class,
                "record_key": record_key,
                "value_hash": hashlib.sha256(value.encode()).hexdigest()[:16],
            })

    return attributes, audit


def anonymize_dicom_metadata_csv(
    df: pd.DataFrame,
    policy: dict,
    id_column: str = "study_uid",
) -> tuple[list[dict], list[dict]]:
    records: list[dict] = []
    audit: list[dict] = []

    if id_column not in df.columns:
        id_column = df.columns[0]

    date_offsets = build_date_offsets(df, id_column)

    for _, row in df.iterrows():
        record_key = str(row[id_column])
        offset = date_offsets.get(record_key, 0)
        attrs, row_audit = row_to_attributes(row, policy, record_key, offset, skip_columns={id_column})
        records.append({
            "record_id": record_key,
            "attributes": attrs,
        })
        audit.extend(row_audit)

    return records, audit


def write_jsonl(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def write_audit_jsonl(audit: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for entry in audit:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def flatten_to_csv(records: list[dict], path: Path) -> None:
    """Convenience export: one row per record, columns = attribute keywords."""
    rows: list[dict[str, Any]] = []
    for rec in records:
        row: dict[str, Any] = {"record_id": rec["record_id"]}
        for field, meta in rec["attributes"].items():
            row[field] = meta["value"]
        rows.append(row)
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
