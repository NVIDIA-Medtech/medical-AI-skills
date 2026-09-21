#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Create small deterministic NIfTI inputs for offline engineering tests."""

from __future__ import annotations

import argparse
import gzip
import json
import math
from contextlib import nullcontext
from pathlib import Path

import nibabel as nib
import numpy as np

# Bound allocations to 2 MiB of int16 data; these are tiny test inputs.
MAX_VOXELS = 1024 * 1024


def write_nifti(
    path: Path,
    *,
    shape: tuple[int, ...] = (8, 9, 10),
    spacing_mm: float = 2.0,
    value: int = 0,
) -> Path:
    """Write a constant-valued 3D or 4D fixture without replacing any file.

    Four-dimensional inputs support dimensionality-rejection tests. Neither
    shape nor voxel values represent anatomy or establish clinical realism.
    """
    path = Path(path)
    if not (path.name.endswith(".nii") or path.name.endswith(".nii.gz")):
        raise ValueError("output must end in .nii or .nii.gz")
    if len(shape) not in (3, 4) or any(
        isinstance(n, bool) or not isinstance(n, int) or n < 1 for n in shape
    ):
        raise ValueError("shape must contain three or four positive integers")
    if math.prod(shape) > MAX_VOXELS:
        raise ValueError(f"test fixtures are limited to {MAX_VOXELS} voxels")
    if not math.isfinite(spacing_mm) or spacing_mm <= 0:
        raise ValueError("spacing_mm must be positive and finite")
    if isinstance(value, bool) or not isinstance(value, int) or not -32768 <= value <= 32767:
        raise ValueError("value must be an int16 integer")

    data = np.full(shape, value, dtype=np.int16)
    image = nib.Nifti1Image(data, np.diag((-spacing_mm, -spacing_mm, spacing_mm, 1.0)))
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also rejects existing symlinks. Empty gzip filename
    # and a fixed mtime keep compressed bytes independent of path and clock.
    with path.open("xb") as raw:
        compressed = path.name.endswith(".gz")
        context = (
            gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0)
            if compressed
            else nullcontext(raw)
        )
        with context as stream:
            image.to_file_map({"image": nib.FileHolder(fileobj=stream)})
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--shape", nargs="+", type=int, default=[8, 9, 10])
    parser.add_argument("--spacing-mm", type=float, default=2.0)
    parser.add_argument("--value", type=int, default=0)
    args = parser.parse_args(argv)
    try:
        path = write_nifti(
            args.output,
            shape=tuple(args.shape),
            spacing_mm=args.spacing_mm,
            value=args.value,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({"path": str(path), "synthetic": True, "model_inference": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
