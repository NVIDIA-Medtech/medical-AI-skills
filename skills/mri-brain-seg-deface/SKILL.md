---
name: mri-brain-seg-deface
description: Predicts a brain mask with HD-BET and removes facial features with Quickshear to write defaced volumes plus brain and defacing masks (MR-RATE MRI step 5); use it to skull-strip and deface NIfTI MRI volumes for research preprocessing. Not for clinical use.
license: Apache-2.0
allowed-tools: Bash
metadata: { author: "NVIDIA MedTech <noreply@nvidia.com>", tags: [MedTech, MRI, brainseg] }
---

# mri-brain-seg-deface — brain segmentation & de-facing

## Purpose

This skill runs the real MR-RATE MRI preprocessing brain-segmentation-and-defacing step (step 5). It predicts a brain mask with HD-BET and removes facial features with Quickshear, writing defaced volumes alongside brain and defacing masks. It is intended for research and development preprocessing of NIfTI MRI volumes. Not for clinical use.

## Instructions

1. Ensure the MR-RATE `data-preprocessing` checkout is available and pass its path via `--mr-rate-root` (or the `$MR_RATE_ROOT` environment variable). Use the placeholder `/path/to/mr-rate/data-preprocessing` in the examples below.
2. Generate synthetic PHI-free fixtures with `fixtures/generate_fixtures.py --step brainseg`, which writes `fixtures/modalities.json` and `fixtures/raw_niftis/A0001/*.nii.gz`.
3. Run a preflight environment-alignment check first with the `--preflight` flag. This verifies the execution environment (Python, required dependencies such as `torch`, `brainles_hd_bet`, `SimpleITK`, `nibabel`, `numpy`, `scipy`, and a CUDA GPU) is aligned before attempting a real run, failing fast on misalignment.
4. Run the wrapper `scripts/run_brain_seg_deface.py` for the real upstream step. The wrapper emits a structured telemetry block (timings/phase durations, environment including versions/GPU/host, and I/O counts) for dev/test/prod monitoring.

Example (preflight):

```
run_script("scripts/run_brain_seg_deface.py", args=["--fixtures", "fixtures", "--out", "out", "--mr-rate-root", "/path/to/mr-rate/data-preprocessing", "--preflight"])
```

Example (real run):

```
run_script("scripts/run_brain_seg_deface.py", args=["--fixtures", "fixtures", "--out", "out", "--mr-rate-root", "/path/to/mr-rate/data-preprocessing"])
```

## Available Scripts

| Script | Purpose | Arguments |
| --- | --- | --- |
| scripts/run_brain_seg_deface.py | Run the real MR-RATE brainseg step (HD-BET brain mask + Quickshear defacing) with a fail-fast preflight environment-alignment check and structured telemetry. | `--fixtures <dir>` `--out <dir>` `--mr-rate-root <path>` `[--device 0]` `[--preflight]` |
| fixtures/generate_fixtures.py | Generate synthetic PHI-free NIfTI inputs for the brainseg step. | `--step brainseg` |

## Prerequisites

- A local MR-RATE `data-preprocessing` checkout, referenced only via `--mr-rate-root` or `$MR_RATE_ROOT`.
- Python >= 3.10.
- Python dependencies: `torch`, `brainles_hd_bet`, `SimpleITK`, `nibabel`, `numpy`, `scipy`.
- A CUDA-capable GPU (this step is GPU-only).
- Fixtures generated via `fixtures/generate_fixtures.py --step brainseg`.

## Limitations

- Requires a CUDA GPU; there is no CPU fallback, so on GPU-less environments only the `--preflight` check can be exercised.
- Ships with small synthetic PHI-free fixtures that are not clinically representative.
- Upstream `accession_to_uid` anonymization is currently an identity pass-through, so study-ID de-identification is a no-op unless inputs are pre-anonymized.
- This is not a regulatory de-identifier; review output before sharing. Not for clinical use.

## Troubleshooting

- Preflight reports a missing dependency: install the listed package into the active environment and re-run `--preflight`.
- Preflight reports no GPU / CUDA unavailable: run on a CUDA-capable machine or verify driver/toolkit installation; the real step cannot run without a GPU.
- `--mr-rate-root` errors: confirm the path points at a valid MR-RATE `data-preprocessing` checkout containing `src/mr_rate_preprocessing/mri_preprocessing/brain_segmentation_and_defacing.py`.
- Empty or missing fixtures: regenerate them with `fixtures/generate_fixtures.py --step brainseg`.
- Inspect the emitted telemetry block (timings, environment, I/O counts) to diagnose phase-level failures or performance issues.

## Examples

Preflight only (verify environment alignment before a real run):

```
run_script("scripts/run_brain_seg_deface.py", args=["--fixtures", "fixtures", "--out", "out", "--mr-rate-root", "$MR_RATE_ROOT", "--preflight"])
```

Full real run on synthetic fixtures with an explicit device:

```
run_script("scripts/run_brain_seg_deface.py", args=["--fixtures", "fixtures", "--out", "out", "--mr-rate-root", "/path/to/mr-rate/data-preprocessing", "--device", "0"])
```
