# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Study orchestration: backends x arms x repeats -> aggregates + results JSON.

Runs the three-step pipeline for the with-skill and without-skill arms across
every requested backend and repeat, grades each run, then computes:

* per-(backend, arm) success rates and per-step pass counts,
* per-backend paired with-vs-without outcomes and an exact one-sided sign test,
* token profiling (provider-reported for live backends; the with-skill arm's
  tool calls do not surface provider usage, which the report states plainly).

The whole study is single-shot / no-repair, matching the reference protocol.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import asdict
from pathlib import Path

from . import paths, tasks, telemetry
from .backends import Backend, make_backend, probe
from .dataset import Dataset
from .grading import grade_pipeline


def sign_test(wins: int, losses: int) -> float:
    """Exact one-sided binomial sign test p-value over decisive pairs (H0 p=0.5)."""
    n = wins + losses
    if n == 0:
        return 1.0
    k = max(wins, losses)
    tail = sum(math.comb(n, i) for i in range(k, n + 1)) * (0.5**n)
    return min(1.0, tail)


def _blank_tokens() -> dict:
    return {"prompt_tokens": 0, "completion_tokens": 0, "reasoning_tokens": 0,
            "total_tokens": 0, "n_calls": 0, "estimated": False}


def _accumulate_tokens(acc: dict, usage: dict) -> None:
    for k in ("prompt_tokens", "completion_tokens", "reasoning_tokens", "total_tokens"):
        acc[k] += int(usage.get(k, 0) or 0)
    acc["n_calls"] += int(usage.get("n_calls", 0) or 0)
    if usage.get("estimated"):
        acc["estimated"] = True


