#!/usr/bin/env python3
"""Verify totalsegmentator evidence packs for skeleton topology.

Three checks specific to TotalSegmentator's total-task label IDs:
  1. Vertebra chain z-monotonicity (C1..sacrum form an ordered chain)
  2. Vertebral body size monotonicity (lumbar >= thoracic >= cervical)
  3. Rib bilateral pairing (rib_left_N volume ≈ rib_right_N volume)

The mask geometry alone is enough — no CT volume needed.
"""
from __future__ import annotations

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

VERIFIER_ID = "medagent.verifiers.totalsegmentator_skeleton_topology_v1"
VERIFIER_VERSION = "0.1.0"
TARGET_SKILL_IDS = {"totalsegmentator"}

# Canonical cranial-to-caudal vertebra chain (TotalSegmentator total task).
# Label IDs descending: C1=50, C2=49, ... S1=26, sacrum=25. The chain in
# order is: C1, C2, C3, C4, C5, C6, C7, T1..T12, L1..L5, S1, sacrum.
VERTEBRA_CHAIN_IDS: list[int] = [
    50, 49, 48, 47, 46, 45, 44,           # C1..C7
    43, 42, 41, 40, 39, 38, 37, 36, 35, 34, 33, 32,  # T1..T12
    31, 30, 29, 28, 27,                   # L1..L5
    26, 25,                               # S1, sacrum
]
VERTEBRA_NAMES: dict[int, str] = {
    50: "C1", 49: "C2", 48: "C3", 47: "C4", 46: "C5", 45: "C6", 44: "C7",
    43: "T1", 42: "T2", 41: "T3", 40: "T4", 39: "T5", 38: "T6", 37: "T7",
    36: "T8", 35: "T9", 34: "T10", 33: "T11", 32: "T12",
    31: "L1", 30: "L2", 29: "L3", 28: "L4", 27: "L5",
    26: "S1", 25: "sacrum",
}
CERVICAL_IDS = {50, 49, 48, 47, 46, 45, 44}
THORACIC_IDS = {43, 42, 41, 40, 39, 38, 37, 36, 35, 34, 33, 32}
LUMBAR_IDS = {31, 30, 29, 28, 27}

# Rib pairs: rib_left_N has id 91+N, rib_right_N has id 103+N, for N=1..12.
RIB_PAIRS: list[tuple[int, int, int]] = [
    (n, 91 + n, 103 + n) for n in range(1, 13)
]

# Tolerances
VERTEBRA_SIZE_TOLERANCE = 0.25   # 25 % — lumbar can be 25% smaller than thoracic and still pass
RIB_VOLUME_TOLERANCE = 0.40      # 40 % — rib_left_N vs rib_right_N
MIN_VERTEBRAE_FOR_CHAIN_CHECK = 3
MIN_RIBS_FOR_PAIR_CHECK = 2


def _resolve_path(pack_dir: Path, raw: str | None) -> Path | None:
    if not raw:
        return None
    return resolve_pack_artifact(pack_dir, raw, Path.cwd())


def _centroid_z(mask: np.ndarray, label_id: int) -> tuple[float, int]:
    """Return (mean z-coordinate, voxel count) for a label."""
    where = np.where(mask == label_id)
    n = int(where[0].size)
    if n == 0:
        return float("nan"), 0
    z_mean = float(np.mean(where[2]))
    return z_mean, n


def _vertebra_chain_check(mask: np.ndarray) -> dict[str, Any]:
    present: list[dict[str, Any]] = []
    for lid in VERTEBRA_CHAIN_IDS:
        z, n = _centroid_z(mask, lid)
        if n > 0:
            present.append({
                "label_id": lid,
                "name": VERTEBRA_NAMES[lid],
                "z_centroid": round(z, 3),
                "voxel_count": n,
            })

    if len(present) < MIN_VERTEBRAE_FOR_CHAIN_CHECK:
        return {
            "verdict": "skipped",
            "reason": f"only {len(present)} vertebrae present (need >= {MIN_VERTEBRAE_FOR_CHAIN_CHECK})",
            "present_in_order": present,
            "violations": [],
            "checks": [],
        }

    # `present` is in canonical cranial-to-caudal order. Check that
    # the z-centroids are monotonic in some direction.
    zs = [v["z_centroid"] for v in present]
    diffs = [zs[i + 1] - zs[i] for i in range(len(zs) - 1)]
    sign_pos = sum(1 for d in diffs if d > 0)
    sign_neg = sum(1 for d in diffs if d < 0)
    # Choose the dominant direction; any flip against it is a violation.
    direction = "ascending" if sign_pos >= sign_neg else "descending"
    violations: list[dict[str, Any]] = []
    for i, d in enumerate(diffs):
        ok = (d > 0) if direction == "ascending" else (d < 0)
        if not ok:
            violations.append({
                "between": [present[i]["name"], present[i + 1]["name"]],
                "z_centroids": [present[i]["z_centroid"], present[i + 1]["z_centroid"]],
                "delta": round(d, 3),
                "expected_direction": direction,
            })

    verdict = "pass" if not violations else "fail"
    return {
        "verdict": verdict,
        "reason": (
            f"{len(present)} vertebrae, z-centroids monotonically {direction}"
            if verdict == "pass"
            else f"{len(violations)} chain order violation(s) along {direction}"
        ),
        "present_in_order": present,
        "direction": direction,
        "violations": violations,
        "checks": [
            make_check(
                "vertebra_chain_monotonic",
                verdict == "pass",
                "ordered" if verdict == "pass" else f"{len(violations)} violation(s)",
                violations=violations,
            )
        ],
    }


