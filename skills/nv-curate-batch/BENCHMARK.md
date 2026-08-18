# Benchmark — nv-curate-batch

Engineering behavior benchmark for batch MR-RATE curation via `nv-curate-study`.
Not a clinical or regulatory claim.

## Task

Curate a tranche by invoking `nv-curate-study` once per study, with optional
smoke cohort and reject-list aggregation.

## With-skill vs without-skill

- **Without:** agent loops studies ad hoc, no shared reject list or smoke gate.
- **With:** one `batch.json`; composition is explicit and auditable per study under
  `<out>/studies/<study_uid>/`.

## Results

_Populate from a mock run of `fixtures/batch.json`._