def run_study(
    dataset: Dataset,
    backend_specs: list[str],
    arms: tuple[str, ...] = ("with", "without"),
    repeats: int = 3,
    mode: str = "mock",
    model: str | None = None,
    cuda: str | None = None,
    out_dir: Path | None = None,
    pii_threshold: float = 1.0,
    arm_style: str = "tool",
    verbose: bool = True,
    qcloop_qc_backend: str = "api",
    qcloop_model: str = "nvidia/nemotron-3-super-120b-a12b",
    qcloop_max_iters: int = 5,
    qcloop_max_row_attempts: int = 3,
    qcloop_limit: int = 0,
    qcloop_input: str | None = None,
    qcloop_python: str | None = None,
) -> dict:
    out_dir = Path(out_dir or (paths.RUNS_DIR / time.strftime("study_%Y%m%d_%H%M%S")))
    out_dir.mkdir(parents=True, exist_ok=True)

    telemetry.configure(verbose)
    n_runs = len(backend_specs) * repeats * len(arms)
    telemetry.rule(
        f"study start: backends={backend_specs} repeats={repeats} arms={list(arms)} "
        f"mode={mode} arm_style={arm_style} -> {n_runs} runs"
    )

    backends: list[Backend] = [make_backend(s) for s in backend_specs]

    qcloop_cfg = tasks.QCLoopConfig(
        input_csv=qcloop_input, python=qcloop_python, qc_backend=qcloop_qc_backend,
        model=qcloop_model, max_iters=qcloop_max_iters,
        max_row_attempts=qcloop_max_row_attempts, limit=qcloop_limit,
    )
    telemetry.log(
        f"step-2 anon-qc-loop: input={qcloop_cfg.resolved_input().name} "
        f"python={qcloop_cfg.resolved_python()} qc_backend={qcloop_cfg.qc_backend} "
        f"model={qcloop_cfg.model}"
    )

    # Probe reachability of network backends up front.
    reachability: dict[str, dict] = {}
    for b in backends:
        if b.kind == "openai":
            telemetry.log(f"probing {b.name} ({b.model}) at {b.base_url} ...")
            pr = probe(b)
            reachability[b.name] = {"reachable": pr.ok, "error": pr.error,
                                    "latency_s": round(pr.latency_s, 3)}
            telemetry.log(f"  {b.name}: reachable={pr.ok} "
                          f"{('%.2fs' % pr.latency_s) if pr.ok else (pr.error or '')}")
        else:
            reachability[b.name] = {"reachable": True, "error": None, "latency_s": 0.0}

    runs: list[dict] = []
    by_ba: dict[str, dict] = {}
    final_labeled: Path | None = None

    for b in backends:
        reachable = reachability[b.name]["reachable"]
        skill_model = model or (b.model if b.kind == "openai" and mode == "live" else None)
        for rep in range(repeats):
            for arm in arms:
                wd = out_dir / b.name / f"rep{rep}" / arm
                telemetry.rule(f"{b.name} | repeat {rep + 1}/{repeats} | arm={arm} "
                               f"({arm_style if arm == 'with' else 'baseline'})")
                needs_backend = (arm == "without") or (arm == "with" and arm_style == "prompt")
                if needs_backend and b.kind == "openai" and not reachable:
                    telemetry.log(f"  SKIPPED: backend {b.name} unreachable")
                    grade = {"passed": False, "n_steps_passed": 0, "n_steps": 3,
                             "grades": {}, "skipped": "backend unreachable"}
                    step_usage, step_runtime, step_exec, surfaces = {}, {}, {}, {}
                else:
                    results = tasks.run_pipeline(
                        dataset, arm, b, wd, mode=mode, model=skill_model, cuda=cuda,
                        arm_style=arm_style, qcloop_cfg=qcloop_cfg,
                    )
                    grade = grade_pipeline(results, dataset, pii_threshold=pii_threshold)
                    _steps = grade.get("grades", {})
                    _parts = []
                    for s in ("select", "pii", "label"):
                        g = _steps.get(s, {})
                        mark = "PASS" if g.get("passed") else "fail"
                        _parts.append(f"{s}=t{g.get('tier', 0)}/{mark}")
                    _pipe = "PASS" if grade["passed"] else "fail"
                    telemetry.log(f"  result: pipeline={_pipe} | " + "  ".join(_parts))
                    step_usage = {s: r.usage for s, r in results.items()}
                    step_runtime = {s: round(r.runtime_s, 3) for s, r in results.items()}
                    step_exec = {s: r.executed for s, r in results.items()}
                    surfaces = {s: r.surface for s, r in results.items()}
                    for s, r in results.items():
                        if r.error:
                            grade.setdefault("errors", {})[s] = r.error
                    if (arm == "with" and final_labeled is None
                            and results.get("label") and results["label"].executed):
                        final_labeled = tasks.assemble_final_dataset(
                            dataset, results.get("pii"), results["label"],
                            out_dir / "evaluation_dataset_labeled.csv")
                run = {
                    "backend": b.name, "backend_kind": b.kind, "backend_model": b.model,
                    "repeat": rep, "arm": arm, "mode": mode,
                    "passed": grade["passed"], "n_steps_passed": grade["n_steps_passed"],
                    "grade": grade, "usage": step_usage, "runtime_s": step_runtime,
                    "executed": step_exec, "surfaces": surfaces,
                }
                runs.append(run)

                key = f"{b.name}|{arm}"
                agg = by_ba.setdefault(key, {
                    "backend": b.name, "arm": arm, "backend_model": b.model,
                    "repeats": 0, "pipeline_passes": 0,
                    "step_passes": {"select": 0, "pii": 0, "label": 0},
                    "tokens": _blank_tokens(), "executed_runs": 0,
                    "exec_seconds": 0.0, "n_exec_steps": 0,
                    "quality_samples": {"pii_clean_rate": [], "pii_residual_leak": [],
                                        "pii_contract": [], "label_micro_f1": [],
                                        "label_exact_match": []},
                })
                agg["repeats"] += 1
                agg["pipeline_passes"] += 1 if grade["passed"] else 0
                for s in ("select", "pii", "label"):
                    g = grade.get("grades", {}).get(s)
                    if g and g.get("passed"):
                        agg["step_passes"][s] += 1
                for s, u in step_usage.items():
                    _accumulate_tokens(agg["tokens"], u or {})
                for s, ex in step_exec.items():
                    if ex:
                        agg["executed_runs"] += 1
                        agg["exec_seconds"] += step_runtime.get(s, 0.0)
                        agg["n_exec_steps"] += 1
                # quality
                gp = grade.get("grades", {})
                if gp.get("pii"):
                    pm = gp["pii"]["metrics"]
                    if pm.get("clean_rate") is not None:
                        agg["quality_samples"]["pii_clean_rate"].append(pm["clean_rate"])
                    if pm.get("residual_leak_rate") is not None:
                        agg["quality_samples"]["pii_residual_leak"].append(
                            pm["residual_leak_rate"])
                    agg["quality_samples"]["pii_contract"].append(
                        1.0 if pm.get("contract_valid") else 0.0)
                if gp.get("label") and arm == "with":
                    agg["quality_samples"]["label_micro_f1"].append(
                        gp["label"]["metrics"].get("micro_f1"))
                    agg["quality_samples"]["label_exact_match"].append(
                        gp["label"]["metrics"].get("exact_match_rate"))

    # finalize per-(backend,arm) means
    for agg in by_ba.values():
        n_exec = agg["n_exec_steps"] or 1
        agg["mean_exec_s"] = round(agg["exec_seconds"] / n_exec, 3)
        agg["mean_total_tokens_per_repeat"] = round(
            agg["tokens"]["total_tokens"] / (agg["repeats"] or 1), 1)
        q = agg.pop("quality_samples")
        agg["quality"] = {
            k: (round(sum(v) / len(v), 4) if v else None) for k, v in q.items()
        }

    # paired with-vs-without per backend
    paired: dict[str, dict] = {}
    for b in backends:
        wins = losses = ties = 0
        for rep in range(repeats):
            with_pass = next((r["passed"] for r in runs
                              if r["backend"] == b.name and r["repeat"] == rep
                              and r["arm"] == "with"), None)
            without_pass = next((r["passed"] for r in runs
                                 if r["backend"] == b.name and r["repeat"] == rep
                                 and r["arm"] == "without"), None)
            if with_pass and not without_pass:
                wins += 1
            elif without_pass and not with_pass:
                losses += 1
            else:
                ties += 1
        paired[b.name] = {
            "pairs": repeats, "skill_wins": wins, "without_wins": losses,
            "ties": ties, "sign_test_p": round(sign_test(wins, losses), 6),
        }
    tot_w = sum(p["skill_wins"] for p in paired.values())
    tot_l = sum(p["without_wins"] for p in paired.values())
    tot_t = sum(p["ties"] for p in paired.values())
    paired["__overall__"] = {
        "pairs": tot_w + tot_l + tot_t, "skill_wins": tot_w, "without_wins": tot_l,
        "ties": tot_t, "sign_test_p": round(sign_test(tot_w, tot_l), 8),
    }

    # paired per step (the composite can mask a decisive single-step gap)
    def _step_pass(backend_name: str, rep: int, arm: str, step: str):
        run = next((r for r in runs if r["backend"] == backend_name and r["repeat"] == rep
                    and r["arm"] == arm), None)
        if not run:
            return None
        g = run.get("grade", {}).get("grades", {}).get(step)
        return bool(g.get("passed")) if g else False

    paired_by_step: dict[str, dict] = {}
    for step in ("select", "pii", "label"):
        w = l = t = 0
        for b in backends:
            for rep in range(repeats):
                wp = _step_pass(b.name, rep, "with", step)
                op = _step_pass(b.name, rep, "without", step)
                if wp and not op:
                    w += 1
                elif op and not wp:
                    l += 1
                else:
                    t += 1
        paired_by_step[step] = {
            "pairs": w + l + t, "skill_wins": w, "without_wins": l, "ties": t,
            "sign_test_p": round(sign_test(w, l), 8),
        }

    # top-line aggregate
    def _sum_arm(arm: str, field: str) -> int:
        return sum(a[field] for k, a in by_ba.items() if a["arm"] == arm)

    aggregate = {
        "with_passes": _sum_arm("with", "pipeline_passes"),
        "with_repeats": _sum_arm("with", "repeats"),
        "without_passes": _sum_arm("without", "pipeline_passes"),
        "without_repeats": _sum_arm("without", "repeats"),
    }

    study = {
        "meta": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "mode": mode,
            "arm_style": arm_style,
            "arms": list(arms),
            "repeats": repeats,
            "pii_threshold": pii_threshold,
            "protocol": "single-shot / no-repair (max_correction_steps=0)",
            "backends": [b.describe() for b in backends],
            "reachability": reachability,
            "dataset": {
                "n": dataset.n, "seed": dataset.seed,
                "inject_pii_k": dataset.ground_truth.get("inject_pii_k"),
                "vocab": dataset.vocab, "vocab_size": len(dataset.vocab),
                "csv": str(dataset.csv_path), "ground_truth": str(dataset.gt_path),
                "labeled_csv": str(final_labeled) if final_labeled else None,
                "source_reports_dir": dataset.ground_truth.get("source_reports_dir"),
                "source_labels_csv": dataset.ground_truth.get("source_labels_csv"),
            },
            "out_dir": str(out_dir),
        },
        "by_backend_arm": by_ba,
        "paired": paired,
        "paired_by_step": paired_by_step,
        "aggregate": aggregate,
        "runs": runs,
    }

    results_path = out_dir / "study_results.json"
    with results_path.open("w", encoding="utf-8") as f:
        json.dump(study, f, indent=2, ensure_ascii=False)
    study["meta"]["results_path"] = str(results_path)
    tot = telemetry.totals()
    telemetry.rule(
        f"study done in {tot['elapsed_s']}s: with "
        f"{aggregate['with_passes']}/{aggregate['with_repeats']}, without "
        f"{aggregate['without_passes']}/{aggregate['without_repeats']} | "
        f"{tot['calls']} LLM calls / {tot['tokens']} tok -> {results_path}"
    )
    return study
