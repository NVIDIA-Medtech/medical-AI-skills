#!/usr/bin/env python3
"""TotalSegmentator (Wasserthal et al.) skill.

Thin wrapper around the official `totalsegmentator.python_api.totalsegmentator`
entrypoint from https://github.com/wasserth/TotalSegmentator. The wrapper does
NOT implement segmentation -- it invokes the Python API exactly as the
upstream README recommends:

    from totalsegmentator.python_api import totalsegmentator
    totalsegmentator(input_path, output_path, ml=True, task="total")

then reads the produced multilabel NIfTI to emit a structured summary.

Engineering verification only. Output is NOT clinically meaningful.
"""
from __future__ import annotations

import contextlib
import json
import os
import sys
import time
from pathlib import Path

import nibabel as nib
import numpy as np
import typer

SKILL_DIR = Path(__file__).resolve().parent.parent
GEOMETRY_TOLERANCE = float("1e-4")
SKILL_ID = "totalsegmentator"


@contextlib.contextmanager
def _stdout_to_stderr():
    """Redirect anything the wrapped package prints to its own stdout to
    stderr, so the eval_engine sees only the JSON we explicitly print at
    the end."""
    fd = sys.stdout.fileno()
    saved = os.dup(fd)
    try:
        os.dup2(sys.stderr.fileno(), fd)
        yield
    finally:
        os.dup2(saved, fd)
        os.close(saved)


def _resolve_device(requested: str) -> tuple[str, str]:
    """Return (totalsegmentator_device, resolved_device_for_evidence).

    TotalSegmentator's Python API accepts `device="gpu"|"cpu"|"mps"`. We
    translate auto/cuda → gpu for the wrapped call and keep the explicit
    `cuda`/`cpu` label in the evidence pack so it's diff-able against
    other CT-segmentation skills.
    """
    import torch  # local import; torch is a TotalSegmentator dep
    if requested == "auto":
        resolved = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        resolved = requested
    ts_device = "gpu" if resolved == "cuda" else resolved
    return ts_device, resolved


def _round_floats(values, ndigits: int = int("6")) -> list[float]:
    return [round(float(v), ndigits) for v in values]


def _input_summary(img: nib.spatialimages.SpatialImage) -> dict:
    zooms = img.header.get_zooms()[: len(img.shape)]
    return {
        "shape": [int(v) for v in img.shape],
        "ndim": len(img.shape),
        "spacing": _round_floats(zooms[:int("3")]),
    }


def _geometry_summary(
    input_img: nib.spatialimages.SpatialImage,
    output_img: nib.spatialimages.SpatialImage,
) -> dict:
    input_shape = [int(v) for v in input_img.shape]
    output_shape = [int(v) for v in output_img.shape]
    input_spacing = _round_floats(input_img.header.get_zooms()[:int("3")])
    output_spacing = _round_floats(output_img.header.get_zooms()[:int("3")])
    affine_max_abs_diff = float(np.max(np.abs(input_img.affine - output_img.affine)))
    return {
        "input_shape": input_shape,
        "output_shape": output_shape,
        "shape_match": input_shape == output_shape,
        "input_spacing": input_spacing,
        "output_spacing": output_spacing,
        "spacing_match": input_spacing == output_spacing,
        "affine_max_abs_diff": round(affine_max_abs_diff, int("8")),
        "affine_match": affine_max_abs_diff <= GEOMETRY_TOLERANCE,
    }


def _load_class_map(task: str) -> dict[int, str]:
    """Return {label_id: name} for a TotalSegmentator task.

    Uses upstream's canonical class map. Returns {} if the package is
    not importable (so a smoke-test path that doesn't actually invoke
    inference still works).
    """
    try:
        from totalsegmentator.map_to_binary import class_map  # type: ignore
    except Exception:
        return {}
    table = class_map.get(task) or {}
    return {int(k): str(v) for k, v in table.items()}