def _vertebra_size_check(mask: np.ndarray) -> dict[str, Any]:
    def median_voxel_count(ids: set[int]) -> tuple[float | None, list[int]]:
        counts = []
        for lid in ids:
            n = int(np.sum(mask == lid))
            if n > 0:
                counts.append(n)
        if not counts:
            return None, []
        return float(np.median(counts)), counts

    c_med, c_counts = median_voxel_count(CERVICAL_IDS)
    t_med, t_counts = median_voxel_count(THORACIC_IDS)
    l_med, l_counts = median_voxel_count(LUMBAR_IDS)

    have = sum(x is not None for x in (c_med, t_med, l_med))
    if have < 2:
        return {
            "verdict": "skipped",
            "reason": f"only {have} of 3 vertebra regions present (cervical/thoracic/lumbar)",
            "cervical_median_voxels": c_med,
            "thoracic_median_voxels": t_med,
            "lumbar_median_voxels": l_med,
            "cervical_count": len(c_counts),
            "thoracic_count": len(t_counts),
            "lumbar_count": len(l_counts),
            "violations": [],
            "checks": [],
        }

    violations: list[str] = []
    tol = VERTEBRA_SIZE_TOLERANCE
    if t_med is not None and c_med is not None and t_med < c_med * (1.0 - tol):
        violations.append(
            f"thoracic median {t_med:.0f} < cervical median {c_med:.0f} (tol {tol:.0%})"
        )
    if l_med is not None and t_med is not None and l_med < t_med * (1.0 - tol):
        violations.append(
            f"lumbar median {l_med:.0f} < thoracic median {t_med:.0f} (tol {tol:.0%})"
        )
    if l_med is not None and c_med is not None and l_med < c_med * (1.0 - tol):
        violations.append(
            f"lumbar median {l_med:.0f} < cervical median {c_med:.0f} (tol {tol:.0%})"
        )

    verdict = "pass" if not violations else "fail"
    return {
        "verdict": verdict,
        "reason": (
            f"vertebral body size monotonic: C={c_med} T={t_med} L={l_med}"
            if verdict == "pass"
            else f"{len(violations)} monotonicity violation(s)"
        ),
        "cervical_median_voxels": c_med,
        "thoracic_median_voxels": t_med,
        "lumbar_median_voxels": l_med,
        "cervical_count": len(c_counts),
        "thoracic_count": len(t_counts),
        "lumbar_count": len(l_counts),
        "violations": violations,
        "checks": [
            make_check(
                "vertebra_size_monotonic",
                verdict == "pass",
                "lumbar >= thoracic >= cervical (within tolerance)"
                if verdict == "pass"
                else "; ".join(violations),
                violations=violations,
            )
        ],
    }


def _rib_pair_check(mask: np.ndarray) -> dict[str, Any]:
    pairs: list[dict[str, Any]] = []
    asymmetric: list[str] = []
    missing_partner: list[str] = []
    tol = RIB_VOLUME_TOLERANCE

    for n, left_id, right_id in RIB_PAIRS:
        left_n = int(np.sum(mask == left_id))
        right_n = int(np.sum(mask == right_id))
        if left_n == 0 and right_n == 0:
            continue
        pair_record: dict[str, Any] = {
            "rib_index": n,
            "left_voxel_count": left_n,
            "right_voxel_count": right_n,
            "left_present": left_n > 0,
            "right_present": right_n > 0,
            "ok": False,
        }
        if left_n == 0 or right_n == 0:
            missing = f"rib_left_{n}" if left_n == 0 else f"rib_right_{n}"
            missing_partner.append(missing)
            pair_record["reason"] = f"missing partner: {missing}"
        else:
            larger = max(left_n, right_n)
            diff = abs(left_n - right_n) / larger
            pair_record["relative_diff"] = round(diff, 4)
            pair_record["ok"] = diff <= tol
            if not pair_record["ok"]:
                asymmetric.append(f"rib pair {n}: rel_diff={diff:.2f}")
        pairs.append(pair_record)

    if len(pairs) < MIN_RIBS_FOR_PAIR_CHECK:
        return {
            "verdict": "skipped",
            "reason": f"only {len(pairs)} rib indices present (need >= {MIN_RIBS_FOR_PAIR_CHECK})",
            "pairs": pairs,
            "missing_partners": missing_partner,
            "asymmetric_pairs": asymmetric,
            "checks": [],
        }

    verdict = "pass" if not (missing_partner or asymmetric) else "fail"
    return {
        "verdict": verdict,
        "reason": (
            f"{len(pairs)} rib pair(s) checked, all symmetric within {tol:.0%}"
            if verdict == "pass"
            else f"{len(missing_partner)} unpaired, {len(asymmetric)} asymmetric"
        ),
        "pairs": pairs,
        "missing_partners": missing_partner,
        "asymmetric_pairs": asymmetric,
        "checks": [
            make_check(
                "rib_pair_bilateral_present",
                len(missing_partner) == 0,
                "all rib indices have both left+right"
                if not missing_partner
                else f"missing partners: {missing_partner}",
                missing=missing_partner,
            ),
            make_check(
                "rib_pair_volume_symmetric",
                len(asymmetric) == 0,
                f"all pairs within {tol:.0%}"
                if not asymmetric
                else "; ".join(asymmetric),
                asymmetric=asymmetric,
            ),
        ],
    }


