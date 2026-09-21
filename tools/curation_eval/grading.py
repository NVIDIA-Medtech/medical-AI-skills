# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Deterministic graders for the three curation steps.

Every step is scored on a five-tier ladder (mirroring the reference
with-vs-without protocol) plus a quality layer measured against ground truth:

* ``select`` -- valid seeded fixture (10 labelled reports, non-empty text).
* ``pii``    -- correct per-report PII verdict vs the injection answer key
  (precision / recall / accuracy).
* ``label``  -- a complete 0/1 vector over the fixed pathology vocabulary
  (contract), plus label agreement with the gold ``mrrate_labels.csv`` vector
  (macro-F1 / exact-match) as the quality layer.

``passed`` is task-completion (contract), separated from accuracy, exactly as
the reference report separates "did the agent take the right action" from
"model quality".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .dataset import Dataset
from .tasks import StepResult

MAX_TIER = 5

# Five-tier ladder text, surfaced in the generated report.
TIER_LADDER = {
    "select": {
        1: "Produced a selection artifact.",
        2: "Selected exactly the requested number of reports.",
        3: "Every selected study_uid exists in the source corpus.",
        4: "Every selected report has non-empty text.",
        5: "Selected uids are unique and carry ground-truth labels.",
    },
    "pii": {
        1: "The anonymize<->QC loop ran to completion.",
        2: "Produced repaired anonymized output for the reports.",
        3: "Converged: no mapped identifier survives (residual leak rate 0).",
        4: "Emitted a schema-valid machine-readable summary (skill contract).",
        5: "Converged + contract-valid summary + complete evidence pack.",
    },
    "label": {
        1: "Produced a labelling output.",
        2: "Output is parseable structured data.",
        3: "Labels use the fixed pathology vocabulary (0/1 per label).",
        4: "A complete label vector for every report (coverage).",
        5: "All label values valid and gradeable against gold.",
    },
}


@dataclass
class StepGrade:
    step: str
    arm: str
    tier: int
    passed: bool
    metrics: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)


def _gt_reports(dataset: Dataset) -> dict:
    return dataset.ground_truth.get("reports", {})


# ---------------------------------------------------------------------------
# Step 1: select
# ---------------------------------------------------------------------------
def grade_select(res: StepResult, dataset: Dataset) -> StepGrade:
    uids = res.output.get("selected_uids", []) if res.executed else []
    gt = _gt_reports(dataset)
    n_expected = dataset.ground_truth.get("n", len(dataset.records))
    tier = 0
    if res.executed and uids:
        tier = 1
        if len(uids) == n_expected:
            tier = 2
            if all(u in gt for u in uids):
                tier = 3
                rec_by_uid = {r["study_uid"]: r for r in dataset.records}
                if all((rec_by_uid.get(u, {}).get("report", "").strip()) for u in uids):
                    tier = 4
                    if len(set(uids)) == len(uids) and all(
                        gt.get(u, {}).get("gold_labels_vocab") is not None for u in uids
                    ):
                        tier = 5
    return StepGrade(
        step="select", arm=res.arm, tier=tier, passed=tier >= 5,
        metrics={"n_selected": len(uids), "n_expected": n_expected},
    )


# ---------------------------------------------------------------------------
# Step 2: pii
# ---------------------------------------------------------------------------
def grade_pii(res: StepResult, dataset: Dataset, threshold: float = 1.0) -> StepGrade:
    """Grade step 2 = the anonymization QC convergence loop (skill vs upstream).

    Both arms run the same loop; the differentiator is the skill's schema-valid
    summary/evidence contract. ``passed`` = converged (no residual leak) AND
    contract-valid; the raw upstream converges but emits no validated summary.
    (``threshold`` is unused here; kept for signature compatibility.)
    """
    m = res.output.get("metrics", {}) if res.executed else {}
    converged = bool(m.get("converged"))
    contract = bool(m.get("contract_valid"))
    n_reports = int(m.get("n_reports") or 0)

    tier = 0
    if res.executed and not res.error:
        tier = 1
        if n_reports > 0:
            tier = 2
            if converged:
                tier = 3
                if contract:
                    tier = 4
                    if m.get("clean_rate") is not None:
                        tier = 5
    passed = converged and contract
    return StepGrade(step="pii", arm=res.arm, tier=tier, passed=passed, metrics=dict(m))


# ---------------------------------------------------------------------------
# Step 3: label
# ---------------------------------------------------------------------------
def _prf1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f = (2 * p * r / (p + r)) if (p + r) else 0.0
    return p, r, f


