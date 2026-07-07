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

import hashlib
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_finetune.py"
spec = importlib.util.spec_from_file_location("run_finetune", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def test_prepare_bundle_files_stages_train_configs_from_local_upstream(tmp_path, monkeypatch):
    bundle = tmp_path / "skill" / "bundle"
    upstream_configs = (
        tmp_path / ".workbench_data" / "upstreams" / "NV-Segment-CTMR" / "NV-Segment-CT" / "configs"
    )
    upstream_configs.mkdir(parents=True)
    for name in (
        "train.json",
        "train_continual.json",
        "multi_gpu_train.json",
        "evaluate.json",
    ):
        (upstream_configs / name).write_text(f'{{"name": "{name}"}}\n')
    trainer_payload = b"pinned trainer\n"
    (upstream_configs.parent / "scripts").mkdir()
    (upstream_configs.parent / "scripts" / "trainer.py").write_bytes(trainer_payload)
    (bundle / "configs").mkdir(parents=True)
    (bundle / "metadata.json").write_text("{}\n")
    (bundle / "vista3d_pretrained_model").mkdir(parents=True)
    (bundle / "vista3d_pretrained_model" / "model.pt").write_bytes(b"model")
    (bundle / "label_dict.json").write_text('{"lung tumor": 23}\n')

    monkeypatch.setattr(mod, "BUNDLE_DIR", bundle)
    monkeypatch.setattr(mod, "SKILL_DIR", tmp_path / "skill")
    monkeypatch.setattr(mod, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(mod, "LABEL_DICT", bundle / "label_dict.json")
    monkeypatch.setattr(mod, "UPSTREAM_TRAINER_SHA256", hashlib.sha256(trainer_payload).hexdigest())

    notes = mod.prepare_bundle_files()

    for name in (
        "train.json",
        "train_continual.json",
        "multi_gpu_train.json",
        "evaluate.json",
    ):
        assert (bundle / "configs" / name).read_text() == f'{{"name": "{name}"}}\n'
    assert (bundle / "configs" / "metadata.json").is_file()
    assert (bundle / "models" / "model.pt").is_file()
    assert (bundle / "scripts" / "trainer.py").read_bytes() == trainer_payload
    assert "restored configs/train.json from local upstream cache" in notes


def test_prepare_bundle_files_restores_drifted_train_configs(tmp_path, monkeypatch):
    bundle = tmp_path / "skill" / "bundle"
    upstream_configs = (
        tmp_path / ".workbench_data" / "upstreams" / "NV-Segment-CTMR" / "NV-Segment-CT" / "configs"
    )
    upstream_configs.mkdir(parents=True)
    for name in (
        "train.json",
        "train_continual.json",
        "multi_gpu_train.json",
        "evaluate.json",
    ):
        (upstream_configs / name).write_text(f'{{"canonical": "{name}"}}\n')
    trainer_payload = b"pinned trainer\n"
    (upstream_configs.parent / "scripts").mkdir()
    (upstream_configs.parent / "scripts" / "trainer.py").write_bytes(trainer_payload)
    (bundle / "configs").mkdir(parents=True)
    for name in (
        "train.json",
        "train_continual.json",
        "multi_gpu_train.json",
        "evaluate.json",
    ):
        (bundle / "configs" / name).write_text(f'{{"drifted": "{name}"}}\n')
    (bundle / "metadata.json").write_text("{}\n")
    (bundle / "vista3d_pretrained_model").mkdir(parents=True)
    (bundle / "vista3d_pretrained_model" / "model.pt").write_bytes(b"model")
    (bundle / "label_dict.json").write_text('{"lung tumor": 23}\n')

    monkeypatch.setattr(mod, "BUNDLE_DIR", bundle)
    monkeypatch.setattr(mod, "SKILL_DIR", tmp_path / "skill")
    monkeypatch.setattr(mod, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(mod, "LABEL_DICT", bundle / "label_dict.json")
    monkeypatch.setattr(mod, "UPSTREAM_TRAINER_SHA256", hashlib.sha256(trainer_payload).hexdigest())

    notes = mod.prepare_bundle_files()

    assert (bundle / "configs" / "evaluate.json").read_text() == '{"canonical": "evaluate.json"}\n'
    assert (bundle / "scripts" / "trainer.py").read_bytes() == trainer_payload
    assert "restored configs/evaluate.json from local upstream cache" in notes


def test_upstream_config_dirs_accept_explicit_local_checkout(tmp_path, monkeypatch):
    config_dir = (
        tmp_path / ".workbench_data" / "upstreams" / "NV-Segment-CTMR" / "NV-Segment-CT" / "configs"
    )
    config_dir.mkdir(parents=True)
    monkeypatch.setattr(mod, "_REPO_ROOT", tmp_path)

    assert config_dir in mod._upstream_config_dirs()


def test_build_override_defines_bundle_image_and_label_keys(tmp_path):
    override = mod.build_override(
        tmp_path / "dataset",
        tmp_path / "datalist.json",
        {"default": [[1, 3]]},
        [64, 64, 64],
        1.0,
        2,
        5e-5,
        tmp_path / "checkpoints",
        tmp_path / "val_during_train",
    )

    assert override["image_key"] == "image"
    assert override["label_key"] == "label"


def test_build_override_auto_seg_matches_task06_prompt_settings(tmp_path):
    override = mod.build_override(
        tmp_path / "dataset",
        tmp_path / "datalist.json",
        {"default": [[1, 23]]},
        [128, 128, 128],
        1.0,
        5,
        5e-5,
        tmp_path / "checkpoints",
        tmp_path / "val_during_train",
        auto_seg=True,
    )

    assert override["drop_label_prob"] == 0.0
    assert override["drop_point_prob"] == 1.0
    expected_spacing = tuple(float("1.5") for _ in range(3))
    assert override["resample_to_spacing"] == expected_spacing


def test_task06_fixture_selects_sanity_preset() -> None:
    assert mod._fixture_preset(Path("/data/Task06")) == "sanity"
    assert mod._fixture_preset(Path("/data/Task06_Lung")) == "sanity"
    assert mod._fixture_preset(Path("/data/spleen_micro")) == "smoke"


def test_monai_runtime_pin_is_exact(monkeypatch):
    monkeypatch.setattr(mod, "package_version", lambda _name: "1.4.1")

    assert mod._monai_is_compatible() is False
    with pytest.raises(mod.typer.BadParameter, match="monai==1.4.0"):
        mod.require_compatible_runtime()


def test_sanity_dataset_prefers_explicit_paths(tmp_path):
    fixture = tmp_path / "Task06"
    explicit = tmp_path / "explicit_task06"
    fixture.mkdir()
    explicit.mkdir()

    assert mod._resolve_sanity_dataset(fixture, None) == fixture.resolve()
    assert mod._resolve_sanity_dataset(fixture, explicit) == explicit.resolve()


def test_ensure_smoke_dataset_materializes_missing_niftis(tmp_path):
    dataset = tmp_path / "spleen_micro"
    dataset.mkdir()
    datalist = dataset / "datalist.json"
    datalist.write_text("""
{
  "training": [
    {"image": "imagesTr/spleen_00.nii.gz", "label": "labelsTr/spleen_00.nii.gz", "fold": 0},
    {"image": "imagesTr/spleen_01.nii.gz", "label": "labelsTr/spleen_01.nii.gz", "fold": 1}
  ],
  "testing": []
}
""")

    smoke_dir, smoke_datalist, generated = mod.ensure_smoke_dataset(
        dataset, datalist, tmp_path / "run"
    )

    assert generated is True
    assert smoke_datalist == smoke_dir / "datalist.json"
    assert (smoke_dir / "imagesTr" / "spleen_00.nii.gz").is_file()
    assert (smoke_dir / "labelsTr" / "spleen_01.nii.gz").is_file()


def test_metric_compat_config_stack_skips_when_mean_dice_accepts_num_classes(
    monkeypatch,
):
    monkeypatch.setattr(mod, "_mean_dice_accepts_num_classes", lambda: True)

    assert mod.metric_compat_config_stack() == []


def test_metric_compat_config_stack_writes_only_when_needed(tmp_path, monkeypatch):
    bundle = tmp_path / "bundle"
    monkeypatch.setattr(mod, "BUNDLE_DIR", bundle)
    monkeypatch.setattr(mod, "_mean_dice_accepts_num_classes", lambda: False)

    stack = mod.metric_compat_config_stack()

    assert stack == ["configs/mean_dice_no_num_classes.json"]
    payload = (bundle / "configs" / "mean_dice_no_num_classes.json").read_text()
    assert '"num_classes"' not in payload


def test_sanity_reference_checks_fail_low_recovery_run():
    checks = mod.sanity_reference_checks(
        formal_pretrained=0.6258574724197388,
        formal_finetuned=0.6258574724197388,
        formal_improvement=0.0,
        training_start=0.6326,
        training_best=0.6326,
        training_improvement=0.0,
        best_checkpoint_changed=False,
        overall_rc=0,
    )

    assert checks["passed"] is False
    assert "formal_pretrained_val_dice_ok" in checks["failed_checks"]
    assert "formal_improvement_ok" in checks["failed_checks"]
    assert "training_best_val_dice_ok" in checks["failed_checks"]
    assert "best_checkpoint_changed_ok" in checks["failed_checks"]


def test_sanity_reference_checks_pass_dwf_reference_like_run():
    checks = mod.sanity_reference_checks(
        formal_pretrained=0.67,
        formal_finetuned=0.684,
        formal_improvement=0.014,
        training_start=0.676,
        training_best=0.691,
        training_improvement=0.015,
        best_checkpoint_changed=True,
        overall_rc=0,
    )

    assert checks["passed"] is True
    assert checks["failed_checks"] == []


def test_compare_checkpoint_weights_detects_reserialized_identical_weights(tmp_path):
    torch = pytest.importorskip("torch")
    reference = tmp_path / "reference.pt"
    candidate = tmp_path / "candidate.pt"
    state = {"layer.weight": torch.ones(2, 2)}

    torch.save(state, reference)
    torch.save({"layer.weight": state["layer.weight"].clone()}, candidate)

    comparison = mod.compare_checkpoint_weights(reference, candidate)

    assert comparison["compared"] is True
    assert comparison["weights_identical"] is True
    assert comparison["differing_tensors"] == 0


def test_compare_checkpoint_weights_detects_changed_tensor(tmp_path):
    torch = pytest.importorskip("torch")
    reference = tmp_path / "reference.pt"
    candidate = tmp_path / "candidate.pt"

    torch.save({"layer.weight": torch.ones(2, 2)}, reference)
    torch.save({"layer.weight": torch.zeros(2, 2)}, candidate)

    comparison = mod.compare_checkpoint_weights(reference, candidate)

    assert comparison["compared"] is True
    assert comparison["weights_identical"] is False
    assert comparison["differing_tensors"] == 1
    assert comparison["max_abs_diff"] == 1.0


def _mlflow_test_result(tmp_path: Path) -> dict:
    return {
        "skill": "nv_segment_ct_finetune",
        "version": "0.4.3",
        "input": {"dataset_dir": str(tmp_path / "sensitive-case-name")},
        "plan": {
            "preset": "smoke",
            "epochs": 2,
            "learning_rate": 5e-5,
            "patch_size": [64, 64, 64],
            "nproc_per_node": 1,
        },
        "output": {
            "training_start_val_dice": 0.4,
            "training_best_val_dice": 0.6,
            "formal_pretrained_val_dice": None,
            "formal_finetuned_val_dice": None,
            "formal_improvement_over_pretrained": None,
            "val_dice_per_epoch": [0.4, 0.6],
        },
        "runtime": {"wall_seconds": 4.0, "peak_gpu_mb": 100, "return_code": 0},
    }


def test_mlflow_off_is_noop(tmp_path):
    result = mod.log_finetune_summary_to_mlflow(
        _mlflow_test_result(tmp_path),
        tmp_path,
        mode="off",
    )

    assert result is None


def test_live_tracking_settings_are_tracking_only():
    settings = mod.build_monai_mlflow_tracking_settings("http://mlflow:5000", "demo", "run")

    configs = settings["configs"]
    assert set(configs) == mod.MLFLOW_TRACKING_CONFIG_KEYS
    assert configs["train#dataloader#multiprocessing_context"] == "spawn"
    assert configs["validate#dataloader#multiprocessing_context"] == "spawn"
    assert configs["trainer"]["iteration_log"] is True
    assert configs["validator"]["epoch_log"] is True
    assert "patch_size" not in configs


def test_prepare_live_mlflow_run_writes_settings_and_precreates_run(tmp_path, monkeypatch):
    class Client:
        def create_run(self, experiment_id, run_name=None, tags=None):
            self.created = (experiment_id, run_name, tags)
            return type("Run", (), {"info": type("Info", (), {"run_id": "live-run"})()})()

    class FakeMlflow:
        def __init__(self):
            self.client = Client()

        def set_tracking_uri(self, uri):
            self.uri = uri

        def set_experiment(self, name):
            self.experiment = name
            return type("Experiment", (), {"experiment_id": "7"})()

        def MlflowClient(self, tracking_uri=None):
            self.client.tracking_uri = tracking_uri
            return self.client

    fake = FakeMlflow()
    monkeypatch.delenv("MLFLOW_ALLOW_FILE_STORE", raising=False)
    live = mod.prepare_live_mlflow_run(
        tmp_path,
        tracking_uri="file:///tmp/mlruns",
        experiment_name="demo",
        requested_run_name="task06",
        preset="sanity",
        mlflow_module=fake,
    )

    assert live["status"] == "ready"
    assert live["run_id"] == "live-run"
    assert Path(live["tracking_settings_file"]).is_file()
    assert fake.client.created[0] == "7"
    assert mod.os.environ["MLFLOW_ALLOW_FILE_STORE"] == "true"


def test_mlflow_summary_logs_safe_post_run_fields(tmp_path):
    class ActiveRun:
        info = type("Info", (), {"run_id": "fake-run"})()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeMlflow:
        def set_tracking_uri(self, uri):
            self.uri = uri

        def set_experiment(self, name):
            self.experiment = name

        def start_run(self, run_name=None, run_id=None):
            self.run_name = run_name
            self.run_id = run_id
            return ActiveRun()

        def end_run(self, status=None):
            self.end_status = status

        def set_tags(self, tags):
            self.tags = tags

        def log_params(self, params):
            self.params = params

        def log_metrics(self, metrics):
            self.metrics = metrics

        def log_metric(self, name, value, step=None):
            self.last_step_metric = (name, value, step)

        def log_dict(self, payload, path):
            self.logged_dict = payload
            self.logged_path = path

    fake = FakeMlflow()
    result = mod.log_finetune_summary_to_mlflow(
        _mlflow_test_result(tmp_path),
        tmp_path,
        mode="local",
        experiment_name="test",
        mlflow_module=fake,
    )

    assert result["status"] == "logged"
    assert result["run_id"] == "fake-run"
    assert fake.end_status == "FINISHED"
    assert fake.last_step_metric == ("validation_dice", 0.6, 1)
    assert "sensitive-case-name" not in str(fake.logged_dict)

    live = {
        "tracking_uri": "http://mlflow:5000",
        "experiment_name": "test",
        "run_name": "live-name",
        "run_id": "existing-run",
        "tracking_settings_file": str(tmp_path / "tracking.json"),
    }
    live_fake = FakeMlflow()
    live_result = mod.log_finetune_summary_to_mlflow(
        _mlflow_test_result(tmp_path),
        tmp_path,
        mode="databricks",
        live_run=live,
        mlflow_module=live_fake,
    )

    assert live_fake.run_id == "existing-run"
    assert not hasattr(live_fake, "last_step_metric")
    assert live_result["live_tracking"] is True


def test_mlflow_failure_is_returned_as_data(tmp_path):
    class BrokenMlflow:
        def set_tracking_uri(self, uri):
            raise RuntimeError("tracking unavailable")

    result = mod.log_finetune_summary_to_mlflow(
        _mlflow_test_result(tmp_path),
        tmp_path,
        mode="local",
        mlflow_module=BrokenMlflow(),
    )

    assert result["status"] == "failed"
    assert "tracking unavailable" in result["error"]
