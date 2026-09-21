---
name: mri-pacs-metadata-filter
description: Cleans a raw PACS DICOM-metadata CSV by enforcing required columns, dropping rows with missing critical identifiers, and de-duplicating series (MR-RATE MRI step 2); use it during MRI dataset preprocessing to produce a filtered metadata CSV before downstream steps. Not for clinical use.
license: Apache-2.0
allowed-tools: Bash
metadata: { author: "NVIDIA MedTech <noreply@nvidia.com>", tags: [MedTech, MRI, pacs] }
---

# mri-pacs-metadata-filter — PACS metadata filtering

## Purpose

This skill wraps step 2 of the MR-RATE MRI preprocessing pipeline: PACS metadata
filtering. Given a raw PACS DICOM-metadata CSV, it enforces the required column
set, drops rows that are missing critical identifiers (e.g. missing patient age
or series identifiers), and de-duplicates repeated series. The result is a
cleaned `filtered.csv` suitable for the later classification, modality-filtering,
and segmentation steps.

The skill does not reimplement the filtering logic. It invokes the genuine
upstream MR-RATE script via a thin wrapper that adds a fail-fast environment
preflight and structured telemetry, so the same behavior can be monitored across
dev, test, and prod. Not for clinical use.

## Instructions

Run the wrapper `scripts/run_pacs_metadata_filter.py`. It first executes a
**preflight** environment-alignment check (verifying the exact upstream script
exists and that the required Python dependencies import), then runs the real
upstream PACS step as a subprocess. It prints a single JSON object to stdout and
also writes a `telemetry.json` into the output directory containing per-phase
timings, environment facts (Python/package versions, host, timestamp), and I/O
counts.

Use `--preflight` to verify environment alignment **before** committing to a real
run. In preflight mode the wrapper performs only the alignment checks and exits
non-zero if the environment is misaligned:

```
run_script("scripts/run_pacs_metadata_filter.py", args=[
    "--fixtures", "/path/to/fixtures",
    "--out", "/path/to/out",
    "--mr-rate-root", "$MR_RATE_ROOT",
    "--preflight",
])
```

Then perform the real run (omit `--preflight`):

```
run_script("scripts/run_pacs_metadata_filter.py", args=[
    "--fixtures", "/path/to/fixtures",
    "--out", "/path/to/out",
    "--mr-rate-root", "$MR_RATE_ROOT",
])
```

The `--fixtures` directory must contain `pacs_metadata.csv`; generate a synthetic
one with `python fixtures/generate_fixtures.py --step pacs --out /path/to/fixtures`.
The wrapper writes the cleaned result to `<out>/filtered.csv`. Provide the
MR-RATE checkout path only via `--mr-rate-root` or the `$MR_RATE_ROOT`
environment variable.

## Available Scripts

| Script | Purpose | Arguments |
| --- | --- | --- |
| scripts/run_pacs_metadata_filter.py | Run the real MR-RATE PACS metadata-filtering step with preflight + telemetry | `--fixtures <dir>` `--out <dir>` `--mr-rate-root <path>` `[--device 0]` `[--preflight]` |
| fixtures/generate_fixtures.py | Generate synthetic PHI-free `pacs_metadata.csv` fixtures | `--step pacs --out <dir>` |

## Prerequisites

- Python >= 3.10.
- The `pandas` package installed in the active interpreter.
- A local MR-RATE (`Forithmus/MR-RATE`) checkout containing
  `src/mr_rate_preprocessing/mri_preprocessing/pacs_metadata_filtering.py`,
  referenced via `--mr-rate-root` or `$MR_RATE_ROOT`.
- No GPU and no `dcm2niix` are required for this step.

## Limitations

- Not a regulatory de-identifier and not for clinical use; review outputs before
  sharing.
- Upstream `accession_to_uid` anonymization is currently an identity
  pass-through, so study-ID de-identification is a no-op unless inputs are
  pre-anonymized.
- Ships with small synthetic fixtures that are not clinically representative.
- The wrapper delegates all filtering behavior to the upstream script and does
  not modify or improve it.

## Troubleshooting

- **Preflight reports `environment not aligned`**: read the failing check names
  in the emitted JSON. `upstream_script_exists` failing means `--mr-rate-root`
  is wrong or the checkout is incomplete; `dep:pandas` failing means `pandas` is
  not installed in the active interpreter.
- **Upstream exits non-zero**: the JSON `error` field and stderr tail carry the
  upstream message. Confirm `<fixtures>/pacs_metadata.csv` exists and has the
  required columns; regenerate it with the fixtures script if needed.
- **No `filtered.csv` produced**: check the `telemetry.io` counts and
  `produced_files` list in the output JSON / `telemetry.json`.

## Examples

Preflight only, using an environment variable for the MR-RATE root:

```
export MR_RATE_ROOT=/path/to/mr-rate/data-preprocessing
python fixtures/generate_fixtures.py --step pacs --out ./fx
python scripts/run_pacs_metadata_filter.py \
    --fixtures ./fx --out ./out --mr-rate-root "$MR_RATE_ROOT" --preflight
```

Full real run against synthetic fixtures:

```
python scripts/run_pacs_metadata_filter.py \
    --fixtures ./fx --out ./out --mr-rate-root /path/to/mr-rate/data-preprocessing
```

On success the wrapper exits 0, writes `./out/filtered.csv`, and emits a JSON
object (also saved to `./out/telemetry.json`) whose `telemetry` block records the
preflight result, per-phase timings, environment, and I/O counts.
