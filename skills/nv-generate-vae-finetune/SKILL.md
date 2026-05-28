---
name: nv-generate-vae-finetune
description: Used for finetuning the NV-Generate-CTMR MAISI VAE from CT/MRI NIfTI datalists. Not for clinical or production data approval.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - medtech
    - ct
    - mri
    - vae
    - finetune
---

# NV-Generate-VAE-Finetune

## Purpose
- Used for finetuning the NV-Generate-CTMR MAISI VAE/autoencoder from user-supplied CT or MRI NIfTI training volumes.
- Not for clinical interpretation, regulatory use, or approving synthetic data for production training.
- Upstream currently documents VAE training in `train_vae_tutorial.ipynb` and provides configs/helpers, but not a `scripts.train_vae` CLI. This skill does not execute the notebook; it stages the required config/datalist glue locally and uses upstream helper APIs.
- Manifest I/O: inputs are `datalist` and `data_base_dir`; outputs are `autoencoder_checkpoint`, `discriminator_checkpoint`, and `result_json`.

## Instructions
- Read `skill_manifest.yaml` before changing arguments, side effects, or validation gates.
- Run `scripts/run_vae_finetune.py` from the Medical AI Skills repo root.
- Use `--preflight` first when checking a new datalist; remove `--preflight` only when the user explicitly wants to launch GPU finetuning.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/run_vae_finetune.py` | Primary entrypoint declared by `skill_manifest.yaml`. | `DATALIST.json --data-base-dir DATA_DIR --output-dir OUT_DIR [--epochs N] [--modality mri] [--patch-size 64,64,64] [--preflight]` |

## Prerequisites
- `NV_GENERATE_ROOT` may point to a current checkout of `https://github.com/NVIDIA-Medtech/NV-Generate-CTMR` containing `configs/config_maisi_vae_train.json`, `scripts/transforms.py`, and `scripts/utils.py`.
- If `NV_GENERATE_ROOT` is unset, the wrapper searches `.workbench_data/upstreams/NV-Generate-CTMR`.
- `CUDA_VISIBLE_DEVICES` is optional and can be used to select the GPU for real training.
- Runtime requirements: NVIDIA CUDA GPU for real training, Python packages from the upstream `requirements.txt`, `lpips`, and downloaded VAE weights unless using `--train-from-scratch`.
- Side effects: writes staged configs, checkpoints, TensorBoard logs, and run summaries under the caller-provided `--output-dir`; may write model caches under the upstream checkout, `~/.cache/huggingface/`, and `~/.cache/torch/`; may contact `https://huggingface.co`, `https://github.com`, and `https://download.pytorch.org`.
- The datalist is a MONAI-style JSON object with non-empty `training[]` and `validation[]` or `testing[]`. Each entry has an `image` path relative to `--data-base-dir` and optional `class` or `modality` of `ct` or `mri`.

## Usage

Preflight only:

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && \
python skills/nv-generate-vae-finetune/scripts/run_vae_finetune.py \
  PATH_TO_DATALIST.json \
  --data-base-dir PATH_TO_DATA_ROOT \
  --output-dir runs/nv_generate_vae_finetune_preflight \
  --preflight
```

GPU finetuning:

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && \
python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && \
python -m pip install lpips tensorboard && \
python skills/nv-generate-vae-finetune/scripts/run_vae_finetune.py \
  PATH_TO_DATALIST.json \
  --data-base-dir PATH_TO_DATA_ROOT \
  --output-dir runs/nv_generate_vae_finetune \
  --epochs 1 \
  --modality mri \
  --patch-size 64,64,64 \
  --download-model-data
```

Replace `PATH_TO_DATALIST.json` and `PATH_TO_DATA_ROOT` with the user's actual paths. Do not use the fixture datalist for real training; it is a preflight-only placeholder.

## Limitations
- Requires a current upstream `NV-Generate-CTMR` checkout with VAE configs and helper APIs. The skill owns the runner glue and does not depend on the notebook.
- Full training can be expensive and is not deterministic across hardware, CUDA, and package versions.
- The wrapper gates file accounting and command provenance, not anatomical realism, reconstruction quality, or downstream model utility.
- Not for clinical deployment, clinical interpretation, autonomous diagnosis, regulatory submission, or production training-data approval.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| `VAE configs/helpers were not found` | `NV_GENERATE_ROOT` does not point at a current NV-Generate-CTMR checkout. | Clone or update `https://github.com/NVIDIA-Medtech/NV-Generate-CTMR` and set `NV_GENERATE_ROOT`. |
| `datalist must include non-empty validation[] or testing[]` | VAE training requires validation data for the configured validation loop. | Add `validation[]` or `testing[]` entries with relative image paths. |
| CUDA, MONAI, or LPIPS import failure | Runtime environment lacks upstream dependencies. | Install `"$NV_GENERATE_ROOT/requirements.txt"` plus `lpips tensorboard` in the selected environment. |
