# Benchmark — report-translation

Engineering behavior benchmark for the report-translation skill. This is an
integration/quality signal, not a clinical or regulatory claim.

## Task

Translate anonymized Turkish radiology reports to English (preserving `[token_N]`
anonymization placeholders), then QC the result — translation quality, residual
non-English (Turkish leftover), and token preservation — and report a summary.

## Modes

| Mode | Engine | GPU | Determinism | Use |
|---|---|---|---|---|
| `mock` (default) | stdlib phrase-dictionary translator + rule-based QC/lang-detect | none | deterministic | CI gates, fixtures, offline verification |
| `live` | upstream `translate_reports_parallel.py` + `detect_turkish_parallel.py` + `quality_check_parallel.py` (vLLM) | CUDA | model-dependent | real translation + QC |

## With-skill vs without-skill

- **Without the skill**, an agent asked to "translate these reports" tends to
  call an LLM directly with an ad-hoc prompt, producing an unaudited result with
  no QC pass rate, no residual-Turkish check, and no guarantee the anonymization
  tokens survived.
- **With the skill**, the agent gets a single documented entrypoint, a
  translation QC pass rate, a residual non-English rate, a deterministic
  token-preservation check, and an evidence pack the paired verifier can audit.

## Results

### Mock smoke (synthetic fixture, 6 reports)

_Populated from `runs/report_translation_pack` (`python -m eval_engine.run`)._

| Metric | Value |
|---|---|
| n_reports | 6 |
| qc.pass_rate | 1.0 |
| language.non_english_rate | 0.0 |
| token_preservation.n_reports_with_tokens | 4 |
| token_preservation.n_reports_token_dropped | 0 |
| token_preservation.preservation_rate | 1.0 |
| eval_engine overall | passed |
| paired verifier verdict | pass |

### Live run (real MR-RATE Turkish reports)

_Populated from a `--mode live` run on a real-data slice (see the run record in
`runs/`). Captures n_reports, qc.pass_rate, non_english_rate, token-drop count,
model id, GPU, and wall time. Not committed (real-data outputs stay in
gitignored `runs/`)._

## Gaps

- Mock translation covers a small synthetic vocabulary; it is not a general
  Turkish->English translator.
- Live throughput/quality depends on the model and GPU; numbers are recorded per
  run, not pinned here.
