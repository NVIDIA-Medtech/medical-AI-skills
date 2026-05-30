#!/usr/bin/env python3
"""Verify nv_generate_ct_rflow evidence packs for engineering-floor quality.

Four tiers, each emitting a sub-verdict:

  artifact_inventory     — every sample's image and label NIfTI resolve and
                           are readable from the recorded paths.
  geometry_consistency   — image and label share shape, spacing, and affine
                           for every sample (recomputed from headers).
  image_hu_plausibility  — image arrays contain both air-range (HU < -500)
                           and bone-range (HU > 200) voxels and are
                           non-constant. A constant synthetic image is the
                           canonical silent failure of a diffusion sampler
                           that converged to background noise.
  label_set_sanity       — every observed label id is in [0, 132] (VISTA3D
                           schema), label_id_count > 0 per sample, and at
                           least one foreground class is present in the
                           generated set.
  declared_anatomy_coverage — every wrapper-declared output label id appears.
  anatomy_hu_plausibility   — anatomy-specific HU floors for labels where a
                              simple engineering bound is defensible.

The verifier does NOT re-run synthesis (CPU-only). For evidence that the
diffusion sampler ran with the user-declared anatomy_list, see the wrapper's
own `output.union_label_ids_present` (recorded by run_rflow_ct.py) — this
verifier reports the same field for cross-check parity.
"""
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
from verifiers._shared.verifier_kit import load_pack_json, run_grader  # noqa: E402

VERIFIER_ID = "medagent.verifiers.ct_synthesis_quality_v1"
VERIFIER_VERSION = "0.1.0"
# Manifests emit `medagent.<name>`; output payloads emit the bare `<name>`.
# Accept either so this verifier works on real eval_engine packs AND on
# hand-built fixture packs.
TARGET_SKILL_IDS = {"nv_generate_ct_rflow", "medagent.nv_generate_ct_rflow"}

# VISTA3D label-space schema: 132 foreground classes + background.
MAX_LABEL_ID = 132
HU_AIR_FLOOR = -500.0
HU_BONE_CEIL = 200.0
LUNG_LOBE_MEDIAN_HU_MAX = -300.0
LUNG_LOBE_NAMES = {
    "left lung upper lobe",
    "left lung lower lobe",
    "right lung upper lobe",
    "right lung middle lobe",
    "right lung lower lobe",
}


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


def _resolve_artifact(pack_dir: Path, raw: str | None) -> Path | None:
    if not raw:
        return None
    p = Path(raw)
    candidates = [p] if p.is_absolute() else [pack_dir / p, REPO_ROOT / p]
    for c in candidates:
        if c.is_file():
            return c
    return None


