---
name: mri-series-classification
description: Assigns each MRI series a modality label (T1w, T2w, FLAIR, SWI, MRA, ...) using the MR-RATE rule hierarchy (MRI step 3); use it when preprocessing MRI study metadata to classify series by modality. Not for clinical use.
license: Apache-2.0
allowed-tools: Bash
metadata: { author: "NVIDIA MedTech <noreply@nvidia.com>", tags: [MedTech, MRI, series] }
---

# mri-series-classification — MRI series classification

## Purpose

This skill assigns each MRI series a modality label (T1w, T2w, FLAIR, SWI, MRA, ...)
by applying the MR-RATE rule hierarchy (MRI preprocessing step 3). It wraps the real
upstream MR-RATE series-classification step so that cleaned series metadata is enriched
with a modality label for each series. It is intended for development and research
preprocessing workflows and is **not for clinical use**.

## Instructions

Run the wrapper script `scripts/run_series_classification.py`. It first performs a
**preflight environment-alignment check** (Python version, required dependencies, and
the MR-RATE upstream layout) and then executes the real upstream series step on the
provided fixtures. The wrapper emits a structured telemetry block (timings, environment
including versions/GPU/host, and I/O counts) and writes a result JSON conforming to
`validators/output_schema.json`.

Use `--preflight` to verify environment alignment **before** attempting a real run; in
this mode the wrapper only reports the alignment checks and does not execute the
upstream step.

Point `--mr-rate-root` at your local MR-RATE `data-preprocessing` checkout (or set the
`$MR_RATE_ROOT` environment variable and pass it through).

Preflight only:

```
run_script("scripts/run_series_classification.py", args=["--fixtures", "fixtures", "--out", "out", "--mr-rate-root", "/path/to/mr-rate/data-preprocessing", "--preflight"])
```

Real run:

```
run_script("scripts/run_series_classification.py", args=["--fixtures", "fixtures", "--out", "out", "--mr-rate-root", "/path/to/mr-rate/data-preprocessing"])
```

Generate the required input fixture first with:

```
run_script("fixtures/generate_fixtures.py", args=["--step", "series"])
```

## Available Scripts

| Script | Purpose | Arguments |
| --- | --- | --- |
| scripts/run_series_classification.py | Preflight environment-alignment check then run the real MR-RATE series step with telemetry | --fixtures <dir> --out <dir> --mr-rate-root <dir> [--device 0] [--preflight] |
| fixtures/generate_fixtures.py | Generate PHI-free synthetic input (`fixtures/cleaned_metadata.csv`) | --step series |

## Prerequisites

- Python >= 3.10.
- Python packages: `pandas`, `numpy`.
- A local MR-RATE `data-preprocessing` checkout, referenced via `--mr-rate-root` or `$MR_RATE_ROOT`.
- Input fixture `fixtures/cleaned_metadata.csv` produced by `fixtures/generate_fixtures.py --step series`.
- No GPU and no `dcm2niix` are required for this step.

## Limitations

- Ships with small synthetic PHI-free fixtures; not clinically representative.
- Upstream `accession_to_uid` anonymization is currently an identity pass-through, so
  study-ID de-identification is a no-op unless inputs are pre-anonymized.
- Not a regulatory de-identifier; review output before sharing. Not for clinical use.

## Troubleshooting

- **Preflight reports misalignment**: install the missing dependency (`pandas`, `numpy`),
  use Python >= 3.10, or fix `--mr-rate-root` to point at a valid MR-RATE
  `data-preprocessing` checkout. Re-run with `--preflight` until all checks pass.
- **Missing input fixture**: run `fixtures/generate_fixtures.py --step series` to create
  `fixtures/cleaned_metadata.csv` before the real run.
- **Upstream import errors**: confirm `--mr-rate-root` contains
  `src/mr_rate_preprocessing/mri_preprocessing/series_classification.py`.

## Examples

Verify the environment is aligned before running (uses `$MR_RATE_ROOT`):

```
run_script("scripts/run_series_classification.py", args=["--fixtures", "fixtures", "--out", "out", "--mr-rate-root", "$MR_RATE_ROOT", "--preflight"])
```

Run the real series-classification step on the synthetic fixtures:

```
run_script("scripts/run_series_classification.py", args=["--fixtures", "fixtures", "--out", "out", "--mr-rate-root", "/path/to/mr-rate/data-preprocessing", "--device", "0"])
```
