# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import json

import nibabel as nib
import numpy as np
import pytest

from tools.test_fixtures.generate_nifti import MAX_VOXELS, main, write_nifti


@pytest.mark.parametrize("suffix", [".nii", ".nii.gz"])
@pytest.mark.parametrize("shape", [(8, 9, 10), (4, 5, 6, 2)])
def test_geometry_values_and_byte_determinism(tmp_path, suffix, shape):
    first = write_nifti(tmp_path / f"first{suffix}", shape=shape, spacing_mm=1.5, value=-7)
    second = write_nifti(tmp_path / f"second{suffix}", shape=shape, spacing_mm=1.5, value=-7)
    assert first.read_bytes() == second.read_bytes()
    image = nib.load(first)
    assert image.shape == shape
    assert image.header.get_zooms()[:3] == pytest.approx((1.5, 1.5, 1.5))
    assert image.get_data_dtype() == np.dtype("int16")
    assert np.array_equal(image.affine, np.diag((-1.5, -1.5, 1.5, 1.0)))
    assert np.all(np.asarray(image.dataobj) == -7)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"shape": (8, 9)},
        {"shape": (0, 9, 10)},
        {"shape": (-1, 9, 10)},
        {"shape": (True, 9, 10)},
        {"shape": (8.0, 9, 10)},
        {"shape": (MAX_VOXELS + 1, 1, 1)},
        {"spacing_mm": 0},
        {"spacing_mm": float("nan")},
        {"spacing_mm": float("inf")},
        {"value": 32768},
        {"value": -32769},
        {"value": 0.5},
        {"value": True},
    ],
)
def test_invalid_parameters_write_nothing(tmp_path, kwargs):
    with pytest.raises(ValueError):
        write_nifti(tmp_path / "new" / "volume.nii", **kwargs)
    assert not list(tmp_path.iterdir())


def test_refuses_non_nifti_extension(tmp_path):
    with pytest.raises(ValueError, match="end in"):
        write_nifti(tmp_path / "volume.json")
    assert not list(tmp_path.iterdir())


def test_never_overwrites_existing_file_or_symlink(tmp_path):
    original = tmp_path / "volume.nii"
    original.write_bytes(b"caller-owned input")
    link = tmp_path / "link.nii"
    link.symlink_to(original)
    for path in (original, link):
        with pytest.raises(FileExistsError):
            write_nifti(path)
    assert original.read_bytes() == b"caller-owned input"


def test_cli_reports_synthetic_not_model_output(tmp_path, capsys):
    path = tmp_path / "volume.nii.gz"
    assert main([str(path), "--shape", "4", "5", "6"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "path": str(path),
        "synthetic": True,
        "model_inference": False,
    }
    assert nib.load(path).shape == (4, 5, 6)


def test_cli_validation_fails_cleanly(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        main([str(tmp_path / "volume.nii"), "--shape", "0", "5", "6"])
    assert exc.value.code == 2
    assert "positive integers" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


def test_pytest_factory(synthetic_nifti_factory, tmp_path):
    path = synthetic_nifti_factory("nested/input.nii.gz", shape=(3, 4, 5))
    assert path == tmp_path / "nested" / "input.nii.gz"
    assert nib.load(path).shape == (3, 4, 5)


@pytest.mark.parametrize("name", ["../outside.nii", "/absolute.nii"])
def test_pytest_factory_rejects_escape(synthetic_nifti_factory, name):
    with pytest.raises(ValueError, match="inside the test directory"):
        synthetic_nifti_factory(name)


def test_pytest_factory_rejects_symlink_parent(synthetic_nifti_factory, tmp_path):
    outside = tmp_path.parent / "outside"
    outside.mkdir()
    (tmp_path / "escape").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="inside the test directory"):
        synthetic_nifti_factory("escape/volume.nii")
    assert not list(outside.iterdir())
