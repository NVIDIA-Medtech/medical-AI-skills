# BENCHMARK: mri-modality-filter

Summary of what the skill adds over an unassisted attempt at MR-RATE MRI
preprocessing step 4 (modality filtering).

## Without the skill

- No standard entrypoint: a user must locate the upstream
  `modality_filtering.py`, assemble the correct CLI arguments (raw data dir,
  classified CSV, output JSON/CSV, process count), and set `PYTHONPATH` to the
  MR-RATE `src` tree by hand.
- No environment gating: missing dependencies (pandas, numpy, nibabel) or a
  wrong MR-RATE root surface only as opaque mid-run failures.
- No consistent, machine-readable result: no structured telemetry (timings,
  environment, I/O), so dev/test/prod monitoring must be built ad hoc.
- Easy to reach for a mock or stub instead of exercising the real code path.

## With the skill

- Single entrypoint `scripts/run_modality_filter.py` with fixed, documented
  arguments and automatic `PYTHONPATH`/PATH wiring to the MR-RATE checkout.
- Fail-fast preflight environment-alignment check (`--preflight`) that verifies
  the upstream script exists and that pandas/numpy/nibabel import, reporting a
  structured `preflight.checks` array before anything executes.
- Real execution, no mock: the genuine upstream MR-RATE modality step runs via
  subprocess and produces real artifacts (`modalities.json`, `metadata.csv`).
- Structured telemetry emitted as one JSON object on stdout and to
  `<out>/telemetry.json`: per-phase timings, environment facts (versions, host,
  timestamp), I/O counts, and the exact command.

## What the automated check verifies

The graded check runs against a real environment: it performs the preflight
environment-alignment check and then executes the real upstream modality step on
synthetic, PHI-free fixtures (generated with `generate_fixtures.py --step
modality`). It asserts on the real produced artifacts and on the telemetry block
(status, preflight alignment, timings, environment, and I/O counts) — not on any
stubbed output.

## Gaps

- Fixtures are small, synthetic, and PHI-free; they exercise the code path but
  are not clinically representative, so they do not validate real-data accuracy.
- Upstream `accession_to_uid` anonymization is an identity pass-through, so no
  de-identification is validated.
- Only the modality step (MR-RATE step 4) is covered; end-to-end pipeline
  behavior and GPU-dependent steps are out of scope for this skill.
- Not a clinical or regulatory validation. Not for clinical use.
