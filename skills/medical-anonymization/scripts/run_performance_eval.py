#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""End-to-end performance evaluation for medical-anonymization (steps 1-8).

Runs all lanes and writes performance_report.json:
  - DICOM metadata: nested + KV compact + format comparison (local)
  - CSV structured + KV (local)
  - NeMo text: reports preview + EHR note preview (local PHI-safe providers)

Usage::

    conda run -n mr-rate-preprocessing python3 scripts/run_performance_eval.py \\
        --output-dir /tmp/medical_anon_perf
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from metadata_formats import compare_formats, measure_file, read_jsonl  # noqa: E402

DEFAULT_DATASET = Path(
    "/home/marc/code/MRI_DICOM_HEAD_DATA_WITH_PHI/deidentified/metadata/dicom_metadata_full.csv"
)
PROVIDERS = SKILL_ROOT / "references" / "providers.local-phi.yaml"
MODELS = SKILL_ROOT / "references" / "models.local-phi.yaml"
ENTRY = SCRIPT_DIR / "anonymize_medical_data.py"
FORMAT_EVAL = SCRIPT_DIR / "evaluate_metadata_formats.py"


def run_cmd(cmd: list[str], *, timeout: int = 3600) -> dict:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "seconds": round(time.perf_counter() - t0, 2),
        "stdout_tail": proc.stdout[-4000:] if proc.stdout else "",
        "stderr_tail": proc.stderr[-2000:] if proc.stderr else "",
    }


def parse_json_stdout(proc_result: dict) -> dict | None:
    if proc_result["returncode"] != 0:
        return None
    try:
        return json.loads(proc_result["stdout_tail"].split("\n")[-1] if "\n" in proc_result["stdout_tail"] else proc_result["stdout_tail"])
    except json.JSONDecodeError:
        # try full stdout from subprocess re-run pattern - caller passes summary separately
        return None


def lane_dicom_metadata(out_dir: Path, dataset: Path) -> dict:
    lane_dir = out_dir / "lane_dicom"
    cmd = [
        sys.executable, str(FORMAT_EVAL), str(dataset),
        "--output-dir", str(lane_dir),
        "--id-column", "study_uid",
    ]
    res = run_cmd(cmd, timeout=300)
    report_path = lane_dir / "format_evaluation.json"
    body: dict = {"lane": "dicom-metadata", "engine": "deterministic-policy", **res}
    if report_path.exists():
        body["format_evaluation"] = json.loads(report_path.read_text(encoding="utf-8"))
    return body


def lane_csv_structured(out_dir: Path) -> dict:
    lane_dir = out_dir / "lane_csv_structured"
    fixture = SKILL_ROOT / "fixtures" / "sample_ehr.csv"
    cmd = [
        sys.executable, str(ENTRY), str(fixture),
        "--output-dir", str(lane_dir),
        "--id-column", "record_id",
        "--local-only",
    ]
    res = run_cmd(cmd, timeout=120)
    body: dict = {"lane": "csv-structured", "engine": "deterministic-policy", **res}
    kv = lane_dir / "anonymized_data_kv.jsonl"
    if kv.exists():
        body["kv_rows"] = sum(1 for _ in kv.open())
        body["kv_bytes"] = kv.stat().st_size
    return body


def lane_nemo(out_dir: Path, *, fixture: Path, extra_args: list[str], lane_name: str) -> dict:
    lane_dir = out_dir / f"lane_{lane_name}"
    cmd = [
        sys.executable, str(ENTRY), str(fixture),
        "--output-dir", str(lane_dir),
        "--num-records", "2",
        "--model-providers", str(PROVIDERS),
        "--model-configs", str(MODELS),
        *extra_args,
    ]
    res = run_cmd(cmd, timeout=1800)
    body: dict = {"lane": lane_name, "engine": "nemo-anonymizer-local-phi", **res}
    run_report = lane_dir / "run_report.json"
    if run_report.exists():
        summary = json.loads(run_report.read_text(encoding="utf-8"))
        body["summary"] = {
            k: summary.get(k)
            for k in ("skill", "input_kind", "text_strategy", "n_records", "nemo_runs", "telemetry")
        }
    return body


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", default="/tmp/medical_anon_perf")
    p.add_argument("--dataset", default=str(DEFAULT_DATASET))
    p.add_argument("--skip-nemo", action="store_true")
    args = p.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()

    lanes: list[dict] = []
    lanes.append(lane_dicom_metadata(out_dir, Path(args.dataset)))
    lanes.append(lane_csv_structured(out_dir))

    if not args.skip_nemo:
        lanes.append(lane_nemo(
            out_dir,
            fixture=SKILL_ROOT / "fixtures" / "batch00_reports_w_PHI.csv",
            extra_args=["--text-columns", "report_w_PHI", "--id-column", "study_uid", "--text-strategy", "redact"],
            lane_name="nemo_reports",
        ))
        lanes.append(lane_nemo(
            out_dir,
            fixture=SKILL_ROOT / "fixtures" / "sample_ehr.csv",
            extra_args=["--text-columns", "note_text", "--id-column", "record_id", "--text-strategy", "redact"],
            lane_name="nemo_ehr",
        ))

    report = {
        "skill": "medical-anonymization",
        "evaluation": "performance-steps-1-8",
        "dataset": args.dataset,
        "nemo_providers": str(PROVIDERS),
        "nemo_models": str(MODELS),
        "nvidia_api_key_set": bool(os.environ.get("NVIDIA_API_KEY")),
        "lanes": lanes,
        "all_lanes_passed": all(l["returncode"] == 0 for l in lanes),
        "telemetry": {"wall_seconds": round(time.perf_counter() - t0, 2)},
    }
    out_path = out_dir / "performance_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["all_lanes_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
