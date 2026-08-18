# BENCHMARK: nv-curate-mri

Short summary of what the skill guarantees when executed, compared to running the
MR-RATE MRI pipeline without it.

## Without the skill

- The operator wires the seven MR-RATE stages together by hand (DICOM to NIfTI,
  PACS metadata filtering, series classification, modality filtering,
  HD-BET/Quickshear defacing, zip, metadata), authoring a batch config and
  invoking `run/run_mri_preprocessing.py` and `run/run_mri_upload.py` directly.
- No standardized environment check: missing dependencies, an absent `dcm2niix`,
  or no visible CUDA GPU are discovered only after a partial run fails midway.
- No uniform machine-readable result: timings, environment facts, and I/O counts
  are scattered across ad-hoc logs, making dev/test/prod monitoring inconsistent.

## With the skill

- One entrypoint, `scripts/run_mri_pipeline.py`, orchestrates the whole pipeline
  from a single batch config.
- **Real-environment preflight** runs first (also available standalone via
  `--preflight`): it asserts the upstream runners exist, required deps import
  (with versions), `dcm2niix` is on `PATH`, and a usable CUDA GPU is visible.
  Misalignment fails fast with a non-zero exit and a named failing check before
  any pipeline work begins.
- **Real upstream execution, no mock**: the wrapper invokes the genuine
  `run_mri_preprocessing.py` then `run_mri_upload.py` runners via subprocess.
- **Structured result + telemetry**: exactly one JSON object on stdout (validated
  against `validators/output_schema.json`) plus `<out>/telemetry.json`, carrying
  per-phase timings, environment facts (versions, GPU, host, timestamp), I/O
  counts (defaced images, zips, metadata CSVs, total files), and the config path.

## What the executed check verifies

The automated grader runs the skill for real on synthetic, PHI-free fixtures
produced by `fixtures/generate_fixtures.py --step orchestrator` (a single T1
study). It confirms the wrapper:

1. runs the real-environment preflight alignment check first;
2. executes the real upstream MR-RATE orchestrator step (no stub/mock);
3. produces real on-disk artifacts under `--out`; and
4. emits a telemetry block (timings, environment, I/O) conforming to the output
   schema.

## Gaps

- The defacing/brain-segmentation stage is GPU-only; on a host without a usable
  CUDA GPU the preflight fails and the full real run cannot proceed (preflight
  still returns a well-formed result).
- Fixtures are small and synthetic; they exercise the pipeline plumbing, not
  clinical accuracy or scale.
- Upstream `accession_to_uid` anonymization is an identity pass-through, so
  study-ID de-identification is a no-op unless inputs are pre-anonymized. This is
  not a regulatory de-identifier and is not for clinical use.
