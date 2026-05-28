# Workflow Run Record

- run id: 5dab9a8a210b
- skill: holohub_endoscopy_tool_tracking v0.1.0
- started: 2026-05-26T05:02:54.656342+00:00
- finished: 2026-05-26T05:03:03.500155+00:00
- elapsed: 8.844s
- exit code: 0

## Skill
- dir: skills/holohub-endoscopy-tool-tracking
- entrypoint: scripts/run_endoscopy_tool_tracking.py

## Fixture
- path: default
- sha256:
- size: 0 bytes

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
  "invocation": {
    "holohub_root": "<home>/Documents/holohub",
    "holohub_commit": "30534c4922a48d3304857f3762730e34c0ef1345",
    "mode": "container",
    "language": "python",
    "source": "replayer",
    "record_type": "visualizer",
    "postprocessor": "tool_tracking_postprocessor",
    "config_path": "<repo>/skills/holohub-endoscopy-tool-tracking/fixtures/configs/endoscopy_workflow_trusted.yaml",
    "data_dir": "<home>/Documents/holohub/data/endoscopy",
    "command": [
      "./holohub",
      "run",
      "endoscopy_tool_tracking",
      "--language",
      "python",
      "--run-args=-s replayer -r visualizer -p tool_tracking_postprocessor -c /workspace/holohub/build/endoscopy_tool_tracking/workbench_configs/endoscopy_workflow_trusted.yaml"
    ],
    "exit_code": 0,
    "container_image": "holohub-endoscopy_tool_tracking:main",
    "container_image_id": "sha256:35221ba8dfdad1605b23ba639d2ed88a4d5382c8e4512aa3d1d1a5e5c69edad9",
    "container_provenance": {
      "image_ref": "holohub-endoscopy_tool_tracking:main",
      "inspect": {
        "status": "ok",
        "id": "sha256:35221ba8dfdad1605b23ba639d2ed88a4d5382c8e4512aa3d1d1a5e5c69edad9",
        "repo_tags": [
          "holohub-endoscopy_tool_tracking:90e0af6b2fa9",
          "holohub-endoscopy_tool_tracking:main",
          "holohub:endoscopy_tool_tracking"
        ],
        "labels": {
          "com.nvidia.build.id": "280215355",
          "com.nvidia.bu
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.
