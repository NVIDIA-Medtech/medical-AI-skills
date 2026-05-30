"""Regenerate ct_segmentation_quality_v1 NIfTI fixtures on demand.

Binary fixtures (.nii.gz, generated output.json/manifest.json/
validation_summary.json under fixtures/*_pack/) are not committed. This
conftest invokes fixtures/build_fixtures.py before any test in this
verifier runs so the pass_pack / fragmented_pack / gt_pass_pack
directories are populated.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

VERIFIER_DIR = Path(__file__).resolve().parent
BUILD = VERIFIER_DIR / "fixtures" / "build_fixtures.py"


def _fixtures_present() -> bool:
    needed = [
        VERIFIER_DIR / "fixtures" / "pass_pack" / "predicted_seg.nii.gz",
        VERIFIER_DIR / "fixtures" / "fragmented_pack" / "predicted_seg.nii.gz",
        VERIFIER_DIR / "fixtures" / "gt_pass_pack" / "predicted_seg.nii.gz",
        VERIFIER_DIR / "fixtures" / "gt_pass_pack" / "reference_seg.nii.gz",
    ]
    return all(p.exists() for p in needed)


def _build_fixtures() -> None:
    spec = importlib.util.spec_from_file_location("build_fixtures", BUILD)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_fixtures"] = module
    spec.loader.exec_module(module)
    module.main()


if not _fixtures_present():
    _build_fixtures()
