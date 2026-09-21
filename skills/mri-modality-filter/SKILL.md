---
name: mri-modality-filter
description: Filters MR-RATE classified MRI series against acceptance criteria (modality, plane, shape/FOV, age) and designates one T1w center modality per study (MR-RATE MRI step 4); use it when preparing MRI studies for downstream MR-RATE preprocessing. Not for clinical use.
license: Apache-2.0
allowed-tools: Bash
metadata: { author: "NVIDIA MedTech <noreply@nvidia.com>", tags: [MedTech, MRI, modality] }
---

# mri-modality-filter — modality filtering & center selection

## Purpose

This skill runs MR-RATE MRI preprocessing step 4 (modality filtering) against the
real upstream code. It filters classified series by acceptance criteria — modality,
imaging plane, shape/FOV, and age — and designates a single T1w center modality per
study. The wrapper adds a fail-fast preflight environment-alignment check and a
structured telemetry block (timings, environment, I/O counts) so the same step can be
monitored consistently across dev, test, and prod. There is no mock path: the genuine
upstream MR-RATE modality step is executed. Not for clinical use.

## Instructions

1. Run a preflight check first to verify the execution environment is aligned before a
   real run. The `--preflight` mode confirms the upstream script exists and that the
   required Python dependencies (pandas, numpy, nibabel) import cleanly, then exits.
2. When the environment is aligned, run the wrapper `scripts/run_modality_filter.py`
   for real. It executes the genuine upstream MR-RATE modality step via subprocess,
   collects the produced artifacts, and emits a single JSON object on stdout plus a
   `telemetry.json` in the output directory. The telemetry block reports per-phase
   timings, environment facts (versions, host, timestamp), and I/O counts.
3. Point `--mr-rate-root` at your local MR-RATE `data-preprocessing` checkout (or set
   `$MR_RATE_ROOT`). Provide fixture inputs via `--fixtures` and an output directory
   via `--out`.

Preflight example:

```
run_script("scripts/run_modality_filter.py", args=[
    "--fixtures", "fixtures",
    "--out", "out",
    "--mr-rate-root", "/path/to/mr-rate/data-preprocessing",
    "--preflight",
])
```

Real run example:

```
run_script("scripts/run_modality_filter.py", args=[
    "--fixtures", "fixtures",
    "--out", "out",
    "--mr-rate-root", "/path/to/mr-rate/data-preprocessing",
])
```

## Available Scripts

| Script | Purpose | Arguments |
| --- | --- | --- |
| scripts/run_modality_filter.py | Run the real MR-RATE modality step (step 4) with preflight + telemetry | --fixtures <dir> --out <dir> --mr-rate-root /path/to/mr-rate/data-preprocessing [--device 0] [--preflight] |
| fixtures/generate_fixtures.py | Generate synthetic PHI-free inputs (`--step modality` writes fixtures/classified.csv and fixtures/raw_niftis/A0001/*.nii.gz) | --step modality |

## Prerequisites

- Python >= 3.10.
- Python dependencies importable in the active environment: pandas, numpy, nibabel.
- A local MR-RATE `data-preprocessing` checkout, referenced via `--mr-rate-root` or
  `$MR_RATE_ROOT` (no GPU or dcm2niix required for this step).
- Fixture inputs generated with `fixtures/generate_fixtures.py --step modality`.

## Limitations

- Ships with small synthetic, PHI-free fixtures that are not clinically representative.
- Upstream `accession_to_uid` anonymization is currently an identity pass-through, so
  study-ID de-identification is a no-op unless inputs are pre-anonymized.
- This is a development/research wrapper, not a regulatory de-identifier or clinical
  tool. Not for clinical use.

## Troubleshooting

- Preflight reports "environment not aligned": inspect the `preflight.checks` array in
  the emitted JSON. A failing `upstream_script_exists` check means `--mr-rate-root` is
  wrong; failing `dep:*` checks mean pandas/numpy/nibabel are missing from the active
  environment.
- Upstream exits non-zero: the `error` field and stderr tail carry the upstream message;
  confirm the fixtures were generated with `--step modality` and that
  `fixtures/classified.csv` and `fixtures/raw_niftis/` exist.
- No JSON on stdout: logs are written to stderr; only the final JSON object goes to
  stdout, and a copy is written to `<out>/telemetry.json`.

## Examples

Generate fixtures, run the preflight, then execute the real step:

```
run_script("fixtures/generate_fixtures.py", args=["--step", "modality"])

run_script("scripts/run_modality_filter.py", args=[
    "--fixtures", "fixtures",
    "--out", "out",
    "--mr-rate-root", "$MR_RATE_ROOT",
    "--preflight",
])

run_script("scripts/run_modality_filter.py", args=[
    "--fixtures", "fixtures",
    "--out", "out",
    "--mr-rate-root", "$MR_RATE_ROOT",
])
```

On success the wrapper writes `out/modalities.json` and `out/metadata.csv`, and emits a
telemetry block covering timings, environment, and I/O counts.
