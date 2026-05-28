# Workflow Run Record

- run id: dc4bd8b8d8d5
- skill: medagent.nv_generate_mr v0.1.0
- started: 2026-05-26T03:36:26.371224+00:00
- finished: 2026-05-26T03:36:38.308238+00:00
- elapsed: 11.937s
- exit code: 0

## Skill
- dir: skills/nv-generate-mr
- entrypoint: scripts/run_mr.py

## Fixture
- path: skills/nv-generate-mr/fixtures/default_mri_t1.json
- sha256: ad15245d12c06339757456313e2ea6ad6c76b5c85214436d65cfe6d218dfb693
- size: 313 bytes

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
  "skill": "nv_generate_mr",
  "model": "NVIDIA-Medtech/NV-Generate-CTMR (rflow-mr)",
  "model_repo": "https://github.com/NVIDIA-Medtech/NV-Generate-CTMR",
  "model_weights_repo": "https://huggingface.co/nvidia/NV-Generate-MR",
  "license": "Wrapper Apache-2.0; NV-Generate-MR weights use NVIDIA Non-Commercial License.",
  "input": {
    "model_config_override_path": "<repo>/skills/nv-generate-mr/fixtures/default_mri_t1.json",
    "model_config_override": {
      "dim": [
        128,
        256,
        256
      ],
      "spacing": [
        1.25,
        1.0,
        1.0
      ],
      "num_inference_steps": 30,
      "cfg_guidance_scale": 15
    },
    "modality_name": "mri_t1",
    "modality_code": 9,
    "dim_requested": [
      128,
      256,
      256
    ],
    "spacing_requested": [
      1.25,
      1.0,
      1.0
    ],
    "num_inference_steps_requested": 30,
    "cfg_guidance_scale_requested": 15,
    "random_seed": 0,
    "version": "rflow-mr"
  },
  "output": {
    "directory": "<repo>/runs/nv_generate_mr_trusted_hash_current/skill_run/samples",
    "samples": [
      {
        "image_path": "<repo>/runs/nv_generate_mr_trusted_hash_current/skill_run/samples/mr_mri_t1_seed0_size128x256x256_spacing1.25x1.00x1.00_20260526043636_rank0_modality9.nii.gz",
        "image_bytes": 7005195,
        "image_sha256": "65469520512044444b58b9c47a32f4d16b92328dbeff326b224c884d0a
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.