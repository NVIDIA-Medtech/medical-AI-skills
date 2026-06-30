---
name: report-translation
description: Used for translating anonymized Turkish radiology reports to English and QC'ing the result (MR-RATE reports stage 02 translation + stage 03 translation QC). Preserves [token_N] anonymization placeholders; checks residual non-English and translation quality. Not for clinical translation of record or clinical use.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - MedTech
    - reports
    - translation
    - translation-qc
---

# Report Translation

## Purpose
- Used for translating anonymized Turkish radiology reports to English and QC'ing the translation: each report is translated, language-detected (residual Turkish leftover), and quality-checked, while every `[token_N]` anonymization placeholder is preserved verbatim (MR-RATE reports_preprocessing stage 02 translation + stage 03 translation QC).
- Not for clinical translation of record, clinical deployment, autonomous diagnosis, or patient-facing use.
- Manifest I/O: input is `reports_csv` (CSV with `UID` + `Anonymized_Rapor` columns, `[token_N]` placeholders); output is `translation_summary` (JSON on stdout) plus `translated.csv` in the run directory.

## Instructions
- Read `skill_manifest.yaml` before changing arguments, side effects, or validation gates.
- Run `scripts/run_report_translation.py` through the documented command below; keep outputs under a caller-provided run directory (`--out`).
- If a host agent exposes `run_script`, use `run_script("scripts/run_report_translation.py", args=[...])`; otherwise run the Bash/Python command shown below.
- Default `--mode mock` is GPU-free and stdlib-only (deterministic phrase-dictionary translation with rule-based QC and language detection). Use `--mode live` for real translation + QC with the upstream vLLM model.
- After a run, audit the evidence pack with `medagent.verifiers.report_translation_quality_v1` before treating it as reviewed evidence.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/run_report_translation.py` | Primary entrypoint declared by `skill_manifest.yaml`. | `REPORTS_CSV [--out DIR] [--mode mock\|live] [--model HF_ID] [--limit N] [--id-col UID] [--text-col Anonymized_Rapor] [--chunk-size N] [--mr-rate-root DIR] [--cuda-visible-devices N]` |

## Prerequisites
- `--mode mock` (default): Python 3.10+ only — no GPU, no network, no extra packages.
- `--mode live`: a CUDA GPU, `vllm`, and the configured vLLM model (cached or downloadable). The upstream scripts `02_translation/translate_reports_parallel.py`, `03_translation_qc/detect_turkish_parallel.py`, and `03_translation_qc/quality_check_parallel.py` must be reachable via `--mr-rate-root` or `$MR_RATE_REPORTS_ROOT`.

| Variable | Mode | Purpose |
|---|---|---|
| `MR_RATE_REPORTS_ROOT` | live | Path to the `reports_preprocessing` directory for upstream-script lookup. |
| `CUDA_VISIBLE_DEVICES` | live | GPU selection (e.g. `1` to use one RTX 6000 Ada, avoiding a small index-0 card). |

## Usage

Mock (default — deterministic, GPU-free; this is the validated path):

```bash
python skills/report-translation/scripts/run_report_translation.py \
  skills/report-translation/fixtures/sample_reports_turkish_anonymized.csv \
  --out runs/report_translation_mock
```

Live (real translation + QC with vLLM; run from the env that has vLLM):

```bash
python skills/report-translation/scripts/run_report_translation.py \
  /path/to/anonymized_reports.csv \
  --out runs/report_translation_live \
  --mode live \
  --model nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4 \
  --limit 100 \
  --cuda-visible-devices 1
```

Evidence pack via the eval engine (mock):

```bash
python -m eval_engine.run skills/report-translation \
  --fixture skills/report-translation/fixtures/sample_reports_turkish_anonymized.csv \
  --out runs/report_translation_pack
```

Output JSON includes `n_reports`, `qc` (translation QC pass rate), `language` (residual non-English rate), and `token_preservation` (placeholders surviving translation). The translated text, detected language, and QC verdict are written to `<out>/translated.csv`.

## Limitations
- Mock mode is a small synthetic-vocabulary phrase-dictionary translator with rule-based QC and language detection for CI/verification — not a clinical translator and not exhaustive on arbitrary text.
- Live mode wraps the upstream SLURM scripts in single-rank mode (translate, then detect-Turkish, then LLM QC); for two-GPU data parallelism use the upstream launchers.
- QC is an LLM judge in live mode and a rule-based check in mock mode; neither is a clinical-accuracy guarantee. Token preservation is a verbatim `[token_N]` string check.
- Not for clinical deployment, clinical translation of record, autonomous diagnosis, or patient-facing use.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| `input CSV must contain 'UID' and 'Anonymized_Rapor' columns` | Wrong columns or delimiter. | Pass `--id-col`/`--text-col`, or fix the CSV header. |
| `could not locate upstream translate_reports_parallel.py` | Live mode cannot find the upstream script. | Set `--mr-rate-root` or `$MR_RATE_REPORTS_ROOT` to the `reports_preprocessing` dir. |
| `upstream translate_reports_parallel.py failed` | vLLM/model/GPU issue in live mode. | Run from the vLLM env; check the model id and `CUDA_VISIBLE_DEVICES`. |
| Sanity gate `language.non_english_rate` fails | A translation still reads as Turkish. | Re-run live with a stronger model, or inspect the offending reports; in mock, the source phrase is outside the known dictionary. |
| Sanity gate `token_preservation.n_reports_token_dropped` fails | A translation dropped a `[token_N]` placeholder. | Re-run live with a stronger model; check the upstream system prompt preserves tokens. |
