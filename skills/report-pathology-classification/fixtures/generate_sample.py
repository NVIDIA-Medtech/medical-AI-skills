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

"""Generate the synthetic brain/spine MRI findings fixture for
report-pathology-classification.

All study ids and findings are fabricated and contain no real PHI. The findings
use the exact keyword terms in ``data/pathologies.json`` (and only those), so
the deterministic mock classifier yields a complete 0/1 label vector per report
(label_coverage_rate = 1.0) with no invalid labels. Each report deliberately
contains a few positive pathology keywords so some labels are 1 and the vector
is always full.

The mock classifier is keyword-presence only (no negation parsing), so the
findings here state positives directly and never embed a pathology term inside a
negated clause.
"""

import csv
from pathlib import Path

# Each report's findings text is built only from terms the mock recognizes,
# arranged so the intended label vector is exact. Comments note expected
# positives.
ROWS = [
    {
        # gliosis, infarction
        "study_uid": "STUDY-0001",
        "findings": (
            "Bilateral periventricular white matter shows gliotic signal changes "
            "consistent with chronic gliosis. A chronic right occipital infarction "
            "is noted. Midline structures are in normal position."
        ),
    },
    {
        # arachnoid cyst, ventriculomegaly
        "study_uid": "STUDY-0002",
        "findings": (
            "There is an arachnoid cyst in the right frontal region measuring a few "
            "millimeters. The ventricular system shows ventriculomegaly. No mass "
            "effect on adjacent structures."
        ),
    },
    {
        # cerebral atrophy, encephalomalacia
        "study_uid": "STUDY-0003",
        "findings": (
            "Diffuse cerebral atrophy with widened sulci and generalized volume loss. "
            "A region of encephalomalacia is seen in the left frontal lobe. No acute "
            "abnormality."
        ),
    },
    {
        # empty sella, pituitary adenoma, mastoiditis
        "study_uid": "STUDY-0004",
        "findings": (
            "Partial empty sella appearance of the sella turcica. A pituitary adenoma "
            "(microadenoma) is suspected on the left. Fluid signal in the right mastoid "
            "air cells compatible with mastoiditis."
        ),
    },
    {
        # meningioma only
        "study_uid": "STUDY-0005",
        "findings": (
            "An extra-axial dural-based lesion in the left convexity is compatible with "
            "meningioma. Surrounding parenchyma is unremarkable. Paranasal sinuses are "
            "clear."
        ),
    },
    {
        # clean control: no recognized pathology terms -> all-zero vector
        "study_uid": "STUDY-0006",
        "findings": (
            "Brain parenchyma demonstrates normal signal intensity. The ventricular "
            "system is symmetric and of normal caliber. No focal lesion. Visualized "
            "orbits and paranasal sinuses are clear."
        ),
    },
]

COLUMNS = ["study_uid", "findings", "clinical_information", "technique", "impression"]


def write(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for row in ROWS:
            full = {c: "" for c in COLUMNS}
            full.update(row)
            writer.writerow(full)


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "sample_reports_mr_findings.csv"
    write(out)
    print(f"wrote {out} ({len(ROWS)} rows)")
