---
name: report-pathology-quality-v1
description: Used to verify radiology-report pathology-classification evidence packs for source gate success, label coverage, JSON-extraction success rate, and absence of out-of-taxonomy labels. Not a clinical diagnostic claim.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - MedTech
    - reports
    - pathology
    - verifier
---

# Report Pathology Classification Quality Verifier

## Purpose
- Used for deterministic second-pass review of a pathology-classification evidence pack (MR-RATE `reports_preprocessing` stage 06).
- Checks that the source pack passed, that every report received a complete 0/1 label vector (coverage), that the JSON-extraction success rate is within threshold, and that no labels fall outside the declared pathology taxonomy.
- Treats incomplete coverage, low JSON-parse rate, and out-of-taxonomy labels as hard failures; treats an unmeasured JSON-extraction signal or an empty pathology set as warnings.
- Manifest I/O: inputs are `report_pathology_evidence_pack`; outputs are `report_pathology_quality_report`.

## Instructions
- Use this verifier only on an evidence pack directory built from a pathology-classification run.
- Run it through `eval_engine/run.py` when producing verifier evidence.
- The verifier entrypoint is `scripts/grade.py`; do not reimplement its checks in an agent prompt.
- Do not treat a pass or warning as a clinical diagnostic guarantee.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/grade.py` | Primary verifier entrypoint declared by `skill_manifest.yaml`. | `EVIDENCE_PACK_DIR` |

## Prerequisites
- No network, GPU, Docker, or extra Python package dependencies are required.
- The input directory must contain `manifest.json`, `validation_summary.json`, and `output.json` from a pathology-classification evidence pack.

## Limitations
- Per-label accuracy is not re-derived; the verifier grades recorded coverage, JSON-parse, and taxonomy-validity metrics.
- A passing verdict is an engineering signal, not a clinical diagnostic claim.
- The pathology taxonomy and its prevalence are defined upstream (`data/pathologies.json`).

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| `target_skill_matches` fails | The fixture is not a pathology-classification evidence pack. | Re-run the verifier against the classification pack directory. |
| `labels_fully_covered` fails | Some reports have no label vector. | Re-run classification so every study_uid is labeled, then merge. |
| `json_parse_success_within_threshold` fails | Too many JSON extractions failed. | Re-run with the CoT-only fallback / extra retries. |
| `no_out_of_taxonomy_labels` fails | A label outside `pathologies.json` was emitted. | Constrain the label set to the declared taxonomy and re-run. |

## Example

```bash
python verifiers/report_pathology_quality_v1/scripts/grade.py \
  verifiers/report_pathology_quality_v1/fixtures/pass_pack

python eval_engine/run.py verifiers/report_pathology_quality_v1 \
  --fixture verifiers/report_pathology_quality_v1/fixtures/pass_pack \
  --out runs/report_pathology_quality
```
