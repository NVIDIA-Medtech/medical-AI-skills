# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""With-vs-without-skill experiment for the report-anonymization skill.

Faithful to the reference protocol
(``docs/with-vs-without-skill-experiment.md``): the two arms differ only in the
documentation the agent may read.

* **With skill**  -- the backend is given ``skills/report-anonymization/SKILL.md``.
* **Without skill** -- the backend is given the vendored upstream NeMo Anonymizer
  README (``tools/curation_eval/upstream_docs/nemo_anonymizer_README.md``).

For each backend x arm x repeat the backend generates ONE bash command from a
symmetric A2-style prompt (embedded-doc / ``minimal`` style, because the chat
backends have no file-reading tool). The command is guarded, executed in a
Python environment where ``nemo-anonymizer`` is installed and ``NVIDIA_API_KEY``
is set, then graded on a deterministic five-tier ladder. The main protocol is
single-shot / no-repair (``max_correction_steps=0``).

Run from the ``medical-AI-skills`` catalog root, e.g.::

    export NVIDIA_API_KEY="nvapi-..."
    python -m tools.curation_eval.anon_experiment \
      --backends mock nemotron120-remote \
      --repeats 1 --limit 100 \
      --input ../../../data/MR-RATE/reports/reports_with_PHI/batch00_reports_w_PHI.csv
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html as _html
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from . import paths, telemetry
from .backends import Backend, make_backend, probe
from .runner import sign_test

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

SKILLS_ROOT = paths.SKILLS_ROOT
SKILL_DOC = SKILLS_ROOT / "skills" / "report-anonymization" / "SKILL.md"
UPSTREAM_DOC = SKILLS_ROOT / "tools" / "curation_eval" / "upstream_docs" / "nemo_anonymizer_README.md"
DEFAULT_REPORT = SKILLS_ROOT / "docs" / "anonymization-with-vs-without-experiment.md"
DEFAULT_INPUT = paths.REPO_ROOT / "data" / "MR-RATE" / "reports" / "reports_with_PHI" / "batch00_reports_w_PHI.csv"

# Python whose `python` should resolve to an env with nemo-anonymizer installed.
# Defaults to the interpreter running the harness (run the harness with an env
# that has nemo-anonymizer, e.g. `data_curration`), overridable for other layouts.
ANON_PYTHON_BIN = os.environ.get("CEVAL_ANON_PYTHON_BIN") or str(Path(sys.executable).parent)


def _rel(p: Path | str) -> str:
    """Repo-relative string when under the catalog root, else the absolute path."""
    p = Path(p)
    try:
        return str(p.resolve().relative_to(SKILLS_ROOT.resolve()))
    except ValueError:
        return str(p)

# Destructive shell fragments blocked by the safety guard (identical for both arms).
_GUARD_PATTERNS = [
    r"\brm\s+-", r"\bsudo\b", r"\bapt(-get)?\b", r"\bdocker\b", r"\bcurl\b",
    r"\bwget\b", r"\bmkfs\b", r"\bshutdown\b", r"\breboot\b", r">\s*/dev/",
    r":\(\)\s*\{", r"\bchmod\s+-R\b", r"\bchown\s+-R\b",
]
_FENCE_RE = re.compile(r"```(?:bash|sh|shell)?\s*\n(.*?)```", re.DOTALL)
_TEXT_COL = "report_w_PHI"
_ID_COL = "study_uid"

TIER_LADDER = {
    1: "A runnable NeMo Anonymizer entrypoint is present.",
    2: "The command references the neutral staged input path.",
    3: "The command targets the correct report text column (report_w_PHI) / wrapper.",
    4: "The command writes to the expected arm output directory.",
    5: "The command executes cleanly and produces an anonymized CSV that transformed the reports.",
}


# --------------------------------------------------------------------------- #
# Data staging
# --------------------------------------------------------------------------- #
def stage_input(input_csv: Path, staged: Path, limit: int) -> int:
    """Copy the first ``limit`` rows (0 = all) to a neutral staged path."""
    staged.parent.mkdir(parents=True, exist_ok=True)
    with input_csv.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = reader.fieldnames or [_ID_COL, _TEXT_COL]
    if limit and limit > 0:
        rows = rows[:limit]
    with staged.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Prompt construction (symmetric A2-style, embedded-doc / minimal)
# --------------------------------------------------------------------------- #
_SYSTEM = (
    "You are a careful assistant that turns a data-engineering task plus one "
    "reference document into exactly one runnable shell command. You output a "
    "single fenced bash code block and nothing else executable."
)


def build_prompt(arm: str, doc_path: Path | None, input_rel: str, out_rel: str, n: int) -> tuple[str, dict]:
    if arm == "unaided" or doc_path is None:
        # No skill, no upstream doc: a plain natural-language user request. The
        # agent must produce a working approach from general knowledge alone.
        task = (
            "You are helping a medical-imaging engineer at the root of a data repository. "
            f"Redact the CSV of radiology reports at the repo-relative path {input_rel} "
            f"(columns {_ID_COL}, {_TEXT_COL}): replace ALL PHI — patient and doctor names, "
            "MRNs, dates, ages, sex, accession numbers, phone numbers, and institution names "
            "— with placeholder labels like [PATIENT], [DATE], [DOCTOR], [MRN], "
            "[INSTITUTION], leaving the clinical findings intact. Write the anonymized CSV "
            f"under {out_rel}. Tier-5 execution runs in a standard Python environment with "
            "common packages available and NVIDIA_API_KEY set. Produce a SINGLE shell command "
            "(or &&-chained sequence) inside one fenced bash code block that does this, "
            "followed by a one-line explanation. Do not run it yourself."
        )
        meta = {"doc_path": None, "doc_bytes": 0, "doc_sha256": "", "prompt_sha256": _sha256(task)}
        return task, meta

    doc_text = doc_path.read_text(encoding="utf-8")
    doc_rel = _rel(doc_path)
    if arm == "with":
        forbidden = "Do not inspect any other files under skills/report-anonymization/."
    else:
        forbidden = "Do not read or use any files under skills/report-anonymization/."
    task = (
        "You are helping a medical-imaging engineer who has cloned "
        "https://github.com/NVIDIA-Medtech/medical-AI-skills and is running commands "
        "from the repository root. "
        f"The input CSV of {n} English radiology reports containing PHI is at the "
        f"repo-relative path {input_rel} (columns: {_ID_COL}, {_TEXT_COL}). De-identify "
        "every report by replacing the detected PHI, and write the anonymized output "
        f"under {out_rel}. Tier-5 execution runs in a Python environment where "
        "nemo-anonymizer is already installed and NVIDIA_API_KEY is already set, so do "
        "NOT include pip install or key-export steps, and use repo-relative paths only. "
        f"The only workflow document available to you is {doc_rel}. "
        f"Read it below. {forbidden} "
        "Then produce a SINGLE shell command (or &&-chained sequence) inside one fenced "
        f"bash code block that anonymizes all {n} reports and writes the result under "
        f"{out_rel}. Follow the bash block with a one-line explanation. Do not run it yourself."
    )
    user = f"{task}\n\n===== DOCUMENT: {doc_rel} =====\n{doc_text}\n===== END DOCUMENT ====="
    meta = {
        "doc_path": doc_rel,
        "doc_bytes": len(doc_text.encode("utf-8")),
        "doc_sha256": _sha256(doc_text),
        "prompt_sha256": _sha256(user),
    }
    return user, meta


_CMD_START_RE = re.compile(r"^\s*(mkdir|python|anonymizer|uv|export|cd|bash)\b")


def _recover_command(text: str) -> str | None:
    """Tolerant fallback: recover an unfenced command (e.g. Nemotron output).

    Takes lines from the first command-looking line until a prose explanation
    line. Diagnostic only; the primary path is a fenced block.
    """
    lines = text.strip().splitlines()
    start = next((i for i, ln in enumerate(lines) if _CMD_START_RE.match(ln)), None)
    if start is None:
        return None
    cmd_lines: list[str] = []
    for ln in lines[start:]:
        s = ln.strip()
        cont = bool(cmd_lines) and cmd_lines[-1].rstrip().endswith("\\")
        shellish = bool(
            _CMD_START_RE.match(ln) or s.startswith("--") or "&&" in s
            or s.startswith("|") or "/" in s or s.endswith("\\") or not s
        )
        if cmd_lines and not cont and not shellish:
            break
        cmd_lines.append(ln)
    return "\n".join(cmd_lines).strip() or None


def extract_command(text: str) -> tuple[str | None, str]:
    """Return (command, method) where method is 'fenced', 'recovered', or 'none'."""
    if not text:
        return None, "none"
    if "</think>" in text:
        text = text.split("</think>")[-1]
    m = _FENCE_RE.search(text)
    if m:
        return m.group(1).strip(), "fenced"
    rec = _recover_command(text)
    if rec:
        return rec, "recovered"
    return None, "none"


