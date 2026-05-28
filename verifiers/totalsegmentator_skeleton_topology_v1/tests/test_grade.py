"""Tests for totalsegmentator_skeleton_topology_v1.

Synthetic packs built inline with TotalSegmentator label IDs.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import nibabel as nib
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
VERIFIER = REPO_ROOT / "verifiers" / "totalsegmentator_skeleton_topology_v1"
SCRIPT = VERIFIER / "scripts" / "grade.py"


def _build_skeleton_pack(
    pack_dir: Path,
    *,
    fragment_chain: bool = False,
    asymmetric_rib_pair: bool = False,
    swap_vertebra_size: bool = False,
    rib_indices: list[int] | None = None,
) -> Path:
    """Build a pack with a synthetic skeleton segmentation.

    Default (healthy):
      - 5 lumbar (L5..L1 = ids 27..31), 4 thoracic (T12..T9 = ids 32..35),
        3 cervical (C7..C5 = ids 44..46) — total 12 vertebrae stacked along
        z-axis (lumbar at low z, cervical at high z, ascending order)
      - vertebra body size monotonic: lumbar 30^3=27000 voxels, thoracic
        20^3=8000, cervical 12^3=1728
      - 6 rib pairs (ribs 1..6) with matched volumes

    Flags:
      fragment_chain: swap L3 and T12 z-position to violate chain monotonicity
      asymmetric_rib_pair: make rib_left_3 huge (4x) and rib_right_3 small
      swap_vertebra_size: cervical bigger than lumbar
    """
    if rib_indices is None:
        rib_indices = [1, 2, 3, 4, 5, 6]

    pack_dir.mkdir(parents=True, exist_ok=True)
    shape = (200, 200, 200)  # large enough to fit a tall skeleton along z
    affine = np.diag([1.0, 1.0, 1.0, 1.0])
    mask = np.zeros(shape, dtype=np.int16)

    # Vertebra placements: stack along z-axis. Each vertebra is a slab at
    # (x_slice, y_slice, z_center). Ascending z = ascending cranial position.
    # Lumbar (L5..L1, ids 27..31) at z=10,20,30,40,50 (low z), 30^3 voxels
    # Thoracic (T12..T9, ids 32..35) at z=60,70,80,90 (mid z), 20^3 voxels
    # Cervical (C7..C5, ids 44..46) at z=100,110,120 (high z), 12^3 voxels
    lumbar_sizes = (30, 30, 30) if not swap_vertebra_size else (10, 10, 10)
    cervical_sizes = (12, 12, 12) if not swap_vertebra_size else (40, 40, 40)
    thoracic_sizes = (20, 20, 20)

    def stamp(label: int, z_center: int, sizes: tuple[int, int, int]) -> None:
        sx, sy, sz = sizes
        x0, y0, z0 = 80, 80, z_center - sz // 2
        mask[x0:x0 + sx, y0:y0 + sy, z0:z0 + sz] = label

    # Lumbar: L5=27 z=10, L4=28 z=20, L3=29 z=30, L2=30 z=40, L1=31 z=50
    lumbar_positions = [(27, 10), (28, 20), (29, 30), (30, 40), (31, 50)]
    # Thoracic: T12=32 z=60, T11=33 z=70, T10=34 z=80, T9=35 z=90
    thoracic_positions = [(32, 60), (33, 70), (34, 80), (35, 90)]
    # Cervical: C7=44 z=100, C6=45 z=110, C5=46 z=120
    cervical_positions = [(44, 100), (45, 110), (46, 120)]

    if fragment_chain:
        # Swap L3 (id 29) z to 150 — far above cervical, breaking chain order
        lumbar_positions = [(27, 10), (28, 20), (29, 150), (30, 40), (31, 50)]

    for lid, z in lumbar_positions:
        stamp(lid, z, lumbar_sizes)
    for lid, z in thoracic_positions:
        stamp(lid, z, thoracic_sizes)
    for lid, z in cervical_positions:
        stamp(lid, z, cervical_sizes)

    # Ribs: bilateral pairs along x. Left rib N has id 91+N, right has 103+N.
    rib_size = (15, 15, 15)
    for n in rib_indices:
        left_id, right_id = 91 + n, 103 + n
        x_left, x_right = 30, 160  # left and right sides of the body
        y = 100
        z = 30 + n * 10  # ribs span thorax
        if asymmetric_rib_pair and n == 3:
            # Make rib_left_3 4x bigger than rib_right_3
            mask[x_left:x_left + 30, y:y + 30, z:z + 30] = left_id  # 27000 voxels
            mask[x_right:x_right + 5, y:y + 5, z:z + 5] = right_id  # 125 voxels
        else:
            mask[x_left:x_left + rib_size[0], y:y + rib_size[1], z:z + rib_size[2]] = left_id
            mask[x_right:x_right + rib_size[0], y:y + rib_size[1], z:z + rib_size[2]] = right_id

    mask_path = pack_dir / "predicted_seg.nii.gz"
    nib.save(nib.Nifti1Image(mask, affine), str(mask_path))

    output_payload = {
        "skill": "totalsegmentator",
        "task": "total",
        "input": {"path": "synthetic_ct.nii.gz"},
        "output": {"path": str(mask_path), "shape": list(shape)},
    }
    (pack_dir / "output.json").write_text(json.dumps(output_payload, indent=2))
    (pack_dir / "validation_summary.json").write_text(json.dumps({"overall_status": "passed"}))
    (pack_dir / "manifest.json").write_text(json.dumps({"skill_id": "totalsegmentator"}))
    return pack_dir


def _run_script(fixture: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(fixture)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def test_healthy_skeleton_passes(tmp_path: Path) -> None:
    pack = _build_skeleton_pack(tmp_path / "healthy")
    payload = _run_script(pack)
    assert payload["overall"] == "pass", payload
    assert payload["vertebra_chain"]["verdict"] == "pass"
    assert payload["vertebra_body_size_monotonic"]["verdict"] == "pass"
    assert payload["rib_pair_symmetry"]["verdict"] == "pass"


def test_fragmented_chain_fails(tmp_path: Path) -> None:
    pack = _build_skeleton_pack(tmp_path / "fragmented", fragment_chain=True)
    payload = _run_script(pack)
    assert payload["overall"] == "fail", payload
    chain = payload["vertebra_chain"]
    assert chain["verdict"] == "fail"
    assert len(chain["violations"]) > 0
    # The violation should involve L3 since we placed it at z=150
    names_in_violations = {n for v in chain["violations"] for n in v["between"]}
    assert "L3" in names_in_violations


def test_inverted_vertebra_size_fails(tmp_path: Path) -> None:
    pack = _build_skeleton_pack(tmp_path / "inverted_size", swap_vertebra_size=True)
    payload = _run_script(pack)
    assert payload["overall"] == "fail"
    size = payload["vertebra_body_size_monotonic"]
    assert size["verdict"] == "fail"
    assert len(size["violations"]) > 0


def test_asymmetric_rib_pair_fails(tmp_path: Path) -> None:
    pack = _build_skeleton_pack(tmp_path / "asym_rib", asymmetric_rib_pair=True)
    payload = _run_script(pack)
    assert payload["overall"] == "fail"
    ribs = payload["rib_pair_symmetry"]
    assert ribs["verdict"] == "fail"
    # rib pair 3 should be in asymmetric_pairs
    assert any("3" in s for s in ribs["asymmetric_pairs"])


def test_too_few_vertebrae_skips(tmp_path: Path) -> None:
    """When fewer than MIN_VERTEBRAE_FOR_CHAIN_CHECK vertebrae are present,
    the chain tier returns skipped (not fail)."""
    pack = _build_skeleton_pack(tmp_path / "scant", rib_indices=[1, 2])
    # Wipe most vertebrae from the mask via a follow-up edit
    mask_path = pack / "predicted_seg.nii.gz"
    mask_img = nib.load(str(mask_path))
    mask = np.asarray(mask_img.get_fdata()).astype(np.int16)
    # Keep only L5 (id=27) and T12 (id=32) — 2 vertebrae, below threshold
    for lid in range(25, 51):
        if lid not in (27, 32):
            mask[mask == lid] = 0
    nib.save(nib.Nifti1Image(mask, mask_img.affine), str(mask_path))

    payload = _run_script(pack)
    assert payload["vertebra_chain"]["verdict"] == "skipped"
