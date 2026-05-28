---
name: radiology-note-summary-quality-v1
description: Used to verify radiology-note-summarizer evidence packs for source-pack success, fixture fact echo, model and prompt identity, and absence of forbidden clinical overreach phrases.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - medtech
    - radiology
    - llm
    - verifier
---

# Radiology Note Summary Quality Verifier

## Purpose
- Used for deterministic second-pass review of a `radiology-note-summarizer` evidence pack.
- Checks source-pack success, fixture fact echo, model identity, prompt hashes, and forbidden clinical/regulatory overreach phrases.
- Manifest I/O: inputs are `radiology_note_summarizer_evidence_pack`; outputs are `radiology_note_summary_quality_report`.

## Instructions
- Use this verifier only on an evidence pack directory produced by `skills/radiology-note-summarizer`.
- Run it through `eval_engine/run.py` when producing verifier evidence.
- The verifier entrypoint is `scripts/grade.py`; do not replace it with prompt-only review.
- Treat a pass as engineering evidence only, not as validation of clinical correctness.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/grade.py` | Primary verifier entrypoint declared by `skill_manifest.yaml`. | `EVIDENCE_PACK_DIR` |

## Prerequisites
- Runtime requirements: Python packages listed in `runtime.side_effects.pip_packages`.
- The input directory must contain `manifest.json`, `validation_summary.json`, and `output.json` from a `radiology-note-summarizer` evidence pack.
- The recorded fixture path and committed prompt files must be available in the checkout for full prompt/fact binding.

## Limitations
- Does not validate clinical correctness, report completeness, differential diagnosis, or medical actionability.
- Forbidden-phrase checks are regex-based and can miss paraphrases.
- Mock-mode packs prove wrapper and gate wiring; they do not prove live hosted-model behavior.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| `target_skill_matches` fails | The fixture is not a radiology-note-summarizer evidence pack. | Re-run the verifier against the source skill pack directory. |
| `fixture_loaded` fails | The source pack references a fixture that is unavailable in this checkout. | Regenerate the source pack with a committed synthetic fixture. |
| `prompt_template_hash_matches` fails | The pack was produced by different prompt text. | Regenerate the source pack or review it as legacy evidence. |
| `forbidden_phrases_absent` fails | Output contains prohibited clinical, treatment, or regulatory language. | Fix the source skill prompt/runtime guard and regenerate evidence. |

## Example

```bash
MOCK_LLM=1 python eval_engine/run.py skills/radiology-note-summarizer \
  --fixture skills/radiology-note-summarizer/fixtures/case_001_input.json \
  --out runs/radiology_note_summarizer_demo

python eval_engine/run.py verifiers/radiology_note_summary_quality_v1 \
  --fixture runs/radiology_note_summarizer_demo \
  --out runs/radiology_note_summary_quality

python verifiers/radiology_note_summary_quality_v1/scripts/grade.py \
  runs/radiology_note_summarizer_demo
```
