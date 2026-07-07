#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Export a privacy-limited Medical AI Skills evidence summary to MLflow."""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

SKILL_NAME = "mlflow_evidence_export"
MODES = ("dry-run", "local", "databricks")


def _load_json(path: Path, *, required: bool = True) -> dict[str, Any]:
    if not path.is_file():
        if required:
            raise ValueError(f"missing evidence-pack file: {path}")
        return {}
    try:
        payload = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"cannot read JSON object from {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return payload


def resolve_pack_dir(source: Path) -> tuple[Path, Path]:
    """Resolve either a direct evidence pack or a trusted-run root."""
    root = source.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"evidence pack is not a directory: {root}")
    if (root / "manifest.json").is_file():
        return root, root
    skill_run = root / "skill_run"
    if (skill_run / "manifest.json").is_file():
        return skill_run, root
    raise ValueError(
        f"{root} is neither an evidence pack nor a trusted-run directory with skill_run/"
    )


def _scalar_metrics(candidate: Any) -> dict[str, float]:
    """Keep only scalar (non-bool) numbers from a candidate metrics object."""
    if not isinstance(candidate, dict):
        return {}
    return {
        str(key): float(value)
        for key, value in candidate.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }


def collect_from_result(result_path: Path) -> dict[str, Any]:
    """Collect comparison-safe fields from a direct skill-run result JSON.

    A direct run of a skill (e.g. a Databricks notebook calling the wrapper) emits
    its result JSON to stdout, not an eval-engine evidence pack. Redirect it to a
    file (``... > result.json``) and pass that file here. Only a curated, scalar
    ``metrics`` block plus identity tags are logged; raw nested fields and file
    paths are never uploaded.
    """
    result = _load_json(result_path)
    skill_id = result.get("skill_id") or result.get("skill")
    skill_version = result.get("skill_version") or result.get("version")
    metrics = _scalar_metrics(result.get("metrics"))

    tags = {
        "medical_ai_skills.not_clinical": "true",
        "medical_ai_skills.intended_use": "engineering_verification",
        "medical_ai_skills.pack_kind": "direct_run",
    }
    optional_tags = {
        "medical_ai_skills.run_id": result.get("run_id"),
        "medical_ai_skills.skill_id": skill_id,
        "medical_ai_skills.skill_version": skill_version,
        "medical_ai_skills.validation_overall": result.get("validation_overall"),
    }
    tags.update({key: str(value) for key, value in optional_tags.items() if value is not None})

    return {
        "source": {
            "pack_path": str(result_path),
            "pack_kind": "direct_run",
            "skill_id": skill_id,
            "skill_version": skill_version,
        },
        "tags": tags,
        "metrics": metrics,
        "logged_summary": {
            "pack_kind": "direct_run",
            "skill_id": skill_id,
            "skill_version": skill_version,
            "metrics": metrics,
        },
    }


def collect_summary(source: Path) -> dict[str, Any]:
    """Collect only comparison-safe fields; do not copy raw pack artifacts."""
    resolved = source.expanduser().resolve()
    if resolved.is_file():
        return collect_from_result(resolved)
    pack, root = resolve_pack_dir(source)
    manifest = _load_json(pack / "manifest.json")
    validation = _load_json(pack / "validation_summary.json")
    runtime = _load_json(pack / "runtime_profile.json")
    trust = _load_json(root / "trust_summary.json", required=False)

    tags = {
        "medical_ai_skills.not_clinical": "true",
        "medical_ai_skills.intended_use": "engineering_verification",
        "medical_ai_skills.pack_kind": str(manifest.get("pack_kind", "unknown")),
    }
    optional_tags = {
        "medical_ai_skills.run_id": manifest.get("run_id"),
        "medical_ai_skills.skill_id": manifest.get("skill_id"),
        "medical_ai_skills.skill_version": manifest.get("skill_version"),
        "medical_ai_skills.repo_git_sha": manifest.get("repo_git_sha"),
        "medical_ai_skills.validation_overall": validation.get("overall_status"),
        "medical_ai_skills.trust_overall": trust.get("overall"),
    }
    tags.update({key: str(value) for key, value in optional_tags.items() if value is not None})

    metrics: dict[str, float] = {}
    for key in ("elapsed_seconds", "exit_code"):
        value = runtime.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            metrics[key] = float(value)

    return {
        "source": {
            "pack_path": str(pack),
            "pack_kind": str(manifest.get("pack_kind", "unknown")),
            "skill_id": manifest.get("skill_id"),
            "skill_version": manifest.get("skill_version"),
        },
        "tags": tags,
        "metrics": metrics,
        "logged_summary": {
            "pack_kind": manifest.get("pack_kind"),
            "skill_id": manifest.get("skill_id"),
            "skill_version": manifest.get("skill_version"),
            "validation_overall": validation.get("overall_status"),
            "trust_overall": trust.get("overall"),
            "metrics": metrics,
        },
    }


