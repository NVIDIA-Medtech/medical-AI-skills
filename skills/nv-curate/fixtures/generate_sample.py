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

"""Generate the synthetic raw-data fixture + datasources.json for nv-curate.

The synthetic Turkish reports carry fabricated PHI in the forms the
report-anonymization mock redacts, and medical text drawn from the
report-translation mock vocabulary, so the full mock pipeline
(anonymize -> translate -> structure -> classify) flows end to end. No real PHI.
"""

import csv
import json
from pathlib import Path

ROWS = [
    {
        "UID": "MR-0001",
        "report": (
            "Tetkik Dr. Mehmet Demir tarafindan degerlendirildi. Hasta Ayse Kara, "
            "45 yasinda kadin. Tarih: 15.03.2024. Medipol Mega Üniversite Hastanesi. "
            "Accession: A12345. Bulgular: bilateral beyaz cevherde gliotik sinyal "
            "degisiklikleri izlendi ve orta hat yapilari normal konumda. "
            "Sonuc: kronik enfarkt ile uyumlu lezyon mevcuttur."
        ),
    },
    {
        "UID": "MR-0002",
        "report": (
            "Prof. Dr. Ali Veli raporu hazirladi. Hasta Fatma Sahin, 60 yasinda kadin. "
            "Tarih: 10.01.2023. Medipol Koşuyolu Hastanesi. Accession: A23456. "
            "Bulgular: sag frontal lobda araknoid kist ile uyumlu lezyon izlendi ve "
            "ventrikuler sistem normal genislikte. Sonuc: araknoid kist mevcuttur."
        ),
    },
    {
        "UID": "MR-0003",
        "report": (
            "Uzm. Dr. Zeynep Aydin tarafindan raporlandi. Hasta Hasan Celik, "
            "50 yasinda erkek. Tarih: 01.02.2024. Sisli Etfal Hastanesi. "
            "Accession: A34567. Bulgular: hipofiz bezi normal boyutlarda ve paranazal "
            "sinusler havali. patolojik sinyal degisikligi saptanmadi. "
            "Sonuc: belirgin lezyon yok."
        ),
    },
]

COLUMNS = ["UID", "report", "clinical_information", "technique", "findings", "impression"]

DATASOURCES = {
    "name": "mrbrain",
    "site": "synthetic-demo",
    "raw_data": {
        "path": "raw_data",
        "reports_glob": "*_reports*.csv",
        "images_glob": "**/*.nii.gz",
    },
    "target": {"ai_ready": True},
    "pipeline": {
        "steps": ["anonymize", "translate", "structure", "classify"],
        "mode": "mock",
        "model": "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4",
        "id_col": "UID",
        "text_col": "report",
    },
    "task": {"type": "analysis", "model": "nv-generate-mr-brain", "modality": "mri_t1"},
    "join_key": "study_uid",
}


def write(base: Path) -> None:
    raw_dir = base / "raw_data"
    raw_dir.mkdir(parents=True, exist_ok=True)
    csv_path = raw_dir / "mrbrain_reports_turkish.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for row in ROWS:
            full = {c: "" for c in COLUMNS}
            full.update(row)
            writer.writerow(full)
    (base / "datasources.json").write_text(json.dumps(DATASOURCES, indent=2), encoding="utf-8")


if __name__ == "__main__":
    base = Path(__file__).resolve().parent
    write(base)
    print(
        f"wrote {base/'raw_data'/'mrbrain_reports_turkish.csv'} ({len(ROWS)} rows) and {base/'datasources.json'}"
    )
