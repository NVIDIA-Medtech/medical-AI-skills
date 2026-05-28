# HoloHub CLI Notes

Authoritative source: <https://github.com/nvidia-holoscan/holohub>.

## Run modes

```bash
./holohub run <app>
./holohub run <app> --local --language python
```

Container mode is the default and may build or pull large images. Local mode
requires Holoscan SDK and app dependencies on the host.

## App paths

Common HoloHub apps read:

| Variable | Purpose |
|---|---|
| `HOLOSCAN_INPUT_PATH` | input data |
| `HOLOSCAN_MODEL_PATH` | model directory |
| `HOLOSCAN_OUTPUT_PATH` | output directory |

Set env vars before invoking `./holohub run`. Only pass app-level flags through
`--run-args` when the HoloHub app expects them.

## Wrapper pattern

```python
cmd = ["./holohub", "run", app_name]
env = os.environ.copy()
env["HOLOSCAN_INPUT_PATH"] = str(fixture_dir)
env["HOLOSCAN_OUTPUT_PATH"] = str(output_dir)
subprocess.run(cmd, cwd=str(holohub_root), env=env, check=True)
```

Clean output directories between runs. Old DICOM SEG or GXF files can create
false positives.

## Capture

Record HoloHub commit, container image ID, model hashes, output file hashes,
and the exact `--run-args` string. Host CPU/RSS cost is weak in container mode;
GPU memory is still visible through `nvidia-smi`.
