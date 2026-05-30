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
    stale = (
        Path("/old/checkouts")
        / REPO_ROOT.name
        / "verifiers"
        / "_shared"
        / "verifier_kit.py"
    )

    resolved = resolve_pack_artifact(Path("/unused-pack"), str(stale))

    assert resolved == target
