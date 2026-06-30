# Benchmark — report-structuring

Engineering behavior benchmark for the report-structuring skill. This is an
integration/quality signal, not a clinical or regulatory claim.

## Task

Parse English radiology reports into four sections (`clinical_information`,
`technique`, `findings`, `impression`), normalize findings to flowing sentences
and impression to em-dash (`—`) bullets, QC the structured result, and report a
deterministic parse / completeness / QC / format summary.

## Modes

| Mode | Engine | GPU | Determinism | Use |
|---|---|---|---|---|
| `mock` (default) | stdlib header-split structurer + rule-based QC | none | deterministic | CI gates, fixtures, offline verification |
| `live` | upstream `structure_reports_parallel.py` (step 04) + `qc_llm_verify.py` (step 05), vLLM | CUDA | model-dependent | real structuring + LLM-judge QC |

## With-skill vs without-skill

- **Without the skill**, an agent asked to "structure these reports" tends to
  hand-write ad-hoc section parsing or call an LLM directly, producing an
  unaudited result with no parse-success metric, inconsistent bullet formatting,
  and no QC pass.
- **With the skill**, the agent gets a single documented entrypoint, a
  deterministic parse/completeness/format check, a structure QC pass-rate, and an
  evidence pack the paired verifier can audit.

## Results

### Mock smoke (synthetic fixture, 5 reports)

_Populated from `runs/report_structuring_pack` (`python -m eval_engine.run`)._

| Metric | Value |
|---|---|
| n_reports | 5 |
| parse.parse_success_rate | 1.0 |
| sections.completeness_rate | 1.0 |
| qc.pass_rate | 1.0 |
| format.n_format_violations | 0 |
| eval_engine overall | passed |
| paired verifier verdict | planned |

### Live run (real MR-RATE English reports)

_Populated from a `--mode live` run on a real-data slice (see the run record in
`runs/`). Captures n_reports, parse success rate, completeness, QC pass-rate,
format violations, model id, GPU, and wall time. Not committed (real-data outputs
stay in gitignored `runs/`)._

## Gaps

- Mock structuring requires the four canonical headers; it is not a general
  free-text section parser.
- The format check is a surface check; clinical content fidelity is covered by
  the LLM-judge QC pass (step 05) and the paired verifier, not by the mock.
- Live throughput/quality depends on the model and GPU; numbers are recorded per
  run, not pinned here.
