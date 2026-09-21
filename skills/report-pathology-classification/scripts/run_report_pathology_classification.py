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

"""Report pathology classification skill wrapper (MR-RATE reports_preprocessing step 06).

Two execution paths, same output contract:

* ``--mode mock`` (default): a deterministic, GPU-free, stdlib-only rule-based
  classifier. For each report it scans the findings text for the keyword terms
  of every pathology in ``data/pathologies.json`` and emits a complete 0/1
  label vector. Used for fixtures, CI gates, and offline verification. NOT a
  clinical classifier.
* ``--mode live``: subprocesses the upstream
  ``06_pathology_classification/classify_pathologies_parallel.py`` (vLLM)
  on real data, then merges the per-rank ``labels_rank_*.json`` shards into a
  single label table.

Both paths compute the same deterministic quality metrics (label coverage,
JSON-parse success, invalid-label count) and emit one JSON summary on stdout
matching the contract audited by
``medagent.verifiers.report_pathology_quality_v1``.

Only the final JSON summary goes to stdout; all logs go to stderr.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

SKILL_NAME = "report-pathology-classification"

# Default pathology vocabulary lives next to this script's skill dir.
DEFAULT_PATHOLOGIES_JSON = Path(__file__).resolve().parents[1] / "data" / "pathologies.json"


def log(msg: str) -> None:
    print(f"[report-pathology-classification] {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Pathology vocabulary
# ---------------------------------------------------------------------------
def load_pathologies(path: Path) -> dict:
    """Load the pathology -> {terms:[...]} mapping.

    Accepts either the skill's compact schema ({"pathologies": {name: {"terms":
    [...]}}}) or the upstream MR-RATE schema ({"pathologies": {name: {"positive":
    "...", "negative": "..."}}}). For the upstream schema the positive phrase is
    used as the single keyword term so the loader stays compatible.
    """
    if not path.exists():
        raise FileNotFoundError(f"pathologies JSON not found: {path}")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    raw = data.get("pathologies", {})
    if not isinstance(raw, dict) or not raw:
        raise ValueError(f"pathologies JSON has no 'pathologies' object: {path}")
    out: dict[str, list[str]] = {}
    for name, spec in raw.items():
        terms: list[str] = []
        if isinstance(spec, dict):
            if isinstance(spec.get("terms"), list):
                terms = [str(t) for t in spec["terms"] if str(t).strip()]
            elif spec.get("positive"):
                terms = [str(spec["positive"])]
        if not terms:
            # Fall back to the pathology name itself as a term.
            terms = [name]
        out[name] = terms
    return out


# ---------------------------------------------------------------------------
# Mock classifier (deterministic, stdlib only)
# ---------------------------------------------------------------------------
def _term_present(term: str, text_lower: str) -> bool:
    """Case-insensitive whole-word(-ish) keyword match.

    Uses word boundaries so a term like ``cyst`` does not match inside
    ``cystic`` unintentionally; multi-word terms match as a contiguous phrase.
    """
    pat = r"\b" + re.escape(term.lower()) + r"\b"
    return re.search(pat, text_lower) is not None


def mock_classify(text: str, pathologies: dict[str, list[str]]) -> dict[str, int]:
    """Return a complete 0/1 label vector for one report.

    For every pathology, the label is 1 iff any of its keyword terms appears in
    the findings text, else 0. The vector always contains every pathology key,
    so coverage is total.
    """
    text_lower = (text or "").lower()
    labels: dict[str, int] = {}
    for name, terms in pathologies.items():
        labels[name] = 1 if any(_term_present(t, text_lower) for t in terms) else 0
    return labels


# ---------------------------------------------------------------------------
# Shared quality metrics (mock + live)
# ---------------------------------------------------------------------------
def _valid_label_vector(labels: dict, pathology_names: list[str]) -> bool:
    """A vector is valid iff it has exactly the expected keys, all values 0/1."""
    if not isinstance(labels, dict):
        return False
    if set(labels.keys()) != set(pathology_names):
        return False
    return all(v in (0, 1) for v in labels.values())


def summarize(
    records: list[dict],
    pathology_names: list[str],
    pathologies_source: str,
    model: str,
    validation_method: str,
    n_json_parse_failures: int,
    elapsed: float,
) -> dict:
    n_reports = len(records)
    n_labeled = 0
    n_present_total = 0
    n_invalid_labels = 0
    for rec in records:
        labels = rec["labels"]
        if _valid_label_vector(labels, pathology_names):
            n_labeled += 1
            n_present_total += sum(1 for v in labels.values() if v == 1)
        else:
            # Count any out-of-vocabulary or non-0/1 entries as invalid.
            if isinstance(labels, dict):
                extra = set(labels.keys()) - set(pathology_names)
                n_invalid_labels += len(extra)
                n_invalid_labels += sum(1 for v in labels.values() if v not in (0, 1))
            else:
                n_invalid_labels += 1
    coverage = (n_labeled / n_reports) if n_reports else 0.0
    n_attempted = n_reports + n_json_parse_failures
    parse_rate = (n_reports / n_attempted) if n_attempted else 1.0
    return {
        "skill": SKILL_NAME,
        "model": model,
        "n_reports": n_reports,
        "pathologies": {
            "n_labels": len(pathology_names),
            "source": pathologies_source,
        },
        "labels": {
            "n_reports_labeled": n_labeled,
            "n_present_total": n_present_total,
            "label_coverage_rate": round(coverage, 6),
        },
        "validation": {
            "method": validation_method,
            "n_json_parse_failures": n_json_parse_failures,
            "json_parse_success_rate": round(parse_rate, 6),
            "n_invalid_labels": n_invalid_labels,
        },
        "runtime": {"elapsed_seconds": round(elapsed, 4)},
    }


# ---------------------------------------------------------------------------
# CSV I/O
# ---------------------------------------------------------------------------
def read_reports(path: Path, id_col: str, text_col: str, limit: int) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"input CSV not found: {path}")
    rows: list[dict] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if (
            reader.fieldnames is None
            or id_col not in reader.fieldnames
            or text_col not in reader.fieldnames
        ):
            raise ValueError(
                f"input CSV must contain '{id_col}' and '{text_col}' columns; found {reader.fieldnames}"
            )
        for row in reader:
            rows.append({"study_uid": row[id_col], "findings": row[text_col] or ""})
            if limit and len(rows) >= limit:
                break
    if not rows:
        raise ValueError(f"no rows read from {path}")
    return rows


def write_labels_csv(out_path: Path, records: list[dict], pathology_names: list[str]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["study_uid"] + pathology_names)
        for rec in records:
            labels = rec["labels"] if isinstance(rec["labels"], dict) else {}
            writer.writerow([rec["study_uid"]] + [int(labels.get(p, 0)) for p in pathology_names])


# ---------------------------------------------------------------------------
# Live mode: locate + run the upstream vLLM script
# ---------------------------------------------------------------------------
def locate_upstream(explicit_root: str | None) -> Path:
    """Find 06_pathology_classification/classify_pathologies_parallel.py.

    Search order: --mr-rate-root, $MR_RATE_REPORTS_ROOT, then walk up looking
    for the reports_preprocessing tree.
    """
    rel = Path("06_pathology_classification") / "classify_pathologies_parallel.py"
    candidates: list[Path] = []
    if explicit_root:
        candidates.append(Path(explicit_root) / rel)
    env_root = os.environ.get("MR_RATE_REPORTS_ROOT")
    if env_root:
        candidates.append(Path(env_root) / rel)
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidates.append(parent / "reports_preprocessing" / rel)
        candidates.append(parent / rel)
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(
        "could not locate upstream classify_pathologies_parallel.py; set --mr-rate-root "
        "or $MR_RATE_REPORTS_ROOT to the reports_preprocessing directory"
    )


def _prepare_reports_dir(
    fixture: Path, id_col: str, text_col: str, limit: int, reports_dir: Path
) -> None:
    """Stage the input CSV as a batch{NN}_reports.csv the upstream loader reads.

    The upstream loader expects ``study_uid`` and ``findings`` columns inside a
    directory of ``batch{NN}_reports.csv`` files; normalize the caller CSV into
    that shape.
    """
    reports_dir.mkdir(parents=True, exist_ok=True)
    rows = read_reports(fixture, id_col, text_col, limit)
    batch_path = reports_dir / "batch00_reports.csv"
    with batch_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["study_uid", "findings"])
        for r in rows:
            writer.writerow([r["study_uid"], r["findings"]])


def run_live(
    args: argparse.Namespace, work_dir: Path, pathologies_json: Path
) -> tuple[list[dict], list[str], int]:
    upstream = locate_upstream(args.mr_rate_root)
    log(f"live mode: upstream={upstream}")
    reports_dir = work_dir / "upstream_reports"
    shard_dir = work_dir / "upstream_out"
    shard_dir.mkdir(parents=True, exist_ok=True)
    _prepare_reports_dir(args.fixture, args.id_col, args.text_col, args.limit, reports_dir)

    cmd = [
        sys.executable,
        str(upstream),
        "--reports_dir",
        str(reports_dir),
        "--pathologies_json",
        str(pathologies_json),
        "--output_dir",
        str(shard_dir),
        "--model_name",
        args.model,
        "--seed",
        str(args.seed),
    ]
    if args.batch_size:
        cmd += ["--batch_size", str(args.batch_size)]
    env = os.environ.copy()
    # Use the existing HF cache; upstream defaults HF_HOME to "./cache" (CWD),
    # which re-downloads weights into the repo and can fill the disk.
    env.setdefault("HF_HOME", str(Path.home() / ".cache" / "huggingface"))
    if args.cuda_visible_devices is not None:
        env["CUDA_VISIBLE_DEVICES"] = args.cuda_visible_devices
    env.setdefault("SLURM_PROCID", "0")
    env.setdefault("SLURM_NTASKS", "1")
    env.setdefault("SLURM_LOCALID", "0")
    log("launching upstream pathology classifier (this loads vLLM + the model)...")
    proc = subprocess.run(cmd, env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"upstream classifier failed with exit code {proc.returncode}")
    return read_upstream_shards(shard_dir)


def read_upstream_shards(shard_dir: Path) -> tuple[list[dict], list[str], int]:
    shards = sorted(shard_dir.glob("labels_rank_*.json"))
    if not shards:
        raise FileNotFoundError(f"no labels_rank_*.json produced under {shard_dir}")
    records: list[dict] = []
    pathology_names: list[str] = []
    n_parse_failures = 0
    for shard in shards:
        with shard.open(encoding="utf-8") as f:
            data = json.load(f)
        for r in data.get("results", []):
            labels = r.get("labels")
            if not isinstance(labels, dict):
                n_parse_failures += 1
                labels = {}
            if not pathology_names and isinstance(labels, dict) and labels:
                pathology_names = list(labels.keys())
            records.append({"study_uid": r.get("study_uid", ""), "labels": labels})
    return records, pathology_names, n_parse_failures


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Classify MR-RATE brain/spine reports against a pathology list (MR-RATE step 06)."
    )
    p.add_argument("fixture", type=Path, help="input CSV of reports (study_uid + findings columns)")
    p.add_argument("--out", type=Path, default=None, help="evidence/work dir for artifacts")
    p.add_argument(
        "--mode",
        choices=["mock", "live"],
        default="mock",
        help="mock = deterministic keyword match (default, GPU-free); live = upstream vLLM",
    )
    p.add_argument(
        "--model",
        type=str,
        default=None,
        help="HF model id for live mode (default nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4)",
    )
    p.add_argument("--limit", type=int, default=0, help="process only first N reports (0 = all)")
    p.add_argument("--id-col", type=str, default="study_uid")
    p.add_argument("--text-col", type=str, default="findings")
    p.add_argument(
        "--pathologies-json",
        type=Path,
        default=None,
        help="pathology vocabulary JSON (default: skill data/pathologies.json)",
    )
    p.add_argument(
        "--seed", type=int, default=42, help="seed passed to the upstream classifier (live mode)"
    )
    p.add_argument("--batch-size", type=int, default=500)
    p.add_argument(
        "--mr-rate-root",
        type=str,
        default=None,
        help="path to reports_preprocessing dir (live mode upstream lookup)",
    )
    p.add_argument(
        "--cuda-visible-devices",
        type=str,
        default=None,
        help="GPU selection for live mode, e.g. '1'",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    work_dir = (args.out or Path.cwd()).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    pathologies_json = (args.pathologies_json or DEFAULT_PATHOLOGIES_JSON).resolve()
    t0 = time.perf_counter()

    if args.mode == "live":
        model = args.model or "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4"
        records, pathology_names, n_parse_failures = run_live(args, work_dir, pathologies_json)
        validation_method = "llm"
        if not pathology_names:
            # Fall back to the declared vocabulary so the label table is complete.
            pathology_names = list(load_pathologies(pathologies_json).keys())
    else:
        model = args.model or "synthetic-mock-rulebased"
        pathologies = load_pathologies(pathologies_json)
        pathology_names = list(pathologies.keys())
        rows = read_reports(args.fixture, args.id_col, args.text_col, args.limit)
        records = []
        for row in rows:
            labels = mock_classify(row["findings"], pathologies)
            records.append({"study_uid": row["study_uid"], "labels": labels})
        validation_method = "rule_based"
        n_parse_failures = 0

    labels_csv = work_dir / "labels.csv"
    write_labels_csv(labels_csv, records, pathology_names)
    elapsed = time.perf_counter() - t0
    summary = summarize(
        records,
        pathology_names,
        "data/pathologies.json",
        model,
        validation_method,
        n_parse_failures,
        elapsed,
    )
    summary["artifacts"] = {"labels_csv": str(labels_csv)}
    log(
        f"done: {len(records)} reports, n_labels={summary['pathologies']['n_labels']}, "
        f"coverage={summary['labels']['label_coverage_rate']}, "
        f"present_total={summary['labels']['n_present_total']}"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
