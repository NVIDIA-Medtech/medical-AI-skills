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

"""Report anonymization skill wrapper (MR-RATE reports_preprocessing step 01).

Two execution paths, same output contract:

* ``--mode mock`` (default): a deterministic, GPU-free, stdlib-only rule-based
  anonymizer. It replaces a small synthetic PHI vocabulary plus date/accession
  patterns with ``[entity_N]`` tokens. Used for fixtures, CI gates, and offline
  verification. NOT a clinical de-identifier.
* ``--mode live``: subprocesses the upstream
  ``01_anonymization/anonymize_reports_parallel.py`` (vLLM) on real data,
  then parses its ``anonymized_rank_*.csv`` / ``mapping_rank_*.csv`` output.

Both paths compute the same deterministic quality metrics (PHI-leak via mapping
check, token-format validity, token/mapping consistency) and emit one JSON
summary on stdout matching the contract audited by
``medagent.verifiers.report_anonymization_quality_v1``.

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

SKILL_NAME = "report-anonymization"

# Canonical anonymization token, e.g. [patient_1], [date_12], [hospital_e3].
CANONICAL_TOKEN_RE = re.compile(r"^\[[a-z][a-z_]*_\d+\]$")
# Any bracketed run, used to find malformed tokens the LLM may have emitted.
ANY_BRACKET_RE = re.compile(r"\[[^\]\n]{1,60}\]")
# A date in the formats seen in Turkish reports: 01.03.2024, 1/3/24, 2023.
DATE_RE = re.compile(r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b")
# Synthetic accession placeholder used in the fixture, e.g. A12345.
ACCESSION_RE = re.compile(r"\bA\d{4,6}\b")

# Small synthetic vocabulary for the MOCK anonymizer. These are the only proper
# nouns present in the committed synthetic fixture, so the mock redacts the
# fixture exactly. Real PHI removal is the job of --mode live (the LLM).
MOCK_INTERNAL_HOSPITALS = [
    "Medipol Mega Üniversite Hastanesi",
    "Medipol Koşuyolu Hastanesi",
    "Medipol Pendik Üniversite Hastanesi",
]
MOCK_EXTERNAL_HOSPITALS = [
    "Sisli Etfal Hastanesi",
    "Acıbadem Kozyatağı Hastanesi",
]
# Title prefixes that introduce a radiologist / referring doctor name.
MOCK_DOCTOR_TITLE_RE = re.compile(
    r"(?:Prof\.|Doç\.|Uzm\.|Op\.)?\s*Dr\.\s+[A-ZÇĞİÖŞÜ][\wçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][\wçğıöşü]+){1,2}"
)
# "Hasta <Ad Soyad>" -> patient name (capture the name, not the word "Hasta").
MOCK_PATIENT_RE = re.compile(r"(?<=Hasta\s)[A-ZÇĞİÖŞÜ][\wçğıöşü]+\s+[A-ZÇĞİÖŞÜ][\wçğıöşü]+")


def log(msg: str) -> None:
    print(f"[report-anonymization] {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Mock anonymizer (deterministic, stdlib only)
# ---------------------------------------------------------------------------
class _Tokenizer:
    """Assigns stable ``[prefix_N]`` tokens; same original -> same token."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}
        self._seen: dict[tuple[str, str], str] = {}
        self.mapping: dict[str, str] = {}

    def token_for(self, prefix: str, original: str) -> str:
        key = (prefix, original)
        if key in self._seen:
            return self._seen[key]
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        token = f"[{prefix}_{self._counters[prefix]}]"
        self._seen[key] = token
        self.mapping[token] = original
        return token


def mock_anonymize(text: str) -> tuple[str, dict[str, str]]:
    """Deterministically redact the synthetic PHI vocabulary + patterns.

    Order matters: multi-word hospital phrases are removed before the doctor
    pattern so a hospital is never mis-tokenized as a person.
    """
    tok = _Tokenizer()
    out = text

    for hosp in MOCK_INTERNAL_HOSPITALS:
        if hosp in out:
            out = out.replace(hosp, tok.token_for("hospital", hosp))
    for hosp in MOCK_EXTERNAL_HOSPITALS:
        if hosp in out:
            out = out.replace(hosp, tok.token_for("hospital_e", hosp))

    def _sub_first_pass(pattern: re.Pattern, prefix: str, src: str) -> str:
        # Replace every distinct match; build mapping as we go.
        def repl(m: re.Match) -> str:
            original = m.group(0).strip()
            return tok.token_for(prefix, original)

        return pattern.sub(repl, src)

    out = _sub_first_pass(MOCK_PATIENT_RE, "patient", out)
    out = _sub_first_pass(MOCK_DOCTOR_TITLE_RE, "radiologist", out)
    out = _sub_first_pass(DATE_RE, "date", out)
    out = _sub_first_pass(ACCESSION_RE, "accession", out)
    return out, tok.mapping


