import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
VERIFIER = REPO_ROOT / "verifiers" / "ct_segmentation_quality_v1"
SCRIPT = VERIFIER / "scripts" / "grade.py"
RUNNER = REPO_ROOT / "eval_engine" / "run.py"


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


def test_pass_pack_passes_plausibility_and_skips_gt() -> None:
    payload = _run_script(VERIFIER / "fixtures" / "pass_pack")

    assert payload["overall"] == "pass"
    assert payload["target"]["skill_id"] == "nv_segment_ct"
    assert payload["artifact_inventory"]["label_map_readable"] is True
    assert payload["artifact_inventory"]["shape_match"] is True
    assert payload["artifact_inventory"]["affine_match"] is True

    plaus = payload["anatomy_plausibility"]
    assert plaus["verdict"] == "pass"
    assert plaus["classes_failing_volume_bounds"] == []
    assert plaus["classes_overfragmented"] == []
    assert plaus["cross_class"]["liver_gt_spleen"]["status"] == "pass"
    assert plaus["cross_class"]["bilateral_symmetry"]["status"] == "pass"
    names = {row["name"] for row in plaus["per_class"]}
    assert {"liver", "spleen", "right kidney", "left kidney"} <= names

    gt = payload["gt_metrics"]
    assert gt["verdict"] == "skipped"
    assert gt["acceptable"] is True


def test_fragmented_pack_fails_plausibility() -> None:
    payload = _run_script(VERIFIER / "fixtures" / "fragmented_pack")

    assert payload["overall"] == "fail"
    plaus = payload["anatomy_plausibility"]
    assert plaus["verdict"] == "fail"
    assert "spleen" in plaus["classes_overfragmented"]
    spleen = next(r for r in plaus["per_class"] if r["name"] == "spleen")
    assert spleen["component_count"] > 10
    assert spleen["largest_cc_fraction"] < 0.5


def test_gt_pass_pack_runs_gt_metrics_and_passes() -> None:
    payload = _run_script(VERIFIER / "fixtures" / "gt_pass_pack")

    assert payload["overall"] == "pass"
    gt = payload["gt_metrics"]
    assert gt["verdict"] == "pass"
    assert gt["acceptable"] is True
    assert gt["ground_truth_path"] is not None
    dice_by_name = {row["name"]: row["dice"] for row in gt["per_class"]}
    assert dice_by_name["liver"] == 1.0
    assert dice_by_name["spleen"] == 1.0
    assert all(row["dice_ok"] for row in gt["per_class"])


def test_canonical_manifest_skill_id_passes(tmp_path: Path) -> None:
    src = VERIFIER / "fixtures" / "pass_pack"
    pack = tmp_path / "canonical_manifest_id_pack"
    pack.mkdir()
    for child in src.iterdir():
        if child.is_file():
            (pack / child.name).write_bytes(child.read_bytes())
        elif child.is_dir():
            import shutil
            shutil.copytree(child, pack / child.name)

    manifest_path = pack / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["skill_id"] = "medagent.nv_segment_ct"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    payload = _run_script(pack)

    assert payload["target"]["skill_id"] == "medagent.nv_segment_ct"
    assert payload["overall"] == "pass"


def test_ctmr_canonical_manifest_skill_id_passes(tmp_path: Path) -> None:
    src = VERIFIER / "fixtures" / "pass_pack"
    pack = tmp_path / "ctmr_canonical_manifest_id_pack"
    pack.mkdir()
    for child in src.iterdir():
        if child.is_file():
            (pack / child.name).write_bytes(child.read_bytes())
        elif child.is_dir():
            import shutil

            shutil.copytree(child, pack / child.name)

    manifest_path = pack / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["skill_id"] = "medagent.nv_segment_ctmr"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    output_path = pack / "output.json"
    output = json.loads(output_path.read_text())
    output["skill"] = "nv_segment_ctmr"
    output["input"]["modality"] = "CT_BODY"
    output_path.write_text(json.dumps(output, indent=2))

    payload = _run_script(pack)

    assert payload["target"]["skill_id"] == "medagent.nv_segment_ctmr"
    assert payload["target"]["input_modality"] == "CT_BODY"
    assert payload["target"]["modality_supported"] is True
    assert payload["overall"] == "pass"


