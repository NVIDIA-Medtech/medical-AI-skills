---
name: nv-curate-study
description: Used for curating one MRI study and its associated radiology report into MR-RATE-ready outputs by running nv-curate-mri then nv-curate and joining on study_uid. Not for clinical or regulatory use.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - MedTech
    - MR-RATE
    - data-curation
    - orchestrator
    - single-study
---

# nv-curate-study

## Purpose

- Curate **one** MRI study plus its associated radiology report for addition to the MR-RATE dataset.
- Composes sibling skills: `nv-curate-mri` (volumes) then `nv-curate` (reports), then joins on `study_uid`.
- Emits a single JSON summary (matched / rejected, stage paths, publish gate).
- Not for clinical deployment, regulatory de-identification, autonomous diagnosis, or patient-facing use.

## Instructions

1. Read `skill_manifest.yaml` and `schemas/study.schema.json` before changing the config contract.
2. Fill a `study.json` (see `fixtures/study.json`) with paths for this one study.
3. Run `scripts/run_curate_study.py`. Prefer `--mode mock` for wiring/CI; use `--mode live` only with a real MR-RATE checkout, GPU, and a **local** OpenAI-compatible LLM server (default model: Nemotron 3 Super 120B).
4. Keep `publish.skip_upload: true` until a human approves QC. This skill never uploads on its own when skip is true.
5. For a full tranche, use `nv-curate-batch` (which invokes this skill per study).

| User prompt | What to run |
|---|---|
| "Curate this one MRI and its report for MR-RATE" | `nv-curate-study` with `study.json` |
| "Curate a batch of MRIs and reports for MR-RATE" | `nv-curate-batch` (calls this skill) |

## Configure the local report LLM (default: Nemotron 3 Super 120B)

Live report curation talks to a **local** OpenAI-compatible server (`vllm serve`, `llama-server`, Ollama, …). Defaults:

| Setting | Default |
|---|---|
| `llm.model` | `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4` (Nemotron 3 Super 120B) |
| `llm.base_url` | `http://127.0.0.1:8080` |
| `llm.backend` | `openai` |
| `llm.api_key` | `EMPTY` (local servers usually ignore this) |

Set them in `study.json`:

```json
"llm": {
  "backend": "openai",
  "model": "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4",
  "base_url": "http://127.0.0.1:8080",
  "api_key": "EMPTY"
}
```

Or override on the CLI / env (CLI wins over JSON; JSON wins over defaults):

```bash
# CLI
--model nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4 \
--base-url http://127.0.0.1:8080

# Env
export CURATION_LLM_MODEL=nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4
export CURATION_LLM_BASE_URL=http://127.0.0.1:8080
```

Also set the same model on the report plan (`datasources.json` → `pipeline.model`) so `nv-curate` stages agree.

**Serve the model first**, then run live curation. Example with vLLM (adjust GPUs/quant as needed):

```bash
# Example: OpenAI-compatible server on the default base_url
vllm serve nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4 --port 8080
```

Ollama example (use the **server-registered** name as `llm.model`):

```bash
# e.g. ollama serve + pull your Nemotron 3 Super 120B tag, then:
# llm.base_url: http://127.0.0.1:11434/v1
# llm.model:    <exact ollama model name>
```

HF reference: [nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4) (also BF16/FP8 variants on Hugging Face).

## Available Scripts

| Script | Purpose | Arguments |
|---|---|---|
| `scripts/run_curate_study.py` | Curate one MRI + report; join; emit JSON | `STUDY.json [--out DIR] [--mode mock\|live] [--device N] [--preflight] [--mr-rate-root DIR] [--model ID] [--base-url URL]` |

## Prerequisites

| Mode | Needs |
|---|---|
| `mock` (default) | Python 3.10+; sibling `nv-curate` (mock stages). No GPU. MRI path is stubbed. |
| `live` | `$MR_RATE_ROOT` (or `--mr-rate-root`), `$MR_RATE_REPORTS_ROOT`, `dcm2niix`, CUDA GPU for MRI; **local LLM server** with Nemotron 3 Super 120B (or override); sibling `nv-curate-mri` + `nv-curate`. |

## Usage

Mock (CI / wiring):

```bash
python skills/nv-curate-study/scripts/run_curate_study.py \
  skills/nv-curate-study/fixtures/study.json \
  --mode mock --out runs/nv_curate_study_demo
```

Live (one real study — fill paths in study.json; LLM server already up):

```bash
export MR_RATE_ROOT=/path/to/MR-RATE/data-preprocessing
export MR_RATE_REPORTS_ROOT="$MR_RATE_ROOT/src/mr_rate_preprocessing/reports_preprocessing"
python skills/nv-curate-study/scripts/run_curate_study.py /path/to/study.json \
  --mode live --device 0 \
  --model nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4 \
  --base-url http://127.0.0.1:8080 \
  --out runs/nv_curate_study_live
```

Preflight only (live MRI env check, no full pipeline):

```bash
python skills/nv-curate-study/scripts/run_curate_study.py /path/to/study.json \
  --mode live --preflight --out runs/nv_curate_study_preflight
```

## Limitations

- Mock mode stubs the MRI track; it does not prove defacing or DICOM conversion.
- Live MRI always runs real upstream MR-RATE code (no MRI mock in `nv-curate-mri`).
- Live reports require a reachable `llm.base_url`; the default model id must match what the server registered.
- Join fails closed: if report or MRI side is missing/failed, `join.status` is `rejected` and publish remains blocked.
- Not a regulatory de-identifier; human QC required before any HF upload.

## Contributing fixes upstream

While this catalog is in testing, the **true upstream for skill PRs** is the
`draft/report-anonymization-skill-testing` branch on
[medatasci/medical-AI-skills](https://github.com/medatasci/medical-AI-skills)
(skills tree:
[skills/](https://github.com/medatasci/medical-AI-skills/tree/draft/report-anonymization-skill-testing/skills)).

If you have a **verified bug**, a **skill improvement**, or a **code improvement**
(clear repro, expected vs actual, and preferably a failing fixture or check),
do not keep it as a private patch — open a pull request:

| What you found | Open the PR against |
|---|---|
| This skill, `nv-curate-batch`, sibling curation skills, docs, or wrappers | [medatasci/medical-AI-skills](https://github.com/medatasci/medical-AI-skills) → base branch `draft/report-anonymization-skill-testing` (see [`CONTRIBUTING.md`](../../CONTRIBUTING.md)) |
| Real MRI/report preprocessing behavior inside MR-RATE `data-preprocessing` | [forithmus/MR-RATE](https://github.com/forithmus/MR-RATE) |

Include repro steps, the `study.json` / command line used, and whether the issue
is mock-only or live. Do not attach PHI or patient data to the PR.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `nv-curate` / `nv-curate-mri` not found | Run from the medical-AI-skills repo root; keep sibling skills installed |
| Live MRI preflight fails | Check `$MR_RATE_ROOT`, `dcm2niix` on PATH, CUDA visibility |
| Report LLM connection errors | Confirm server is up at `llm.base_url` and `llm.model` matches the served name |
| `join.status=rejected` | Compare `study_uid` on both sides; rerun the failing stage skill only |
| Agent wants a full batch | Switch to `nv-curate-batch` |
