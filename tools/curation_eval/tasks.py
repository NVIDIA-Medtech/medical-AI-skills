# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""The three curation steps, each realised in a with-skill and without-skill arm.

* Step 1 ``select`` -- shared, deterministic fixture (both arms consume the same
  seeded 10-report sample). The reproducible selection *is* the skill-shaped
  behaviour for this step; it is graded for validity but is not the with/without
  differentiator.
* Step 2 ``pii`` -- with-skill runs the ``report-anonymization`` wrapper; the
  without-skill arm asks the backend, from a generic prompt, for a yes/no PII
  verdict per report.
* Step 3 ``label`` -- with-skill runs the ``report-pathology-classification``
  wrapper (fixed vocabulary + complete 0/1 vector); the without-skill arm asks
  the backend to "assign disease labels" with no fixed vocabulary or schema.

Each step returns a ``StepResult`` with the parsed per-report output, whether it
executed, aggregated token usage, and runtime.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import paths, telemetry
from .backends import Backend
from .dataset import Dataset

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


@dataclass
class StepResult:
    step: str
    arm: str
    executed: bool = False
    error: str | None = None
    output: dict = field(default_factory=dict)
    usage: dict = field(default_factory=dict)
    runtime_s: float = 0.0
    raw_path: str | None = None
    surface: str | None = None  # runnable surface used (skill script or "llm:<model>")


def _empty_usage() -> dict:
    return {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "reasoning_tokens": 0,
        "n_calls": 0,
        "estimated": False,
    }


def _add_usage(acc: dict, u: dict) -> None:
    for k in ("prompt_tokens", "completion_tokens", "total_tokens", "reasoning_tokens"):
        acc[k] = acc.get(k, 0) + int(u.get(k, 0) or 0)
    acc["n_calls"] = acc.get("n_calls", 0) + 1
    if u.get("estimated"):
        acc["estimated"] = True


# ---------------------------------------------------------------------------
# Skill subprocess helper
# ---------------------------------------------------------------------------
def _run_skill(script: Path, cli_args: list[str]) -> tuple[int, str, str, float]:
    cmd = [sys.executable, str(script)] + cli_args
    mode = cli_args[cli_args.index("--mode") + 1] if "--mode" in cli_args else "?"
    telemetry.log(f"  \u2192 skill {script.name} (--mode {mode}) starting")
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd, cwd=str(paths.SKILLS_ROOT), capture_output=True, text=True
    )
    elapsed = time.perf_counter() - t0
    telemetry.log(f"  \u2190 skill {script.name} rc={proc.returncode} {elapsed:.1f}s")
    return proc.returncode, proc.stdout, proc.stderr, elapsed


def _extract_json(text: str) -> dict | None:
    """Best-effort parse of the first JSON object in a model response."""
    if not text:
        return None
    text = text.strip()
    # Strip <think>...</think> reasoning blocks some models emit.
    if "</think>" in text:
        text = text.split("</think>")[-1].strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        obj = json.loads(text[start : end + 1])
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def _extract_last_json(text: str) -> dict | None:
    """Return the LAST top-level balanced JSON object that parses to a dict.

    Needed for the skill's live stdout, where the wrapped upstream script's own
    prints (including a stray ``{}``) precede the skill's final JSON summary.
    """
    if not text:
        return None
    candidates: list[str] = []
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start != -1:
                candidates.append(text[start : i + 1])
    for cand in reversed(candidates):
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return None


# ---------------------------------------------------------------------------
# Step 1: select (shared fixture)
# ---------------------------------------------------------------------------
def step_select(dataset: Dataset, arm: str, work_dir: Path) -> StepResult:
    out = work_dir / "selected.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["study_uid", "report"])
        for rec in dataset.records:
            writer.writerow([rec["study_uid"], rec.get("report", "")])
    return StepResult(
        step="select",
        arm=arm,
        executed=True,
        output={"selected_uids": [r["study_uid"] for r in dataset.records]},
        usage=_empty_usage(),
        raw_path=str(out),
        surface="seeded-sampler",
    )


# ---------------------------------------------------------------------------
# Step 2: PII confirmation
# ---------------------------------------------------------------------------
_PII_SYSTEM = (
    "You are a careful assistant reviewing radiology report text for residual "
    "personally identifiable information (PII/PHI): patient or doctor names, "
    "dates, accession numbers, phone numbers, emails, or record IDs. "
    'Respond with STRICT JSON on a single line: {"pii_present": true} or '
    '{"pii_present": false}. Output only that JSON object.'
)


