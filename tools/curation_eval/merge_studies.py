#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Merge several anon_experiment ``study_results.json`` files into one grand report.

The with-vs-without report is rendered purely from the ``attempts`` array (plus
``reachability`` / ``backend_specs``), so combining runs is just concatenating those
arrays and re-rendering. This does NOT re-run or re-judge anything — it reuses each
run's already-computed attempts and judge results, so it is cheap and offline.

IMPORTANT: only merge runs that used the SAME JUDGE; otherwise residual-PHI escape
counts are not comparable across arms. Each attempt must also have a unique
``(backend, arm)`` label across studies, or aggregation collapses them together.

Usage::

    python -m tools.curation_eval.merge_studies \
        runs/.../study_buildnvidia_100 runs/.../study_unaided_100 \
        --out docs/anonymization-grand-100.md
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import fields
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.curation_eval.anon_experiment import AttemptResult, aggregate, finalize_outputs


def _load(path: str | Path) -> dict:
    p = Path(path)
    if p.is_dir():
        p = p / "study_results.json"
    if not p.is_file():
        raise SystemExit(f"study_results.json not found: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def merge(study_paths: list[str], report_path: str) -> tuple[str, str]:
    fnames = {f.name for f in fields(AttemptResult)}
    attempts: list[AttemptResult] = []
    reachability: list[dict] = []
    seen_reach: set[str] = set()
    backend_specs: list[str] = []
    seen_labels: set[tuple[str, str, int]] = set()
    n = 0
    staged_input = ""
    timeout = 2400.0
    execute = True

    for sp in study_paths:
        d = _load(sp)
        for a in d.get("attempts", []):
            label = (a.get("backend"), a.get("arm"), a.get("repeat"))
            if label in seen_labels:
                print(f"WARNING: duplicate (backend, arm, repeat)={label} from {sp} "
                      "— attempts will aggregate together; give runs distinct labels.",
                      file=sys.stderr)
            seen_labels.add(label)
            attempts.append(AttemptResult(**{k: v for k, v in a.items() if k in fnames}))
        for r in d.get("reachability", []):
            if r["backend"] not in seen_reach:
                reachability.append(r)
                seen_reach.add(r["backend"])
        m = d.get("meta", {})
        for s in m.get("backend_specs", []):
            if s not in backend_specs:
                backend_specs.append(s)
        n = max(n, int(m.get("n_reports") or 0))
        staged_input = staged_input or m.get("staged_input", "")
        timeout = m.get("timeout_s", timeout)
        execute = m.get("executed_tier5", execute)

    if not attempts:
        raise SystemExit("no attempts found across the provided studies")

    study = aggregate(attempts, reachability, backend_specs, 1, n,
                      Path(staged_input or "merged"), timeout, execute)
    return finalize_outputs(study, report_path)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("studies", nargs="+", help="study dirs or study_results.json paths to merge")
    p.add_argument("--out", required=True, help="output markdown report path (.html written alongside)")
    args = p.parse_args(argv)
    md, html = merge(args.studies, args.out)
    print(f"wrote {md}")
    print(f"wrote {html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
