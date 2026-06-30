---
name: report-anonymization-quality-v1
description: Used to verify radiology-report anonymization evidence packs for source gate success, PHI leakage rate, anonymization-token format validity, and token/mapping consistency. Not for regulatory de-identification.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - MedTech
    - reports
    - anonymization
    - verifier
---

# Report Anonymization Quality Verifier

## Purpose
- Used for deterministic second-pass review of a radiology-report anonymization evidence pack (e.g. MR-RATE `reports_preprocessing` stage 01).
- Checks that the source pack passed, that the measured PHI leakage rate is within threshold, that anonymization tokens are well formed, and that tokens are consistent with the recorded `Token_Mapping`.
- Treats any confirmed PHI leak as a hard failure; treats malformed tokens and low mapping-extraction rate as warnings.
- Manifest I/O: inputs are `report_anonymization_evidence_pack`; outputs are `report_anonymization_quality_report`.

## Instructions
- Use this verifier only on an evidence pack directory built from a report-anonymization run.
- Run it through `eval_engine/run.py` when producing verifier evidence.
- The verifier entrypoint is `scripts/grade.py`; do not reimplement its checks in an agent prompt.
- Do not treat a pass or warning as regulatory de-identification proof.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/grade.py` | Primary verifier entrypoint declared by `skill_manifest.yaml`. | `EVIDENCE_PACK_DIR` |

## Prerequisites
- No network, GPU, Docker, or extra Python package dependencies are required.
- The input directory must contain `manifest.json`, `validation_summary.json`, and `output.json` from a report-anonymization evidence pack.
- The PHI leakage signal (`output.json.phi_leak`) is computed upstream (deterministic mapping check or LLM judge); this verifier grades the recorded value.

## Limitations
- PHI leakage is graded from the recorded metric; the verifier does not re-read the raw pre-anonymization reports.
- A passing verdict is an engineering signal, not a regulatory de-identification certification.
- Token/mapping consistency depends on upstream `Token_Mapping` quality.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| `target_skill_matches` fails | The fixture is not a report-anonymization evidence pack. | Re-run the verifier against the anonymization pack directory. |
| `source_pack_passed` fails | The source skill gates did not pass. | Inspect the source pack's `validation_summary.json` first. |
| `phi_leak_within_threshold` fails | A report still contains original PHI. | Re-anonymize the flagged reports and rebuild the pack. |
| `phi_leak_evaluated` warns | PHI leakage was not measured. | Rebuild the pack with the LLM PHI judge enabled. |

## Example

```bash
python verifiers/report_anonymization_quality_v1/scripts/grade.py \
  verifiers/report_anonymization_quality_v1/fixtures/pass_pack

python eval_engine/run.py verifiers/report_anonymization_quality_v1 \
  --fixture verifiers/report_anonymization_quality_v1/fixtures/pass_pack \
  --out runs/report_anonymization_quality
```