# ---------------------------------------------------------------------------
# Shared quality metrics (mock + live)
# ---------------------------------------------------------------------------
def _phi_leak(records: list[dict]) -> dict:
    """Deterministic check: no original mapping value survives verbatim."""
    n_evaluated = 0
    n_leaked = 0
    for rec in records:
        mapping = rec["mapping"]
        if not isinstance(mapping, dict) or not mapping:
            continue
        n_evaluated += 1
        anon_lower = rec["anonymized"].lower()
        for original in mapping.values():
            original = (original or "").strip()
            # Skip trivially short originals (e.g. a lone year fragment) to
            # avoid false leaks on common substrings.
            if len(original) < 3:
                continue
            if original.lower() in anon_lower:
                n_leaked += 1
                break
    leak_rate = (n_leaked / n_evaluated) if n_evaluated else 0.0
    return {
        "method": "mapping_deterministic",
        "n_evaluated": n_evaluated,
        "n_leaked": n_leaked,
        "leak_rate": round(leak_rate, 6),
    }


def _token_format(records: list[dict]) -> dict:
    n_with_tokens = 0
    n_malformed = 0
    examples: list[str] = []
    for rec in records:
        text = rec["anonymized"]
        brackets = ANY_BRACKET_RE.findall(text)
        canonical = [b for b in brackets if CANONICAL_TOKEN_RE.match(b)]
        if canonical:
            n_with_tokens += 1
        for b in brackets:
            if not CANONICAL_TOKEN_RE.match(b):
                n_malformed += 1
                if len(examples) < 10:
                    examples.append(b)
    return {
        "n_reports_with_tokens": n_with_tokens,
        "n_malformed_tokens": n_malformed,
        "malformed_examples": examples,
    }


def _token_consistency(records: list[dict]) -> dict:
    n_inconsistent = 0
    n_parsed = 0
    for rec in records:
        mapping = rec["mapping"]
        parsed = isinstance(mapping, dict)
        if parsed:
            n_parsed += 1
        text_tokens = {
            b for b in ANY_BRACKET_RE.findall(rec["anonymized"]) if CANONICAL_TOKEN_RE.match(b)
        }
        keys = set(mapping.keys()) if parsed else set()
        if text_tokens - keys:
            n_inconsistent += 1
    n = len(records)
    return {
        "n_reports": n,
        "n_inconsistent": n_inconsistent,
        "mapping_extraction_rate": round((n_parsed / n) if n else 0.0, 6),
    }


def summarize(records: list[dict], model: str, elapsed: float) -> dict:
    return {
        "skill": SKILL_NAME,
        "model": model,
        "n_reports": len(records),
        "phi_leak": _phi_leak(records),
        "token_format": _token_format(records),
        "token_consistency": _token_consistency(records),
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
            rows.append({"uid": row[id_col], "report": row[text_col] or ""})
            if limit and len(rows) >= limit:
                break
    if not rows:
        raise ValueError(f"no rows read from {path}")
    return rows


def write_anonymized_csv(out_path: Path, records: list[dict]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["UID", "Anonymized_Rapor", "Token_Mapping"])
        for rec in records:
            writer.writerow(
                [rec["uid"], rec["anonymized"], json.dumps(rec["mapping"], ensure_ascii=False)]
            )


# ---------------------------------------------------------------------------
# Live mode: locate + run the upstream vLLM script
# ---------------------------------------------------------------------------
def locate_upstream(explicit_root: str | None) -> Path:
    """Find 01_anonymization/anonymize_reports_parallel.py.

    Search order: --mr-rate-root, $MR_RATE_REPORTS_ROOT, then walk up looking
    for the reports_preprocessing tree.
    """
    rel = Path("01_anonymization") / "anonymize_reports_parallel.py"
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
        "could not locate upstream anonymize_reports_parallel.py; set --mr-rate-root "
        "or $MR_RATE_REPORTS_ROOT to the reports_preprocessing directory"
    )


