# Benchmark: mri-pacs-metadata-filter

Summary of what an agent achieves **with** this skill versus **without** it when
asked to clean a raw PACS DICOM-metadata CSV (MR-RATE MRI step 2).

## Without the skill

- The agent must locate the upstream MR-RATE PACS filtering script, guess its CLI
  arguments (`--input-csv` / `--output-csv`), and set `PYTHONPATH` correctly.
- No environment check: missing `pandas` or a wrong MR-RATE root surfaces only as
  an opaque mid-run traceback.
- No standardized output: timings, environment provenance, and I/O counts are not
  captured, so dev/test/prod runs are not comparably monitorable.
- Higher risk of silently running against the wrong checkout or fixtures.

## With the skill

- A single wrapper, `scripts/run_pacs_metadata_filter.py`, invokes the **real**
  upstream PACS step (no mock, no stub) with the correct arguments and PYTHONPATH.
- A fail-fast **preflight** verifies execution-environment alignment (the exact
  upstream script exists; `pandas` imports) and is exposed standalone via
  `--preflight` to gate a run.
- Every run emits one JSON object on stdout plus `<out>/telemetry.json` with a
  structured `telemetry` block: per-phase timings (preflight/upstream), environment
  facts (Python and package versions, host, timestamp), the exact command, the
  upstream return code, and I/O counts.
- Deterministic, PHI-free fixtures (`generate_fixtures.py --step pacs`) produce a
  CSV with 2 valid series, 1 exact duplicate, and 1 missing-age row, exercising
  column enforcement, missing-identifier dropping, and series de-duplication.

## What the executed check guarantees

The automated grader runs the skill for real. It:

1. Runs a **real-environment preflight** and asserts alignment (upstream script
   present, `pandas` importable).
2. Runs the **real upstream PACS step** on the synthetic fixtures.
3. Asserts on the **real artifacts** — `<out>/filtered.csv` exists and reflects
   the expected filtering (duplicate removed, missing-critical-identifier row
   dropped) — and on the **telemetry** (status `ok`, non-empty timings,
   environment facts, and I/O counts).

## Known gaps

- Upstream `accession_to_uid` anonymization is an identity pass-through, so
  study-ID de-identification is a no-op unless inputs are pre-anonymized; this is
  not a regulatory de-identifier.
- Fixtures are small and synthetic, not clinically representative; the benchmark
  validates mechanics and contract, not clinical accuracy.
- Not for clinical use.
