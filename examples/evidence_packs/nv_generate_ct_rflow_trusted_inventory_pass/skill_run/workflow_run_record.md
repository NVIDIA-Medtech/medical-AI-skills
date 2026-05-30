# Workflow Run Record

- run id: 47f0993b6a4d
- skill: medagent.nv_generate_ct_rflow v0.1.0
- started: 2026-05-26T03:25:02.376914+00:00
- finished: 2026-05-26T03:26:22.368373+00:00
- elapsed: 79.991s
- exit code: 0

## Skill
- dir: skills/nv-generate-ct-rflow
- entrypoint: scripts/run_rflow_ct.py

## Fixture
- path: skills/nv-generate-ct-rflow/fixtures/chest_lung_tumor_controllable.json
- sha256: de9544cb2d0d20891c6db496e23e911fd7f7656809a56400738c6d4be61868d9
- size: 763 bytes

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
    "config_infer_override_path": "<repo>/skills/nv-generate-ct-rflow/fixtures/chest_lung_tumor_controllable.json",
    "config_infer_override": {
      "num_output_samples": 1,
      "body_region": [
        "chest"
      ],
      "anatomy_list": [
        "lung tumor",
        "left lung upper lobe",
        "left lung lower lobe",
        "right lung upper lobe",
        "right lung middle lobe",
        "right lung lower lobe",
        "heart"
      ],
      "controllable_anatomy_size": [
        [
          "lung tumor",
          0.2
        ]
      ],
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
      "lung tumor",
      "left lung upper lobe",
      "left lung lower lobe",
      "right lung upper lobe",
      "right lung middle lobe",
      "right lung lower lobe",
      "heart"
    ],
    "effective_anatomy_for_output": [
      "lung tumor"
    ],
    "paired_output_label_semantics": "Saved paired
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.