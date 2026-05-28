---
name: holohub-imaging-ai-segmentator
description: Used for running HoloHub imaging_ai_segmentator on a DICOM CT series and recording artifacts. Not for clinical segmentation claims.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - medtech
    - holohub
    - segmentation
---

# HoloHub Imaging AI Segmentator

## Purpose
- Used for running HoloHub imaging_ai_segmentator on a DICOM CT series and recording artifacts. Not for clinical segmentation claims.
- Use the wrapper exactly as documented; do not replace the upstream entrypoint with a handwritten implementation.
- Manifest I/O: inputs are `dicom_dir`; outputs are `dicom_seg`, `nifti_segmentation`, and `result_json`.

## Instructions
- Read `skill_manifest.yaml` before changing arguments, side effects, or validation gates.
- Run `scripts/run_holohub_app.py` through the documented command below; keep outputs under a caller-provided run directory.
- If a host agent exposes `run_script`, use `run_script("scripts/run_holohub_app.py", args=[...])`; otherwise run the Bash/Python command shown below.
- Check the emitted JSON and paired verifier guidance before treating the run as evidence.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/run_holohub_app.py` | Primary entrypoint declared by skill_manifest.yaml. | `[PATH_TO_DICOM_DIR]` plus `HOLOHUB_ROOT` and optional `HOLOSCAN_*` env vars |

## Prerequisites
- Required environment variables: `HOLOHUB_ROOT`.
- Runtime requirements: GPU/CUDA when declared by the manifest; Docker/NVIDIA Container Toolkit when container mode is used.
- Side effects: writes HoloHub artifacts under `$HOLOHUB_ROOT`, may create `/tmp/holohub-*.cid`, may write Docker layers under `/var/lib/docker/`, and may pull from `https://github.com` and `https://nvcr.io`.
- Run commands from the repository root unless an existing section below says otherwise.

## Limitations
- HoloHub's auto-downloaded "test" DICOM fixture is a single-slice CT (CT_DICOM_SINGLE/7106) and triggers an empty segmentation: graph executes but the output mask is all zeros. Real verification needs a multi-slice CT abdomen series. The repo ships `fixtures/build_dicom_from_nifti.py` which converts a Decathlon Spleen NIfTI volume into a HoloHub-acceptable DICOM CT series.
- Synthesised DICOM fixtures must include `ImageType=['ORIGINAL', 'PRIMARY']` (HoloHub's SeriesSelectorOperator filter) and `StudyID` (required by highdicom's DICOM SEG writer). Missing either silently falls back to the auto-fetched single-slice brain CT or fails late inside the SEG writer.
- Container mode requires docker, an NVIDIA GPU, and ~18GB GPU memory for a 55-slice CT abdomen series during sliding-window inference.
- First container build downloads the Holoscan SDK image (~minutes). Subsequent runs reuse the cached image. The wrapper passes `--configure-args=-DHOLOHUB_DOWNLOAD_DATASETS=OFF` to skip re-fetching the upstream test DICOM zip on every run.
- Not for clinical deployment, clinical interpretation, autonomous diagnosis, regulatory submission.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| Missing dependency or import error | Runtime package drift from `skill_manifest.yaml`. | Install the packages declared in the manifest or use the documented setup command. |
| Empty or schema-invalid output | Wrong input path, unsupported modality, or upstream failure. | Re-run with a known fixture and inspect the wrapper JSON plus stderr. |
| Validation gate failure | Output violated a declared engineering invariant. | Keep the failed evidence pack and use the gate message to repair inputs or wrapper code. |

Runs `applications/imaging_ai_segmentator` through HoloHub's documented CLI.
It does not reimplement the DICOM to MONAI to DICOM SEG pipeline.

## Preconditions

Clone HoloHub and point `HOLOHUB_ROOT` at it; container mode also needs
Docker, NVIDIA Container Toolkit, an NVIDIA GPU, and network access for the
first-run image pull.

```bash
git clone https://github.com/nvidia-holoscan/holohub.git $HOME/holohub
export HOLOHUB_ROOT=$HOME/holohub
```

The `--fixture` directory must contain a single readable DICOM series. The
skill's `fixture_help` lists builder scripts that synthesize DICOM from
public NIfTI datasets (e.g., MSD09 Spleen) when you don't have a real series
on disk.

Optional HoloHub controls:

| Variable | Purpose |
|---|---|
| `HOLOHUB_RUN_MODE` | Select `container` or `local` execution. |
| `HOLOSCAN_OUTPUT_PATH` | Override the app output directory scanned by the wrapper. |
| `HOLOSCAN_MODEL_PATH` | Override the model directory passed to the HoloHub app. |
| `HOLOHUB_TIMEOUT_SECONDS` | Bound the upstream app subprocess. |

## Usage

```bash
HOLOHUB_ROOT=/path/to/holohub HOLOHUB_RUN_MODE=container \
python3 -m eval_engine.run skills/holohub-imaging-ai-segmentator \
  --fixture /path/to/ct_series \
  --out runs/holohub_imaging_demo
``` The wrapper records HoloHub commit, container image,
output file inventory, non-empty segmentation checks, runtime, and cost.

Do not treat the bundled HoloHub smoke data as clinical validation.
