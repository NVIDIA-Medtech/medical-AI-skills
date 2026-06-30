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

"""Generate the synthetic Turkish-report fixture for report-anonymization.

All names, dates, hospitals, and accession numbers are fabricated and contain
no real PHI. The PHI appears only in forms the mock anonymizer can redact, so
the fixture deterministically yields a clean evidence pack (0 leak, 0 malformed,
0 inconsistent).
"""

import csv
from pathlib import Path

ROWS = [
    {
        "UID": "STUDY-0001",
        "report": (
            "Tetkik Dr. Mehmet Demir tarafindan degerlendirildi. Hasta Ayse Kara, "
            "45 yasinda kadin. Tarih: 15.03.2024. Medipol Mega Üniversite Hastanesi. "
            "Accession: A12345. Bulgular: Bilateral periventrikuler beyaz cevherde "
            "gliotik sinyal degisiklikleri izlendi. Orta hat yapilari normal konumda."
        ),
    },
    {
        "UID": "STUDY-0002",
        "report": (
            "Prof. Dr. Ali Veli raporu hazirladi. Hasta Fatma Sahin daha once "
            "10.01.2023 tarihinde Sisli Etfal Hastanesi'nde gorulmus. Kontrol: "
            "20.05.2024, Medipol Koşuyolu Hastanesi. Accession: A23456. Bulgular: "
            "Sag frontal lobda 8 mm boyutunda araknoid kist ile uyumlu lezyon. "
            "Ventrikuler sistem normal genislikte."
        ),
    },
    {
        "UID": "STUDY-0003",
        "report": (
            "Uzm. Dr. Zeynep Aydin tarafindan raporlandi. Hasta Hasan Celik, "
            "60 yasinda erkek. 01.02.2024 tarihli inceleme. Medipol Pendik Üniversite "
            "Hastanesi. Accession: A34567. Bulgular: Sol serebellar hemisferde kronik "
            "enfarkt sekeli izlendi. Belirgin kitle etkisi yok."
        ),
    },
    {
        "UID": "STUDY-0004",
        "report": (
            "Dr. Cem Oz degerlendirdi. Hasta Elif Yildiz, 33 yasinda kadin. Tarih: "
            "12.06.2024. Medipol Mega Üniversite Hastanesi. Accession: A45678. "
            "Bulgular: Intrakraniyal patolojik sinyal degisikligi saptanmadi. "
            "Paranazal sinusler havali."
        ),
    },
    {
        "UID": "STUDY-0005",
        "report": (
            "Op. Dr. Burak Sen raporu hazirladi. Hasta Deniz Acar daha once "
            "05.05.2022 tarihinde Acıbadem Kozyatağı Hastanesi'nde tetkik edilmis. "
            "Kontrol: 18.04.2024, Medipol Koşuyolu Hastanesi. Accession: A56789. "
            "Bulgular: Hipofiz bezi normal boyutlarda. Empty sella gorunumu yok."
        ),
    },
]

COLUMNS = ["UID", "report", "clinical_information", "technique", "findings", "impression"]


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
    out = Path(__file__).resolve().parent / "sample_reports_turkish.csv"
    write(out)
    print(f"wrote {out} ({len(ROWS)} rows)")
