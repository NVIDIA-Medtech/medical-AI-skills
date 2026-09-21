#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Wide CSV ↔ long (record_id, field, value) ↔ nested/KV JSONL conversions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

KV_KEYS = ("record_id", "field", "value", "action", "phi_class")


def wide_csv_to_long(df: pd.DataFrame, id_column: str) -> pd.DataFrame:
    """Melt wide CSV to one row per (record_id, field, value). Skips blanks."""
    if id_column not in df.columns:
        id_column = df.columns[0]
    value_cols = [c for c in df.columns if c != id_column]
    long_df = df.melt(id_vars=[id_column], value_vars=value_cols, var_name="field", value_name="value")
    long_df = long_df.rename(columns={id_column: "record_id"})
    long_df["value"] = long_df["value"].astype(str)
    long_df = long_df[long_df["value"].str.strip() != ""]
    long_df = long_df[long_df["value"].str.lower() != "nan"]
    return long_df.reset_index(drop=True)


def long_df_to_kv_rows(
    long_df: pd.DataFrame,
    *,
    action_col: str | None = None,
    phi_class_col: str | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _, r in long_df.iterrows():
        entry: dict[str, Any] = {
            "record_id": str(r["record_id"]),
            "field": str(r["field"]),
            "value": str(r["value"]),
        }
        if action_col and action_col in long_df.columns and pd.notna(r.get(action_col)):
            entry["action"] = str(r[action_col])
        if phi_class_col and phi_class_col in long_df.columns and pd.notna(r.get(phi_class_col)):
            entry["phi_class"] = str(r[phi_class_col])
        rows.append(entry)
    return rows


def nested_records_to_kv(
    records: Iterable[dict],
    *,
    compact: bool = False,
) -> list[dict[str, Any]]:
    """One nested record per study → many (record_id, field, value) rows."""
    rows: list[dict[str, Any]] = []
    for rec in records:
        rid = rec["record_id"]
        for field, meta in rec.get("attributes", {}).items():
            if compact:
                rows.append({"record_id": rid, "field": field, "value": meta["value"]})
            else:
                rows.append({
                    "record_id": rid,
                    "field": field,
                    "value": meta["value"],
                    "action": meta.get("action", "keep"),
                    "phi_class": meta.get("phi_class", "technical"),
                })
    return rows


def kv_rows_to_nested(kv_rows: Iterable[dict], *, preserve_order: bool = True) -> list[dict]:
    """Reconstruct nested records from KV rows (round-trip check)."""
    order: list[str] = []
    by_id: dict[str, dict[str, dict]] = {}
    for row in kv_rows:
        rid = row["record_id"]
        if rid not in by_id:
            order.append(rid)
            by_id[rid] = {}
        field = row["field"]
        by_id[rid][field] = {
            "keyword": field,
            "value": row["value"],
            "action": row.get("action", "keep"),
            "phi_class": row.get("phi_class", "technical"),
        }
    ids = order if preserve_order else sorted(by_id)
    return [{"record_id": rid, "attributes": by_id[rid]} for rid in ids]


def kv_rows_to_wide_csv(kv_rows: Iterable[dict], path: Path) -> None:
    """Pivot KV rows back to wide CSV (one row per record_id)."""
    rows = list(kv_rows)
    if not rows:
        pd.DataFrame(columns=["record_id"]).to_csv(path, index=False, encoding="utf-8-sig")
        return
    df = pd.DataFrame(rows)
    wide = df.pivot_table(index="record_id", columns="field", values="value", aggfunc="first")
    wide = wide.reset_index()
    wide.to_csv(path, index=False, encoding="utf-8-sig")


def write_jsonl_rows(rows: Iterable[dict], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


def read_jsonl(path: Path) -> list[dict]:
    out: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def estimate_tokens(text: str, model: str = "cl100k_base") -> int:
    try:
        import tiktoken

        enc = tiktoken.get_encoding(model)
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text) // 4)


def measure_file(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "lines": len(lines),
        "chars": len(raw),
        "tokens_estimated": estimate_tokens(raw),
        "bytes_per_line": round(path.stat().st_size / max(len(lines), 1), 1),
        "tokens_per_line": round(estimate_tokens(raw) / max(len(lines), 1), 1),
    }


def per_record_token_stats(nested_path: Path, kv_path: Path, kv_compact_path: Path) -> dict[str, Any]:
    nested_lines = read_jsonl(nested_path)
    kv_by_id: dict[str, list[str]] = {}
    for row in read_jsonl(kv_path):
        kv_by_id.setdefault(row["record_id"], []).append(json.dumps(row, ensure_ascii=False))
    compact_by_id: dict[str, list[str]] = {}
    for row in read_jsonl(kv_compact_path):
        compact_by_id.setdefault(row["record_id"], []).append(json.dumps(row, ensure_ascii=False))

    nested_toks, kv_toks, compact_toks = [], [], []
    for rec in nested_lines:
        rid = rec["record_id"]
        nested_toks.append(estimate_tokens(json.dumps(rec, ensure_ascii=False)))
        kv_toks.append(estimate_tokens("\n".join(kv_by_id.get(rid, []))))
        compact_toks.append(estimate_tokens("\n".join(compact_by_id.get(rid, []))))

    def _median(xs: list[int]) -> float:
        xs = sorted(xs)
        m = len(xs) // 2
        return float(xs[m]) if xs else 0.0

    return {
        "median_tokens_per_record": {
            "nested": _median(nested_toks),
            "kv_full": _median(kv_toks),
            "kv_compact": _median(compact_toks),
        },
        "total_tokens_per_record_sum": {
            "nested": sum(nested_toks),
            "kv_full": sum(kv_toks),
            "kv_compact": sum(compact_toks),
        },
    }


def compare_formats(
    nested_path: Path,
    kv_path: Path,
    kv_compact_path: Path,
    *,
    n_fields: int,
    n_records: int,
) -> dict[str, Any]:
    nested_m = measure_file(nested_path)
    kv_m = measure_file(kv_path)
    compact_m = measure_file(kv_compact_path)

    kv_rows = read_jsonl(kv_path)
    nested_orig = read_jsonl(nested_path)
    round_trip_ok = kv_rows_to_nested(kv_rows) == nested_orig

    per_rec = per_record_token_stats(nested_path, kv_path, kv_compact_path)

    return {
        "n_records": n_records,
        "n_fields_populated": n_fields,
        "nested": {**nested_m, "fool_proof": "one_line_per_record"},
        "kv_full": {**kv_m, "fool_proof": "one_line_per_field_with_action"},
        "kv_compact": {**compact_m, "fool_proof": "one_line_per_field_minimal"},
        "file_totals": {
            "kv_full_vs_nested_bytes_ratio": round(kv_m["bytes"] / max(nested_m["bytes"], 1), 3),
            "kv_compact_vs_nested_bytes_ratio": round(compact_m["bytes"] / max(nested_m["bytes"], 1), 3),
            "kv_compact_vs_nested_tokens_ratio": round(
                compact_m["tokens_estimated"] / max(nested_m["tokens_estimated"], 1), 3
            ),
        },
        "per_record_tokens": per_rec,
        "round_trip_kv_to_nested": round_trip_ok,
        "recommendation": _recommendation(nested_m, kv_m, compact_m, per_rec),
    }


def _recommendation(nested_m: dict, kv_m: dict, compact_m: dict, per_rec: dict) -> str:
    med = per_rec["median_tokens_per_record"]
    parts = []
    if compact_m["tokens_estimated"] < nested_m["tokens_estimated"]:
        pct = round(100 * (1 - compact_m["tokens_estimated"] / nested_m["tokens_estimated"]), 1)
        parts.append(f"kv-compact saves {pct}% total tokens vs nested")
    else:
        pct = round(100 * (1 - nested_m["tokens_estimated"] / compact_m["tokens_estimated"]), 1)
        parts.append(f"nested saves {pct}% total tokens vs kv-compact")
    if med["kv_compact"] < med["nested"]:
        parts.append("kv-compact wins per-study median token budget")
    else:
        parts.append("nested wins per-study median token budget")
    parts.append("kv lines are stream-parseable; nested is one JSON object per study")
    return "; ".join(parts)
