#!/usr/bin/env python3
"""Run the canonical HoloHub `imaging_ai_segmentator` app via its native CLI.

This script is intentionally a *thin wrapper*. It cd's to the holohub root,
invokes `./holohub run imaging_ai_segmentator`, scans the output dir, and
prints a JSON evidence payload to stdout for the eval_engine.

Conventions used by `eval_engine/run.py`:
  * argv[1] is the fixture path (a DICOM directory). May be the literal
    string "default" to indicate "use whatever HoloHub provisioned at
    $HOLOHUB_ROOT/data/imaging_ai_segmentator/dicom".
  * Configuration is taken from environment variables so the eval_engine's
    fixed `[python, script, fixture]` invocation pattern still works:
      HOLOHUB_ROOT          required, path to a clone of HoloHub
      HOLOHUB_RUN_MODE      "container" (default) or "local"
      HOLOSCAN_OUTPUT_PATH  optional override for app output dir
      HOLOSCAN_MODEL_PATH   optional override for model dir
      HOLOHUB_TIMEOUT_SECONDS  default 1800
  * JSON payload printed to stdout. The script exits 0 whenever it can
    produce a payload, even if the holohub run itself failed -- the
    failure is recorded in `invocation.exit_code` so the eval_engine's
    sanity gate can fire on it.

This script does NOT reimplement DICOM loading, MONAI inference, or DICOM
SEG writing. Those live inside the HoloHub application; this is a verifier
that runs the canonical entry point and inspects results.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_SKILLS_DIR = _SCRIPT_DIR.parent.parent
if str(_SKILLS_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILLS_DIR))
from _shared.docker_capture import capture_container_provenance  # noqa: E402
from _shared.wrapper_utils import (  # noqa: E402
    collect_group,
    docker_image_id,
    emit,
    fail_with,
    git_commit,
    sha256_file,
    tail,
)


APP_TIME_PATTERNS = [
    re.compile(r"inference (?:took|time)[^0-9]*([0-9]+\.?[0-9]*)\s*s", re.I),
    re.compile(r"app(?:lication)? (?:took|time)[^0-9]*([0-9]+\.?[0-9]*)\s*s", re.I),
    re.compile(r"execution_time[^0-9]*([0-9]+\.?[0-9]*)", re.I),
]

# The MONAI segmentation operator prints the maximum label value of the
# output mask. If the value is 0 the segmentation is empty (every voxel
# was assigned to the background class) -- this is the canonical silent
# failure when input anatomy does not match what the model was trained
# on, or when the input volume is too small / cropped.
SEG_MAX_PATTERN = re.compile(
    r"Output Seg image pixel max value:\s*([0-9]+)", re.I
)
SEG_SHAPE_PATTERN = re.compile(
    r"Output Seg image numpy array shaped:\s*\(([^)]+)\)", re.I
)
EMPTY_SEG_WARN_PATTERN = re.compile(
    r"Encoding an empty segmentation", re.I
)


def parse_app_seconds(stdout: str, stderr: str) -> float | None:
    for source in (stdout, stderr):
        for pat in APP_TIME_PATTERNS:
            m = pat.search(source)
            if m:
                try:
                    return float(m.group(1))
                except ValueError:
                    continue
    return None


def parse_seg_signals(stdout: str, stderr: str) -> dict[str, Any]:
    text = stdout + "\n" + stderr
    out: dict[str, Any] = {
        "seg_pixel_max_value": None,
        "seg_array_shape": None,
        "empty_segmentation_warning": False,
    }
    m = SEG_MAX_PATTERN.search(text)
    if m:
        try:
            out["seg_pixel_max_value"] = int(m.group(1))
        except ValueError:
            pass
    m = SEG_SHAPE_PATTERN.search(text)
    if m:
        try:
            out["seg_array_shape"] = [
                int(x.strip()) for x in m.group(1).split(",") if x.strip()
            ]
        except ValueError:
            pass
    if EMPTY_SEG_WARN_PATTERN.search(text):
        out["empty_segmentation_warning"] = True
    return out


def scan_output(output_root: Path) -> dict[str, Any]:
    if not output_root.exists():
        return {
            "dicom_seg": {"count": 0, "total_bytes": 0, "files": []},
            "nifti": {
                "original": {"count": 0, "total_bytes": 0, "files": []},
                "segmentation": {"count": 0, "total_bytes": 0, "files": []},
            },
        }

    # The HoloHub app writes:
    #   <output>/<seg-uid>.dcm                      (DICOM SEG)
    #   <output>/saved_images_folder/<series>/<series>.nii      (original)
    #   <output>/saved_images_folder/<series>/<series>_seg.nii  (segmentation)
    dicom_seg_files = sorted(output_root.glob("*.dcm"))

    saved = output_root / "saved_images_folder"
    original_niftis: list[Path] = []
    segmentation_niftis: list[Path] = []
    if saved.exists():
        for nii in sorted(saved.rglob("*.nii*")):
            name = nii.name
            if name.endswith("_seg.nii") or name.endswith("_seg.nii.gz"):
                segmentation_niftis.append(nii)
            else:
                original_niftis.append(nii)

    return {
        "dicom_seg": collect_group(dicom_seg_files, output_root),
        "nifti": {
            "original": collect_group(original_niftis, output_root),
            "segmentation": collect_group(segmentation_niftis, output_root),
        },
    }


def stage_container_input(holohub_root: Path, input_path: str) -> None:
    """Stage the requested input where the HoloHub container expects it."""
    if not input_path:
        return

    staged_input = holohub_root / "data" / "imaging_ai_segmentator" / "dicom"
    # Wipe the entire staged_input subtree so HoloHub's auto-fetched brain
    # DICOM cannot compete with the caller's fixture during recursive scans.
    if staged_input.exists():
        shutil.rmtree(staged_input)
    staged_input.mkdir(parents=True, exist_ok=True)

    src = Path(input_path)
    if src.is_dir():
        for f in src.iterdir():
            if f.is_file():
                shutil.copy2(f, staged_input / f.name)
        return
    shutil.copy2(src, staged_input / src.name)


def copy_container_output_back(holohub_root: Path, output_path: Path) -> None:
    """Copy container-mode output from HoloHub's default path to output_path."""
    staged_output_local = holohub_root / "build" / "imaging_ai_segmentator" / "output"
    if not staged_output_local.exists() or staged_output_local.resolve() == output_path.resolve():
        return

    for entry in staged_output_local.iterdir():
        dst = output_path / entry.name
        if entry.is_file():
            if dst.exists():
                dst.unlink()
            shutil.copy2(entry, dst)
            continue
        if entry.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(entry, dst)