def run_live(args: argparse.Namespace, work_dir: Path) -> list[dict]:
    upstream = locate_upstream(args.mr_rate_root)
    log(f"live mode: upstream={upstream}")
    shard_dir = work_dir / "upstream_out"
    shard_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(upstream),
        "--input_file",
        str(args.fixture),
        "--output_dir",
        str(shard_dir),
        "--id_col",
        args.id_col,
        "--text_col",
        args.text_col,
        "--model",
        args.model,
        "--chunk_size",
        str(args.chunk_size),
        "--tensor_parallel_size",
        str(args.tensor_parallel_size),
    ]
    if args.limit:
        cmd += ["--limit", str(args.limit)]
    env = os.environ.copy()
    # Use the existing HF cache; upstream defaults HF_HOME to "./cache" (CWD),
    # which re-downloads weights into the repo and can fill the disk.
    env.setdefault("HF_HOME", str(Path.home() / ".cache" / "huggingface"))
    if args.cuda_visible_devices is not None:
        env["CUDA_VISIBLE_DEVICES"] = args.cuda_visible_devices
    env.setdefault("SLURM_PROCID", "0")
    env.setdefault("SLURM_NTASKS", "1")
    log("launching upstream anonymizer (this loads vLLM + the model)...")
    proc = subprocess.run(cmd, env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"upstream anonymizer failed with exit code {proc.returncode}")
    return read_upstream_shards(shard_dir, args.id_col)


def read_upstream_shards(shard_dir: Path, id_col: str) -> list[dict]:
    shards = sorted(shard_dir.glob("anonymized_rank_*.csv"))
    if not shards:
        raise FileNotFoundError(f"no anonymized_rank_*.csv produced under {shard_dir}")
    records: list[dict] = []
    for shard in shards:
        with shard.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                raw_map = row.get("Token_Mapping", "") or ""
                try:
                    mapping = json.loads(raw_map) if raw_map.strip() else {}
                    if not isinstance(mapping, dict):
                        mapping = {}
                except json.JSONDecodeError:
                    mapping = {}
                records.append(
                    {
                        "uid": row.get(id_col, ""),
                        "anonymized": row.get("Anonymized_Rapor", "") or "",
                        "mapping": mapping,
                    }
                )
    return records


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Anonymize Turkish radiology reports (MR-RATE step 01)."
    )
    p.add_argument("fixture", type=Path, help="input CSV of reports (UID + report columns)")
    p.add_argument("--out", type=Path, default=None, help="evidence/work dir for artifacts")
    p.add_argument(
        "--mode",
        choices=["mock", "live"],
        default="mock",
        help="mock = deterministic rule-based (default, GPU-free); live = upstream vLLM",
    )
    p.add_argument(
        "--model",
        type=str,
        default=None,
        help="HF model id for live mode (default nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4)",
    )
    p.add_argument("--limit", type=int, default=0, help="process only first N reports (0 = all)")
    p.add_argument("--id-col", type=str, default="UID")
    p.add_argument("--text-col", type=str, default="report")
    p.add_argument("--chunk-size", type=int, default=200)
    p.add_argument(
        "--tensor-parallel-size",
        type=int,
        default=1,
        help="GPUs to shard the model across (2 = both RTX 6000 Ada; "
        "needed to fit a 30-35B model on this box). Pair with --cuda-visible-devices '1,2'.",
    )
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
    t0 = time.perf_counter()

    if args.mode == "live":
        model = args.model or "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4"
        records = run_live(args, work_dir)
    else:
        model = args.model or "synthetic-mock-rulebased"
        rows = read_reports(args.fixture, args.id_col, args.text_col, args.limit)
        records = []
        for row in rows:
            anon, mapping = mock_anonymize(row["report"])
            records.append({"uid": row["uid"], "anonymized": anon, "mapping": mapping})

    write_anonymized_csv(work_dir / "anonymized.csv", records)
    elapsed = time.perf_counter() - t0
    summary = summarize(records, model, elapsed)
    summary["artifacts"] = {"anonymized_csv": str((work_dir / "anonymized.csv"))}
    log(f"done: {len(records)} reports, leak_rate={summary['phi_leak']['leak_rate']}")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
