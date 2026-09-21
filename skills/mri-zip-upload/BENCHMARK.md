# BENCHMARK — mri-zip-upload

Summary of what this skill guarantees, contrasted with not having it.

## Without the skill

- An agent must locate the MR-RATE zip step (step 6), assemble the correct
  argument set, and set up `PYTHONPATH`/imports by hand.
- No environment gate: a run can fail deep inside the upstream code because the
  script path is wrong or `numpy`/`nibabel` are missing, with no structured
  signal about why.
- No standardized telemetry: timings, environment (versions/host), and I/O
  counts are not captured, so dev/test/prod monitoring and reproducibility
  checks are ad hoc.
- Easy to accidentally validate against a mock or stub rather than the real
  upstream behavior.

## With the skill

- The executed grading check runs a real-environment **preflight** (verifies the
  exact upstream script exists and required deps `numpy`/`nibabel` import with
  versions) and, when aligned, runs the **real upstream zip step** on synthetic
  PHI-free fixtures — there is no mock path.
- It asserts on **real artifacts** (produced zip/output files under `--out`) and
  on the **telemetry** block (per-phase timings, environment facts, I/O counts),
  with output conforming to `validators/output_schema.json`.
- `--preflight` gives a fast, side-effect-free alignment gate for dev/test/prod
  before a real run.
- One JSON contract on stdout plus `<out>/telemetry.json` makes runs
  monitorable and reproducible.

## Guarantees asserted

- `status == "ok"` and `mode == "real"` on a successful real run.
- `preflight.aligned == true` with all `preflight.checks` passing.
- Non-empty `outputs.produced_files` and `telemetry.io.n_output_files > 0`.
- Presence of `telemetry.wall_seconds`, `telemetry.phases`, and
  `telemetry.environment`.

## Gaps

- Upstream `accession_to_uid` anonymization is an identity pass-through, so
  study-ID de-identification is a no-op unless inputs are pre-anonymized; the
  skill does not add real de-identification.
- Fixtures are small and synthetic — they exercise the code path but are not
  clinically representative and do not benchmark throughput at real scale.
- Hugging Face upload is skipped (`--skip-upload`); network upload behavior is
  not exercised.
- Not a regulatory de-identifier. Not for clinical use.
