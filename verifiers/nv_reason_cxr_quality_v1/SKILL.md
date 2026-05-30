---
name: nv-reason-cxr-quality-v1
description: Used to verify nv-reason-cxr evidence packs for source-pack success, fixture/image hash binding, NV-Reason-CXR runtime identity, response shape, scope disclosure, and conservative forbidden overreach phrases.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - MedTech
    - radiology
    - chest-xray
    - verifier
---

# NV Reason CXR Quality Verifier

## Purpose
- Used for deterministic second-pass review of an `nv-reason-cxr` evidence pack.
- Checks source-pack success, fixture case/prompt binding, image readability and hash, model/runtime identity, output response shape, limitation disclosure, and forbidden overreach phrases.
- Manifest I/O: inputs are `nv_reason_cxr_evidence_pack`; outputs are `nv_reason_cxr_quality_report`.

## Instructions
- Use this verifier only on an evidence pack directory produced by `skills/nv-reason-cxr`.
- Run it through `eval_engine/run.py` when producing verifier evidence.
- The verifier entrypoint is `scripts/grade.py`; do not replace it with prompt-only review.
- Treat a pass as engineering evidence only, not as validation of clinical correctness or model quality.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/grade.py` | Primary verifier entrypoint declared by `skill_manifest.yaml`. | `EVIDENCE_PACK_DIR` |

## Prerequisites
- Runtime requirements: Python standard library only.
- The input directory must contain `manifest.json`, `validation_summary.json`, and `output.json` from an `nv-reason-cxr` evidence pack.
- The recorded fixture path and image artifact must be available for full fixture/image binding.

## Limitations
- Does not validate chest X-ray interpretation, model correctness, report completeness, or medical actionability.
- Forbidden-phrase checks are regex-based and can miss paraphrases.
- Mock-mode packs prove wrapper and gate wiring; they do not prove live NV-Reason-CXR-3B model behavior.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| `target_skill_matches` fails | The fixture is not an `nv-reason-cxr` evidence pack. | Re-run the verifier against the source skill pack directory. |
| `fixture_loaded` fails | The source pack references a fixture that is unavailable in this checkout. | Regenerate the source pack with a committed synthetic fixture. |
| `image_sha256_matches` fails | The recorded image artifact changed or is unavailable. | Regenerate the source pack or inspect artifact provenance. |
| `forbidden_phrases_absent` fails | Output contains treatment, regulatory, patient-directed, or absolute-certainty language. | Fix the source skill prompt/runtime guard and regenerate evidence. |

## Example

```bash
MOCK_NV_REASON_CXR=1 python eval_engine/run.py skills/nv-reason-cxr \
  --fixture skills/nv-reason-cxr/fixtures/synthetic_cxr_input.json \
  --out runs/nv_reason_cxr_demo

python eval_engine/run.py verifiers/nv_reason_cxr_quality_v1 \
  --fixture runs/nv_reason_cxr_demo \
  --out runs/nv_reason_cxr_quality

python verifiers/nv_reason_cxr_quality_v1/scripts/grade.py \
  runs/nv_reason_cxr_demo
```
