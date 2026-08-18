<!--
SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: Apache-2.0
-->

# medical-anonymization

General-purpose medical data anonymization: [NeMo Anonymizer](https://github.com/NVIDIA-NeMo/Anonymizer) for unstructured text plus deterministic policies for CSV identifiers and DICOM metadata headers.

> **Engineering / research use only.** Not a regulatory de-identifier. Review output before sharing.

## Input lanes

| Lane | Entry | API key |
|------|-------|---------|
| DICOM metadata CSV | `--input-kind dicom-metadata-csv` | No |
| Mixed EHR/report CSV | auto or `--input-kind csv` | Yes (for text columns) |
| Plain text | `--input-kind text` | Yes |

## Strategies

**NeMo (text):** `redact`, `substitute`, `annotate`, `hash`, `rewrite`

**Structured / DICOM:** `keep`, `drop`, `redact`, `hash`, `uid_remap`, `date_shift`, `bucket`

## Quick start

```bash
# DICOM metadata (local)
python skills/medical-anonymization/scripts/anonymize_medical_data.py \
  skills/medical-anonymization/fixtures/sample_dicom_metadata.csv \
  --output-dir runs/dicom --input-kind dicom-metadata-csv

# EHR CSV — hash MRN, skip NeMo
python skills/medical-anonymization/scripts/anonymize_medical_data.py \
  skills/medical-anonymization/fixtures/sample_ehr.csv \
  --output-dir runs/ehr --local-only

# Reports (legacy wrapper still works)
export NVIDIA_API_KEY="nvapi-..."
python skills/medical-anonymization/scripts/anonymize_reports.py \
  skills/medical-anonymization/fixtures/batch00_reports_w_PHI.csv \
  --output-dir runs/reports --num-records 5
```

See `SKILL.md` for full usage and `policies/default-medical.yaml` for field policies.

## Layout

```
medical-anonymization/
├── scripts/
│   ├── anonymize_medical_data.py   # primary entrypoint
│   ├── anonymize_reports.py        # legacy radiology CSV wrapper
│   ├── dicom_policy.py
│   ├── structured_policy.py
│   └── nemo_text.py
├── policies/default-medical.yaml
├── fixtures/                       # sample_note.txt, sample_ehr.csv, sample_dicom_metadata.csv
└── validators/output_schema.json
```

## License

Apache-2.0
