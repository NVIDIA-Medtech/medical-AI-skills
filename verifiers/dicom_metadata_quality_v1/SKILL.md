---
name: dicom-metadata-quality-v1
description: Used to verify dicom-metadata-extract evidence packs for source gate success, header fact completeness, PHI-flag consistency, and scope disclosure. Not for de-identification.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - medtech
    - dicom
    - verifier
---

# DICOM Metadata Quality Verifier

## Purpose
- Used for deterministic second-pass review of a `dicom-metadata-extract` evidence pack.
- Checks that the source pack passed, required header facts are present, PHI tag presence is represented consistently, and the limited PHI scope is disclosed.
- Reports standard PHI tag presence as a warning, not a failure.
- Manifest I/O: inputs are `dicom_metadata_evidence_pack`; outputs are `dicom_metadata_quality_report`.

## Instructions
- Use this verifier only on an evidence pack directory produced by `skills/dicom-metadata-extract`.
- Run it through `eval_engine/run.py` when producing verifier evidence.
- The verifier entrypoint is `scripts/grade.py`; do not reimplement its checks in an agent prompt.
- Do not treat a pass or warning as de-identification proof.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/grade.py` | Primary verifier entrypoint declared by `skill_manifest.yaml`. | `EVIDENCE_PACK_DIR` |

## Prerequisites
- No network, GPU, Docker, or extra Python package dependencies are required.
- The input directory must contain `manifest.json`, `validation_summary.json`, and `output.json` from a `dicom-metadata-extract` evidence pack.

## Limitations
- PHI tag presence is advisory; this is not a de-identification audit.
- Private tags and burnt-in pixel text remain out of scope.
- The verifier audits the emitted metadata facts; it does not re-read the original DICOM file.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| `target_skill_matches` fails | The fixture is not a `dicom-metadata-extract` evidence pack. | Re-run the verifier against the source skill pack directory. |
| `source_pack_passed` fails | The source skill gates did not pass. | Inspect the source pack's `validation_summary.json` before verifier findings. |
| `phi_scope_disclosed` fails | The source output no longer discloses standard-tag, private-tag, or burnt-in pixel limits. | Restore explicit scope text in the source skill output. |

## Example

```bash
python verifiers/dicom_metadata_quality_v1/scripts/grade.py \
  examples/evidence_packs/dicom_metadata_pass

python eval_engine/run.py verifiers/dicom_metadata_quality_v1 \
  --fixture examples/evidence_packs/dicom_metadata_pass \
  --out runs/dicom_metadata_quality
```
