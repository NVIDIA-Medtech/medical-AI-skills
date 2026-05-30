---
name: ct-segmentation-quality-v1
description: Audits nv_segment_ct evidence packs for label-map readability, anatomy plausibility (organ volume bounds, fragmentation, bilateral symmetry, liver-larger-than-spleen), and optional per-class Dice/IoU against a referenced ground-truth label map. Engineering verification only.
license: Apache-2.0
---

# ct_segmentation_quality_v1

## Purpose
- Audits `nv_segment_ct` evidence packs for label-map readability, anatomy plausibility, requested-label containment, and optional Dice/IoU against a recorded ground-truth label map.
- Use this after the source segmentation skill has produced an evidence pack. Engineering verification only.
- Manifest I/O: inputs are `nv_segment_ct_evidence_pack`; outputs are `ct_segmentation_quality_report`.

## Instructions
- Run `scripts/grade.py` on the evidence-pack directory that should be audited.
- If a host agent exposes `run_script`, use `run_script("scripts/grade.py", args=["RUNS/PACK_DIR"])`.
- Prefer the eval-engine command when you need a verifier evidence pack; use the direct Python command for quick local inspection.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/grade.py` | Primary verifier entrypoint declared by `skill_manifest.yaml`. | `EVIDENCE_PACK_DIR` |

## Prerequisites
- The target pack must contain `manifest.json`, `validation_summary.json`, and `output.json`.
- The label-map path recorded in `output.path` must resolve from the pack directory or current repo root.

## Limitations
- Single-pack verifier only; dataset-level aggregation belongs in `benchmarks/`.
- Anatomy bounds are engineering floors and may fail pediatric, post-resection, or pathological cases intentionally.
- Not for clinical interpretation.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| Missing pack files | The fixture path is not an evidence-pack directory. | Point the verifier at the completed source-skill run directory. |
| Label map unreadable | `output.path` is missing or stale. | Preserve source-skill artifacts with the evidence pack before auditing. |
| Plausibility failure | Output violates an engineering floor. | Keep the failed verifier output and inspect per-tier reasons. |

Paired verifier for `skills/nv-segment-ct`.

```bash
python eval_engine/run.py verifiers/ct_segmentation_quality_v1 \
  --fixture runs/spleen_clean \
  --out runs/spleen_clean_quality
```

The verifier reads the target pack's `manifest.json`, `validation_summary.json`,
and `output.json`. It loads the label-map NIfTI referenced at `output.path`,
recomputes per-class voxel counts and converts to volumes using the recorded
spacing. It then runs three tiers:

- **artifact_inventory** — label-map file exists, integer dtype, shape and
  affine match the recorded input geometry.
- **anatomy_plausibility** — per-class volume bounds (e.g. spleen 50-500 mL),
  largest connected component dominates, fragmentation cap, bilateral organ
  symmetry, and `liver_volume > spleen_volume` when both are present.
- **gt_metrics** — runs only if `input.ground_truth_path` is recorded in the
  evidence pack and the file is readable. Computes per-class Dice and IoU
  against the reference and checks per-class Dice floors.

Per-class anatomy bounds live in `validators/anatomy_bounds.json`. Bounds are
population-typical adult ranges; pediatric or post-resection cases will fail
intentionally for v0.1.

This is a single-pack verifier. Dataset-level aggregation (mean Dice across
N cases) belongs in `benchmarks/`.

Not for clinical interpretation.
