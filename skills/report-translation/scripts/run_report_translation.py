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

"""Report-translation skill wrapper (MR-RATE reports_preprocessing step 02 + 03 QC).

Two execution paths, same output contract:

* ``--mode mock`` (default): a deterministic, GPU-free, stdlib-only translator.
  It rewrites a small synthetic Turkish->English medical phrase dictionary,
  preserves every ``[token_N]`` anonymization placeholder verbatim, then
  rule-based-grades the result: language detection (no residual Turkish) and
  translation QC (fully English + tokens preserved). Used for fixtures, CI
  gates, and offline verification. NOT a clinical translator.
* ``--mode live``: subprocesses the upstream
  ``02_translation/translate_reports_parallel.py`` (vLLM) to translate, then
  ``03_translation_qc/detect_turkish_parallel.py`` and
  ``03_translation_qc/quality_check_parallel.py`` to grade, and parses their
  ``*_rank_*.csv`` output.

Both paths emit the same JSON summary on stdout matching the contract audited by
``medagent.verifiers.report_translation_quality_v1``: qc (pass rate), language
(residual non-English rate), and token_preservation (placeholders survive).

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

SKILL_NAME = "report-translation"

# Anonymization placeholder, e.g. [token_1], [patient_3], [hospital_e2].
TOKEN_RE = re.compile(r"\[[a-z][a-z_]*_[a-z0-9]+\]")

# ---------------------------------------------------------------------------
# Mock Turkish->English medical phrase dictionary (deterministic, stdlib only)
# ---------------------------------------------------------------------------
# These are the ONLY Turkish phrases present in the committed synthetic fixture,
# so the mock translates the fixture exactly to English with zero residual
# Turkish. Real translation is the job of --mode live (the LLM). Longest phrases
# are applied first so multi-word terms are not partially matched.
MOCK_PHRASES: dict[str, str] = {
    "Beyin MRG incelemesi": "Brain MRI examination",
    "Kraniyal MRG incelemesi": "Cranial MRI examination",
    "kontrastsiz": "non-contrast",
    "kontrastli": "contrast-enhanced",
    "Bulgular": "Findings",
    "Sonuc": "Impression",
    "Teknik": "Technique",
    "Klinik bilgi": "Clinical information",
    "beyaz cevherde": "in the white matter",
    "beyaz cevher": "white matter",
    "gri cevher": "gray matter",
    "lateral ventrikuller": "lateral ventricles",
    "lateral ventrikul": "lateral ventricle",
    "ventrikuler sistem": "ventricular system",
    "beyin sapi": "brainstem",
    "serebellar hemisfer": "cerebellar hemisphere",
    "korpus kallozum": "corpus callosum",
    "hipofiz bezi": "pituitary gland",
    "orta hat yapilari": "midline structures",
    "paranazal sinusler": "paranasal sinuses",
    "patolojik sinyal degisikligi": "pathological signal change",
    "sinyal degisiklikleri": "signal changes",
    "gliotik": "gliotic",
    "iskemik": "ischemic",
    "kronik enfarkt": "chronic infarct",
    "araknoid kist": "arachnoid cyst",
    "ile uyumlu": "consistent with",
    "lezyon": "lesion",
    "normal konumda": "in normal position",
    "normal genislikte": "of normal width",
    "normal boyutlarda": "of normal size",
    "saptanmadi": "was not detected",
    "izlendi": "was observed",
    "izlenmemistir": "was not observed",
    "mevcuttur": "is present",
    "havali": "aerated",
    "boyutunda": "in size",
    "milimetrik": "millimetric",
    "sag": "right",
    "sol": "left",
    "bilateral": "bilateral",
    "frontal lobda": "in the frontal lobe",
    "Tarih": "Date",
    "yasinda": "years old",
    "kadin": "female",
    "erkek": "male",
    "hasta": "patient",
    "ve": "and",
    "yok": "absent",
    "mm": "mm",
}


# Single-pass alternation over all source phrases, longest-first and anchored at
# word boundaries, so a short Turkish word (e.g. "ve") is matched only as a
# standalone token and never inside an English word the replacement produced
# ("observed", "ventricle"). Built once at import.
def _build_phrase_re() -> re.Pattern:
    keys = sorted(MOCK_PHRASES, key=len, reverse=True)
    alt = "|".join(re.escape(k) for k in keys)
    # \b boundaries keep substitutions on whole-word phrases; one pass over the
    # source means already-translated English is never re-scanned.
    return re.compile(r"\b(?:" + alt + r")\b")


MOCK_PHRASE_RE = _build_phrase_re()

# Turkish-specific letters and a small set of grammatical-suffix / stopword
# markers used by the rule-based language detector. If any of these survive in
# the translated text, the report is flagged as non-English.
TURKISH_CHARS = set("çğıöşüÇĞİÖŞÜ")
TURKISH_MARKERS = [
    "mistir",
    "mektedir",
    "miştir",
    "tedir",
    "dir ",
    "tir ",
    " bir ",
    " ile ",
    " icin ",
    " olan ",
    " ancak ",
]


def log(msg: str) -> None:
    print(f"[report-translation] {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Mock translator (deterministic)
# ---------------------------------------------------------------------------
def mock_translate(text: str) -> str:
    """Rewrite the synthetic Turkish phrase set to English, preserving tokens.

    Anonymization placeholders are masked out before phrase substitution so a
    token is never altered, then restored verbatim. Longer phrases are applied
    before shorter ones so multi-word medical terms win over their substrings.
    """
    # Mask tokens so phrase substitution can never touch them.
    saved: list[str] = []

    def _mask(m: re.Match) -> str:
        saved.append(m.group(0))
        return f"\x00{len(saved) - 1}\x00"

    masked = TOKEN_RE.sub(_mask, text)

    # Single left-to-right pass: each match is replaced once and the resulting
    # English is never re-scanned, so short keys cannot corrupt longer output.
    out = MOCK_PHRASE_RE.sub(lambda m: MOCK_PHRASES[m.group(0)], masked)

    # Restore tokens verbatim.
    def _unmask(m: re.Match) -> str:
        return saved[int(m.group(1))]

    out = re.sub(r"\x00(\d+)\x00", _unmask, out)
    return out


# ---------------------------------------------------------------------------
# Rule-based graders (mock language detection + QC)
# ---------------------------------------------------------------------------
def detect_language_rule_based(text: str) -> str:
    """Return 'english', 'turkish', or 'unknown' for a translated report.

    Deterministic stand-in for the upstream LLM detector: Turkish-specific
    characters or grammatical-suffix markers => 'turkish'; otherwise 'english'.
    Anonymization tokens are ignored (they are language-neutral).
    """
    stripped = TOKEN_RE.sub(" ", text)
    if not stripped.strip():
        return "unknown"
    if any(ch in TURKISH_CHARS for ch in stripped):
        return "turkish"
    low = " " + stripped.lower() + " "
    if any(marker in low for marker in TURKISH_MARKERS):
        return "turkish"
    return "english"


def qc_verdict_rule_based(source_tokens: set[str], translated: str, language: str) -> str:
    """Return 'PASS', 'FAIL', or 'unknown' for one translation.

    Rule-based stand-in for the upstream LLM QC judge: a translation PASSES when
    it is fully English and every source anonymization token survived; it FAILS
    when residual non-English is detected or any token was dropped.
    """
    if not translated.strip():
        return "unknown"
    out_tokens = set(TOKEN_RE.findall(translated))
    if language != "english":
        return "FAIL"
    if source_tokens - out_tokens:
        return "FAIL"
    return "PASS"


# ---------------------------------------------------------------------------
# Shared metrics + summary (mock + live)
# ---------------------------------------------------------------------------
def summarize(
    records: list[dict], qc_method: str, lang_method: str, model: str, elapsed: float
) -> dict:
    """Build the output contract from per-report records.

    Each record: {uid, source, translated, source_tokens(list), language, qc}.
    """
    n = len(records)

    # Translation QC over decisive + unknown verdicts.
    qc_pass = sum(1 for r in records if r["qc"] == "PASS")
    qc_fail = sum(1 for r in records if r["qc"] == "FAIL")
    qc_unknown = sum(1 for r in records if r["qc"] not in ("PASS", "FAIL"))
    decisive = qc_pass + qc_fail
    pass_rate = (qc_pass / decisive) if decisive else 0.0

    # Residual non-English / Turkish-leftover.
    non_english = sum(1 for r in records if r["language"] != "english")
    non_english_rate = (non_english / n) if n else 0.0

    # Anonymization-token preservation through translation.
    n_with_tokens = sum(1 for r in records if r["source_tokens"])
    n_dropped = 0
    for r in records:
        src = set(r["source_tokens"])
        if not src:
            continue
        out = set(TOKEN_RE.findall(r["translated"]))
        if src - out:
            n_dropped += 1
    preservation_rate = ((n_with_tokens - n_dropped) / n_with_tokens) if n_with_tokens else 1.0

    return {
        "skill": SKILL_NAME,
        "model": model,
        "n_reports": n,
        "qc": {
            "method": qc_method,
            "n_evaluated": n,
            "n_pass": qc_pass,
            "n_fail": qc_fail,
            "n_unknown": qc_unknown,
            "pass_rate": round(pass_rate, 6),
        },
        "language": {
            "method": lang_method,
            "n_evaluated": n,
            "n_non_english": non_english,
            "non_english_rate": round(non_english_rate, 6),
        },
        "token_preservation": {
            "n_reports_with_tokens": n_with_tokens,
            "n_reports_token_dropped": n_dropped,
            "preservation_rate": round(preservation_rate, 6),
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
            rows.append({"uid": row[id_col], "source": row[text_col] or ""})
            if limit and len(rows) >= limit:
                break
    if not rows:
        raise ValueError(f"no rows read from {path}")
    return rows


def write_translated_csv(out_path: Path, records: list[dict]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["UID", "Anonymized_Rapor", "Translated_Rapor", "detected_language", "qc_verdict"]
        )
        for rec in records:
            writer.writerow(
                [
                    rec["uid"],
                    rec["source"],
                    rec["translated"],
                    rec["language"],
                    rec["qc"],
                ]
            )


# ---------------------------------------------------------------------------
# Mock path
# ---------------------------------------------------------------------------
def run_mock(args: argparse.Namespace) -> list[dict]:
    rows = read_reports(args.fixture, args.id_col, args.text_col, args.limit)
    records: list[dict] = []
    for row in rows:
        source = row["source"]
        source_tokens = TOKEN_RE.findall(source)
        translated = mock_translate(source)
        language = detect_language_rule_based(translated)
        qc = qc_verdict_rule_based(set(source_tokens), translated, language)
        records.append(
            {
                "uid": row["uid"],
                "source": source,
                "translated": translated,
                "source_tokens": source_tokens,
                "language": language,
                "qc": qc,
            }
        )
    return records


# ---------------------------------------------------------------------------
# Live mode: locate + run the upstream vLLM scripts (translate -> detect -> QC)
# ---------------------------------------------------------------------------
def locate_upstream(explicit_root: str | None, rel: Path) -> Path:
    """Find an upstream script relative to the reports_preprocessing tree.

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


