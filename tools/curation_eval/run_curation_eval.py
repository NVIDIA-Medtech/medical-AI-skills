# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""CLI for the curation with-vs-without-skill evaluation.

Subcommands:

* ``dataset`` -- build the seeded evaluation dataset (deterministic, no LLM).
* ``run``     -- run the study (backends x arms x repeats), grade, aggregate,
                 and write ``study_results.json`` + the markdown report.
* ``report``  -- re-render the markdown report from an existing results JSON.

Run from the ``medical-AI-skills`` catalog root, e.g.::

    python -m tools.curation_eval.run_curation_eval run --backends mock --mode mock
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from . import paths
from .dataset import build_dataset, load_dataset
from .report import render_report, write_report
from .runner import run_study


def _cmd_dataset(args: argparse.Namespace) -> int:
    out = Path(args.out)
    ds = build_dataset(out_dir=out, n=args.n, seed=args.seed,
                       inject_pii_k=args.inject_pii, text_col=args.text_col)
    print(json.dumps({
        "csv": str(ds.csv_path), "ground_truth": str(ds.gt_path),
        "n": ds.n, "seed": ds.seed, "vocab_size": len(ds.vocab),
        "injected_pii": sum(1 for g in ds.ground_truth["reports"].values()
                            if g["pii_present"]),
    }, indent=2))
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    study_out = Path(args.out) if args.out else (
        paths.RUNS_DIR / time.strftime("study_%Y%m%d_%H%M%S"))
    study_out.mkdir(parents=True, exist_ok=True)

    if args.dataset_dir:
        ds = load_dataset(Path(args.dataset_dir))
    else:
        ds = build_dataset(out_dir=study_out / "dataset", n=args.n, seed=args.seed,
                           inject_pii_k=args.inject_pii)

    study = run_study(
        dataset=ds,
        backend_specs=args.backends,
        arms=tuple(args.arms),
        repeats=args.repeats,
        mode=args.mode,
        model=args.model,
        cuda=args.cuda_visible_devices,
        out_dir=study_out,
        pii_threshold=args.pii_threshold,
        arm_style=args.arm_style,
        verbose=not args.quiet,
        qcloop_qc_backend=args.qcloop_qc_backend,
        qcloop_model=args.qcloop_model,
        qcloop_max_iters=args.qcloop_max_iters,
        qcloop_max_row_attempts=args.qcloop_max_row_attempts,
        qcloop_limit=args.qcloop_limit,
        qcloop_input=args.qcloop_input,
        qcloop_python=args.qcloop_python,
    )

    report_path = Path(args.report) if args.report else paths.DEFAULT_REPORT_MD
    write_report(study, report_path)
    write_report(study, study_out / "report.md")

    agg = study["aggregate"]
    ov = study["paired"]["__overall__"]
    print(json.dumps({
        "results": study["meta"]["results_path"],
        "report": str(report_path),
        "with_passes": f"{agg['with_passes']}/{agg['with_repeats']}",
        "without_passes": f"{agg['without_passes']}/{agg['without_repeats']}",
        "paired": {"skill_wins": ov["skill_wins"], "without_wins": ov["without_wins"],
                   "ties": ov["ties"], "sign_test_p": ov["sign_test_p"]},
        "reachability": study["meta"]["reachability"],
    }, indent=2))
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    with Path(args.results).open(encoding="utf-8") as f:
        study = json.load(f)
    out = Path(args.out) if args.out else paths.DEFAULT_REPORT_MD
    out.write_text(render_report(study), encoding="utf-8")
    print(str(out))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="curation_eval",
        description="With-vs-without-skill evaluation for MR-RATE curation skills.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("dataset", help="build the seeded evaluation dataset")
    d.add_argument("--n", type=int, default=10)
    d.add_argument("--seed", type=int, default=42)
    d.add_argument("--inject-pii", type=int, default=3)
    d.add_argument("--text-col", default="report")
    d.add_argument("--out", default=str(paths.RUNS_DIR / "dataset"))
    d.set_defaults(func=_cmd_dataset)

    r = sub.add_parser("run", help="run the study and write the report")
    r.add_argument("--backends", nargs="+", default=["mock"],
                   help="backend specs: 'mock', a registry name, or name=base_url=model")
    r.add_argument("--arms", nargs="+", default=["with", "without"],
                   choices=["with", "without"])
    r.add_argument("--repeats", type=int, default=3)
    r.add_argument("--mode", choices=["mock", "live"], default="mock",
                   help="skill execution mode for the with-skill arm (arm-style=tool)")
    r.add_argument("--arm-style", choices=["tool", "prompt"], default="tool",
                   help="with-skill arm: 'tool' runs the skill script; 'prompt' gives "
                        "the same backend the skill's contract (same-model control)")
    r.add_argument("--model", default=None, help="override skill live-mode model id")
    r.add_argument("--cuda-visible-devices", default=None)
    r.add_argument("--pii-threshold", type=float, default=1.0)
    r.add_argument("--dataset-dir", default=None, help="reuse a prebuilt dataset dir")
    r.add_argument("--n", type=int, default=10)
    r.add_argument("--seed", type=int, default=42)
    r.add_argument("--inject-pii", type=int, default=3)
    r.add_argument("--out", default=None, help="study output dir")
    r.add_argument("--report", default=None, help="markdown report path")
    r.add_argument("--quiet", action="store_true",
                   help="suppress streaming progress telemetry on stderr")
    # Step-2 anonymization QC-loop (skill vs upstream script) config.
    r.add_argument("--qcloop-qc-backend", choices=["api", "local", "nemo"], default="api",
                   help="GLiNER-PII QC backend for the anon-qc-loop step (api = hosted)")
    r.add_argument("--qcloop-model", default="nvidia/nemotron-3-super-120b-a12b",
                   help="repair model id for the anon-qc-loop step")
    r.add_argument("--qcloop-max-iters", type=int, default=5)
    r.add_argument("--qcloop-max-row-attempts", type=int, default=3)
    r.add_argument("--qcloop-limit", type=int, default=0,
                   help="process only the first N rows of the qc-loop input (0 = all)")
    r.add_argument("--qcloop-input", default=None,
                   help="qc-loop input CSV (default: the skill's leaky fixture)")
    r.add_argument("--qcloop-python", default=None,
                   help="python interpreter for the live qc-loop (default: anon-vllm env)")
    r.set_defaults(func=_cmd_run)

    rep = sub.add_parser("report", help="re-render report from results JSON")
    rep.add_argument("results", help="path to study_results.json")
    rep.add_argument("--out", default=None)
    rep.set_defaults(func=_cmd_report)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
