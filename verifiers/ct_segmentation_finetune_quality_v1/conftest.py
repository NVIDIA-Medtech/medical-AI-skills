"""Regenerate ct_segmentation_finetune_quality_v1 synthetic packs on demand.

The fixture packs (pass_pack, regress_pack, bad_audit_pack) are gitignored
because the checkpoint stand-in is a 1.2 MB binary blob. This conftest
invokes fixtures/build_fixtures.py before any test in this verifier runs.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

VERIFIER_DIR = Path(__file__).resolve().parent
BUILD = VERIFIER_DIR / "fixtures" / "build_fixtures.py"


def _fixtures_present() -> bool:
    needed = [
        VERIFIER_DIR / "fixtures" / "pass_pack" / "checkpoint.pt",
        VERIFIER_DIR / "fixtures" / "regress_pack" / "checkpoint.pt",
        VERIFIER_DIR / "fixtures" / "bad_audit_pack" / "checkpoint.pt",
    ]
    return all(p.exists() for p in needed)


def _build_fixtures() -> None:
    spec = importlib.util.spec_from_file_location("build_finetune_fixtures", BUILD)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_finetune_fixtures"] = module
    spec.loader.exec_module(module)
    module.main()


if not _fixtures_present():
    _build_fixtures()
