"""NAT function wrappers for every committed Medical AI Skills skill.

Each function shells out to the existing skill entrypoint exactly as the
skill's SKILL.md / scripts/* documents. No reimplementation. The wrapper
returns a small JSON summary so the agent's reasoning stays cheap.

The NAT profiler tracks the agent's LLM calls (input/output tokens) at the
workflow level. Per-skill totals are sliced from
``standardized_data_all.csv`` by ``example_number``.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

from pydantic import Field

from nat.builder.builder import Builder
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.function import FunctionBaseConfig

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLS = REPO_ROOT / "skills"
SKILL_PYTHON = os.environ.get("MEDICAL_AI_SKILLS_SKILL_PYTHON", sys.executable)
READ_FILE_MAX_CHARS = 16000  # ~4000 tokens; covers a typical SKILL.md
LIST_DIR_MAX_ENTRIES = 100


# --- generic filesystem tools (so the agent can do what a real user would) ---

class ReadFileConfig(FunctionBaseConfig, name="read_file"):
    pass


@register_function(config_type=ReadFileConfig)
async def read_file(_config, _builder) -> AsyncGenerator[FunctionInfo, None]:
    async def _fn(path: str) -> str:
        try:
            p = Path(path).expanduser().resolve()
            if not p.is_file():
                return json.dumps({"error": "not a file", "path": str(p)})
            text = p.read_text(errors="replace")
            truncated = len(text) > READ_FILE_MAX_CHARS
            if truncated:
                text = text[:READ_FILE_MAX_CHARS]
            return json.dumps({
                "path": str(p), "truncated": truncated,
                "size_chars": p.stat().st_size, "content": text,
            })
        except Exception as e:
            return json.dumps({"error": type(e).__name__, "message": str(e)})

    yield FunctionInfo.from_fn(_fn, description=(
        "Read a local text file (e.g. a skill's SKILL.md, an output.json, a "
        "fixture). Returns JSON with content (truncated to "
        f"{READ_FILE_MAX_CHARS} chars) and the file size."
    ))


class ListDirectoryConfig(FunctionBaseConfig, name="list_directory"):
    pass


@register_function(config_type=ListDirectoryConfig)
async def list_directory(_config, _builder) -> AsyncGenerator[FunctionInfo, None]:
    async def _fn(path: str) -> str:
        try:
            p = Path(path).expanduser().resolve()
            if not p.is_dir():
                return json.dumps({"error": "not a directory", "path": str(p)})
            entries = []
            for child in sorted(p.iterdir())[:LIST_DIR_MAX_ENTRIES]:
                kind = "dir" if child.is_dir() else "file"
                size = child.stat().st_size if child.is_file() else None
                entries.append({"name": child.name, "kind": kind, "size": size})
            return json.dumps({
                "path": str(p), "n_entries": len(entries),
                "truncated": len(list(p.iterdir())) > LIST_DIR_MAX_ENTRIES,
                "entries": entries,
            })
        except Exception as e:
            return json.dumps({"error": type(e).__name__, "message": str(e)})

    yield FunctionInfo.from_fn(_fn, description=(
        "List entries in a local directory. Returns JSON with name, kind "
        "(file|dir), and size for each entry (max "
        f"{LIST_DIR_MAX_ENTRIES}). Useful for inspecting a dataset before "
        "deciding which skill to invoke."
    ))


def _short_err(stderr: str, n: int = 400) -> str:
    return stderr[-n:] if stderr else ""


def _summarize_finetune(stdout: str) -> str:
    try:
        r = json.loads(stdout)
    except json.JSONDecodeError:
        return json.dumps({"error": "not-json", "stdout_tail": stdout[-400:]})
    return json.dumps({
        "preset": r.get("plan", {}).get("preset"),
        "return_code": r.get("runtime", {}).get("return_code"),
        "wall_seconds": r.get("runtime", {}).get("wall_seconds"),
        "best_val_dice": r.get("output", {}).get("best_val_dice"),
        "oom": r.get("output", {}).get("oom"),
    })


def _run(cmd: list[str], env_extra: dict[str, str] | None = None,
         timeout: int = 600) -> dict:
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          timeout=timeout, env=env)
    return {
        "rc": proc.returncode,
        "stdout": proc.stdout,
        "stderr_tail": _short_err(proc.stderr),
    }


# --- finetune_smoke (already used in initial validation) -----------------------

class FinetuneSmokeConfig(FunctionBaseConfig, name="finetune_smoke"):
    output_dir: str = Field(default="runs/nat_smoke")


@register_function(config_type=FinetuneSmokeConfig)
async def finetune_smoke(config: FinetuneSmokeConfig, _builder: Builder) -> AsyncGenerator[FunctionInfo, None]:
    async def _fn(unused: str = "") -> str:
        out_dir = (REPO_ROOT / config.output_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        r = _run([
            SKILL_PYTHON,
            str(SKILLS / "nv-segment-ct-finetune/scripts/run_finetune.py"),
            "--smoke", "--output-dir", str(out_dir),
        ], timeout=300)
        if r["rc"] != 0:
            return json.dumps({"error": "failed", **r})
        return _summarize_finetune(r["stdout"])

    yield FunctionInfo.from_fn(_fn, description=(
        "Run the nv_segment_ct_finetune smoke preset (1 iter on bundled "
        "spleen_micro, ~30 s, GPU). Returns JSON with return_code, wall_seconds, "
        "best_val_dice, oom."
    ))


# --- dicom_metadata_extract ----------------------------------------------------

class DicomMetaConfig(FunctionBaseConfig, name="dicom_meta_extract"):
    pass


@register_function(config_type=DicomMetaConfig)
async def dicom_meta_extract(_config, _builder) -> AsyncGenerator[FunctionInfo, None]:
    async def _fn(unused: str = "") -> str:
        r = _run([
            SKILL_PYTHON,
            str(SKILLS / "dicom-metadata-extract/scripts/extract_metadata.py"),
            str(SKILLS / "dicom-metadata-extract/fixtures/sample_ct.dcm"),
        ], timeout=60)
        if r["rc"] != 0:
            return json.dumps({"error": "failed", **r})
        try:
            j = json.loads(r["stdout"])
            return json.dumps({"return_code": 0,
                               "patient_keys": list(j.get("patient", {}).keys())[:5],
                               "modality": j.get("study", {}).get("modality")})
        except Exception:
            return json.dumps({"return_code": 0, "stdout_head": r["stdout"][:200]})

    yield FunctionInfo.from_fn(_fn, description=(
        "Extract DICOM metadata via pydicom from the sample CT fixture. "
        "Returns return_code and a short summary."
    ))


# --- dicom_series_to_volume ----------------------------------------------------

class DicomSeriesConfig(FunctionBaseConfig, name="dicom_series_to_volume"):
    pass


@register_function(config_type=DicomSeriesConfig)
async def dicom_series_to_volume(_config, _builder) -> AsyncGenerator[FunctionInfo, None]:
    async def _fn(unused: str = "") -> str:
        out_dir = REPO_ROOT / "runs" / "nat_dicom_series"
        out_dir.mkdir(parents=True, exist_ok=True)
        r = _run([
            SKILL_PYTHON,
            str(SKILLS / "dicom-series-to-volume/scripts/series_to_volume.py"),
            str(SKILLS / "dicom-series-to-volume/fixtures/clean_axial"),
            "--output", str(out_dir / "vol.nii.gz"),
        ], timeout=120)
        return json.dumps({"return_code": r["rc"], "stderr_tail": r["stderr_tail"][:200]})

    yield FunctionInfo.from_fn(_fn, description=(
        "Convert the bundled clean_axial DICOM series fixture to a NIfTI volume. "
        "Returns return_code."
    ))

# --- nv_segment_ct (VISTA3D) ---------------------------------------------------

class NvSegmentCtConfig(FunctionBaseConfig, name="nv_segment_ct"):
    pass


@register_function(config_type=NvSegmentCtConfig)
async def nv_segment_ct_fn(_config, _builder) -> AsyncGenerator[FunctionInfo, None]:
    async def _fn(unused: str = "") -> str:
        out_dir = REPO_ROOT / "runs" / "nat_vista3d"
        out_dir.mkdir(parents=True, exist_ok=True)
        r = _run([
            SKILL_PYTHON,
            str(SKILLS / "nv-segment-ct/scripts/run_vista3d.py"),
            str(SKILLS / "nv-segment-ct/fixtures/spleen_03.nii.gz"),
            "--output-dir", str(out_dir),
        ], timeout=600)
        try:
            j = json.loads(r["stdout"])
            return json.dumps({
                "return_code": r["rc"],
                "wall_seconds": j.get("runtime", {}).get("wall_seconds"),
                "n_masks": len(j.get("output", {}).get("masks", [])),
            })
        except Exception:
            return json.dumps({"return_code": r["rc"],
                               "stderr_tail": r["stderr_tail"][:200]})

    yield FunctionInfo.from_fn(_fn, description=(
        "Run NV-Segment-CT (VISTA3D) on the bundled spleen_03 NIfTI fixture. "
        "Returns return_code, wall_seconds, n_masks."
    ))
