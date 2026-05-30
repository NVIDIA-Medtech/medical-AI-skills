# Workflow Run Record

- run id: 01eec42b240c
- skill: medagent.nv_segment_ct v0.2.0
- started: 2026-05-26T01:47:35.143965+00:00
- finished: 2026-05-26T01:48:10.863554+00:00
- elapsed: 35.72s
- exit code: 0

## Skill
- dir: skills/nv-segment-ct
- entrypoint: scripts/run_vista3d.py

## Fixture
- path: skills/nv-segment-ct/fixtures/spleen_03.nii.gz
- sha256: 18fcb3df7da91366440dc4e14a9cc814024fce4df73db999b1d32e659ad127f9
- size: 11352181 bytes

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
  "skill": "nv_segment_ct",
  "model": "NVIDIA-Medtech/NV-Segment-CT (VISTA3D)",
  "model_repo": "https://huggingface.co/nvidia/NV-Segment-CT",
  "license": "NVIDIA Open Model License (commercial-friendly)",
  "input": {
    "path": "skills/nv-segment-ct/fixtures/spleen_03.nii.gz",
    "shape": [
      512,
      512,
      40
    ],
    "ndim": 3,
    "spacing": [
      0.738281,
      0.738281,
      5.0
    ],
    "ground_truth_path": null
  },
  "output": {
    "shape": [
      512,
      512,
      40
    ],
    "label_prompts_requested": [
      1,
      3,
      5,
      14
    ],
    "label_ids_present": [
      1,
      3,
      5,
      14
    ],
    "unexpected_label_ids": [],
    "label_set_valid": true,
    "class_counts": {
      "label_id_1": 456974,
      "label_id_3": 60161,
      "label_id_5": 51177,
      "label_id_14": 49652
    },
    "voxel_volume_ml": 0.00272529,
    "class_volumes_ml": {
      "label_id_1": 1245.3886,
      "label_id_3": 163.9564,
      "label_id_5": 139.4724,
      "label_id_14": 135.3163
    },
    "any_label_present": true,
    "geometry": {
      "input_shape": [
        512,
        512,
        40
      ],
      "output_shape": [
        512,
        512,
        40
      ],
      "shape_match": true,
      "input_spacing": [
        0.738281,
        0.738281,
        5.0
      ],
      "output_spacing": [
        0.738281,
        0.738281,
        5.0
      ],
      "spacing_match": true,
      "affine_max_abs_diff": 0.0,

```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.