def grade(pack_dir: Path) -> dict[str, Any]:
    output_payload = load_pack_json(pack_dir, "output.json")
    validation = load_pack_json(pack_dir, "validation_summary.json")
    manifest = load_pack_json(pack_dir, "manifest.json")

    skill_id = manifest.get("skill_id") or output_payload.get("skill") or ""
    source_status = validation.get("overall_status", "")

    output = output_payload.get("output") or {}
    mask_path = _resolve_path(pack_dir, output.get("path"))

    inventory: dict[str, Any] = {
        "label_map_path": str(mask_path) if mask_path else None,
        "label_map_readable": False,
        "label_map_shape": [],
    }

    if mask_path is None or not mask_path.exists():
        return {
            "verifier": {"id": VERIFIER_ID, "version": VERIFIER_VERSION},
            "target": {
                "evidence_pack": str(pack_dir),
                "skill_id": skill_id,
                "source_overall_status": source_status,
                "label_map_path": None,
            },
            "input_inventory": inventory,
            "vertebra_chain": {"verdict": "skipped", "reason": "mask unreadable", "present_in_order": [], "violations": [], "checks": []},
            "vertebra_body_size_monotonic": {"verdict": "skipped", "reason": "mask unreadable", "violations": [], "checks": []},
            "rib_pair_symmetry": {"verdict": "skipped", "reason": "mask unreadable", "pairs": [], "missing_partners": [], "asymmetric_pairs": [], "checks": []},
            "overall": "fail",
        }

    try:
        mask_img = nib.load(str(mask_path))
        mask = np.asarray(mask_img.get_fdata()).astype(np.int64)
    except Exception as e:
        inventory["label_map_readable"] = False
        return {
            "verifier": {"id": VERIFIER_ID, "version": VERIFIER_VERSION},
            "target": {
                "evidence_pack": str(pack_dir),
                "skill_id": skill_id,
                "source_overall_status": source_status,
                "label_map_path": str(mask_path),
            },
            "input_inventory": inventory,
            "vertebra_chain": {"verdict": "skipped", "reason": f"load failed: {e}", "present_in_order": [], "violations": [], "checks": []},
            "vertebra_body_size_monotonic": {"verdict": "skipped", "reason": f"load failed: {e}", "violations": [], "checks": []},
            "rib_pair_symmetry": {"verdict": "skipped", "reason": f"load failed: {e}", "pairs": [], "missing_partners": [], "asymmetric_pairs": [], "checks": []},
            "overall": "fail",
        }

    inventory["label_map_readable"] = True
    inventory["label_map_shape"] = [int(v) for v in mask.shape]

    chain = _vertebra_chain_check(mask)
    size = _vertebra_size_check(mask)
    ribs = _rib_pair_check(mask)

    overall = (
        "pass"
        if (
            skill_id in TARGET_SKILL_IDS
            and inventory["label_map_readable"]
            and chain["verdict"] in ("pass", "skipped")
            and size["verdict"] in ("pass", "skipped")
            and ribs["verdict"] in ("pass", "skipped")
        )
        else "fail"
    )

    return {
        "verifier": {"id": VERIFIER_ID, "version": VERIFIER_VERSION},
        "target": {
            "evidence_pack": str(pack_dir),
            "skill_id": skill_id,
            "source_overall_status": source_status,
            "label_map_path": str(mask_path),
        },
        "input_inventory": inventory,
        "vertebra_chain": chain,
        "vertebra_body_size_monotonic": size,
        "rib_pair_symmetry": ribs,
        "overall": overall,
    }


if __name__ == "__main__":
    run_grader(grade, sort_keys=True)
