---
name: report-translation-quality-v1
description: Used to verify Turkish-to-English radiology-report translation evidence packs for source gate success, LLM-judged QC pass rate, residual non-English rate, and anonymization-token preservation. Not a clinical accuracy claim.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - MedTech
    - reports
    - translation
    - verifier
---

# Report Translation Quality Verifier

## Purpose
- Used for deterministic second-pass review of a radiology-report translation evidence pack (e.g. MR-RATE `reports_preprocessing` stage 02 + 03 QC).
- Checks that the source pack passed, that the LLM-judged translation QC pass rate is within threshold, that the residual non-English (Turkish leftover) rate is within threshold, and that anonymization tokens are preserved verbatim through translation.
- Treats dropped anonymization tokens and a very low QC pass rate or high residual non-English rate as hard failures; treats marginal bands and unparseable verdicts as warnings.
- Manifest I/O: inputs are `report_translation_evidence_pack`; outputs are `report_translation_quality_report`.

## Instructions
- Use this verifier only on an evidence pack directory built from a report-translation + QC run.
- Run it through `eval_engine/run.py` when producing verifier evidence.
- The verifier entrypoint is `scripts/grade.py`; do not reimplement its checks in an agent prompt.
- Do not treat a pass or warning as a clinical accuracy guarantee.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/grade.py` | Primary verifier entrypoint declared by `skill_manifest.yaml`. | `EVIDENCE_PACK_DIR` |

## Prerequisites
- No network, GPU, Docker, or extra Python package dependencies are required.
- The input directory must contain `manifest.json`, `validation_summary.json`, and `output.json` from a report-translation evidence pack.
- The QC pass rate (`output.json.qc`) and language-detection rate (`output.json.language`) are computed upstream by the pipeline's LLM stages; this verifier grades the recorded values.

## Limitations
- Translation QC and language detection are LLM-judged upstream and can include false positives.
- A passing verdict is an engineering signal, not a clinical accuracy claim.
- Token preservation is a verbatim string check and does not assess semantic fidelity beyond the recorded QC verdict.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| `target_skill_matches` fails | The fixture is not a report-translation evidence pack. | Re-run the verifier against the translation pack directory. |
| `translation_qc_pass_rate` fails | Too many translations failed LLM QC. | Retranslate the flagged reports and rebuild the pack. |
| `residual_non_english_within_threshold` fails | Translations still contain Turkish. | Retranslate the flagged reports (pipeline stage 03 retranslation). |
| `anonymization_tokens_preserved` fails | Translation dropped or altered a token. | Retranslate preserving `[token_N]` placeholders verbatim. |

## Example

```bash
python verifiers/report_translation_quality_v1/scripts/grade.py \
  verifiers/report_translation_quality_v1/fixtures/pass_pack

python eval_engine/run.py verifiers/report_translation_quality_v1 \
  --fixture verifiers/report_translation_quality_v1/fixtures/pass_pack \
  --out runs/report_translation_quality
```
