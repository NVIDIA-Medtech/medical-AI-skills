#!/usr/bin/env python3
"""Run NVIDIA HoloHub `endoscopy_tool_tracking` via its canonical CLI.

This script is intentionally a *thin wrapper* around the upstream
`./holohub run endoscopy_tool_tracking` documented at
https://github.com/nvidia-holoscan/holohub/tree/main/applications/endoscopy_tool_tracking.

It does NOT reimplement the Holoscan operator graph, the LSTM TRT
inference plugin, the tool-tracking postprocessor, or the Holoviz
overlay. It cd's to the holohub clone, invokes the documented CLI
verbatim, scans the recording output dir, and prints a JSON evidence
payload to stdout for the eval_engine.

Conventions used by `eval_engine/run.py`:
  * argv[1] is the fixture path. The literal string "default" means
    "use whatever HoloHub provisioned at $HOLOHUB_ROOT/data/endoscopy/";
    any other value is treated as a path to a directory containing a
    GXF Stream Replayer pair (<clip>.gxf_index + <clip>.gxf_entities).
  * Configuration via env so the eval_engine's fixed
    [python, script, fixture] invocation pattern still works:
      HOLOHUB_ROOT                 required
      HOLOHUB_RUN_MODE             container (default) | local
      HOLOHUB_LANGUAGE             cpp (default) | python
      HOLOHUB_SOURCE               replayer (default) | aja | deltacast | yuan
      HOLOHUB_RECORD_TYPE          none (default) | input | visualizer
      HOLOHUB_POSTPROCESSOR        tool_tracking_postprocessor (default) | slang_shader
      HOLOHUB_CONFIG               optional YAML path (-c)
      HOLOHUB_DATA_DIR             optional data dir (-d)
      HOLOHUB_RECORDING_OUTPUT_DIR optional override of recording scan dir
      HOLOHUB_TIMEOUT_SECONDS      default 1800
  * JSON payload printed to stdout. The script exits 0 whenever it
    can produce a payload, even if the upstream CLI itself failed --
    the failure is recorded in `invocation.exit_code` so the
    eval_engine's sanity gate can fire on it.

The wrapper does NOT compute per-frame detection counts, bbox
in-image sanity, or mean-tools-per-frame. The upstream baseline does
not emit those signals on stdout, and decoding GXF tensor streams to
reconstruct them would be homegrown logic outside the upstream
tool's spec. That belongs to a downstream verifier.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
_SKILLS_DIR = _SCRIPT_DIR.parent.parent
if str(_SKILLS_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILLS_DIR))
from export_tool_detections import export_tool_detections  # noqa: E402
from _shared.docker_capture import capture_container_provenance  # noqa: E402
from _shared.wrapper_utils import (  # noqa: E402
    collect_group,
    docker_image_id,
    emit,
    fail_with,
    file_sha256_safe,
    git_commit,
    sha256_file,
    tail,
)


# ---------- output scanner (reads only what the upstream CLI wrote) ----------

# Endoscopy tool tracking does not write outputs by default (--record_type=none).
# When --record_type is set to `input` or `visualizer`, the application's
# VideoStreamRecorderOp writes to a directory configured in the YAML
# (default Medical AI Skills convention: <HOLOHUB_ROOT>/build/endoscopy_tool_tracking/
# recording_output/). The scanner reports what is present; it does NOT
# decode GXF tensor streams.

def scan_output(output_root: Path) -> dict[str, Any]:
    if not output_root.exists():
        return {
            "gxf":   {"count": 0, "total_bytes": 0, "files": []},
            "video": {"count": 0, "total_bytes": 0, "files": []},
            "other": {"count": 0, "total_bytes": 0, "files": []},
        }

    gxf: list[Path] = []
    video: list[Path] = []
    other: list[Path] = []
    for p in sorted(output_root.rglob("*")):
        if not p.is_file():
            continue
        suffix = p.suffix.lower()
        if suffix in (".gxf_index", ".gxf_entities"):
            gxf.append(p)
        elif suffix in (".mp4", ".mkv", ".raw"):
            video.append(p)
        else:
            other.append(p)

    return {
        "gxf":   collect_group(gxf, output_root),
        "video": collect_group(video, output_root),
        "other": collect_group(other, output_root),
    }


# ---------- driver ----------


# Documented enum values for the upstream CLI's flags. The wrapper
# refuses to fabricate values the upstream does not accept, so the
# `./holohub run` invocation can never get an unrecognised flag value
# from this script.
LANGUAGES   = ("cpp", "python")
SOURCES     = ("replayer", "aja", "deltacast", "yuan")
RECORD_TYPES = ("none", "input", "visualizer")
POSTPROCESSORS = ("tool_tracking_postprocessor", "slang_shader")
RUN_MODES   = ("container", "local")


def _container_visible_holohub_path(path: Path, holohub_root: Path, stage_dir: Path) -> str:
    """Return the /workspace/holohub path for a host file used in container mode."""
    try:
        rel = path.relative_to(holohub_root)
    except ValueError:
        stage_dir.mkdir(parents=True, exist_ok=True)
        staged = stage_dir / path.name
        if staged.resolve() != path:
            shutil.copy2(path, staged)
        rel = staged.relative_to(holohub_root)
    return "/workspace/holohub/" + rel.as_posix()


def _enum(name: str, value: str, allowed: tuple[str, ...]) -> str | int:
    """Return the validated value, or an error code via fail_with()."""
    if value in allowed:
        return value
    return fail_with(
        f"{name} must be one of {'|'.join(allowed)}, got {value!r}"
    )


def main() -> int:
    fixture_arg = sys.argv[1] if len(sys.argv) > 1 else "default"

    holohub_root_str = os.environ.get("HOLOHUB_ROOT", "").strip()
    if not holohub_root_str:
        return fail_with("HOLOHUB_ROOT env var is required")
    holohub_root = Path(holohub_root_str).expanduser().resolve()
    if not (holohub_root / "holohub").exists():
        return fail_with(
            f"HOLOHUB_ROOT={holohub_root} has no ./holohub script. "
            f"Did you `git clone https://github.com/nvidia-holoscan/holohub.git`?"
        )

    mode = (os.environ.get("HOLOHUB_RUN_MODE", "").strip() or "container")
    rc_or_mode = _enum("HOLOHUB_RUN_MODE", mode, RUN_MODES)
    if isinstance(rc_or_mode, int):
        return rc_or_mode

    language = (os.environ.get("HOLOHUB_LANGUAGE", "").strip() or "cpp")
    rc_or_lang = _enum("HOLOHUB_LANGUAGE", language, LANGUAGES)
    if isinstance(rc_or_lang, int):
        return rc_or_lang

    source = (os.environ.get("HOLOHUB_SOURCE", "").strip() or "replayer")
    rc_or_src = _enum("HOLOHUB_SOURCE", source, SOURCES)
    if isinstance(rc_or_src, int):
        return rc_or_src

    record_type = (os.environ.get("HOLOHUB_RECORD_TYPE", "").strip() or "none")
    rc_or_rec = _enum("HOLOHUB_RECORD_TYPE", record_type, RECORD_TYPES)
    if isinstance(rc_or_rec, int):
        return rc_or_rec

    postprocessor = (os.environ.get("HOLOHUB_POSTPROCESSOR", "").strip()
                     or "tool_tracking_postprocessor")
    rc_or_pp = _enum("HOLOHUB_POSTPROCESSOR", postprocessor, POSTPROCESSORS)
    if isinstance(rc_or_pp, int):
        return rc_or_pp

    config_path_str = os.environ.get("HOLOHUB_CONFIG", "").strip()
    config_path = Path(config_path_str).expanduser().resolve() if config_path_str else None
    if config_path is not None and not config_path.is_file():
        return fail_with(f"HOLOHUB_CONFIG={config_path} is not a file")
    config_arg_path: str | None = None
    if config_path is not None:
        if mode == "container":
            config_arg_path = _container_visible_holohub_path(
                config_path,
                holohub_root,
                holohub_root / "build" / "endoscopy_tool_tracking" / "workbench_configs",
            )
        else:
            config_arg_path = str(config_path)

    data_dir_env = os.environ.get("HOLOHUB_DATA_DIR", "").strip()
    if data_dir_env:
        data_dir = Path(data_dir_env).expanduser().resolve()
    else:
        data_dir = (holohub_root / "data" / "endoscopy").resolve()

    timeout_s = float(os.environ.get("HOLOHUB_TIMEOUT_SECONDS", "1800"))

    # Stage a custom fixture if the caller passed a real path. The "default"
    # sentinel means "use whatever HoloHub provisioned at the data dir";
    # we don't touch data/ in that case.
    if fixture_arg != "default":
        fixture_path = Path(fixture_arg).expanduser().resolve()
        if not fixture_path.exists():
            return fail_with(f"fixture path not found: {fixture_path}")
        if not fixture_path.is_dir():
            return fail_with(
                f"fixture must be a directory containing GXF replayer "
                f"pair (<clip>.gxf_index + <clip>.gxf_entities); got "
                f"{fixture_path} (not a directory)"
            )
        # Stage to data/endoscopy/video/ so VideoStreamReplayerOp finds
        # it. Wipe the whole subdir first so a previous run's clip cannot
        # compete with this run's fixture during recursive scans.
        staged_video = data_dir / "video"
        if staged_video.exists():
            shutil.rmtree(staged_video)
        staged_video.mkdir(parents=True, exist_ok=True)
        for entry in fixture_path.iterdir():
            if entry.is_file():
                shutil.copy2(entry, staged_video / entry.name)

    # Recording scan dir. Default to a Medical AI Skills convention; the
    # caller can point at the YAML's actual recorder.directory if they
    # know it differs.
    rec_dir_env = os.environ.get("HOLOHUB_RECORDING_OUTPUT_DIR", "").strip()
    if rec_dir_env:
        recording_output_dir = Path(rec_dir_env).expanduser().resolve()
    else:
        recording_output_dir = (
            holohub_root / "build" / "endoscopy_tool_tracking" / "recording_output"
        ).resolve()
    # Wipe stale recordings before each run so a previous run's
    # output cannot bleed into this run's evidence pack.
    if recording_output_dir.exists():
        shutil.rmtree(recording_output_dir)
    recording_output_dir.mkdir(parents=True, exist_ok=True)

    # Construct argv per the upstream `./holohub run --help`.
    # `./holohub run` accepts `--language` directly; app-level flags are
    # forwarded through `--run-args="..."`.
    #
    # The upstream cpp binary (`endoscopy_tool_tracking`) uses getopt and
    # accepts only `-c <config>` and `-d <data>`. Earlier revisions of this
    # wrapper also forwarded `-s/-r/-p`, but the cpp binary rejects those
    # with `invalid option -- 's'`, after which getopt halts and the binary
    # falls back to its baked-in default YAML — so the user's source /
    # postprocessor / record_type choices were silently ignored in cpp
    # mode. For cpp we therefore pass only `-c` and `-d`; the choice of
    # source / postprocessor / record_type belongs in the config YAML.
    # The python entrypoint accepts the full -s/-r/-p set, so we keep them
    # for `--language python`.
    app_args: list[str] = []
    if language == "python":
        app_args += [
            "-s", source,
            "-r", record_type,
            "-p", postprocessor,
        ]
    if config_arg_path is not None:
        app_args += ["-c", config_arg_path]
    if data_dir_env:
        app_args += ["-d", str(data_dir)]
    run_args_value = " ".join(app_args)

    cmd: list[str] = ["./holohub", "run", "endoscopy_tool_tracking"]
    if mode == "local":
        cmd += ["--local"]
    cmd += [
        "--language", language,
        f"--run-args={run_args_value}",
    ]

    # Drift fingerprints captured before the run so they're recorded
    # even if the subprocess fails.
    holohub_commit_val = git_commit(holohub_root)
    container_image = (
        "holohub-endoscopy_tool_tracking:main" if mode == "container" else None
    )
    container_image_id_val = (
        docker_image_id(container_image) if container_image else None
    )
    # The upstream HoloHub data manager places the ONNX directly under
    # data/endoscopy/, not data/endoscopy/model/, so the model fingerprint
    # is read from <data_dir>/tool_loc_convlstm.onnx. Verified against
    # holohub@0eb7dcfb on 2026-05-10.
    model_path = data_dir / "tool_loc_convlstm.onnx"
    model_sha = file_sha256_safe(model_path)

    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(holohub_root),
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        rc = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
    except subprocess.TimeoutExpired as e:
        rc = int("124")
        stdout = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        stderr_raw = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
        stderr = stderr_raw + f"\n[TIMEOUT after {timeout_s}s]"
    except FileNotFoundError as e:
        rc = int("127")
        stdout = ""
        stderr = f"command not found: {e}"
    elapsed = time.monotonic() - t0

    if mode == "container" and container_image:
        container_image_id_val = docker_image_id(container_image)
        try:
            container_provenance = capture_container_provenance(container_image)
        except Exception as e:
            container_provenance = {"status": "failed", "reason": repr(e)}
    else:
        container_provenance = {"status": "skipped", "reason": "not container mode"}

    export_enabled = os.environ.get("HOLOHUB_EXPORT_TOOL_DETECTIONS", "").strip().lower()
    if export_enabled in ("", "auto"):
        do_export = record_type in ("input", "visualizer")
    else:
        do_export = export_enabled in ("1", "true", "yes", "on")

    detection_path, detection_meta = export_tool_detections(
        recording_output_dir,
        stdout,
        stderr,
        enabled=do_export,
    )

    output_inventory = scan_output(recording_output_dir)
    recording_file_count = sum(
        int(output_inventory[group]["count"]) for group in ("gxf", "video", "other")
    )
    recording_total_bytes = sum(
        int(output_inventory[group]["total_bytes"]) for group in ("gxf", "video", "other")
    )
    output_inventory.update({
        "recording_file_count": recording_file_count,
        "recording_total_bytes": recording_total_bytes,
        # `record_type=none` is a valid smoke path. If the caller requested
        # recording, absence of any artifact is a spec failure the eval_engine
        # can catch via a simple sanity check.
        "recording_written_ok": record_type == "none" or recording_file_count > 0,
    })

    payload: dict[str, Any] = {
        "invocation": {
            "holohub_root":         str(holohub_root),
            "holohub_commit":       holohub_commit_val,
            "mode":                 mode,
            "language":             language,
            "source":               source,
            "record_type":          record_type,
            "postprocessor":        postprocessor,
            "config_path":          str(config_path) if config_path else None,
            "data_dir":             str(data_dir),
            "command":              cmd,
            "exit_code":            rc,
            "container_image":      container_image,
            "container_image_id":   container_image_id_val if mode == "container" else None,
            "container_provenance": container_provenance,
            "model_path":           str(model_path),
            "model_sha256":         model_sha,
            "fixture":              fixture_arg,
            "recording_output_dir": str(recording_output_dir),
        },
        "output": output_inventory,
        "detection_export": detection_meta,
        "runtime": {
            "subprocess_seconds": elapsed,
        },
        "logs": {
            "stdout_tail": tail(stdout),
            "stderr_tail": tail(stderr),
        },
    }

    emit(payload)
    # Always exit 0 if we produced a payload -- the eval_engine reads it
    # and the sanity gate fires on `invocation.exit_code != 0` if the
    # upstream CLI itself failed. This keeps the gate uniform.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
