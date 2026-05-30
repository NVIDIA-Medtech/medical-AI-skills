from pathlib import Path

from eval_engine.integrity import _integrity_scan


def test_nvidia_disclosure_program_url_is_allowed(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    (skill_dir / "skill-card.md").write_text(
        "Please report NVIDIA AI Concerns "
        "at https://app.intigriti.com/programs/nvidia/nvidiavdp/detail.\n"
    )

    result = _integrity_scan(skill_dir)

    assert result == {"status": "clean", "findings": [], "n_findings": 0}
