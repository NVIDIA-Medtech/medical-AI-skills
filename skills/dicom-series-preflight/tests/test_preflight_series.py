"""Unit tests for dicom_series_preflight."""
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).resolve().parents[3]
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"

sys.path.insert(0, str(SCRIPTS))
from preflight_series import preflight  # noqa: E402


@pytest.fixture(scope="module")
def _ensure_fixtures():
    if not (FIXTURES / "clean_no_phi").is_dir():
        import subprocess
        import sys

        subprocess.run(
            [sys.executable, str(FIXTURES / "generate_fixtures.py")],
            check=True,
            cwd=REPO,
        )


def test_clean_no_phi_passes(_ensure_fixtures):
    result = preflight(FIXTURES / "clean_no_phi")
    assert result["preflight"]["verdict"] == "pass"
    assert result["orientation"]["axcodes_match"] is True
    assert result["inventory"]["n_corrupt"] == 0
    assert result["input_dir"] == "skills/dicom-series-preflight/fixtures/clean_no_phi"


def test_flipped_lr_fails(_ensure_fixtures):
    result = preflight(FIXTURES / "flipped_lr")
    assert result["preflight"]["verdict"] == "fail"
    assert result["orientation"]["axcodes_match"] is False


def test_clean_axial_warns_phi(_ensure_fixtures):
    result = preflight(FIXTURES / "clean_axial")
    assert result["preflight"]["verdict"] == "warn"
    assert result["phi"]["phi_present"] is True