def test_ctmr_mri_body_manifest_skill_id_fails_this_ct_verifier(tmp_path: Path) -> None:
    src = VERIFIER / "fixtures" / "pass_pack"
    pack = tmp_path / "ctmr_mri_manifest_id_pack"
    pack.mkdir()
    for child in src.iterdir():
        if child.is_file():
            (pack / child.name).write_bytes(child.read_bytes())
        elif child.is_dir():
            import shutil

            shutil.copytree(child, pack / child.name)

    manifest_path = pack / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["skill_id"] = "medagent.nv_segment_ctmr"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    output_path = pack / "output.json"
    output = json.loads(output_path.read_text())
    output["skill"] = "nv_segment_ctmr"
    output["input"]["modality"] = "MRI_BODY"
    output_path.write_text(json.dumps(output, indent=2))

    payload = _run_script(pack)

    assert payload["target"]["skill_id"] == "medagent.nv_segment_ctmr"
    assert payload["target"]["input_modality"] == "MRI_BODY"
    assert payload["target"]["modality_supported"] is False
    assert payload["overall"] == "fail"


def test_label_set_subset_skips_when_no_requested(tmp_path: Path) -> None:
    """When the pack records no `label_prompts_requested`, the subset check
    can't compute a verdict — it should skip cleanly, not fail."""
    payload = _run_script(VERIFIER / "fixtures" / "pass_pack")
    subset = payload["label_set_subset"]
    # The committed pass_pack records label_prompts_requested = [1, 3, 5, 14]
    # and label_ids_present is the subset {1, 3, 5, 14}. Subset passes.
    assert subset["verdict"] in ("pass", "skipped"), payload
    if subset["verdict"] == "pass":
        assert subset["extras"] == []


def test_label_set_subset_fails_when_extras_present(tmp_path: Path) -> None:
    """Synthesize a pack where the agent's output contains classes that
    weren't in `label_prompts_requested` — verifier must fail."""
    src = VERIFIER / "fixtures" / "pass_pack"
    # Copy the pack to tmp and mutate output.json
    pack = tmp_path / "extras_pack"
    pack.mkdir()
    for child in src.iterdir():
        if child.is_file():
            (pack / child.name).write_bytes(child.read_bytes())
        elif child.is_dir():
            import shutil
            shutil.copytree(child, pack / child.name)
    # Mutate: request only spleen (3), but record present = [1,3,5,14,7,29,32]
    # (i.e. liver, right/left kidney + portal vein + colon + stomach as
    # extras the agent didn't ask for). Anatomy-plausibility passes each one
    # individually; only the subset check should catch the mismatch.
    out_json = pack / "output.json"
    payload = json.loads(out_json.read_text())
    payload["output"]["label_prompts_requested"] = [3]  # only spleen requested
    out_json.write_text(json.dumps(payload, indent=2))

    result = _run_script(pack)
    subset = result["label_set_subset"]
    assert subset["verdict"] == "fail", result
    assert subset["requested"] == [3]
    assert set(subset["extras"]).issuperset({1, 5, 14}), subset
    assert result["overall"] == "fail"


def test_eval_engine_run_validates_pass_pack(tmp_path: Path) -> None:
    out = tmp_path / "verifier_pack"
    proc = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            str(VERIFIER),
            "--fixture",
            str(VERIFIER / "fixtures" / "pass_pack"),
            "--out",
            str(out),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    validation = json.loads((out / "validation_summary.json").read_text())
    assert validation["overall_status"] == "passed"
    assert validation["sanity_status"] == "passed"
