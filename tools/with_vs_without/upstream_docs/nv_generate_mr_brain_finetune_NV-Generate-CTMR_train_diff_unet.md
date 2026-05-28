---
name: train_diff_unet_mr_brain
description: Upstream NV-Generate-CTMR notes for MR-brain diffusion-UNet finetuning from a MONAI-style datalist.
---

# MR-Brain Diffusion-UNet Finetuning

NV-Generate-CTMR documents diffusion-UNet finetuning in
`train_diff_unet_tutorial.ipynb` and exposes reusable script entrypoints for
the runnable stages. The notebook itself is not a CLI; an automated run should
stage JSON configs under the requested output directory and invoke the upstream
scripts from the NV-Generate-CTMR checkout.

## Inputs

Use a MONAI-style datalist with relative image paths:

```json
{
  "training": [
    {"image": "imagesTr/case001.nii.gz", "modality": "mri_t1"}
  ],
  "testing": []
}
```

Resolve each relative `image` against the selected data root. Supported
MR-brain modalities come from `configs/modality_mapping.json`, including
`mri_t1`, `mri_t2`, `mri_flair`, `mri_swi`, and skull-stripped variants.

## Configs To Stage

Copy or derive these files into the run output directory before editing them:

- `configs/config_network_rflow.json`
- `configs/environment_maisi_diff_model_rflow-mr-brain.json`
- `configs/config_maisi_diff_model_rflow-mr-brain.json`
- `configs/modality_mapping.json`

Do not edit the files in `.workbench_data/upstreams` or `$NV_GENERATE_ROOT` in
place. Put edited runtime configs under the requested output directory.

Set at least these environment-config values in the staged copy:

- `data_base_dir`: data root containing the datalist-relative images
- `json_data_list`: staged datalist path
- `embedding_base_dir`: output subdirectory for image embeddings
- `model_dir`: output subdirectory for checkpoints
- `output_dir`: optional inference output subdirectory
- `modality_mapping_path`: staged or upstream modality mapping file
- `trained_autoencoder_path`: existing autoencoder checkpoint path
- `existing_ckpt_filepath`: pretrained diffusion checkpoint path, or null for from-scratch

In the staged model config, set `diffusion_unet_train.n_epochs`, batch size,
learning rate, and cache rate for the requested run size. For preflight-only
checks, validate paths and staged config shape without launching GPU training.

## Runnable Upstream Stages

From the NV-Generate-CTMR checkout, the normal stages are:

```bash
python -m scripts.diff_model_create_training_data \
  -e OUT/configs/environment_maisi_diff_model.json \
  -c OUT/configs/config_maisi_diff_model.json \
  -t OUT/configs/config_maisi.json \
  -g 1

python -m scripts.diff_model_train \
  -e OUT/configs/environment_maisi_diff_model.json \
  -c OUT/configs/config_maisi_diff_model.json \
  -t OUT/configs/config_maisi.json \
  -g 1
```

Optional inference uses `python -m scripts.diff_model_infer` with the same
three config paths and GPU count.

## Preflight Boundary

For a preflight-scale comparison, do not train on placeholder files. Check that
the datalist is valid JSON, contains non-empty `training`, all referenced paths
exist under the data root, modality values are supported, and the staged config
files would point at output-local work directories. Write a small JSON summary
under the requested output directory.

## Scope

This is engineering workflow plumbing only. It does not validate anatomical
realism, model utility, clinical interpretation, regulatory readiness, or
production training-data approval.