def _run_upstream(script: Path, extra: list[str], args: argparse.Namespace) -> None:
    cmd = (
        [sys.executable, str(script)]
        + extra
        + [
            "--model",
            args.model,
            "--chunk_size",
            str(args.chunk_size),
        ]
    )
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
    log(f"launching upstream: {script.name} (loads vLLM + the model)...")
    proc = subprocess.run(cmd, env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"upstream {script.name} failed with exit code {proc.returncode}")


def run_live(args: argparse.Namespace, work_dir: Path) -> list[dict]:
    translate = locate_upstream(
        args.mr_rate_root, Path("02_translation") / "translate_reports_parallel.py"
    )
    detect = locate_upstream(
        args.mr_rate_root, Path("03_translation_qc") / "detect_turkish_parallel.py"
    )
    quality = locate_upstream(
        args.mr_rate_root, Path("03_translation_qc") / "quality_check_parallel.py"
    )

    trans_dir = work_dir / "upstream_translated"
    detect_dir = work_dir / "upstream_detect"
    qc_dir = work_dir / "upstream_qc"

    # 1) Translate Turkish -> English.
    _run_upstream(
        translate,
        [
            "--input_file",
            str(args.fixture),
            "--output_dir",
            str(trans_dir),
            "--id_col",
            args.id_col,
            "--text_col",
            args.text_col,
        ],
        args,
    )
    translated_shards = sorted(trans_dir.glob("translated_rank_*.csv"))
    if not translated_shards:
        raise FileNotFoundError(f"no translated_rank_*.csv produced under {trans_dir}")

    # 2) Language detection over the translations.
    _run_upstream(
        detect,
        [
            "--input_dir",
            str(trans_dir),
            "--input_glob",
            "translated_rank_*.csv",
            "--output_dir",
            str(detect_dir),
            "--id_col",
            args.id_col,
            "--english_col",
            "Translated_Rapor",
        ],
        args,
    )

    # 3) LLM QC judge over (Turkish, English) pairs.
    _run_upstream(
        quality,
        [
            "--input_dir",
            str(trans_dir),
            "--input_glob",
            "translated_rank_*.csv",
            "--output_dir",
            str(qc_dir),
            "--id_col",
            args.id_col,
            "--turkish_col",
            args.text_col,
            "--english_col",
            "Translated_Rapor",
        ],
        args,
    )

    return read_upstream_packs(translated_shards, detect_dir, qc_dir, args.id_col, args.text_col)


