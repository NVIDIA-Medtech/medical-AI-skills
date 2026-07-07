---
name: mlflow-evidence-export
description: Used for exporting a sanitized Medical AI Skills evidence-pack summary to MLflow. Not for raw medical-data upload or model registration.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: NVIDIA MedTech Team
  tags:
    - MedTech
    - MLflow
    - evidence
---

# MLflow Evidence Export

## Purpose

- Used for mirroring comparison-safe evidence-pack facts into an MLflow experiment.
- Wraps the MLflow Python client and emits a schema-checked export result.
- Manifest input is `evidence_source`; output is `export_result` JSON.

## Instructions

- Run `scripts/export_evidence_pack.py` with an evidence pack, trusted-run directory, or direct result JSON.
- Start with the default `dry-run` mode and inspect the tags and metrics before enabling export.
- If a host exposes `run_script`, use `run_script("scripts/export_evidence_pack.py", args=["PACK_DIR", "--mode", "dry-run"])`.
- Do not add raw evidence artifacts, checkpoints, DICOM, or NIfTI files to this prototype.

## Available Scripts

| Script | Purpose | Arguments |
|---|---|---|
| `scripts/export_evidence_pack.py` | Export a sanitized evidence summary through MLflow. | `PACK_DIR [--mode dry-run\|local\|databricks] [--tracking-uri URI] [--experiment-name NAME] [--run-name NAME]` |

## Prerequisites

- Python 3.10+.
- Install `mlflow>=2.10,<4` only for `local` or `databricks` mode; `dry-run` uses the standard library.
- For Databricks, configure MLflow authentication using `DATABRICKS_HOST` and `DATABRICKS_TOKEN`, or the caller's standard Databricks profile. `MLFLOW_TRACKING_URI` may also be set by the caller.
- Without an explicit tracking URI, local mode writes under `<current-working-directory>/mlruns`; Databricks mode may contact `https://<caller-provided-databricks-workspace>`.

## Usage

Inspect the proposed summary without contacting MLflow:

```bash
python skills/mlflow-evidence-export/scripts/export_evidence_pack.py \
  runs/example_pack --mode dry-run
```

Log to a local MLflow file store:

```bash
python skills/mlflow-evidence-export/scripts/export_evidence_pack.py \
  runs/example_pack --mode local --experiment-name medical-ai-skills
```

Export a direct skill run (the simplest path for a Databricks notebook). A skill
emits its result JSON to stdout, so redirect it to a file and pass that file:

```bash
python skills/nv-generate-ct-rflow/scripts/run_rflow_ct.py FIXTURE.json \
  --output-dir /tmp/nv-generate-ct-output --yes \
  > /tmp/nv-generate-ct-result.json
python skills/mlflow-evidence-export/scripts/export_evidence_pack.py \
  /tmp/nv-generate-ct-result.json \
  --mode databricks --experiment-name /Shared/medical-ai-skills
```

The exporter accepts either an eval-engine evidence pack (a directory with
`manifest.json`) or a single direct-run result JSON file. In the direct-run
case it logs a scalar `metrics` block from the result plus identity tags; to
surface skill-specific numbers (e.g. tumor volume, generation time), the skill's
emitted result should carry a top-level `metrics` object of scalar values.

## Limitations

- This discussion prototype logs only tags, runtime metrics, and one sanitized JSON summary.
- It does not upload evidence-pack files or large artifacts.
- It does not register models or validate Databricks permissions.
- Engineering verification only; not for clinical or regulatory use.

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| Evidence pack not recognized | `manifest.json` is absent from the directory and its `skill_run/` child. | Pass a direct evidence pack or trusted-run root. |
| MLflow import fails | Live mode was selected without MLflow installed. | Install the declared MLflow version or use `--mode dry-run`. |
| Databricks request fails | Credentials, tracking URI, or experiment permissions are missing. | Validate the caller's Databricks MLflow configuration outside the skill. |
