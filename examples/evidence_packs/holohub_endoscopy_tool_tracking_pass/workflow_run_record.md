# Workflow Run Record

- run id: f246170cc0b0
- skill: holohub_endoscopy_tool_tracking v0.1.0
- started: 2026-05-10T21:19:44.588188+00:00
- finished: 2026-05-10T21:19:51.085030+00:00
- elapsed: 6.497s
- exit code: 0

## Skill
- dir: skills/holohub-endoscopy-tool-tracking
- entrypoint: scripts/run_endoscopy_tool_tracking.py

## Fixture
- path: skills/holohub-endoscopy-tool-tracking/fixtures/example_clip_stub
- sha256: e6e72ba1e8bdbc136ba8b2a96d4e0ce8290500bb3ca388c498017eb05121bf73
- size: 341 bytes

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
    "holohub_root": ".workbench_data/holohub",
    "holohub_commit": "0eb7dcfb94d8b09a28075fb87337fcc12cff0af5",
    "mode": "container",
    "language": "python",
    "source": "replayer",
    "record_type": "visualizer",
    "postprocessor": "tool_tracking_postprocessor",
    "config_path": null,
    "data_dir": ".workbench_data/holohub/data/endoscopy",
    "command": [
      "./holohub",
      "run",
      "endoscopy_tool_tracking",
      "--language",
      "python",
      "--run-args=-s replayer -r visualizer -p tool_tracking_postprocessor"
    ],
    "exit_code": 0,
    "container_image": "holohub-endoscopy_tool_tracking:main",
    "container_image_id": "sha256:ed7b6078a0b871f53a87a3440400052d6a6f3a19a068b1023a80a260429660b3",
    "model_path": ".workbench_data/holohub/data/endoscopy/tool_loc_convlstm.onnx",
    "model_sha256": "d05733d49187f10975eafd762001f4535f5029fd071ca39779f953c7886a3c18",
    "fixture": "skills/holohub-endoscopy-tool-tracking/fixtures/example_clip_stub",
    "recording_output_dir": ".workbench_data/holohub/build/endoscopy_tool_tracking/recording_output"
  },
  "output": {
    "gxf": {
      "count": 2,
      "total_bytes": 368991600,
      "files": [
        {
          "path": "tensor.gxf_entities",
          "bytes": 368984400,
      
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.