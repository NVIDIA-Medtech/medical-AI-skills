---
name: totalsegmentator-hu-consistency-v1
description: Audits totalsegmentator evidence packs for HU-intensity consistency inside each organ mask. For each present label, samples voxels from the input CT volume where mask == label_id and checks the median HU against population-typical per-tissue ranges (liver 30-70, spleen 35-55, bone 200-1500, lung -1000 to -500, etc.). Catches mask-in-wrong-place failures the anatomy-plausibility tier cannot. Engineering verification only.
license: Apache-2.0
---

# totalsegmentator_hu_consistency_v1

## Purpose
- Audits TotalSegmentator evidence packs for HU-intensity consistency inside each predicted organ mask.
- Use this after `skills/totalsegmentator` has produced a pack that preserves both the input CT volume and predicted multilabel mask. Engineering verification only.
- Manifest I/O: inputs are `totalsegmentator_evidence_pack`; outputs are `totalsegmentator_hu_consistency_report`.

## Instructions
- Run `scripts/grade.py` on the TotalSegmentator evidence-pack directory.
- If a host agent exposes `run_script`, use `run_script("scripts/grade.py", args=["RUNS/TOTALSEG_PACK"])`.
- Prefer the eval-engine command when you need a verifier evidence pack; use the direct Python command for quick local inspection.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/grade.py` | Primary verifier entrypoint declared by `skill_manifest.yaml`. | `EVIDENCE_PACK_DIR` |

## Prerequisites
- The target pack must preserve the input CT path from `input.path` and mask path from `output.path`.
- HU bounds are defined in `validators/hu_bounds_total.json` for the TotalSegmentator `total` task.

## Limitations
- Operates on CT HU values; non-CT or heavily transformed inputs can fail intentionally.
- HU ranges are population-typical engineering floors, not clinical tissue validation.
- Not for clinical interpretation.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| Input or mask unreadable | Recorded paths do not resolve from the pack. | Preserve input and output NIfTI files with the source evidence pack. |
| HU consistency failure | A predicted organ mask sits on tissue with implausible HU. | Inspect per-class HU statistics and source segmentation output. |
| No checked classes | The mask lacks labels covered by the HU-bounds table. | Pair with `totalsegmentator_quality_v1` for structural checks. |

Paired verifier for `skills/totalsegmentator`.

```bash
python eval_engine/run.py verifiers/totalsegmentator_hu_consistency_v1 \
  --fixture runs/totalseg_pack
```

The verifier reads `output.json`, loads the *input CT volume* (referenced by
`input.path`) and the *predicted multilabel mask* (referenced by
`output.path`), then for each label ID present in the mask:

1. Samples the HU values at voxels where `mask == label_id`.
2. Computes median, mean, std, p10, p90.
3. Looks up the expected HU range from `validators/hu_bounds_total.json`.
4. Flags the class as failing if its median HU falls outside that range.

This catches a failure mode the anatomy_plausibility tier cannot: a mask
that is geometrically plausible (right shape, right size, right
connectivity) but placed on the wrong tissue (e.g. a "liver" mask sitting
on the colon — same approximate volume, but the intensity inside is air,
not parenchyma). Anatomy bounds say it looks like a liver; HU bounds say
it isn't one.

Tiers:

- **input_inventory** — input CT volume and mask both readable, shape and
  affine match.
- **hu_consistency** — per-class median HU within population-typical range
  for the recorded organ. Overall passes when ≥ `min_pass_fraction` of
  checked classes pass.

Per-class HU bounds live in `validators/hu_bounds_total.json` and are scoped
to the default `total` task. Vessels use a wide band so both non-contrast
and contrast-enhanced CTs pass. Pediatric and pathological cases may fail
intentionally; the verifier is an engineering floor.

Not for clinical interpretation.
