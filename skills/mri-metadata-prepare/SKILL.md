---
name: mri-metadata-prepare
description: Merges patient IDs and anonymized study dates, drops sensitive UID/accession columns, and writes a clean per-batch metadata CSV for the MR-RATE MRI pipeline (step 7); use it to produce a shareable metadata table after brain segmentation. Not for clinical use.
license: Apache-2.0
allowed-tools: Bash
metadata: { author: "NVIDIA MedTech <noreply@nvidia.com>", tags: [MedTech, MRI, metadata] }
---

# mri-metadata-prepare — de-identified metadata preparation

## Purpose

This skill wraps the real MR-RATE MRI-preprocessing metadata step (step 7). It
merges patient IDs and anonymized study dates into the per-series metadata,
drops sensitive UID/accession columns, and writes a clean per-batch metadata
CSV. The wrapper runs the genuine upstream code — not a mock — with a fail-fast
environment-alignment preflight and structured telemetry for dev/test/prod
monitoring. Not for clinical use.

## Instructions

1. Ensure the MR-RATE `data-preprocessing` checkout is available and pass its
   location via `--mr-rate-root` (or the `$MR_RATE_ROOT` environment variable).
2. Generate synthetic, PHI-free inputs with
   `fixtures/generate_fixtures.py --step metadata`, which writes
   `fixtures/processed/A0001/{img,seg}`, `fixtures/modalities.json`,
   `fixtures/modalities_metadata.csv`, and the two mapping `.xlsx` files.
3. Run a preflight first to verify the execution environment is aligned (the
   exact upstream script exists and required Python dependencies import) before
   attempting a real run:

   ```
   run_script("scripts/run_metadata_prepare.py", args=[
       "--fixtures", "fixtures",
       "--out", "out",
       "--mr-rate-root", "$MR_RATE_ROOT",
       "--preflight",
   ])
   ```

4. Then perform the real metadata step. The wrapper is
   `scripts/run_metadata_prepare.py`:

   ```
   run_script("scripts/run_metadata_prepare.py", args=[
       "--fixtures", "fixtures",
       "--out", "out",
       "--mr-rate-root", "/path/to/mr-rate/data-preprocessing",
   ])
   ```

5. Inspect the JSON emitted on stdout and `out/telemetry.json`. On success the
   cleaned per-batch metadata CSV is written to `out/metadata.csv`.

The wrapper always runs a preflight environment-alignment check first, then
emits a single JSON object containing a `telemetry` block with per-phase
timings, environment facts (Python/package versions, host, timestamp), and I/O
counts. Exit code 0 means aligned/success; non-zero means misaligned or an
upstream failure.

## Available Scripts

| Script | Purpose | Arguments |
| --- | --- | --- |
| scripts/run_metadata_prepare.py | Run the real MR-RATE metadata step (step 7) with preflight + telemetry | `--fixtures <dir> --out <dir> --mr-rate-root <dir> [--device 0] [--preflight]` |

## Prerequisites

- Python >= 3.10.
- Python packages: `pandas`, `openpyxl`, `numpy`, `nibabel`.
- A local checkout of the MR-RATE `data-preprocessing` tree, supplied via
  `--mr-rate-root` or `$MR_RATE_ROOT`. The upstream script
  `src/mr_rate_preprocessing/mri_preprocessing/prepare_metadata.py` must exist
  under that root.
- No GPU and no `dcm2niix` are required for this step.
- Synthetic fixtures produced by `fixtures/generate_fixtures.py --step metadata`.

## Limitations

- Upstream `accession_to_uid` anonymization is currently an identity
  pass-through, so study-ID de-identification is a no-op unless inputs are
  pre-anonymized.
- Ships with small synthetic PHI-free fixtures that are not clinically
  representative.
- This is not a regulatory de-identifier; review output before sharing.
- Not for clinical use.

## Troubleshooting

- **Preflight reports `environment not aligned`**: the JSON `preflight.checks`
  array names the failing check. `upstream_script_exists` failing means
  `--mr-rate-root` is wrong or the checkout is incomplete; a `dep:<name>` check
  failing means an expected Python package is missing — install it and re-run.
- **Upstream exits non-zero**: read the `error` field in the emitted JSON and
  the stderr tail; confirm the fixtures were generated with
  `--step metadata` and that the mapping `.xlsx` files are present.
- **No `out/metadata.csv`**: the run failed before writing output; check
  `out/telemetry.json` for the `command`, `upstream_returncode`, and phase
  timings.

## Examples

Preflight only (verify environment alignment, run nothing else):

```
run_script("scripts/run_metadata_prepare.py", args=[
    "--fixtures", "fixtures",
    "--out", "out",
    "--mr-rate-root", "/path/to/mr-rate/data-preprocessing",
    "--preflight",
])
```

Full real run against generated fixtures:

```
run_script("scripts/run_metadata_prepare.py", args=[
    "--fixtures", "fixtures",
    "--out", "out",
    "--mr-rate-root", "$MR_RATE_ROOT",
    "--device", "0",
])
```
