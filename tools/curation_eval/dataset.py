# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Step 1: build the evaluation dataset from the real MR-RATE corpus.

Responsibilities:

* Sample ``n`` reports (seeded, reproducible) from ``data/MR-RATE/reports/reports``,
  restricted to ``study_uid``s that also have ground-truth pathology labels in
  ``mrrate_labels.csv`` (so step-3 accuracy is gradeable).
* Guarantee the sampled reports are genuinely PII-free (they are already
  de-identified), then inject known PII into ``inject_pii_k`` of them so step 2
  ("confirm no PII") is a real detection task with a known answer key.
* Emit ``evaluation_dataset.csv`` (the shared input both arms operate on) and
  ``ground_truth.json`` (the answer key: gold labels + injected-PII record).

The dataset build is deterministic and needs no LLM, so this artifact is a real
result on its own.
"""

from __future__ import annotations

import csv
import json
import random
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from . import paths

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# --- Broad PII oracle: only used at sampling time to reject candidate reports
#     that already trip any identifier pattern, so the "clean" pool is truly
#     clean and ground truth == the injection record. ---------------------------
_ORACLE_PATTERNS: dict[str, re.Pattern] = {
    "date": re.compile(r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b"),
    "accession": re.compile(r"\bA\d{4,6}\b"),
    "doctor": re.compile(
        r"(?:Prof\.|Do\u00e7\.|Uzm\.|Op\.)?\s*Dr\.\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){1,2}"
    ),
    "phone": re.compile(r"\b(?:\+?\d[\d ().-]{7,}\d)\b"),
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    "mrn": re.compile(r"\b(?:MRN|mrn)[:#]?\s*\d{4,}\b"),
}

# --- Injectable PII: forms detectable both by a regex reviewer and by the
#     report-anonymization skill's mock detectors (Dr. Name / date / accession). --
_INJECT_DOCTORS = [
    "Dr. John Smith",
    "Prof. Dr. Michael Brown",
    "Dr. Emily Carter",
    "Dr. Robert Johnson",
    "Dr. Sarah Williams",
    "Dr. David Miller",
]
_INJECT_DATES = ["12.03.2024", "05.11.2023", "27.01.2025", "09.07.2022", "18.09.2024"]
_INJECT_ACCESSIONS = ["A123456", "A784512", "A305199", "A662014", "A990321"]


def scan_pii(text: str) -> list[dict]:
    """Return a list of ``{"type", "value"}`` hits from the broad oracle."""
    hits: list[dict] = []
    for kind, pat in _ORACLE_PATTERNS.items():
        for m in pat.finditer(text or ""):
            hits.append({"type": kind, "value": m.group(0).strip()})
    return hits


@dataclass
class Dataset:
    out_dir: Path
    csv_path: Path
    gt_path: Path
    seed: int
    text_col: str
    id_col: str
    records: list[dict]
    ground_truth: dict
    vocab: list[str]  # pathology label names shared by skill + gold

    @property
    def n(self) -> int:
        return len(self.records)


# ---------------------------------------------------------------------------
# Ground-truth pathology labels
# ---------------------------------------------------------------------------
def load_gold_labels() -> tuple[list[str], dict[str, dict[str, int]]]:
    """Load ``mrrate_labels.csv`` -> (label_names, {uid: {label: 0/1}})."""
    if not paths.LABELS_CSV.exists():
        raise FileNotFoundError(f"labels CSV not found: {paths.LABELS_CSV}")
    gold: dict[str, dict[str, int]] = {}
    with paths.LABELS_CSV.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        names = [c for c in (reader.fieldnames or []) if c != "study_uid"]
        for row in reader:
            uid = (row.get("study_uid") or "").strip()
            if not uid:
                continue
            vec: dict[str, int] = {}
            for name in names:
                try:
                    vec[name] = 1 if int(row.get(name) or 0) else 0
                except (TypeError, ValueError):
                    vec[name] = 0
            gold[uid] = vec
    return names, gold


def load_skill_vocab() -> list[str]:
    """Pathology names the skill's bundled vocabulary covers (the mock subset)."""
    with paths.PATHOLOGIES_JSON.open(encoding="utf-8") as f:
        data = json.load(f)
    return list((data.get("pathologies") or {}).keys())


# ---------------------------------------------------------------------------
# Corpus access
# ---------------------------------------------------------------------------
def _corpus_files() -> list[Path]:
    files = sorted(paths.DATA_REPORTS_DIR.glob("batch*_reports.csv"))
    if not files:
        raise FileNotFoundError(f"no batch*_reports.csv under {paths.DATA_REPORTS_DIR}")
    return files


def _build_uid_index(gold_uids: set[str]) -> dict[str, Path]:
    """Map each gold-labelled ``study_uid`` to the first corpus file it appears in."""
    index: dict[str, Path] = {}
    for fp in _corpus_files():
        with fp.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or "study_uid" not in reader.fieldnames:
                continue
            for row in reader:
                uid = (row.get("study_uid") or "").strip()
                if uid and uid in gold_uids and uid not in index:
                    index[uid] = fp
    return index


def _read_rows_for_uids(uids_by_file: dict[Path, set[str]]) -> dict[str, dict]:
    """Read the full report rows for the requested uids, one scan per file."""
    out: dict[str, dict] = {}
    for fp, wanted in uids_by_file.items():
        remaining = set(wanted)
        with fp.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                uid = (row.get("study_uid") or "").strip()
                if uid in remaining:
                    out[uid] = dict(row)
                    remaining.discard(uid)
                    if not remaining:
                        break
    return out