def step_pii_with(dataset: Dataset, arm: str, work_dir: Path, mode: str, model: str | None,
                  cuda: str | None) -> StepResult:
    args = [
        str(dataset.csv_path),
        "--out", str(work_dir),
        "--mode", mode,
        "--id-col", "study_uid",
        "--text-col", "report",
    ]
    if model:
        args += ["--model", model]
    if cuda:
        args += ["--cuda-visible-devices", cuda]
    rc, stdout, stderr, elapsed = _run_skill(paths.ANON_SCRIPT, args)
    res = StepResult(step="pii", arm=arm, runtime_s=elapsed, usage=_empty_usage(),
                     surface=f"skill:report-anonymization({mode})")
    if rc != 0:
        res.error = f"anonymization skill exit {rc}: {stderr.strip()[-400:]}"
        return res
    anon_csv = work_dir / "anonymized.csv"
    verdicts: dict[str, dict] = {}
    try:
        with anon_csv.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                uid = (row.get("UID") or "").strip()
                raw_map = row.get("Token_Mapping", "") or "{}"
                try:
                    mapping = json.loads(raw_map)
                    mapping = mapping if isinstance(mapping, dict) else {}
                except json.JSONDecodeError:
                    mapping = {}
                verdicts[uid] = {
                    "pii_present": bool(mapping),
                    "detected": list(mapping.values()),
                    "parsed": True,
                }
    except FileNotFoundError:
        res.error = "anonymization skill produced no anonymized.csv"
        return res
    res.executed = True
    res.output = {"verdicts": verdicts, "summary": _extract_json(stdout) or {}}
    res.raw_path = str(anon_csv)
    return res


def _pii_query(dataset: Dataset, arm: str, backend: Backend, work_dir: Path,
               system: str, surface: str, fname: str) -> StepResult:
    usage = _empty_usage()
    verdicts: dict[str, dict] = {}
    t0 = time.perf_counter()
    n = len(dataset.records)
    for i, rec in enumerate(dataset.records, 1):
        uid = rec["study_uid"]
        user = f"<report>\n{rec.get('report', '')}\n</report>"
        r = backend.chat(system, user)
        telemetry.call_tick("pii", arm, i, n, r.ok, r.latency_s,
                            (r.usage or {}).get("total_tokens", 0))
        if r.usage:
            _add_usage(usage, r.usage)
        if not r.ok:
            verdicts[uid] = {"pii_present": None, "parsed": False, "error": r.error}
            continue
        obj = _extract_json(r.text)
        if obj is None or "pii_present" not in obj or not isinstance(obj.get("pii_present"), bool):
            verdicts[uid] = {"pii_present": None, "parsed": False, "raw": r.text[:200]}
        else:
            verdicts[uid] = {"pii_present": bool(obj["pii_present"]), "parsed": True}
    out = work_dir / fname
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(verdicts, f, indent=2, ensure_ascii=False)
    return StepResult(
        step="pii", arm=arm, executed=True, output={"verdicts": verdicts},
        usage=usage, runtime_s=time.perf_counter() - t0, raw_path=str(out),
        surface=surface,
    )


def step_pii_without(dataset: Dataset, arm: str, backend: Backend, work_dir: Path) -> StepResult:
    return _pii_query(dataset, arm, backend, work_dir, _PII_SYSTEM,
                      f"llm:{backend.model}", "pii_without.json")


# ---------------------------------------------------------------------------
# Step 3: disease labelling
# ---------------------------------------------------------------------------
_LABEL_SYSTEM = (
    "You are a radiology assistant. Read the report findings and assign disease "
    "labels describing the pathologies mentioned as present. Respond with STRICT "
    'JSON: {"diseases": ["...", "..."]}. Output only that JSON object.'
)


