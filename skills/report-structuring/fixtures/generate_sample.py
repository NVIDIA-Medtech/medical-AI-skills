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

"""Generate the synthetic English-report fixture for report-structuring.

Every report is fabricated and contains no real PHI. Each report has the four
canonical section headers (``Clinical Information:``, ``Technique:``,
``Findings:``, ``Impression:``) that the mock structurer splits on. Findings are
written as flowing sentences (no bullet markers) and impressions as one item per
line, so the deterministic mock yields a clean evidence pack: 100% parse success,
100% section completeness, 0 format violations, and a >= 0.9 QC pass-rate.

The header labels here must stay in lockstep with SECTION_HEADERS in
scripts/run_report_structuring.py so the split, the format-leak check, and the
fixture all agree.
"""

import csv
from pathlib import Path

ROWS = [
    {
        "UID": "STUDY-0001",
        "report": (
            "BRAIN MRI REPORT\n"
            "Clinical Information: Headache and intermittent dizziness for three weeks.\n"
            "Technique: Axial and sagittal sequences were obtained without contrast.\n"
            "Findings: The cerebral hemispheres show normal gray-white differentiation. "
            "A few scattered foci of signal change are seen in the periventricular white matter. "
            "Midline structures are in normal position and the ventricular system is normal in size.\n"
            "Impression: Mild nonspecific white matter signal changes. No acute intracranial abnormality."
        ),
    },
    {
        "UID": "STUDY-0002",
        "report": (
            "CRANIAL MRI REPORT\n"
            "Clinical Information: Follow-up of a previously noted arachnoid cyst.\n"
            "Technique: Multiplanar sequences were acquired before and after contrast.\n"
            "Findings: A well-defined extra-axial lesion in the right frontal region is consistent "
            "with an arachnoid cyst and is stable in size. The remaining brain parenchyma is unremarkable. "
            "There is no mass effect and the ventricles are of normal width.\n"
            "Impression: Stable right frontal arachnoid cyst. No new intracranial lesion."
        ),
    },
    {
        "UID": "STUDY-0003",
        "report": (
            "BRAIN MRI REPORT\n"
            "Clinical Information: Prior cerebellar infarct, now with balance complaints.\n"
            "Technique: Standard sequences were performed without contrast.\n"
            "Findings: There is an area of encephalomalacia in the left cerebellar hemisphere "
            "compatible with a chronic infarct sequela. No restricted diffusion is identified to "
            "suggest an acute event. The brainstem and fourth ventricle appear normal.\n"
            "Impression: Chronic left cerebellar infarct sequela. No acute ischemic change."
        ),
    },
    {
        "UID": "STUDY-0004",
        "report": (
            "CRANIAL MRI REPORT\n"
            "Clinical Information: Screening study in a patient with chronic sinus symptoms.\n"
            "Technique: Axial and coronal sequences were obtained without contrast.\n"
            "Findings: No intracranial pathologic signal change is detected. The paranasal sinuses "
            "are clear and well aerated. The orbits and the visualized skull base are unremarkable.\n"
            "Impression: Normal brain study. No significant abnormality."
        ),
    },
    {
        "UID": "STUDY-0005",
        "report": (
            "BRAIN MRI REPORT\n"
            "Clinical Information: Evaluation of the pituitary region for hormonal imbalance.\n"
            "Technique: Dedicated thin-section sequences were acquired before and after contrast.\n"
            "Findings: The pituitary gland is normal in height and shows homogeneous enhancement. "
            "The optic chiasm and cavernous sinuses are unremarkable. There is no empty sella appearance "
            "and no evidence of a focal adenoma.\n"
            "Impression: Normal pituitary appearance. No focal lesion identified."
        ),
    },
]

COLUMNS = ["UID", "report"]


def write(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for row in ROWS:
            writer.writerow({c: row.get(c, "") for c in COLUMNS})


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "sample_reports_english.csv"
    write(out)
    print(f"wrote {out} ({len(ROWS)} rows)")
