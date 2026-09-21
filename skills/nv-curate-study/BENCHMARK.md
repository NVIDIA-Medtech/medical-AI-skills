# Benchmark — nv-curate-study

Engineering behavior benchmark for single-study MR-RATE curation.
Not a clinical or regulatory claim.

## Task

Curate one MRI + associated report by composing `nv-curate-mri` and `nv-curate`,
then join on `study_uid` with publish blocked until human QC.

## Modes

| Mode | MRI | Reports | GPU |
|---|---|---|---|
| `mock` (default) | stubbed | `nv-curate --mode mock` | none |
| `live` | real `nv-curate-mri` | `nv-curate --mode live` | CUDA |

## With-skill vs without-skill

- **Without:** agent must manually sequence MRI preprocessing, report stages,
  join keys, and upload gates.
- **With:** one `study.json` + one entrypoint; batch skill reuses this unit.

## Results

_Populate from a mock run of `fixtures/study.json`._
