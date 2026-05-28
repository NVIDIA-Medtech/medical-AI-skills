---
name: holohub-imaging-segmentation-quality-v1
description: Audits HoloHub imaging_ai_segmentator evidence packs for DICOM SEG and NIfTI presence, non-empty segmentation signals, and optional NIfTI foreground checks. Engineering verification only.
license: Apache-2.0
---

# holohub_imaging_segmentation_quality_v1

## Purpose
- Audits HoloHub `imaging_ai_segmentator` evidence packs for DICOM SEG/NIfTI artifact presence and non-empty segmentation signals.
- Use this after the HoloHub imaging segmentation skill has produced an evidence pack. Engineering verification only.
- Manifest I/O: inputs are `imaging_evidence_pack`; outputs are `segmentation_quality_report`.

## Instructions
- Run `scripts/grade.py` on the HoloHub imaging evidence-pack directory.
- If a host agent exposes `run_script`, use `run_script("scripts/grade.py", args=["RUNS/HOLOHUB_IMAGING_PACK"])`.
- Prefer the eval-engine command when you need a verifier evidence pack; use the direct Python command for quick local inspection.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/grade.py` | Primary verifier entrypoint declared by `skill_manifest.yaml`. | `EVIDENCE_PACK_DIR` |

## Prerequisites
- The target pack must contain source-skill `output.json`, `validation_summary.json`, and `manifest.json`.
- Optional NIfTI foreground checks require the segmentation NIfTI to still exist under the pack or recorded artifact path.

## Limitations
- This verifier checks non-empty segmentation artifacts, not clinical segmentation accuracy.
- DICOM SEG/NIfTI inventory is an engineering signal; pair with dataset or anatomy verifiers for deeper quality claims.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| Empty segmentation | Source HoloHub run produced a DICOM SEG/NIfTI with no foreground signal. | Use a multi-slice CT abdomen series and rerun the source skill. |
| Missing NIfTI | Artifact inventory did not preserve the generated segmentation file. | Keep generated files with the evidence pack before auditing. |
| Source pack failed | The source skill did not pass its own gates. | Resolve source-pack failures before using verifier output as evidence. |

Paired verifier for `skills/holohub-imaging-ai-segmentator`.

```bash
python eval_engine/run.py verifiers/holohub_imaging_segmentation_quality_v1 \
  --fixture runs/holohub_imaging_demo \
  --out runs/holohub_imaging_demo_quality
```

Reads the target pack's `output.json`, `validation_summary.json`, and `manifest.json`.
Requires the source skill pack to have passed, HoloHub `exit_code == 0`, non-trivial
DICOM SEG and NIfTI inventory, and `seg_signals.seg_pixel_max_value > 0` (the
canonical empty-segmentation detector for TotalSegmentator runs).

When the segmentation NIfTI is present on disk under the pack, optionally loads it
with nibabel to confirm foreground voxels.
