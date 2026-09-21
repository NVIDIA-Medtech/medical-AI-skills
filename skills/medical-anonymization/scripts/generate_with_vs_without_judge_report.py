#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Generate rad-style with-vs-without report for medical-anonymization (reports lane).

Runs (or reuses) with-skill vs without-skill radiology report anonymization, scores
residual PHI with an LLM judge + deterministic scan, computes a paired sign test,
and writes Markdown + HTML dashboard (same template as report-anonymization eval).

Usage::

    python generate_with_vs_without_judge_report.py \\
      --output-md ../../docs/anonymization-with-vs-without-medical-local.md
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
CATALOG_ROOT = SKILL_ROOT.parents[1]  # medical-AI-skills
sys.path.insert(0, str(CATALOG_ROOT))

from tools.curation_eval.anon_experiment import (  # noqa: E402
    _load_reports,
    _ordered_uids,
    compute_paired_row,
    llm_judge_escapes,
    score_residual_phi,
)
from tools.curation_eval.backends import make_backend, probe  # noqa: E402
from tools.curation_eval.runner import sign_test  # noqa: E402

PYTHON = Path("/home/marc/.conda/envs/reports-openai/bin/python")
WITH_ENTRY = SCRIPT_DIR / "anonymize_medical_data.py"
WITHOUT_ENTRY = SCRIPT_DIR / "without_skill_baseline.py"
PROVIDERS = SKILL_ROOT / "references" / "providers.local-phi.yaml"
MODELS = SKILL_ROOT / "references" / "models.local-phi.yaml"
DEFAULT_INPUT = SKILL_ROOT / "fixtures" / "batch00_reports_w_PHI.csv"
DEFAULT_EVAL_JSON = SKILL_ROOT / "docs" / "with-vs-without-results.json"
DEFAULT_OUT_MD = CATALOG_ROOT / "docs" / "anonymization-with-vs-without-medical-local.md"
ID_COL = "study_uid"
TEXT_COL = "report_w_PHI"
BACKEND_NAME = "local-phi"


@dataclass
class ArmJudgeResult:
    arm: str
    output_csv: Path
    exec_seconds: float
    judge_model: str
    judge_out_phi_total: int = 0
    judge_rows_clean: int = 0
    judge_rows_scored: int = 0
    judge_row_phi: list[dict[str, Any]] = field(default_factory=list)
    judge_usage: dict[str, Any] = field(default_factory=dict)
    regex_total: int = 0
    regex_rows_clean: int = 0
    regex_row_counts: list[dict[str, Any]] = field(default_factory=list)
    input_phi_baseline: int = 0


def run_cmd(cmd: list[str], timeout: int = 7200) -> tuple[int, float]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, round(time.perf_counter() - t0, 2)


def run_reports_arm(arm: str, input_csv: Path, out_dir: Path, *, full: bool) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / "anonymized_data.csv"
    if arm == "with":
        cmd = [
            str(PYTHON), str(WITH_ENTRY), str(input_csv),
            "--output-dir", str(out_dir),
            "--id-column", ID_COL,
            "--text-columns", TEXT_COL,
            "--model-providers", str(PROVIDERS),
            "--model-configs", str(MODELS),
        ]
        if full:
            cmd.append("--full")
        else:
            cmd += ["--num-records", "20"]
    else:
        cmd = [
            str(PYTHON), str(WITHOUT_ENTRY), str(input_csv),
            "--output-dir", str(out_dir),
            "--text-column", TEXT_COL,
            "--id-column", ID_COL,
            "--model-providers", str(PROVIDERS),
            "--model-configs", str(MODELS),
        ]
        if not full:
            cmd += ["--num-records", "20"]
    rc, _ = run_cmd(cmd)
    if rc != 0 or not out_csv.exists():
        raise RuntimeError(f"{arm} arm failed rc={rc}; expected {out_csv}")
    return out_csv


