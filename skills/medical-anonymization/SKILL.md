---
name: medical-anonymization
description: "General-purpose medical data anonymization: NeMo Anonymizer for unstructured text (redact, substitute, annotate, hash, rewrite) plus deterministic policies for CSV identifiers and DICOM metadata headers. Not for regulatory de-identification or clinical use."
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - MedTech
    - anonymization
    - de-identification
    - PHI
    - DICOM
    - EHR
    - reports
---

# Medical Anonymization

## Purpose

General-purpose anonymization for medical datasets across three input lanes:

| Lane | Input | Engine |
|------|-------|--------|
| **Text** | `.txt` or single text column | NeMo Anonymizer |
| **CSV** | Mixed columns (notes + identifiers) | NeMo for text columns + deterministic policy for structured columns |
| **DICOM metadata** | Flat CSV export of DICOM tags | Policy engine → canonical **JSONL** (+ optional flat CSV) |

Not for regulatory de-identification, clinical deployment, or patient-facing use.

## NeMo text strategies

From [NeMo Anonymizer](https://github.com/NVIDIA-NeMo/Anonymizer) replace/rewrite modes:

| Strategy | What it does |
|----------|----------------|
| `redact` | Replace entities with tokens, e.g. `[PATIENT]` |
| `substitute` | LLM-generated synthetic replacements |
| `annotate` | Tag entities, e.g. `<John Doe, patient>` |
| `hash` | Deterministic hash tokens per entity |
| `rewrite` | Full-passage LLM rewrite with evaluate-repair loop |

## Structured / DICOM actions

Deterministic (no LLM), configured in `policies/default-medical.yaml`:

| Action | Use |
|--------|-----|
| `keep` | Leave value unchanged |
| `drop` | Remove field/column |
| `redact` | Replace with template token |
| `hash` | SHA-256 digest (truncated) |
| `uid_remap` | Deterministic pseudonym UID |
| `date_shift` | Per-record consistent date offset |
| `bucket` | Coarse bucketing (e.g. age ranges) |

DICOM metadata outputs (`--metadata-format nested|kv|both`, default `both`). Wide CSV is melted to `(record_id, field, value)` before policy runs.

| File | Shape | Best for |
|------|-------|----------|
| `deidentified_metadata_nested.jsonl` | 1 line / study | LLM per-study context (fewest tokens with action metadata) |
| `deidentified_metadata_kv.jsonl` | 1 line / field + action | Stream parsing, field filters |
| `deidentified_metadata_kv_compact.jsonl` | 1 line / field, value only | KV without action overhead |

Shareable audit: `audit.jsonl` (hashes, not raw PHI).

### Format evaluation (`dicom_metadata_full.csv`, 85 studies)

```bash
python scripts/evaluate_metadata_formats.py /path/to/dicom_metadata_full.csv --output-dir runs/format_eval
```

| Format | Total tokens | Median / study | Parse safety |
|--------|-------------|----------------|--------------|
| Input wide CSV | ~83k | ~964 | Fragile (column alignment) |
| Nested JSONL | ~447k | ~5,054 | One object / study |
| KV compact | ~448k | ~5,171 | One line / field |
| KV full | ~585k | ~6,782 | Self-describing lines |

Nested wins slightly on tokens per study; KV wins on stream-parse safety. Wide CSV is ~5× smaller but loses per-field `action` audit.

Report: `MRI_DICOM_HEAD_DATA_WITH_PHI/deidentified/metadata/format_eval/format_evaluation.json`

## Instructions

- Read `skill_manifest.yaml` before changing arguments or validation gates.
- Primary entrypoint: `scripts/anonymize_medical_data.py`
- Legacy report wrapper: `scripts/anonymize_reports.py` (radiology CSV only)
- Set `NVIDIA_API_KEY` for NeMo text passes (remote build.nvidia.com). DICOM-metadata and structured-only runs work with `--local-only` (no API key).
- Policy file: `policies/default-medical.yaml` (override with `--policy`)

## Usage

### DICOM metadata (local, no API key)

```bash
python skills/medical-anonymization/scripts/anonymize_medical_data.py \
  skills/medical-anonymization/fixtures/sample_dicom_metadata.csv \
  --output-dir runs/dicom_anon \
  --input-kind dicom-metadata-csv \
  --id-column study_uid
```

### Mixed EHR CSV (structured + text)

```bash
export NVIDIA_API_KEY="nvapi-..."
python skills/medical-anonymization/scripts/anonymize_medical_data.py \
  skills/medical-anonymization/fixtures/sample_ehr.csv \
  --output-dir runs/ehr_anon \
  --text-columns note_text \
  --id-column record_id \
  --text-strategy redact \
  --full
```

Structured columns only (no NeMo):

```bash
python skills/medical-anonymization/scripts/anonymize_medical_data.py \
  skills/medical-anonymization/fixtures/sample_ehr.csv \
  --output-dir runs/ehr_struct \
  --local-only
```

### Plain text file

```bash
export NVIDIA_API_KEY="nvapi-..."
python skills/medical-anonymization/scripts/anonymize_medical_data.py \
  skills/medical-anonymization/fixtures/sample_note.txt \
  --output-dir runs/note_anon \
  --input-kind text \
  --text-strategy substitute
```

### All NeMo strategies

```bash
--text-strategy redact|substitute|annotate|hash|rewrite
```

## Outputs

| Artifact | When |
|----------|------|
| `run_report.json` | Always |
| `deidentified_metadata_nested.jsonl` | DICOM metadata lane |
| `deidentified_metadata_kv.jsonl` | DICOM metadata lane (long format) |
| `deidentified_metadata_kv_compact.jsonl` | DICOM metadata lane (minimal long format) |
| `audit.jsonl` | DICOM metadata lane |
| `deidentified_metadata_flat.csv` | DICOM metadata lane (convenience) |
| `anonymized_data.csv` | CSV lane |
| `anonymized_text.txt` | Text lane |

Stdout: single JSON summary (Medical AI Skills invariant).

## Limitations

- NeMo text passes require `NVIDIA_API_KEY` and network; output is non-deterministic.
- DICOM policy operates on **flat CSV exports**, not raw `.dcm` files (use `dicom-metadata-extract` upstream).
- Structured actions are policy-driven heuristics, not a certified de-identification profile.
- `rewrite` mode changes prose structure; use when bracketed redaction is insufficient.

## Troubleshooting

| Error | Fix |
|-------|-----|
| `No module named 'yaml'` | `pip install pyyaml` or `pip install -r requirements.txt` |
| NeMo auth failure | Export `NVIDIA_API_KEY` or use `--local-only` for structured/DICOM paths |
| Wrong lane detected | Pass explicit `--input-kind` |
