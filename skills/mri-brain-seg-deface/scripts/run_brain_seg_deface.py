#!/usr/bin/env python3
"""Wrapper: run the real MR-RATE brainseg step with preflight + telemetry."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import run_step

UPSTREAM_REL = "src/mr_rate_preprocessing/mri_preprocessing/brain_segmentation_and_defacing.py"


def build_args(fx: Path, out: Path, device: str):
    return ["--modalities-json", str(fx / "modalities.json"),
            "--raw-dir", str(fx / "raw_niftis"),
            "--output-dir", str(out / "processed"), "--device", device]


def main() -> int:
    ap = argparse.ArgumentParser(description="Run MR-RATE brainseg step (real upstream) with preflight + telemetry")
    ap.add_argument("--fixtures", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--mr-rate-root", required=True)
    ap.add_argument("--device", default="0")
    ap.add_argument("--preflight", action="store_true")
    a = ap.parse_args()
    return run_step("mri-brain-seg-deface", "brainseg", mr_rate_root=a.mr_rate_root,
                    fixtures=a.fixtures, out=a.out, upstream_rel=UPSTREAM_REL,
                    build_args=build_args, deps=['torch', 'brainles_hd_bet', 'SimpleITK', 'nibabel', 'numpy', 'scipy'],
                    need_dcm2niix=False, need_gpu=True,
                    device=a.device, preflight_only=a.preflight)


if __name__ == "__main__":
    raise SystemExit(main())
