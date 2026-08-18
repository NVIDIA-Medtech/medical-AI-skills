---
name: nv-curate-mri
description: Orchestrates the full MR-RATE MRI curation pipeline (DICOM to NIfTI, metadata filtering, series classification, modality filtering, HD-BET/Quickshear defacing, zip, and metadata) from a single batch config; use it to run the real upstream MR-RATE orchestrator step end to end on a batch of studies. Not for clinical use.
license: Apache-2.0
allowed-tools: Bash
metadata: { author: "NVIDIA MedTech <noreply@nvidia.com>", tags: [MedTech, MRI, orchestrator] }
---

# nv-curate-mri — MR-RATE MRI pipeline orchestrator

## Purpose

`nv-curate-mri` orchestrates the entire MR-RATE MRI-preprocessing pipeline from one
batch configuration. It drives the genuine upstream runners
(`run/run_mri_preprocessing.py` then `run/run_mri_upload.py`) so that a batch of
studies flows through every stage:

- DICOM to NIfTI conversion (dcm2niix)
- PACS metadata filtering
- series classification
- modality filtering
- brain segmentation / defacing (HD-BET + Quickshear)
- zipping of processed outputs
- metadata preparation

There is no mock path: the skill always executes the real upstream code. It wraps
that execution with a fail-fast preflight environment-alignment check and a
structured telemetry block for dev/test/prod monitoring. Not for clinical use.

## Instructions

Use the wrapper `scripts/run_mri_pipeline.py`. It first runs a **preflight
environment-alignment check** (upstream runners present, required Python
dependencies importable with versions, `dcm2niix` on `PATH`, and a usable CUDA GPU
visible), then executes the real upstream orchestrator step and emits a telemetry
block (per-phase timings, environment facts, and I/O counts).

Verify the environment first with `--preflight` (this runs only the alignment
check and exits without executing the pipeline):

```
run_script("scripts/run_mri_pipeline.py", args=[
    "--fixtures", "/path/to/fixtures",
    "--out", "/path/to/out",
    "--mr-rate-root", "/path/to/mr-rate/data-preprocessing",
    "--preflight",
])
```

Then perform a full real run:

```
run_script("scripts/run_mri_pipeline.py", args=[
    "--fixtures", "/path/to/fixtures",
    "--out", "/path/to/out",
    "--mr-rate-root", "/path/to/mr-rate/data-preprocessing",
])
```

The `--mr-rate-root` value must point at your local MR-RATE
`data-preprocessing` checkout (you may also export it as `$MR_RATE_ROOT` and pass
that). Optionally pass `--device 0` to select the CUDA device. Generate synthetic,
PHI-free inputs for `--fixtures` with
`fixtures/generate_fixtures.py --step orchestrator --out <dir>`.

The wrapper prints exactly one JSON object on stdout (conforming to
`validators/output_schema.json`) and also writes `<out>/telemetry.json`. Exit code
`0` means aligned/success; non-zero means a misaligned environment or an upstream
failure.

## Available Scripts

| Script | Purpose | Arguments |
| --- | --- | --- |
| scripts/run_mri_pipeline.py | Run the full MR-RATE MRI orchestrator (real runners) with preflight + telemetry | `--fixtures <dir> --out <dir> --mr-rate-root <dir> [--device 0] [--preflight]` |
| fixtures/generate_fixtures.py | Generate synthetic PHI-free orchestrator inputs (single T1 study) | `--step orchestrator --out <dir>` |

## Prerequisites

- A local MR-RATE `data-preprocessing` checkout, referenced via `--mr-rate-root`
  or `$MR_RATE_ROOT` (use the placeholder `/path/to/mr-rate/data-preprocessing`).
- Python >= 3.10 with the upstream dependencies importable: `pandas`, `numpy`,
  `nibabel`, `pydicom`, `SimpleITK`, `scipy`, `torch`, `brainles_hd_bet`,
  `openpyxl`, `yaml`.
- `dcm2niix` on `PATH`.
- A usable CUDA GPU (the defacing/brain-segmentation stage is GPU-only).
- Input fixtures directory (e.g. produced by `fixtures/generate_fixtures.py`).

## Limitations

- The brain-segmentation/defacing stage requires CUDA; without a visible GPU the
  preflight check fails and no pipeline runs.
- Upstream `accession_to_uid` anonymization is currently an identity
  pass-through, so study-ID de-identification is a no-op unless inputs are
  pre-anonymized.
- Ships with small synthetic PHI-free fixtures only; not clinically
  representative.
- Not a regulatory de-identifier and not for clinical use; review outputs before
  sharing.

## Troubleshooting

- **`environment not aligned` error / non-zero exit in preflight**: read the
  `preflight.checks` array in the JSON output. Each failing check names the
  problem (missing runner, missing dependency, `dcm2niix` not on `PATH`, or no
  CUDA GPU). Fix the reported item and re-run `--preflight`.
- **`upstream_script_exists` / `runner_exists` false**: `--mr-rate-root` does not
  point at a valid `data-preprocessing` checkout containing
  `run/run_mri_preprocessing.py` and `run/run_mri_upload.py`.
- **`cuda_gpu_available` false**: ensure `torch` sees a GPU; check
  `CUDA_VISIBLE_DEVICES` and the `--device` index.
- **`dcm2niix_on_path` false**: install `dcm2niix` and ensure it is on `PATH`.
- **Pipeline runner exited non-zero**: inspect the `error` field and
  `<out>/logs`; the `telemetry.phases` timings show which runner stage ran.

## Examples

Preflight only (verify alignment, run nothing):

```
run_script("scripts/run_mri_pipeline.py", args=[
    "--fixtures", "/path/to/fixtures",
    "--out", "/path/to/out",
    "--mr-rate-root", "/path/to/mr-rate/data-preprocessing",
    "--preflight",
])
```

Full real run selecting GPU 0:

```
run_script("scripts/run_mri_pipeline.py", args=[
    "--fixtures", "/path/to/fixtures",
    "--out", "/path/to/out",
    "--mr-rate-root", "/path/to/mr-rate/data-preprocessing",
    "--device", "0",
])
```

Generate synthetic inputs, then run:

```
run_script("fixtures/generate_fixtures.py", args=["--step", "orchestrator", "--out", "/path/to/fixtures"])
run_script("scripts/run_mri_pipeline.py", args=[
    "--fixtures", "/path/to/fixtures",
    "--out", "/path/to/out",
    "--mr-rate-root", "/path/to/mr-rate/data-preprocessing",
])
```
