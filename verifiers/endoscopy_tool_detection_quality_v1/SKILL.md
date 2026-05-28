---
name: endoscopy-tool-detection-quality-v1
description: Audits HoloHub endoscopy tool-tracking evidence packs for decoded detection presence, nonzero tool count, bbox sanity, frame coverage, and count distribution. Engineering verification only.
license: Apache-2.0
---

# endoscopy_tool_detection_quality_v1

## Purpose
- Audits HoloHub endoscopy tool-tracking evidence packs for decoded detection presence, nonzero tool counts, bounding-box sanity, frame coverage, and count distribution.
- Use this after the endoscopy tool-tracking skill has run and recorded artifacts. Engineering verification only.
- Manifest I/O: inputs are `endoscopy_evidence_pack`; outputs are `detection_quality_report`.

## Instructions
- Run `scripts/grade.py` on the endoscopy evidence-pack directory.
- If a host agent exposes `run_script`, use `run_script("scripts/grade.py", args=["RUNS/ENDOSCOPY_PACK"])`.
- Prefer the eval-engine command when you need a verifier evidence pack; use the direct Python command for quick local inspection.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/grade.py` | Primary verifier entrypoint declared by `skill_manifest.yaml`. | `EVIDENCE_PACK_DIR` |

## Prerequisites
- The target pack must include the source wrapper `output.json` plus any decoded detection artifact referenced by that output.
- Raw recording inventory alone is not enough for a passing detection-quality audit.

## Limitations
- Audits decoded detection evidence only; it does not decode raw GXF recordings itself.
- Not for clinical detection-quality claims or intra-operative guidance.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| No decoded detections | Source run recorded only raw artifacts. | Export detections with the source skill helper or preserve the sidecar detection file. |
| Bounding-box failure | Coordinates are missing, inverted, or out of frame. | Inspect decoded detection rows and frame metadata. |
| Frame coverage failure | Detections cover too little of the recorded frame range. | Check recorder/export configuration and rerun the source skill. |

Paired verifier for `skills/holohub-endoscopy-tool-tracking`.

```bash
python eval_engine/run.py verifiers/endoscopy_tool_detection_quality_v1 \
  --fixture runs/endoscopy_demo \
  --out runs/endoscopy_demo_detection_quality
```

The verifier reads the target pack's `manifest.json`,
`validation_summary.json`, and `output.json`. It requires recording artifacts
and a decoded detection artifact (`.json`, `.jsonl`, or `.csv`) with at least
one detection. It then checks frame coverage, mean detections per frame, and
in-frame non-degenerate bounding boxes when frame dimensions are available.

Raw `.gxf_entities` inventory alone is not enough; missing decoded detections
fail the verifier instead of passing as domain evidence.
