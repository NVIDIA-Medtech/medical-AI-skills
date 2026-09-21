---
name: report-structuring
description: Used for parsing English radiology reports into four structured sections (clinical_information, technique, findings, impression), normalizing findings to flowing sentences and impression to em-dash bullets, then QC-ing the result (MR-RATE reports stages 04 + 05). Not for de-identification, regulatory reporting, or clinical use.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - MedTech
    - reports
    - structuring
    - quality-control
---

# Report Structuring

## Purpose
- Used for parsing English radiology reports into four structured sections (`clinical_information`, `technique`, `findings`, `impression`), normalizing the formatting (findings as flowing sentences, impression as em-dash `—` bullets), and running a structure QC pass (MR-RATE reports_preprocessing stages 04 structuring + 05 structure QC).
- Not for de-identification, regulatory reporting, clinical deployment, autonomous diagnosis, or patient-facing use. Inputs must already be anonymized (stage 01) and translated to English.
- Manifest I/O: input is `reports_csv` (CSV with `UID` + `report` columns); output is `structuring_summary` (JSON on stdout) plus `structured.csv` in the run directory.

## Instructions
- Read `skill_manifest.yaml` before changing arguments, side effects, or validation gates.
- Run `scripts/run_report_structuring.py` through the documented command below; keep outputs under a caller-provided run directory (`--out`).
- If a host agent exposes `run_script`, use `run_script("scripts/run_report_structuring.py", args=[...])`; otherwise run the Bash/Python command shown below.
- Default `--mode mock` is GPU-free and stdlib-only (deterministic header-split + rule-based QC). Use `--mode live` for real structuring with the upstream vLLM model and the LLM-judge QC pass.
- After a run, audit the evidence pack with `medagent.verifiers.report_structuring_quality_v1` before treating it as reviewed evidence.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/run_report_structuring.py` | Primary entrypoint declared by `skill_manifest.yaml`. | `REPORTS_CSV [--out DIR] [--mode mock\|live] [--model HF_ID] [--limit N] [--id-col UID] [--text-col report] [--no-qc] [--mr-rate-root DIR] [--cuda-visible-devices N]` |

## Prerequisites
- `--mode mock` (default): Python 3.10+ only — no GPU, no network, no extra packages.
- `--mode live`: a CUDA GPU, `vllm`, and the configured vLLM model (cached or downloadable). The upstream scripts `04_structuring/structure_reports_parallel.py` and `05_structure_qc/qc_llm_verify.py` must be reachable via `--mr-rate-root` or `$MR_RATE_REPORTS_ROOT`. The upstream structurer reads an `english_anonymized_report` column plus `AccessionNo` and `UID`.

| Variable | Mode | Purpose |
|---|---|---|
| `MR_RATE_REPORTS_ROOT` | live | Path to the `reports_preprocessing` directory for upstream-script lookup. |
| `CUDA_VISIBLE_DEVICES` | live | GPU selection (e.g. `1` to use one RTX 6000 Ada, avoiding a small index-0 card). |

## Usage

Mock (default — deterministic, GPU-free; this is the validated path):

```bash
python skills/report-structuring/scripts/run_report_structuring.py \
  skills/report-structuring/fixtures/sample_reports_english.csv \
  --out runs/report_structuring_mock
```

Live (real structuring + LLM-judge QC with vLLM; run from the env that has vLLM):

```bash
python skills/report-structuring/scripts/run_report_structuring.py \
  /path/to/english_reports.csv \
  --out runs/report_structuring_live \
  --mode live \
  --model nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4 \
  --limit 100 \
  --cuda-visible-devices 1
```

Add `--no-qc` to run only the structuring pass (step 04) and use the deterministic rule-based QC instead of the upstream LLM judge (step 05).

Evidence pack via the eval engine (mock):

```bash
python -m eval_engine.run skills/report-structuring \
  --fixture skills/report-structuring/fixtures/sample_reports_english.csv \
  --out runs/report_structuring_pack
```

Output JSON includes `n_reports`, `parse` (parse success rate), `sections` (completeness rate), `qc` (pass rate), and `format` (bullet/header-leak violations). The structured sections are written to `<out>/structured.csv`.

## Limitations
- Mock mode is a deterministic header-split structurer for CI/verification: it requires the four canonical headers (`Clinical Information:`, `Technique:`, `Findings:`, `Impression:`) and is not a general report parser.
- Live mode wraps the upstream SLURM scripts in single-rank mode; for two-GPU data parallelism use the upstream launcher.
- The `format` check is a surface check (bullets in findings, leaked headers in section bodies); it does not verify clinical content fidelity — that is the job of the LLM-judge QC pass (step 05) and the paired verifier.
- This skill does NOT de-identify. De-identification is a separate stage (report-anonymization, MR-RATE stage 01).
- Not for clinical deployment, regulatory reporting, autonomous diagnosis, or patient-facing use.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| `input CSV must contain 'UID' and 'report' columns` | Wrong columns or delimiter. | Pass `--id-col`/`--text-col`, or fix the CSV header. |
| `could not locate upstream 04_structuring/structure_reports_parallel.py` | Live mode cannot find the upstream script. | Set `--mr-rate-root` or `$MR_RATE_REPORTS_ROOT` to the `reports_preprocessing` dir. |
| `upstream structurer failed` / `upstream QC failed` | vLLM/model/GPU issue in live mode. | Run from the vLLM env; check the model id and `CUDA_VISIBLE_DEVICES`. |
| Sanity gate `format.n_format_violations` fails | A bullet leaked into findings or a section header leaked into a body. | Inspect `<out>/structured.csv`; in live mode re-run with a stronger model. |
| Sanity gate `parse.parse_success_rate` / `sections.completeness_rate` fails | Reports lacked the canonical headers or produced empty findings/impression. | Ensure inputs carry the four section headers; in live mode inspect parse failures. |
