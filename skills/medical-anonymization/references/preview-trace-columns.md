<!--
SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: Apache-2.0
-->

# Preview trace columns (`preview.parquet`)

In preview mode the wrapper writes `<output-dir>/preview.parquet`, which is
`result.trace_dataframe` from NeMo Anonymizer: a superset of the user-facing
`result.dataframe` that keeps the internal underscore-prefixed columns
explaining every entity decision. Load it with `pandas.read_parquet`. This is
the trace schema the skill's summary and residual-leak audit are derived from.

Columns in a Replace/Redact preview (22 total), with the ones the wrapper reads:

| Column | Used by wrapper | Meaning |
|---|:--:|---|
| `study_uid` | yes | Passthrough id column (`--id-column`). |
| `report_w_PHI` | | Original input text column (`--text-column`). |
| `report_w_PHI_replaced` | yes | Anonymized text (the wrapper's `report` output). |
| `report_w_PHI_with_spans` | | Input text annotated with detected entity spans. |
| `_anonymizer_record_id` | | Internal per-record id. |
| `_raw_detected_entities` | yes | Stage 1: raw GLiNER-PII detections (JSON string). |
| `_seed_entities` / `_seed_entities_json` | | Seed detections fed to validation. |
| `_seed_validation_candidates` / `_validation_candidates` | | Candidates presented to the LLM validator. |
| `_seed_tagged_text` / `_initial_tagged_text` / `_merged_tagged_text` | | Intermediate tagged-text renderings. |
| `_validated_entities` | yes | Stage 2: LLM keep/drop decisions per seed entity. |
| `_validated_seed_entities` | | Validated seed entities. |
| `_augmented_entities` | yes | Stage 3: LLM-augmented entities beyond the seed set. |
| `_merged_entities` / `_detected_entities` | | Merged detection set. |
| `final_entities` | yes | Stage 4: final merged entity set actually replaced. |
| `_entities_by_value` | | Entities grouped by value. |
| `_replacement_map` | yes | Stage 5: `{replacements: [{label, original, synthetic}]}` used for the residual-leak audit. |

The wrapper maps these to five reported `pipeline_stages`
(`raw_gliner_detection`, `seed_validation`, `entity_augmentation`,
`final_entity_merge`, `replacement`) and computes `residual_phi_leak` from
`_replacement_map` vs `report_w_PHI_replaced`. Cell payloads are Python
objects in memory and survive a parquet round-trip as dicts/arrays, except
`_raw_detected_entities`, which is stored as a JSON string.
