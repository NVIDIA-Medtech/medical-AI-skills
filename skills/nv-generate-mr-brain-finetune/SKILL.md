---
name: nv-generate-mr-brain-finetune
description: Used for finetuning NV-Generate-CTMR MR-brain diffusion UNet from a NIfTI datalist. Not for clinical or production data approval.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - medtech
    - mri
    - brain
    - finetune
---

# NV-Generate-MR-Brain-Finetune

## Purpose
- Used for finetuning the NV-Generate-CTMR `rflow-mr-brain` diffusion UNet from user-supplied NIfTI training volumes.
- Not for clinical interpretation, regulatory use, or approving synthetic data for production training.
- The wrapper stages the config glue locally and delegates execution to existing upstream scripts: `scripts.diff_model_create_training_data`, `scripts.diff_model_train`, and optionally `scripts.diff_model_infer`. It does not execute the notebook.
- Manifest I/O: inputs are `datalist` and `data_base_dir`; outputs are `finetuned_checkpoint`, optional `inference_outputs`, and `result_json`.

## Instructions
- Read `skill_manifest.yaml` before changing arguments, side effects, or validation gates.
- Run `scripts/run_mr_brain_finetune.py` from the Medical AI Skills repo root.
- If a host agent exposes `run_script`, use `run_script("scripts/run_mr_brain_finetune.py", args=[...])`; otherwise run the Bash/Python command below.
- Use `--preflight` first when checking a new datalist; remove `--preflight` only when the user explicitly wants to launch GPU finetuning.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/run_mr_brain_finetune.py` | Primary entrypoint declared by `skill_manifest.yaml`. | `DATALIST.json --data-base-dir DATA_DIR --output-dir OUT_DIR [--epochs N] [--modality mri_t1] [--run-inference] [--preflight]` |

## Prerequisites
- `NV_GENERATE_ROOT` may point to a current checkout of `https://github.com/NVIDIA-Medtech/NV-Generate-CTMR` containing `scripts/diff_model_create_training_data.py`, `scripts/diff_model_train.py`, and `scripts/diff_model_infer.py`.
- If `NV_GENERATE_ROOT` is unset, the wrapper searches `.workbench_data/upstreams/NV-Generate-CTMR`.
- `CUDA_VISIBLE_DEVICES` is optional and can be used to select the GPU for real training.
- Runtime requirements: NVIDIA CUDA GPU for real training, Python packages from the upstream `requirements.txt`, and downloaded MR-brain weights.
- Side effects: writes staged configs, embeddings, checkpoints, optional inference images, and logs under the caller-provided `--output-dir`; may write model caches under the upstream checkout and `~/.cache/huggingface/`; may contact `https://huggingface.co` for model assets and `https://github.com` for the upstream checkout.
- The datalist is a MONAI-style JSON object with `training[].image` paths relative to `--data-base-dir`. `training[].modality` is optional and defaults to `mri_t1`.

## Usage

Preflight only:

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && \
python skills/nv-generate-mr-brain-finetune/scripts/run_mr_brain_finetune.py \
  PATH_TO_DATALIST.json \
  --data-base-dir PATH_TO_DATA_ROOT \
  --output-dir runs/nv_generate_mr_brain_finetune_preflight \
  --preflight
```

GPU finetuning:

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && \
python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && \
python skills/nv-generate-mr-brain-finetune/scripts/run_mr_brain_finetune.py \
  PATH_TO_DATALIST.json \
  --data-base-dir PATH_TO_DATA_ROOT \
  --output-dir runs/nv_generate_mr_brain_finetune \
  --epochs 2 \
  --modality mri_t1 \
  --run-inference
```

Replace `PATH_TO_DATALIST.json` and `PATH_TO_DATA_ROOT` with the user's actual paths. Do not use the fixture datalist for real training; it is a preflight-only placeholder.

## Limitations
- Requires a current upstream `NV-Generate-CTMR` checkout with the existing diffusion training scripts. The skill itself stages the required config and datalist glue locally and does not depend on the notebook or PR #33.
- Full training can be expensive and is not deterministic across hardware, CUDA, and package versions.
- The wrapper gates file accounting and command provenance, not anatomical realism or downstream model utility.
- Not for clinical deployment, clinical interpretation, autonomous diagnosis, regulatory submission, or production training-data approval.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| `diffusion training scripts were not found` | `NV_GENERATE_ROOT` does not point at a current NV-Generate-CTMR checkout. | Clone or update `https://github.com/NVIDIA-Medtech/NV-Generate-CTMR` and set `NV_GENERATE_ROOT`. |
| `missing datalist image` | `training[].image` paths are not relative to `--data-base-dir` or files are absent. | Fix the datalist or pass the correct data root. |
| CUDA or MONAI import failure | Runtime environment lacks upstream dependencies. | Install `"$NV_GENERATE_ROOT/requirements.txt"` in the selected environment. |