def step_label_with(dataset: Dataset, arm: str, work_dir: Path, mode: str, model: str | None,
                    cuda: str | None) -> StepResult:
    args = [
        str(dataset.csv_path),
        "--out", str(work_dir),
        "--mode", mode,
        "--id-col", "study_uid",
        "--text-col", "findings",
    ]
    if model:
        args += ["--model", model]
    if cuda:
        args += ["--cuda-visible-devices", cuda]
    rc, stdout, stderr, elapsed = _run_skill(paths.PATHOLOGY_SCRIPT, args)
    res = StepResult(step="label", arm=arm, runtime_s=elapsed, usage=_empty_usage(),
                     surface=f"skill:report-pathology-classification({mode})")
    if rc != 0:
        res.error = f"pathology skill exit {rc}: {stderr.strip()[-400:]}"
        return res
    labels_csv = work_dir / "labels.csv"
    labels: dict[str, dict] = {}
    vocab_out: list[str] = []
    try:
        with labels_csv.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            vocab_out = [c for c in (reader.fieldnames or []) if c != "study_uid"]
            for row in reader:
                uid = (row.get("study_uid") or "").strip()
                labels[uid] = {c: (1 if str(row.get(c, "0")).strip() in ("1", "1.0") else 0)
                               for c in vocab_out}
    except FileNotFoundError:
        res.error = "pathology skill produced no labels.csv"
        return res
    res.executed = True
    res.output = {"labels": labels, "vocab": vocab_out, "schema": "fixed_vector",
                  "summary": _extract_json(stdout) or {}}
    res.raw_path = str(labels_csv)
    return res


# --- Same-model "with skill contract" prompts (arm_style="prompt") ----------
# These give the backend the skill's contract (for labelling: the exact fixed
# pathology vocabulary and the complete-0/1-vector schema) while holding the
# model fixed, isolating the skill's contribution.
_PII_WITH_SYSTEM = (
    "You are running the report-anonymization skill's review contract. Scan the "
    "radiology report for residual PII/PHI (patient/doctor names, dates, "
    "accession numbers, phone numbers, emails, record IDs). Return STRICT JSON on "
    'one line: {"pii_present": true|false}. Output only that JSON object.'
)


def _label_with_system(vocab: list[str]) -> str:
    listing = ", ".join(f'"{v}"' for v in vocab)
    return (
        "You are running the report-pathology-classification skill's contract. "
        "For the report findings, output a COMPLETE 0/1 label for EVERY pathology "
        "in this fixed vocabulary (1 = present, 0 = absent), using these EXACT "
        f"keys and no others: [{listing}]. Return STRICT JSON: "
        '{"labels": {"<pathology>": 0 or 1, ...}} containing all listed keys. '
        "Output only that JSON object."
    )


def step_pii_with_prompt(dataset: Dataset, arm: str, backend: Backend, work_dir: Path) -> StepResult:
    return _pii_query(dataset, arm, backend, work_dir, _PII_WITH_SYSTEM,
                      f"llm+skill-contract:{backend.model}", "pii_with_prompt.json")


def step_label_with_prompt(dataset: Dataset, arm: str, backend: Backend,
                           work_dir: Path) -> StepResult:
    usage = _empty_usage()
    labels: dict[str, dict] = {}
    system = _label_with_system(dataset.vocab)
    t0 = time.perf_counter()
    n = len(dataset.records)
    for i, rec in enumerate(dataset.records, 1):
        uid = rec["study_uid"]
        user = f"<report>\n{rec.get('findings', '')}\n</report>"
        r = backend.chat(system, user)
        telemetry.call_tick("label", arm, i, n, r.ok, r.latency_s,
                            (r.usage or {}).get("total_tokens", 0))
        if r.usage:
            _add_usage(usage, r.usage)
        vec: dict[str, int] = {}
        if r.ok:
            obj = _extract_json(r.text)
            src = obj.get("labels") if isinstance(obj, dict) and isinstance(obj.get("labels"), dict) else obj
            if isinstance(src, dict):
                for name in dataset.vocab:
                    if name in src:
                        try:
                            vec[name] = 1 if int(src[name]) else 0
                        except (TypeError, ValueError):
                            pass
        labels[uid] = vec
    out = work_dir / "labels.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["study_uid"] + dataset.vocab)
        for rec in dataset.records:
            lv = labels.get(rec["study_uid"], {})
            writer.writerow([rec["study_uid"]] + [lv.get(k, "") for k in dataset.vocab])
    return StepResult(
        step="label", arm=arm, executed=True,
        output={"labels": labels, "vocab": dataset.vocab, "schema": "fixed_vector"},
        usage=usage, runtime_s=time.perf_counter() - t0, raw_path=str(out),
        surface=f"llm+skill-contract:{backend.model}",
    )


