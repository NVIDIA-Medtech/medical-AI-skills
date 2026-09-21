# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Opt-in pytest factory; never imported by skill runtime code."""

from pathlib import Path

import pytest

from tools.test_fixtures.generate_nifti import write_nifti


@pytest.fixture
def synthetic_nifti_factory(tmp_path):
    """Return a writer restricted to this test's temporary directory."""

    def create(name="volume.nii.gz", **kwargs):
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("fixture name must stay inside the test directory")
        path = tmp_path / relative
        if not path.resolve().is_relative_to(tmp_path.resolve()):
            raise ValueError("fixture name must stay inside the test directory")
        return write_nifti(path, **kwargs)

    return create