def main() -> int:
    fixture_arg = sys.argv[1] if len(sys.argv) > 1 else "default"

    holohub_root_str = os.environ.get("HOLOHUB_ROOT", "").strip()
    if not holohub_root_str:
        sys.stderr.write("HOLOHUB_ROOT env var is required\n")
        return 2
    holohub_root = Path(holohub_root_str).expanduser().resolve()
    if not (holohub_root / "holohub").exists():
        sys.stderr.write(f"HOLOHUB_ROOT={holohub_root} has no ./holohub script\n")
        return 2

    mode = os.environ.get("HOLOHUB_RUN_MODE", "container").strip() or "container"
    if mode not in ("container", "local"):
        sys.stderr.write(f"HOLOHUB_RUN_MODE must be container|local, got {mode!r}\n")
        return 2

    timeout_s = float(os.environ.get("HOLOHUB_TIMEOUT_SECONDS", "1800"))

    if fixture_arg == "default":
        input_path = ""
    else:
        input_path = str(Path(fixture_arg).expanduser().resolve())

    output_path_env = os.environ.get("HOLOSCAN_OUTPUT_PATH", "").strip()
    if output_path_env:
        output_path = Path(output_path_env).expanduser().resolve()
    else:
        output_path = holohub_root / "build" / "imaging_ai_segmentator" / "output"
    output_path.mkdir(parents=True, exist_ok=True)

    # Clean stale outputs from a previous run so we don't false-positive
    # on a sanity check by inheriting last run's DICOM SEG.
    for entry in output_path.iterdir():
        if entry.is_file():
            entry.unlink()
        elif entry.is_dir():
            shutil.rmtree(entry)

    model_path_env = os.environ.get("HOLOSCAN_MODEL_PATH", "").strip()
    model_path = Path(model_path_env).expanduser().resolve() if model_path_env else None

    env = os.environ.copy()
    if input_path:
        env["HOLOSCAN_INPUT_PATH"] = input_path
    env["HOLOSCAN_OUTPUT_PATH"] = str(output_path)
    if model_path:
        env["HOLOSCAN_MODEL_PATH"] = str(model_path)

    cmd: list[str] = ["./holohub", "run", "imaging_ai_segmentator"]
    # `imaging_ai_segmentator/CMakeLists.txt` has `option(HOLOHUB_DOWNLOAD_DATASETS "..." ON)`
    # which on every cmake configure (i.e. every `./holohub run`) (re-)fetches
    # both the MONAI TotalSegmentator model and CT_DICOM_SINGLE.zip, the
    # latter dropping a single-slice "Routine Brain" DICOM into
    # data/imaging_ai_segmentator/dicom/imaging_ai_segmentator/CT_DICOM_SINGLE/
    # — which the StudyLoader's recursive scan then picks up alongside the
    # caller's fixture. The model.pt is small (72 MB) and conventionally
    # left in place after first build, so disabling the download option on
    # subsequent runs is safe and prevents the brain DICOM from coming
    # back. The eval_engine documents the first-run requirement in SKILL.md.
    # HoloHub's argparse rejects `-D...` as a separate token because it
    # looks like a flag; use the `=` form so the dash prefix stays
    # attached to the option value.
    cmd += ["--configure-args=-DHOLOHUB_DOWNLOAD_DATASETS=OFF"]
    if mode == "local":
        cmd += ["--local", "--language", "python"]
    else:
        # Container mode: ./holohub run does NOT propagate host env vars
        # like HOLOSCAN_INPUT_PATH / HOLOSCAN_OUTPUT_PATH into the
        # container, and HoloHub's --add-volume always mounts to
        # /workspace/volumes/<basename> (it does not accept host:container
        # syntax). The reliable convention is to stage the input under
        # the HoloHub clone's own data/ tree (which is bind-mounted to
        # /workspace/holohub) at the application's default location:
        #
        #     <HOLOHUB_ROOT>/data/imaging_ai_segmentator/dicom/
        #
        # The wrapper copies the caller's fixture there so the container
        # picks it up via the Dockerfile's HOLOSCAN_INPUT_PATH default.
        # Output stays in <HOLOHUB_ROOT>/build/imaging_ai_segmentator/
        # output/ (also visible via the workspace mount).
        stage_container_input(holohub_root, input_path)
        # Container's default output is <HOLOHUB_ROOT>/build/.../output;
        # remap our requested output_path to that location for the run,
        # then copy results back at the end. Wipe stale results so a
        # previous run's DICOM SEG / NIfTI does not bleed into this run's
        # evidence pack via the post-run copy.
        staged_output = holohub_root / "build" / "imaging_ai_segmentator" / "output"
        if staged_output.exists():
            shutil.rmtree(staged_output)
        staged_output.mkdir(parents=True, exist_ok=True)

    container_image = "holohub-imaging_ai_segmentator:main" if mode == "container" else None

    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(holohub_root),
            env=env,
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
    elapsed = time.monotonic() - t0

    if mode == "container" and container_image:
        container_image_id_val = docker_image_id(container_image)
        try:
            container_provenance = capture_container_provenance(container_image)
        except Exception as e:
            container_provenance = {"status": "failed", "reason": repr(e)}
    else:
        container_provenance = {"status": "skipped", "reason": "not container mode"}

    # Container mode wrote results into the holohub workspace's default
    # output path; copy them back to the caller-requested output path so
    # scan_output() and the eval_engine can find them.
    if mode == "container":
        try:
            copy_container_output_back(holohub_root, output_path)
        except Exception as e:
            sys.stderr.write(f"warning: failed to copy staged output back: {e}\n")

    payload: dict[str, Any] = {
        "invocation": {
            "holohub_root": str(holohub_root),
            "holohub_commit": git_commit(holohub_root),
            "mode": mode,
            "command": cmd,
            "exit_code": rc,
            "container_image": container_image,
            "container_image_id": container_image_id_val if mode == "container" else None,
            "container_provenance": container_provenance,
            "input_path": env.get("HOLOSCAN_INPUT_PATH", ""),
            "output_path": env.get("HOLOSCAN_OUTPUT_PATH", ""),
            "model_path": env.get("HOLOSCAN_MODEL_PATH", "") or None,
        },
        "output": {
            **scan_output(output_path),
            "seg_signals": parse_seg_signals(stdout, stderr),
        },
        "runtime": {
            "subprocess_seconds": elapsed,
            "app_seconds": parse_app_seconds(stdout, stderr),
        },
        "logs": {
            "stdout_tail": tail(stdout),
            "stderr_tail": tail(stderr),
        },
    }

    emit(payload)
    # Always exit 0 if we produced a payload -- the eval_engine can read it
    # and the sanity gate will fire on `invocation.exit_code != 0` if
    # the holohub run itself failed. This keeps the gate uniform.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