def _parse_roi_subset(value: str, class_map: dict[int, str]) -> list[int]:
    """Accept comma/space separated TotalSegmentator label IDs or class names."""
    if not value.strip():
        return []
    name_to_id = {
        name.lower().replace("-", "_").replace(" ", "_"): label_id
        for label_id, name in class_map.items()
    }
    tokens = [
        token.strip()
        for part in value.split(",")
        for token in part.split()
        if token.strip()
    ]
    requested: list[int] = []
    unknown: list[str] = []
    for token in tokens:
        if token.isdigit():
            requested.append(int(token))
            continue
        normalized = token.lower().replace("-", "_").replace(" ", "_")
        if normalized in name_to_id:
            requested.append(name_to_id[normalized])
        else:
            unknown.append(token)
    if unknown:
        examples = ", ".join(name_to_id.keys())
        raise typer.BadParameter(
            "unknown TotalSegmentator ROI name(s): "
            + ", ".join(unknown)
            + f". Use label IDs or task class names such as: {examples[:int("240")]}"
        )
    # Preserve user order while dropping duplicates.
    return list(dict.fromkeys(requested))


def _mask_summary(
    mask_path: Path,
    input_img: nib.spatialimages.SpatialImage,
    requested_label_ids: list[int],
    class_map: dict[int, str],
) -> dict:
    mask_img = nib.load(str(mask_path))
    arr = np.asarray(mask_img.get_fdata()).astype(np.int64)
    spacing = mask_img.header.get_zooms()[:int("3")]
    voxel_volume_ml = float(np.prod(spacing)) / float("1000.0")
    unique, counts = np.unique(arr, return_counts=True)

    # The "requested" set drives the subset check. If the caller did not
    # pass --roi-subset, we treat the full task class map as "requested"
    # so any unknown / out-of-range labels in the output land in
    # unexpected_label_ids.
    if requested_label_ids:
        requested = set(int(x) for x in requested_label_ids)
    else:
        requested = set(class_map.keys())

    class_counts: dict[str, int] = {}
    class_volumes_ml: dict[str, float] = {}
    label_ids_present: list[int] = []
    unexpected: list[int] = []
    for v, c in zip(unique.tolist(), counts.tolist()):
        label_id = int(v)
        if label_id == 0:
            continue
        label_ids_present.append(label_id)
        if requested and label_id not in requested:
            unexpected.append(label_id)
        name = class_map.get(label_id, f"label_id_{label_id}")
        class_counts[name] = int(c)
        class_volumes_ml[name] = round(int(c) * voxel_volume_ml, int("4"))

    return {
        "shape": [int(v) for v in arr.shape],
        "label_prompts_requested": sorted(requested) if requested_label_ids else [],
        "label_ids_present": sorted(label_ids_present),
        "unexpected_label_ids": sorted(unexpected),
        "label_set_valid": len(unexpected) == 0,
        "class_counts": class_counts,
        "voxel_volume_ml": round(voxel_volume_ml, int("8")),
        "class_volumes_ml": class_volumes_ml,
        "any_label_present": len(class_counts) > 0,
        "geometry": _geometry_summary(input_img, mask_img),
    }


def _empty_output_summary(input_summary: dict, requested: list[int]) -> dict:
    return {
        "path": None,
        "shape": [],
        "label_prompts_requested": sorted(set(int(x) for x in requested)),
        "label_ids_present": [],
        "unexpected_label_ids": [],
        "label_set_valid": False,
        "class_counts": {},
        "voxel_volume_ml": None,
        "class_volumes_ml": {},
        "any_label_present": False,
        "geometry": {
            "input_shape": input_summary["shape"],
            "output_shape": [],
            "shape_match": False,
            "input_spacing": input_summary["spacing"],
            "output_spacing": [],
            "spacing_match": False,
            "affine_max_abs_diff": None,
            "affine_match": False,
        },
    }


# Per-task weight licence tiers — mirrors skill_manifest.yaml
# license_restrictions.weights_per_task. Recorded in the evidence pack so
# downstream tooling can gate on it.
ACADEMIC_TASKS = frozenset({
    "heartchambers_highres", "appendicular_bones", "appendicular_bones_mr",
    "tissue_types", "tissue_types_mr", "tissue_4_types",
    "brain_structures", "vertebrae_body", "face", "face_mr",
    "thigh_shoulder_muscles", "thigh_shoulder_muscles_mr",
    "coronary_arteries", "aortic_sinuses", "brain_aneurysm",
})


