# Workflow Run Record

- run id: cfda1c7966f7
- skill: medagent.nv_segment_ct v0.1.0
- started: 2026-05-04T10:46:25.248255+00:00
- finished: 2026-05-04T10:46:31.094713+00:00
- elapsed: 5.846s
- exit code: 0

## Skill
- dir: <repo>/skills/nv-segment-ct
- entrypoint: scripts/segment_ct.py

## Fixture
- path: <repo>/skills/nv-segment-ct/fixtures/spleen_03.nii.gz
- sha256: 18fcb3df7da91366440dc4e14a9cc814024fce4df73db999b1d32e659ad127f9
- size: 11352181 bytes

## Validation
- status: passed

## Output (excerpt)
```json
{
  "skill": "nv_segment_ct",
  "model": "NVIDIA-Medtech/NV-Segment-CT (VISTA3D)",
  "model_repo": "https://huggingface.co/nvidia/NV-Segment-CT",
  "license": "NVIDIA Open Model License (commercial-friendly)",
  "input": {
    "path": "<repo>/skills/nv-segment-ct/fixtures/spleen_03.nii.gz",
    "resampled_shape": [
      253,
      253,
      131
    ]
  },
  "output": {
    "path": "<repo>/skills/nv-segment-ct/fixtures/spleen_03_seg.nii.gz",
    "shape": [
      128,
      128,
      128
    ],
    "label_prompts_requested": [
      1,
      3,
      5,
      14
    ],
    "class_counts": {
      "liver": 287451,
      "spleen": 27993,
      "right kidney": 41550,
      "left kidney": 39996
    },
    "any_label_present": true
  },
  "model_load": {
    "missing_keys": 0,
    "unexpected_keys": 0
  },
  "inference_mode": "single_patch_128_with_class_vector",
  "runtime": {
    "model_load_seconds": 0.474,
    "preprocess_seconds": 0.301,
    "inference_seconds": 3.314,
    "postprocess_seconds": 0.018,
    "device": "cpu"
  },
  "intended_use_disclaimer": "Engineering verification only. Output is NOT clinically meaningful. VISTA3D requires resampling to 1.5mm isotropic and HU clipping; eval_engine applies a simplified preprocessing chain that may degrade output vs the official MONAI bundle inference workflow."
}
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.