# Workflow Run Record

> Reference evidence pack from a real RTX 6000 Ada run.
> The `samples/` directory (one 10 MB CT NIfTI + paired 290 KB label NIfTI)
> was elided before committing — Medical AI Skills policy: no large generated
> medical artifacts in the tracked tree. Regenerate by running
> `make run-skill SKILL=nv_generate_ct_rflow FIXTURE=skills/nv-generate-ct-rflow/fixtures/default_config_infer.json OUT=runs/nv_generate_ct_rflow_demo`
> after exporting `NV_GENERATE_ROOT` to your NV-Generate-CTMR clone.

- run id: 8b009bc17c0a
- skill: medagent.nv_generate_ct_rflow v0.1.0
- started: 2026-05-19T08:52:05.436864+00:00
- finished: 2026-05-19T08:53:32.610138+00:00
- elapsed: 87.173s
- exit code: 0

## Skill
- dir: skills/nv-generate-ct-rflow
- entrypoint: scripts/run_rflow_ct.py

## Fixture
- path: skills/nv-generate-ct-rflow/fixtures/default_config_infer.json
- sha256: 59e81d33e194b42634a02d75beb84b664446159decf3f169b3523c334c3fd5c0
- size: 623 bytes

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
  "skill": "nv_generate_ct_rflow",
  "model": "NVIDIA-Medtech/NV-Generate-CTMR (rflow-ct)",
  "model_repo": "https://github.com/NVIDIA-Medtech/NV-Generate-CTMR",
  "model_weights_repo": "https://huggingface.co/nvidia/NV-Generate-CT",
  "license": "NVIDIA Open Model License (commercial-friendly)",
  "input": {
    "config_infer_override_path": "/<home>/Documents/medical-AI-skills/skills/nv-generate-ct-rflow/fixtures/default_config_infer.json",
    "config_infer_override": {
      "num_output_samples": 1,
      "body_region": [
        "chest"
      ],
      "anatomy_list": [
        "lung tumor"
      ],
      "controllable_anatomy_size": [],
      "output_size": [
        256,
        256,
        256
      ],
      "spacing": [
        1.5,
        1.5,
        2.0
      ],
      "num_inference_steps": 30,
      "image_output_ext": ".nii.gz",
      "label_output_ext": ".nii.gz"
    },
    "anatomy_list_requested": [
      "lung tumor"
    ],
    "body_region_requested": [
      "chest"
    ],
    "num_output_samples_requested": 1,
    "output_size_requested": [
      256,
      256,
      256
    ],
    "spacing_requested": [
      1.5,
      1.5,
      2.0
    ],
    "random_seed": 0,
    "version": "rflow-ct"
  },
  "output": {
    "directory": "/<home>/Documents/medical-AI-skills/runs/nv_generate_ct_rflow_gpu_demo/samples",
    "samples": [
      {
        "image_path": "/<home>/Documents/medical-AI-skills/runs/nv_generate_ct_rflow_gpu_demo/samples/sample_20260
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.