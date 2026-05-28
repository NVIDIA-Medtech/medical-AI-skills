---
name: totalsegmentator
description: Used for running TotalSegmentator on CT or MR NIfTI volumes and recording multilabel-mask evidence. Not for clinical use.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - medtech
    - segmentation
    - totalsegmentator
---

# TotalSegmentator

## Purpose
- Used for running TotalSegmentator on CT or MR NIfTI volumes and recording multilabel-mask evidence. Not for clinical use.
- Use the wrapper exactly as documented; do not replace the upstream entrypoint with a handwritten implementation.
- Manifest I/O: inputs are `ct_or_mr_volume`; outputs are `label_map` and `result_json`.

## Instructions
- Read `skill_manifest.yaml` before changing arguments, side effects, or validation gates.
- Run `scripts/run_totalsegmentator.py` through the documented command below; keep outputs under a caller-provided run directory.
- If a host agent exposes `run_script`, use `run_script("scripts/run_totalsegmentator.py", args=[...])`; otherwise run the Bash/Python command shown below.
- Check the emitted JSON and paired verifier guidance before treating the run as evidence.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/run_totalsegmentator.py` | Primary entrypoint declared by skill_manifest.yaml. | `PATH_TO_CT.nii.gz [--output-dir OUT_DIR] [--task total] [--roi-subset IDS] [--fast]` |

## Prerequisites
- Runtime requirements: GPU/CUDA when declared by the manifest; Python packages listed in `runtime.side_effects.pip_packages`.
- Side effects: may cache TotalSegmentator assets under `~/.totalsegmentator/` and may download from `https://zenodo.org` or `https://github.com` on first use.
- Run commands from the repository root unless an existing section below says otherwise.

