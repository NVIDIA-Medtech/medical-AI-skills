"""Tests for skills/holohub-endoscopy-tool-tracking.

These tests verify the *wrapper* spec — argv construction, env
wiring, output scanning, drift fingerprint capture. They do NOT
exercise the Holoscan SDK, the LSTM TRT inference plugin, or the
endoscopy sample (which require a Holoscan container and a GPU).
The full-integration tests use a tiny stub `holohub` shell script
that mimics the upstream CLI's behaviour: argparse the documented
flags and (optionally) drop a fake recording file in the recording
output dir. The wrapper's spec for the upstream CLI is
'invoke `./holohub run endoscopy_tool_tracking --language ... -s ...
-r ... -p ...`, scan recording_output_dir'; this stub satisfies that
spec exactly.

Test taxonomy:
  * Argument-construction tests (no subprocess that does work)
  * Error-path tests (missing env / bad enum values / missing fixture)
  * Full-integration tests using a stub holohub script
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SCRIPT = SKILL / "scripts" / "run_endoscopy_tool_tracking.py"
EXAMPLE_FIXTURE = SKILL / "fixtures" / "example_clip_stub"


def _make_stub_holohub_root(tmp_path: Path, write_recording: bool = True) -> Path:
    """Create a fake HoloHub clone with a stub `./holohub` shell script.

    The stub mimics the upstream CLI: parse argv, optionally write a
    fake recording into Medical AI Skills' default scan dir
    (build/endoscopy_tool_tracking/recording_output/). The wrapper's
    spec for the upstream CLI is 'invoke `./holohub run
    endoscopy_tool_tracking --language ... --run-args="-s ... -r ...
    -p ..."`, scan recording_output_dir'; this stub satisfies that
    spec.
    """
    holohub_root = tmp_path / "holohub"
    holohub_root.mkdir(parents=True)

    # Build dir is where the recorder will write by default. Match the
    # Medical AI Skills convention so the wrapper's scan picks it up.
    rec_out = holohub_root / "build" / "endoscopy_tool_tracking" / "recording_output"
    rec_out.mkdir(parents=True)

    # data dir + (fake) model file so the model-sha256 fingerprint has
    # something to hash. Not required for the wrapper to succeed but
    # exercises the drift-fingerprint code path. The upstream HoloHub
    # data manager places the ONNX directly under data/endoscopy/
    # (no model/ subdir) — verified against the real holohub@0eb7dcfb.
    data_dir = holohub_root / "data" / "endoscopy"
    data_dir.mkdir(parents=True)
    (data_dir / "tool_loc_convlstm.onnx").write_bytes(b"\x00stub_onnx_bytes\x00" * 64)

    stub = holohub_root / "holohub"
    stub.write_text(
        '#!/usr/bin/env bash\n'
        '# Stub HoloHub CLI for tests. Mirrors the real `./holohub run`\n'
        '# argparse, which accepts --language directly but takes app-level\n'
        '# flags via --run-args="...".\n'
        'shift  # eat "run"\n'
        'shift  # eat "endoscopy_tool_tracking"\n'
        'WROTE=0\n'
        f'WRITE_REC={"1" if write_recording else "0"}\n'
        f'REC_OUT="{rec_out}"\n'
        'RUN_ARGS=""\n'
        'while [[ $# -gt 0 ]]; do\n'
        '  case "$1" in\n'
        '    --local) shift ;;\n'
        '    --language) shift 2 ;;\n'
        '    --run-args=*) RUN_ARGS="${1#--run-args=}"; shift ;;\n'
        '    --run-args) RUN_ARGS="$2"; shift 2 ;;\n'
        '    *)  shift ;;\n'
        '  esac\n'
        'done\n'
        '# Parse forwarded app args out of RUN_ARGS so the stub can mimic\n'
        '# the upstream binary writing a recording when -r is input/visualizer.\n'
        'set -- $RUN_ARGS\n'
        'while [[ $# -gt 0 ]]; do\n'
        '  case "$1" in\n'
        '    -r)\n'
        '      RT="$2"\n'
        '      if [[ "$RT" == "input" || "$RT" == "visualizer" ]] && [[ "$WRITE_REC" == "1" ]]; then\n'
        '        printf "stub-recording" > "$REC_OUT/clip.gxf_index"\n'
        '        printf "stub-entities-bytes-payload" > "$REC_OUT/clip.gxf_entities"\n'
        '        cat > "$REC_OUT/tool_detections.jsonl" <<\'DETEOF\'\n'
        '{"frame": 0, "width": 640, "height": 480, "detections": [{"bbox": [100, 120, 80, 50], "class": "grasper", "score": 0.96}, {"bbox": [300, 90, 70, 95], "class": "scissors", "score": 0.91}]}\n'
        '{"frame": 1, "width": 640, "height": 480, "detections": [{"bbox": [110, 124, 82, 52], "class": "grasper", "score": 0.95}]}\n'
        '{"frame": 2, "width": 640, "height": 480, "detections": [{"bbox": [120, 130, 78, 51], "class": "grasper", "score": 0.94}]}\n'
        'DETEOF\n'
        '        WROTE=1\n'
        '      fi\n'
        '      shift 2 ;;\n'
        '    -s|-p|-c|-d) shift 2 ;;\n'
        '    *)  shift ;;\n'
        '  esac\n'
        'done\n'
        'echo "stub holohub run endoscopy_tool_tracking completed (wrote=$WROTE)"\n'
        'exit 0\n'
    )
    stub.chmod(0o755)

    # Make it a real git repo so holohub_commit fingerprint is non-empty.
    git = ["git", "-C", str(holohub_root),
           "-c", "user.email=test@x", "-c", "user.name=test",
           "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false"]
    subprocess.run(git + ["init", "-q"], check=True)
    subprocess.run(git + ["add", "-A"], check=True)
    subprocess.run(git + ["commit", "-q", "-m", "stub"], check=True)
    return holohub_root


def _run(fixture: Path | str, env: dict[str, str]) -> tuple[int, str, str]:
    full_env = os.environ.copy()
    full_env.update(env)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(fixture)],
        capture_output=True,
        text=True,
        env=full_env,
        timeout=120,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _payload(stdout: str) -> dict:
    return json.loads(stdout)


# ---------- error-path tests ----------

def test_missing_holohub_root_fails_with_clear_error() -> None:
    rc, out, err = _run("default", env={"HOLOHUB_ROOT": ""})
    assert rc == 2
    assert "HOLOHUB_ROOT" in err


def test_bad_holohub_root_without_holohub_script_fails(tmp_path: Path) -> None:
    bogus = tmp_path / "not-a-holohub-clone"
    bogus.mkdir()
    rc, out, err = _run("default", env={"HOLOHUB_ROOT": str(bogus)})
    assert rc == 2
    assert "./holohub" in err


def test_invalid_run_mode_fails(tmp_path: Path) -> None:
    holohub = _make_stub_holohub_root(tmp_path)
    rc, out, err = _run("default", env={
        "HOLOHUB_ROOT": str(holohub),
        "HOLOHUB_RUN_MODE": "bogus",
    })
    assert rc == 2
    assert "container|local" in err


def test_invalid_language_fails(tmp_path: Path) -> None:
    holohub = _make_stub_holohub_root(tmp_path)
    rc, out, err = _run("default", env={
        "HOLOHUB_ROOT": str(holohub),
        "HOLOHUB_LANGUAGE": "rust",
    })
    assert rc == 2
    assert "cpp|python" in err


def test_invalid_source_fails(tmp_path: Path) -> None:
    holohub = _make_stub_holohub_root(tmp_path)
    rc, out, err = _run("default", env={
        "HOLOHUB_ROOT": str(holohub),
        "HOLOHUB_SOURCE": "webcam",
    })
    assert rc == 2
    assert "replayer" in err


def test_invalid_record_type_fails(tmp_path: Path) -> None:
    holohub = _make_stub_holohub_root(tmp_path)
    rc, out, err = _run("default", env={
        "HOLOHUB_ROOT": str(holohub),
        "HOLOHUB_RECORD_TYPE": "everything",
    })
    assert rc == 2
    assert "input|visualizer" in err


def test_invalid_postprocessor_fails(tmp_path: Path) -> None:
    holohub = _make_stub_holohub_root(tmp_path)
    rc, out, err = _run("default", env={
        "HOLOHUB_ROOT": str(holohub),
        "HOLOHUB_POSTPROCESSOR": "yolo_postprocessor",
    })
    assert rc == 2
    assert "tool_tracking_postprocessor" in err


def test_missing_fixture_path_fails(tmp_path: Path) -> None:
    holohub = _make_stub_holohub_root(tmp_path)
    rc, out, err = _run("/no/such/fixture/dir", env={
        "HOLOHUB_ROOT": str(holohub),
    })
    assert rc == 2
    assert "fixture" in err.lower()


def test_fixture_must_be_directory(tmp_path: Path) -> None:
    holohub = _make_stub_holohub_root(tmp_path)
    not_a_dir = tmp_path / "stray_file.txt"
    not_a_dir.write_text("not a dir")
    rc, out, err = _run(not_a_dir, env={"HOLOHUB_ROOT": str(holohub)})
    assert rc == 2
    assert "directory" in err.lower() or "gxf" in err.lower()


def test_missing_config_path_fails(tmp_path: Path) -> None:
    holohub = _make_stub_holohub_root(tmp_path)
    rc, out, err = _run("default", env={
        "HOLOHUB_ROOT": str(holohub),
        "HOLOHUB_CONFIG": str(tmp_path / "no_such.yaml"),
    })
    assert rc == 2
    assert "HOLOHUB_CONFIG" in err


# ---------- full-integration tests using stub ./holohub ----------

def test_full_wrapper_with_stub_emits_well_formed_payload(tmp_path: Path) -> None:
    holohub = _make_stub_holohub_root(tmp_path)
    rc, out, err = _run("default", env={"HOLOHUB_ROOT": str(holohub)})
    assert rc == 0, f"wrapper exited {rc}: {err}"
    p = _payload(out)

    # Argv spec: ./holohub run endoscopy_tool_tracking --language ...
    # cpp mode does not forward -s/-r/-p because the upstream cpp binary
    # accepts source/record/postprocessor through its YAML config.
    cmd = p["invocation"]["command"]
    assert cmd[:3] == ["./holohub", "run", "endoscopy_tool_tracking"]
    assert "--language" in cmd
    assert cmd[cmd.index("--language") + 1] == "cpp"
    run_args = next(a for a in cmd if a.startswith("--run-args="))
    forwarded = shlex.split(run_args.removeprefix("--run-args="))
    assert forwarded == []

    # Stub exited cleanly.
    assert p["invocation"]["exit_code"] == 0

    # Defaults come through.
    assert p["invocation"]["mode"] == "container"
    assert p["invocation"]["language"] == "cpp"
    assert p["invocation"]["source"] == "replayer"
    assert p["invocation"]["record_type"] == "none"
    assert p["invocation"]["postprocessor"] == "tool_tracking_postprocessor"
    assert p["invocation"]["fixture"] == "default"

    # Drift fingerprints.
    assert p["invocation"]["holohub_commit"], "holohub_commit empty"
    # Stub model file's sha256 was captured.
    assert p["invocation"]["model_sha256"], "model_sha256 empty"

    # No recording when record_type=none.
    assert p["output"]["gxf"]["count"] == 0
    assert p["output"]["recording_file_count"] == 0
    assert p["output"]["recording_written_ok"] is True


def test_record_type_visualizer_picks_up_recording(tmp_path: Path) -> None:
    holohub = _make_stub_holohub_root(tmp_path)
    rc, out, err = _run("default", env={
        "HOLOHUB_ROOT": str(holohub),
        "HOLOHUB_LANGUAGE": "python",
        "HOLOHUB_RECORD_TYPE": "visualizer",
    })
    assert rc == 0, err
    p = _payload(out)
    assert p["invocation"]["record_type"] == "visualizer"
    cmd = p["invocation"]["command"]
    run_args = next(a for a in cmd if a.startswith("--run-args="))
    forwarded = shlex.split(run_args.removeprefix("--run-args="))
    assert forwarded[forwarded.index("-r") + 1] == "visualizer"
    # Stub wrote a .gxf_index + .gxf_entities pair.
    assert p["output"]["gxf"]["count"] == 2
    assert p["output"]["gxf"]["total_bytes"] > 0
    assert p["output"]["recording_file_count"] == 3
    assert p["output"]["recording_written_ok"] is True
    assert p["output"]["other"]["count"] >= 1
    assert p["detection_export"]["method"] == "existing_sidecar"


def test_record_type_visualizer_without_recording_sets_gate_false(tmp_path: Path) -> None:
    holohub = _make_stub_holohub_root(tmp_path, write_recording=False)
    rc, out, err = _run("default", env={
        "HOLOHUB_ROOT": str(holohub),
        "HOLOHUB_RECORD_TYPE": "visualizer",
    })
    assert rc == 0, err
    p = _payload(out)
    assert p["invocation"]["record_type"] == "visualizer"
    assert p["output"]["recording_file_count"] == 0
    assert p["output"]["recording_written_ok"] is False


def test_local_mode_adds_local_flag(tmp_path: Path) -> None:
    holohub = _make_stub_holohub_root(tmp_path)
    rc, out, err = _run("default", env={
        "HOLOHUB_ROOT": str(holohub),
        "HOLOHUB_RUN_MODE": "local",
        "HOLOHUB_LANGUAGE": "python",
    })
    assert rc == 0, err
    p = _payload(out)
    cmd = p["invocation"]["command"]
    assert "--local" in cmd
    assert p["invocation"]["mode"] == "local"
    assert p["invocation"]["language"] == "python"
    # Container image should be None in local mode (no docker fingerprint).
    assert p["invocation"]["container_image"] is None
    assert p["invocation"]["container_image_id"] is None


def test_custom_fixture_is_staged_into_data_endoscopy_video(tmp_path: Path) -> None:
    holohub = _make_stub_holohub_root(tmp_path)
    fixture = tmp_path / "my_clip"
    fixture.mkdir()
    (fixture / "my_clip.gxf_index").write_bytes(b"INDEX-PAYLOAD")
    (fixture / "my_clip.gxf_entities").write_bytes(b"ENTITIES-PAYLOAD")
    rc, out, err = _run(fixture, env={"HOLOHUB_ROOT": str(holohub)})
    assert rc == 0, err
    staged = holohub / "data" / "endoscopy" / "video"
    assert (staged / "my_clip.gxf_index").is_file()
    assert (staged / "my_clip.gxf_entities").is_file()
    p = _payload(out)
    assert p["invocation"]["fixture"] == str(fixture)


def test_stale_recording_is_wiped_before_each_run(tmp_path: Path) -> None:
    holohub = _make_stub_holohub_root(tmp_path)
    rec_dir = holohub / "build" / "endoscopy_tool_tracking" / "recording_output"
    sentinel = rec_dir / "stale_from_previous_run.gxf_index"
    sentinel.write_bytes(b"\x00" * 1000)
    rc, out, err = _run("default", env={"HOLOHUB_ROOT": str(holohub)})
    assert rc == 0, err
    assert not sentinel.exists(), "stale recording should have been wiped"


def test_fixture_default_does_not_touch_data_endoscopy_video(tmp_path: Path) -> None:
    # When --fixture is "default", we should NOT wipe data/endoscopy/video
    # (the upstream auto-fetch lives there). Plant a sentinel file and
    # confirm it survives.
    holohub = _make_stub_holohub_root(tmp_path)
    video_dir = holohub / "data" / "endoscopy" / "video"
    video_dir.mkdir(parents=True)
    sentinel = video_dir / "upstream_sample.gxf_index"
    sentinel.write_bytes(b"upstream-bundled-sample")
    rc, out, err = _run("default", env={"HOLOHUB_ROOT": str(holohub)})
    assert rc == 0, err
    assert sentinel.exists(), "default-fixture run must not touch data/endoscopy/video"


def test_recording_output_dir_override(tmp_path: Path) -> None:
    holohub = _make_stub_holohub_root(tmp_path)
    custom_out = tmp_path / "my_recordings"
    custom_out.mkdir()
    # Drop a file there before the run, the wrapper should wipe it.
    (custom_out / "stale.gxf_index").write_bytes(b"OLD")
    rc, out, err = _run("default", env={
        "HOLOHUB_ROOT": str(holohub),
        "HOLOHUB_RECORDING_OUTPUT_DIR": str(custom_out),
    })
    assert rc == 0, err
    p = _payload(out)
    assert p["invocation"]["recording_output_dir"] == str(custom_out)
    assert not (custom_out / "stale.gxf_index").exists()


def test_data_dir_override_is_passed_to_cli(tmp_path: Path) -> None:
    holohub = _make_stub_holohub_root(tmp_path)
    custom_data = tmp_path / "alt_data" / "endoscopy"
    custom_data.mkdir(parents=True)
    rc, out, err = _run("default", env={
        "HOLOHUB_ROOT": str(holohub),
        "HOLOHUB_DATA_DIR": str(custom_data),
    })
    assert rc == 0, err
    p = _payload(out)
    cmd = p["invocation"]["command"]
    run_args = next(a for a in cmd if a.startswith("--run-args="))
    forwarded = shlex.split(run_args.removeprefix("--run-args="))
    assert forwarded[forwarded.index("-d") + 1] == str(custom_data)
    assert p["invocation"]["data_dir"] == str(custom_data)


def test_config_path_is_passed_to_cli(tmp_path: Path) -> None:
    holohub = _make_stub_holohub_root(tmp_path)
    config_yaml = tmp_path / "my_config.yaml"
    config_yaml.write_text("# stub yaml\n")
    rc, out, err = _run("default", env={
        "HOLOHUB_ROOT": str(holohub),
        "HOLOHUB_CONFIG": str(config_yaml),
    })
    assert rc == 0, err
    p = _payload(out)
    cmd = p["invocation"]["command"]
    run_args = next(a for a in cmd if a.startswith("--run-args="))
    forwarded = shlex.split(run_args.removeprefix("--run-args="))
    forwarded_config = forwarded[forwarded.index("-c") + 1]
    assert forwarded_config == "/workspace/holohub/build/endoscopy_tool_tracking/workbench_configs/my_config.yaml"
    assert (holohub / "build" / "endoscopy_tool_tracking" / "workbench_configs" / "my_config.yaml").read_text() == "# stub yaml\n"
    assert p["invocation"]["config_path"] == str(config_yaml)


def test_local_config_path_is_passed_to_cli_verbatim(tmp_path: Path) -> None:
    holohub = _make_stub_holohub_root(tmp_path)
    config_yaml = tmp_path / "my_config.yaml"
    config_yaml.write_text("# stub yaml\n")
    rc, out, err = _run("default", env={
        "HOLOHUB_ROOT": str(holohub),
        "HOLOHUB_RUN_MODE": "local",
        "HOLOHUB_CONFIG": str(config_yaml),
    })
    assert rc == 0, err
    p = _payload(out)
    cmd = p["invocation"]["command"]
    run_args = next(a for a in cmd if a.startswith("--run-args="))
    forwarded = shlex.split(run_args.removeprefix("--run-args="))
    assert forwarded[forwarded.index("-c") + 1] == str(config_yaml)
    assert p["invocation"]["config_path"] == str(config_yaml)
