---
name: mri-dcm2niix
description: Converts a folder of DICOM slices to a gzip-compressed NIfTI volume via the MR-RATE dcm2niix wrapper (MRI preprocessing step 1); use it to prepare MRI DICOM series for downstream NIfTI-based processing. Not for clinical use.
license: Apache-2.0
allowed-tools: Bash
metadata: { author: "NVIDIA MedTech <noreply@nvidia.com>", tags: [MedTech, MRI, dcm2niix] }
---

# mri-dcm2niix — DICOM to NIfTI conversion

## Purpose

This skill converts a folder of DICOM slices into a gzip-compressed NIfTI
(`.nii.gz`) volume by running the real MR-RATE MRI-preprocessing `dcm2niix`
step (step 1 of the pipeline). It wraps the genuine upstream conversion with a
fail-fast environment preflight and structured telemetry so runs are
observable across dev, test, and prod. Not for clinical use.

## Instructions

1. Ensure the MR-RATE `data-preprocessing` checkout is available and pass its
   path via `--mr-rate-root` (or the `$MR_RATE_ROOT` environment variable).
2. Generate synthetic, PHI-free input fixtures with the fixtures generator
   (`--step dcm2niix`). This writes `fixtures/dicom/A0001/*.dcm` and
   `fixtures/dicom_folder_paths.csv`.
3. Run a **preflight** first with `--preflight` to verify execution-environment
   alignment (the upstream script exists, required Python deps import, and
   `dcm2niix` is on `PATH`) before any real conversion. A misaligned
   environment exits non-zero.
4. Run the real conversion with the wrapper `scripts/run_dcm2niix.py`. It
   invokes the upstream step via subprocess, collects the produced NIfTI
   artifacts, and emits a single JSON object on stdout plus
   `<out>/telemetry.json` containing a `telemetry` block (per-phase timings,
   environment facts incl. package versions and host, and I/O counts).

Example (preflight, then real run):

```
run_script("scripts/run_dcm2niix.py", args=["--fixtures", "fixtures", "--out", "out", "--mr-rate-root", "$MR_RATE_ROOT", "--preflight"])
run_script("scripts/run_dcm2niix.py", args=["--fixtures", "fixtures", "--out", "out", "--mr-rate-root", "$MR_RATE_ROOT"])
```

## Available Scripts

| Script | Purpose | Arguments |
| --- | --- | --- |
| scripts/run_dcm2niix.py | Run the real MR-RATE dcm2niix step (DICOM folder -> gzip NIfTI) with preflight + telemetry | `--fixtures <fixtures_dir> --out <out_dir> --mr-rate-root <mr_rate_root> [--device 0] [--preflight]` |
| fixtures/generate_fixtures.py | Generate synthetic PHI-free DICOM inputs and `dicom_folder_paths.csv` | `--step dcm2niix` |

## Prerequisites

- Python >= 3.10.
- A local MR-RATE `data-preprocessing` checkout, referenced via
  `--mr-rate-root` or `$MR_RATE_ROOT` (e.g.
  `/path/to/mr-rate/data-preprocessing`).
- Upstream Python dependencies importable: `pandas`, `pydicom`.
- `dcm2niix` installed and available on `PATH`.
- No GPU required for this step.

## Limitations

- Ships with small synthetic fixtures that are not clinically representative.
- Upstream study-ID anonymization is an identity pass-through, so
  de-identification is a no-op unless inputs are pre-anonymized.
- Not a regulatory de-identifier and not for clinical use, autonomous
  diagnosis, or patient-facing use.

## Troubleshooting

- **Preflight reports "environment not aligned"**: read the failing check names
  in the JSON `preflight.checks`. Common causes: wrong `--mr-rate-root` (missing
  upstream script), a dependency not installed, or `dcm2niix` not on `PATH`.
- **`dcm2niix_on_path` fails**: install `dcm2niix` and ensure it is on `PATH`.
- **Upstream exits non-zero**: check the `error` field in the JSON and the
  stderr tail; confirm `fixtures/dicom_folder_paths.csv` points at valid DICOM
  folders.
- **No output files**: verify fixtures were generated with
  `generate_fixtures.py --step dcm2niix` and that `--fixtures` points at that
  directory.

## Examples

Generate fixtures, preflight, then convert:

```
run_script("fixtures/generate_fixtures.py", args=["--step", "dcm2niix"])
run_script("scripts/run_dcm2niix.py", args=["--fixtures", "fixtures", "--out", "out", "--mr-rate-root", "/path/to/mr-rate/data-preprocessing", "--preflight"])
run_script("scripts/run_dcm2niix.py", args=["--fixtures", "fixtures", "--out", "out", "--mr-rate-root", "/path/to/mr-rate/data-preprocessing"])
```

On success the wrapper prints a JSON object with `status: "ok"`, the produced
NIfTI files under `outputs.produced_files`, and a `telemetry` block; it also
writes `out/telemetry.json`.
