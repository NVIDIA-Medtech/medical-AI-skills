#!/usr/bin/env python3
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

"""Build generated binary artifacts for dicom_volume_quality_v1 fixtures."""

from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np

FIXTURE_DIR = Path(__file__).resolve().parent
PASS_PACK = FIXTURE_DIR / "pass_pack"
ARTIFACT = PASS_PACK / "artifacts" / "clean_axial.nii.gz"


def main() -> int:
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    data = np.full((64, 64, 32), -1000.0, dtype=np.float32)
    zz, yy, xx = np.ogrid[:32, :64, :64]
    blob = (xx - 42) ** 2 + (yy - 35) ** 2 + (zz - 16) ** 2 < 5**2
    data[np.moveaxis(blob, 0, 2)] = 60.0
    affine = np.array(
        [
            [-1.0, 0.0, 0.0, 0.0],
            [0.0, -1.0, 0.0, 0.0],
            [0.0, 0.0, 2.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )
    nib.save(nib.Nifti1Image(data, affine), str(ARTIFACT))
    print(f"wrote {ARTIFACT.relative_to(FIXTURE_DIR.parents[2])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