def _sha256_path(path: Path | None) -> str | None:
    if path is None:
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _artifact_inventory(pack_dir: Path, samples: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    all_ok = bool(samples)
    for s in samples:
        img_path = _resolve_artifact(pack_dir, s.get("image_path"))
        lbl_path = _resolve_artifact(pack_dir, s.get("label_path"))
        ok = bool(img_path and lbl_path)
        all_ok = all_ok and ok
        rows.append(
            {
                "image_path_declared": s.get("image_path"),
                "label_path_declared": s.get("label_path"),
                "image_resolved": img_path is not None,
                "label_resolved": lbl_path is not None,
                "image_bytes": img_path.stat().st_size if img_path else None,
                "label_bytes": lbl_path.stat().st_size if lbl_path else None,
                "image_sha256": _sha256_path(img_path),
                "label_sha256": _sha256_path(lbl_path),
            }
        )
    return {
        "verdict": "pass" if all_ok else "fail",
        "samples": rows,
        "failed_checks": [] if all_ok else ["one or more sample artifacts did not resolve"],
    }


def _recompute_pair(pack_dir: Path, sample: dict[str, Any]) -> dict[str, Any]:
    """Re-read the image/label NIfTI and recompute geometry + content stats.

    The verifier intentionally does not trust the wrapper-reported numbers;
    it re-derives them from the headers so an evidence-pack manifest bug
    cannot mask a real silent failure.
    """
    image_path = _resolve_artifact(pack_dir, sample.get("image_path"))
    label_path = _resolve_artifact(pack_dir, sample.get("label_path"))
    rec: dict[str, Any] = {
        "image_path": _public_path(image_path) if image_path else sample.get("image_path"),
        "label_path": _public_path(label_path) if label_path else sample.get("label_path"),
        "image_ok": False,
        "label_ok": False,
    }
    if image_path is None or label_path is None:
        return rec

    try:
        img = nib.load(str(image_path))
        arr = np.asarray(img.get_fdata(), dtype=np.float32)
        rec["image_ok"] = True
        rec["image_shape"] = [int(v) for v in arr.shape]
        rec["image_spacing"] = [round(float(v), 6) for v in img.header.get_zooms()[:3]]
        finite = arr[np.isfinite(arr)]
        if finite.size:
            rec["image_hu_min"] = round(float(finite.min()), 3)
            rec["image_hu_max"] = round(float(finite.max()), 3)
            rec["image_hu_negative_present"] = bool((finite < HU_AIR_FLOOR).any())
            rec["image_hu_bone_present"] = bool((finite > HU_BONE_CEIL).any())
            rec["image_nonconstant"] = bool(finite.max() - finite.min() > 1.0)
    except Exception as e:
        rec["image_error"] = repr(e)
        return rec

    try:
        lbl = nib.load(str(label_path))
        marr = np.asarray(lbl.get_fdata()).astype(np.int64)
        rec["label_ok"] = True
        rec["label_shape"] = [int(v) for v in marr.shape]
        rec["label_spacing"] = [round(float(v), 6) for v in lbl.header.get_zooms()[:3]]
        unique = np.unique(marr).tolist()
        ids = [int(v) for v in unique if int(v) != 0]
        rec["label_ids_present"] = sorted(ids)
        rec["label_id_count"] = len(ids)
        rec["label_foreground_voxels"] = int((marr != 0).sum())
        rec["label_out_of_range"] = sorted(v for v in ids if v < 0 or v > MAX_LABEL_ID)
        if rec["image_ok"] and rec["image_shape"] == rec["label_shape"]:
            label_hu_stats: dict[str, dict[str, Any]] = {}
            for label_id in ids:
                voxels = arr[marr == label_id]
                finite_voxels = voxels[np.isfinite(voxels)]
                if finite_voxels.size:
                    label_hu_stats[str(label_id)] = {
                        "voxels": int(finite_voxels.size),
                        "min_hu": round(float(finite_voxels.min()), 3),
                        "median_hu": round(float(np.median(finite_voxels)), 3),
                        "max_hu": round(float(finite_voxels.max()), 3),
                    }
            rec["label_hu_stats"] = label_hu_stats
        rec["shape_match"] = rec["image_shape"] == rec["label_shape"]
        rec["spacing_match"] = rec["image_spacing"] == rec["label_spacing"]
        affine_diff = float(np.max(np.abs(img.affine - lbl.affine)))
        rec["affine_max_abs_diff"] = round(affine_diff, 8)
        rec["affine_match"] = affine_diff <= 1e-4
    except Exception as e:
        rec["label_error"] = repr(e)

    return rec


def _geometry_consistency(records: list[dict[str, Any]]) -> dict[str, Any]:
    failed: list[str] = []
    for i, r in enumerate(records):
        if not (r.get("image_ok") and r.get("label_ok")):
            failed.append(f"sample[{i}]: image or label unreadable")
            continue
        if not r.get("shape_match"):
            failed.append(f"sample[{i}]: shape mismatch image={r.get('image_shape')} label={r.get('label_shape')}")
        if not r.get("spacing_match"):
            failed.append(f"sample[{i}]: spacing mismatch")
        if not r.get("affine_match"):
            failed.append(f"sample[{i}]: affine mismatch (max_abs_diff={r.get('affine_max_abs_diff')})")
    return {"verdict": "pass" if not failed else "fail", "failed_checks": failed}


def _image_hu_plausibility(records: list[dict[str, Any]]) -> dict[str, Any]:
    failed: list[str] = []
    for i, r in enumerate(records):
        if not r.get("image_ok"):
            failed.append(f"sample[{i}]: image unreadable")
            continue
        if not r.get("image_nonconstant"):
            failed.append(
                f"sample[{i}]: constant image — diffusion did not produce signal "
                f"(min={r.get('image_hu_min')} max={r.get('image_hu_max')})"
            )
        if not r.get("image_hu_negative_present"):
            failed.append(
                f"sample[{i}]: no HU<{HU_AIR_FLOOR} voxels (air/lung absent — not CT-like)"
            )
        if not r.get("image_hu_bone_present"):
            failed.append(
                f"sample[{i}]: no HU>{HU_BONE_CEIL} voxels (no bone/dense tissue — not CT-like)"
            )
    return {"verdict": "pass" if not failed else "fail", "failed_checks": failed}


def _label_set_sanity(records: list[dict[str, Any]]) -> dict[str, Any]:
    failed: list[str] = []
    any_foreground = False
    union: set[int] = set()
    for i, r in enumerate(records):
        if not r.get("label_ok"):
            failed.append(f"sample[{i}]: label unreadable")
            continue
        out_of_range = r.get("label_out_of_range") or []
        if out_of_range:
            failed.append(
                f"sample[{i}]: label ids out of VISTA3D range [0,{MAX_LABEL_ID}]: {out_of_range}"
            )
        if r.get("label_id_count", 0) == 0:
            failed.append(f"sample[{i}]: no foreground labels present (id_count=0)")
        else:
            any_foreground = True
        for v in r.get("label_ids_present") or []:
            union.add(int(v))
    if records and not any_foreground:
        failed.append("no sample has any foreground label")
    return {
        "verdict": "pass" if not failed else "fail",
        "failed_checks": failed,
        "union_label_ids_present": sorted(union),
    }


def _declared_anatomy_coverage(output: dict[str, Any], labels: dict[str, Any]) -> dict[str, Any]:
    failed: list[str] = []
    mapping = output.get("output_label_mapping") or []
    if not mapping:
        failed.append("output.output_label_mapping is missing or empty")
        expected_output_ids: set[int] = set()
    else:
        expected_output_ids = set()
        for i, item in enumerate(mapping):
            if not isinstance(item, dict):
                failed.append(f"output_label_mapping[{i}] is not an object")
                continue
            output_label_id = item.get("output_label_id")
            anatomy = item.get("anatomy")
            maisi_label_id = item.get("maisi_label_id")
            if not isinstance(anatomy, str) or not anatomy:
                failed.append(f"output_label_mapping[{i}] has invalid anatomy {anatomy!r}")
            if not isinstance(maisi_label_id, int):
                failed.append(f"output_label_mapping[{i}] has invalid maisi_label_id {maisi_label_id!r}")
            if not isinstance(output_label_id, int) or output_label_id <= 0:
                failed.append(f"output_label_mapping[{i}] has invalid output_label_id {output_label_id!r}")
                continue
            expected_output_ids.add(output_label_id)

    observed = {int(v) for v in labels.get("union_label_ids_present") or []}
    missing = sorted(expected_output_ids - observed)
    if missing:
        failed.append(f"declared output label id(s) missing from generated masks: {missing}")

    return {
        "verdict": "pass" if not failed else "fail",
        "failed_checks": failed,
        "expected_output_label_ids": sorted(expected_output_ids),
        "observed_label_ids": sorted(observed),
        "missing_expected_output_label_ids": missing,
    }


def _anatomy_hu_plausibility(records: list[dict[str, Any]], output: dict[str, Any]) -> dict[str, Any]:
    failed: list[str] = []
    checked: list[dict[str, Any]] = []
    mapping = output.get("output_label_mapping") or []

    for item in mapping:
        if not isinstance(item, dict):
            continue
        anatomy = item.get("anatomy")
        output_label_id = item.get("output_label_id")
        if anatomy not in LUNG_LOBE_NAMES or not isinstance(output_label_id, int):
            continue
        key = str(output_label_id)
        for i, record in enumerate(records):
            stats = (record.get("label_hu_stats") or {}).get(key)
            if not stats:
                failed.append(
                    f"sample[{i}]: {anatomy} output label {output_label_id} has no voxels"
                )
                continue
            row = {
                "sample_index": i,
                "anatomy": anatomy,
                "output_label_id": output_label_id,
                "median_hu": stats["median_hu"],
                "voxels": stats["voxels"],
            }
            checked.append(row)
            if float(stats["median_hu"]) > LUNG_LOBE_MEDIAN_HU_MAX:
                failed.append(
                    f"sample[{i}]: {anatomy} median HU {stats['median_hu']} exceeds "
                    f"lung-lobe ceiling {LUNG_LOBE_MEDIAN_HU_MAX}"
                )

    return {
        "verdict": "pass" if not failed else "fail",
        "failed_checks": failed,
        "checked_anatomies": checked,
    }


def grade(pack_dir: Path) -> dict[str, Any]:
    output_payload = load_pack_json(pack_dir, "output.json")
    validation = load_pack_json(pack_dir, "validation_summary.json")
    manifest = load_pack_json(pack_dir, "manifest.json")

    skill_id = manifest.get("skill_id") or output_payload.get("skill") or ""
    source_status = validation.get("overall_status", "")
    output = output_payload.get("output") or {}
    samples_declared = output.get("samples") or []

    artifact = _artifact_inventory(pack_dir, samples_declared)
    records = [_recompute_pair(pack_dir, s) for s in samples_declared]
    geometry = _geometry_consistency(records)
    hu = _image_hu_plausibility(records)
    labels = _label_set_sanity(records)
    declared = _declared_anatomy_coverage(output, labels)
    anatomy_hu = _anatomy_hu_plausibility(records, output)

    tiers_pass = (
        artifact["verdict"] == "pass"
        and geometry["verdict"] == "pass"
        and hu["verdict"] == "pass"
        and labels["verdict"] == "pass"
        and declared["verdict"] == "pass"
        and anatomy_hu["verdict"] == "pass"
    )
    skill_ok = skill_id in TARGET_SKILL_IDS

    return {
        "verifier": {"id": VERIFIER_ID, "version": VERIFIER_VERSION},
        "target": {
            "evidence_pack": _public_path(pack_dir),
            "skill_id": skill_id,
            "source_overall_status": source_status,
            "num_samples_declared": len(samples_declared),
        },
        "artifact_inventory": artifact,
        "geometry_consistency": geometry,
        "image_hu_plausibility": hu,
        "label_set_sanity": labels,
        "declared_anatomy_coverage": declared,
        "anatomy_hu_plausibility": anatomy_hu,
        "overall": "pass" if (skill_ok and tiers_pass) else "fail",
    }


if __name__ == "__main__":
    run_grader(grade, sort_keys=True)
