---
name: totalsegmentator-skeleton-topology-v1
description: Audits totalsegmentator evidence packs for skeleton topology — vertebrae form a contiguous z-ordered chain (C1→sacrum), vertebral body size grows from cervical to thoracic to lumbar, and ribs form 12 bilateral pairs with similar volumes. Catches fragmented vertebrae and mislabeled ribs. Engineering verification only.
license: Apache-2.0
---

# totalsegmentator_skeleton_topology_v1

## Purpose
- Audits TotalSegmentator skeleton labels for vertebra chain order, vertebral body size progression, and rib-pair symmetry.
- Use this after `skills/totalsegmentator` has produced an evidence pack for the `total` task with skeleton labels present. Engineering verification only.
- Manifest I/O: inputs are `totalsegmentator_evidence_pack`; outputs are `totalsegmentator_skeleton_topology_report`.

## Instructions
- Run `scripts/grade.py` on the TotalSegmentator evidence-pack directory.
- If a host agent exposes `run_script`, use `run_script("scripts/grade.py", args=["RUNS/TOTALSEG_PACK"])`.
- Prefer the eval-engine command when you need a verifier evidence pack; use the direct Python command for quick local inspection.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/grade.py` | Primary verifier entrypoint declared by `skill_manifest.yaml`. | `EVIDENCE_PACK_DIR` |

## Prerequisites
- The target pack must preserve the predicted multilabel mask path recorded in `output.path`.
- Skeleton topology checks use TotalSegmentator `total` task canonical vertebra and rib label IDs.

## Limitations
- Operates on mask geometry only; it does not inspect CT HU values or ground-truth Dice.
- Useful for skeleton-label consistency, not for general organ segmentation quality.
- Not for clinical interpretation.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| Mask unreadable | `output.path` no longer resolves. | Preserve the predicted multilabel mask with the source pack. |
| Vertebra order failure | Vertebra labels are out of z-order or fragmented. | Inspect per-label centroid output and source segmentation. |
| Rib symmetry failure | Left/right rib labels are missing or asymmetric. | Pair this output with structural and HU verifiers before trusting the pack. |

Paired verifier for `skills/totalsegmentator`.

```bash
python eval_engine/run.py verifiers/totalsegmentator_skeleton_topology_v1 \
  --fixture runs/totalseg_pack
```

The verifier reads `output.json`, loads the predicted multilabel mask, and
runs three skeleton-specific tiers:

- **vertebra_chain** — for every vertebra present (sacrum, S1, L5..L1, T12..T1,
  C7..C1, label IDs 25–50), compute the z-centroid. Walk the canonical
  cranial-to-caudal order and assert the z-centroids are monotonic (either
  consistently increasing or consistently decreasing along the chain). A
  "jump out of order" indicates a mis-labeled vertebra or a fragmentation.
- **vertebra_body_size_monotonic** — median voxel count of lumbar bodies
  (L1–L5) must be ≥ thoracic (T1–T12) ≥ cervical (C1–C7), within a 25 %
  tolerance. Lumbar bodies are anatomically larger than thoracic, which are
  larger than cervical.
- **rib_pair_symmetry** — for N=1..12, `rib_left_N` (label 91+N) and
  `rib_right_N` (label 103+N) should be either both present or both absent,
  and their volumes should differ by ≤ 40 % when both present. Catches
  ribs assigned the wrong index (e.g. an L7 mislabeled as L8) or
  asymmetric coverage.

This verifier doesn't need a CT volume — it operates purely on the mask
geometry. Use it together with `totalsegmentator_quality_v1` (anatomy
plausibility, GT Dice) and `totalsegmentator_hu_consistency_v1` (per-organ
HU range) for full coverage on the `total` task.

Vertebrae and rib IDs are TotalSegmentator's `total` task canonical IDs.
Not for clinical interpretation.
