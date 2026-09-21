<!--
SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: Apache-2.0
-->

# report-anonymization

De-identify English radiology reports by replacing PHI entities detected by
[NeMo Anonymizer](https://github.com/NVIDIA-NeMo/Anonymizer) (GLiNER-PII
detection + LLM augmentation/validation) with bracketed role tokens
(`[PATIENT]`, `[DOCTOR]`, `[DATE]`, ...). This is **MR-RATE
`reports_preprocessing` stage 01**, packaged as an agent-callable Medical AI
Skill around the upstream `nemo-anonymizer` package.

> **Engineering / research use only.** This skill is **not** a regulatory
> de-identifier and does not guarantee removal of all PHI. It is not for
> clinical deployment, autonomous diagnosis, or patient-facing use. Review
> output before sharing data.

## What it does

- Calls the documented `Anonymizer()` Python API in Replace mode (`Redact`,
  `format_template="[{label}]"`) with a strict GLiNER label set for report PHI.
- Emits an `anonymization_summary` JSON on stdout (progress logs go to stderr)
  and writes `anonymized_reports.csv` (`study_uid,report`) plus a detailed
  `run_report.json` to the output directory. Preview mode also writes
  `preview.parquet` (the full pipeline trace).
- Reports per-stage entity counts, timings, throughput, a tiktoken input-token
  estimate, and an informational `residual_phi_leak` verbatim check.

| I/O | Detail |
|---|---|
| Input | `reports_csv` — CSV with `study_uid` + `report_w_PHI` columns |
| Output (stdout) | `anonymization_summary` JSON (validated against `validators/output_schema.json`) |
| Output (files) | `<output-dir>/anonymized_reports.csv`, `<output-dir>/run_report.json`, `<output-dir>/preview.parquet` (preview only) |

## Quick start

Run from the `medical-AI-skills` repo root. Set your key first — detection runs
on build.nvidia.com:

```bash
export NVIDIA_API_KEY="nvapi-..."

# Preview 5 rows (cheap; writes the trace parquet)
python skills/report-anonymization/scripts/anonymize_reports.py \
  skills/report-anonymization/fixtures/batch00_reports_w_PHI.csv \
  --output-dir runs/report_anonymization_preview \
  --num-records 5

# Full run on every row
python skills/report-anonymization/scripts/anonymize_reports.py \
  /path/to/reports_w_PHI.csv \
  --output-dir runs/report_anonymization_full \
  --full
```

### Test dataset

A 100-case **synthetic** dataset (generated, contains **no real PHI**) is bundled at
`data/synthetic_reports_100_w_PHI.csv` (`study_uid`, `report_w_PHI`) for end-to-end
testing and reproducing `BENCHMARK.md`:

```bash
python skills/report-anonymization/scripts/anonymize_reports.py \
  skills/report-anonymization/data/synthetic_reports_100_w_PHI.csv \
  --output-dir runs/report_anonymization_100 --full
```

### Key arguments

`REPORTS_CSV --output-dir DIR [--full] [--num-records N] [--text-column report_w_PHI] [--id-column study_uid] [--gliner-threshold 0.3] [--evaluate] [--no-emit-telemetry]`

| Environment variable | Required | Purpose |
|---|---|---|
| `NVIDIA_API_KEY` | yes | Auth for the bundled build.nvidia.com providers (GLiNER-PII + LLM). |
| `NEMO_TELEMETRY_ENABLED` | no | `false` disables NeMo's anonymous run telemetry (same as `--no-emit-telemetry`). |

## Output summary fields

`n_reports`, `records_passed` / `records_failed`, `pass_rate`, `entities`
(total + per-label counts), `residual_phi_leak` (informational verbatim
replacement-map check), `pipeline_stages` (per NeMo detection iteration),
`telemetry` (wall-clock timings, throughput, tiktoken input-token estimate),
and `artifacts` (written paths).

## Repository layout

```
report-anonymization/
├── SKILL.md                     # agent-facing skill definition
├── README.md                    # this file
├── skill_manifest.yaml          # I/O contract, runtime, sanity checks
├── requirements.txt             # nemo-anonymizer + pandas + pyarrow + tiktoken
├── scripts/
│   └── anonymize_reports.py     # entrypoint (real NeMo Anonymizer wrapper)
├── validators/
│   └── output_schema.json       # output JSON schema
├── data/
│   └── synthetic_reports_100_w_PHI.csv  # 100-case synthetic test set (no real PHI)
├── fixtures/
│   └── batch00_reports_w_PHI.csv  # small synthetic-PHI preview sample (input)
├── references/
│   ├── upstream-nemo-anonymizer.md    # upstream tool reference
│   └── preview-trace-columns.md       # preview.parquet trace schema
├── evals/
│   └── evals.json               # NV-ACES eval dataset
└── BENCHMARK.md                 # with-skill / without-skill results
```

## Verification

- Output JSON is gated by `validators/output_schema.json` and the manifest
  `validation.sanity_checks`.
- With-vs-without evidence lives in
  [`docs/anonymization-with-vs-without-experiment.md`](../../docs/anonymization-with-vs-without-experiment.md).

## Limitations

- Detection runs on remote LLMs at build.nvidia.com; requires `NVIDIA_API_KEY`
  and network access, and output is non-deterministic.
- Strict GLiNER label mode: only listed PHI types are detected.
- `residual_phi_leak` is an informational verbatim check, not a completeness
  guarantee. Not a regulatory de-identifier.

## License

Apache-2.0. See the SPDX headers in the source files.
