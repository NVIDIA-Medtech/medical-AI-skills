---
name: mri-zip-upload
description: Validates that each MRI study has all expected modality files, anonymizes study IDs to UIDs, and zips each processed study for Hugging Face upload (MR-RATE MRI step 6); use it when preparing processed MRI studies for packaging and upload. Not for clinical use.
license: Apache-2.0
allowed-tools: Bash
metadata: { author: "NVIDIA MedTech <noreply@nvidia.com>", tags: [MedTech, MRI, zip] }
---

# mri-zip-upload — zip & upload processed studies

## Purpose

This skill wraps the real MR-RATE MRI-preprocessing zip step (step 6). It validates
that every processed study contains all expected modality files, anonymizes study
IDs to UIDs, and packages each study into a zip archive ready for Hugging Face
upload. The wrapper runs the genuine upstream code (no mock), gated by a fail-fast
environment-alignment preflight and instrumented with structured telemetry
(timings, environment, I/O counts) for dev/test/prod monitoring.

Not for clinical use.

## Instructions

1. Generate synthetic, PHI-free fixtures with `fixtures/generate_fixtures.py --step zip`,
   which writes a complete `fixtures/processed/A0001/{img,seg}` tree and
   `fixtures/modalities.json`.
2. Run the wrapper `scripts/run_zip_upload.py`. It first runs a preflight
   environment-alignment check (verifies the upstream script exists and required
   deps import), then executes the real upstream zip step and emits a telemetry
   block (per-phase timings, environment incl. versions/host, I/O counts).
3. Use `--preflight` to verify environment alignment WITHOUT executing the real
   run — useful to gate a run in dev/test/prod before committing to it.

Preflight-only example:

```
run_script("scripts/run_zip_upload.py", args=["--fixtures", "fixtures", "--out", "out", "--mr-rate-root", "/path/to/mr-rate/data-preprocessing", "--preflight"])
```

Real run example:

```
run_script("scripts/run_zip_upload.py", args=["--fixtures", "fixtures", "--out", "out", "--mr-rate-root", "/path/to/mr-rate/data-preprocessing"])
```

You may also point at the MR-RATE root via the `$MR_RATE_ROOT` environment
variable and pass it through `--mr-rate-root`.

## Available Scripts

| Script | Purpose | Arguments |
| --- | --- | --- |
| scripts/run_zip_upload.py | Run the real MR-RATE zip step (step 6) with preflight + telemetry | `--fixtures <dir> --out <dir> --mr-rate-root /path/to/mr-rate/data-preprocessing [--device 0] [--preflight]` |
| fixtures/generate_fixtures.py | Generate synthetic PHI-free input fixtures | `--step zip` |

## Prerequisites

- Python >= 3.10.
- Python packages: `numpy`, `nibabel` (checked by preflight).
- A local checkout of the MR-RATE `data-preprocessing` root, passed via
  `--mr-rate-root` (or `$MR_RATE_ROOT`). No GPU and no `dcm2niix` are required
  for this step.

## Limitations

- Upstream `accession_to_uid` anonymization is currently an identity
  pass-through, so study-ID de-identification is a no-op unless inputs are
  pre-anonymized.
- Ships with small synthetic PHI-free fixtures; not clinically representative.
- Not a regulatory de-identifier; review output before sharing. Not for clinical use.

## Troubleshooting

- **Preflight reports "environment not aligned"**: the JSON `preflight.checks`
  array names the failed check. `upstream_script_exists` failing means
  `--mr-rate-root` is wrong — it must point at the MR-RATE `data-preprocessing`
  root. `dep:<name>` failing means a required package (`numpy`/`nibabel`) is
  missing from the active Python environment.
- **Upstream exits non-zero**: the `error` field and stderr tail carry the
  upstream message; confirm the fixtures were generated with `--step zip` and
  that `fixtures/processed` and `fixtures/modalities.json` exist.
- **No zips produced**: check `telemetry.io.n_output_files` and the study tree
  under `fixtures/processed/`; each study must contain the expected modality files.

## Examples

Generate fixtures, run a preflight gate, then the real step:

```
run_script("fixtures/generate_fixtures.py", args=["--step", "zip"])
run_script("scripts/run_zip_upload.py", args=["--fixtures", "fixtures", "--out", "out", "--mr-rate-root", "/path/to/mr-rate/data-preprocessing", "--preflight"])
run_script("scripts/run_zip_upload.py", args=["--fixtures", "fixtures", "--out", "out", "--mr-rate-root", "/path/to/mr-rate/data-preprocessing"])
```

The wrapper prints a single JSON object on stdout (also written to
`<out>/telemetry.json`) with `status`, `outputs`, `preflight`, and a `telemetry`
block containing timings, environment facts, and I/O counts.
