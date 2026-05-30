---
name: train_vae
description: Upstream NV-Generate-CTMR notes for MAISI VAE finetuning from CT/MRI NIfTI datalists.
---

# MAISI VAE Finetuning

NV-Generate-CTMR documents VAE finetuning in `train_vae_tutorial.ipynb`. The
upstream repository provides configs and helper APIs, but no dedicated
`scripts.train_vae` command. An automated run should stage the VAE configs and
either run a local training loop against the upstream helper APIs or perform a
preflight-only staging check when the input bundle contains placeholders.

## Inputs

Use a MONAI-style datalist with relative image paths and modality class labels:

```json
{
  "training": [
    {"image": "imagesTr/case001.nii.gz", "class": "mri"}
  ],
  "validation": [
    {"image": "imagesVal/case001.nii.gz", "class": "mri"}
  ]
}
```

`testing` may be used instead of `validation` for the validation split. Each
entry needs an `image` path relative to the data root. The VAE transform
supports `ct` and `mri` classes; MRI-specific sequences should be normalized to
the `mri` class for VAE intensity transforms.

## Upstream Files

Stage or read these upstream files:

- `configs/config_network_rflow.json`
- `configs/environment_maisi_vae_train.json`
- `configs/config_maisi_vae_train.json`
- `scripts/transforms.py`, especially `VAE_Transform`
- `scripts/utils.py`, especially `define_instance`, `KL_loss`, and `dynamic_infer`
- `scripts/download_model_data.py` for fetching `models/autoencoder_v1.pt`

Do not edit `.workbench_data/upstreams` or `$NV_GENERATE_ROOT` in place. Put
edited runtime configs, staged datalists, checkpoints, TensorBoard logs, and
summaries under the requested output directory.

## Training Components From The Notebook

The notebook constructs:

- `VAE_Transform` for train and validation datasets
- MONAI `CacheDataset` and `DataLoader`
- `define_instance(args, "autoencoder_def")` for the MAISI autoencoder
- MONAI `PatchDiscriminator`
- reconstruction, KL, perceptual, and adversarial losses
- Adam optimizers and LambdaLR warmup schedulers
- optional checkpoint loading from `trained_autoencoder_path`
- checkpoint outputs `autoencoder.pt`, `discriminator.pt`, and best-epoch autoencoder checkpoints

For real training, install the upstream requirements plus `lpips` and
`tensorboard`, use a CUDA GPU, and provide real CT/MRI NIfTI volumes. Use small
patches, low cache rate, and one epoch for workflow smoke runs.

## Preflight Boundary

For a preflight-scale comparison, do not train on placeholder files. Check that
the datalist has non-empty training and validation/testing splits, all relative
image paths exist under the data root, modalities normalize to `ct` or `mri`,
and staged VAE config files point under the requested output directory. Write a
small JSON summary under the requested output directory.

## Scope

This is engineering workflow plumbing only. It does not validate reconstruction
quality, anatomical realism, downstream diffusion-model utility, clinical
interpretation, regulatory readiness, or production training-data approval.
