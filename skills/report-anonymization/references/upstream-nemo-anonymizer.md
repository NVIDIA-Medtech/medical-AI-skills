<!--
SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: Apache-2.0
-->

# Upstream reference: NeMo Anonymizer

One-hop reference for the upstream tool this skill wraps. Source of truth:

- Repo: <https://github.com/NVIDIA-NeMo/Anonymizer>
- Upstream Claude Code skill: <https://github.com/NVIDIA-NeMo/Anonymizer/blob/main/skills/anonymizer/SKILL.md>
- PyPI: `nemo-anonymizer` (this skill pins `>=0.2.1,<0.3`; validated with `0.2.1`)

This wrapper does not reimplement the pipeline — it calls the documented
`Anonymizer()` Python API. Read this file to understand what the wrapper is
delegating to; run `scripts/anonymize_reports.py` (not a hand-written call) for
normal use.

## What NeMo Anonymizer does

Detect-then-transform pipeline over a text column:

1. **Detect** entities with GLiNER-PII (zero-shot) plus LLM augmentation and
   validation.
2. **Replace** each detected entity in place with one of four strategies, or
   **Rewrite** the whole text.

Default providers are hosted on build.nvidia.com and require `NVIDIA_API_KEY`.
The bundled model pool (`src/anonymizer/config/default_model_configs/models.yaml`)
uses `nvidia/gliner-pii` for detection and `openai/gpt-oss-120b` for
augment/validate.

## Replace strategies (upstream)

| Strategy | Output for "Alice" (first_name) | Configurable |
|---|---|---|
| Substitute | Maya | instructions |
| Redact | [REDACTED_FIRST_NAME] | format_template |
| Annotate | \<Alice, first_name> | format_template |
| Hash | \<HASH_FIRST_NAME_3bc51062973c> | format_template, algorithm, digest_length |

**This skill uses `Redact` with `format_template="[{label}]"`** so each detected
entity becomes a bracketed uppercase role token (`[PATIENT]`, `[DOCTOR]`,
`[DATE]`, ...). Substitute / Annotate / Hash / Rewrite are upstream options that
this stage-01 wrapper intentionally does not expose.

## Minimal upstream Python API (for reference only)

```python
from anonymizer import Anonymizer, AnonymizerConfig, AnonymizerInput, Detect, Redact

anonymizer = Anonymizer()  # bundled build.nvidia.com providers; needs NVIDIA_API_KEY
config = AnonymizerConfig(
    detect=Detect(entity_labels=[...], gliner_threshold=0.3),
    replace=Redact(format_template="[{label}]"),
)
result = anonymizer.run(config=config, data=AnonymizerInput(source="reports.csv", text_column="report_w_PHI"))
result.dataframe            # user-facing columns
result.trace_dataframe      # full pipeline trace (superset)
result.failed_records       # dropped rows (infra issues: rate limits, auth)
```

## Detection knobs used by this skill

- `Detect.entity_labels`: passing an explicit list switches GLiNER to **strict
  mode** — only listed labels are detected. Every PHI type to scrub must be
  listed or it leaks. This skill lists `patient, patient_mrn, doctor,
  date_of_birth, age, sex, date, accession_number, institution`.
- `Detect.gliner_threshold` (default 0.3): lower for recall, raise for precision.
- `AnonymizerInput.data_summary`: a one-line domain description; the single
  cheapest quality lever. Improves both detection and (in Rewrite mode) rewriting.

## Telemetry and privacy (upstream)

NeMo Anonymizer emits one anonymous run event per `run()`/`preview()` with
technical metadata only (strategy, models, model hosts, record counts, duration,
failure attribution) — no record contents. Opt out with
`AnonymizerConfig(emit_telemetry=False)`, `--no-emit-telemetry`, or
`NEMO_TELEMETRY_ENABLED=false`. Use of build.nvidia.com is subject to NVIDIA
Build's own terms; it is for evaluation/testing, not production PHI.

## Not privacy guarantees

Anonymizer is best-effort. Outputs may need human review. This skill is not a
regulatory de-identifier (see `skill_manifest.yaml` `phi_scope_disclaimer`).
