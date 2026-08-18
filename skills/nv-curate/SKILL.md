---
name: nv-curate
description: Used for orchestrating the MR-RATE report-curation pipeline — inventory raw data, then de-identify, translate, structure, and label reports into an AI-ready dataset, and hand off to training or analysis. Not for clinical or regulatory use.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - MedTech
    - reports
    - data-curation
    - pipeline
    - orchestrator
---

# nv-curate

## Purpose
- Used for end-to-end curation of medical report data into an AI-ready dataset: inventory a raw-data location, then run de-identification (step 01), translation + QC (02+03), structuring + QC (04+05), and pathology labeling (06), and assemble a dataset joined by `study_uid`.
- Orchestrates the sibling skills `report-anonymization`, `report-translation`, `report-structuring`, and `report-pathology-classification`, and hands the result to a training (`nv-generate-mr-brain-finetune`) or analysis task.
- Not for clinical deployment, regulatory de-identification, autonomous diagnosis, or patient-facing use.
- Manifest I/O: input is `datasources_json` (plan in `schemas/datasources.schema.json`); output is `curation_summary` (JSON on stdout) plus an AI-ready datalist under the run/target directory.

## Instructions
- Read `skill_manifest.yaml` and `schemas/datasources.schema.json` before changing arguments or the config contract.
- Run `scripts/nv_curate.py` with the action that matches the user's request. If a host agent exposes `run_script`, use `run_script("scripts/nv_curate.py", args=[...])`; otherwise run the command shown below.
- The three end-user prompts map to the three actions:

| User prompt | Action | What it does |
|---|---|---|
| "Create an inventory of the data in DIR and what processing it needs to be AI ready" | `--action plan` | Scans DIR, reports counts/columns/image presence/PHI risk, writes a `datasources.json` plan. |
| "Extract, de-identify, translate, structure, and save it to TARGET" | `--action curate` | Runs the 4 transform stages on the configured raw data and assembles the AI-ready datalist. |
| "Use nv-curate to retrieve and transform DATA and fine-tune the MR-brain diffusion model" | `--action finetune` | Runs `curate`, builds the MONAI datalist, and reports hand-off readiness for `nv-generate-mr-brain-finetune`. |

- For end-to-end **MR-RATE database ingest** of one study (MRI + report), use
  [`nv-curate-study`](../nv-curate-study/SKILL.md). For a tranche, use
  [`nv-curate-batch`](../nv-curate-batch/SKILL.md) (calls the study skill).
  Copy-paste prompts: [`docs/prompts/mr-rate-ingest.md`](../../docs/prompts/mr-rate-ingest.md).

