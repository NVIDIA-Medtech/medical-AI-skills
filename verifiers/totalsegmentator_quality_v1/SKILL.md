---
name: totalsegmentator-quality-v1
description: Audits totalsegmentator evidence packs for label-map readability, anatomy plausibility (organ volume bounds, fragmentation, bilateral symmetry, liver-larger-than-spleen using TotalSegmentator's class IDs), and optional per-class Dice/IoU against a referenced ground-truth label map. Engineering verification only.
license: Apache-2.0
---

# totalsegmentator_quality_v1

## Purpose
- Audits TotalSegmentator evidence packs for multilabel mask readability, anatomy plausibility, ROI-subset containment, and optional Dice/IoU against a recorded ground-truth label map.
- Use this after `skills/totalsegmentator` has produced an evidence pack. Engineering verification only.
- Manifest I/O: inputs are `totalsegmentator_evidence_pack`; outputs are `totalsegmentator_quality_report`.

## Instructions
- Run `scripts/grade.py` on the TotalSegmentator evidence-pack directory.
- If a host agent exposes `run_script`, use `run_script("scripts/grade.py", args=["RUNS/TOTALSEG_PACK"])`.
- Prefer the eval-engine command when you need a verifier evidence pack; use the direct Python command for quick local inspection.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/grade.py` | Primary verifier entrypoint declared by `skill_manifest.yaml`. | `EVIDENCE_PACK_DIR` |

## Prerequisites
- The target pack must contain `manifest.json`, `validation_summary.json`, and `output.json`.
- The predicted multilabel NIfTI path recorded in `output.path` must still resolve.

## Limitations
- Single-pack verifier only; dataset-level aggregation belongs in `benchmarks/`.
- Anatomy bounds are scoped mainly to the `total` task and are engineering floors, not clinical quality claims.
- Not for clinical interpretation.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| Missing mask | The generated multilabel NIfTI is not preserved with the pack. | Keep source-skill artifacts before auditing. |
| Extra labels | The output contains labels outside the recorded `--roi-subset`. | Re-run the source skill with the intended class subset. |
| Plausibility failure | Class volumes or topology violate engineering bounds. | Inspect per-tier verifier output and source command arguments. |

Paired verifier for `skills/totalsegmentator`.

```bash
python eval_engine/run.py verifiers/totalsegmentator_quality_v1 \
  --fixture runs/totalseg_spleen \
  --out runs/totalseg_spleen_quality
```

The verifier reads the target pack's `manifest.json`, `validation_summary.json`,
and `output.json`. It loads the multilabel NIfTI referenced at `output.path`,
recomputes per-class voxel counts and converts to volumes using the recorded
spacing. It then runs four tiers:

- **artifact_inventory** — label-map file exists, integer dtype, shape and
  affine match the recorded input geometry.
- **anatomy_plausibility** — per-class volume bounds (TotalSegmentator class
  IDs: 1=spleen, 2=kidney_right, 3=kidney_left, 5=liver, 7=pancreas, …),
  largest connected component dominates, fragmentation cap, bilateral organ
  symmetry, and `liver_volume > spleen_volume` when both are present.
- **label_set_subset** — when the pack records a non-empty
  `output.label_prompts_requested` (i.e. the wrapper was invoked with
  `--roi-subset`), the verifier asserts that no class outside that set
  appeared in the output. When `roi_subset` was unset, this tier returns
  `skipped` / `pass` since the full task class map is "requested".
- **gt_metrics** — runs only if `input.ground_truth_path` is recorded in the
  evidence pack and the file is readable. Computes per-class Dice and IoU
  against the reference and checks per-class Dice floors.

Per-class anatomy bounds live in
`validators/anatomy_bounds_total.json` and are scoped to the default `total`
task. Other tasks (`total_mr`, `body`, `lung_vessels`, …) currently fall
through to no per-class bounds (anatomy_plausibility still runs but only
catches structural failures like fragmentation, not volume-out-of-range).
Bounds for additional tasks are TODO.

This is a single-pack verifier. Dataset-level aggregation (mean Dice across
N cases) belongs in `benchmarks/`.

Not for clinical interpretation.
