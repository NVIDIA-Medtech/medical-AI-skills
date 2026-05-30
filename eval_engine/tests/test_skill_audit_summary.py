from eval_engine import skill_audit_summary


def _row(target: str, overall: str, *, advisory: int = 0) -> dict:
    return {
        "target": target,
        "target_path": target,
        "overall": overall,
        "tier1_passed": 20,
        "tier1_total": 20,
        "tier2_passed": 24,
        "tier2_total": 24,
        "blocking": 0,
        "advisory": advisory,
    }


def test_summary_passes_when_real_specs_pass_and_negative_fails() -> None:
    rows = [
        _row("dicom-metadata-extract", "pass"),
        _row("verifiers_ct_segmentation_quality_v1", "pass"),
        _row(skill_audit_summary.EXPECTED_NEGATIVE_TARGET, "fail"),
    ]

    summary = skill_audit_summary.summarize_rows(rows)

    assert summary["audit_status"] == "pass"
    assert summary["real_runs"] == 2
    assert summary["real_failed"] == 0
    assert summary["real_advisory_issues"] == 0
    assert summary["unexpected_failures"] == []
    assert summary["advisory_failures"] == []
    assert summary["calibration_failures"] == []


def test_summary_fails_on_real_spec_failure() -> None:
    rows = [
        _row("dicom-metadata-extract", "pass"),
        _row("nv-segment-ct", "fail"),
        _row(skill_audit_summary.EXPECTED_NEGATIVE_TARGET, "fail"),
    ]

    summary = skill_audit_summary.summarize_rows(rows)

    assert summary["audit_status"] == "fail"
    assert [item["target"] for item in summary["unexpected_failures"]] == ["nv-segment-ct"]
    assert summary["advisory_failures"] == []
    assert summary["calibration_failures"] == []


def test_summary_fails_on_real_spec_advisories() -> None:
    rows = [
        _row("dicom-metadata-extract", "pass"),
        _row("verifiers_ct_segmentation_quality_v1", "pass", advisory=2),
        _row(skill_audit_summary.EXPECTED_NEGATIVE_TARGET, "fail", advisory=10),
    ]

    summary = skill_audit_summary.summarize_rows(rows)

    assert summary["audit_status"] == "fail"
    assert summary["real_failed"] == 0
    assert summary["real_advisory_issues"] == 2
    assert [item["target"] for item in summary["advisory_failures"]] == [
        "verifiers_ct_segmentation_quality_v1"
    ]
    assert summary["unexpected_failures"] == []
    assert summary["calibration_failures"] == []


def test_summary_fails_when_negative_fixture_passes() -> None:
    rows = [
        _row("dicom-metadata-extract", "pass"),
        _row(skill_audit_summary.EXPECTED_NEGATIVE_TARGET, "pass"),
    ]

    summary = skill_audit_summary.summarize_rows(rows)

    assert summary["audit_status"] == "fail"
    assert summary["unexpected_failures"] == []
    assert summary["calibration_failures"][0]["target"] == skill_audit_summary.EXPECTED_NEGATIVE_TARGET


def test_formatted_summary_labels_calibration_failure_as_expected() -> None:
    rows = [
        _row("dicom-metadata-extract", "pass"),
        _row(skill_audit_summary.EXPECTED_NEGATIVE_TARGET, "fail"),
    ]
    summary = skill_audit_summary.summarize_rows(rows)

    text = skill_audit_summary.format_summary(summary)

    assert "real specs: 1/1 pass, 0 fail, 0 advisory issues" in text
    assert "negative_sloppy_skill: fail (expected fail)" in text
    assert "audit status: pass" in text


def test_single_output_summary_passes_when_no_advisories(tmp_path) -> None:
    path = tmp_path / "output.json"
    path.write_text(
        """
{
  "target_skill": "/repo/skills/dicom-metadata-extract",
  "tier1_structural": {"checks_passed": 20, "checks_total": 20},
  "tier2_spec_honesty": {"checks_passed": 24, "checks_total": 24},
  "overall": "pass",
  "blocking_issues_count": 0,
  "advisory_issues_count": 0
}
""".strip()
    )

    summary = skill_audit_summary.summarize_single_output(path)

    assert summary["audit_status"] == "pass"
    assert summary["row"]["target"] == "dicom-metadata-extract"
    assert "audit status: pass" in skill_audit_summary.format_single_summary(summary)


def test_single_output_summary_fails_on_advisories(tmp_path) -> None:
    path = tmp_path / "output.json"
    path.write_text(
        """
{
  "target_skill": "/repo/skills/vague-skill",
  "tier1_structural": {"checks_passed": 20, "checks_total": 20},
  "tier2_spec_honesty": {"checks_passed": 23, "checks_total": 24},
  "overall": "pass",
  "blocking_issues_count": 0,
  "advisory_issues_count": 1
}
""".strip()
    )

    summary = skill_audit_summary.summarize_single_output(path)

    assert summary["audit_status"] == "fail"
    assert summary["issues"] == ["advisory=1"]
    assert "strict failures: advisory=1" in skill_audit_summary.format_single_summary(summary)
