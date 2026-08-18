# BENCHMARK: mri-dcm2niix

Summary of what an agent achieves with vs. without this skill for the MR-RATE
MRI-preprocessing `dcm2niix` step (DICOM folder -> gzip-compressed NIfTI).

## Without the skill

- The agent must locate the upstream `dcm2nii.py` entrypoint, discover its CLI
  contract (`--input-csv`, `--output-dir`, `--max-workers`), and wire
  `PYTHONPATH` to the MR-RATE `src` tree by hand.
- No environment gating: missing deps (`pandas`, `pydicom`) or a missing
  `dcm2niix` binary surface only as opaque mid-run failures.
- No standardized result: timings, environment facts, and I/O counts are not
  captured, so runs are not comparable or monitorable across dev/test/prod.
- Input creation (DICOM folders + `dicom_folder_paths.csv`) is ad hoc.

## With the skill

- **Real preflight**: `--preflight` runs a real execution-environment alignment
  check (upstream script exists, `pandas`/`pydicom` import with versions,
  `dcm2niix` on `PATH`) and exits non-zero if misaligned — before any
  conversion runs.
- **Real upstream execution**: the wrapper invokes the genuine MR-RATE
  `dcm2niix` step via subprocess on synthetic PHI-free fixtures (no mock path).
- **Asserts on real artifacts + telemetry**: emits one JSON object (validated
  against `validators/output_schema.json`) and `out/telemetry.json` with
  `status`, produced NIfTI files, per-phase timings, environment
  (versions/host/timestamp), and I/O counts. The automated grader executes the
  skill for real and asserts on these real artifacts and telemetry.

## What the executed check guarantees

1. A real-environment preflight passes (or fails fast with named checks).
2. The real upstream `dcm2niix` step runs on generated fixtures and produces
   `.nii.gz` output under the out dir.
3. A schema-valid JSON result plus a structured telemetry block are emitted.

## Gaps

- Fixtures are small and synthetic, so conversion correctness is validated
  structurally (artifacts + telemetry), not against clinical ground truth.
- Upstream study-ID anonymization is an identity pass-through; the skill does
  not perform regulatory de-identification.
- GPU is not exercised (this step needs none), so GPU-alignment guarantees do
  not apply here.
- Not for clinical use.
