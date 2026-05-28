# holohub_endoscopy_tool_tracking fixtures

Committed here:

- `example_clip_stub/`: empty path-existence fixture for tests.
- `configs/endoscopy_one_shot.yaml`: copy of the upstream endoscopy_tool_tracking
  config with `replayer.repeat: false` so the stream replayer terminates after
  the clip ends instead of looping forever. Use it for end-to-end smoke runs
  where you need the recording to be written out and the process to exit
  cleanly. Pass via `HOLOHUB_CONFIG=skills/holohub-endoscopy-tool-tracking/fixtures/configs/endoscopy_one_shot.yaml`.

Real runs use HoloHub-managed GXF stream pairs under:

```text
$HOLOHUB_ROOT/data/endoscopy/video/
```

First smoke run:

```bash
HOLOHUB_ROOT=$HOME/holohub HOLOHUB_RUN_MODE=container \
python3 -m eval_engine.run skills/holohub-endoscopy-tool-tracking \
  --fixture default \
  --out runs/endoscopy_demo
```

Custom fixtures must be GXF Stream Replayer pairs:
`<clip>.gxf_index` and `<clip>.gxf_entities`. Raw mp4/mkv is not accepted by
the upstream app.
