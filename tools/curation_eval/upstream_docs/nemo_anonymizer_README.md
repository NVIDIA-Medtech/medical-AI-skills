<!--
SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: Apache-2.0

Vendored upstream documentation for the with-vs-without-skill experiment
(without-skill arm). Source: https://github.com/NVIDIA-NeMo/Anonymizer
README.md and skills/anonymizer/SKILL.md. This is the upstream-docs baseline a
reasonable user would have; it does not reference the report-anonymization skill.
-->

# NeMo Anonymizer

**Detect and replace sensitive entities in text using LLM-powered workflows.**

## What can you do with Anonymizer?

- **Detect entities** using GLiNER-PII and LLM-based augmentation and validation
- **Replace with 4 strategies** — LLM-generated substitute, redact, annotate, or hash (deterministic, local)
- **Preview results** before full runs with `display_record()` visualization

## Quick Start

### 1. Install

```bash
pip install nemo-anonymizer
```

Or install from source:

```bash
git clone https://github.com/NVIDIA-NeMo/Anonymizer.git
cd Anonymizer
make install
```

### 2. Set up model providers

By default, Anonymizer uses models hosted on build.nvidia.com — GLiNER-PII for
entity detection and a text LLM for augmentation/validation. Set your key:

```bash
export NVIDIA_API_KEY="your-nvidia-api-key"
```

### 3. Anonymize text

#### CLI

```bash
DATA_URL="https://raw.githubusercontent.com/NVIDIA-NeMo/Anonymizer/refs/heads/main/docs/data/NVIDIA_synthetic_biographies.csv"

# Preview on a small sample
anonymizer preview --source $DATA_URL --text-column biography --replace redact --num_records 3

# Full run with output file
anonymizer run --source $DATA_URL --text-column biography --replace redact --output result.csv

# Validate config without running
anonymizer validate --source $DATA_URL --text-column biography --replace hash
```

Run `anonymizer --help` or `anonymizer <subcommand> --help` for all options. The
CLI can also be invoked via `python -m anonymizer` or (from a source checkout)
`uv run anonymizer`.

Key `run` / `preview` options:

- `--source PATH` — input CSV/JSONL/Parquet (or URL).
- `--text-column NAME` — the column to anonymize. **Required to match your data**
  (there is no report-specific default; e.g. use `--text-column report_w_PHI` for
  a CSV whose text column is `report_w_PHI`).
- `--replace {substitute,redact,annotate,hash}` — the replacement strategy.
- `--output PATH` — where to write the anonymized table (for `run`).
- `--num_records N` — number of rows for `preview`.
- `--no-emit-telemetry` — disable anonymous run telemetry.

#### Python API

```python
from anonymizer import Anonymizer, AnonymizerConfig, AnonymizerInput, Redact

anonymizer = Anonymizer()  # bundled build.nvidia.com providers; needs NVIDIA_API_KEY
config = AnonymizerConfig(replace=Redact())

result = anonymizer.run(
    config=config,
    data=AnonymizerInput(source="reports.csv", text_column="report_w_PHI"),
)
result.dataframe            # user-facing columns (includes <text-column>_replaced)
result.trace_dataframe      # full pipeline trace (superset)
result.dataframe.to_csv("result.csv", index=False)
```

## Replacement Strategies

| Strategy | Output for "Alice" (first_name) | Configurable |
|---|---|---|
| Substitute | Maya | instructions |
| Redact | [REDACTED_FIRST_NAME] | format_template |
| Annotate | \<Alice, first_name> | format_template |
| Hash | \<HASH_FIRST_NAME_3bc51062973c> | format_template, algorithm, digest_length |

```python
from anonymizer import Redact, Annotate, Hash, Substitute

AnonymizerConfig(replace=Substitute())                       # LLM contextual replacements
AnonymizerConfig(replace=Redact(format_template="****"))     # constant redaction
AnonymizerConfig(replace=Annotate(format_template="<{text}-|-{label}>"))
AnonymizerConfig(replace=Hash(algorithm="sha256", digest_length=8))
```

## Detection

- `Detect(entity_labels=[...])` switches GLiNER to **strict mode**: only the
  listed labels are detected. `Detect.gliner_threshold` (default 0.3) trades
  recall for precision. GLiNER labels are natural-language concept names
  (e.g. `patient`, `doctor`, `date`, `accession_number`, `institution`).
- Always set `AnonymizerInput.data_summary` — a one-line description of the data
  domain. It is the single cheapest quality lever.

## Requirements

- Python 3.11+
- NVIDIA API key for the default model providers (GLiNER-PII + text LLM), or
  custom model endpoints.

## Telemetry and Privacy

NeMo Anonymizer collects anonymous run-level telemetry (strategy, models, model
hosts, record counts, run duration, failure attribution) — no record contents.
Opt out with `--no-emit-telemetry`, `AnonymizerConfig(emit_telemetry=False)`, or
`NEMO_TELEMETRY_ENABLED=false`.

## License

Apache License 2.0.
