#!/usr/bin/env python3
"""Verify NV-Generate-MR image-only evidence packs."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from verifiers._shared.verifier_kit import (  # noqa: E402
    load_pack_json,
    make_check,
    resolve_pack_artifact,
    run_grader,
)

VERIFIER_ID = "medagent.verifiers.mr_synthesis_quality_v1"
VERIFIER_VERSION = "0.1.0"
TARGET_SKILL_IDS = {
    "medagent.nv_generate_mr",
    "nv_generate_mr",
    "medagent.nv_generate_mr_brain",
    "nv_generate_mr_brain",
}
OUTPUT_SKILL_TO_VERSION = {
    "nv_generate_mr": "rflow-mr",
    "nv_generate_mr_brain": "rflow-mr-brain",
}
SUPPORTED_MODALITIES = {"mri", "mri_t1", "mri_t2", "mri_flair"}


def _public_path(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        resolved = path.resolve()
    except (OSError, ValueError):
        return str(path)
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def _positive_shape(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 3
        and all(isinstance(item, int) and item > 0 for item in value)
    )


def _positive_spacing(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 3
        and all(isinstance(item, (int, float)) and item > 0 for item in value)
    )


def _spacing_close(left: list[float], right: list[float], *, tol: float = 1e-4) -> bool:
    return len(left) == len(right) and all(abs(float(a) - float(b)) <= tol for a, b in zip(left, right))


def _resolve_image_path(pack_dir: Path, raw: Any) -> Path | None:
    if not isinstance(raw, str) or not raw:
        return None
    return resolve_pack_artifact(pack_dir, raw, REPO_ROOT)


def _sha256_path(path: Path | None) -> str | None:
    if path is None:
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _recompute_image(pack_dir: Path, sample: dict[str, Any], requested_shape: list[int], requested_spacing: list[float]) -> dict[str, Any]:
    path = _resolve_image_path(pack_dir, sample.get("image_path"))
    record: dict[str, Any] = {
        "declared_path": sample.get("image_path"),
        "resolved_path": _public_path(path) if path is not None else None,
        "exists": bool(path is not None and path.is_file()),
        "image_bytes": path.stat().st_size if path is not None and path.is_file() else None,
        "image_sha256": _sha256_path(path) if path is not None and path.is_file() else None,
        "readable": False,
    }
    if path is None or not path.is_file():
        return record
    try:
        img = nib.load(str(path))
        arr = np.asarray(img.get_fdata(), dtype=np.float32)
        finite = arr[np.isfinite(arr)]
    except Exception as exc:
        record["error"] = repr(exc)
        return record
    record["readable"] = True
    record["shape"] = [int(v) for v in arr.shape]
    record["spacing"] = [round(float(v), 6) for v in img.header.get_zooms()[:3]]
    record["shape_match_requested"] = record["shape"] == requested_shape
    record["spacing_match_requested"] = _spacing_close(record["spacing"], requested_spacing)
    record["finite_fraction"] = round(float(finite.size / arr.size), 6) if arr.size else 0.0
    record["all_finite"] = bool(arr.size and finite.size == arr.size)
    if finite.size:
        record["intensity_min"] = round(float(finite.min()), 6)
        record["intensity_max"] = round(float(finite.max()), 6)
        record["intensity_mean"] = round(float(finite.mean()), 6)
        record["intensity_std"] = round(float(finite.std()), 6)
        record["image_nonconstant"] = bool(float(finite.max() - finite.min()) > 1.0)
        record["image_nonnegative"] = bool((finite >= 0).all())
    else:
        record["image_nonconstant"] = False
        record["image_nonnegative"] = False
    return record


def _scope_disclosed(output_payload: dict[str, Any]) -> bool:
    text = str(output_payload.get("intended_use_disclaimer") or "").lower()
    return "engineering" in text and (
        "not clinically meaningful" in text or "not clinical" in text
    )


def grade(pack_dir: Path) -> dict[str, Any]:
    pack_dir = pack_dir.resolve()
    output_payload = load_pack_json(pack_dir, "output.json")
    validation = load_pack_json(pack_dir, "validation_summary.json")
    manifest = load_pack_json(pack_dir, "manifest.json")

    skill_id = str(manifest.get("skill_id") or output_payload.get("skill") or "")
    output_skill = str(output_payload.get("skill") or "")
    input_payload = output_payload.get("input") or {}
    output = output_payload.get("output") or {}
    invocation = output_payload.get("invocation") or {}
    runtime = output_payload.get("runtime") or {}
    samples = output.get("samples") if isinstance(output.get("samples"), list) else []
    requested_shape = input_payload.get("dim_requested")
    requested_spacing = input_payload.get("spacing_requested")
    requested_shape = requested_shape if _positive_shape(requested_shape) else []
    requested_spacing = requested_spacing if _positive_spacing(requested_spacing) else []
    image_records = [
        _recompute_image(pack_dir, sample, requested_shape, requested_spacing)
        for sample in samples
        if isinstance(sample, dict)
    ]

    all_readable = bool(image_records) and all(item.get("readable") for item in image_records)
    all_shape = bool(image_records) and all(item.get("shape_match_requested") for item in image_records)
    all_spacing = bool(image_records) and all(item.get("spacing_match_requested") for item in image_records)
    all_finite = bool(image_records) and all(item.get("all_finite") for item in image_records)
    all_nonconstant = bool(image_records) and all(item.get("image_nonconstant") for item in image_records)
    all_nonnegative = bool(image_records) and all(item.get("image_nonnegative") for item in image_records)
    expected_version = OUTPUT_SKILL_TO_VERSION.get(output_skill)

    checks = [
        make_check("target_skill_matches", skill_id in TARGET_SKILL_IDS, f"skill_id={skill_id!r}"),
        make_check(
            "source_pack_passed",
            validation.get("overall_status") == "passed",
            f"source pack overall={validation.get('overall_status')!r}",
        ),
        make_check(
            "output_skill_supported",
            output_skill in OUTPUT_SKILL_TO_VERSION,
            f"output.skill={output_skill!r}",
        ),
        make_check(
            "version_matches_skill",
            expected_version is not None and input_payload.get("version") == expected_version,
            f"input.version={input_payload.get('version')!r}, expected={expected_version!r}",
        ),
        make_check(
            "modality_supported",
            input_payload.get("modality_name") in SUPPORTED_MODALITIES
            and isinstance(input_payload.get("modality_code"), int),
            f"modality={input_payload.get('modality_name')!r}, code={input_payload.get('modality_code')!r}",
        ),
        make_check(
            "official_entrypoint_matches",
            invocation.get("official_entrypoint") == "python -m scripts.diff_model_infer",
            f"official_entrypoint={invocation.get('official_entrypoint')!r}",
        ),
        make_check(
            "subprocess_succeeded",
            invocation.get("exit_code") == 0,
            f"exit_code={invocation.get('exit_code')!r}",
        ),
        make_check(
            "model_inventory_present",
            bool((invocation.get("model_inventory") or {}).get("all_present")),
            f"model_inventory.all_present={(invocation.get('model_inventory') or {}).get('all_present')!r}",
        ),
        make_check(
            "samples_declared",
            isinstance(output.get("num_samples"), int)
            and output.get("num_samples") == len(samples)
            and len(samples) >= 1,
            f"num_samples={output.get('num_samples')!r}, samples={len(samples)}",
        ),
        make_check(
            "image_artifacts_readable",
            all_readable,
            f"readable={sum(1 for item in image_records if item.get('readable'))}/{len(image_records)}",
            images=image_records,
        ),
        make_check(
            "image_shapes_match_requested",
            all_shape,
            f"requested_shape={requested_shape!r}",
        ),
        make_check(
            "image_spacing_matches_requested",
            all_spacing,
            f"requested_spacing={requested_spacing!r}",
        ),
        make_check(
            "image_values_finite",
            all_finite,
            "all image voxels must be finite",
        ),
        make_check(
            "image_values_nonconstant",
            all_nonconstant,
            "all images must have non-trivial intensity variation",
        ),
        make_check(
            "image_values_nonnegative",
            all_nonnegative,
            "MR synthesis wrapper reports post-decoded nonnegative intensity volumes",
        ),
        make_check(
            "aggregate_flags_match_recomputed",
            output.get("all_images_readable") is all_readable
            and output.get("all_shapes_match_requested") is all_shape
            and output.get("all_spacing_match_requested") is all_spacing
            and output.get("all_images_finite") is all_finite
            and output.get("all_images_nonconstant") is all_nonconstant
            and output.get("all_images_nonnegative") is all_nonnegative,
            "output aggregate flags must match verifier recomputation",
        ),
        make_check(
            "runtime_identity_present",
            isinstance(runtime.get("subprocess_seconds"), (int, float))
            and runtime.get("subprocess_seconds") >= 0
            and str(runtime.get("device") or "").strip() != "",
            f"runtime={runtime!r}",
        ),
        make_check(
            "scope_disclosed",
            _scope_disclosed(output_payload),
            "intended_use_disclaimer must disclose engineering-only and non-clinical scope",
        ),
    ]

    hard_fail = any(check["status"] == "fail" for check in checks)
    overall = "fail" if hard_fail else "pass"

    return {
        "verifier": {"id": VERIFIER_ID, "version": VERIFIER_VERSION},
        "target": {
            "evidence_pack": _public_path(pack_dir),
            "skill_id": skill_id,
            "source_overall_status": validation.get("overall_status"),
        },
        "mr_quality": {
            "verdict": overall,
            "acceptable": overall == "pass",
            "output_skill": output_skill,
            "version": input_payload.get("version"),
            "modality_name": input_payload.get("modality_name"),
            "num_samples": len(image_records),
            "all_images_readable": all_readable,
            "all_shapes_match_requested": all_shape,
            "all_spacing_match_requested": all_spacing,
            "all_images_finite": all_finite,
            "all_images_nonconstant": all_nonconstant,
            "all_images_nonnegative": all_nonnegative,
        },
        "checks": checks,
        "overall": overall,
    }


if __name__ == "__main__":
    run_grader(grade, sort_keys=True)