# ---------------------------------------------------------------------------
# PII injection
# ---------------------------------------------------------------------------
def _inject_pii(text: str, rng: random.Random) -> tuple[str, list[dict]]:
    doctor = rng.choice(_INJECT_DOCTORS)
    date = rng.choice(_INJECT_DATES)
    accession = rng.choice(_INJECT_ACCESSIONS)
    line = f"\n\nReported by {doctor} on {date}. Accession {accession}."
    items = [
        {"type": "doctor", "value": doctor},
        {"type": "date", "value": date},
        {"type": "accession", "value": accession},
    ]
    return text + line, items


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build_dataset(
    out_dir: Path,
    n: int = 10,
    seed: int = 42,
    inject_pii_k: int = 3,
    text_col: str = "report",
    id_col: str = "study_uid",
) -> Dataset:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)

    label_names, gold = load_gold_labels()
    skill_vocab = load_skill_vocab()
    # The label set we can both classify (skill) and grade (gold).
    vocab = [name for name in skill_vocab if name in set(label_names)]
    if not vocab:
        raise RuntimeError("skill pathology vocabulary does not intersect gold label columns")

    index = _build_uid_index(set(gold.keys()))
    candidate_uids = list(index.keys())
    rng.shuffle(candidate_uids)

    # Pull a pool bigger than n so we can reject any non-clean candidates.
    pool_uids = candidate_uids[: max(n * 8, n + 20)]
    uids_by_file: dict[Path, set[str]] = {}
    for uid in pool_uids:
        uids_by_file.setdefault(index[uid], set()).add(uid)
    rows_by_uid = _read_rows_for_uids(uids_by_file)

    # Keep only genuinely clean reports (no oracle hit) with non-empty text.
    clean_uids: list[str] = []
    for uid in pool_uids:  # preserve shuffled order
        row = rows_by_uid.get(uid)
        if not row:
            continue
        text = (row.get(text_col) or "").strip()
        findings = (row.get("findings") or "").strip()
        if not text or not findings:
            continue
        if scan_pii(row.get(text_col) or ""):
            continue
        clean_uids.append(uid)
        if len(clean_uids) >= n:
            break
    if len(clean_uids) < n:
        raise RuntimeError(
            f"only found {len(clean_uids)} clean labelled reports; requested {n}"
        )
    chosen = clean_uids[:n]

    # Choose which of the chosen reports get PII injected.
    inject_pii_k = max(0, min(inject_pii_k, n))
    inject_set = set(rng.sample(chosen, inject_pii_k)) if inject_pii_k else set()

    records: list[dict] = []
    gt_reports: dict[str, dict] = {}
    for uid in chosen:
        row = rows_by_uid[uid]
        report_text = row.get(text_col) or ""
        findings = row.get("findings") or ""
        injected_items: list[dict] = []
        pii_present = False
        if uid in inject_set:
            report_text, injected_items = _inject_pii(report_text, rng)
            pii_present = True
        rec = {
            "study_uid": uid,
            "report": report_text,
            "clinical_information": row.get("clinical_information", ""),
            "technique": row.get("technique", ""),
            "findings": findings,
            "impression": row.get("impression", ""),
        }
        records.append(rec)
        gold_full = gold.get(uid, {})
        gt_reports[uid] = {
            "pii_present": pii_present,
            "injected_items": injected_items,
            "gold_labels_full": gold_full,
            "gold_labels_vocab": {name: int(gold_full.get(name, 0)) for name in vocab},
        }

    csv_path = out_dir / "evaluation_dataset.csv"
    fieldnames = ["study_uid", "report", "clinical_information", "technique", "findings", "impression"]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            writer.writerow(rec)

    ground_truth = {
        "seed": seed,
        "n": n,
        "inject_pii_k": inject_pii_k,
        "id_col": id_col,
        "text_col": text_col,
        "vocab": vocab,
        "label_names_full": label_names,
        "reports": gt_reports,
        "source_reports_dir": str(paths.DATA_REPORTS_DIR),
        "source_labels_csv": str(paths.LABELS_CSV),
    }
    gt_path = out_dir / "ground_truth.json"
    with gt_path.open("w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2, ensure_ascii=False)

    return Dataset(
        out_dir=out_dir,
        csv_path=csv_path,
        gt_path=gt_path,
        seed=seed,
        text_col=text_col,
        id_col=id_col,
        records=records,
        ground_truth=ground_truth,
        vocab=vocab,
    )


def load_dataset(out_dir: Path) -> Dataset:
    """Reload a previously built dataset from ``out_dir``."""
    out_dir = Path(out_dir)
    csv_path = out_dir / "evaluation_dataset.csv"
    gt_path = out_dir / "ground_truth.json"
    with gt_path.open(encoding="utf-8") as f:
        ground_truth = json.load(f)
    records: list[dict] = []
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            records.append(dict(row))
    return Dataset(
        out_dir=out_dir,
        csv_path=csv_path,
        gt_path=gt_path,
        seed=ground_truth.get("seed", 0),
        text_col=ground_truth.get("text_col", "report"),
        id_col=ground_truth.get("id_col", "study_uid"),
        records=records,
        ground_truth=ground_truth,
        vocab=ground_truth.get("vocab", []),
    )