def step_label_without(dataset: Dataset, arm: str, backend: Backend, work_dir: Path) -> StepResult:
    usage = _empty_usage()
    free_labels: dict[str, dict] = {}
    t0 = time.perf_counter()
    n = len(dataset.records)
    for i, rec in enumerate(dataset.records, 1):
        uid = rec["study_uid"]
        user = f"<report>\n{rec.get('findings', '')}\n</report>"
        r = backend.chat(_LABEL_SYSTEM, user)
        telemetry.call_tick("label", arm, i, n, r.ok, r.latency_s,
                            (r.usage or {}).get("total_tokens", 0))
        if r.usage:
            _add_usage(usage, r.usage)
        if not r.ok:
            free_labels[uid] = {"diseases": None, "parsed": False, "error": r.error}
            continue
        obj = _extract_json(r.text)
        if obj is None or not isinstance(obj.get("diseases"), list):
            free_labels[uid] = {"diseases": None, "parsed": False, "raw": r.text[:200]}
        else:
            free_labels[uid] = {"diseases": [str(x) for x in obj["diseases"]], "parsed": True}
    out = work_dir / "label_without.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(free_labels, f, indent=2, ensure_ascii=False)
    return StepResult(
        step="label", arm=arm, executed=True,
        output={"free_labels": free_labels, "schema": "free_text"},
        usage=usage, runtime_s=time.perf_counter() - t0, raw_path=str(out),
        surface=f"llm:{backend.model}",
    )


def assemble_final_dataset(dataset: Dataset, pii_res: StepResult, label_res: StepResult,
                           out_path: Path) -> Path | None:
    """Merge the with-skill labelling output into the final populated CSV.

    Keyed by ``study_uid``: the selected reports with their assigned disease
    labels. (Step 2 is now the anonymization QC loop over a dedicated leaky
    input, so it does not produce per-sampled-report PII columns here.)
    """
    labels = label_res.output.get("labels", {}) if label_res and label_res.executed else {}
    vocab = label_res.output.get("vocab", dataset.vocab) if label_res else dataset.vocab
    if not labels:
        return None
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    header = ["study_uid", "positive_labels"] + vocab + ["report"]
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for rec in dataset.records:
            uid = rec["study_uid"]
            lv = labels.get(uid, {}) if isinstance(labels.get(uid), dict) else {}
            positives = [k for k in vocab if lv.get(k) == 1]
            writer.writerow(
                [uid, "; ".join(positives)]
                + [lv.get(k, "") for k in vocab]
                + [rec.get("report", "")]
            )
    return out_path


# ---------------------------------------------------------------------------
# Step 2 (replacement): anonymization QC convergence loop.
# WITH skill  = the report-anonymization-qc-loop skill wrapper.
# WITHOUT skill = the raw upstream anonymize_qc_loop.py.
# Both run the SAME underlying loop live (via the anon-vllm env + hosted QC
# backend + Nemotron repair); the skill additionally emits a schema-valid JSON
# summary + evidence pack, which is the measured with-vs-without differentiator.
# ---------------------------------------------------------------------------
@dataclass
class QCLoopConfig:
    input_csv: Path | None = None       # default: skill's leaky fixture
    python: Path | None = None          # default: anon-vllm python (has openai+pandas)
    qc_backend: str = "api"             # hosted GLiNER-PII (no local install needed)
    model: str = "nvidia/nemotron-3-super-120b-a12b"
    max_iters: int = 5
    max_row_attempts: int = 3
    limit: int = 0

    def resolved_input(self) -> Path:
        return Path(self.input_csv) if self.input_csv else paths.QC_LOOP_FIXTURE

    def resolved_python(self) -> Path:
        return Path(self.python) if self.python else paths.ANON_VLLM_PYTHON


