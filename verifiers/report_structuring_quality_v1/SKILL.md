---
name: report-structuring-quality-v1
description: Used to verify radiology-report structuring evidence packs for source gate success, section-parse rate, structure-QC pass rate, and formatting-rule violations. Not a clinical accuracy claim.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - MedTech
    - reports
    - structuring
    - verifier
---

# Report Structuring Quality Verifier

## Purpose
- Used for deterministic second-pass review of a radiology-report structuring evidence pack (MR-RATE `reports_preprocessing` stage 04 structuring + stage 05 structure QC).
- Checks that the source pack passed, that the section-parse success rate is within threshold, that the structure-QC pass rate is within threshold, and that formatting rules hold (findings are not bulleted, no section-header leakage). Section completeness is advisory (empty impression can be correct).
- Treats parse failures, low QC pass rate, and formatting violations as hard failures; treats unmeasured QC and low completeness as warnings.
- Manifest I/O: inputs are `report_structuring_evidence_pack`; outputs are `report_structuring_quality_report`.

## Instructions
- Use this verifier only on an evidence pack directory built from a report-structuring run.
- Run it through `eval_engine/run.py` when producing verifier evidence.
- The verifier entrypoint is `scripts/grade.py`; do not reimplement its checks in an agent prompt.
- Do not treat a pass or warning as a clinical accuracy guarantee.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/grade.py` | Primary verifier entrypoint declared by `skill_manifest.yaml`. | `EVIDENCE_PACK_DIR` |

## Prerequisites
- No network, GPU, Docker, or extra Python package dependencies are required.
- The input directory must contain `manifest.json`, `validation_summary.json`, and `output.json` from a report-structuring evidence pack.

## Limitations
- Structure QC is graded from the recorded metric; the verifier does not re-read the raw reports or re-run the LLM judge.
- A passing verdict is an engineering signal, not a clinical accuracy claim.
- Empty-impression reports are acceptable; section completeness is warn-only.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| `target_skill_matches` fails | The fixture is not a report-structuring evidence pack. | Re-run the verifier against the structuring pack directory. |
| `parse_success_rate_within_threshold` fails | Too many reports failed to parse into 4 sections. | Re-run structuring with the no-think fallback and merge. |
| `structure_qc_pass_rate_within_threshold` fails | Too many structured reports failed QC. | Fix flagged reports (missing/hallucinated content) and re-QC. |
| `formatting_rules_clean` fails | Findings are bulleted or a section header leaked into a body. | Re-run structuring enforcing the formatting rules. |

## Example

```bash
python verifiers/report_structuring_quality_v1/scripts/grade.py \
  verifiers/report_structuring_quality_v1/fixtures/pass_pack

python eval_engine/run.py verifiers/report_structuring_quality_v1 \
  --fixture verifiers/report_structuring_quality_v1/fixtures/pass_pack \
  --out runs/report_structuring_quality
```
