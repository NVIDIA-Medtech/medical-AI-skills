---
name: nv-curate-batch
description: Used for curating a batch of MRI studies and associated radiology reports into MR-RATE-ready outputs by invoking nv-curate-study once per study, with smoke-cohort and reject-list gates before publish. Not for clinical or regulatory use.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - MedTech
    - MR-RATE
    - data-curation
    - orchestrator
    - batch
---

# nv-curate-batch

## Purpose

- Curate a **tranche/batch** of MRI studies and associated radiology reports for MR-RATE.
- Invokes sibling skill **`nv-curate-study` once per study** (smoke cohort first, then remainder).
- Aggregates matched vs reject lists; keeps publish blocked until human approval.
- Not for clinical deployment, regulatory de-identification, autonomous diagnosis, or patient-facing use.

## Instructions

1. Read `skill_manifest.yaml` and `schemas/batch.schema.json`.
2. Build a `batch.json` that lists per-study `study.json` paths (or embeds study configs). See `fixtures/batch.json`.
3. Ensure `nv-curate-study` is present — this skill shells out to its entrypoint; it does not reimplement MRI/report stages.
4. Run with `--mode mock` for wiring; `--mode live` for production (requires MR-RATE + GPU + **local** Nemotron 3 Super 120B server by default).
5. Do not set `publish.skip_upload: false` until QC of the matched set is complete.

| User prompt | Skill |
|---|---|
| "Curate this one MRI and its report" | `nv-curate-study` |
| "Curate this batch/tranche of MRIs and reports for MR-RATE" | `nv-curate-batch` |

## Configure the local report LLM (default: Nemotron 3 Super 120B)

Same contract as `nv-curate-study`. Set once on `batch.json` (applied to every study):

```json
"llm": {
  "backend": "openai",
  "model": "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4",
  "base_url": "http://127.0.0.1:8080",
  "api_key": "EMPTY"
}
```

Or CLI / env:

```bash
--model nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4 \
--base-url http://127.0.0.1:8080

export CURATION_LLM_MODEL=nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4
export CURATION_LLM_BASE_URL=http://127.0.0.1:8080
```

Serve the model before `--mode live` (example):

```bash
vllm serve nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4 --port 8080
```

See [`nv-curate-study/SKILL.md`](../nv-curate-study/SKILL.md) for Ollama and override details.

## Available Scripts

| Script | Purpose | Arguments |
|---|---|---|
| `scripts/run_curate_batch.py` | Run `nv-curate-study` per study; aggregate | `BATCH.json [--out DIR] [--mode mock\|live] [--smoke N] [--device N] [--mr-rate-root DIR] [--model ID] [--base-url URL]` |

## Prerequisites

- Sibling skill `nv-curate-study` (and transitively `nv-curate` / `nv-curate-mri` for live).
- Same env as `nv-curate-study` for the chosen mode, including a local LLM server when live.

## Usage

Mock batch (fixture with 2 studies):

```bash
python skills/nv-curate-batch/scripts/run_curate_batch.py \
  skills/nv-curate-batch/fixtures/batch.json \
  --mode mock --smoke 1 --out runs/nv_curate_batch_demo
```

Live tranche (LLM server already listening on `base_url`):

```bash
export MR_RATE_ROOT=/path/to/MR-RATE/data-preprocessing
export MR_RATE_REPORTS_ROOT="$MR_RATE_ROOT/src/mr_rate_preprocessing/reports_preprocessing"
python skills/nv-curate-batch/scripts/run_curate_batch.py /path/to/batch.json \
  --mode live --smoke 5 --device 0 \
  --model nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4 \
  --base-url http://127.0.0.1:8080 \
  --out runs/nv_curate_batch_live
```

## Limitations

- Per-study quality equals `nv-curate-study` for that study; this skill gates orchestration completeness and join aggregates only.
- Mock mode stubs MRI and may stub reports when sibling mock stages are missing.
- Live reports require a reachable `llm.base_url` with the configured Nemotron (or override) model loaded.
- Never uploads while `publish.skip_upload` is true or any required study is rejected (configurable `fail_closed`).

## Contributing fixes upstream

While this catalog is in testing, the **true upstream for skill PRs** is the
`draft/report-anonymization-skill-testing` branch on
[medatasci/medical-AI-skills](https://github.com/medatasci/medical-AI-skills)
(skills tree:
[skills/](https://github.com/medatasci/medical-AI-skills/tree/draft/report-anonymization-skill-testing/skills)).

If you have a **verified bug**, a **skill improvement**, or a **code improvement**
(clear repro, expected vs actual, and preferably a failing fixture or check),
open a pull request rather than keeping a private fork patch:

| What you found | Open the PR against |
|---|---|
| This skill, `nv-curate-study`, sibling curation skills, docs, or wrappers | [medatasci/medical-AI-skills](https://github.com/medatasci/medical-AI-skills) → base branch `draft/report-anonymization-skill-testing` (see [`CONTRIBUTING.md`](../../CONTRIBUTING.md)) |
| Real MRI/report preprocessing behavior inside MR-RATE `data-preprocessing` | [forithmus/MR-RATE](https://github.com/forithmus/MR-RATE) |

Include the `batch.json` / smoke settings, which `study_uid` failed, and mock vs
live. Do not attach PHI or patient data to the PR.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `nv-curate-study` missing | Install/checkout sibling skill under `skills/nv-curate-study/` |
| Many rejects | Inspect `<out>/studies/<id>/summary.json`; rerun that study only |
| Need a single study | Use `nv-curate-study` directly |
