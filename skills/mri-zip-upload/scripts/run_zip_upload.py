#!/usr/bin/env python3
"""Wrapper: run the real MR-RATE zip step with preflight + telemetry."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import run_step

UPSTREAM_REL = "src/mr_rate_preprocessing/mri_preprocessing/zip_and_upload.py"


def build_args(fx: Path, out: Path, device: str):
    return ["--input-dir", str(fx / "processed"),
            "--modalities-json", str(fx / "modalities.json"),
            "--batch-id", "batchTEST", "--output-dir", str(out),
            "--repo-id", "dummy/repo", "--skip-upload", "--num-zip-workers", "1"]


def main() -> int:
    ap = argparse.ArgumentParser(description="Run MR-RATE zip step (real upstream) with preflight + telemetry")
    ap.add_argument("--fixtures", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--mr-rate-root", required=True)
    ap.add_argument("--device", default="0")
    ap.add_argument("--preflight", action="store_true")
    a = ap.parse_args()
    return run_step("mri-zip-upload", "zip", mr_rate_root=a.mr_rate_root,
                    fixtures=a.fixtures, out=a.out, upstream_rel=UPSTREAM_REL,
                    build_args=build_args, deps=['numpy', 'nibabel'],
                    need_dcm2niix=False, need_gpu=False,
                    device=a.device, preflight_only=a.preflight)


if __name__ == "__main__":
    raise SystemExit(main())
