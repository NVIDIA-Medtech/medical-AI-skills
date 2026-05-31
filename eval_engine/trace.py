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

"""Helpers for evidence-pack agent trace records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TRACE_SCHEMA_VERSION = "0.1.0"


def normalize_trace_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return a trace record with v0 canonical aliases added.

    Historical packs used compact aliases (`ts`, `kind`, `args`, `elapsed_s`).
    New packs keep those aliases for compatibility while also writing the
    longer fields that future schema consumers can depend on.
    """
    normalized = dict(record)
    if "timestamp" not in normalized and normalized.get("ts") is not None:
        normalized["timestamp"] = normalized["ts"]
    if "ts" not in normalized and normalized.get("timestamp") is not None:
        normalized["ts"] = normalized["timestamp"]

    if "event_type" not in normalized:
        for key in ("kind", "type"):
            if normalized.get(key) is not None:
                normalized["event_type"] = normalized[key]
                break
    if "kind" not in normalized and normalized.get("event_type") is not None:
        normalized["kind"] = normalized["event_type"]

    if "inputs" not in normalized and normalized.get("args") is not None:
        normalized["inputs"] = normalized["args"]
    if "duration_seconds" not in normalized:
        for key in ("elapsed_s", "elapsed_seconds"):
            if normalized.get(key) is not None:
                normalized["duration_seconds"] = normalized[key]
                break

    normalized.setdefault("trace_schema_version", TRACE_SCHEMA_VERSION)
    return normalized


def normalize_legacy_trace_record(record: dict[str, Any]) -> dict[str, Any]:
    """Compatibility normalization for validating historical trace records."""
    return normalize_trace_record(record)


def write_trace_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    normalized = [normalize_trace_record(record) for record in records]
    path.write_text("\n".join(json.dumps(record) for record in normalized) + "\n")
