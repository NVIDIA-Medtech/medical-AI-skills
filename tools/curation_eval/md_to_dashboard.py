#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Regenerate the HTML dashboard from a Markdown report, keeping the two in sync.

Renders `<report>.md` into a self-contained dashboard `<report>.html` (KPI cards
parsed from the report's '### Headline' table plus the full report body). Runs
with the standard library only.

Usage::

    python -m tools.curation_eval.md_to_dashboard docs/anonymization-with-vs-without-experiment.md
    python -m tools.curation_eval.md_to_dashboard REPORT.md OUT.html
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as a script (python tools/curation_eval/md_to_dashboard.py ...).
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.curation_eval.anon_experiment import _sanitize, render_dashboard_html


def convert(md_path: Path, out_path: Path | None = None) -> Path:
    md_path = Path(md_path)
    if not md_path.exists():
        raise SystemExit(f"markdown report not found: {md_path}")
    out_path = Path(out_path) if out_path else md_path.with_suffix(".html")
    md = md_path.read_text(encoding="utf-8")
    out_path.write_text(_sanitize(render_dashboard_html(md)), encoding="utf-8")
    return out_path


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit("usage: md_to_dashboard.py <report.md> [out.html]")
    out = convert(Path(argv[0]), Path(argv[1]) if len(argv) > 1 else None)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
