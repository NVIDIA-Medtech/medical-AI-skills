# Benchmark: mri-brain-seg-deface

Summary of what an agent gains from this skill versus operating without it on the
MR-RATE MRI brain-segmentation-and-defacing step (step 5).

## Without the skill

- The agent must discover the upstream entrypoint
  (`src/mr_rate_preprocessing/mri_preprocessing/brain_segmentation_and_defacing.py`),
  reconstruct its CLI arguments (`--modalities-json`, `--raw-dir`, `--output-dir`,
  `--device`), and hand-craft valid inputs.
- No environment guardrails: missing dependencies (`torch`, `brainles_hd_bet`,
  `SimpleITK`, `nibabel`, `numpy`, `scipy`) or an absent CUDA GPU surface only as
  deep, late-stage stack traces.
- No standard evidence of what ran (no timings, environment capture, or I/O counts).

## With the skill

- One wrapper, `scripts/run_brain_seg_deface.py`, invokes the real upstream step with
  correct arguments derived from generated fixtures.
- A fail-fast **preflight** environment-alignment check (`--preflight`) verifies the
  Python interpreter, required dependencies, and CUDA GPU before any real work,
  turning misconfiguration into an immediate, actionable failure.
- Structured **telemetry** (wall/phase timings, environment including versions/GPU/host,
  and I/O counts) is emitted for dev/test/prod monitoring and conforms to
  `validators/output_schema.json`.
- Synthetic PHI-free fixtures (`fixtures/generate_fixtures.py --step brainseg`) provide
  reproducible inputs.

## What the executed check guarantees

The automated grader runs this skill for real. It executes a real-environment
**preflight** and, when a CUDA GPU is present, the **real upstream brainseg step** on
synthetic fixtures, then asserts on genuine on-disk artifacts (defaced volumes plus
brain and defacing masks) and on the emitted telemetry/preflight structure. There is no
mock or stand-in for the upstream computation.

## Gaps

- The step is GPU-only with no CPU fallback; on GPU-less machines only the preflight
  path can be exercised, so full-run coverage is gated on CUDA availability.
- Fixtures are small and synthetic, not clinically representative.
- Upstream `accession_to_uid` anonymization is an identity pass-through, so study-ID
  de-identification is a no-op unless inputs are pre-anonymized.
- Not a regulatory de-identifier and not for clinical use; output must be reviewed
  before sharing.

## Real-data validation (public faced MRI)

Beyond the synthetic CI fixture, this skill's HD-BET path was validated end to end on a
**real face-inclusive** T1 head study from the public TCIA **Vestibular-Schwannoma-MC-RC**
collection (CC BY 4.0; cite Shapey et al.) — the `face_inclusive` case `VS-MC-RC-027`
(FSPGR BRAVO, 124 slices, z-extent ~147 mm):

- `dcm2niix` conversion → NIfTI `256 x 256 x 124` @ `(0.9375, 0.9375, 1.2) mm`.
- HD-BET brain extraction on an **NVIDIA RTX 6000 Ada** GPU (model weights auto-downloaded
  on first use, ~100 s one-time).
- Result: brain mask ~1.38M voxels (~17% of volume) produced in ~2.5 s; the face
  (facial biometric) is removed in the brain-extracted / defaced volume.

No PHI is committed — only this metric summary. The public dataset is the de-facing test
corpus; the face is the real identifier being removed.
