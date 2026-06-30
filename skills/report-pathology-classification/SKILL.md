---
name: report-pathology-classification
description: Used for classifying brain/spine MRI report findings against a fixed pathology list, emitting one 0/1 label per pathology per report (MR-RATE reports stage 06). Not for clinical diagnosis or patient-facing use.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - MedTech
    - reports
    - classification
    - pathology
---

# Report Pathology Classification

## Purpose
- Used for classifying brain/spine MRI report findings against a fixed pathology list: each report receives one `0/1` label per pathology in `data/pathologies.json`, written to a `labels.csv` (MR-RATE reports_preprocessing stage 06).
- Not for clinical diagnosis, clinical deployment, autonomous diagnosis, or patient-facing use.
- Manifest I/O: input is `reports_csv` (CSV with `study_uid` + `findings` columns); output is `pathology_classification_summary` (JSON on stdout) plus `labels.csv` in the run directory.

## Instructions
- Read `skill_manifest.yaml` before changing arguments, side effects, or validation gates.
- Run `scripts/run_report_pathology_classification.py` through the documented command below; keep outputs under a caller-provided run directory (`--out`).
- If a host agent exposes `run_script`, use `run_script("scripts/run_report_pathology_classification.py", args=[...])`; otherwise run the Bash/Python command shown below.
- Default `--mode mock` is GPU-free and stdlib-only (deterministic keyword-presence classification). Use `--mode live` for real classification with the upstream multi-step vLLM model.
- The findings text is not de-identified by this skill; run `report-anonymization` first if the input may contain PHI.
- After a run, audit the evidence pack with `medagent.verifiers.report_pathology_quality_v1` (planned) before treating it as reviewed evidence.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/run_report_pathology_classification.py` | Primary entrypoint declared by `skill_manifest.yaml`. | `REPORTS_CSV [--out DIR] [--mode mock\|live] [--model HF_ID] [--limit N] [--id-col study_uid] [--text-col findings] [--pathologies-json PATH] [--seed N] [--batch-size N] [--mr-rate-root DIR] [--cuda-visible-devices N]` |

## Prerequisites
- `--mode mock` (default): Python 3.10+ only — no GPU, no network, no extra packages.
- `--mode live`: a CUDA GPU, `vllm`, and the configured vLLM model (cached or downloadable). The upstream script `06_pathology_classification/classify_pathologies_parallel.py` must be reachable via `--mr-rate-root` or `$MR_RATE_REPORTS_ROOT`.

| Variable | Mode | Purpose |
|---|---|---|
| `MR_RATE_REPORTS_ROOT` | live | Path to the `reports_preprocessing` directory for upstream-script lookup. |
| `CUDA_VISIBLE_DEVICES` | live | GPU selection (e.g. `1` to use one RTX 6000 Ada, avoiding a small index-0 card). |

## Usage

Mock (default — deterministic, GPU-free; this is the validated path):

```bash
python skills/report-pathology-classification/scripts/run_report_pathology_classification.py \
  skills/report-pathology-classification/fixtures/sample_reports_mr_findings.csv \
  --out runs/report_pathology_classification_mock
```

Live (real classification with vLLM; run from the env that has vLLM):

```bash
python skills/report-pathology-classification/scripts/run_report_pathology_classification.py \
  /path/to/reports.csv \
  --out runs/report_pathology_classification_live \
  --mode live \
  --model nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4 \
  --limit 100 \
  --cuda-visible-devices 1
```

Evidence pack via the eval engine (mock):

```bash
python -m eval_engine.run skills/report-pathology-classification \
  --fixture skills/report-pathology-classification/fixtures/sample_reports_mr_findings.csv \
  --out runs/report_pathology_classification_pack
```

Output JSON includes `n_reports`, `pathologies` (label count + source), `labels` (coverage), and `validation` (JSON-parse success, invalid-label count). The per-report label vector is written to `<out>/labels.csv` with `study_uid` plus one `0/1` column per pathology.

## Limitations
- Mock mode is a small synthetic-vocabulary keyword classifier for CI/verification — it does not parse negation, uncertainty, or clinical context, and is not a clinical classifier.
- Live mode wraps the upstream single-rank classifier; for multi-GPU data parallelism use the upstream SLURM launcher.
- The committed `data/pathologies.json` is a 10-label subset of the full upstream pathology list; the full upstream file carries the complete label set.
- Labels are research-grade signals derived from text only; they are not a diagnosis and do not reflect imaging review.
- Not for clinical deployment, autonomous diagnosis, regulatory decision-making, or patient-facing use.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| `input CSV must contain 'study_uid' and 'findings' columns` | Wrong columns or delimiter. | Pass `--id-col`/`--text-col`, or fix the CSV header. |
| `pathologies JSON not found` | `--pathologies-json` points nowhere, or `data/pathologies.json` is missing. | Omit the flag to use the bundled vocabulary, or pass a valid path. |
| `could not locate upstream classify_pathologies_parallel.py` | Live mode cannot find the upstream script. | Set `--mr-rate-root` or `$MR_RATE_REPORTS_ROOT` to the `reports_preprocessing` dir. |
| `upstream classifier failed` | vLLM/model/GPU issue in live mode. | Run from the vLLM env; check the model id and `CUDA_VISIBLE_DEVICES`. |
| Sanity gate `labels.label_coverage_rate` fails | A report produced an incomplete label vector. | Re-run live with a stronger model, or check the offending reports for parse failures. |