def guard_reason(command: str) -> str | None:
    for pat in _GUARD_PATTERNS:
        if re.search(pat, command):
            return f"blocked by safety guard: matched /{pat}/"
    return None


# --------------------------------------------------------------------------- #
# Execution + grading
# --------------------------------------------------------------------------- #
@dataclass
class AttemptResult:
    backend: str
    arm: str
    repeat: int
    command: str | None = None
    extraction: str = "none"
    raw_response: str = ""
    guard_blocked: bool = False
    guard_reason: str | None = None
    exec_rc: int | None = None
    exec_seconds: float = 0.0
    stdout_tail: str = ""
    stderr_tail: str = ""
    output_csv: str | None = None
    n_out_rows: int = 0
    n_transformed: int = 0
    in_phi_total: int = 0
    out_phi_total: int = 0
    rows_clean: int = 0
    rows_scored: int = 0
    phi_by_type: dict = field(default_factory=dict)
    row_phi: list = field(default_factory=list)
    judge_model: str = ""
    judge_out_phi_total: int = 0
    judge_rows_clean: int = 0
    judge_rows_scored: int = 0
    judge_row_phi: list = field(default_factory=list)
    judge_usage: dict = field(default_factory=dict)
    tier: int = 0
    completed: bool = False
    passed: bool = False
    failed_tiers: list = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    doc_meta: dict = field(default_factory=dict)


def _pick_output_csv(candidates: list[Path], staged_input: Path) -> Path | None:
    candidates = [p for p in candidates if p.resolve() != staged_input.resolve()]
    if not candidates:
        return None
    # Prefer a file whose name signals anonymized output; else newest.
    for pref in ("anonymized", "result", "output", "redact"):
        for p in candidates:
            if pref in p.name.lower():
                return p
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _find_output_csv(out_dir: Path, staged_input: Path) -> Path | None:
    # 1) Expected location: any CSV inside the per-repeat output dir (.../arm/repN/).
    hit = _pick_output_csv(list(out_dir.rglob("*.csv")), staged_input)
    if hit is not None:
        return hit
    # 2) Fallback: a rep-named sibling CSV in the arm dir (e.g. .../arm/repN.csv), for
    #    agents that ran `--output <arm>/repN.csv` instead of writing into <arm>/repN/.
    #    Scoped to this repeat's name so it never picks up another attempt's output.
    rep = out_dir.name
    parent = out_dir.parent
    if parent.is_dir():
        sibs = [p for p in parent.glob(f"*{rep}*.csv") if p.parent == parent]
        return _pick_output_csv(sibs, staged_input)
    return None


def _load_reports(path: Path, text_hint: str | None = None) -> tuple[list[str], dict[str, str]]:
    """Return (ordered_texts, uid->text). Detects the anonymized text column."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        cols = reader.fieldnames or []
    if not rows:
        return [], {}
    if text_hint and text_hint in cols:
        text_col = text_hint
    else:
        for cand in ("report", f"{_TEXT_COL}_replaced", "anonymized_report", "Anonymized_Rapor"):
            if cand in cols:
                text_col = cand
                break
        else:
            others = [c for c in cols if c not in (_ID_COL, _TEXT_COL)]
            text_col = others[0] if others else (_TEXT_COL if _TEXT_COL in cols else cols[-1])
    texts = [str(r.get(text_col, "")) for r in rows]
    by_uid = {str(r.get(_ID_COL, i)): str(r.get(text_col, "")) for i, r in enumerate(rows)}
    return texts, by_uid


# Residual-PHI escape signals scanned in anonymized text AFTER stripping
# [PLACEHOLDER] tokens. These are unambiguous identifiers in radiology reports
# (clinical findings rarely contain dates, long IDs, or "Dr. Name"). Conservative
# by design: middle initials and bare org names are not counted, so escape counts
# under-report rather than over-report.
_ESCAPE_PATTERNS = [
    (re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"), "date_numeric"),
    (re.compile(r"\b\d{4}-\d{1,2}-\d{1,2}\b"), "date_iso"),
    (re.compile(r"\b(?:January|February|March|April|May|June|July|August|September|"
                r"October|November|December)\s+\d{1,2},?\s+\d{4}\b"), "date_prose"),
    (re.compile(r"\b\d{5,}\b"), "long_id"),
    (re.compile(r"\b(?:Dr|Prof|Mr|Mrs|Ms)\.?\s+[A-Z][a-z]{2,}"), "titled_name"),
    (re.compile(r"\b\d{3}[-.)]\s?\d{3}[-.]\d{4}\b"), "phone"),
]


def score_residual_phi(text: str) -> tuple[int, dict[str, int], list[str]]:
    """Count residual PHI signals in text, ignoring [PLACEHOLDER] tokens."""
    stripped = re.sub(r"\[[^\]]*\]", " ", text or "")
    total = 0
    by_type: dict[str, int] = {}
    examples: list[str] = []
    for rx, name in _ESCAPE_PATTERNS:
        for m in rx.finditer(stripped):
            total += 1
            by_type[name] = by_type.get(name, 0) + 1
            if len(examples) < 6:
                examples.append(m.group(0).strip())
    return total, by_type, examples


def _ordered_uids(path: Path) -> list[str]:
    try:
        with Path(path).open(encoding="utf-8-sig", newline="") as f:
            return [str(r.get(_ID_COL, i)) for i, r in enumerate(csv.DictReader(f))]
    except OSError:
        return []


# --------------------------------------------------------------------------- #
# LLM-as-judge residual-PHI grader
# --------------------------------------------------------------------------- #
_JUDGE_SYSTEM = (
    "You are a strict PHI auditor for ANONYMIZED radiology reports. In the text you "
    "receive, PHI should already be replaced by placeholder tokens in square brackets "
    "(e.g. [PATIENT], [DATE], [DOCTOR], [REDACTED_FIRST_NAME]). Find only PHI that "
    "ESCAPED redaction: real identifying values still present as plain text instead of "
    "a [bracketed] placeholder. Count as escaped PHI: patient or doctor names and name "
    "fragments (including a middle initial left next to a redacted name), dates in any "
    "format, ages, sex, medical record numbers, accession numbers, phone numbers, "
    "addresses, and institution/hospital names. Do NOT count anything inside square "
    "brackets. Do NOT count clinical findings, anatomy, measurements, modality, or "
    "technique terms. Respond with STRICT JSON only: "
    '{"escapes": [{"type": "<kind>", "value": "<exact text>"}], "n_escapes": <int>}. '
    'If nothing escaped, return {"escapes": [], "n_escapes": 0}.'
)


def _parse_json_obj(text: str) -> dict | None:
    if not text:
        return None
    if "</think>" in text:
        text = text.split("</think>")[-1]
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        text = m.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        obj = json.loads(text[start : end + 1])
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def llm_judge_escapes(backend: Backend, text: str) -> tuple[int | None, list, dict]:
    """Ask the judge backend to count residual PHI escapes in one anonymized report.

    Returns (n_escapes | None if unscored, example list, usage).
    """
    r = backend.chat(_JUDGE_SYSTEM, f"<anonymized_report>\n{text}\n</anonymized_report>")
    usage = r.usage or {}
    if not r.ok:
        return None, [], usage
    obj = _parse_json_obj(r.text)
    if not isinstance(obj, dict):
        return None, [], usage
    escapes = obj.get("escapes") if isinstance(obj.get("escapes"), list) else []
    n = obj.get("n_escapes")
    if not isinstance(n, int):
        n = len(escapes)
    return n, escapes[:8], usage


def judge_attempt(att: AttemptResult, judge: Backend, staged_abs: Path) -> None:
    """Score an attempt's anonymized output row-by-row with the LLM judge."""
    if not att.output_csv:
        return
    out_abs = Path(att.output_csv)
    if not out_abs.is_absolute():
        out_abs = SKILLS_ROOT / att.output_csv
    if not out_abs.exists():
        return
    out_texts, _ = _load_reports(out_abs)
    uids = _ordered_uids(staged_abs)
    jrows: list[dict] = []
    j_total = j_clean = j_scored = 0
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "reasoning_tokens": 0,
             "total_tokens": 0, "n_calls": 0, "estimated": False}
    for i, text in enumerate(out_texts):
        n, examples, u = llm_judge_escapes(judge, text)
        _add_usage(usage, u)
        if n is None:
            jrows.append({"uid": uids[i] if i < len(uids) else str(i), "n": -1, "examples": []})
            continue
        j_scored += 1
        j_total += n
        j_clean += 1 if n == 0 else 0
        jrows.append({"uid": uids[i] if i < len(uids) else str(i), "n": n, "examples": examples})
        telemetry.call_tick("judge", att.backend + "/" + att.arm, i + 1, len(out_texts),
                            True, u.get("latency_s", 0.0) if isinstance(u, dict) else 0.0,
                            (u or {}).get("total_tokens", 0))
    att.judge_model = judge.model
    att.judge_out_phi_total = j_total
    att.judge_rows_clean = j_clean
    att.judge_rows_scored = j_scored
    att.judge_row_phi = jrows
    att.judge_usage = usage


