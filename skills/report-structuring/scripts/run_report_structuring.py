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

"""Report structuring skill wrapper (MR-RATE reports_preprocessing steps 04 + 05).

Two execution paths, same output contract:

* ``--mode mock`` (default): a deterministic, GPU-free, stdlib-only structurer.
  It splits each English report on its section headers (``Clinical Information:``,
  ``Technique:``, ``Findings:``, ``Impression:``) into 4 fields, then normalizes
  formatting: findings become flowing sentences (no bullets), impression becomes
  em-dash (U+2014) bullets. A deterministic rule-based QC then checks each
  structured row for missing findings/impression, header leakage, and format
  violations. Used for fixtures, CI gates, and offline verification. NOT a
  clinical structurer.
* ``--mode live``: subprocesses the upstream
  ``04_structuring/structure_reports_parallel.py`` (vLLM) to structure
  real reports, then optionally subprocesses
  ``05_structure_qc/qc_llm_verify.py`` for the LLM-judge QC pass, and parses the
  ``structure_rank_*.csv`` / ``qc_rank_*.csv`` shards.

Both paths compute the same deterministic quality metrics (parse success,
section completeness, QC pass-rate, format violations) and emit one JSON summary
on stdout matching the contract audited by
``medagent.verifiers.report_structuring_quality_v1``.

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

SKILL_NAME = "report-structuring"

# The 4 canonical section headers, in report order. The mock structurer splits
# on these (case-insensitive, line-anchored). Each maps to an output column.
SECTION_HEADERS = [
    ("clinical_information", "Clinical Information"),
    ("technique", "Technique"),
    ("findings", "Findings"),
    ("impression", "Impression"),
]
HEADER_LABELS = [label for _, label in SECTION_HEADERS]

# A header line is "<Label>:" optionally with trailing content on the same line.
# Built once from the labels above so the splitter and the leak-check agree.
_HEADER_ALT = "|".join(re.escape(lbl) for lbl in HEADER_LABELS)
HEADER_LINE_RE = re.compile(rf"^\s*({_HEADER_ALT})\s*:\s*(.*)$", re.IGNORECASE)
# Any residual header label followed by a colon, used to detect leaks in bodies.
HEADER_LEAK_RE = re.compile(rf"(?:{_HEADER_ALT})\s*:", re.IGNORECASE)
# Bullet markers that must NOT appear in findings (which are flowing sentences).
BULLET_RE = re.compile(r"(?m)^\s*(?:[—–\-\*•·]|\d+[.)])\s+")
# The canonical impression bullet prefix: em dash + space (U+2014).
EM_DASH = "—"
IMPRESSION_BULLET_PREFIX = EM_DASH + " "


def log(msg: str) -> None:
    print(f"[report-structuring] {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Mock structurer (deterministic, stdlib only)
# ---------------------------------------------------------------------------
def _split_sections(text: str) -> dict[str, str]:
    """Split a report into the 4 canonical sections on its header lines.

    Returns a dict with keys clinical_information/technique/findings/impression.
    Content before the first recognized header is discarded (title/greeting
    lines), matching the upstream "remove standalone title lines" rule.
    """
    sections: dict[str, str] = {key: "" for key, _ in SECTION_HEADERS}
    label_to_key = {label.lower(): key for key, label in SECTION_HEADERS}

    # Match headers wherever they occur — line-anchored (multi-line reports) or
    # inline within a sentence (single-line reports) — so both layouts parse.
    matches = list(re.finditer(rf"({_HEADER_ALT})\s*:", text, re.IGNORECASE))
    if not matches:
        return sections
    for i, m in enumerate(matches):
        key = label_to_key[m.group(1).lower()]
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections[key] = (sections[key] + " " + body).strip() if sections[key] else body
    return sections


def _normalize_findings(text: str) -> str:
    """Findings = flowing sentences. Strip bullet markers, collapse blank lines."""
    if not text:
        return ""
    lines = []
    for line in text.splitlines():
        stripped = BULLET_RE.sub("", line).strip()
        if stripped:
            lines.append(stripped)
    # Join distinct observations into a single flowing paragraph.
    return " ".join(lines).strip()


def _normalize_impression(text: str) -> str:
    """Impression = one em-dash bullet per distinct line."""
    if not text:
        return ""
    out_lines = []
    for line in text.splitlines():
        stripped = BULLET_RE.sub("", line).strip()
        if not stripped:
            continue
        out_lines.append(IMPRESSION_BULLET_PREFIX + stripped)
    return "\n".join(out_lines).strip()


def mock_structure(text: str) -> dict:
    """Deterministically structure one report into 4 normalized sections."""
    sections = _split_sections(text)
    findings = _normalize_findings(sections["findings"])
    impression = _normalize_impression(sections["impression"])
    has_any = bool(findings or impression)
    return {
        "clinical_information": sections["clinical_information"],
        "technique": sections["technique"],
        "findings": findings,
        "impression": impression,
        "parse_status": "ok" if has_any else "parse_failed",
    }


# ---------------------------------------------------------------------------
# Shared quality metrics (mock + live)
# ---------------------------------------------------------------------------
def _parse_block(records: list[dict], method: str) -> dict:
    n_eval = len(records)
    n_fail = sum(1 for r in records if r.get("parse_status") != "ok")
    rate = ((n_eval - n_fail) / n_eval) if n_eval else 0.0
    return {
        "method": method,
        "n_evaluated": n_eval,
        "n_parse_failures": n_fail,
        "parse_success_rate": round(rate, 6),
    }


def _sections_block(records: list[dict]) -> dict:
    ok = [r for r in records if r.get("parse_status") == "ok"]
    n_find = sum(1 for r in ok if (r.get("findings") or "").strip())
    n_imp = sum(1 for r in ok if (r.get("impression") or "").strip())
    # Complete = has both a non-empty findings and impression.
    n_complete = sum(
        1 for r in ok if (r.get("findings") or "").strip() and (r.get("impression") or "").strip()
    )
    rate = (n_complete / len(ok)) if ok else 0.0
    return {
        "n_with_findings": n_find,
        "n_with_impression": n_imp,
        "completeness_rate": round(rate, 6),
    }


def _format_block(records: list[dict]) -> dict:
    """Deterministic format check over structured rows.

    A violation is: (a) a bullet marker inside findings, or (b) a leaked section
    header inside any section body. n_findings_bulleted counts rows whose
    findings still carry bullets (a subset of violations).
    """
    n_findings_bulleted = 0
    n_header_leaks = 0
    n_violations = 0
    for r in records:
        if r.get("parse_status") != "ok":
            continue
        findings = r.get("findings") or ""
        impression = r.get("impression") or ""
        clin = r.get("clinical_information") or ""
        tech = r.get("technique") or ""

        bulleted = bool(BULLET_RE.search(findings))
        if bulleted:
            n_findings_bulleted += 1
            n_violations += 1

        leaked = False
        for body in (clin, tech, findings, impression):
            if HEADER_LEAK_RE.search(body):
                leaked = True
                break
        if leaked:
            n_header_leaks += 1
            n_violations += 1
    return {
        "n_findings_bulleted": n_findings_bulleted,
        "n_header_leaks": n_header_leaks,
        "n_format_violations": n_violations,
    }


def _qc_block_rule_based(records: list[dict]) -> dict:
    """Rule-based QC: a row passes if it parsed ok, has findings + impression,
    impression bullets use the em-dash prefix, and findings carry no bullets."""
    n_eval = 0
    n_pass = 0
    n_fail = 0
    for r in records:
        if r.get("parse_status") != "ok":
            continue
        n_eval += 1
        findings = r.get("findings") or ""
        impression = r.get("impression") or ""
        ok = (
            bool(findings.strip())
            and bool(impression.strip())
            and not BULLET_RE.search(findings)
            and all(
                line.startswith(IMPRESSION_BULLET_PREFIX)
                for line in impression.splitlines()
                if line.strip()
            )
        )
        if ok:
            n_pass += 1
        else:
            n_fail += 1
    rate = (n_pass / n_eval) if n_eval else 0.0
    return {
        "method": "rule_based",
        "n_evaluated": n_eval,
        "n_pass": n_pass,
        "n_fail": n_fail,
        "n_unknown": 0,
        "pass_rate": round(rate, 6),
    }


def _qc_block_from_verdicts(records: list[dict], verdicts: dict[str, str]) -> dict:
    """LLM-judge QC: tally pass/fail/unknown from upstream qc_rank verdicts."""
    n_eval = 0
    n_pass = n_fail = n_unknown = 0
    for r in records:
        if r.get("parse_status") != "ok":
            continue
        n_eval += 1
        verdict = verdicts.get(str(r.get("uid", "")), "unknown")
        if verdict == "pass":
            n_pass += 1
        elif verdict == "fail":
            n_fail += 1
        else:
            n_unknown += 1
    rate = (n_pass / n_eval) if n_eval else 0.0
    return {
        "method": "llm_judge",
        "n_evaluated": n_eval,
        "n_pass": n_pass,
        "n_fail": n_fail,
        "n_unknown": n_unknown,
        "pass_rate": round(rate, 6),
    }


def summarize(records: list[dict], model: str, elapsed: float, qc: dict, parse_method: str) -> dict:
    return {
        "skill": SKILL_NAME,
        "model": model,
        "n_reports": len(records),
        "parse": _parse_block(records, parse_method),
        "sections": _sections_block(records),
        "qc": qc,
        "format": _format_block(records),
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


def write_structured_csv(out_path: Path, records: list[dict]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cols = ["UID", "clinical_information", "technique", "findings", "impression", "parse_status"]
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        for rec in records:
            writer.writerow(
                [
                    rec.get("uid", ""),
                    rec.get("clinical_information", ""),
                    rec.get("technique", ""),
                    rec.get("findings", ""),
                    rec.get("impression", ""),
                    rec.get("parse_status", ""),
                ]
            )


# ---------------------------------------------------------------------------
# Live mode: locate + run the upstream vLLM scripts
# ---------------------------------------------------------------------------
def _locate_upstream(explicit_root: str | None, rel: Path) -> Path:
    """Find an upstream script under reports_preprocessing.

    Search order: --mr-rate-root, $MR_RATE_REPORTS_ROOT, then walk up looking
    for the reports_preprocessing tree.
    """
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
        f"could not locate upstream {rel}; set --mr-rate-root or "
        "$MR_RATE_REPORTS_ROOT to the reports_preprocessing directory"
    )


def run_live(args: argparse.Namespace, work_dir: Path) -> tuple[list[dict], dict[str, str], bool]:
    structure_script = _locate_upstream(
        args.mr_rate_root, Path("04_structuring") / "structure_reports_parallel.py"
    )
    log(f"live mode: structuring upstream={structure_script}")
    struct_dir = work_dir / "structure_out"
    struct_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    # Use the existing HF cache; upstream defaults HF_HOME to "./cache" (CWD),
    # which re-downloads weights into the repo and can fill the disk.
    env.setdefault("HF_HOME", str(Path.home() / ".cache" / "huggingface"))
    if args.cuda_visible_devices is not None:
        env["CUDA_VISIBLE_DEVICES"] = args.cuda_visible_devices
    env.setdefault("SLURM_PROCID", "0")
    env.setdefault("SLURM_NTASKS", "1")
    env.setdefault("SLURM_LOCALID", args.cuda_visible_devices or "0")

    cmd = [
        sys.executable,
        str(structure_script),
        "--input_file",
        str(args.fixture),
        "--output_dir",
        str(struct_dir),
    ]
    log("launching upstream structurer (this loads vLLM + the model)...")
    proc = subprocess.run(cmd, env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"upstream structurer failed with exit code {proc.returncode}")
    records = _read_structure_shards(struct_dir)

    verdicts: dict[str, str] = {}
    qc_ran = False
    if not args.no_qc:
        qc_script = _locate_upstream(
            args.mr_rate_root, Path("05_structure_qc") / "qc_llm_verify.py"
        )
        log(f"live mode: qc upstream={qc_script}")
        # The QC script consumes the merged structured CSV with raw_report.
        merged = struct_dir / "structured_merged.csv"
        _merge_structure_shards(struct_dir, merged)
        qc_dir = work_dir / "qc_out"
        qc_dir.mkdir(parents=True, exist_ok=True)
        qc_cmd = [
            sys.executable,
            str(qc_script),
            "--input_file",
            str(merged),
            "--output_dir",
            str(qc_dir),
        ]
        log("launching upstream QC judge...")
        qc_proc = subprocess.run(qc_cmd, env=env)
        if qc_proc.returncode != 0:
            raise RuntimeError(f"upstream QC failed with exit code {qc_proc.returncode}")
        verdicts = _read_qc_shards(qc_dir)
        qc_ran = True
    return records, verdicts, qc_ran


def _read_structure_shards(struct_dir: Path) -> list[dict]:
    shards = sorted(struct_dir.glob("structure_rank_*.csv"))
    if not shards:
        raise FileNotFoundError(f"no structure_rank_*.csv produced under {struct_dir}")
    records: list[dict] = []
    for shard in shards:
        with shard.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                status = row.get("parse_status", "ok") or "ok"
                records.append(
                    {
                        "uid": row.get("UID", "") or row.get("AccessionNo", ""),
                        "accession": row.get("AccessionNo", ""),
                        "raw_report": row.get("raw_report", "") or "",
                        "clinical_information": row.get("clinical_information", "") or "",
                        "technique": row.get("technique", "") or "",
                        "findings": row.get("findings", "") or "",
                        "impression": row.get("impression", "") or "",
                        "parse_status": "ok" if status == "ok" else status,
                    }
                )
    return records


def _merge_structure_shards(struct_dir: Path, merged: Path) -> None:
    shards = sorted(struct_dir.glob("structure_rank_*.csv"))
    fieldnames: list[str] | None = None
    rows: list[dict] = []
    for shard in shards:
        with shard.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if fieldnames is None:
                fieldnames = list(reader.fieldnames or [])
            for row in reader:
                rows.append(row)
    if fieldnames is None:
        fieldnames = []
    with merged.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _read_qc_shards(qc_dir: Path) -> dict[str, str]:
    verdicts: dict[str, str] = {}
    for shard in sorted(qc_dir.glob("qc_rank_*.csv")):
        with shard.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                acc = str(row.get("AccessionNo", ""))
                verdicts[acc] = row.get("verdict", "unknown") or "unknown"
    return verdicts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Structure English radiology reports into 4 sections (MR-RATE steps 04 + 05)."
    )
    p.add_argument("fixture", type=Path, help="input CSV of reports (UID + report columns)")
    p.add_argument("--out", type=Path, default=None, help="evidence/work dir for artifacts")
    p.add_argument(
        "--mode",
        choices=["mock", "live"],
        default="mock",
        help="mock = deterministic header-split (default, GPU-free); live = upstream vLLM",
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
    p.add_argument(
        "--no-qc",
        action="store_true",
        help="live mode only: skip the upstream LLM-judge QC pass (step 05)",
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
        records, verdicts, qc_ran = run_live(args, work_dir)
        parse_method = "llm"
        if qc_ran:
            qc = _qc_block_from_verdicts(records, verdicts)
        else:
            qc = _qc_block_rule_based(records)
    else:
        model = args.model or "synthetic-mock"
        rows = read_reports(args.fixture, args.id_col, args.text_col, args.limit)
        records = []
        for row in rows:
            structured = mock_structure(row["report"])
            structured["uid"] = row["uid"]
            records.append(structured)
        parse_method = "rule_based"
        qc = _qc_block_rule_based(records)

    write_structured_csv(work_dir / "structured.csv", records)
    elapsed = time.perf_counter() - t0
    summary = summarize(records, model, elapsed, qc, parse_method)
    summary["artifacts"] = {"structured_csv": str((work_dir / "structured.csv"))}
    log(
        f"done: {len(records)} reports, parse_success_rate="
        f"{summary['parse']['parse_success_rate']}, qc.pass_rate={summary['qc']['pass_rate']}, "
        f"format.n_format_violations={summary['format']['n_format_violations']}"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