def _mlflow_available() -> bool:
    try:
        return importlib.util.find_spec("mlflow") is not None
    except (ImportError, ValueError):
        return False


def _tracking_uri(mode: str, requested: str | None) -> str:
    if requested:
        return requested
    if mode == "databricks":
        return "databricks"
    return (Path.cwd() / "mlruns").resolve().as_uri()


def log_summary(
    summary: dict[str, Any],
    *,
    mode: str,
    tracking_uri: str | None,
    experiment_name: str | None,
    run_name: str | None,
    mlflow_module: Any | None = None,
) -> dict[str, Any]:
    """Log one sanitized summary. Errors are returned as data."""
    uri = _tracking_uri(mode, tracking_uri)
    try:
        if mode == "local" and uri.startswith("file:"):
            os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
        mlflow = mlflow_module or importlib.import_module("mlflow")
        mlflow.set_tracking_uri(uri)
        if experiment_name:
            mlflow.set_experiment(experiment_name)
        with mlflow.start_run(run_name=run_name) as active_run:
            mlflow.set_tags(summary["tags"])
            if summary["metrics"]:
                mlflow.log_metrics(summary["metrics"])
            mlflow.log_dict(
                summary["logged_summary"],
                "medical_ai_skills/evidence_summary.json",
            )
            run_id = active_run.info.run_id
    except Exception as exc:
        return {
            "available": mlflow_module is not None or _mlflow_available(),
            "tracking_uri": uri,
            "experiment_name": experiment_name,
            "run_id": None,
            "error": f"{type(exc).__name__}: {exc}",
        }
    return {
        "available": True,
        "tracking_uri": uri,
        "experiment_name": experiment_name,
        "run_id": run_id,
        "error": None,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source",
        type=Path,
        help="Evidence pack, trusted-run directory, or direct result JSON",
    )
    parser.add_argument("--mode", choices=MODES, default="dry-run")
    parser.add_argument("--tracking-uri")
    parser.add_argument("--experiment-name")
    parser.add_argument("--run-name")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = collect_summary(args.source)
    except ValueError as exc:
        print(
            json.dumps(
                {
                    "skill": SKILL_NAME,
                    "status": "failed",
                    "mode": args.mode,
                    "source": {
                        "pack_path": str(args.source),
                        "pack_kind": "unknown",
                        "skill_id": None,
                        "skill_version": None,
                    },
                    "tags": {},
                    "metrics": {},
                    "mlflow": {
                        "available": _mlflow_available(),
                        "tracking_uri": args.tracking_uri,
                        "experiment_name": args.experiment_name,
                        "run_id": None,
                        "error": str(exc),
                    },
                    "intended_use_disclaimer": "Engineering verification only.",
                },
                indent=2,
            )
        )
        return 2

    payload = {
        "skill": SKILL_NAME,
        "status": "dry_run",
        "mode": args.mode,
        "source": summary["source"],
        "tags": summary["tags"],
        "metrics": summary["metrics"],
        "mlflow": {
            "available": _mlflow_available(),
            "tracking_uri": args.tracking_uri,
            "experiment_name": args.experiment_name,
            "run_id": None,
            "error": None,
        },
        "intended_use_disclaimer": (
            "Engineering verification only. The prototype logs a sanitized summary, "
            "not raw medical data or evidence-pack artifacts."
        ),
    }
    if args.mode != "dry-run":
        payload["mlflow"] = log_summary(
            summary,
            mode=args.mode,
            tracking_uri=args.tracking_uri,
            experiment_name=args.experiment_name,
            run_name=args.run_name or f"evidence:{Path(summary['source']['pack_path']).name}",
        )
        payload["status"] = "logged" if payload["mlflow"]["error"] is None else "failed"

    print(json.dumps(payload, indent=2))
    return 0 if payload["status"] != "failed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