def grade(att: AttemptResult, out_rel: Path, out_abs: Path, staged_rel: Path,
          staged_abs: Path, n_expected: int) -> None:
    cmd = att.command or ""
    low = cmd.lower()
    failed: list[str] = []

    nemo_entry = bool(
        "anonymize_reports.py" in cmd
        or re.search(r"\banonymizer\s+(run|preview|validate)\b", low)
        or "-m anonymizer" in low
        or "from anonymizer" in low
        or "import anonymizer" in low
        or "anonymizer.run(" in low
        or "anonymizer.preview(" in low
    )
    if att.arm == "unaided":
        # No doc: any runnable Python approach counts as a real entrypoint.
        generic_py = bool(re.search(r"\bpython[0-9.]*\b", low)
                          and (".py" in low or " -c" in low or "<<" in cmd or "-m " in low))
        t1 = nemo_entry or generic_py
    else:
        t1 = nemo_entry
    t2 = str(staged_rel) in cmd or staged_rel.name in cmd
    t3 = _TEXT_COL.lower() in low or "anonymize_reports.py" in cmd
    t4 = str(out_rel) in cmd or out_rel.name in cmd

    tier = 0
    for ok, label in ((t1, 1), (t2, 2), (t3, 3), (t4, 4)):
        if ok and tier == label - 1:
            tier = label
        elif not ok:
            failed.append(f"tier{label}:{TIER_LADDER[label]}")

    # Tier 5 requires the four command tiers AND a clean, transforming execution.
    t5 = False
    if tier == 4 and att.exec_rc == 0:
        out_csv = _find_output_csv(out_abs, staged_abs)
        if out_csv is not None:
            att.output_csv = _rel(out_csv)
            out_texts, _ = _load_reports(out_csv)
            in_texts, _ = _load_reports(staged_abs, text_hint=_TEXT_COL)
            att.n_out_rows = len(out_texts)
            # Positional compare (row i vs row i). Robust when the output drops the
            # study_uid passthrough column, which upstream `anonymizer run` does.
            comparable = min(len(out_texts), len(in_texts))
            transformed = sum(
                1 for i in range(comparable)
                if out_texts[i].strip() and out_texts[i].strip() != in_texts[i].strip()
            )
            att.n_transformed = transformed

            # Row-level residual-PHI escape scoring (positional; robust to a
            # dropped study_uid passthrough column).
            uids = _ordered_uids(staged_abs)
            row_phi: list[dict] = []
            in_tot = out_tot = clean = 0
            by_type: dict[str, int] = {}
            for i in range(comparable):
                ic, _, _ = score_residual_phi(in_texts[i])
                oc, obt, oex = score_residual_phi(out_texts[i])
                in_tot += ic
                out_tot += oc
                for k, v in obt.items():
                    by_type[k] = by_type.get(k, 0) + v
                is_clean = oc == 0
                clean += 1 if is_clean else 0
                row_phi.append({"uid": uids[i] if i < len(uids) else str(i),
                                "in_phi": ic, "out_phi": oc, "clean": is_clean,
                                "examples": oex})
            att.in_phi_total = in_tot
            att.out_phi_total = out_tot
            att.rows_clean = clean
            att.rows_scored = comparable
            att.phi_by_type = by_type
            att.row_phi = row_phi

            enough_rows = att.n_out_rows >= max(1, min(n_expected, len(in_texts)))
            majority_transformed = transformed >= max(1, int(0.8 * comparable))
            if enough_rows and majority_transformed:
                t5 = True
    if tier == 4 and not t5:
        failed.append(f"tier5:{TIER_LADDER[5]}")
    if t5:
        tier = 5
    att.tier = tier
    att.completed = tier >= 5
    att.passed = tier >= 5  # provisional; overridden by the 0-escape judge criterion when judged
    att.failed_tiers = failed


def run_command(command: str, out_dir: Path, timeout: float) -> tuple[int, str, str, float]:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PATH"] = f"{ANON_PYTHON_BIN}:{env.get('PATH', '')}"
    env.setdefault("NEMO_TELEMETRY_ENABLED", "false")
    # NB: do NOT set PYTHONNOUSERSITE here. The shared tier-5 env resolves some
    # transitive deps (e.g. dateutil for pandas) from the user site-packages;
    # blanking user-site breaks `import pandas` for both arms symmetrically.
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            ["bash", "-c", command], cwd=str(SKILLS_ROOT), env=env,
            capture_output=True, text=True, timeout=timeout,
        )
        elapsed = time.perf_counter() - t0
        return proc.returncode, proc.stdout, proc.stderr, elapsed
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s", time.perf_counter() - t0


def run_attempt(backend: Backend, arm: str, repeat: int, doc_path: Path,
                staged_rel: Path, staged_abs: Path, out_rel: Path, out_abs: Path,
                n: int, timeout: float, execute: bool) -> AttemptResult:
    att = AttemptResult(backend=backend.name, arm=arm, repeat=repeat)
    user, meta = build_prompt(arm, doc_path, str(staged_rel), str(out_rel), n)
    att.doc_meta = meta
    telemetry.log(f"  [{backend.name}/{arm}#{repeat}] generating command...")
    r = backend.chat(_SYSTEM, user)
    att.raw_response = r.text or ""
    att.usage = r.usage or {}
    if not r.ok:
        att.stderr_tail = f"backend error: {r.error}"
        att.failed_tiers = [f"tier{t}:{TIER_LADDER[t]}" for t in range(1, 6)]
        return att
    att.command, att.extraction = extract_command(r.text)
    if not att.command:
        att.failed_tiers = [f"tier{t}:{TIER_LADDER[t]}" for t in range(1, 6)]
        att.stderr_tail = "no bash command in response"
        return att
    gr = guard_reason(att.command)
    if gr:
        att.guard_blocked = True
        att.guard_reason = gr
    if execute and not att.guard_blocked:
        telemetry.log(f"  [{backend.name}/{arm}#{repeat}] executing command (timeout {timeout:.0f}s)...")
        rc, so, se, secs = run_command(att.command, out_abs, timeout)
        att.exec_rc = rc
        att.exec_seconds = secs
        att.stdout_tail = (so or "")[-800:]
        att.stderr_tail = (se or "")[-800:]
        telemetry.log(f"  [{backend.name}/{arm}#{repeat}] exit={rc} {secs:.1f}s")
    grade(att, out_rel, out_abs, staged_rel, staged_abs, n)
    return att


# --------------------------------------------------------------------------- #
# Study orchestration
# --------------------------------------------------------------------------- #
def _usage_acc() -> dict:
    return {"prompt_tokens": 0, "completion_tokens": 0, "reasoning_tokens": 0,
            "total_tokens": 0, "n_calls": 0, "estimated": False}


def _add_usage(acc: dict, u: dict) -> None:
    for k in ("prompt_tokens", "completion_tokens", "reasoning_tokens", "total_tokens"):
        acc[k] += int(u.get(k, 0) or 0)
    acc["n_calls"] += 1
    if u.get("estimated"):
        acc["estimated"] = True


DOC_FOR_ARM = {"with": SKILL_DOC, "without": UPSTREAM_DOC, "unaided": None}


def run_study(backend_specs: list[str], arms: tuple[str, ...], repeats: int,
              staged_input: Path, n: int, study_out: Path, timeout: float,
              execute: bool) -> tuple[list[AttemptResult], list[dict]]:
    attempts: list[AttemptResult] = []
    reachability: list[dict] = []

    backends: list[Backend] = []
    for spec in backend_specs:
        b = make_backend(spec)
        backends.append(b)
        ping = probe(b)
        reachability.append({"backend": b.name, "kind": b.kind, "model": b.model,
                             "reachable": ping.ok, "ping_s": round(ping.latency_s, 3),
                             "error": ping.error})
        telemetry.log(f"backend {b.name} ({b.model}) reachable={ping.ok} {ping.latency_s:.2f}s")

    staged_abs = staged_input.resolve()
    staged_rel = Path(_rel(staged_input))
    for b in backends:
        for arm in arms:
            for rep in range(1, repeats + 1):
                out_abs = study_out / b.name / arm / f"rep{rep}"
                out_rel = Path(_rel(out_abs))
                att = run_attempt(b, arm, rep, DOC_FOR_ARM.get(arm), staged_rel, staged_abs,
                                  out_rel, out_abs, n, timeout, execute)
                attempts.append(att)
                out_abs.mkdir(parents=True, exist_ok=True)
                (out_abs / "attempt.json").write_text(json.dumps(asdict(att), indent=2), encoding="utf-8")

    return attempts, reachability