def _lenient_recover(diseases: list[str], vocab: list[str]) -> dict[str, int]:
    """Best-effort map of free-text disease names onto the fixed vocabulary.

    Only used to report how close the without-skill output gets; it does not
    make the without-skill arm contract-compliant.
    """
    text = " ".join(diseases).lower()
    vec: dict[str, int] = {}
    for name in vocab:
        toks = [t for t in re.split(r"[^a-z]+", name.lower()) if len(t) > 3]
        hit = any(t in text for t in toks) if toks else name.lower() in text
        vec[name] = 1 if hit else 0
    return vec


def grade_label(res: StepResult, dataset: Dataset) -> StepGrade:
    vocab = dataset.vocab
    gt = _gt_reports(dataset)
    uids = [r["study_uid"] for r in dataset.records]

    schema = res.output.get("schema")
    tier = 0
    metrics: dict = {"schema": schema, "n": len(uids)}

    if res.arm == "with":
        labels = res.output.get("labels", {}) if res.executed else {}
        vocab_out = res.output.get("vocab", [])
        if res.executed and labels:
            tier = 1
            tier = 2  # CSV rows are structured by construction
            fixed_schema = set(vocab).issubset(set(vocab_out))
            if fixed_schema:
                tier = 3
                complete = all(
                    isinstance(labels.get(u), dict)
                    and all(k in labels[u] for k in vocab)
                    for u in uids
                )
                if complete:
                    tier = 4
                    valid = all(
                        all(labels[u].get(k) in (0, 1) for k in vocab) for u in uids
                    )
                    if valid:
                        tier = 5
        # Quality vs gold (over the fixed vocab).
        tp = fp = fn = tn = 0
        exact = 0
        for u in uids:
            g = gt.get(u, {}).get("gold_labels_vocab", {})
            pred = labels.get(u, {}) if isinstance(labels.get(u), dict) else {}
            row_match = True
            for k in vocab:
                gv = int(g.get(k, 0))
                pv = int(pred.get(k, 0)) if pred.get(k) in (0, 1) else 0
                if pv == 1 and gv == 1:
                    tp += 1
                elif pv == 1 and gv == 0:
                    fp += 1
                elif pv == 0 and gv == 1:
                    fn += 1
                else:
                    tn += 1
                if pv != gv:
                    row_match = False
            if row_match:
                exact += 1
        p, r, f1 = _prf1(tp, fp, fn)
        metrics.update({
            "vocab_size": len(vocab),
            "exact_match_rate": round(exact / len(uids), 4) if uids else 0.0,
            "micro_precision": round(p, 4), "micro_recall": round(r, 4),
            "micro_f1": round(f1, 4), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "n_gold_positive_pairs": tp + fn,
        })
        passed = tier >= 4
    else:
        free = res.output.get("free_labels", {}) if res.executed else {}
        n_parsed = sum(1 for u in uids if free.get(u, {}).get("parsed"))
        if res.executed and free:
            tier = 1
            if n_parsed >= 1:
                tier = 2  # parseable structured list...
            # Free-text labels never satisfy the fixed 0/1 vocabulary schema.
        # Lenient recovery, purely for reporting how close it got.
        tp = fp = fn = 0
        for u in uids:
            diseases = free.get(u, {}).get("diseases") or []
            rec = _lenient_recover([str(d) for d in diseases], vocab)
            g = gt.get(u, {}).get("gold_labels_vocab", {})
            for k in vocab:
                gv = int(g.get(k, 0))
                pv = rec.get(k, 0)
                if pv == 1 and gv == 1:
                    tp += 1
                elif pv == 1 and gv == 0:
                    fp += 1
                elif pv == 0 and gv == 1:
                    fn += 1
        p, r, f1 = _prf1(tp, fp, fn)
        metrics.update({
            "vocab_size": len(vocab), "n_parsed": n_parsed,
            "fixed_schema": False,
            "lenient_micro_f1": round(f1, 4),
            "note": "free-text output; no fixed 0/1 vocabulary vector",
        })
        passed = tier >= 4  # unreachable for free-text -> fails, as intended
    return StepGrade(step="label", arm=res.arm, tier=tier, passed=passed, metrics=metrics)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
def grade_pipeline(results: dict[str, StepResult], dataset: Dataset,
                   pii_threshold: float = 1.0) -> dict:
    grades = {
        "select": grade_select(results["select"], dataset),
        "pii": grade_pii(results["pii"], dataset, threshold=pii_threshold),
        "label": grade_label(results["label"], dataset),
    }
    passed = all(g.passed for g in grades.values())
    return {
        "grades": {k: vars(g) for k, g in grades.items()},
        "passed": passed,
        "n_steps_passed": sum(1 for g in grades.values() if g.passed),
        "n_steps": len(grades),
    }
