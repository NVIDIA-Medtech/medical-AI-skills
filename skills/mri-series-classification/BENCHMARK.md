# Benchmark: mri-series-classification

## Summary

This skill wraps the real MR-RATE MRI series-classification step (MRI preprocessing
step 3), which assigns each MRI series a modality label (T1w, T2w, FLAIR, SWI, MRA, ...)
using a rule hierarchy.

## Without the skill

- An operator must locate the correct upstream module
  (`src/mr_rate_preprocessing/mri_preprocessing/series_classification.py`), assemble the
  right input CSV, and invoke it by hand.
- No environment-alignment check: version, dependency, or path mismatches surface only as
  opaque runtime failures mid-run.
- No structured record of what ran: no timings, no captured environment
  (versions/GPU/host), no I/O counts, and no schema-validated result.

## With the skill

- A single wrapper (`scripts/run_series_classification.py`) runs a **fail-fast preflight**
  environment-alignment check (Python version, `pandas`/`numpy`, and MR-RATE upstream
  layout) via `--preflight` before any real work.
- It then executes the **genuine upstream series step** on PHI-free synthetic fixtures
  produced by `fixtures/generate_fixtures.py --step series` — no mocking.
- It emits a structured **telemetry block** (wall/phase timings, environment including
  versions/GPU/host, and I/O counts) and a result JSON validated against
  `validators/output_schema.json`.
- The automated check executes the skill for real: it runs the real-environment preflight
  AND the real upstream series step on synthetic fixtures, then asserts on the real
  artifacts and the emitted telemetry.

## Guarantees

- Real preflight + real upstream execution (no mock).
- Schema-conformant, monitorable output (telemetry: timings, environment, I/O).
- Reproducible on the bundled synthetic fixtures.

## Gaps

- Fixtures are small, synthetic, and PHI-free; results are not clinically representative.
- Upstream `accession_to_uid` anonymization is an identity pass-through, so ID
  de-identification is a no-op unless inputs are pre-anonymized.
- Not a regulatory de-identifier and **not for clinical use**.
