#!/usr/bin/env python3
"""Wrapper: run the whole MR-RATE MRI pipeline (real runners) with preflight + telemetry."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import run_pipeline


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the full MR-RATE MRI pipeline (real runners) with preflight + telemetry")
    ap.add_argument("--fixtures", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--mr-rate-root", required=True)
    ap.add_argument("--device", default="0")
    ap.add_argument("--preflight", action="store_true")
    a = ap.parse_args()
    return run_pipeline("nv-curate-mri", "orchestrator", mr_rate_root=a.mr_rate_root,
                        fixtures=a.fixtures, out=a.out, device=a.device,
                        preflight_only=a.preflight)


if __name__ == "__main__":
    raise SystemExit(main())
