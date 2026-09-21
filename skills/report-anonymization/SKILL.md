---
name: report-anonymization
description: "Used for de-identifying English radiology reports with NeMo Anonymizer (GLiNER-PII + LLM): replaces detected PHI with bracketed role tokens like [PATIENT], [DOCTOR], [DATE] (MR-RATE reports stage 01). Not for regulatory de-identification or clinical use."
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - MedTech
    - reports
    - anonymization
    - de-identification
    - PHI
---

# Report Anonymization

## Purpose
- Used for de-identifying English radiology reports: PHI entities detected by [NeMo Anonymizer](https://github.com/NVIDIA-NeMo/Anonymizer) (GLiNER-PII detection + LLM augmentation/validation) are replaced in place with bracketed role tokens, e.g. `Patient: John A. Doe` -> `Patient: [PATIENT]`, `MRN: 12345678` -> `MRN: [PATIENT_MRN]`, `Dr. Emily Patel` -> `Dr. [DOCTOR]` (MR-RATE reports_preprocessing stage 01).
- Not for regulatory de-identification, clinical deployment, autonomous diagnosis, or patient-facing use.
- Manifest I/O: input is `reports_csv` (CSV with `study_uid` + `report_w_PHI` columns); output is `anonymization_summary` (JSON on stdout) plus `anonymized_reports.csv` and `run_report.json` in the output directory.

## Instructions
- Read `skill_manifest.yaml` before changing arguments, side effects, or validation gates.
- Set `NVIDIA_API_KEY` first: detection runs on remote models at build.nvidia.com. Without it the run fails with a connection/auth error.
- Run `scripts/anonymize_reports.py` through the documented command below. Pass the input CSV as the positional argument and a caller-provided run directory as `--output-dir`. Use `--full` to process every row; omit it to preview `--num-records` rows (cheap iteration that also writes `preview.parquet`).
- If a host agent exposes `run_script`, use `run_script("scripts/anonymize_reports.py", args=[REPORTS_CSV, "--output-dir", OUT, "--full"])`; otherwise run the Bash/Python command shown below.
- Do not hand-write a NeMo Anonymizer invocation for normal runs; this wrapper owns config, output shaping, telemetry, and the residual-leak audit. See `references/upstream-nemo-anonymizer.md` for the upstream contract.
- The single JSON object on stdout is the machine-readable summary; progress logs go to stderr.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/anonymize_reports.py` | Primary entrypoint declared by `skill_manifest.yaml`. | `REPORTS_CSV --output-dir DIR [--full] [--num-records N] [--text-column report_w_PHI] [--id-column study_uid] [--gliner-threshold 0.3] [--evaluate] [--no-emit-telemetry]` |

## Prerequisites
- Python 3.11+ with `nemo-anonymizer>=0.2.1`, `pandas`, `pyarrow`, and `tiktoken` (see `requirements.txt`).
- `NVIDIA_API_KEY` for the bundled build.nvidia.com providers (GLiNER-PII detector + `openai/gpt-oss-120b` validator/augmenter).
- Network access to `https://integrate.api.nvidia.com`.

| Variable | Required | Purpose |
|---|---|---|
| `NVIDIA_API_KEY` | yes | Auth for the bundled build.nvidia.com model providers used for detection. |
| `NEMO_TELEMETRY_ENABLED` | no | Set to `false` to disable NeMo Anonymizer's anonymous run telemetry (or pass `--no-emit-telemetry`). |

## Usage

Preview a few rows (cheap; writes `preview.parquet` trace):

```bash
export NVIDIA_API_KEY="nvapi-..."
python skills/report-anonymization/scripts/anonymize_reports.py \
  skills/report-anonymization/fixtures/batch00_reports_w_PHI.csv \
  --output-dir runs/report_anonymization_preview \
  --num-records 5
```

Full run on every row:

```bash
export NVIDIA_API_KEY="nvapi-..."
python skills/report-anonymization/scripts/anonymize_reports.py \
  /path/to/reports_w_PHI.csv \
  --output-dir runs/report_anonymization_full \
  --full
```

### Bundled test dataset

A 100-case **synthetic** test dataset (generated, no real PHI) is included at
`data/synthetic_reports_100_w_PHI.csv` (columns `study_uid`, `report_w_PHI`) so you
can exercise the skill end-to-end and reproduce the `BENCHMARK.md` results:

```bash
export NVIDIA_API_KEY="nvapi-..."
python skills/report-anonymization/scripts/anonymize_reports.py \
  skills/report-anonymization/data/synthetic_reports_100_w_PHI.csv \
  --output-dir runs/report_anonymization_100 \
  --full
```

The smaller `fixtures/batch00_reports_w_PHI.csv` remains the quick preview sample.

Evidence pack via the eval engine:

```bash
python -m eval_engine.run skills/report-anonymization \
  --fixture skills/report-anonymization/fixtures/batch00_reports_w_PHI.csv \
  --out runs/report_anonymization_pack
```

The stdout `anonymization_summary` JSON includes `n_reports`, `records_passed`/`records_failed`, `entities` (total + per-label counts), `residual_phi_leak` (informational verbatim replacement-map check), `pipeline_stages` (per NeMo detection iteration), and `telemetry` (wall-clock timings, throughput, and a tiktoken input-token estimate). The anonymized text is written to `<output-dir>/anonymized_reports.csv` (columns `study_uid,report`) and the full report to `<output-dir>/run_report.json`.

## Limitations
- Detection/validation run on remote LLMs at build.nvidia.com; the skill requires `NVIDIA_API_KEY` and network access and its output is non-deterministic (hence `reproducibility.mode: preflight`).
- Strict GLiNER label mode: only the listed PHI entity types are detected; entity types the detector never proposes are not replaced.
- `residual_phi_leak` is an informational verbatim replacement-map check, not a completeness guarantee; it does not detect PHI the model never mapped and skips originals shorter than 3 characters.
- Redact strategy only. Upstream NeMo Anonymizer also offers Substitute, Annotate, Hash, and Rewrite; those are out of scope for this stage-01 wrapper.
- Not for clinical deployment, regulatory de-identification, autonomous diagnosis, or patient-facing use.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| `Text column 'report_w_PHI' not in ...` | Wrong column or delimiter. | Pass `--text-column`/`--id-column`, or fix the CSV header. |
| `Workflow failed: Connection to model ... failed while running health checks` | `NVIDIA_API_KEY` unset/invalid, or no network to build.nvidia.com. | Export a valid `NVIDIA_API_KEY` and confirm access to `https://integrate.api.nvidia.com`. |
| Non-zero exit with `records_failed > 0` | Records dropped mid-pipeline (rate limits, transient API errors). | Inspect `run_report.json` `failed_records`; re-run. Dropped rows are infra issues, not strategy issues. |
| `No module named 'anonymizer'` | `nemo-anonymizer` not installed in the active env. | `pip install -r skills/report-anonymization/requirements.txt`. |
