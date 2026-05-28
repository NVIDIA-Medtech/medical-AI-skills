# Workflow Run Record

- run id: c8621d9e3c07
- skill: medagent.verifiers.endoscopy_tool_detection_quality_v1 v0.1.0
- started: 2026-05-26T04:06:35.972019+00:00
- finished: 2026-05-26T04:06:36.089848+00:00
- elapsed: 0.118s
- exit code: 0

## Skill
- dir: verifiers/endoscopy_tool_detection_quality_v1
- entrypoint: scripts/grade.py

## Fixture
- path: verifiers/endoscopy_tool_detection_quality_v1/fixtures/pass_pack
- sha256: ee234f97e766eb7de0838f3b67cdd13f12b5f4598d771fab813d260165600d29
- size: 1454 bytes

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
        "actual_sha256": null,
        "bytes": 14,
        "declared_bytes": 14,
        "declared_path": "clip.gxf_index",
        "declared_sha256": "fixture",
        "exists": true,
        "hash_checked": false,
        "hash_match": null,
        "kind": "gxf",
        "path": "<repo>/verifiers/endoscopy_tool_detection_quality_v1/fixtures/pass_pack/recordings/clip.gxf_index",
        "usable": true
      },
      {
        "actual_sha256": null,
        "bytes": 17,
        "declared_bytes": 16,
        "declared_path": "clip.gxf_entities",
        "declared_sha256": "fixture",
        "exists": true,
        "hash_checked": false,
        "hash_match": null,
        "kind": "gxf",
        "path": "<repo>/verifiers/endoscopy_tool_detection_quality_v1/fixtures/pass_pack/recordings/clip.gxf_entities",
        "usable": true
      },
      {
        "actual_sha256": null,
        "bytes": 19,
        "declared_bytes": 18,
        "declared_path": "overlay.mp4",
        "declared_sha256": "fixture",
        "exists": true,
        "hash_checked": false,
        "hash_match": null,
        "kind": "video",
        "path": "<repo>/verifiers/endoscopy_tool_detection_quality_v1/fixtures/pass_pack/recordings/overlay.mp4",
        "usable": true
      },
      {
        "actual_sha256": null,

```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.