def _residual_leak_from_csv(csv_path: Path) -> dict | None:
    """Deterministic residual-PHI check on a loop's anonymized_current.csv.

    Comparable across arms: for each row with a Token_Mapping, flag it if any
    mapped original value >= 3 chars survives verbatim in the anonymized text.
    """
    if not csv_path.exists():
        return None
    n_eval = n_leak = 0
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            mapping = _extract_json(row.get("Token_Mapping", "") or "{}") or {}
            if not isinstance(mapping, dict) or not mapping:
                continue
            n_eval += 1
            anon_lower = (row.get("Anonymized_Rapor", "") or "").lower()
            for orig in mapping.values():
                orig = (str(orig) or "").strip()
                if len(orig) < 3:
                    continue
                if orig.lower() in anon_lower:
                    n_leak += 1
                    break
    return {"n_evaluated": n_eval, "n_leaked": n_leak,
            "leak_rate": round(n_leak / n_eval, 6) if n_eval else 0.0}


def _read_loop_metrics(work_dir: Path) -> tuple[dict, dict]:
    """Return (baseline, final) from a loop's metrics.jsonl (work_dir or loop_out)."""
    for cand in (work_dir / "metrics.jsonl", work_dir / "loop_out" / "metrics.jsonl"):
        if cand.exists():
            lines = [json.loads(ln) for ln in cand.read_text(encoding="utf-8").splitlines()
                     if ln.strip()]
            if lines:
                return lines[0], lines[-1]
    return {}, {}


def _count_needs_review(work_dir: Path) -> int:
    for cand in (work_dir / "needs_review.csv", work_dir / "loop_out" / "needs_review.csv"):
        if cand.exists():
            with cand.open(encoding="utf-8-sig", newline="") as f:
                return max(0, sum(1 for _ in f) - 1)
    return 0


def _run_qcloop_cmd(python: Path, script: Path, cli_args: list[str], label: str) -> tuple[int, str, str, float]:
    cmd = [str(python), str(script)] + cli_args
    telemetry.log(f"  \u2192 anon-qc-loop [{label}] {script.name} starting (live)")
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=str(paths.SKILLS_ROOT), capture_output=True, text=True)
    elapsed = time.perf_counter() - t0
    telemetry.log(f"  \u2190 anon-qc-loop [{label}] rc={proc.returncode} {elapsed:.1f}s")
    return proc.returncode, proc.stdout, proc.stderr, elapsed


def _finalize_qcloop(res: StepResult, work_dir: Path, summary: dict | None,
                     contract_valid: bool) -> StepResult:
    baseline, final = _read_loop_metrics(work_dir)
    residual = _residual_leak_from_csv(work_dir / "anonymized_current.csv")
    n_total = int(final.get("n_total") or baseline.get("n_total") or 0)
    n_pass = int(final.get("n_pass", 0))
    # initial flagged (not-clean) rate from baseline metrics
    base_not_clean = int(baseline.get("n_fail", 0)) + int(baseline.get("n_retired", 0)) \
        + int(baseline.get("n_qc_error", 0))
    metrics = {
        "iterations": int(final.get("iter", summary.get("iterations", 0) if summary else 0)),
        "n_reports": n_total or (summary.get("n_reports", 0) if summary else 0),
        "initial_flagged_rate": round(base_not_clean / n_total, 6) if n_total else None,
        "clean_rate": round(n_pass / n_total, 6) if n_total else (
            summary.get("resolution", {}).get("clean_rate") if summary else None),
        "residual_leak_rate": residual["leak_rate"] if residual else (
            summary.get("residual_leak", {}).get("leak_rate") if summary else None),
        "n_needs_review": _count_needs_review(work_dir),
        "contract_valid": contract_valid,
        "converged": (residual is not None and residual["leak_rate"] == 0.0),
    }
    res.output = {"metrics": metrics, "summary": summary or {}}
    res.executed = True
    return res


