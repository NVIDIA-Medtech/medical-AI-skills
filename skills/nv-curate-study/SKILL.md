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
3. Run `scripts/run_curate_study.py`. Prefer `--mode mock` for wiring/CI; use `--mode live` only with a real MR-RATE checkout, GPU, and report vLLM env.
4. Keep `publish.skip_upload: true` until a human approves QC. This skill never uploads on its own when skip is true.
5. For a full tranche, use `nv-curate-batch` (which invokes this skill per study).

| User prompt | What to run |
|---|---|
| "Curate this one MRI and its report for MR-RATE" | `nv-curate-study` with `study.json` |
| "Curate a batch of MRIs and reports for MR-RATE" | `nv-curate-batch` (calls this skill) |

## Available Scripts

| Script | Purpose | Arguments |
|---|---|---|
| `scripts/run_curate_study.py` | Curate one MRI + report; join; emit JSON | `STUDY.json [--out DIR] [--mode mock\|live] [--device N] [--preflight] [--mr-rate-root DIR]` |

## Prerequisites

| Mode | Needs |
|---|---|
| `mock` (default) | Python 3.10+; sibling `nv-curate` (mock stages). No GPU. MRI path is stubbed. |
| `live` | `$MR_RATE_ROOT` (or `--mr-rate-root`), `$MR_RATE_REPORTS_ROOT`, `dcm2niix`, CUDA GPU, report vLLM stack; sibling `nv-curate-mri` + `nv-curate`. |

## Usage

Mock (CI / wiring):

```bash
python skills/nv-curate-study/scripts/run_curate_study.py \
  skills/nv-curate-study/fixtures/study.json \
  --mode mock --out runs/nv_curate_study_demo
```

Live (one real study — fill paths in study.json first):

```bash
export MR_RATE_ROOT=/path/to/MR-RATE/data-preprocessing
export MR_RATE_REPORTS_ROOT="$MR_RATE_ROOT/src/mr_rate_preprocessing/reports_preprocessing"
python skills/nv-curate-study/scripts/run_curate_study.py /path/to/study.json \
  --mode live --device 0 --out runs/nv_curate_study_live
```

Preflight only (live MRI env check, no full pipeline):

```bash
python skills/nv-curate-study/scripts/run_curate_study.py /path/to/study.json \
  --mode live --preflight --out runs/nv_curate_study_preflight
```

## Limitations

- Mock mode stubs the MRI track; it does not prove defacing or DICOM conversion.
- Live MRI always runs real upstream MR-RATE code (no MRI mock in `nv-curate-mri`).
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
| `join.status=rejected` | Compare `study_uid` on both sides; rerun the failing stage skill only |
| Agent wants a full batch | Switch to `nv-curate-batch` |