def _row_escape_map(attempt: AttemptResult | dict) -> dict[str, int]:
    """Map study_uid -> residual PHI escape count for scored report rows."""
    rows = attempt.judge_row_phi if isinstance(attempt, AttemptResult) else attempt.get("judge_row_phi", [])
    out: dict[str, int] = {}
    for row in rows or []:
        n = int(row.get("n", -1))
        if n >= 0:
            out[str(row["uid"])] = n
    return out


def compute_paired_row(attempts: list[AttemptResult | dict]) -> dict:
    """Paired with-vs-without sign-test inputs at report-row granularity."""
    def _get(a, key):
        return getattr(a, key) if isinstance(a, AttemptResult) else a[key]

    paired: dict[str, dict] = {}
    overall_wins = overall_losses = overall_ties = 0
    backends = sorted({_get(a, "backend") for a in attempts})
    for backend in backends:
        wa = {_get(a, "repeat"): a for a in attempts if _get(a, "backend") == backend and _get(a, "arm") == "with"}
        wo = {_get(a, "repeat"): a for a in attempts if _get(a, "backend") == backend and _get(a, "arm") == "without"}
        wins = losses = ties = 0
        for rep in sorted(set(wa) & set(wo)):
            with_map = _row_escape_map(wa[rep])
            without_map = _row_escape_map(wo[rep])
            for uid in sorted(set(with_map) & set(without_map)):
                nw, no = with_map[uid], without_map[uid]
                if nw < no:
                    wins += 1
                elif no < nw:
                    losses += 1
                else:
                    ties += 1
        overall_wins += wins
        overall_losses += losses
        overall_ties += ties
        paired[backend] = {
            "pairs": wins + losses + ties,
            "skill_wins": wins,
            "without_wins": losses,
            "ties": ties,
            "sign_test_p": round(sign_test(wins, losses), 6),
        }
    paired["__overall__"] = {
        "pairs": overall_wins + overall_losses + overall_ties,
        "skill_wins": overall_wins,
        "without_wins": overall_losses,
        "ties": overall_ties,
        "sign_test_p": round(sign_test(overall_wins, overall_losses), 6),
    }
    return paired


def compute_per_cell(attempts: list[AttemptResult | dict]) -> dict[str, dict]:
    """Per backend/arm stats: report-row redaction passes and mean attempt tier."""
    def _get(a, key):
        return getattr(a, key) if isinstance(a, AttemptResult) else a[key]

    by_ba: dict[tuple[str, str], list] = {}
    for a in attempts:
        by_ba.setdefault((_get(a, "backend"), _get(a, "arm")), []).append(a)

    per_cell: dict[str, dict] = {}
    for (backend, arm), atts in sorted(by_ba.items()):
        row_passes = sum(_get(a, "judge_rows_clean") or 0 for a in atts)
        row_total = sum(_get(a, "judge_rows_scored") or 0 for a in atts)
        attempt_passes = sum(1 for a in atts if _get(a, "passed"))
        per_cell[f"{backend}/{arm}"] = {
            "row_passes": row_passes,
            "row_total": row_total,
            "attempt_passes": attempt_passes,
            "attempt_total": len(atts),
            "passes": attempt_passes,
            "repeats": len(atts),
            "tiers": [_get(a, "tier") for a in atts],
            "mean_tier": round(sum(_get(a, "tier") for a in atts) / len(atts), 2) if atts else 0,
        }
    return per_cell


def aggregate(attempts: list[AttemptResult], reachability: list[dict],
              backend_specs: list[str], repeats: int, n: int, staged_input: Path,
              timeout: float, execute: bool) -> dict:
    per_cell = compute_per_cell(attempts)
    paired = compute_paired_row(attempts)

    token_rows = []
    by_ba: dict[tuple[str, str], list[AttemptResult]] = {}
    for a in attempts:
        by_ba.setdefault((a.backend, a.arm), []).append(a)
    for (backend, arm), atts in sorted(by_ba.items()):
        usage = _usage_acc()
        exec_secs = []
        for a in atts:
            if a.usage:
                _add_usage(usage, a.usage)
            if a.exec_rc is not None:
                exec_secs.append(a.exec_seconds)
        cell = per_cell[f"{backend}/{arm}"]
        token_rows.append({
            "backend": backend, "arm": arm, "repeats": len(atts),
            "passes": cell["attempt_passes"],
            "row_passes": cell["row_passes"], "row_total": cell["row_total"],
            "llm_calls": usage["n_calls"], "prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            "reasoning_tokens": usage["reasoning_tokens"],
            "total_tokens": usage["total_tokens"], "estimated": usage["estimated"],
            "mean_exec_s": round(sum(exec_secs) / len(exec_secs), 3) if exec_secs else 0.0,
        })

    with_atts = [a for a in attempts if a.arm == "with"]
    without_atts = [a for a in attempts if a.arm == "without"]
    unaided_atts = [a for a in attempts if a.arm == "unaided"]
    return {
        "meta": {
            "generated": time.strftime("%Y-%m-%d %H:%M"),
            "protocol": "single-shot / no-repair (max_correction_steps=0)",
            "repeats": repeats, "n_reports": n,
            "staged_input": str(staged_input),
            "with_doc": str(SKILL_DOC.relative_to(SKILLS_ROOT)),
            "without_doc": str(UPSTREAM_DOC.relative_to(SKILLS_ROOT)),
            "executed_tier5": execute, "timeout_s": timeout,
            "anon_python_bin": ANON_PYTHON_BIN,
            "backend_specs": backend_specs,
        },
        "aggregate": {
            "with_passes": sum(1 for a in with_atts if a.passed), "with_total": len(with_atts),
            "without_passes": sum(1 for a in without_atts if a.passed), "without_total": len(without_atts),
            "unaided_passes": sum(1 for a in unaided_atts if a.passed), "unaided_total": len(unaided_atts),
        },
        "per_cell": per_cell,
        "paired": paired,
        "token_profiling": token_rows,
        "reachability": reachability,
        "attempts": [asdict(a) for a in attempts],
    }


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def _pct(n: int, d: int) -> str:
    return f"{(100.0 * n / d):.0f}%" if d else "n/a"


def _md_cell(s: str) -> str:
    """Make a value safe for a Markdown table cell (no pipes/newlines/formatting)."""
    s = re.sub(r"\s+", " ", str(s)).strip()
    return s.replace("|", "/").replace("`", "'").replace("*", "")


def _row_escape_values(attempts: list[dict], key: str, idx: int, limit: int = 12) -> str:
    """Distinct escaped values found at report index ``idx`` across the given attempts."""
    vals: list[str] = []
    for a in attempts:
        rows = a.get(key, [])
        if idx < len(rows):
            for e in rows[idx].get("examples", []):
                v = e.get("value") if isinstance(e, dict) else e
                if v:
                    vals.append(str(v))
    return _md_cell(", ".join(list(dict.fromkeys(vals))[:limit])) or "—"


