#!/usr/bin/env python3
"""Wrapper: run the real MR-RATE dcm2niix step with preflight + telemetry."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import run_step

UPSTREAM_REL = "src/mr_rate_preprocessing/mri_preprocessing/dcm2nii.py"


def build_args(fx: Path, out: Path, device: str):
    return ["--input-csv", str(fx / "dicom_folder_paths.csv"),
            "--output-dir", str(out / "niftis"), "--max-workers", "2"]


def main() -> int:
    ap = argparse.ArgumentParser(description="Run MR-RATE dcm2niix step (real upstream) with preflight + telemetry")
    ap.add_argument("--fixtures", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--mr-rate-root", required=True)
    ap.add_argument("--device", default="0")
    ap.add_argument("--preflight", action="store_true")
    a = ap.parse_args()
    return run_step("mri-dcm2niix", "dcm2niix", mr_rate_root=a.mr_rate_root,
                    fixtures=a.fixtures, out=a.out, upstream_rel=UPSTREAM_REL,
                    build_args=build_args, deps=['pandas', 'pydicom'],
                    need_dcm2niix=True, need_gpu=False,
                    device=a.device, preflight_only=a.preflight)


if __name__ == "__main__":
    raise SystemExit(main())