- Default `--mode mock` is deterministic and GPU-free (each stage uses its skill's mock path). Use `--mode live` for real de-identification/translation/structuring/labeling against a **local** OpenAI-compatible LLM (default: Nemotron 3 Super 120B `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4`; needs that model served locally plus `$MR_RATE_REPORTS_ROOT`).
- After a `curate`/`finetune` run, audit each stage's evidence pack under `<out>/stages/<step>` with that stage's paired verifier (`report_anonymization_quality_v1`, `report_translation_quality_v1`, `report_structuring_quality_v1`, `report_pathology_quality_v1`).
- The image track (diffusion finetune) requires NIfTI volumes in `raw_data` named/keyed by `study_uid`. Without them, the curated dataset is the analysis track (reports + labels) and the finetune hand-off is reported not-ready — do not fabricate a finetune.

## Configure the local report LLM (default: Nemotron 3 Super 120B)

Live mode expects a local OpenAI-compatible server. Preferred defaults:

| Setting | Default |
|---|---|
| `--model` / `pipeline.model` | `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4` |
| Upstream stage `--base_url` | `http://127.0.0.1:8080` (MR-RATE `pipeline_common` default) |

In `datasources.json`:

```json
"pipeline": {
  "steps": ["anonymize", "translate", "structure", "classify"],
  "mode": "live",
  "model": "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4"
}
```

Serve first, then curate:

```bash
vllm serve nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4 --port 8080
```

End-to-end ingest skills (`nv-curate-study` / `nv-curate-batch`) expose the same defaults via their `llm` block and `--model` / `--base-url` flags.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/nv_curate.py` | Primary entrypoint declared by `skill_manifest.yaml`. | `DATASOURCES.json [--out DIR] [--action plan\|curate\|finetune] [--mode mock\|live] [--model HF_ID] [--limit N] [--mr-rate-root DIR] [--cuda-visible-devices N]` |

## Prerequisites
- `--mode mock` (default): Python 3.10+ only — no GPU, no network, no extra packages.
- `--mode live`: a CUDA GPU host serving the configured local LLM (default Nemotron 3 Super 120B), `vllm` or another OpenAI-compatible server, and `$MR_RATE_REPORTS_ROOT` pointing at the `reports_preprocessing` directory.
- The four sibling stage skills must be present in the same `skills/` directory.

| Variable | Mode | Purpose |
|---|---|---|
| `MR_RATE_REPORTS_ROOT` | live | Path to `reports_preprocessing` for upstream-script lookup (passed through to each stage). |
| `CUDA_VISIBLE_DEVICES` | live | GPU selection passed through to each stage (e.g. `1`). |
| `CURATION_LLM_MODEL` | live | Optional override for the local model id (study/batch skills). |
| `CURATION_LLM_BASE_URL` | live | Optional override for the OpenAI-compatible base URL (study/batch skills). |

## Usage

Plan (prompt 1):

```bash
python skills/nv-curate/scripts/nv_curate.py skills/nv-curate/fixtures/raw_data \
  --action plan --out runs/nv_curate_plan
```

Curate (prompt 2 — mock, deterministic, the validated path):

```bash
python skills/nv-curate/scripts/nv_curate.py skills/nv-curate/fixtures/datasources.json \
  --action curate --out runs/nv_curate_demo
```

Curate + finetune hand-off (prompt 3):

```bash
python skills/nv-curate/scripts/nv_curate.py skills/nv-curate/fixtures/datasources.json \
  --action finetune --out runs/nv_curate_finetune
```

Live end-to-end on real data (local Nemotron 3 Super 120B already served):

```bash
MR_RATE_REPORTS_ROOT=/path/to/reports_preprocessing \
python skills/nv-curate/scripts/nv_curate.py /data/mrbrain/datasources.json \
  --action curate --mode live --model nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4 \
  --cuda-visible-devices 1 --out runs/nv_curate_live
```

Evidence pack via the eval engine (mock):

```bash
python -m eval_engine.run skills/nv-curate \
  --fixture skills/nv-curate/fixtures/datasources.json --out runs/nv_curate_pack
```

## Limitations
- The orchestrator never loads a model or GPU; quality depends on the stage skills' chosen mode.
- Mock mode is for CI/verification, not clinical de-identification.
- Per-stage quality is gated by each stage's paired verifier on its pack; nv-curate itself gates orchestration completeness, not per-stage quality.
- The finetune hand-off needs image volumes joined by `study_uid`; text-only curation yields the analysis dataset and a not-ready finetune hand-off.
- Not for clinical deployment, regulatory de-identification, autonomous diagnosis, or patient-facing use.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| `raw_data.path does not exist` | Wrong `raw_data.path` in the config. | Fix the path (relative paths resolve against the datasources.json location). |
| `no report CSVs matching ...` | `reports_glob` does not match the raw files. | Adjust `raw_data.reports_glob`. |
| `stage <step> failed` | A stage skill errored (live: vLLM/model/GPU). | Run that stage skill directly to see its stderr; check the model/GPU/env. |
| `finetune_handoff.ready` is false | No image volumes joined by study_uid. | Add NIfTI volumes to `raw_data` (image track) before finetuning. |
