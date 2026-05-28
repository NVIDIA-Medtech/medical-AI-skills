---
name: holohub-endoscopy-tool-tracking
description: Used for running HoloHub endoscopy_tool_tracking via ./holohub run and recording execution evidence. Not for detection-quality claims.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - medtech
    - holohub
    - endoscopy
---

# HoloHub Endoscopy Tool Tracking

## Purpose
- Used for running HoloHub endoscopy_tool_tracking via ./holohub run and recording execution evidence. Not for detection-quality claims.
- Use the wrapper exactly as documented; do not replace the upstream entrypoint with a handwritten implementation.
- Manifest I/O: inputs are `endoscopy_clip`; outputs are `recording_files` and `result_json`.

## Instructions
- Read `skill_manifest.yaml` before changing arguments, side effects, or validation gates.
- Run `scripts/run_endoscopy_tool_tracking.py` through the documented command below; keep outputs under a caller-provided run directory.
- If a host agent exposes `run_script`, use `run_script("scripts/run_endoscopy_tool_tracking.py", args=[...])`; otherwise run the Bash/Python command shown below.
- Check the emitted JSON and paired verifier guidance before treating the run as evidence.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/export_tool_detections.py` | Helper imported by the primary entrypoint to normalize detections. | Imported only; do not call directly. |
| `scripts/run_endoscopy_tool_tracking.py` | Primary entrypoint declared by skill_manifest.yaml. | `[PATH_TO_GXF_REPLAYER_DIR]` plus `HOLOHUB_ROOT` and optional `HOLOHUB_*` env vars |

## Prerequisites
- Required environment variables: `HOLOHUB_ROOT`.
- Runtime requirements: GPU/CUDA when declared by the manifest; Docker/NVIDIA Container Toolkit when container mode is used.
- Side effects: container mode may write Docker layers under `/var/lib/docker/` and pull images from `https://nvcr.io`; source or sample fetches use `https://github.com`.
- Run commands from the repository root unless an existing section below says otherwise.

## Limitations
- The upstream baseline `endoscopy_tool_tracking` application does NOT emit FPS or frame-count signals on stdout. The skill therefore does not parse one and does not gate on throughput — that gap is declared honestly rather than filled with homegrown logic. A sibling skill that adds an instrumented Holoscan operator could expose the metric upstream, after which a future revision of this manifest could pin against it.
- The recording output path is config-dependent (the recorder operator's `directory` field in the YAML). The default scan path `<HOLOHUB_ROOT>/build/endoscopy_tool_tracking/recording_output/` is Medical AI Skills convention and is overrideable via HOLOHUB_RECORDING_OUTPUT_DIR. If your YAML writes elsewhere, override or the recording inventory will be empty.
- Container mode requires Docker, an NVIDIA GPU, and the Holoscan SDK container (~several GB). First-run pull/build takes minutes; subsequent runs reuse the cached image.
- Custom fixtures must be in the GXF Stream Replayer format (`.gxf_index` + matching `.gxf_entities`). Raw mp4/mkv is not accepted by `VideoStreamReplayerOp`.
- Not for clinical deployment, clinical interpretation, autonomous diagnosis, regulatory submission.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| Missing dependency or import error | Runtime package drift from `skill_manifest.yaml`. | Install the packages declared in the manifest or use the documented setup command. |
| Empty or schema-invalid output | Wrong input path, unsupported modality, or upstream failure. | Re-run with a known fixture and inspect the wrapper JSON plus stderr. |
| Validation gate failure | Output violated a declared engineering invariant. | Keep the failed evidence pack and use the gate message to repair inputs or wrapper code. |

Runs `applications/endoscopy_tool_tracking` through HoloHub's documented CLI.
The wrapper does not reimplement the Holoscan graph or decode GXF entity
streams.

## Preconditions

Clone HoloHub and point `HOLOHUB_ROOT` at it; container mode also needs a
running Docker daemon and an NVIDIA GPU. The wrapper does not download
HoloHub for you — that's intentional, since HoloHub's data-manager pulls
sample clips and Docker images into the user's clone.

```bash
git clone https://github.com/nvidia-holoscan/holohub.git $HOME/holohub
export HOLOHUB_ROOT=$HOME/holohub
```

`HOLOHUB_RUN_MODE=container` (default) requires Docker; `HOLOHUB_RUN_MODE=local`
requires the Holoscan SDK installed natively.

Optional HoloHub controls:

| Variable | Purpose |
|---|---|
| `HOLOHUB_LANGUAGE` | Select `python` or `cpp` app variant. |
| `HOLOHUB_SOURCE` | Select replayer or supported capture source. |
| `HOLOHUB_RECORD_TYPE` | Select no recording, input recording, or visualizer recording. |
| `HOLOHUB_POSTPROCESSOR` | Select the application postprocessor override. |
| `HOLOHUB_CONFIG` | Pass a bounded application YAML via `-c`. |
| `HOLOHUB_DATA_DIR` | Pass a HoloHub data directory via `-d`. |
| `HOLOHUB_RECORDING_OUTPUT_DIR` | Override where the wrapper scans for recorder output. |
| `HOLOHUB_TIMEOUT_SECONDS` | Bound the upstream app subprocess. |

## Usage

```bash
HOLOHUB_ROOT=/path/to/holohub HOLOHUB_RUN_MODE=container \
HOLOHUB_LANGUAGE=python HOLOHUB_RECORD_TYPE=visualizer \
python3 -m eval_engine.run skills/holohub-endoscopy-tool-tracking \
  --fixture default \
  --out runs/endoscopy_demo
```

## Preconditions for a non-interactive run

App-level HoloHub flags are passed through `--run-args`. Non-interactive runs
usually need bounded replayer, headless visualization, and recorder config
overrides under the HoloHub tree so container paths resolve correctly.

Pass a bounded application config via `HOLOHUB_CONFIG`; otherwise the upstream
sample replayer can loop forever and block commands scheduled after the app
run. The bundled Medical AI Skills config is:

```bash
HOLOHUB_CONFIG=skills/holohub-endoscopy-tool-tracking/fixtures/configs/endoscopy_workflow_trusted.yaml
```

Required config overrides:

- `replayer.repeat: false`
- `replayer.count: <finite frame count>`
- `holoviz.headless: true`
- `recorder.directory`: a path inside the mounted HoloHub workspace when
  recording output should be collected

The evidence pack proves pipeline execution, runtime envelope, HoloHub/model
fingerprints, recording inventory, and optional `tool_detections.jsonl` export
(log parse or sidecar in the recording dir). Tool-count, bbox, and frame-coverage
quality are checked by
`verifiers/endoscopy_tool_detection_quality_v1` when decoded detections are
available.
