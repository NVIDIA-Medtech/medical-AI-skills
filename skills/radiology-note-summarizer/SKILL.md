---
name: radiology-note-summarizer
description: Used for hosted-LLM summarization smoke tests from synthetic radiology notes and DICOM metadata. Not for clinical reporting.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - medtech
    - radiology
    - summarization
---

# radiology_note_summarizer

## Purpose
- Used for hosted-LLM summarization smoke tests from synthetic radiology notes and DICOM metadata. Not for clinical reporting.
- Use the wrapper exactly as documented; do not replace the upstream entrypoint with a handwritten implementation.
- Manifest I/O: inputs are `case`; outputs are `summary`.

## Instructions
- Read `skill_manifest.yaml` before changing arguments, side effects, or validation gates.
- Run `scripts/summarize.py` through the documented command below; keep outputs under a caller-provided run directory.
- If a host agent exposes `run_script`, use `run_script("scripts/summarize.py", args=[...])`; otherwise run the Bash/Python command shown below.
- Check the emitted JSON and paired verifier guidance before treating the run as evidence.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/summarize.py` | Primary entrypoint declared by skill_manifest.yaml. | `PATH_TO_FIXTURE.json` plus `MOCK_LLM=1` or `NV_INFER_TOKEN` |

## Prerequisites
- No special runtime service is required beyond the packages declared in `skill_manifest.yaml`.
- Side effects: `MOCK_LLM=1` is offline; live summarization sends the prompt to `https://inference-api.nvidia.com` using `NV_INFER_TOKEN`.
- Run commands from the repository root unless an existing section below says otherwise.

## Limitations
- Output is engineering evidence only. Not a clinical report. The `not_for` list above applies in full.
- Generative prose may hallucinate. The factual_echo gate verifies that declared input fields (StudyInstanceUID, Modality, BodyPartExamined) appear verbatim or as substrings in the output; the prose itself is not semantically verified.
- Replay is deterministic only when temperature=0.0 + seed=42 AND the NIM-hosted model has not been server-side updated. The `model_identity` gate catches the first; server-side model-version drift is not yet detected.
- With `MOCK_LLM=1` the skill skips the network call and returns a canned response computed deterministically from the input fixture. Use this for dry-runs and CI; it is not a substitute for a real NIM call.
- Not for clinical interpretation, autonomous diagnosis, regulatory submission, patient-facing report generation.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| Missing dependency or import error | Runtime package drift from `skill_manifest.yaml`. | Install the packages declared in the manifest or use the documented setup command. |
| Empty or schema-invalid output | Wrong input path, unsupported modality, or upstream failure. | Re-run with a known fixture and inspect the wrapper JSON plus stderr. |
| Validation gate failure | Output violated a declared engineering invariant. | Keep the failed evidence pack and use the gate message to repair inputs or wrapper code. |

Reference hosted-LLM skill. It demonstrates how an LLM-using wrapper declares
model identity, factual echo, runtime integrity, and token/cost gates.

```bash
NV_INFER_TOKEN=... python scripts/summarize.py \
  skills/radiology-note-summarizer/fixtures/case_001_input.json
```

The fixture contains DICOM metadata plus a note. Output JSON includes
`study_instance_uid`, `findings`, `impressions`, `flags_for_followup`, and a
`runtime` block with model, endpoint, token counts, request ID, and prompt
hashes.

The skill must not add findings absent from the input note. Set `MOCK_LLM=1`
for offline verification (and `MOCK_LLM=fail_<gate>` to exercise each gate's
fault-injection variant; see `scripts/summarize.py`).

Live-call override variables are for backend probes only: `LLM_ENDPOINT`,
`LLM_MODEL`, and `LLM_TEMPERATURE` replace the manifest-declared hosted model
settings and will be caught by the model-identity gate if they drift from the
published skill contract.
