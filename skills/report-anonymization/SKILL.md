---
name: report-anonymization
description: Used for de-identifying Turkish radiology reports by replacing names, dates, hospitals, and accession numbers with [entity_N] tokens (MR-RATE reports stage 01). Not for regulatory de-identification or clinical use.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - MedTech
    - reports
    - anonymization
    - de-identification
---

# Report Anonymization

## Purpose
- Used for de-identifying Turkish radiology reports: detected names, dates, hospitals, radiologist names, and accession numbers are replaced with deterministic `[entity_N]` tokens, and a `Token_Mapping` is recorded per report (MR-RATE reports_preprocessing stage 01).
- Not for regulatory de-identification, clinical deployment, or patient-facing use.
- Manifest I/O: input is `reports_csv` (CSV with `UID` + `report` columns); output is `anonymization_summary` (JSON on stdout) plus `anonymized.csv` in the run directory.

## Instructions
- Read `skill_manifest.yaml` before changing arguments, side effects, or validation gates.
- Run `scripts/run_anonymization.py` through the documented command below; keep outputs under a caller-provided run directory (`--out`).
- If a host agent exposes `run_script`, use `run_script("scripts/run_anonymization.py", args=[...])`; otherwise run the Bash/Python command shown below.
- Default `--mode mock` is GPU-free and stdlib-only (deterministic rule-based redaction). Use `--mode live` for real de-identification with the upstream vLLM model.
- After a run, audit the evidence pack with `medagent.verifiers.report_anonymization_quality_v1` before treating it as reviewed evidence.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/run_anonymization.py` | Primary entrypoint declared by `skill_manifest.yaml`. | `REPORTS_CSV [--out DIR] [--mode mock\|live] [--model HF_ID] [--limit N] [--id-col UID] [--text-col report] [--mr-rate-root DIR] [--cuda-visible-devices N]` |

## Prerequisites
- `--mode mock` (default): Python 3.10+ only — no GPU, no network, no extra packages.
- `--mode live`: a CUDA GPU, `vllm`, and the configured vLLM model (cached or downloadable). The upstream script `01_anonymization/anonymize_reports_parallel.py` must be reachable via `--mr-rate-root` or `$MR_RATE_REPORTS_ROOT`.

| Variable | Mode | Purpose |
|---|---|---|
| `MR_RATE_REPORTS_ROOT` | live | Path to the `reports_preprocessing` directory for upstream-script lookup. |
| `CUDA_VISIBLE_DEVICES` | live | GPU selection (e.g. `1` to use one RTX 6000 Ada, avoiding a small index-0 card). |

## Usage

Mock (default — deterministic, GPU-free; this is the validated path):

```bash
python skills/report-anonymization/scripts/run_anonymization.py \
  skills/report-anonymization/fixtures/sample_reports_turkish.csv \
  --out runs/report_anonymization_mock
```

Live (real de-identification with vLLM; run from the env that has vLLM):

```bash
python skills/report-anonymization/scripts/run_anonymization.py \
  /path/to/reports.csv \
  --out runs/report_anonymization_live \
  --mode live \
  --model nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4 \
  --limit 100 \
  --cuda-visible-devices 1
```

Evidence pack via the eval engine (mock):

```bash
python -m eval_engine.run skills/report-anonymization \
  --fixture skills/report-anonymization/fixtures/sample_reports_turkish.csv \
  --out runs/report_anonymization_pack
```

Output JSON includes `n_reports`, `phi_leak` (deterministic mapping check), `token_format`, and `token_consistency`. The anonymized text and `Token_Mapping` are written to `<out>/anonymized.csv`.

## Limitations
- Mock mode is a small synthetic-vocabulary redactor for CI/verification — not a clinical de-identifier and not exhaustive on arbitrary text.
- Live mode wraps the upstream SLURM script in single-rank mode; for two-GPU data parallelism use the upstream `run_dual_gpu.sh`.
- PHI-leak is a verbatim mapping check: it cannot detect PHI the model never mapped, non-standard identifiers, or burnt-in pixel text.
- Not for clinical deployment, regulatory de-identification, autonomous diagnosis, or patient-facing use.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| `input CSV must contain 'UID' and 'report' columns` | Wrong columns or delimiter. | Pass `--id-col`/`--text-col`, or fix the CSV header. |
| `could not locate upstream anonymize_reports_parallel.py` | Live mode cannot find the upstream script. | Set `--mr-rate-root` or `$MR_RATE_REPORTS_ROOT` to the `reports_preprocessing` dir. |
| `upstream anonymizer failed` | vLLM/model/GPU issue in live mode. | Run from the vLLM env; check the model id and `CUDA_VISIBLE_DEVICES`. |
| Sanity gate `phi_leak.leak_rate` fails | A mapped original value survived in the anonymized text. | Re-run live with a stronger model, or fix the offending reports. |