def judge_arm_csv(
    arm: str,
    csv_path: Path,
    source_csv: Path,
    judge_backend,
    exec_seconds: float,
) -> ArmJudgeResult:
    texts, _ = _load_reports(csv_path, text_hint=TEXT_COL)
    uids = _ordered_uids(source_csv)
    in_texts, _ = _load_reports(source_csv, text_hint=TEXT_COL)

    res = ArmJudgeResult(
        arm=arm,
        output_csv=csv_path,
        exec_seconds=exec_seconds,
        judge_model=judge_backend.model,
    )
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "n_calls": 0}
    regex_rows: list[dict[str, Any]] = []

    for i, text in enumerate(texts):
        uid = uids[i] if i < len(uids) else str(i)
        n, examples, u = llm_judge_escapes(judge_backend, text)
        for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
            usage[k] += int((u or {}).get(k, 0) or 0)
        usage["n_calls"] += 1
        if n is None:
            res.judge_row_phi.append({"uid": uid, "n": -1, "examples": []})
        else:
            res.judge_rows_scored += 1
            res.judge_out_phi_total += n
            if n == 0:
                res.judge_rows_clean += 1
            res.judge_row_phi.append({"uid": uid, "n": n, "examples": examples})

        in_phi, _, _ = score_residual_phi(in_texts[i] if i < len(in_texts) else "")
        res.input_phi_baseline += in_phi
        rx_n, _, rx_ex = score_residual_phi(text)
        res.regex_total += rx_n
        if rx_n == 0:
            res.regex_rows_clean += 1
        regex_rows.append({"uid": uid, "n": rx_n, "examples": rx_ex})

    res.judge_usage = usage
    res.regex_row_counts = regex_rows
    return res


def _example_values(rows: list[dict], limit: int = 6) -> str:
    seen: list[str] = []
    for row in rows:
        for ex in row.get("examples") or []:
            if isinstance(ex, dict):
                val = str(ex.get("value", ""))
            else:
                val = str(ex)
            if val and val not in seen:
                seen.append(val)
            if len(seen) >= limit:
                break
        if len(seen) >= limit:
            break
    return ", ".join(seen) if seen else "none"


def _row_escape_values(attempts: list[dict], key: str, idx: int) -> str:
    vals: list[str] = []
    for att in attempts:
        rows = att.get(key) or []
        if idx >= len(rows):
            continue
        row = rows[idx]
        for ex in row.get("examples") or []:
            if isinstance(ex, dict):
                v = str(ex.get("value", ""))
            else:
                v = str(ex)
            if v:
                vals.append(v)
    return ", ".join(dict.fromkeys(vals)) if vals else "—"


def load_capability_summary(eval_json: Path | None) -> dict[str, Any]:
    if not eval_json or not eval_json.exists():
        return {}
    return json.loads(eval_json.read_text(encoding="utf-8"))