def _read_csv_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_upstream_packs(
    translated_shards: list[Path], detect_dir: Path, qc_dir: Path, id_col: str, text_col: str
) -> list[dict]:
    # Index detection + QC verdicts by UID.
    lang_by_uid: dict[str, str] = {}
    for shard in sorted(detect_dir.glob("detect_rank_*.csv")):
        for row in _read_csv_rows(shard):
            uid = row.get(id_col) or row.get("UID") or ""
            lang_by_uid[uid] = (row.get("detected_language") or "unknown").lower()
    qc_by_uid: dict[str, str] = {}
    for shard in sorted(qc_dir.glob("qc_rank_*.csv")):
        for row in _read_csv_rows(shard):
            uid = row.get(id_col) or row.get("UID") or ""
            qc_by_uid[uid] = (row.get("verdict") or "unknown").upper()

    records: list[dict] = []
    for shard in translated_shards:
        for row in _read_csv_rows(shard):
            uid = row.get(id_col, "")
            source = row.get(text_col) or row.get("Anonymized_Rapor") or ""
            translated = row.get("Translated_Rapor", "") or ""
            language = lang_by_uid.get(uid, "unknown")
            qc = qc_by_uid.get(uid, "unknown")
            records.append(
                {
                    "uid": uid,
                    "source": source,
                    "translated": translated,
                    "source_tokens": TOKEN_RE.findall(source),
                    "language": language,
                    "qc": qc,
                }
            )
    if not records:
        raise FileNotFoundError("no translated records parsed from upstream output")
    return records


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Translate anonymized Turkish radiology reports to English and QC them "
        "(MR-RATE steps 02 + 03)."
    )
    p.add_argument(
        "fixture", type=Path, help="input CSV of anonymized reports (UID + Anonymized_Rapor)"
    )
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
    p.add_argument("--text-col", type=str, default="Anonymized_Rapor")
    p.add_argument("--chunk-size", type=int, default=1000)
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
        qc_method = "llm_judge"
        lang_method = "llm_detect"
    else:
        model = args.model or "synthetic-mock"
        records = run_mock(args)
        qc_method = "rule_based"
        lang_method = "rule_based"

    write_translated_csv(work_dir / "translated.csv", records)
    elapsed = time.perf_counter() - t0
    summary = summarize(records, qc_method, lang_method, model, elapsed)
    summary["artifacts"] = {"translated_csv": str((work_dir / "translated.csv"))}
    log(
        f"done: {len(records)} reports, qc_pass_rate={summary['qc']['pass_rate']}, "
        f"non_english_rate={summary['language']['non_english_rate']}, "
        f"preservation_rate={summary['token_preservation']['preservation_rate']}"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