def render_report(study: dict) -> str:
    m = study["meta"]
    agg = study["aggregate"]
    atts = study["attempts"]
    paired = compute_paired_row(atts)
    per_cell = compute_per_cell(atts)
    ov = paired["__overall__"]
    L: list[str] = []
    L.append("# Report Anonymization — With-vs-Without Skill Experiment\n")
    L.append(f"Generated: {m['generated']} (local).")
    L.append(f"Protocol: {m['protocol']}. Repeats per backend/arm: {m['repeats']}.\n")
    L.append(
        "This report evaluates the **report-anonymization** skill: does "
        "`LLM + SKILL.md` help an agent produce a correct NeMo Anonymizer command "
        "compared with `LLM + upstream NeMo Anonymizer README`? Both arms differ "
        "only in the one document the agent may read; both execute the real NeMo "
        "Anonymizer pipeline for tier-5.\n")
    L.append("**Pass criterion: an arm passes only if it produced anonymized output AND an LLM "
             "judge found ZERO residual PHI escapes across all rows — any single escape is a fail.**\n")
    L.append("This is an engineering reproducibility protocol. It is not a clinical, "
             "diagnostic, or regulatory claim.\n")

    L.append("## Evaluation task\n")
    n_backends = len({a["backend"] for a in atts})
    nrep = int(m.get("n_reports") or 0)
    L.append(f"- **Dataset (dataset level):** {nrep} reports, staged from `{m['staged_input']}`.")
    L.append(f"- **Backends:** {n_backends}. Each backend anonymizes all {nrep} reports, so each arm covers "
             f"{n_backends} **backend-runs** = {n_backends * nrep} **report-runs** (one report processed by one backend).")
    L.append("- **Residual PHI escape (item level):** one un-redacted PHI value the judge finds in a report-run. "
             "A single report-run can contain several escapes, so escape counts exceed the number of leaky report-runs.")
    L.append(f"- With-skill document: `{m['with_doc']}`")
    L.append(f"- Without-skill document: `{m['without_doc']}`")
    L.append(f"- Tier-5 execution: {'yes' if m['executed_tier5'] else 'no (command generation only)'}"
             f" (fresh output dir per attempt; `python` -> env with nemo-anonymizer, `NVIDIA_API_KEY` set).\n")

    L.append("## Current aggregate result\n")

    # Headline: redaction quality by arm (the primary result).
    judged_all = [a for a in atts if a.get("judge_rows_scored")]
    passmap = {
        "with": ("With skill (SKILL.md)", agg["with_passes"], agg["with_total"]),
        "without": ("Without skill (upstream README)", agg["without_passes"], agg["without_total"]),
        "unaided": ("Unaided (natural request, no doc)", agg.get("unaided_passes", 0), agg.get("unaided_total", 0)),
    }
    if judged_all:
        jm = next((a.get("judge_model") for a in judged_all if a.get("judge_model")), "llm-judge")
        L.append("### Headline — PHI redaction result by arm\n")
        L.append(f"**Pass = a backend-run produced output AND had zero residual PHI escapes across all its "
                 f"reports (any escape is a fail).** Residual escapes (individual PHI items) are counted by an "
                 f"LLM judge (`{jm}`) re-reading each anonymized report. Each column names its unit: "
                 "*backend-runs* (out of the backends run) vs *report-runs* (report x backend) vs *items*.\n")
        L.append("| Arm | Backend-runs producing output | Residual PHI escapes (items) | "
                 "Report-runs fully redacted (report x backend) | Backend-runs with 0 escapes |")
        L.append("|---|:--:|--:|:--:|:--:|")
        for key in ("with", "without", "unaided"):
            label, _np, nt_ = passmap[key]
            arm_atts = [a for a in atts if a["arm"] == key]
            if not arm_atts:
                continue
            total = len(arm_atts)
            completed = sum(1 for a in arm_atts if a.get("completed") or a.get("tier", 0) >= 5)
            passed = sum(1 for a in arm_atts if a.get("passed"))
            esc = sum(a.get("judge_out_phi_total", 0) for a in arm_atts if a.get("judge_rows_scored"))
            clean = sum(a.get("judge_rows_clean", 0) for a in arm_atts if a.get("judge_rows_scored"))
            scored = sum(a.get("judge_rows_scored", 0) for a in arm_atts)
            b = "**" if key == "with" else ""
            L.append(f"| {b}{label}{b} | {completed}/{total} | {b}{esc}{b} | {b}{clean}/{scored}{b} | "
                     f"{b}{passed}/{total}{b} |")
        L.append("")

    L.append("### Overall result (dataset level) — pass = produced output with zero PHI escapes\n")
    L.append("Each row is one **backend-run** (one backend anonymizing the full staged dataset). "
             "A pass requires tier-5 output and zero residual PHI escapes across all reports in that run.\n")
    L.append("| Arm | Passes with 0 PHI escapes |")
    L.append("|---|---:|")
    L.append(f"| With skill (SKILL.md) | {agg['with_passes']}/{agg['with_total']} ({_pct(agg['with_passes'], agg['with_total'])}) |")
    L.append(f"| Without skill (upstream README) | {agg['without_passes']}/{agg['without_total']} ({_pct(agg['without_passes'], agg['without_total'])}) |")
    if agg.get("unaided_total"):
        L.append(f"| Unaided (natural request, no doc) | {agg['unaided_passes']}/{agg['unaided_total']} ({_pct(agg['unaided_passes'], agg['unaided_total'])}) |")
    L.append("")

    L.append("### Paired with-vs-without (exact one-sided sign test, report-row level)\n")
    L.append("Each **pair** is one report row (`study_uid`) on the same backend and repeat. "
             "**Skill wins** if with-skill had strictly fewer residual PHI escapes; "
             "**Without wins** if without-skill had fewer; **Tie** if equal (including 0 vs 0).\n")
    L.append("| Scope | Report pairs | Skill wins | Without wins | Ties | Sign-test p |")
    L.append("|---|---:|---:|---:|---:|---:|")
    for backend in sorted(k for k in paired if k != "__overall__"):
        p = paired[backend]
        L.append(f"| {backend} | {p['pairs']} | {p['skill_wins']} | {p['without_wins']} | {p['ties']} | {p['sign_test_p']} |")
    L.append(f"| **overall** | {ov['pairs']} | {ov['skill_wins']} | {ov['without_wins']} | {ov['ties']} | {ov['sign_test_p']} |\n")

    L.append("### Per-backend, per-arm report-row pass counts and mean tier\n")
    L.append("**Report-rows fully redacted** = judge scored the row and found zero residual PHI escapes. "
             "**Mean tier** is the attempt-level command ladder (1–5), averaged across repeats.\n")
    L.append("| Backend/arm | Report-rows fully redacted | Mean tier (attempt) |")
    L.append("|---|---:|---:|")
    for cell in sorted(per_cell):
        c = per_cell[cell]
        L.append(
            f"| {cell} | {c['row_passes']}/{c['row_total']} "
            f"({_pct(c['row_passes'], c['row_total'])}) | {c['mean_tier']} |"
        )
    L.append("")

    # --- Row-level residual-PHI escapes ---------------------------------------
    atts = study["attempts"]
    L.append("## PHI redaction (row-level)\n")

    judged = [a for a in atts if a.get("judge_rows_scored")]
    if judged:
        jm = next((a.get("judge_model") for a in judged if a.get("judge_model")), "llm-judge")
        L.append(f"### LLM-as-judge residual escapes (primary) — judge model `{jm}`\n")
        L.append("An independent model re-read each anonymized report and flagged residual PHI — real "
                 "identifying values still present as plain text rather than a `[bracketed]` placeholder. "
                 "This is the primary escape metric; the deterministic scan below is a conservative "
                 "cross-check.\n")
        L.append("| Backend / arm | Reports fully redacted (of dataset, per backend) | Residual PHI escapes (items) | Example escaped values |")
        L.append("|---|:--:|--:|---|")
        for a in sorted(judged, key=lambda a: (a["backend"], a["arm"])):
            ex: list[str] = []
            for r in a.get("judge_row_phi", []):
                for e in r.get("examples", []):
                    if isinstance(e, dict) and e.get("value"):
                        ex.append(str(e["value"]))
                    elif isinstance(e, str):
                        ex.append(e)
            ex_str = ", ".join(list(dict.fromkeys(ex))[:6])
            L.append(f"| {a['backend']}/{a['arm']} | {a['judge_rows_clean']}/{a['judge_rows_scored']} | "
                     f"{a['judge_out_phi_total']} | {ex_str or 'none'} |")
        L.append("")
        L.append("#### Per-report residual PHI escape counts — one row per dataset report (0 = fully redacted)\n")
        L.append("Each cell is the number of residual PHI items the judge found in that report under the given "
                 "backend/arm (not a pass/fail; a report can hold several items).\n")
        L.append("| study_uid (report) | " + " | ".join(f"{a['backend']}/{a['arm']} (items)" for a in judged)
                 + " | Escaped PHI values |")
        L.append("|---|" + "---:|" * len(judged) + "---|")
        jbase = judged[0]["judge_row_phi"]
        jnrows = max(len(a["judge_row_phi"]) for a in judged)
        for i in range(jnrows):
            uid = jbase[i]["uid"] if i < len(jbase) else str(i)
            cells = [str(a["judge_row_phi"][i]["n"]) if i < len(a["judge_row_phi"]) else "—" for a in judged]
            vals = _row_escape_values(judged, "judge_row_phi", i)
            L.append(f"| `{uid}` | " + " | ".join(cells) + f" | {vals} |")
        L.append("")

    L.append("### Deterministic scan (cross-check)\n")
    L.append("Conservative regex scan for residual PHI signals (numeric dates, prose dates, 5+ digit IDs, "
             "`Dr./Prof./Mr./Mrs./Ms.` + name, phones), excluding `[PLACEHOLDER]` tokens. Middle initials "
             "and bare institution names are not counted, so this under-reports rather than over-reports.\n")
    L.append("### Per-arm residual summary\n")
    L.append("| Backend/arm | Rows fully redacted | Residual PHI escapes | Baseline PHI in input | Escape types |")
    L.append("|---|---:|---:|---:|---|")
    for a in sorted(atts, key=lambda a: (a["backend"], a["arm"])):
        if a.get("rows_scored"):
            types = ", ".join(f"{k}={v}" for k, v in sorted((a.get("phi_by_type") or {}).items())) or "none"
            L.append(f"| {a['backend']}/{a['arm']} | {a['rows_clean']}/{a['rows_scored']} | "
                     f"{a['out_phi_total']} | {a['in_phi_total']} | {types} |")
        else:
            L.append(f"| {a['backend']}/{a['arm']} | n/a | n/a | n/a | (no anonymized output produced) |")
    L.append("")
    scored = [a for a in atts if a.get("rows_scored")]
    if scored:
        L.append("### Per-row residual escape counts (0 = fully redacted)\n")
        L.append("| study_uid | input PHI | " + " | ".join(f"{a['backend']}/{a['arm']}" for a in scored)
                 + " | Escaped values (regex) |")
        L.append("|---|---:|" + "---:|" * len(scored) + "---|")
        base = scored[0]["row_phi"]
        nrows = max(len(a["row_phi"]) for a in scored)
        for i in range(nrows):
            uid = base[i]["uid"] if i < len(base) else str(i)
            inphi = base[i]["in_phi"] if i < len(base) else ""
            cells = [str(a["row_phi"][i]["out_phi"]) if i < len(a["row_phi"]) else "—" for a in scored]
            vals = _row_escape_values(scored, "row_phi", i)
            L.append(f"| `{uid}` | {inphi} | " + " | ".join(cells) + f" | {vals} |")
        L.append("")

    L.append("## Token profiling\n")
    L.append("Provider-reported usage for the command-generation call (the agent overhead "
             "to pick the command). The NeMo Anonymizer pipeline's own internal token use "
             "during tier-5 execution is not surfaced as provider usage.\n")
    L.append("| Backend | Arm | Repeats | Passes with 0 PHI escapes | LLM calls | Prompt tok | Completion tok | Reasoning tok | Total tok | Mean exec s |")
    L.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in study["token_profiling"]:
        star = "*" if r["estimated"] else ""
        L.append(f"| {r['backend']} | {r['arm']} | {r['repeats']} | {r['passes']} | {r['llm_calls']} | "
                 f"{r['prompt_tokens']} | {r['completion_tokens']} | {r['reasoning_tokens']} | "
                 f"{r['total_tokens']}{star} | {r['mean_exec_s']} |")
    if any(r["estimated"] for r in study["token_profiling"]):
        L.append("\n`*` = estimated (backend approximates tokens rather than reporting exact usage).")
    L.append("")

    L.append("## Five-tier grade\n")
    L.append("| Tier | Check |")
    L.append("|---|---|")
    for t in range(1, 6):
        L.append(f"| {t} | {TIER_LADDER[t]} |")
    L.append("")

    L.append("## Generated commands\n")
    for a in study["attempts"]:
        head = f"**{a['backend']} / {a['arm']} / rep{a['repeat']}** — tier {a['tier']}, {'PASS' if a['passed'] else 'fail'}"
        if a.get("extraction") == "recovered":
            head += " (command recovered from an unfenced response)"
        if a.get("guard_blocked"):
            head += f" (guard: {a['guard_reason']})"
        L.append(head + "\n")
        if a.get("command"):
            L.append("```bash\n" + a["command"] + "\n```")
        else:
            L.append("_no command extracted_")
        if a.get("failed_tiers"):
            L.append(f"- failed: {', '.join(a['failed_tiers'])}")
        if a.get("exec_rc") is not None:
            L.append(f"- exec rc={a['exec_rc']} ({a['exec_seconds']:.1f}s), out_rows={a['n_out_rows']}, transformed={a['n_transformed']}")
        if a.get("stderr_tail") and not a.get("passed"):
            tail = a["stderr_tail"].strip().splitlines()[-3:]
            if tail:
                L.append("- stderr tail: `" + " / ".join(t.strip() for t in tail) + "`")
        L.append("")

    L.append("## Backend reachability (probed at run time)\n")
    L.append("| Backend | Kind | Model | Reachable | Ping s |")
    L.append("|---|---|---|:--:|---:|")
    for r in study["reachability"]:
        L.append(f"| {r['backend']} | {r['kind']} | `{r['model']}` | {'yes' if r['reachable'] else 'no'} | {r['ping_s']} |")
    L.append("")

    L.append("## Findings\n")
    with_p, with_t = agg["with_passes"], agg["with_total"]
    without_p, without_t = agg["without_passes"], agg["without_total"]
    atts = study["attempts"]

    def _mean_exec(arm: str) -> float | None:
        xs = [a["exec_seconds"] for a in atts if a["arm"] == arm and a.get("exec_rc") == 0]
        return round(sum(xs) / len(xs), 1) if xs else None

    jw = [a for a in atts if a["arm"] == "with" and a.get("judge_rows_scored")]
    jo = [a for a in atts if a["arm"] == "without" and a.get("judge_rows_scored")]
    w_esc = sum(a["judge_out_phi_total"] for a in jw)
    w_clean = sum(a["judge_rows_clean"] for a in jw)
    w_scored = sum(a["judge_rows_scored"] for a in jw)
    o_esc = sum(a["judge_out_phi_total"] for a in jo)
    o_clean = sum(a["judge_rows_clean"] for a in jo)
    o_scored = sum(a["judge_rows_scored"] for a in jo)
    if jw and jo:
        ratio = f" (~{o_esc / max(1, w_esc):.0f}x fewer items with the skill)" if o_esc > w_esc else ""
        wrep: dict[str, int] = {}
        for a in jw:
            for r in a.get("judge_row_phi", []):
                wrep[r["uid"]] = wrep.get(r["uid"], 0) + max(0, int(r["n"]))
        conc = ""
        if wrep:
            top_uid, top_n = max(wrep.items(), key=lambda kv: kv[1])
            if top_n and w_esc and top_n >= max(2, w_esc // 2):
                conc = (f" Concentration: {top_n} of the {w_esc} with-skill escape items came from one hard "
                        f"report (`{top_uid}`) that the strict labels missed across backends.")
        L.append(f"- **Redaction quality gap (primary result):** with-skill left **{w_esc}** residual PHI "
                 f"escapes (individual PHI items) and fully redacted **{w_clean}/{w_scored}** report-runs; "
                 f"without-skill left **{o_esc}** items and fully redacted **{o_clean}/{o_scored}** "
                 f"report-runs{ratio}. The skill's strict GLiNER label set drives detection; the "
                 "upstream-README default redaction leaves many residual fragments (mostly name middle "
                 "initials)." + conc)
    L.append(
        f"- Under the strict zero-escape pass criterion, with-skill passed {with_p}/{with_t} backend-runs and "
        f"without-skill {without_p}/{without_t} backend-runs" + (
            " — the skill fully redacts the header PHI while the upstream-README arm leaves residual "
            "fragments the judge flags." if with_p > without_p
            else " — neither backend-run cleared a perfect zero-escape bar at this scale, so the item-level "
                 "escape counts above are the primary signal."))
    mw, mo = _mean_exec("with"), _mean_exec("without")
    if mw is not None and mo is not None:
        slow = max((a for a in atts if a.get("exec_rc") == 0), key=lambda a: a["exec_seconds"], default=None)
        extra = ""
        if slow is not None and slow["arm"] == "without":
            extra = (f" The slowest arm was {slow['backend']}/without at {slow['exec_seconds']:.0f}s: the "
                     "unaided upstream-default detection path (no strict label set) does far more LLM "
                     "augmentation and nearly hit the wall-clock budget.")
        L.append(f"- Robustness/speed: mean tier-5 execution was {mw}s with-skill vs {mo}s without-skill."
                 + extra + " The wrapper's strict GLiNER label set bounds detection cost.")
    recovered = [a for a in atts if a.get("extraction") == "recovered"]
    if recovered:
        names = ", ".join(f"{a['backend']}/{a['arm']}" for a in recovered)
        L.append(f"- Protocol compliance: {names} emitted an unfenced command that only the tolerant "
                 "recovery fallback could extract (a known formatting fragility), whereas the "
                 "wrapper-based commands were clean fenced one-liners.")
    L.append("- Output contract: the with-skill wrapper emits `study_uid,report` plus a schema-valid "
             "`anonymization_summary` JSON and per-stage telemetry; the upstream `anonymizer run` output "
             "drops the `study_uid` passthrough and emits raw trace columns (`report_w_PHI_replaced`, ...).")
    hung = [a for a in study["attempts"]
            if ("hung" in (a.get("stderr_tail") or "").lower()
                or "did not complete" in (a.get("stderr_tail") or "").lower())]
    if hung:
        names = ", ".join(f"{a['backend']}/{a['arm']}" for a in hung)
        L.append(f"- Incomplete arm(s): **{names}** hung and did not complete within the wall-clock "
                 "budget (killed; recorded as a tier-5 non-completion). This pilot's paired result for "
                 "that pair is provisional pending a rerun.")
    if agg.get("unaided_total"):
        L.append(f"- Unaided baseline (natural request, no doc, no skill): "
                 f"{agg['unaided_passes']}/{agg['unaided_total']} produced a runnable anonymization "
                 "command — the hardest arm, standing in for a user who just asks the model to redact "
                 "the CSV with no NeMo Anonymizer documentation at all.")
    judged = [a for a in atts if a.get("judge_rows_scored")]
    if judged and any(a["arm"] == "unaided" for a in judged):
        by_arm: dict[str, list[int]] = {}
        for a in judged:
            agg_arm = by_arm.setdefault(a["arm"], [0, 0, 0])
            agg_arm[0] += a["judge_out_phi_total"]
            agg_arm[1] += a["judge_rows_clean"]
            agg_arm[2] += a["judge_rows_scored"]
        parts = "; ".join(f"{arm}: {v[0]} escape items, {v[1]}/{v[2]} report-runs fully redacted"
                          for arm, v in sorted(by_arm.items()))
        L.append(f"- LLM-judge residual PHI by arm (lower is better): {parts}. "
                 "See the per-report judge table above.")
    L.append("- `Pass` = produced output AND zero LLM-judged residual PHI escapes (any escape is a fail). "
             "`Produced output` (tier-5 completion) is reported separately, so a leaky-but-complete arm "
             "shows as produced-output yet fails.\n")

    L.append("## Reproduce\n")
    L.append("From the `medical-AI-skills` catalog root:\n")
    L.append("```bash\nexport NVIDIA_API_KEY=\"nvapi-...\"\npython -m tools.curation_eval.anon_experiment \\\n"
             f"  --backends {' '.join(m['backend_specs'])} \\\n"
             f"  --repeats {m['repeats']} --limit {m['n_reports']}\n```\n")
    return "\n".join(L)


# --------------------------------------------------------------------------- #
# HTML dashboard (kept in sync with the Markdown report)
# --------------------------------------------------------------------------- #
def _sanitize(text: str) -> str:
    """Strip catalog-root and home prefixes so committed artifacts are repo-relative."""
    home = os.path.expanduser("~")
    return (text.replace(str(SKILLS_ROOT.resolve()) + "/", "")
                .replace(str(SKILLS_ROOT.resolve()), ".").replace(home, "~"))


def _md_inline(s: str) -> str:
    s = _html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def _md_to_html(md: str) -> str:
    """Minimal, dependency-free Markdown -> HTML for this report's constructs."""
    lines = md.split("\n")
    out: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if line.lstrip().startswith("```"):
            i += 1
            code: list[str] = []
            while i < n and not lines[i].lstrip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>" + _html.escape("\n".join(code), quote=False) + "</code></pre>")
            continue
        if line.startswith("|") and i + 1 < n and re.match(r"^\|[\s:|-]+\|?\s*$", lines[i + 1]):
            header = [c.strip() for c in line.strip().strip("|").split("|")]
            i += 2
            rows: list[list[str]] = []
            while i < n and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            t = ["<table><thead><tr>"] + [f"<th>{_md_inline(h)}</th>" for h in header] + ["</tr></thead><tbody>"]
            for r in rows:
                cells = "".join(f'<td>{_md_inline(c)}</td>' for c in r)
                t.append(f"<tr>{cells}</tr>")
            t.append("</tbody></table>")
            out.append("".join(t))
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{_md_inline(m.group(2))}</h{lvl}>")
            i += 1
            continue
        if re.match(r"^---+\s*$", line):
            out.append("<hr>")
            i += 1
            continue
        if line.lstrip().startswith("- "):
            items: list[str] = []
            while i < n and lines[i].lstrip().startswith("- "):
                items.append(f"<li>{_md_inline(lines[i].lstrip()[2:])}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        if line.strip() == "":
            i += 1
            continue
        if line.startswith(">"):
            out.append(f"<blockquote>{_md_inline(line.lstrip('> '))}</blockquote>")
            i += 1
            continue
        para = [line]
        i += 1
        while i < n and lines[i].strip() != "" and not lines[i].startswith(("|", "#", "- ", ">", "```")):
            para.append(lines[i])
            i += 1
        out.append("<p>" + _md_inline(" ".join(para)) + "</p>")
    return "\n".join(out)


_DASHBOARD_CSS = """
:root{--bg:#0f172a;--panel:#1e293b;--muted:#94a3b8;--fg:#e2e8f0;--line:#334155;
--good:#22c55e;--good-bg:#052e16;--bad:#ef4444;--bad-bg:#450a0a;--warn:#f59e0b;--accent:#38bdf8;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}
header.top{padding:24px 32px;border-bottom:1px solid var(--line);background:linear-gradient(180deg,#111827,#0f172a);}
header.top h1{margin:0 0 6px;font-size:22px;}
header.top .sub{color:var(--muted);font-size:13px;}
.wrap{max-width:1100px;margin:0 auto;padding:24px 32px 64px;}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin:8px 0 28px;}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px;}
.card .label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.04em;}
.card .value{font-size:30px;font-weight:700;margin:6px 0 2px;}
.card .foot{color:var(--muted);font-size:12px;}
.card.good{border-color:#14532d}.card.good .value{color:var(--good)}
.card.bad{border-color:#7f1d1d}.card.bad .value{color:var(--bad)}
.card.accent .value{color:var(--accent)}
h2{margin:32px 0 12px;font-size:18px;border-bottom:1px solid var(--line);padding-bottom:6px;}
h3{margin:22px 0 10px;font-size:15px;color:#cbd5e1;}
h4{margin:16px 0 8px;font-size:13px;color:var(--muted);text-transform:uppercase;letter-spacing:.03em;}
table{border-collapse:collapse;width:100%;margin:8px 0 18px;font-size:13px;}
th,td{border:1px solid var(--line);padding:6px 10px;text-align:left;}
th{background:#0b1220;color:#cbd5e1;position:sticky;top:0;}
tbody tr:nth-child(even){background:rgba(148,163,184,.05);}
td code,p code,li code{background:#0b1220;border:1px solid var(--line);border-radius:4px;padding:1px 5px;font-size:12px;}
pre{background:#0b1220;border:1px solid var(--line);border-radius:10px;padding:14px 16px;overflow:auto;}
pre code{background:none;border:none;padding:0;font-size:12.5px;color:#e2e8f0;}
a{color:var(--accent);} hr{border:none;border-top:1px solid var(--line);margin:24px 0;}
blockquote{border-left:3px solid var(--accent);margin:12px 0;padding:4px 14px;color:var(--muted);}
.badge{display:inline-block;border-radius:6px;padding:1px 8px;font-size:12px;font-weight:600;}
.badge.pass{background:var(--good-bg);color:var(--good);}
.badge.fail{background:var(--bad-bg);color:var(--bad);}
.body table td:first-child{white-space:nowrap;}
details.rowtable{border:1px solid var(--line);border-radius:10px;padding:4px 14px;margin:12px 0;background:#0b1220;}
details.rowtable>summary{cursor:pointer;color:var(--accent);font-weight:600;padding:8px 0;list-style:none;}
details.rowtable>summary::-webkit-details-marker{display:none;}
details.rowtable>summary::before{content:"\\25B6\\00a0\\00a0";font-size:11px;}
details.rowtable[open]>summary::before{content:"\\25BC\\00a0\\00a0";}
details.rowtable td:last-child{color:var(--warn);}
footer{color:var(--muted);font-size:12px;padding:24px 32px;border-top:1px solid var(--line);}
"""


def _make_collapsible(body_html: str) -> str:
    """Wrap the per-report / per-row escape tables in collapsed <details> blocks."""
    pat = re.compile(
        r'(?P<h><h[34]>(?P<title>[^<]*residual (?:PHI )?escape counts[^<]*)</h[34]>)'
        r'(?P<mid>(?:\s*<p>.*?</p>)?)'
        r'\s*(?P<table><table>.*?</table>)', re.DOTALL)

    def repl(m: re.Match) -> str:
        return (f'<details class="rowtable"><summary>{m.group("title")} — click to expand</summary>'
                f'{m.group("mid")}{m.group("table")}</details>')

    return pat.sub(repl, body_html)


def _parse_headline(md_text: str) -> dict[str, list[str]]:
    """Parse the '### Headline' table from the report so KPIs come from the MD itself."""
    lines = md_text.split("\n")
    try:
        start = next(i for i, l in enumerate(lines) if l.startswith("### Headline"))
    except StopIteration:
        return {}
    i = start + 1
    while i < len(lines) and not lines[i].startswith("|"):
        i += 1
    i += 2  # skip header + separator rows
    rows: dict[str, list[str]] = {}
    while i < len(lines) and lines[i].startswith("|"):
        cells = [re.sub(r"[*`]", "", c).strip() for c in lines[i].strip().strip("|").split("|")]
        if cells and cells[0]:
            rows[cells[0]] = cells
        i += 1
    return rows


def _meta_line(md_text: str, prefix: str) -> str:
    for l in md_text.split("\n"):
        if l.startswith(prefix):
            return l[len(prefix):].strip().rstrip(".")
    return ""


def _card(cls: str, label: str, value: str, foot: str) -> str:
    return (f'<div class="card {cls}"><div class="label">{_html.escape(label)}</div>'
            f'<div class="value">{_html.escape(str(value))}</div>'
            f'<div class="foot">{_html.escape(foot)}</div></div>')


def render_dashboard_html(md_text: str) -> str:
    """Self-contained HTML dashboard rendered from the Markdown report (same content).

    KPI cards are parsed from the report's '### Headline' table so the dashboard
    stays a faithful mirror of the Markdown and can be regenerated from the MD alone.
    """
    rows = _parse_headline(md_text)

    def findrow(prefix: str) -> list[str] | None:
        for label, cells in rows.items():
            if label.lower().startswith(prefix):
                return cells
        return None

    # Headline cells: [Arm, Backend-runs producing output, Residual PHI escapes (items),
    #                   Report-runs fully redacted, Backend-runs with 0 escapes]
    w, o = findrow("with skill"), findrow("without skill")
    cards: list[str] = []
    if w and len(w) >= 5:
        cards.append(_card("good", "With skill · residual PHI items", w[2], f"{w[3]} report-runs fully redacted"))
    if o and len(o) >= 5:
        cards.append(_card("bad", "Without skill · residual PHI items", o[2], f"{o[3]} report-runs fully redacted"))
    if w and o and len(w) >= 5 and len(o) >= 5:
        try:
            we, oe = int(w[2]), int(o[2])
            if we and oe > we:
                cards.append(_card("accent", "Escape reduction with skill", f"~{oe / we:.0f}x",
                                   "fewer residual PHI escapes"))
        except ValueError:
            pass
    mrep = re.search(r"Reports:\s*\**\s*(\d+)", md_text)
    if mrep:
        cards.append(_card("", "Dataset", mrep.group(1), "reports"))

    body_html = _make_collapsible(_md_to_html(md_text))
    gen, proto = _meta_line(md_text, "Generated:"), _meta_line(md_text, "Protocol:")
    subtitle = _html.escape(" · ".join(x for x in (gen, proto) if x)) + " · pass = zero PHI escapes"
    kpis = ('<section class="kpis">' + "".join(cards) + "</section>") if cards else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Report Anonymization — With-vs-Without Dashboard</title>
<style>{_DASHBOARD_CSS}</style>
</head>
<body>
<header class="top">
  <h1>Report Anonymization — With-vs-Without Skill Dashboard</h1>
  <div class="sub">{subtitle}</div>
</header>
<div class="wrap">
  {kpis}
  <div class="body">
  {body_html}
  </div>
</div>
<footer>Generated from docs/anonymization-with-vs-without-experiment.md by
tools/curation_eval/anon_experiment.py. Engineering reproducibility artifact; not a clinical or regulatory claim.</footer>
</body>
</html>
"""


def finalize_outputs(study: dict, report_path: str) -> tuple[str, str]:
    """Write the Markdown report AND a synced HTML dashboard (both sanitized)."""
    md = _sanitize(render_report(study))
    rp = Path(report_path)
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(md, encoding="utf-8")
    html_path = rp.with_suffix(".html")
    html_path.write_text(_sanitize(render_dashboard_html(md)), encoding="utf-8")
    return str(rp), str(html_path)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--backends", nargs="+", default=["mock"],
                   help="backend specs: 'mock', a registry name, or name=base_url=model[=API_KEY_ENV]")
    p.add_argument("--arms", nargs="+", default=["with", "without"],
                   choices=["with", "without", "unaided"],
                   help="which arms to run (with=SKILL.md, without=upstream README, unaided=natural request)")
    p.add_argument("--judge", default=None,
                   help="backend spec for the LLM-as-judge residual-PHI grader (scores all arms)")
    p.add_argument("--merge", default=None,
                   help="prior study dir (or study_results.json) whose attempts are folded in before judging")
    p.add_argument("--repeats", type=int, default=1)
    p.add_argument("--input", default=str(DEFAULT_INPUT), help="source reports CSV")
    p.add_argument("--limit", type=int, default=100, help="rows to stage (0 = all)")
    p.add_argument("--out", default=None, help="study output dir")
    p.add_argument("--report", default=str(DEFAULT_REPORT), help="markdown report path")
    p.add_argument("--timeout", type=float, default=2400.0, help="per-command exec timeout (s)")
    p.add_argument("--no-execute", action="store_true",
                   help="generate + grade commands but do not run tier-5 (dry, no API cost for exec)")
    p.add_argument("--quiet", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    telemetry.configure(verbose=not args.quiet)
    study_out = Path(args.out) if args.out else (paths.RUNS_DIR / "anon" / time.strftime("study_%Y%m%d_%H%M%S"))
    study_out.mkdir(parents=True, exist_ok=True)

    input_csv = Path(args.input)
    if not input_csv.exists():
        raise SystemExit(f"input CSV not found: {input_csv}")
    staged = study_out / "_inputs" / "reports_w_PHI.csv"
    n = stage_input(input_csv, staged, args.limit)
    staged_abs = staged.resolve()
    telemetry.log(f"staged {n} reports -> {staged}")

    attempts, reachability = run_study(
        backend_specs=args.backends, arms=tuple(args.arms), repeats=args.repeats,
        staged_input=staged, n=n, study_out=study_out, timeout=args.timeout,
        execute=not args.no_execute,
    )

    merged_specs = list(args.backends)
    if args.merge:
        prior_path = Path(args.merge)
        if prior_path.is_dir():
            prior_path = prior_path / "study_results.json"
        prior = json.loads(prior_path.read_text(encoding="utf-8"))
        fnames = {f.name for f in fields(AttemptResult)}
        prior_atts = [AttemptResult(**{k: v for k, v in d.items() if k in fnames})
                      for d in prior.get("attempts", [])]
        attempts = prior_atts + attempts
        seen = {r["backend"] for r in reachability}
        for r in prior.get("reachability", []):
            if r["backend"] not in seen:
                reachability.append(r)
                seen.add(r["backend"])
        for s in prior.get("meta", {}).get("backend_specs", []):
            if s not in merged_specs:
                merged_specs.append(s)
        telemetry.log(f"merged {len(prior_atts)} prior attempt(s) from {prior_path}")

    if args.judge:
        judge = make_backend(args.judge)
        jp = probe(judge)
        telemetry.log(f"judge {judge.model} reachable={jp.ok} {jp.latency_s:.2f}s")
        for a in attempts:
            judge_attempt(a, judge, staged_abs)
        # Pass criterion: an arm passes only if it produced output AND the judge
        # found ZERO residual PHI escapes. Any escape is a fail.
        for a in attempts:
            a.completed = a.tier >= 5
            a.passed = bool(a.completed and a.judge_rows_scored > 0 and a.judge_out_phi_total == 0)

    study = aggregate(attempts, reachability, merged_specs, args.repeats, n,
                      Path(_rel(staged)), args.timeout, not args.no_execute)
    (study_out / "study_results.json").write_text(json.dumps(study, indent=2), encoding="utf-8")
    # Write the Markdown report and the synced HTML dashboard (repo-relative, sanitized).
    md_path, html_path = finalize_outputs(study, args.report)
    finalize_outputs(study, str(study_out / "report.md"))
    telemetry.log(f"wrote report {md_path} + dashboard {html_path}")

    ov = study["paired"]["__overall__"]
    print(json.dumps({
        "report": md_path,
        "dashboard_html": html_path,
        "results": str(study_out / "study_results.json"),
        "with_passes": f"{study['aggregate']['with_passes']}/{study['aggregate']['with_total']}",
        "without_passes": f"{study['aggregate']['without_passes']}/{study['aggregate']['without_total']}",
        "paired_overall": ov,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
