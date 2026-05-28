# Workflow Run Record

- run id: 2621bbd017eb
- skill: medagent.find_skills v0.2.0
- started: 2026-05-26T01:25:16.068932+00:00
- finished: 2026-05-26T01:25:16.306665+00:00
- elapsed: 0.238s
- exit code: 0

## Skill
- dir: skills/find-skills
- entrypoint: scripts/find_skills.py

## Fixture
- path: skills/find-skills/fixtures/example_task.txt
- sha256: 7a48cce6b7321724d8a41119300b57695cc0d9ddea62e23a6d0d82a316b81326
- size: 26 bytes

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
  "skill": "find_skills",
  "input": {
    "query": "segment a CT NIfTI volume"
  },
  "catalog": {
    "count": 28
  },
  "top_recommendation": {
    "id": "medagent.nv_segment_ct",
    "path": "skills/nv-segment-ct",
    "kind": "skill",
    "summary": "Engineering-time wrapper around NVIDIA-Medtech NV-Segment-CT (VISTA3D 132-class CT seg foundation model). Invokes the official `HuggingFacePipelineHelper` from https://huggingface.co/nvidia/NV-Segment-CT exactly as the model card recommends.",
    "scope": "development",
    "not_for": [
      "clinical deployment",
      "clinical interpretation",
      "autonomous diagnosis",
      "regulatory submission"
    ],
    "inputs": [
      {
        "name": "ct_volume",
        "type": "file_path",
        "formats": [
          "nifti"
        ]
      }
    ],
    "outputs": [
      {
        "name": "label_map",
        "type": "file_path",
        "formats": [
          "nifti"
        ]
      },
      {
        "name": "result_json",
        "type": "json",
        "formats": []
      }
    ],
    "paired_verifiers": [
      {
        "id": "medagent.verifiers.ct_segmentation_quality_v1",
        "status": "implemented"
      }
    ],
    "requires_gpu": "cuda",
    "requires_docker": false,
    "limitations": [
      "This is a thin wrapper. Inference, preprocessing, and postprocessing are delegated entirely to the official `hugging_face_pipeline.HuggingFacePipelineHelper` in bundle/. Do not modify code under bundle/.",

```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.
