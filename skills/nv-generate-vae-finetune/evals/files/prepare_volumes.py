# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

"""Materialize a synthetic CT/MR input bundle for both sides of the evaluation."""

import json
import sys
from pathlib import Path

import nibabel as nib
import numpy as np


def main(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    x, y, z = np.ogrid[:64, :64, :64]
    datalist = {}
    for split, center in (("training", 28), ("validation", 34)):
        radius = (x - center) ** 2 + (y - 32) ** 2 + (z - 32) ** 2
        entries = []
        for modality, background, peak in (("ct", -1000, 80), ("mri", 0, 400)):
            pixels = np.where(radius < 24**2, peak - radius // 12, background).astype(np.int16)
            name = f"{split}_{modality}.nii.gz"
            nib.save(nib.Nifti1Image(pixels, np.diag([1.5, 1.5, 2, 1])), root / name)
            entries.append({"image": name, "modality": modality})
        datalist[split] = entries
    (root / "vae_datalist.json").write_text(json.dumps(datalist, indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
