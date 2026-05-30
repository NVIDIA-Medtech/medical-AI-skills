---
name: mr-synthesis-quality-v1
description: Used to verify nv-generate-mr and nv-generate-mr-brain evidence packs by re-reading generated MR NIfTI images and checking geometry, finite nonconstant nonnegative intensities, runtime identity, and scope disclosure.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - MedTech
    - MR
    - generation
    - verifier
---

# MR Synthesis Quality Verifier

## Purpose
- Used for deterministic second-pass review of `nv-generate-mr` and `nv-generate-mr-brain` evidence packs.
- Re-reads generated image artifacts and checks source-pack success, upstream entrypoint identity, model inventory, modality/version identity, shape and spacing consistency, finite nonconstant nonnegative voxel values, aggregate-flag honesty, runtime identity, and scope disclosure.
- Manifest I/O: inputs are `nv_generate_mr_evidence_pack`; outputs are `mr_synthesis_quality_report`.

## Instructions
- Use this verifier only on evidence packs produced by `skills/nv-generate-mr` or `skills/nv-generate-mr-brain`.
- Run it through `eval_engine/run.py` when producing verifier evidence.
- The verifier entrypoint is `scripts/grade.py`; do not replace it with prompt-only review.
- Treat a pass as an engineering floor only, not as validation of anatomical realism, diagnostic utility, or training-data suitability.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/grade.py` | Primary verifier entrypoint declared by `skill_manifest.yaml`. | `EVIDENCE_PACK_DIR` |

## Prerequisites
- Runtime requirements: Python packages listed in `runtime.side_effects.pip_packages`.
- The input directory must contain `manifest.json`, `validation_summary.json`, and `output.json` from a supported MR generation evidence pack.
- Referenced generated image artifacts must be available for NIfTI header/data checks.

## Limitations
- Does not validate anatomical realism, radiologic image quality, diagnosis, regulatory claims, or production training-data suitability.
- Basic numeric checks catch empty/corrupt outputs, not subtle model failures.
- Does not re-run the upstream diffusion model.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| `target_skill_matches` fails | The fixture is not an `nv-generate-mr` or `nv-generate-mr-brain` evidence pack. | Re-run the verifier against a supported source pack. |
| `image_artifacts_readable` fails | A generated NIfTI path is missing, moved, or unreadable. | Regenerate or restore the source evidence pack artifacts. |
| `image_values_nonconstant` fails | The generated image is constant or nearly empty. | Inspect upstream logs and regenerate evidence after fixing runtime/input issues. |
| `aggregate_flags_match_recomputed` fails | Source output flags disagree with verifier recomputation. | Fix the wrapper summary logic and regenerate the source pack. |

## Example

```bash
python eval_engine/run.py verifiers/mr_synthesis_quality_v1 \
  --fixture runs/nv_generate_mr_demo \
  --out runs/mr_synthesis_quality

python verifiers/mr_synthesis_quality_v1/scripts/grade.py \
  runs/nv_generate_mr_demo
```