def _task_license(task: str) -> str:
    return "academic_only" if task in ACADEMIC_TASKS else "non_commercial"


def _package_version() -> str | None:
    try:
        import totalsegmentator  # type: ignore
        return getattr(totalsegmentator, "__version__", None)
    except Exception:
        return None


app = typer.Typer(add_completion=False)


@app.command()
def main(
    nifti_path: Path = typer.Argument(..., exists=True, dir_okay=False),
    output_dir: Path = typer.Option(None, "--output-dir", "-o", help="dir for the multilabel mask"),
    task: str = typer.Option("total", "--task", help="TotalSegmentator task name (see upstream README)"),
    roi_subset: str = typer.Option(
        "",
        "--roi-subset",
        help=(
            "Optional comma/space-separated TotalSegmentator class IDs or "
            "class names to restrict inference and the subset check"
        ),
    ),
    device: str = typer.Option("auto", "--device", help="auto | cuda | cpu"),
    fast: bool = typer.Option(False, "--fast", help="Use TotalSegmentator's 3mm fast mode"),
    ground_truth: Path = typer.Option(
        None,
        "--ground-truth",
        exists=True,
        dir_okay=False,
        help=(
            "Optional reference label map. Recorded under input.ground_truth_path "
            "for downstream verifiers. The skill does not compute any GT metrics."
        ),
    ),
) -> None:
    """Run TotalSegmentator on a CT or MR NIfTI volume."""
    if output_dir is None:
        stem = nifti_path.name
        for suffix in (".nii.gz", ".nii"):
            if stem.endswith(suffix):
                stem = stem[: -len(suffix)]
                break
        output_dir = nifti_path.parent / f"{stem}_totalseg_out"
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    mask_path = output_dir / f"{nifti_path.stem.split('.')[0]}_totalseg.nii.gz"

    class_map = _load_class_map(task)
    requested_ids = _parse_roi_subset(roi_subset, class_map)

    ts_device, resolved_device = _resolve_device(device)

    try:
        from totalsegmentator.python_api import totalsegmentator  # type: ignore
    except ModuleNotFoundError as e:
        result = {
            "skill": SKILL_ID,
            "error": "TotalSegmentator package is not installed",
            "detail": str(e),
            "install_command": "pip install TotalSegmentator",
        }
        print(json.dumps(result, indent=2))
        raise typer.Exit(2)

    api_kwargs = {
        "ml": True,
        "task": task,
        "device": ts_device,
        "fast": fast,
        "quiet": True,
    }
    if requested_ids:
        api_kwargs["roi_subset"] = [class_map[i] for i in requested_ids if i in class_map] or None

    with _stdout_to_stderr():
        t0 = time.perf_counter()
        totalsegmentator(str(nifti_path), str(mask_path), **api_kwargs)
        t_inf = time.perf_counter() - t0

    input_img = nib.load(str(nifti_path))
    input_summary = _input_summary(input_img)
    if mask_path.exists():
        output_summary = _mask_summary(mask_path, input_img, requested_ids, class_map)
        output_summary["path"] = str(mask_path)
    else:
        output_summary = _empty_output_summary(input_summary, requested_ids)

    result = {
        "skill": SKILL_ID,
        "model": "TotalSegmentator (Wasserthal et al.)",
        "model_repo": "https://github.com/wasserth/TotalSegmentator",
        "package_version": _package_version(),
        "task": task,
        "task_license": _task_license(task),
        "license": "Apache-2.0 (code); weights per task — see task_license",
        "input": {
            "path": str(nifti_path),
            **input_summary,
            "ground_truth_path": str(ground_truth) if ground_truth is not None else None,
        },
        "output": output_summary,
        "invocation": {
            "python_api": "totalsegmentator.python_api.totalsegmentator",
            "ml": True,
            "fast": fast,
            "roi_subset_class_ids": requested_ids,
        },
        "runtime": {
            "inference_seconds": round(t_inf, int("3")),
            "device": resolved_device,
            "ts_device_arg": ts_device,
        },
        "intended_use_disclaimer": (
            "Engineering verification only. Output is NOT clinically meaningful. "
            "This wrapper invokes the official totalsegmentator.python_api; it "
            "does not modify inference."
        ),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    app()