## Limitations
- Thin wrapper. Inference, preprocessing, postprocessing, and weight download are delegated entirely to `totalsegmentator.python_api`. Do not modify the installed package.
- The wrapper always passes `ml=True` so the output is a single multilabel NIfTI (one file containing all class IDs). The upstream default (folder of per-class binary masks) is not exposed by this wrapper.
- Anatomy bounds in `verifiers/totalsegmentator_quality_v1/validators/anatomy_bounds_total.json` are population-typical adult ranges. Pediatric, surgically-resected, or pathologically-enlarged cases will fail intentionally; the verifier is an engineering floor, not a clinical assessment.
- Output may be schema-valid but semantically empty (e.g. wrong-task inference on a CT volume that doesn't contain the requested anatomy). The verifier's `any_label_present` and per-class volume bounds gates catch this.
- Not for clinical deployment, clinical interpretation, autonomous diagnosis, regulatory submission.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| Missing dependency or import error | Runtime package drift from `skill_manifest.yaml`. | Install the packages declared in the manifest or use the documented setup command. |
| Empty or schema-invalid output | Wrong input path, unsupported modality, or upstream failure. | Re-run with a known fixture and inspect the wrapper JSON plus stderr. |
| Validation gate failure | Output violated a declared engineering invariant. | Keep the failed evidence pack and use the gate message to repair inputs or wrapper code. |

Wraps the upstream [`totalsegmentator`](https://github.com/wasserth/TotalSegmentator)
Python API exactly as the README recommends:

```python
from totalsegmentator.python_api import totalsegmentator
totalsegmentator(input_path, output_path, ml=True, task="total")
```

The wrapper does not reimplement inference, nnU-Net, or post-processing.

## License

The TotalSegmentator **code** is Apache-2.0. The **model weights** are not.
Most CT/MR task weights ship under "free for non-commercial use"; a few
high-resolution and brain/face tasks require a free academic license or a
paid commercial license. The wrapper records the per-task weight license
under `output.task_license` so downstream tooling can gate on it. Users are
responsible for compliance.

The skill_manifest's `license_restrictions.weights_per_task` block
enumerates which tasks need an academic license; see
`skills/totalsegmentator/skill_manifest.yaml`.

## Preconditions

Two one-time installs:

```bash
# 1. The package (pulls in PyTorch + nnU-Net):
pip install TotalSegmentator

# 2. Pre-download weights for the tasks you plan to use (optional —
#    TotalSegmentator auto-downloads on first run to ~/.totalsegmentator/):
totalseg_download_weights -t total
```

Weights land in `~/.totalsegmentator/nnunet/results/` (gitignored by the
home dir). The CT-Spleen example fixture is shared with the
`nv_segment_ct` skill and is fetched on demand:

```bash
python skills/nv-segment-ct/fixtures/fetch_spleen_fixture.py
```

The local fixture protocol is documented in `fixtures/README.md`; this skill
does not commit NIfTI volumes directly.

Runtime needs an NVIDIA GPU with CUDA for usable throughput (CT volume:
~30 s/case on H100, ~20 min/case on CPU). CPU fallback works for tiny
fixtures.

## Usage

From Medical AI Skills repo root:

```bash
pip install TotalSegmentator && \
python skills/totalsegmentator/scripts/run_totalsegmentator.py PATH_TO_CT.nii.gz \
  --task total \
  --roi-subset "spleen,kidney_right,kidney_left,liver" \
  --output-dir totalseg_outputs
```

Flags:

- `--task` — TotalSegmentator task name (default `total`; see upstream
  README for the full list: `total`, `total_mr`, `body`, `lung_vessels`,
  `cerebral_bleed`, `head_glands_cavities`, …). Pass-through; the skill
  does not validate against the upstream task list, so an unknown name
  errors out via upstream.
- `--roi-subset "spleen,kidney_right,kidney_left,liver"` — optional
  comma/space-separated TotalSegmentator class names or class IDs. When
  provided, only those classes are computed and recorded under
  `output.label_prompts_requested` for the verifier's subset check.
  Default: all classes for the selected task.
- `--device auto|cuda|cpu` — default `auto`. Translates to
  TotalSegmentator's `device="gpu"|"cpu"` argument.
- `--fast` — use TotalSegmentator's 3 mm fast mode (lower resolution, ~5×
  faster, slightly lower Dice). Default off.
- `--ground-truth PATH` — record a reference label map under
  `input.ground_truth_path`. The wrapper does not compute Dice; that is
  the paired verifier's job.

The `pip install TotalSegmentator` step in the usage command is load-bearing in
a fresh Python environment; do not replace it with only `nibabel` or `typer`,
because the wrapper needs the upstream `totalsegmentator.python_api` and class
map before inference.

The evidence output records the upstream `totalsegmentator` version,
task name, weight license tier, input geometry, output multilabel mask
path, observed label IDs, unexpected labels (those outside the task's
class map or outside `--roi-subset`), per-class voxel counts, per-class
physical volumes computed from the output mask header spacing, runtime,
and fixed code-derived artifact checks (mask shape, affine match, label
set, foreground count).

Anatomy plausibility (per-class volume bounds tuned to TotalSegmentator's
label IDs, fragmentation caps, bilateral symmetry, liver larger than
spleen) and optional per-class Dice/IoU against the recorded ground truth
are checked by `verifiers/totalsegmentator_quality_v1` (paired verifier).

## Common Total Task Class IDs

For the upstream `total` CT task, use these canonical class names or IDs:

| Anatomy | Class name | ID |
|---|---|---:|
| Spleen | `spleen` | 1 |
| Right kidney | `kidney_right` | 2 |
| Left kidney | `kidney_left` | 3 |
| Liver | `liver` | 5 |

Prefer class names in agent-generated commands when possible:

```bash
python skills/totalsegmentator/scripts/run_totalsegmentator.py PATH_TO_CT.nii.gz \
  --task total \
  --roi-subset "spleen,kidney_right,kidney_left,liver" \
  --output-dir runs/totalseg_case
```

The equivalent numeric form is `--roi-subset "1,2,3,5"`. Do not use VISTA3D
or NV-Segment-CT label IDs for this skill; TotalSegmentator uses its own
label map.

Not for clinical interpretation, production deployment, or any
diagnostic use.
