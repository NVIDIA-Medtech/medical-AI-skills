---
name: dicom-volume-quality-v1
description: Used to verify dicom-series-to-volume evidence packs by comparing JSON geometry evidence with the emitted NIfTI artifact. Not for clinical validation.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - medtech
    - dicom
    - nifti
    - verifier
---

# DICOM Volume Quality Verifier

## Purpose
- Used for deterministic second-pass review of a `dicom-series-to-volume` evidence pack.
- Checks that the source pack passed and that the declared NIfTI artifact matches reported shape, spacing, affine orientation, and voxel range evidence.
- Manifest I/O: inputs are `dicom_series_to_volume_evidence_pack`; outputs are `dicom_volume_quality_report`.

## Instructions
- Use this verifier only on an evidence pack directory produced by `skills/dicom-series-to-volume`.
- Run it through `eval_engine/run.py` when producing verifier evidence.
- The verifier entrypoint is `scripts/grade.py`; do not reimplement its checks in an agent prompt.
- Do not treat a pass as clinical validation of conversion quality.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/grade.py` | Primary verifier entrypoint declared by `skill_manifest.yaml`. | `EVIDENCE_PACK_DIR` |

## Prerequisites
- Runtime requirements: Python packages listed in `runtime.side_effects.pip_packages`.
- The input directory must contain `manifest.json`, `validation_summary.json`, `output.json`, and the NIfTI file declared by `output.path`.

## Limitations
- Audits the emitted NIfTI and JSON evidence; it does not re-read DICOM inputs.
- Does not prove clinical correctness of orientation or HU scaling.
- Does not repair non-canonical orientation, spacing, or voxel metadata.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| `target_skill_matches` fails | The fixture is not a `dicom-series-to-volume` evidence pack. | Re-run the verifier against the source skill pack directory. |
| `output_artifact_exists` fails | The source pack declares a missing or moved NIfTI path. | Keep the NIfTI inside the pack or use a repo-relative path that resolves from the repository root. |
| `shape_matches_nifti` fails | The JSON output no longer matches the saved NIfTI artifact. | Inspect the source pack and regenerate the evidence after fixing the converter. |

## Example

```bash
python verifiers/dicom_volume_quality_v1/scripts/grade.py \
  examples/evidence_packs/dicom_series_to_volume_pass

python eval_engine/run.py verifiers/dicom_volume_quality_v1 \
  --fixture examples/evidence_packs/dicom_series_to_volume_pass \
  --out runs/dicom_volume_quality
```
