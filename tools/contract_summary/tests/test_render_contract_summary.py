from __future__ import annotations

from pathlib import Path

from tools.render_contract_summary import render_contract_summary


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_dicom_preflight_contract_summary_surfaces_core_contract() -> None:
    markdown = render_contract_summary(REPO_ROOT / "skills" / "dicom-series-preflight")

    assert "# Contract Summary: dicom-series-preflight" in markdown
    assert "medagent.dicom_series_preflight" in markdown
    assert "scripts/preflight_series.py" in markdown
    assert "dicom_dir" in markdown
    assert "preflight_json" in markdown
    assert "medagent.verifiers.dicom_preflight_quality_v1" in markdown
    assert "examples/evidence_packs/dicom_series_preflight_trusted_pass" in markdown
    assert "Header-only; does not decode pixel data" in markdown


def test_contract_summary_handles_verifier_contract() -> None:
    markdown = render_contract_summary(REPO_ROOT / "verifiers" / "dicom_preflight_quality_v1")

    assert "# Contract Summary: dicom-preflight-quality-v1" in markdown
    assert "medagent.verifiers.dicom_preflight_quality_v1" in markdown
    assert "scripts/grade.py" in markdown
    assert "dicom_series_preflight_evidence_pack" in markdown
    assert "dicom_preflight_quality_report" in markdown
