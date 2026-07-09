# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Render a markdown report for a curation with-vs-without study.

Structure mirrors ``docs/with-vs-without-skill-experiment.md``: protocol,
aggregate result, per-step success, paired sign test, token profiling, a
quality layer, the five-tier ladder, findings, and reproduce commands.
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path

from . import paths
from .backends import LIVE_BACKENDS
from .grading import TIER_LADDER
from .tasks import _LABEL_SYSTEM, _label_with_system


def _pct(n: int, d: int) -> str:
    return f"{(100.0 * n / d):.0f}%" if d else "n/a"


def _fmt(x, nd: int = 4) -> str:
    if x is None:
        return "n/a"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def _resolve(p: str) -> Path:
    """Resolve a stored (possibly skills-root-relative) path to an existing file."""
    pp = Path(p)
    if pp.exists():
        return pp
    alt = paths.SKILLS_ROOT / p
    return alt if alt.exists() else pp


def _sample_rows_table(study: dict, max_rows: int = 10) -> list[str]:
    """Render the actual sampled reports with with-skill outputs vs ground truth."""
    ds = study["meta"]["dataset"]
    gt_path = ds.get("ground_truth")
    if not gt_path:
        return []
    try:
        with _resolve(gt_path).open(encoding="utf-8") as f:
            gt = json.load(f)
    except (OSError, ValueError):
        return []
    reports = gt.get("reports", {})
    vocab = gt.get("vocab", [])

    skill_pii: dict[str, str] = {}
    skill_labels: dict[str, str] = {}
    labeled = ds.get("labeled_csv")
    if labeled:
        try:
            with _resolve(labeled).open(encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    uid = (row.get("study_uid") or "").strip()
                    skill_pii[uid] = row.get("pii_status", "") or ""
                    skill_labels[uid] = row.get("positive_labels", "") or ""
        except OSError:
            pass

    order = (list(skill_labels.keys()) or list(reports.keys()))[:max_rows]
    if not order:
        return []

    lines = ["### Sample of the selected reports (step 3 labelling)", ""]
    lines.append(
        "The sampled reports with the with-skill assigned disease labels against "
        "the gold `mrrate_labels.csv` vectors (`\u2014` = no positive label). Step 2 "
        "(the anonymization QC loop) runs on a separate leaky input, so it is not "
        "shown per-report here."
    )
    lines.append("")
    have_skill = bool(skill_labels)
    if have_skill:
        lines.append("| # | study_uid | Disease labels \u2014 skill | Disease labels "
                     "\u2014 gold |")
        lines.append("|--:|---|---|---|")
    else:
        lines.append("| # | study_uid | Disease labels \u2014 gold |")
        lines.append("|--:|---|---|")
    for i, uid in enumerate(order, 1):
        r = reports.get(uid, {})
        gold_vec = r.get("gold_labels_vocab") or {}
        gold_pos = [k for k in vocab if int(gold_vec.get(k, 0)) == 1]
        gold_str = "; ".join(gold_pos) if gold_pos else "\u2014"
        if have_skill:
            skill_str = skill_labels.get(uid) or "\u2014"
            lines.append(f"| {i} | `{uid}` | {skill_str} | {gold_str} |")
        else:
            lines.append(f"| {i} | `{uid}` | {gold_str} |")
    lines.append("")
    return lines


def _methods_section(study: dict) -> list[str]:
    """Detailed, reproducible Methods: step 2 = anon-QC loop, step 3 = labelling."""
    meta = study["meta"]
    ds = meta["dataset"]
    vocab = ds.get("vocab", [])
    arm_style = meta.get("arm_style", "tool")
    mode = meta.get("mode", "mock")
    backends = meta.get("backends", [])

    L: list[str] = []
    a = L.append
    a("## Methods (detailed)")
    a("")
    a("Engineering reproducibility protocol (not a clinical/regulatory claim). "
      f"This report used **arm-style = `{arm_style}`** (controls step 3) and "
      f"**skill mode = `{mode}`** (step-3 tool arm). **Step 2 always runs live** as "
      "published-skill-script vs raw-upstream-script.")
    a("")

    a("### M1. Models and transport")
    a("")
    a("| Backend (step 3) | Kind | Model id | Endpoint |")
    a("|---|---|---|---|")
    for b in backends:
        if b["kind"] == "mock":
            base = "in-process (deterministic, no network)"
        else:
            base = LIVE_BACKENDS.get(b["name"], {}).get("base_url", "(inline spec)")
        a(f"| {b['name']} | {b['kind']} | `{b['model']}` | {base} |")
    a("")
    a("Step-3 LLM calls send **only** `model` + `messages` (service defaults; no "
      "sampling knobs), one call per report per arm; provider token usage is "
      "recorded verbatim. **Step 2** runs the loop as a subprocess under the "
      "`anon-vllm` env (needs `openai`+`pandas`), using a hosted **GLiNER-PII** QC "
      "backend and a **Nemotron** repair model over the NVIDIA API. The study is "
      f"single-shot / no-repair, repeated **{meta.get('repeats')}×** per "
      "backend/arm; the loop itself iterates internally to convergence.")
    a("")

    a("### M2. Inputs")
    a("")
    a(f"- **Steps 1 & 3 (select, label):** {ds['n']} reports sampled with seed "
      f"`{ds['seed']}` from `{ds.get('source_reports_dir')}`, restricted to "
      f"gold-labelled study_uids; gold from `{ds.get('source_labels_csv')}`.")
    a(f"- **Fixed pathology vocabulary ({len(vocab)} labels):** {', '.join(vocab)}.")
    a("- **Step 2 (anon-QC loop):** a CSV of already-anonymized reports carrying "
      "*residual* leaks plus the original source text and token mapping "
      "(`UID, Anonymized_Rapor, report, Token_Mapping`). Default input is the "
      "skill's committed fixture `sample_anonymized_with_leaks.csv`. (The sampled "
      "reports have no residual-leak/source/mapping structure, so step 2 uses this "
      "dedicated leaky input rather than the sampled set.)")
    a("")

    a("### M3. Step 2 — anonymization QC loop (skill vs upstream script)")
    a("")
    a("Both arms run the same anonymize\u2194QC repair loop: QC-scan the anonymized "
      "text for residual identifiers, re-anonymize the ORIGINAL source of every "
      "flagged row with the missed identifiers injected as hints, re-QC just those "
      "rows, and iterate until clean / a row hits its attempt cap (retired to "
      "`needs_review.csv`) / `--max-iters`.")
    a("")
    a("**With skill** (published wrapper):")
    a("")
    a("```bash")
    a("<anon-vllm-python> skills/report-anonymization-qc-loop/scripts/"
      "run_anonymization_qc_loop.py \\")
    a("  <leaky.csv> --out <dir> --mode live --model nvidia/nemotron-3-super-120b-a12b \\")
    a("  --qc-backend api --max-iters 5 --max-row-attempts 3 --mr-rate-root <reports_preprocessing>")
    a("```")
    a("")
    a("**Without skill** (raw upstream script):")
    a("")
    a("```bash")
    a("<anon-vllm-python> .../01_anonymization/anonymize_qc_loop.py \\")
    a("  --input_file <leaky.csv> --output_dir <dir> --id_col UID --text_col Anonymized_Rapor \\")
    a("  --source_col report --mapping_col Token_Mapping --qc_backend api \\")
    a("  --anon_model nvidia/nemotron-3-super-120b-a12b --max_iters 5 --max_row_attempts 3")
    a("```")
    a("")
    a("Crucially, the skill's `--mode live` **subprocesses that same upstream "
      "script**, so both arms produce the same converged anonymization. The "
      "measured difference is the **contract**: the skill emits a schema-valid JSON "
      "summary (`iterations`, `resolution.clean_rate`, `residual_leak`, "
      "`token_format`, `needs_review`) validated against its "
      "`validators/output_schema.json`, plus a normalized evidence pack; the raw "
      "script prints a human table and leaves raw CSVs (`anonymized_current.csv`, "
      "`metrics.jsonl`, `needs_review.csv`) that must be interpreted and wired by "
      "hand. Convergence is verified identically for both arms by a deterministic "
      "residual-leak check on `anonymized_current.csv` (no mapped original value "
      "\u2265 3 chars survives verbatim).")
    a("")

    a("### M4. Step 3 — disease labelling")
    a("")
    used_a = " **(used by this report)**" if arm_style == "prompt" else ""
    used_b = " **(used by this report)**" if arm_style == "tool" else ""
    a(f"**arm-style `prompt`{used_a}** — both arms call the same backend on the "
      "report `findings` (wrapped in `<report>…</report>`); only the system prompt "
      "differs.")
    a("")
    a("Without skill:")
    a("")
    a("```text")
    a(_LABEL_SYSTEM)
    a("```")
    a("")
    a("With skill (the fixed vocabulary is injected verbatim):")
    a("")
    a("```text")
    a(_label_with_system(vocab))
    a("```")
    a("")
    a("The with-skill response is parsed into a fixed 0/1 vector over the "
      "vocabulary; the without-skill response is a free-text disease list that "
      "cannot satisfy the fixed schema.")
    a("")
    a(f"**arm-style `tool`{used_b}** — with skill runs the classification skill "
      "script instead of a prompt:")
    a("")
    a("```bash")
    a("python skills/report-pathology-classification/scripts/"
      "run_report_pathology_classification.py \\")
    a("  <evaluation_dataset.csv> --out <dir> --mode <mock|live> \\")
    a("  --id-col study_uid --text-col findings")
    a("```")
    a("")

    a("### M5. Response parsing (step 3)")
    a("")
    a("Model responses are parsed leniently: a leading `<think>…</think>` block is "
      "stripped, a fenced JSON code block is unwrapped if present, and the first "
      "balanced `{…}` object is JSON-parsed. A response yielding no valid object "
      "(or wrong keys) is scored as a contract failure for that report.")
    a("")

    a("### M6. Grading (deterministic)")
    a("")
    a("- **Step 1 select** — pass = tier 5 (exact count; every uid in the corpus "
      "with gold labels; non-empty text).")
    a("- **Step 2 anon-QC loop** — pass = **converged** (deterministic residual "
      "leak rate = 0 on `anonymized_current.csv`) **AND** a schema-valid summary "
      "was emitted (the skill contract). The raw upstream arm converges (same loop) "
      "but emits no validated summary, so it does not pass the contract. Reported: "
      "iterations, initial-flagged rate, clean-rate, residual-leak rate, "
      "needs-review count, contract-valid.")
    a("- **Step 3 label** — pass = a complete 0/1 vector over the fixed vocabulary "
      "for every report (tier 4); free-text cannot reach this. Quality: micro-F1 "
      "and exact-match vs the gold vectors.")
    a("- **Pipeline (composite)** — pass only if all three steps pass. **Paired "
      "test** — per repeat, with vs without outcomes are paired; an exact one-sided "
      "binomial sign test is computed per step and for the composite.")
    a("")

    a("### M7. Summary and honesty notes")
    a("")
    a("- Step 2 measures the skill's **contract/evidence** value: both arms run the "
      "identical live loop and converge, but only the skill yields a "
      "schema-validated, agent-consumable summary + evidence pack (the raw script "
      "requires correct manual flags/columns/backend and emits raw files only).")
    a("- Step 3 measures the skill's **fixed-vocabulary/schema** value: with the "
      "contract the model completes a checkable label vector; unaided it returns "
      "free-text.")
    a("- `passed` is task/contract completion, not clinical correctness; accuracy "
      "is reported separately. Step-2 LLM/QC tokens are spent inside the loop "
      "subprocess and are not captured in the harness token profile.")
    a("")
    return L


def render_report(study: dict) -> str:
    meta = study["meta"]
    agg = study["aggregate"]
    by_ba = study["by_backend_arm"]
    paired = study["paired"]
    ds = meta["dataset"]
    mode = meta["mode"]
    backends = meta["backends"]
    kinds = {b["kind"] for b in backends}
    has_llm = any(k == "openai" for k in kinds)

    L: list[str] = []
    a = L.append

    a("# Curation Skills — With-vs-Without Skill Experiment")
    a("")
    a(f"Generated: {time.strftime('%Y-%m-%d %H:%M')} (local).")
    a(f"Protocol: {meta['protocol']}. Repeats per backend/arm: {meta['repeats']}.")
    a("")
    a("This report evaluates the MR-RATE report-curation skills on a three-step "
      "pipeline: **(1) select** radiology reports, **(2) anonymize + PHI-QC to "
      "convergence** (the anonymize\u2194QC repair loop), and **(3) assign a disease "
      "label** per report. Each step is run in a with-skill and a without-skill arm:")
    a("")
    a("- **Step 2 (anonymization QC loop)** \u2014 *with skill* runs the published "
      "`report-anonymization-qc-loop` skill; *without skill* runs the raw upstream "
      "`anonymize_qc_loop.py` script directly. Both execute the same live loop "
      "(hosted GLiNER-PII QC + Nemotron repair); the skill additionally emits a "
      "schema-valid summary + evidence pack, which is the measured differentiator.")
    a("- **Step 3 (disease labelling)** \u2014 *with skill* supplies the skill's fixed "
      "pathology vocabulary + complete-0/1-vector contract; *without skill* is a "
      "generic request with no vocabulary or schema.")
    a("")
    a("Grading is deterministic: corpus membership (step 1); loop convergence (no "
      "residual mapped identifier survives) plus emission of a schema-valid "
      "contract (step 2); and the gold `mrrate_labels.csv` vectors (step 3). "
      "`passed` measures task/contract completion, reported separately from "
      "accuracy \u2014 as the reference protocol separates \"did the agent take the "
      "right action\" from model quality.")
    a("")
    a("This is an engineering reproducibility protocol. It is not a clinical, "
      "diagnostic, or regulatory claim.")
    a("")

    # Interpretation note
    arm_style = meta.get("arm_style", "tool")
    a("## How to read this run")
    a("")
    if arm_style == "prompt":
        a("> **Same-model control.** Both arms use the named LLM backend(s) on the "
          "identical report and task; the *only* difference is that the with-skill "
          "arm's prompt carries the skill's contract (for labelling: the exact "
          "fixed pathology vocabulary and complete-0/1-vector schema), while the "
          "without-skill arm gets a generic request. This isolates the skill's "
          "contribution while holding the model fixed.")
    elif mode == "mock" and not has_llm:
        a("> **Methodology / plumbing proof.** The with-skill arm runs the skills' "
          "deterministic GPU-free `mock` mode (a real skill path), and the "
          "without-skill arm uses a deterministic stand-in backend. It proves the "
          "dataset, arms, graders, and aggregation work end-to-end and is "
          "reproducible offline. It is **not** a skill-value claim about real LLMs "
          "— for that, use `--arm-style prompt` (same-model) or `--mode live` with "
          "network backends (see *Reproduce*).")
    elif mode == "mock" and has_llm:
        a("> The with-skill arm runs the skills' deterministic `mock` mode (a tool "
          "call); the without-skill arm uses the named LLM backend(s) unaided. "
          "This contrasts the shipped skill tool against an unaided model.")
    else:
        a("> The with-skill arm runs the skills' `live` mode wrapping the named "
          "model; the without-skill arm uses the same model unaided. This is the "
          "same-model, with-wrapper-vs-without comparison.")
    a("")
    a("The note above describes **step 3 (labelling)**. **Step 2 (the "
      "anonymization QC loop)** is always the published skill script vs the raw "
      "upstream script and runs live, independent of arm-style.")
    a("")

    # Dataset
    a("## Evaluation dataset")
    a("")
    a(f"- Reports: **{ds['n']}**, seeded sample (seed `{ds['seed']}`) from "
      f"`{ds['source_reports_dir']}`, restricted to study_uids with gold labels.")
    if ds.get("inject_pii_k"):
        a(f"- Note: {ds['inject_pii_k']} of {ds['n']} sampled reports have a synthetic "
          "identifier line injected, but step 2 now runs the anonymization QC loop "
          "on a separate leaky fixture, so this injection is not used for grading.")
    a(f"- Pathology vocabulary: **{ds['vocab_size']} labels** "
      f"(`{', '.join(ds['vocab'])}`), a subset shared by the skill and the gold "
      "label file.")
    a(f"- Files: `{ds['csv']}`, ground truth `{ds['ground_truth']}`.")
    if ds.get("labeled_csv"):
        a(f"- Final populated dataset (with-skill assigned disease labels per "
          f"report): `{ds['labeled_csv']}`.")
    a("")
    for line in _sample_rows_table(study):
        a(line)

    # Aggregate
    a("## Current aggregate result")
    a("")
    a("Success rates are reported per step (the primary metric) and as a strict "
      "full-pipeline composite (all three steps pass).")
    a("")
    # per-step success totals across all backends/repeats
    a("### Per-step success rate (all backends, all repeats)")
    a("")
    a("| Step | With skill | Without skill |")
    a("|---|---:|---:|")
    for step, label in (("select", "1 select"), ("pii", "2 anon-QC-loop"),
                        ("label", "3 disease-label")):
        wp = sum(v["step_passes"][step] for k, v in by_ba.items() if v["arm"] == "with")
        wr = sum(v["repeats"] for k, v in by_ba.items() if v["arm"] == "with")
        op = sum(v["step_passes"][step] for k, v in by_ba.items() if v["arm"] == "without")
        orr = sum(v["repeats"] for k, v in by_ba.items() if v["arm"] == "without")
        a(f"| {label} | {wp}/{wr} ({_pct(wp, wr)}) | {op}/{orr} ({_pct(op, orr)}) |")
    a("")
    pbs = study.get("paired_by_step", {})
    if pbs:
        a("### Per-step paired with-vs-without (exact sign test)")
        a("")
        a("| Step | Pairs | Skill wins | Without wins | Ties | Sign-test p |")
        a("|---|---:|---:|---:|---:|---:|")
        for step, label in (("select", "1 select"), ("pii", "2 QC-loop"),
                            ("label", "3 label")):
            p = pbs.get(step)
            if p:
                a(f"| {label} | {p['pairs']} | {p['skill_wins']} | {p['without_wins']} | "
                  f"{p['ties']} | {p['sign_test_p']} |")
        a("")
    a("### Full-pipeline composite (all 3 steps pass)")
    a("")
    a(f"- With-skill: **{agg['with_passes']}/{agg['with_repeats']}** full pipelines.")
    a(f"- Without-skill: **{agg['without_passes']}/{agg['without_repeats']}** full "
      "pipelines.")
    ov = paired["__overall__"]
    a(f"- Paired composite: skill won **{ov['skill_wins']}**, without-skill won "
      f"**{ov['without_wins']}**, ties **{ov['ties']}** "
      f"(exact one-sided sign test p = {ov['sign_test_p']}).")
    a("")

    # Per-backend, per-step
    a("### Per-backend, per-step pass counts")
    a("")
    a("| Backend | Arm | Pipeline | Step 1 select | Step 2 QC-loop | Step 3 label |")
    a("|---|---|---:|---:|---:|---:|")
    for b in backends:
        for arm in meta["arms"]:
            key = f"{b['name']}|{arm}"
            r = by_ba.get(key)
            if not r:
                continue
            rep = r["repeats"]
            a(f"| {b['name']} | {arm} | {r['pipeline_passes']}/{rep} | "
              f"{r['step_passes']['select']}/{rep} | {r['step_passes']['pii']}/{rep} | "
              f"{r['step_passes']['label']}/{rep} |")
    a("")

    # Paired table
    a("### Paired with-vs-without (per backend)")
    a("")
    a("| Backend | Pairs | Skill wins | Without wins | Ties | Sign-test p |")
    a("|---|---:|---:|---:|---:|---:|")
    for b in backends:
        p = paired.get(b["name"])
        if p:
            a(f"| {b['name']} | {p['pairs']} | {p['skill_wins']} | "
              f"{p['without_wins']} | {p['ties']} | {p['sign_test_p']} |")
    a(f"| **overall** | {ov['pairs']} | {ov['skill_wins']} | {ov['without_wins']} | "
      f"{ov['ties']} | {ov['sign_test_p']} |")
    a("")

    # Token profiling
    a("## Token profiling")
    a("")
    a("Provider-reported usage per backend/arm. The **with-skill** arm calls the "
      "skill wrapper as a tool; its internal usage is not surfaced as provider "
      "tokens (0 shown), while the **without-skill** arm's tokens are the model "
      "calls it makes to improvise the task.")
    a("")
    a("| Backend | Arm | Repeats | Passes | LLM calls | Prompt tok | Completion tok | "
      "Total tok | Mean total/repeat | Mean exec s |")
    a("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for b in backends:
        for arm in meta["arms"]:
            key = f"{b['name']}|{arm}"
            r = by_ba.get(key)
            if not r:
                continue
            t = r["tokens"]
            est = "*" if t.get("estimated") else ""
            a(f"| {b['name']} | {arm} | {r['repeats']} | {r['pipeline_passes']} | "
              f"{t['n_calls']} | {t['prompt_tokens']} | {t['completion_tokens']} | "
              f"{t['total_tokens']}{est} | {r['mean_total_tokens_per_repeat']} | "
              f"{r['mean_exec_s']} |")
    a("")
    a("`*` = estimated (mock backend approximates tokens by whitespace; real "
      "backends report exact usage).")
    a("")

    # Quality layer
    a("## Quality layer (vs ground truth)")
    a("")
    a("Task completion (`passed`, above) is separate from accuracy. This layer "
      "reports agreement with the answer keys.")
    a("")
    a("| Backend | Arm | Step 2 clean-rate | Step 2 residual-leak | Step 2 contract | "
      "Step 3 label micro-F1 | Step 3 exact-match |")
    a("|---|---|---:|---:|:--:|---:|---:|")
    for b in backends:
        for arm in meta["arms"]:
            key = f"{b['name']}|{arm}"
            r = by_ba.get(key)
            if not r:
                continue
            q = r["quality"]
            f1 = _fmt(q.get("label_micro_f1")) if arm == "with" else "n/a (free-text)"
            em = _fmt(q.get("label_exact_match")) if arm == "with" else "n/a"
            contract = q.get("pii_contract")
            contract_s = ("yes" if contract == 1.0 else "no" if contract == 0.0
                          else _fmt(contract)) if contract is not None else "n/a"
            a(f"| {b['name']} | {arm} | {_fmt(q.get('pii_clean_rate'))} | "
              f"{_fmt(q.get('pii_residual_leak'))} | {contract_s} | {f1} | {em} |")
    a("")

    # Findings
    a("## Findings")
    a("")
    a(_findings_text(study))
    a("")

    # Five-tier ladder
    a("## Five-tier grade (per step)")
    a("")
    _step_labels = {"select": "select", "pii": "anon-QC-loop", "label": "label"}
    for step in ("select", "pii", "label"):
        a(f"**{_step_labels[step]}**")
        a("")
        a("| Tier | Check |")
        a("|---|---|")
        for tier in range(1, 6):
            a(f"| {tier} | {TIER_LADDER[step][tier]} |")
        a("")

    # Reachability
    a("## Backend reachability (probed at run time)")
    a("")
    a("| Backend | Kind | Model | Reachable | Note |")
    a("|---|---|---|:--:|---|")
    for b in backends:
        rc = meta["reachability"].get(b["name"], {})
        note = rc.get("error") or f"{rc.get('latency_s', 0)}s ping"
        a(f"| {b['name']} | {b['kind']} | `{b['model']}` | "
          f"{'yes' if rc.get('reachable') else 'no'} | {note} |")
    a("")

    # Reproduce
    a("## Reproduce")
    a("")
    a("From the `medical-AI-skills` catalog root:")
    a("")
    a("```bash")
    a("# Build the dataset (deterministic; no LLM needed)")
    a("python -m tools.curation_eval.run_curation_eval dataset --n 10 --seed 42 "
      "--inject-pii 3 --out runs/curation_eval/dataset")
    a("")
    a("# Offline methodology proof (mock skill mock backend)")
    a("python -m tools.curation_eval.run_curation_eval run --backends mock "
      "--repeats 3 --mode mock")
    a("")
    a("# Live, multi-backend (same model with-wrapper vs without); needs the")
    a("# servers reachable and a GPU for the skills' live mode")
    a("python -m tools.curation_eval.run_curation_eval run \\")
    a("  --backends ollama-nemotron ollama-qwen --repeats 3 --mode live "
      "--cuda-visible-devices 1")
    a("```")
    a("")
    a(f"Artifacts for this run: `{meta['out_dir']}` (per-arm outputs + "
      "`study_results.json`).")
    a("")
    for line in _methods_section(study):
        a(line)
    return "\n".join(L)


def _findings_text(study: dict) -> str:
    by_ba = study["by_backend_arm"]
    pbs = study.get("paired_by_step", {})

    def _tot(arm: str, step: str) -> tuple[int, int]:
        p = sum(a["step_passes"][step] for k, a in by_ba.items() if a["arm"] == arm)
        r = sum(a["repeats"] for k, a in by_ba.items() if a["arm"] == arm)
        return p, r

    def _q(arm: str, key: str):
        vals = [a["quality"].get(key) for k, a in by_ba.items()
                if a["arm"] == arm and a["quality"].get(key) is not None]
        return (sum(vals) / len(vals)) if vals else None

    wl, wlr = _tot("with", "label")
    ol, olr = _tot("without", "label")
    wq, wqr = _tot("with", "pii")
    oq, oqr = _tot("without", "pii")
    lab_p = pbs.get("label", {})
    qc_p = pbs.get("pii", {})

    lines = []
    lines.append(
        f"- **Step 2 (anonymization QC loop).** With-skill passed **{wq}/{wqr}**; "
        f"without-skill **{oq}/{oqr}** (paired sign-test p = "
        f"{qc_p.get('sign_test_p', 'n/a')}). Both arms run the *identical* live "
        f"loop and typically converge (mean residual-leak: with "
        f"{_fmt(_q('with', 'pii_residual_leak'))}, without "
        f"{_fmt(_q('without', 'pii_residual_leak'))}; mean clean-rate: with "
        f"{_fmt(_q('with', 'pii_clean_rate'))}, without "
        f"{_fmt(_q('without', 'pii_clean_rate'))}). The pass difference is the "
        f"**contract**: the skill emits a schema-valid summary + evidence pack "
        f"(contract rate {_fmt(_q('with', 'pii_contract'))}) an agent/verifier can "
        f"consume, while the raw upstream script emits only raw CSVs (contract rate "
        f"{_fmt(_q('without', 'pii_contract'))}) and must be invoked with the exact "
        f"flags/columns/backend by hand."
    )
    lines.append(
        f"- **Step 3 (disease labelling).** With-skill passed **{wl}/{wlr}**; "
        f"without-skill **{ol}/{olr}** (paired sign-test p = "
        f"{lab_p.get('sign_test_p', 'n/a')}). Given the skill's fixed vocabulary + "
        f"complete-0/1-vector schema the model completes the contract; unaided it "
        f"returns free-text and fails coverage."
    )
    lines.append(
        "- **Step 1 (selection)** is a shared, deterministic seeded fixture graded "
        "for validity; table-stakes, not a with/without differentiator."
    )
    lines.append(
        "- **Composite note.** The full-pipeline gate requires all three steps, so "
        "read the per-step rates as the primary signal."
    )
    return "\n".join(lines)


def write_report(study: dict, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(study), encoding="utf-8")
    return path
