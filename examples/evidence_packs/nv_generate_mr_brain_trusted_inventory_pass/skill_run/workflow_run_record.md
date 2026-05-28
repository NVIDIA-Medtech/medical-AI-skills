# Workflow Run Record

- run id: 2be2250061c9
- skill: medagent.nv_generate_mr_brain v0.1.0
- started: 2026-05-26T03:37:04.948634+00:00
- finished: 2026-05-26T03:37:21.750089+00:00
- elapsed: 16.801s
- exit code: 0

## Skill
- dir: skills/nv-generate-mr-brain
- entrypoint: scripts/run_mr_brain.py

## Fixture
- path: skills/nv-generate-mr-brain/fixtures/default_mri_t1.json
- sha256: 1ac5e95ebeb304bed0534b9be30c464b98b9c482a17f7640b1884511c2fc647d
- size: 289 bytes

## Validation
- overall: passed
- schema: passed
- sanity: passed
- runtime: within_envelope
- cost: passed
- env_pin: skipped
- integrity: clean

## Output (excerpt)
```json
{
  "skill": "nv_generate_mr_brain",
  "model": "NVIDIA-Medtech/NV-Generate-CTMR (rflow-mr-brain)",
  "model_repo": "https://github.com/NVIDIA-Medtech/NV-Generate-CTMR",
  "model_weights_repo": "https://huggingface.co/nvidia/NV-Generate-MR-Brain",
  "license": "Wrapper Apache-2.0; NV-Generate-MR-Brain weights use NVIDIA Open Model License.",
  "input": {
    "model_config_override_path": "<repo>/skills/nv-generate-mr-brain/fixtures/default_mri_t1.json",
    "model_config_override": {
      "dim": [
        256,
        256,
        256
      ],
      "spacing": [
        1.0,
        1.0,
        1.0
      ],
      "num_inference_steps": 30,
      "cfg_guidance_scale": 10
    },
    "modality_name": "mri_t1",
    "modality_code": 9,
    "dim_requested": [
      256,
      256,
      256
    ],
    "spacing_requested": [
      1.0,
      1.0,
      1.0
    ],
    "num_inference_steps_requested": 30,
    "cfg_guidance_scale_requested": 10,
    "random_seed": 1234,
    "version": "rflow-mr-brain"
  },
  "output": {
    "directory": "<repo>/runs/nv_generate_mr_brain_trusted_hash_current/skill_run/samples",
    "samples": [
      {
        "image_path": "<repo>/runs/nv_generate_mr_brain_trusted_hash_current/skill_run/samples/mr_brain_mri_t1_seed1234_size256x256x256_spacing1.00x1.00x1.00_20260526043719_rank0_modality9.nii.gz",
        "image_bytes": 9337901,
        "image_sha256": "ed62
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.