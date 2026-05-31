# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pathlib import Path

from verifiers._shared.verifier_kit import REPO_ROOT, resolve_pack_artifact


def test_resolve_repo_placeholder_path() -> None:
    target = REPO_ROOT / "verifiers" / "_shared" / "verifier_kit.py"

    resolved = resolve_pack_artifact(
        Path("/unused-pack"), "<repo>/verifiers/_shared/verifier_kit.py"
    )

    assert resolved == target


def test_resolve_relative_pack_artifact(tmp_path: Path) -> None:
    pack = tmp_path / "pack"
    artifact = pack / "artifacts" / "output.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}")

    resolved = resolve_pack_artifact(pack, "artifacts/output.json")

    assert resolved == artifact


def test_resolve_relative_artifact_from_extra_base(tmp_path: Path) -> None:
    pack = tmp_path / "pack"
    extra = tmp_path / "run"
    artifact = extra / "outputs" / "mask.nii.gz"
    pack.mkdir()
    artifact.parent.mkdir(parents=True)
    artifact.write_text("mask")

    resolved = resolve_pack_artifact(pack, "outputs/mask.nii.gz", extra)

    assert resolved == artifact


def test_relocates_absolute_path_from_another_checkout() -> None:
    target = REPO_ROOT / "verifiers" / "_shared" / "verifier_kit.py"
    stale = Path("/old/checkouts") / REPO_ROOT.name / "verifiers" / "_shared" / "verifier_kit.py"

    resolved = resolve_pack_artifact(Path("/unused-pack"), str(stale))

    assert resolved == target
