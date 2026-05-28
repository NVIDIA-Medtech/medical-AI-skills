#!/usr/bin/env python3
"""Verify endoscopy tool-tracking evidence packs for minimum domain evidence.

This verifier consumes an evidence-pack directory produced by
`holohub_endoscopy_tool_tracking`. It deliberately sits outside the wrapper:
the wrapper proves the upstream HoloHub application ran; this verifier asks
whether the pack contains detection-quality evidence strong enough to support
the surgical claim.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from verifiers._shared.verifier_kit import (  # noqa: E402
    load_pack_json,
    make_check,
    resolve_pack_artifact,
    run_grader,
)

VERIFIER_ID = "medagent.verifiers.endoscopy_tool_detection_quality_v1"
VERIFIER_VERSION = "0.1.0"
TARGET_SKILL_IDS = {"holohub_endoscopy_tool_tracking"}

DETECTION_SUFFIXES = {".json", ".jsonl", ".ndjson", ".csv"}
DETECTION_NAME_HINTS = (
    "detect",
    "detection",
    "bbox",
    "box",
    "instrument",
    "tool",
    "tracking",
)
_HEX = set("0123456789abcdef")


def _declared_sha256(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    lowered = value.lower()
    if len(lowered) == 64 and all(ch in _HEX for ch in lowered):
        return lowered
    return None


def _sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            data = f.read(chunk)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def _file_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in (".gxf_index", ".gxf_entities"):
        return "gxf"
    if suffix in (".mp4", ".mkv", ".raw"):
        return "video"
    if suffix in DETECTION_SUFFIXES and _looks_like_detection_file(path):
        return "detection"
    return "other"


def _looks_like_detection_file(path: Path) -> bool:
    name = path.name.lower()
    return path.suffix.lower() in DETECTION_SUFFIXES and any(
        hint in name for hint in DETECTION_NAME_HINTS
    )


def _resolve_artifact_path(pack_dir: Path, recording_dir: Path | None, rel: str) -> Path:
    extra_bases: list[Path] = []
    if recording_dir is not None:
        extra_bases.append(recording_dir)
    extra_bases.extend([pack_dir / "recordings", Path.cwd()])
    return resolve_pack_artifact(pack_dir, rel, *extra_bases)


def _recording_dir(pack_dir: Path, output_payload: dict[str, Any]) -> Path | None:
    inv = output_payload.get("invocation") or {}
    value = inv.get("recording_output_dir")
    if not isinstance(value, str) or not value:
        local = pack_dir / "recordings"
        return local if local.exists() else None
    return resolve_pack_artifact(pack_dir, value, Path.cwd())


def _artifact_record(
    path: Path,
    *,
    declared_path: str,
    kind: str,
    declared_bytes: Any = None,
    declared_sha256: Any = None,
) -> dict[str, Any]:
    exists = path.exists() and path.is_file()
    actual_bytes = path.stat().st_size if exists else 0
    verified_sha = _declared_sha256(declared_sha256)
    actual_sha = _sha256_file(path) if exists and verified_sha is not None else None
    hash_match = (actual_sha == verified_sha) if verified_sha is not None else None
    return {
        "path": str(path),
        "declared_path": declared_path,
        "kind": kind,
        "exists": exists,
        "bytes": actual_bytes
        or (declared_bytes if isinstance(declared_bytes, int) else 0),
        "declared_bytes": declared_bytes if isinstance(declared_bytes, int) else None,
        "declared_sha256": declared_sha256 if isinstance(declared_sha256, str) else None,
        "actual_sha256": actual_sha,
        "hash_checked": verified_sha is not None,
        "hash_match": hash_match,
        "usable": exists and hash_match is not False,
    }


def _listed_artifacts(pack_dir: Path, output_payload: dict[str, Any]) -> list[dict[str, Any]]:
    output = output_payload.get("output") or {}
    rec_dir = _recording_dir(pack_dir, output_payload)
    artifacts: list[dict[str, Any]] = []
    for group in ("gxf", "video", "other"):
        group_blob = output.get(group) or {}
        for item in group_blob.get("files") or []:
            if not isinstance(item, dict):
                continue
            rel = str(item.get("path") or "")
            if not rel:
                continue
            path = _resolve_artifact_path(pack_dir, rec_dir, rel)
            artifacts.append(
                _artifact_record(
                    path,
                    declared_path=rel,
                    kind=_file_kind(path),
                    declared_bytes=item.get("bytes"),
                    declared_sha256=item.get("sha256"),
                )
            )

    if artifacts:
        return artifacts

    local_recordings = pack_dir / "recordings"
    if local_recordings.exists():
        for path in sorted(local_recordings.rglob("*")):
            if not path.is_file():
                continue
            artifacts.append(
                _artifact_record(
                    path,
                    declared_path=str(path.relative_to(local_recordings)),
                    kind=_file_kind(path),
                )
            )
    return artifacts


def _bbox_from_detection(det: dict[str, Any]) -> tuple[str, tuple[float, float, float, float]] | None:
    if isinstance(det.get("bbox"), list) and len(det["bbox"]) >= 4:
        try:
            vals = tuple(float(x) for x in det["bbox"][:4])
            return str(det.get("bbox_format") or "xywh").lower(), vals
        except (TypeError, ValueError):
            return None
    if all(k in det for k in ("x", "y", "width", "height")):
        try:
            return "xywh", (
                float(det["x"]),
                float(det["y"]),
                float(det["width"]),
                float(det["height"]),
            )
        except (TypeError, ValueError):
            return None
    if all(k in det for k in ("x", "y", "w", "h")):
        try:
            return "xywh", (
                float(det["x"]),
                float(det["y"]),
                float(det["w"]),
                float(det["h"]),
            )
        except (TypeError, ValueError):
            return None
    if all(k in det for k in ("x1", "y1", "x2", "y2")):
        try:
            return "xyxy", (
                float(det["x1"]),
                float(det["y1"]),
                float(det["x2"]),
                float(det["y2"]),
            )
        except (TypeError, ValueError):
            return None
    if all(k in det for k in ("left", "top", "right", "bottom")):
        try:
            return "xyxy", (
                float(det["left"]),
                float(det["top"]),
                float(det["right"]),
                float(det["bottom"]),
            )
        except (TypeError, ValueError):
            return None
    return None


def _bbox_ok(
    bbox: tuple[str, tuple[float, float, float, float]] | None,
    width: float | None,
    height: float | None,
) -> bool:
    if bbox is None:
        return False
    fmt, vals = bbox
    x0, y0, a, b = vals
    if fmt in ("xyxy", "x1y1x2y2"):
        x1, y1 = a, b
        nondegenerate = x1 > x0 and y1 > y0
        in_frame = True
        if width is not None and height is not None:
            in_frame = x0 >= 0 and y0 >= 0 and x1 <= width and y1 <= height
        return nondegenerate and in_frame

    # Default to xywh because most detector JSON exports use it.
    w, h = a, b
    nondegenerate = w > 0 and h > 0
    in_frame = True
    if width is not None and height is not None:
        in_frame = x0 >= 0 and y0 >= 0 and (x0 + w) <= width and (y0 + h) <= height
    return nondegenerate and in_frame


def _frame_dims(frame: dict[str, Any]) -> tuple[float | None, float | None]:
    width = frame.get("width", frame.get("frame_width", frame.get("image_width")))
    height = frame.get("height", frame.get("frame_height", frame.get("image_height")))
    try:
        return (
            float(width) if width is not None else None,
            float(height) if height is not None else None,
        )
    except (TypeError, ValueError):
        return None, None


def _class_label(det: dict[str, Any]) -> str:
    for key in ("tool_class", "class_name", "class", "label", "category_name", "category", "tool", "name"):
        value = det.get(key)
        if value not in (None, ""):
            return str(value)
    return "unknown"


def _looks_like_detection_obj(obj: Any) -> bool:
    return isinstance(obj, dict) and (
        "bbox" in obj
        or all(k in obj for k in ("x", "y", "width", "height"))
        or all(k in obj for k in ("x1", "y1", "x2", "y2"))
        or "score" in obj
        or "confidence" in obj
    )


def _normalise_frame(obj: dict[str, Any], fallback_idx: int) -> dict[str, Any]:
    if isinstance(obj.get("detections"), list):
        detections = [d for d in obj["detections"] if isinstance(d, dict)]
    elif isinstance(obj.get("annotations"), list):
        detections = [d for d in obj["annotations"] if isinstance(d, dict)]
    elif _looks_like_detection_obj(obj):
        detections = [obj]
    else:
        detections = []
    frame_id = obj.get("frame", obj.get("frame_id", obj.get("image_id", fallback_idx)))
    width, height = _frame_dims(obj)
    return {
        "frame": str(frame_id),
        "width": width,
        "height": height,
        "detections": detections,
    }


def _frames_from_json_obj(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, dict):
        if isinstance(obj.get("frames"), list):
            return [
                _normalise_frame(frame, idx)
                for idx, frame in enumerate(obj["frames"])
                if isinstance(frame, dict)
            ]
        if isinstance(obj.get("images"), list) and isinstance(obj.get("annotations"), list):
            image_dims = {
                str(img.get("id", idx)): _frame_dims(img)
                for idx, img in enumerate(obj["images"])
                if isinstance(img, dict)
            }
            grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for ann in obj["annotations"]:
                if isinstance(ann, dict):
                    grouped[str(ann.get("image_id", "0"))].append(ann)
            frames = []
            for idx, (frame_id, detections) in enumerate(sorted(grouped.items())):
                width, height = image_dims.get(frame_id, (None, None))
                frames.append({
                    "frame": frame_id or str(idx),
                    "width": width,
                    "height": height,
                    "detections": detections,
                })
            return frames
        return [_normalise_frame(obj, 0)]
    if isinstance(obj, list):
        if all(_looks_like_detection_obj(item) for item in obj):
            grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for idx, det in enumerate(obj):
                frame_id = str(det.get("frame", det.get("frame_id", idx)))
                grouped[frame_id].append(det)
            return [
                {"frame": frame_id, "width": None, "height": None, "detections": detections}
                for frame_id, detections in sorted(grouped.items())
            ]
        return [
            _normalise_frame(item, idx)
            for idx, item in enumerate(obj)
            if isinstance(item, dict)
        ]
    return []


def _read_detection_frames(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix in (".jsonl", ".ndjson"):
        frames: list[dict[str, Any]] = []
        for idx, line in enumerate(path.read_text().splitlines()):
            line = line.strip()
            if not line:
                continue
            frames.extend(_frames_from_json_obj(json.loads(line)))
            if frames and frames[-1].get("frame") == "0":
                frames[-1]["frame"] = str(idx)
        return frames
    if suffix == ".json":
        return _frames_from_json_obj(json.loads(path.read_text()))
    if suffix == ".csv":
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        with path.open(newline="") as f:
            for idx, row in enumerate(csv.DictReader(f)):
                frame_id = str(row.get("frame") or row.get("frame_id") or idx)
                grouped[frame_id].append(dict(row))
        return [
            {"frame": frame_id, "width": None, "height": None, "detections": detections}
            for frame_id, detections in sorted(grouped.items())
        ]
    return []


def _detection_metrics(paths: list[Path]) -> dict[str, Any]:
    if not paths:
        return {
            "verdict": "skipped",
            "reason": "no decoded detection artifact found",
            "source_files": [],
            "frames_observed": 0,
            "frames_with_detections": 0,
            "tools_detected_count": 0,
            "mean_detections_per_frame": 0.0,
            "max_detections_per_frame": 0,
            "frame_coverage": 0.0,
            "bbox_sanity": {"checked": 0, "invalid": 0},
            "tool_class_distribution": {},
            "checks": [],
        }

    frames: list[dict[str, Any]] = []
    parse_errors: list[str] = []
    for path in paths:
        try:
            frames.extend(_read_detection_frames(path))
        except Exception as e:
            parse_errors.append(f"{path}: {e}")

    frame_ids = [str(f.get("frame")) for f in frames]
    unique_frames = sorted(set(frame_ids))
    detections_per_frame: list[int] = []
    classes: Counter[str] = Counter()
    bbox_checked = 0
    bbox_invalid = 0
    for frame in frames:
        detections = [d for d in frame.get("detections", []) if isinstance(d, dict)]
        detections_per_frame.append(len(detections))
        width = frame.get("width")
        height = frame.get("height")
        for det in detections:
            classes[_class_label(det)] += 1
            bbox = _bbox_from_detection(det)
            bbox_checked += 1
            if not _bbox_ok(bbox, width, height):
                bbox_invalid += 1

    tools_detected = sum(detections_per_frame)
    frames_observed = len(unique_frames)
    frames_with_detections = sum(1 for count in detections_per_frame if count > 0)
    mean = tools_detected / frames_observed if frames_observed else 0.0
    coverage = frames_with_detections / frames_observed if frames_observed else 0.0
    max_count = max(detections_per_frame) if detections_per_frame else 0

    checks = [
        make_check(
            "detections_parsed",
            not parse_errors and frames_observed > 0,
            "decoded detection frames were parsed" if not parse_errors and frames_observed > 0
            else "; ".join(parse_errors) or "no frames found in detection artifact",
            parse_errors=parse_errors,
        ),
        make_check(
            "tools_detected_count_gt_zero",
            tools_detected > 0,
            f"tools_detected_count={tools_detected}",
            actual=tools_detected,
            expected="> 0",
        ),
        make_check(
            "frame_coverage_gte_0_6",
            coverage >= 0.6,
            f"frame_coverage={coverage:.3f}",
            actual=coverage,
            expected=">= 0.6",
        ),
        make_check(
            "mean_detections_per_frame_reasonable",
            0.5 <= mean <= 4.0,
            f"mean_detections_per_frame={mean:.3f}",
            actual=mean,
            expected="[0.5, 4.0]",
        ),
        make_check(
            "bbox_sanity",
            bbox_checked > 0 and bbox_invalid == 0,
            f"bbox_checked={bbox_checked}, bbox_invalid={bbox_invalid}",
            actual={"checked": bbox_checked, "invalid": bbox_invalid},
            expected="checked > 0 and invalid == 0",
        ),
        make_check(
            "tool_class_observed",
            bool(classes),
            f"classes={dict(classes)}",
            actual=dict(classes),
        ),
    ]

    verdict = "pass" if all(c["status"] == "pass" for c in checks) else "fail"
    return {
        "verdict": verdict,
        "reason": "all detection-quality floor checks passed" if verdict == "pass"
        else "one or more detection-quality floor checks failed",
        "source_files": [str(p) for p in paths],
        "frames_observed": frames_observed,
        "frames_with_detections": frames_with_detections,
        "tools_detected_count": tools_detected,
        "mean_detections_per_frame": mean,
        "max_detections_per_frame": max_count,
        "frame_coverage": coverage,
        "bbox_sanity": {"checked": bbox_checked, "invalid": bbox_invalid},
        "tool_class_distribution": dict(classes),
        "checks": checks,
    }


def grade(pack_dir: Path) -> dict[str, Any]:
    output_payload = load_pack_json(pack_dir, "output.json")
    validation = load_pack_json(pack_dir, "validation_summary.json")
    manifest = load_pack_json(pack_dir, "manifest.json")

    skill_id = manifest.get("skill_id") or output_payload.get("skill_id") or ""
    source_status = validation.get("overall_status", "")
    record_type = ((output_payload.get("invocation") or {}).get("record_type") or "")
    rec_dir = _recording_dir(pack_dir, output_payload)
    artifacts = _listed_artifacts(pack_dir, output_payload)
    existing = [a for a in artifacts if a["exists"]]
    hash_mismatches = [a for a in existing if a["hash_match"] is False]
    usable = [a for a in existing if a["usable"]]
    nonempty = [a for a in usable if int(a.get("bytes") or 0) > 0]
    gxf_indices = [a for a in usable if Path(a["path"]).suffix.lower() == ".gxf_index"]
    gxf_entities = [a for a in usable if Path(a["path"]).suffix.lower() == ".gxf_entities"]
    index_stems = {Path(a["path"]).name.removesuffix(".gxf_index") for a in gxf_indices}
    entity_stems = {Path(a["path"]).name.removesuffix(".gxf_entities") for a in gxf_entities}
    detection_paths = [
        Path(a["path"])
        for a in usable
        if a["kind"] == "detection" and Path(a["path"]).exists()
    ]

    inventory = {
        "recording_output_dir": str(rec_dir) if rec_dir is not None else "",
        "recording_file_count": len(existing),
        "usable_recording_file_count": len(usable),
        "recording_total_bytes": sum(int(a.get("bytes") or 0) for a in existing),
        "hash_mismatch_count": len(hash_mismatches),
        "gxf_index_count": len(gxf_indices),
        "gxf_entities_count": len(gxf_entities),
        "gxf_pair_count": len(index_stems & entity_stems),
        "video_count": sum(1 for a in existing if a["kind"] == "video"),
        "detection_artifact_count": len(detection_paths),
        "files": artifacts,
    }

    floor_checks = [
        make_check("output_json_present", bool(output_payload), "output.json loaded"),
        make_check(
            "target_skill_is_endoscopy",
            skill_id in TARGET_SKILL_IDS,
            f"skill_id={skill_id!r}",
            actual=skill_id,
            expected=sorted(TARGET_SKILL_IDS),
        ),
        make_check(
            "source_pack_passed",
            source_status == "passed",
            f"source overall_status={source_status!r}",
            actual=source_status,
            expected="passed",
        ),
        make_check(
            "declared_artifact_hashes_match",
            len(hash_mismatches) == 0,
            "all verifiable artifact hashes match"
            if not hash_mismatches
            else f"{len(hash_mismatches)} artifact(s) do not match declared sha256",
            actual=len(hash_mismatches),
            expected=0,
        ),
        make_check(
            "recording_artifact_present",
            len(usable) > 0,
            f"usable_recording_file_count={len(usable)}",
            actual=len(usable),
            expected="> 0",
        ),
        make_check(
            "recording_files_nonempty",
            len(usable) > 0 and len(nonempty) == len(usable),
            f"nonempty={len(nonempty)} / usable={len(usable)}",
            actual={"nonempty": len(nonempty), "usable": len(usable)},
        ),
        make_check(
            "gxf_pair_or_video_present",
            inventory["gxf_pair_count"] > 0 or inventory["video_count"] > 0,
            f"gxf_pair_count={inventory['gxf_pair_count']}, video_count={inventory['video_count']}",
            actual={
                "gxf_pair_count": inventory["gxf_pair_count"],
                "video_count": inventory["video_count"],
            },
        ),
        make_check(
            "decoded_detection_artifact_present",
            len(detection_paths) > 0,
            f"detection_artifact_count={len(detection_paths)}",
            actual=len(detection_paths),
            expected="> 0",
        ),
    ]
    domain_floor = {
        "verdict": "pass" if all(c["status"] == "pass" for c in floor_checks) else "fail",
        "checks": floor_checks,
    }

    metrics = _detection_metrics(detection_paths)
    overall = (
        "pass"
        if domain_floor["verdict"] == "pass" and metrics["verdict"] == "pass"
        else "fail"
    )

    return {
        "verifier": {"id": VERIFIER_ID, "version": VERIFIER_VERSION},
        "target": {
            "evidence_pack": str(pack_dir),
            "skill_id": skill_id,
            "source_overall_status": source_status,
            "record_type": record_type,
        },
        "artifact_inventory": inventory,
        "domain_floor": domain_floor,
        "detection_metrics": metrics,
        "overall": overall,
    }


if __name__ == "__main__":
    run_grader(grade, sort_keys=True)
