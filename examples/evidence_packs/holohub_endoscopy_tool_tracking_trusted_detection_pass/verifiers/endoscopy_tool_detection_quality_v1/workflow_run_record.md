# Workflow Run Record

- run id: e5bf70fdd55c
- skill: medagent.verifiers.endoscopy_tool_detection_quality_v1 v0.1.0
- started: 2026-05-26T05:03:03.891065+00:00
- finished: 2026-05-26T05:03:04.036491+00:00
- elapsed: 0.145s
- exit code: 0

## Skill
- dir: verifiers/endoscopy_tool_detection_quality_v1
- entrypoint: scripts/grade.py

## Fixture
- path: runs/holohub_endoscopy_trusted_default_pass_current3/skill_run
- sha256: 3e50e048b1358df51345c40661249eb466cde87868388e6c609d0074668d9abc
- size: 62773 bytes

## Validation
- overall: passed
- schema: passed
- sanity: passed
- runtime: within_envelope
- cost: skipped
- env_pin: skipped
- integrity: clean

## Output (excerpt)
```json
{
  "artifact_inventory": {
    "detection_artifact_count": 1,
    "files": [
      {
        "actual_sha256": "3c2212f6d4a492046ac40f88e168c3aa2e0fa369d571d4f8df575229a7e13c0d",
        "bytes": 147593760,
        "declared_bytes": 147593760,
        "declared_path": "tensor.gxf_entities",
        "declared_sha256": "3c2212f6d4a492046ac40f88e168c3aa2e0fa369d571d4f8df575229a7e13c0d",
        "exists": true,
        "hash_checked": true,
        "hash_match": true,
        "kind": "gxf",
        "path": "<home>/Documents/holohub/build/endoscopy_tool_tracking/recording_output/tensor.gxf_entities",
        "usable": true
      },
      {
        "actual_sha256": "aa724e414d38700dc6e1da7afe491c60699d14bf5c21c2bcdde91e2b1c80ce7c",
        "bytes": 2880,
        "declared_bytes": 2880,
        "declared_path": "tensor.gxf_index",
        "declared_sha256": "aa724e414d38700dc6e1da7afe491c60699d14bf5c21c2bcdde91e2b1c80ce7c",
        "exists": true,
        "hash_checked": true,
        "hash_match": true,
        "kind": "gxf",
        "path": "<home>/Documents/holohub/build/endoscopy_tool_tracking/recording_output/tensor.gxf_index",
        "usable": true
      },
      {
        "actual_sha256": "fc2cedcce06fb044813ab2c35ef0f1c65152f4cb8f67a6f64d1fbc3c1813dc45",
        "bytes": 925,
        "declared_bytes": 925,
        "declared_path": "tool_detections.jsonl",
        "declared_sha256": "fc2cedcce06fb044813ab2c35ef0f1c65152f4cb8f67a6f64d1fbc3c1813dc45",
        "exis
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.