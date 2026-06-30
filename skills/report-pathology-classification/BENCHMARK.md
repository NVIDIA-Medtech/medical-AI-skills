# Benchmark — report-pathology-classification

Engineering behavior benchmark for the report-pathology-classification skill.
This is an integration/quality signal, not a clinical or regulatory claim.

## Task

Classify brain/spine MRI report findings against a fixed pathology list (one
`0/1` label per pathology per report; emit a `labels.csv`) and report a
deterministic label-coverage / label-validity summary.

## Modes

| Mode | Engine | GPU | Determinism | Use |
|---|---|---|---|---|
| `mock` (default) | stdlib keyword-presence classifier | none | deterministic | CI gates, fixtures, offline verification |
| `live` | upstream `classify_pathologies_parallel.py` (vLLM, multi-step CoT/JSON/verify) | CUDA | model-dependent | real classification |

## With-skill vs without-skill

- **Without the skill**, an agent asked to "label these reports for pathologies"
  tends to hand-write an ad-hoc prompt or regex, producing an unaudited result
  with no coverage metric and an inconsistent or incomplete label set.
- **With the skill**, the agent gets a single documented entrypoint, a fixed
  pathology vocabulary, a complete-vector coverage check, a label-validity
  metric, and an evidence pack the paired verifier can audit.

## Results

### Mock smoke (synthetic fixture, 6 reports, 10 pathologies)

_Populated from `runs/report_pathology_classification_pack` (`python -m eval_engine.run`)._

| Metric | Value |
|---|---|
| n_reports | 6 |
| pathologies.n_labels | 10 |
| labels.label_coverage_rate | 1.0 |
| labels.n_present_total | 10 |
| validation.json_parse_success_rate | 1.0 |
| validation.n_invalid_labels | 0 |
| eval_engine overall | passed |
| paired verifier verdict | planned |

### Live run (real MR-RATE brain/spine reports)

_Populated from a `--mode live` run on a real-data slice (see the run record in
`runs/`). Captures n_reports, n_labels, coverage, JSON-parse success, model id,
GPU, and wall time. Not committed (real-data outputs stay in gitignored `runs/`)._

## Gaps

- Mock classification covers a small synthetic vocabulary and does not parse
  negation or context; it is not a general medical classifier.
- Live throughput/quality depends on the model and GPU; numbers are recorded per
  run, not pinned here.
