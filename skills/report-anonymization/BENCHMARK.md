<!--
SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: Apache-2.0
-->

# Benchmark — report-anonymization

Engineering behavior benchmark for the report-anonymization skill. This is an
integration/quality signal, not a clinical or regulatory claim.

## Task

De-identify English radiology reports (replace patient/doctor names, MRNs,
dates, accession numbers, and institutions with bracketed role tokens via NeMo
Anonymizer Redact) and emit a schema-valid `anonymization_summary` plus an
`anonymized_reports.csv`.

## With-skill vs without-skill

The with-vs-without protocol compares `LLM + report-anonymization/SKILL.md`
against `LLM + upstream NeMo Anonymizer docs` on the same task and the same
staged input (the MR-RATE `batch00_reports_w_PHI.csv` reports). Both arms run
the real NeMo Anonymizer pipeline for tier-5 execution; they differ only in the
documentation the agent may read.

- **Without the skill**, an agent must discover from the upstream README/skill
  how to wire `AnonymizerInput` / `Detect` (strict label mode) / `Redact`,
  which text column to use, and where to write output — and typically improvises
  an unaudited script with no machine-readable summary.
- **With the skill**, the agent gets one documented entrypoint that owns the
  strict PHI label set, output shaping (`study_uid,report`), a schema-gated JSON
  summary, per-stage entity telemetry, and the residual-leak audit.

## Results

Full run: single-shot, no-repair; 1 repeat; **100 reports** staged from the
MR-RATE `batch00_reports_w_PHI.csv`; two build.nvidia.com backends
(Nemotron-3-Super-120B, GPT-OSS-120B). Pass criterion: **any residual PHI escape
is a fail**, where escapes are counted by an **LLM-as-judge** (GPT-OSS-120B) that
re-reads each anonymized report. Produced-output (tier-5 completion) is reported
separately.

| Arm | Produced output | Residual PHI escapes (LLM judge) | Rows fully redacted | Pass (0 escapes) |
|---|:--:|--:|:--:|:--:|
| **with skill** (`report-anonymization/SKILL.md`) | 2/2 | **21** | **197/200** | 0/2 |
| without skill (upstream NeMo README) | 2/2 | 227 | 85/200 | 0/2 |

- **Redaction quality is the decisive gap (~11x).** With the skill, agents left **21** residual PHI escapes and fully redacted **197/200** rows (98.5%); reading only the upstream README they left **227** escapes and fully redacted just **85/200** rows (42.5%). The skill's strict GLiNER label set drives detection; the upstream-default path leaves pervasive residual fragments (mostly name middle initials, plus some dates/institutions).
- **Neither arm clears the strict zero-escape bar at 100-row scale** (both 0/2 pass): the with-skill misses were a handful of names/one institution GLiNER did not propose (e.g. `Mercy General Hospital`, `Raoul`). The escape counts — not the pass/fail — are the primary signal.
- **Speed:** mean tier-5 exec ~293s with-skill vs ~343s without on 100 rows (the upstream-default path does far more augmentation; gpt-oss/without ran ~362s).
- **10-row pilot with a third `unaided` arm** (plain "redact this CSV" request, no doc) is preserved in git history of the report: unaided left 47 escapes / 0 rows clean and one backend produced no output — the hardest baseline.

Full per-backend/per-arm detail, per-row judge escape counts, generated commands,
token profiling, and the five-tier grade are in the checked-in report:

- [`docs/anonymization-with-vs-without-experiment.md`](../../docs/anonymization-with-vs-without-experiment.md)

Reproduce (from the `medical-AI-skills` catalog root):

```bash
export NVIDIA_API_KEY="nvapi-..."
# with + without arms
python -m tools.curation_eval.anon_experiment \
  --backends nemotron120-remote "gptoss=https://integrate.api.nvidia.com/v1=openai/gpt-oss-120b=NVIDIA_API_KEY" \
  --judge "gptoss=https://integrate.api.nvidia.com/v1=openai/gpt-oss-120b=NVIDIA_API_KEY" \
  --repeats 1 --limit 10 --timeout 120 \
  --input <path>/batch00_reports_w_PHI.csv
# add the unaided arm, folding in a prior study, judging all arms
python -m tools.curation_eval.anon_experiment --arms unaided \
  --backends nemotron120-remote "gptoss=…=NVIDIA_API_KEY" \
  --judge "gptoss=…=NVIDIA_API_KEY" --merge runs/curation_eval/anon/<prior_study> \
  --repeats 1 --limit 10 --timeout 120 --input <path>/batch00_reports_w_PHI.csv
```

Scale up with `--limit 100` (and more `--repeats`) when the run budget allows.

## Gaps

- Detection runs on remote LLMs (build.nvidia.com); throughput and exact leak
  counts depend on the model and rate limits and are recorded per run, not
  pinned here.
- Grading measures task completion (a contract-valid anonymized artifact) and a
  deterministic residual-PHI heuristic, not clinical de-identification quality.
