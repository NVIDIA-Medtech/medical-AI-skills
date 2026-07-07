# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "export_evidence_pack.py"
spec = importlib.util.spec_from_file_location("export_evidence_pack", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def _write_pack(path: Path) -> None:
    path.mkdir(parents=True)
    (path / "manifest.json").write_text(
        json.dumps(
            {
                "pack_kind": "skill_run",
                "run_id": "test-run",
                "skill_id": "medagent.test",
                "skill_version": "1.0.0",
            }
        )
    )
    (path / "validation_summary.json").write_text(json.dumps({"overall_status": "passed"}))
    (path / "runtime_profile.json").write_text(json.dumps({"elapsed_seconds": 2.5, "exit_code": 0}))


def test_collect_summary_accepts_trusted_run_root(tmp_path: Path) -> None:
    pack = tmp_path / "trusted" / "skill_run"
    _write_pack(pack)
    (tmp_path / "trusted" / "trust_summary.json").write_text(json.dumps({"overall": "passed"}))

    summary = mod.collect_summary(tmp_path / "trusted")

    assert summary["source"]["skill_id"] == "medagent.test"
    assert summary["tags"]["medical_ai_skills.trust_overall"] == "passed"
    assert summary["metrics"] == {"elapsed_seconds": 2.5, "exit_code": 0.0}


def test_collect_summary_accepts_direct_run_result(tmp_path: Path) -> None:
    result_path = tmp_path / "result.json"
    result_path.write_text(
        json.dumps(
            {
                "skill": "medagent.nv_generate_ct_rflow",
                "version": "0.3.0",
                "run_id": "demo-run",
                "metrics": {"generation_time_s": 118.4, "exit_code": 0, "ok": True},
                "output": {"path": "/private/patient/scan.nii.gz"},
            }
        )
    )

    summary = mod.collect_summary(result_path)

    assert summary["source"]["pack_kind"] == "direct_run"
    assert summary["source"]["skill_id"] == "medagent.nv_generate_ct_rflow"
    # scalars kept, bool dropped, no raw output path leaked into the logged summary
    assert summary["metrics"] == {"generation_time_s": 118.4, "exit_code": 0.0}
    assert "/private/patient" not in json.dumps(summary["logged_summary"])


def test_main_defaults_to_dry_run(tmp_path: Path, capsys) -> None:
    pack = tmp_path / "pack"
    _write_pack(pack)

    return_code = mod.main([str(pack)])
    payload = json.loads(capsys.readouterr().out)

    assert return_code == 0
    assert payload["status"] == "dry_run"
    assert payload["mode"] == "dry-run"
    assert payload["mlflow"]["run_id"] is None


def test_main_reports_invalid_pack_as_schema_shaped_failure(tmp_path: Path, capsys) -> None:
    return_code = mod.main([str(tmp_path / "missing")])
    payload = json.loads(capsys.readouterr().out)

    assert return_code == 2
    assert payload["status"] == "failed"
    assert payload["source"]["pack_kind"] == "unknown"
    assert "not a directory" in payload["mlflow"]["error"]


def test_log_summary_uses_only_sanitized_payload(tmp_path: Path) -> None:
    pack = tmp_path / "pack"
    _write_pack(pack)
    summary = mod.collect_summary(pack)

    class ActiveRun:
        info = type("Info", (), {"run_id": "fake-run"})()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeMlflow:
        def __init__(self):
            self.logged_dict = None

        def set_tracking_uri(self, uri):
            self.uri = uri

        def set_experiment(self, name):
            self.experiment = name

        def start_run(self, run_name=None):
            self.run_name = run_name
            return ActiveRun()

        def set_tags(self, tags):
            self.tags = tags

        def log_metrics(self, metrics):
            self.metrics = metrics

        def log_dict(self, payload, path):
            self.logged_dict = payload
            self.logged_path = path

    fake = FakeMlflow()
    result = mod.log_summary(
        summary,
        mode="local",
        tracking_uri="file:///tmp/mlruns",
        experiment_name="test",
        run_name="test-run",
        mlflow_module=fake,
    )

    assert result["run_id"] == "fake-run"
    assert fake.logged_path == "medical_ai_skills/evidence_summary.json"
    assert str(pack) not in json.dumps(fake.logged_dict)
