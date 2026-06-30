# Benchmark — report-anonymization

Engineering behavior benchmark for the report-anonymization skill. This is an
integration/quality signal, not a clinical or regulatory claim.

## Task

De-identify Turkish radiology reports (replace names, dates, hospitals,
accession numbers with `[entity_N]` tokens; emit a per-report `Token_Mapping`)
and report a deterministic PHI-leak / token-quality summary.

## Modes

| Mode | Engine | GPU | Determinism | Use |
|---|---|---|---|---|
| `mock` (default) | stdlib rule-based redactor | none | deterministic | CI gates, fixtures, offline verification |
| `live` | upstream `anonymize_reports_parallel.py` (vLLM) | CUDA | model-dependent | real de-identification |

## With-skill vs without-skill

- **Without the skill**, an agent asked to "de-identify these reports" tends to
  hand-write ad-hoc regex or call an LLM directly, producing an unaudited result
  with no PHI-leak metric and an inconsistent token scheme.
- **With the skill**, the agent gets a single documented entrypoint, a
  deterministic PHI-leak mapping check, a canonical token format, and an
  evidence pack the paired verifier can audit.

## Results

### Mock smoke (synthetic fixture, 5 reports)

_Populated from `runs/report_anonymization_pack` (`python -m eval_engine.run`)._

| Metric | Value |
|---|---|
| n_reports | 5 |
| phi_leak.leak_rate | 0.0 |
| token_format.n_malformed_tokens | 0 |
| token_consistency.n_inconsistent | 0 |
| token_consistency.mapping_extraction_rate | 1.0 |
| eval_engine overall | passed |
| paired verifier verdict | pass |

### Live run (real MR-RATE Turkish reports)

_Populated from a `--mode live` run on a real-data slice (see the run record in
`runs/`). Captures n_reports, leak_rate, malformed/inconsistent counts, model id,
GPU, and wall time. Not committed (real-data outputs stay in gitignored `runs/`)._

## Gaps

- Mock redaction covers a small synthetic vocabulary; it is not a general NER.
- Live throughput/quality depends on the model and GPU; numbers are recorded per
  run, not pinned here.
