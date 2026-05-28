import argparse
import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_mr_brain_finetune.py"
spec = importlib.util.spec_from_file_location("run_mr_brain_finetune", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def _write_datalist(root: Path, image_name: str = "imagesTr/case001.nii.gz") -> Path:
    image = root / image_name
    image.parent.mkdir(parents=True)
    image.write_text("placeholder\n")
    datalist = root / "datalist.json"
    datalist.write_text(json.dumps({"training": [{"image": image_name}], "testing": []}))
    return datalist


def _args(tmp_path: Path, datalist: Path) -> argparse.Namespace:
    return argparse.Namespace(
        output_dir=tmp_path / "out",
        data_base_dir=tmp_path,
        datalist=datalist,
        modality="mri_t1",
        epochs=2,
        batch_size=1,
        lr=1e-5,
        cache_rate=0.0,
        num_gpus=1,
        autoencoder_num_splits=2,
        infer_dim=[64, 64, 64],
        infer_spacing=[1.0, 1.0, 1.0],
        top_region_index=[0, 1, 0, 0],
        bottom_region_index=[0, 0, 1, 0],
        random_seed=123,
        num_inference_steps=4,
        cfg_guidance_scale=10.0,
        output_prefix="test",
        download_model_data=False,
        train_from_scratch=False,
        skip_create_training_data=False,
        skip_train=False,
        run_inference=True,
        no_amp=True,
        existing_ckpt_filepath=None,
        trained_autoencoder_path=None,
        model_filename="",
        preflight=True,
    )


def _fake_upstream(root: Path) -> Path:
    configs = root / "configs"
    scripts = root / "scripts"
    configs.mkdir(parents=True)
    scripts.mkdir()
    for script in (
        "download_model_data.py",
        "diff_model_create_training_data.py",
        "diff_model_train.py",
        "diff_model_infer.py",
    ):
        (scripts / script).write_text("")
    (configs / "config_network_rflow.json").write_text(
        json.dumps({"include_body_region": False, "autoencoder_def": {"num_splits": 4}})
    )
    (configs / "environment_maisi_diff_model_rflow-mr-brain.json").write_text(
        json.dumps(
            {
                "trained_autoencoder_path": "models/autoencoder_v1.pt",
                "existing_ckpt_filepath": "models/diff_unet_3d_rflow-mr-brain_v0.pt",
                "model_filename": "diff_unet_3d_rflow-mr-brain_v0.pt",
            }
        )
    )
    (configs / "config_maisi_diff_model_rflow-mr-brain.json").write_text(
        json.dumps({"diffusion_unet_train": {}, "diffusion_unet_inference": {}})
    )
    (configs / "modality_mapping.json").write_text(json.dumps({"mri_t1": 9}))
    return root


def test_validate_datalist_accepts_relative_images_and_default_modality(tmp_path: Path) -> None:
    datalist = _write_datalist(tmp_path)

    summary = mod._validate_datalist(tmp_path, datalist, "mri_t1")

    assert summary["training_cases"] == 1
    assert summary["testing_cases"] == 0
    assert summary["modalities"] == ["mri_t1"]


def test_validate_datalist_rejects_missing_image(tmp_path: Path) -> None:
    datalist = tmp_path / "datalist.json"
    datalist.write_text(json.dumps({"training": [{"image": "missing.nii.gz"}]}))

    with pytest.raises(FileNotFoundError):
        mod._validate_datalist(tmp_path, datalist, "mri_t1")


def test_stage_configs_targets_existing_upstream_scripts(tmp_path: Path) -> None:
    datalist = _write_datalist(tmp_path)
    args = _args(tmp_path, datalist)
    upstream = _fake_upstream(tmp_path / "upstream")

    staged = mod._stage_configs(args, upstream)
    plan = mod._build_command_plan(args, upstream, staged)

    modules = [" ".join(cmd) for cmd in plan]
    assert any("scripts.diff_model_create_training_data" in cmd for cmd in modules)
    assert any("scripts.diff_model_train" in cmd for cmd in modules)
    assert any("scripts.diff_model_infer" in cmd for cmd in modules)
    assert not any("diff_model_train_workflow" in cmd for cmd in modules)
    staged_env = json.loads(Path(staged["env_config"]).read_text())
    assert staged_env["json_data_list"].endswith("workflow/dataset.json")
    assert staged_env["modality_mapping_path"].endswith("configs/modality_mapping.json")


def test_preflight_payload_succeeds_without_upstream(tmp_path: Path) -> None:
    datalist = _write_datalist(tmp_path)
    args = _args(tmp_path, datalist)
    args.output_dir.mkdir()
    dataset = mod._validate_datalist(tmp_path, datalist, "mri_t1")

    payload = mod._payload(args, dataset, None, ["/missing"], [["python"]], 0, 0.1)

    assert payload["skill"] == "nv_generate_mr_brain_finetune"
    assert payload["runtime"]["preflight_only"] is True
    assert payload["invocation"]["official_entrypoint"] == mod.UPSTREAM_ENTRYPOINT
    assert payload["invocation"]["exit_code"] == 0
