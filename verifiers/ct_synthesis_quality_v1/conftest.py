# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Regenerate ct_synthesis_quality_v1 synthetic packs on demand.

The fixture packs contain NIfTI image/label files which are gitignored.
This conftest builds them before any test in this verifier runs.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

VERIFIER_DIR = Path(__file__).resolve().parent
BUILD = VERIFIER_DIR / "fixtures" / "build_fixtures.py"


def _fixtures_present() -> bool:
    # Check for the NIfTI pairs, not the JSONs — the JSONs are committed but
    # the .nii.gz files are gitignored, so CI fresh-checkouts need a rebuild.
    fixture_root = VERIFIER_DIR / "fixtures"
    for pack in ("pass_pack", "constant_image_pack", "out_of_range_label_pack"):
        pack_dir = fixture_root / pack
        if not list(pack_dir.glob("*_image.nii.gz")):
            return False
        if not list(pack_dir.glob("*_label.nii.gz")):
            return False
    return True


def _build_fixtures() -> None:
    spec = importlib.util.spec_from_file_location("build_synthesis_fixtures", BUILD)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_synthesis_fixtures"] = module
    spec.loader.exec_module(module)
    module.main()


if not _fixtures_present():
    _build_fixtures()