def render_markdown(
    *,
    n_reports: int,
    with_arm: ArmJudgeResult,
    without_arm: ArmJudgeResult,
    paired: dict,
    capability: dict[str, Any],
    judge_reachable: bool,
    generated: str,
) -> str:
    attempts = [
        {
            "backend": BACKEND_NAME,
            "arm": "with",
            "repeat": 1,
            "judge_row_phi": with_arm.judge_row_phi,
            "judge_out_phi_total": with_arm.judge_out_phi_total,
            "judge_rows_clean": with_arm.judge_rows_clean,
            "judge_rows_scored": with_arm.judge_rows_scored,
            "judge_model": with_arm.judge_model,
            "exec_seconds": with_arm.exec_seconds,
        },
        {
            "backend": BACKEND_NAME,
            "arm": "without",
            "repeat": 1,
            "judge_row_phi": without_arm.judge_row_phi,
            "judge_out_phi_total": without_arm.judge_out_phi_total,
            "judge_rows_clean": without_arm.judge_rows_clean,
            "judge_rows_scored": without_arm.judge_rows_scored,
            "judge_model": without_arm.judge_model,
            "exec_seconds": without_arm.exec_seconds,
        },
    ]
    ov = paired.get("__overall__", {})

    w_pass_run = 1 if with_arm.judge_out_phi_total == 0 and with_arm.judge_rows_scored else 0
    o_pass_run = 1 if without_arm.judge_out_phi_total == 0 and without_arm.judge_rows_scored else 0

    ratio = ""
    if with_arm.judge_out_phi_total and without_arm.judge_out_phi_total > with_arm.judge_out_phi_total:
        ratio = f" (~{without_arm.judge_out_phi_total / with_arm.judge_out_phi_total:.0f}x fewer items with the skill)"

    lines = [
        "# Medical Anonymization — With-vs-Without Skill Experiment",
        "",
        f"Generated: {generated}.",
        "Protocol: scripted pipeline comparison (not agent command generation). "
        "NeMo inner anonymizer: local GLiNER + `medgemma:27b`. Judge: local `medgemma:27b`.",
        "",
        "This report evaluates the **medical-anonymization** skill on the radiology-reports "
        "lane: `anonymize_medical_data.py` + `SKILL.md` vs upstream NeMo README baseline "
        "(`without_skill_baseline.py`). Both arms execute the real NeMo pipeline on the same "
        "staged CSV; they differ in policy (strict entity labels, redact template) and output contract.",
        "",
        "**Pass criterion: an arm passes only if it produced anonymized output AND an LLM judge "
        "found ZERO residual PHI escapes across all rows — any single escape is a fail.**",
        "",
        "This is an engineering reproducibility protocol. It is not a clinical, diagnostic, "
        "or regulatory claim.",
        "",
        "## Evaluation task",
        "",
        f"- **Dataset:** {n_reports} radiology reports from "
        f"`skills/medical-anonymization/fixtures/batch00_reports_w_PHI.csv`. "
        f"Reports: **{n_reports}**.",
        f"- **Backend:** 1 (`{BACKEND_NAME}`: local GLiNER @ 172.20.0.1:8001, Ollama medgemma:27b).",
        "- **With-skill entrypoint:** `skills/medical-anonymization/scripts/anonymize_medical_data.py`",
        "- **Without-skill entrypoint:** `skills/medical-anonymization/scripts/without_skill_baseline.py`",
        f"- **Judge reachable:** {'yes' if judge_reachable else 'no'} (`{with_arm.judge_model}`)",
        "",
        "## Current aggregate result",
        "",
        "### Result by arm — redaction quality, pass rate, and timing",
        "",
        "One row per **arm**. **Pass = produced output AND zero residual PHI escapes across all "
        f"reports (any escape is a fail).** Judge: `{with_arm.judge_model}`.",
        "",
        "| Arm | Backend-runs producing output | Passes with 0 PHI escapes | "
        "Residual PHI escapes (items) | Report-runs fully redacted (report x backend) | "
        "Total exec (s) | Avg s/report |",
        "|---|:--:|:--:|--:|:--:|--:|--:|",
        f"| **With skill (SKILL.md)** | 1/1 | **{w_pass_run}/1 ({100 * w_pass_run}%)** | "
        f"**{with_arm.judge_out_phi_total}** | **{with_arm.judge_rows_clean}/{with_arm.judge_rows_scored}** | "
        f"{with_arm.exec_seconds:.1f} | "
        f"{with_arm.exec_seconds / max(1, with_arm.judge_rows_scored):.1f} |",
        f"| Without skill (upstream README) | 1/1 | {o_pass_run}/1 ({100 * o_pass_run}%) | "
        f"{without_arm.judge_out_phi_total} | "
        f"{without_arm.judge_rows_clean}/{without_arm.judge_rows_scored} | "
        f"{without_arm.exec_seconds:.1f} | "
        f"{without_arm.exec_seconds / max(1, without_arm.judge_rows_scored):.1f} |",
        "",
        "### Headline — PHI redaction result by arm",
        "",
        f"| Arm | Backend-runs producing output | Residual PHI escapes (items) | "
        f"Report-runs fully redacted (report x backend) | Backend-runs with 0 escapes |",
        f"|---|:--:|--:|:--:|:--:|",
        f"| **With skill (SKILL.md)** | 1/1 | **{with_arm.judge_out_phi_total}** | "
        f"**{with_arm.judge_rows_clean}/{with_arm.judge_rows_scored}** | **{w_pass_run}/1** |",
        f"| Without skill (upstream README) | 1/1 | {without_arm.judge_out_phi_total} | "
        f"{without_arm.judge_rows_clean}/{without_arm.judge_rows_scored} | {o_pass_run}/1 |",
        "",
        "### Overall result (dataset level) — pass = produced output with zero PHI escapes",
        "",
        "| Arm | Passes with 0 PHI escapes |",
        "|---|---:|",
        f"| With skill (SKILL.md) | {w_pass_run}/1 ({100 * w_pass_run}%) |",
        f"| Without skill (upstream README) | {o_pass_run}/1 ({100 * o_pass_run}%) |",
        "",
        "### Paired with-vs-without (exact one-sided sign test, report-row level)",
        "",
        "Each **pair** is one report row (`study_uid`). **Skill wins** if with-skill had strictly "
        "fewer residual PHI escapes; **Without wins** if without-skill had fewer; **Tie** if equal.",
        "",
        "| Scope | Report pairs | Skill wins | Without wins | Ties | Sign-test p |",
        "|---|---:|---:|---:|---:|---:|",
        f"| {BACKEND_NAME} | {paired.get(BACKEND_NAME, {}).get('pairs', ov.get('pairs', 0))} | "
        f"{paired.get(BACKEND_NAME, {}).get('skill_wins', 0)} | "
        f"{paired.get(BACKEND_NAME, {}).get('without_wins', 0)} | "
        f"{paired.get(BACKEND_NAME, {}).get('ties', 0)} | "
        f"{paired.get(BACKEND_NAME, {}).get('sign_test_p', 'n/a')} |",
        f"| **overall** | {ov.get('pairs', 0)} | {ov.get('skill_wins', 0)} | "
        f"{ov.get('without_wins', 0)} | {ov.get('ties', 0)} | {ov.get('sign_test_p', 'n/a')} |",
        "",
        "### Per-backend, per-arm report-row pass counts",
        "",
        "| Backend/arm | Report-rows fully redacted | Mean exec s |",
        "|---|---:|---:|",
        f"| {BACKEND_NAME}/with | {with_arm.judge_rows_clean}/{with_arm.judge_rows_scored} | "
        f"{with_arm.exec_seconds:.1f} |",
        f"| {BACKEND_NAME}/without | {without_arm.judge_rows_clean}/{without_arm.judge_rows_scored} | "
        f"{without_arm.exec_seconds:.1f} |",
        "",
        "## PHI redaction (row-level)",
        "",
        f"### LLM-as-judge residual escapes (primary) — judge model `{with_arm.judge_model}`",
        "",
        "An independent model re-read each anonymized report and flagged residual PHI — real "
        "identifying values still present as plain text rather than a `[bracketed]` placeholder.",
        "",
        "| Backend / arm | Reports fully redacted | Residual PHI escapes (items) | Example escaped values |",
        "|---|:--:|--:|---|",
        f"| {BACKEND_NAME}/with | {with_arm.judge_rows_clean}/{with_arm.judge_rows_scored} | "
        f"{with_arm.judge_out_phi_total} | {_example_values(with_arm.judge_row_phi)} |",
        f"| {BACKEND_NAME}/without | {without_arm.judge_rows_clean}/{without_arm.judge_rows_scored} | "
        f"{without_arm.judge_out_phi_total} | {_example_values(without_arm.judge_row_phi)} |",
        "",
        "#### Per-report residual PHI escape counts — one row per dataset report (0 = fully redacted)",
        "",
        "Each cell is the number of residual PHI items the judge found in that report.",
        "",
        f"| study_uid (report) | {BACKEND_NAME}/with (items) | {BACKEND_NAME}/without (items) | Escaped PHI values |",
        f"|---|---:|---:|---|",
    ]

    nrows = max(len(with_arm.judge_row_phi), len(without_arm.judge_row_phi))
    for i in range(nrows):
        w_row = with_arm.judge_row_phi[i] if i < len(with_arm.judge_row_phi) else {"uid": "?", "n": "—"}
        o_row = without_arm.judge_row_phi[i] if i < len(without_arm.judge_row_phi) else {"uid": "?", "n": "—"}
        uid = w_row.get("uid") or o_row.get("uid")
        vals = _row_escape_values(
            [{"judge_row_phi": with_arm.judge_row_phi}, {"judge_row_phi": without_arm.judge_row_phi}],
            "judge_row_phi",
            i,
        )
        lines.append(f"| `{uid}` | {w_row.get('n', '—')} | {o_row.get('n', '—')} | {vals} |")

    lines.extend([
        "",
        "### Deterministic scan (cross-check)",
        "",
        "Conservative regex scan for residual PHI signals (dates, long IDs, titled names, phones), "
        "excluding `[PLACEHOLDER]` tokens.",
        "",
        "| Backend/arm | Rows fully redacted | Residual PHI escapes | Baseline PHI in input |",
        "|---|---:|---:|---:|",
        f"| {BACKEND_NAME}/with | {with_arm.regex_rows_clean}/{len(with_arm.regex_row_counts)} | "
        f"{with_arm.regex_total} | {with_arm.input_phi_baseline} |",
        f"| {BACKEND_NAME}/without | {without_arm.regex_rows_clean}/{len(without_arm.regex_row_counts)} | "
        f"{without_arm.regex_total} | {without_arm.input_phi_baseline} |",
        "",
        "## Structured + DICOM capability (medical-anonymization only)",
        "",
        "The rad-reports experiment above isolates **text redaction quality**. The "
        "medical-anonymization skill additionally provides deterministic structured-field policy "
        "and DICOM metadata JSONL — gaps the without-skill baseline cannot cover.",
        "",
    ])

    if capability:
        summary = capability.get("summary", {})
        lines.extend([
            "| Lane | With skill (s) | Without skill (s) | Expected without gap |",
            "|------|---------------:|------------------:|----------------------|",
        ])
        per_task = summary.get("per_task_seconds", {})
        expected = capability.get("expected_without_failures", {})
        for task in ("dicom-metadata", "ehr", "reports"):
            secs = per_task.get(task, {})
            gap = ", ".join(expected.get(task, [])) or "—"
            lines.append(
                f"| {task} | {secs.get('with', 'n/a')} | {secs.get('without', 'n/a')} | {gap} |"
            )
        lines.append("")

    lines.extend([
        "## Timing",
        "",
        f"- With-skill pipeline: **{with_arm.exec_seconds:.1f}s** "
        f"({with_arm.exec_seconds / max(1, with_arm.judge_rows_scored):.1f}s/report)",
        f"- Without-skill pipeline: **{without_arm.exec_seconds:.1f}s** "
        f"({without_arm.exec_seconds / max(1, without_arm.judge_rows_scored):.1f}s/report)",
        f"- Judge calls: {with_arm.judge_usage.get('n_calls', 0) + without_arm.judge_usage.get('n_calls', 0)} "
        f"({with_arm.judge_usage.get('total_tokens', 0) + without_arm.judge_usage.get('total_tokens', 0)} tokens)",
        "",
        "## Findings",
        "",
        f"- **Redaction quality (reports lane):** with-skill left **{with_arm.judge_out_phi_total}** "
        f"residual PHI items and fully redacted **{with_arm.judge_rows_clean}/{with_arm.judge_rows_scored}** "
        f"report-runs; without-skill left **{without_arm.judge_out_phi_total}** items and fully redacted "
        f"**{without_arm.judge_rows_clean}/{without_arm.judge_rows_scored}** report-runs{ratio}.",
        f"- **Paired sign test:** {ov.get('skill_wins', 0)} skill-wins, {ov.get('without_wins', 0)} "
        f"without-wins, {ov.get('ties', 0)} ties (p = {ov.get('sign_test_p', 'n/a')}).",
        "- **Capability gap:** without-skill has no DICOM policy, no structured MRN hashing, no "
        "nested/KV JSONL or audit trail (see structured + DICOM section).",
        "- `Pass` = produced output AND zero LLM-judged residual PHI escapes (any escape is a fail).",
        "",
        "## Reproduce",
        "",
        "```bash",
        f"{PYTHON} skills/medical-anonymization/scripts/generate_with_vs_without_judge_report.py \\",
        f"  --output-md docs/anonymization-with-vs-without-medical-local.md",
        "```",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", default=str(DEFAULT_INPUT))
    p.add_argument("--work-dir", default="/tmp/medical_anon_judge_report")
    p.add_argument("--output-md", default=str(DEFAULT_OUT_MD))
    p.add_argument("--capability-json", default=str(DEFAULT_EVAL_JSON))
    p.add_argument("--judge", default="ollama-medgemma")
    p.add_argument("--preview-only", action="store_true",
                   help="NeMo preview on first rows only (default: full dataset)")
    p.add_argument("--skip-run", action="store_true",
                   help="Reuse existing anonymized CSVs in work-dir")
    args = p.parse_args()

    input_csv = Path(args.input)
    work_dir = Path(args.work_dir)
    out_md = Path(args.output_md)
    n_reports = len(_ordered_uids(input_csv))

    with_dir = work_dir / "with" / "reports"
    without_dir = work_dir / "without" / "reports"

    if args.skip_run:
        with_csv = with_dir / "anonymized_data.csv"
        without_csv = without_dir / "anonymized_data.csv"
        if not with_csv.exists() or not without_csv.exists():
            raise SystemExit(f"missing CSVs under {work_dir}; drop --skip-run")
        timing_path = work_dir / "pipeline_timing.json"
        if timing_path.exists():
            timing = json.loads(timing_path.read_text(encoding="utf-8"))
            with_secs = float(timing.get("with_seconds", 0))
            without_secs = float(timing.get("without_seconds", 0))
        else:
            with_secs = without_secs = 0.0
    else:
        full = not args.preview_only
        print(f"Running with-skill on {n_reports} reports (full={full})...")
        t0 = time.perf_counter()
        with_csv = run_reports_arm("with", input_csv, with_dir, full=full)
        with_secs = time.perf_counter() - t0
        print(f"Running without-skill...")
        t0 = time.perf_counter()
        without_csv = run_reports_arm("without", input_csv, without_dir, full=full)
        without_secs = time.perf_counter() - t0
        (work_dir / "pipeline_timing.json").write_text(
            json.dumps({"with_seconds": round(with_secs, 2), "without_seconds": round(without_secs, 2)}),
            encoding="utf-8",
        )

    judge = make_backend(args.judge)
    ping = probe(judge)
    print(f"Judge {judge.model} reachable={ping.ok}")

    print("Judging with-skill output...")
    with_arm = judge_arm_csv("with", with_csv, input_csv, judge, with_secs)
    print("Judging without-skill output...")
    without_arm = judge_arm_csv("without", without_csv, input_csv, judge, without_secs)

    attempts = [
        {"backend": BACKEND_NAME, "arm": "with", "repeat": 1, "judge_row_phi": with_arm.judge_row_phi},
        {"backend": BACKEND_NAME, "arm": "without", "repeat": 1, "judge_row_phi": without_arm.judge_row_phi},
    ]
    paired = compute_paired_row(attempts)

    capability = load_capability_summary(Path(args.capability_json) if args.capability_json else None)
    generated = datetime.now().strftime("%Y-%m-%d %H:%M (local)")
    md = render_markdown(
        n_reports=n_reports,
        with_arm=with_arm,
        without_arm=without_arm,
        paired=paired,
        capability=capability,
        judge_reachable=ping.ok,
        generated=generated,
    )

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(md, encoding="utf-8")
    print(f"Wrote {out_md}")

    from tools.curation_eval.md_to_dashboard import convert  # noqa: E402

    out_html = convert(out_md)
    html = out_html.read_text(encoding="utf-8")
    html = html.replace(
        "<title>Report Anonymization — With-vs-Without Dashboard</title>",
        "<title>Medical Anonymization — With-vs-Without Dashboard</title>",
    ).replace(
        "<h1>Report Anonymization — With-vs-Without Skill Dashboard</h1>",
        "<h1>Medical Anonymization — With-vs-Without Skill Dashboard</h1>",
    )
    out_html.write_text(html, encoding="utf-8")
    print(f"Wrote {out_html}")

    summary = {
        "with_escapes": with_arm.judge_out_phi_total,
        "without_escapes": without_arm.judge_out_phi_total,
        "with_clean": f"{with_arm.judge_rows_clean}/{with_arm.judge_rows_scored}",
        "without_clean": f"{without_arm.judge_rows_clean}/{without_arm.judge_rows_scored}",
        "sign_test_p": paired.get("__overall__", {}).get("sign_test_p"),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
