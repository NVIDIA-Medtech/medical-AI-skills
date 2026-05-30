#!/usr/bin/env python3
"""Build generated artifact dependencies for mr_synthesis_quality_v1 fixtures."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
CT_SYNTH_BUILDER = (
    REPO_ROOT
    / "verifiers"
    / "ct_synthesis_quality_v1"
    / "fixtures"
    / "build_fixtures.py"
)


def main() -> int:
    proc = subprocess.run(
        [sys.executable, str(CT_SYNTH_BUILDER)],
        cwd=REPO_ROOT,
        text=True,
    )
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
