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

"""Generate the synthetic anonymized-Turkish-report fixture for report-translation.

All reports are fabricated and contain no real PHI: patient/doctor names, dates,
hospitals, and accession numbers are already replaced by ``[token_N]``
anonymization placeholders (this is the input to MR-RATE stage 02, i.e. the
output of stage 01). The Turkish prose is drawn ONLY from the small phrase set
that the mock translator knows, so the mock yields a clean evidence pack:
- every report translates to fully English (non_english_rate = 0.0),
- every ``[token_N]`` placeholder survives translation (preservation_rate = 1.0),
- every translation QC verdict is PASS (qc.pass_rate = 1.0).

Tokens use a lowercase ``[name_N]`` form (e.g. ``[token_1]``, ``[hospital_e2]``)
and are language-neutral, so they neither trigger language detection nor get
rewritten by the phrase dictionary.
"""

import csv
from pathlib import Path

# Each report is assembled from phrase-dictionary keys + anonymization tokens +
# numbers/units (language-neutral). Two reports intentionally carry no token so
# n_reports_with_tokens < n_reports, exercising that branch of the metric.
ROWS = [
    {
        "UID": "STUDY-0001",
        "Anonymized_Rapor": (
            "Beyin MRG incelemesi kontrastsiz. "
            "Klinik bilgi: hasta [token_1] , 45 yasinda kadin . Tarih [token_2] . [token_3] . "
            "Bulgular : bilateral beyaz cevherde gliotik sinyal degisiklikleri izlendi . "
            "orta hat yapilari normal konumda . "
            "Sonuc : patolojik sinyal degisikligi saptanmadi ."
        ),
    },
    {
        "UID": "STUDY-0002",
        "Anonymized_Rapor": (
            "Kraniyal MRG incelemesi kontrastli . "
            "Klinik bilgi: hasta [token_4] , 60 yasinda erkek . Tarih [token_5] . [hospital_e1] . "
            "Bulgular : sag frontal lobda 8 mm boyutunda araknoid kist ile uyumlu lezyon izlendi . "
            "ventrikuler sistem normal genislikte . "
            "Sonuc : sol serebellar hemisfer normal konumda ."
        ),
    },
    {
        "UID": "STUDY-0003",
        "Anonymized_Rapor": (
            "Beyin MRG incelemesi kontrastsiz . "
            "Bulgular : sol serebellar hemisfer kronik enfarkt ile uyumlu . "
            "beyin sapi ve korpus kallozum normal konumda . "
            "Sonuc : patolojik sinyal degisikligi saptanmadi ."
        ),
    },
    {
        "UID": "STUDY-0004",
        "Anonymized_Rapor": (
            "Beyin MRG incelemesi kontrastsiz . "
            "Klinik bilgi: hasta [token_6] , 33 yasinda kadin . Tarih [token_7] . [token_8] . "
            "Bulgular : patolojik sinyal degisikligi saptanmadi . "
            "paranazal sinusler havali . lateral ventrikuller normal genislikte . "
            "Sonuc : orta hat yapilari normal konumda ."
        ),
    },
    {
        "UID": "STUDY-0005",
        "Anonymized_Rapor": (
            "Kraniyal MRG incelemesi kontrastli . "
            "Bulgular : hipofiz bezi normal boyutlarda . "
            "milimetrik araknoid kist sag frontal lobda izlendi . "
            "Sonuc : iskemik sinyal degisiklikleri yok ."
        ),
    },
    {
        "UID": "STUDY-0006",
        "Anonymized_Rapor": (
            "Beyin MRG incelemesi kontrastsiz . "
            "Klinik bilgi: hasta [token_9] , 52 yasinda erkek . Tarih [token_10] . [hospital_e2] . "
            "Bulgular : bilateral beyaz cevher normal . "
            "lateral ventrikul ve beyin sapi normal konumda . "
            "Sonuc : patolojik sinyal degisikligi saptanmadi ."
        ),
    },
]

COLUMNS = ["UID", "Anonymized_Rapor"]


def write(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for row in ROWS:
            writer.writerow(row)


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "sample_reports_turkish_anonymized.csv"
    write(out)
    print(f"wrote {out} ({len(ROWS)} rows)")