def step_anon_qc_loop_with(cfg: QCLoopConfig, arm: str, work_dir: Path) -> StepResult:
    work_dir.mkdir(parents=True, exist_ok=True)
    args = [
        str(cfg.resolved_input()), "--out", str(work_dir), "--mode", "live",
        "--model", cfg.model, "--qc-backend", cfg.qc_backend,
        "--max-iters", str(cfg.max_iters), "--max-row-attempts", str(cfg.max_row_attempts),
        "--mr-rate-root", str(paths.MR_RATE_REPORTS_ROOT),
    ]
    if cfg.limit:
        args += ["--limit", str(cfg.limit)]
    rc, stdout, stderr, elapsed = _run_qcloop_cmd(
        cfg.resolved_python(), paths.QC_LOOP_SKILL_SCRIPT, args, "with-skill")
    res = StepResult(step="anon_qc_loop", arm=arm, runtime_s=elapsed, usage=_empty_usage(),
                     surface=f"skill:report-anonymization-qc-loop(live,{cfg.qc_backend})")
    if rc != 0:
        res.error = f"qc-loop skill exit {rc}: {stderr.strip()[-400:]}"
        return res
    summary = _extract_last_json(stdout)
    # Contract = a parseable summary carrying the skill's declared keys.
    contract_valid = bool(
        summary and summary.get("skill") == "report-anonymization-qc-loop"
        and isinstance(summary.get("resolution"), dict)
        and isinstance(summary.get("residual_leak"), dict)
    )
    res.raw_path = str(work_dir / "anonymized_current.csv")
    return _finalize_qcloop(res, work_dir, summary, contract_valid)


def step_anon_qc_loop_without(cfg: QCLoopConfig, arm: str, work_dir: Path) -> StepResult:
    work_dir.mkdir(parents=True, exist_ok=True)
    args = [
        "--input_file", str(cfg.resolved_input()), "--output_dir", str(work_dir),
        "--id_col", "UID", "--text_col", "Anonymized_Rapor",
        "--source_col", "report", "--mapping_col", "Token_Mapping",
        "--qc_backend", cfg.qc_backend, "--anon_model", cfg.model,
        "--max_iters", str(cfg.max_iters), "--max_row_attempts", str(cfg.max_row_attempts),
    ]
    if cfg.limit:
        args += ["--limit", str(cfg.limit)]
    rc, stdout, stderr, elapsed = _run_qcloop_cmd(
        cfg.resolved_python(), paths.UPSTREAM_QC_LOOP, args, "without-skill")
    res = StepResult(step="anon_qc_loop", arm=arm, runtime_s=elapsed, usage=_empty_usage(),
                     surface=f"upstream:anonymize_qc_loop.py(live,{cfg.qc_backend})")
    if rc != 0:
        res.error = f"upstream qc-loop exit {rc}: {stderr.strip()[-400:]}"
        return res
    # The raw upstream prints a human table, not a schema-valid JSON summary.
    contract_valid = False
    res.raw_path = str(work_dir / "anonymized_current.csv")
    return _finalize_qcloop(res, work_dir, None, contract_valid)


# ---------------------------------------------------------------------------
# Pipeline driver
# ---------------------------------------------------------------------------
def run_pipeline(
    dataset: Dataset,
    arm: str,
    backend: Backend,
    work_dir: Path,
    mode: str = "mock",
    model: str | None = None,
    cuda: str | None = None,
    arm_style: str = "tool",
    qcloop_cfg: "QCLoopConfig | None" = None,
) -> dict[str, StepResult]:
    """Run all three steps for one arm.

    ``arm`` in {"with", "without"}.

    * Step 1 ``select`` -- shared seeded fixture.
    * Step 2 ``pii`` -- the anonymization QC convergence loop: WITH = the
      ``report-anonymization-qc-loop`` skill, WITHOUT = the raw upstream
      ``anonymize_qc_loop.py``. Fixed skill-vs-upstream comparison (independent
      of ``arm_style``); both run live via the anon-vllm env.
    * Step 3 ``label`` -- ``arm_style`` controls the with-skill arm: ``tool``
      runs the skill script; ``prompt`` gives the same backend the skill's
      contract (same-model control).
    """
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    cfg = qcloop_cfg or QCLoopConfig()
    results: dict[str, StepResult] = {}
    results["select"] = step_select(dataset, arm, work_dir / "select")

    # Step 2: anonymization QC loop (skill vs upstream script).
    if arm == "with":
        results["pii"] = step_anon_qc_loop_with(cfg, arm, work_dir / "pii")
    else:
        results["pii"] = step_anon_qc_loop_without(cfg, arm, work_dir / "pii")

    # Step 3: disease labelling.
    if arm == "with" and arm_style == "tool":
        results["label"] = step_label_with(dataset, arm, work_dir / "label", mode, model, cuda)
    elif arm == "with" and arm_style == "prompt":
        results["label"] = step_label_with_prompt(dataset, arm, backend, work_dir / "label")
    else:
        results["label"] = step_label_without(dataset, arm, backend, work_dir / "label")
    return results
