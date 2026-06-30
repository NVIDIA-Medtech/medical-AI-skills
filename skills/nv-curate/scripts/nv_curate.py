#!/usr/bin/env python3
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

"""nv-curate — medical data-curation orchestrator (MR-RATE reports pipeline).

Deterministic, stdlib-only orchestrator that drives the report-preprocessing
skills (report-anonymization -> report-translation -> report-structuring ->
report-pathology-classification) and assembles an AI-ready dataset described by
a ``datasources.json`` config. Three actions map to the three end-user prompts:

* ``plan``     (prompt 1): inventory a raw-data directory and emit a
  ``datasources.json`` curation plan + an inventory summary.
* ``curate``   (prompt 2, default): run the transform pipeline on the configured
  raw data and assemble an AI-ready datalist (de-identified, structured,
  labeled), joined by study id.
* ``finetune`` (prompt 3): run ``curate`` then build the MONAI datalist and
  report hand-off readiness for the nv-generate-mr-brain-finetune skill.

Each stage is its own gated skill, invoked by subprocess; nv-curate records each
stage's key metric. Only the final JSON summary goes to stdout; logs to stderr.

The orchestrator itself never loads a model or a GPU. Stage skills run in
``--mode mock`` (deterministic, GPU-free) or ``--mode live`` (upstream vLLM).
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

SKILL_NAME = "nv-curate"
SKILLS_DIR = Path(__file__).resolve().parents[2]  # skills/

# Pipeline stages. Each stage's input is the previous stage's output file; the
# very first input is the raw reports CSV. Entrypoints + column handoffs are
# pinned (these are sibling skills in this pack).
STAGES = [
    {
        "step": "anonymize",
        "skill": "report-anonymization",
        "entrypoint": "scripts/run_anonymization.py",
        "id_col": "UID",
        "text_col": "report",
        "out_file": "anonymized.csv",
        "metric": ["phi_leak", "leak_rate"],
        "metric_label": "phi_leak_rate",
    },
    {
        "step": "translate",
        "skill": "report-translation",
        "entrypoint": "scripts/run_report_translation.py",
        "id_col": "UID",
        "text_col": "Anonymized_Rapor",
        "out_file": "translated.csv",
        "metric": ["qc", "pass_rate"],
        "metric_label": "translation_qc_pass_rate",
    },
    {
        "step": "structure",
        "skill": "report-structuring",
        "entrypoint": "scripts/run_report_structuring.py",
        "id_col": "UID",
        "text_col": "Translated_Rapor",
        "out_file": "structured.csv",
        "metric": ["qc", "pass_rate"],
        "metric_label": "structure_qc_pass_rate",
    },
    {
        "step": "classify",
        "skill": "report-pathology-classification",
        "entrypoint": "scripts/run_report_pathology_classification.py",
        "id_col": "UID",
        "text_col": "findings",
        "out_file": "labels.csv",
        "metric": ["labels", "label_coverage_rate"],
        "metric_label": "label_coverage_rate",
    },
]
STAGE_BY_STEP = {s["step"]: s for s in STAGES}

IMAGE_EXTS = (".dcm", ".nii", ".nii.gz")


def log(msg: str) -> None:
    print(f"[nv-curate] {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"datasources config not found: {path}")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg.setdefault("name", path.stem)
    cfg.setdefault("pipeline", {})
    cfg["pipeline"].setdefault("steps", [s["step"] for s in STAGES])
    cfg["pipeline"].setdefault("mode", "mock")
    cfg.setdefault("task", {"type": "analysis"})
    cfg["_config_dir"] = str(path.resolve().parent)
    return cfg


def _resolve(cfg: dict, rel: str | None) -> Path | None:
    if not rel:
        return None
    p = Path(rel)
    if not p.is_absolute():
        p = Path(cfg["_config_dir"]) / p
    return p


# ---------------------------------------------------------------------------
# Inventory / plan (prompt 1)
# ---------------------------------------------------------------------------
def inventory_raw(raw_dir: Path, reports_glob: str, images_glob: str) -> dict:
    reports = sorted(raw_dir.glob(reports_glob)) if raw_dir.exists() else []
    images = []
    if raw_dir.exists():
        for ext in IMAGE_EXTS:
            images.extend(raw_dir.rglob(f"*{ext}"))
    n_report_rows = 0
    columns: list[str] = []
    for rp in reports:
        try:
            with rp.open(encoding="utf-8-sig", newline="") as f:
                reader = csv.reader(f)
                header = next(reader, [])
                if not columns:
                    columns = header
                n_report_rows += sum(1 for _ in reader)
        except Exception:
            continue
    return {
        "raw_dir": str(raw_dir),
        "n_report_files": len(reports),
        "n_report_rows": n_report_rows,
        "report_columns": columns,
        "n_image_files": len(images),
        "has_images": len(images) > 0,
        "phi_risk": "high" if reports else "unknown",
        "needs_processing": ["anonymize", "translate", "structure", "classify"],
    }


def build_plan(cfg: dict, inv: dict) -> dict:
    return {
        "name": cfg.get("name"),
        "raw_data": {
            "path": inv["raw_dir"],
            "reports_glob": cfg.get("raw_data", {}).get("reports_glob", "*_reports*.csv"),
            "images_glob": cfg.get("raw_data", {}).get("images_glob", "**/*.dcm"),
        },
        "target": cfg.get("target", {"path": "<set target path>", "ai_ready": True}),
        "pipeline": {
            "steps": [s["step"] for s in STAGES],
            "mode": cfg.get("pipeline", {}).get("mode", "mock"),
            "model": cfg.get("pipeline", {}).get(
                "model", "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4"
            ),
            "id_col": "UID",
            "text_col": "report",
        },
        "task": cfg.get("task", {"type": "analysis"}),
        "join_key": "study_uid",
    }


# ---------------------------------------------------------------------------
# Pipeline (prompt 2)
# ---------------------------------------------------------------------------
def run_stage(
    stage: dict,
    input_csv: Path,
    stage_out: Path,
    mode: str,
    model: str | None,
    limit: int,
    cuda: str | None,
    mr_root: str | None,
) -> dict:
    skill_dir = SKILLS_DIR / stage["skill"]
    entry = skill_dir / stage["entrypoint"]
    if not entry.exists():
        raise FileNotFoundError(f"stage skill entrypoint missing: {entry}")
    stage_out.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(entry),
        str(input_csv),
        "--out",
        str(stage_out),
        "--mode",
        mode,
        "--id-col",
        stage["id_col"],
        "--text-col",
        stage["text_col"],
    ]
    if model:
        cmd += ["--model", model]
    if limit:
        cmd += ["--limit", str(limit)]
    if cuda is not None:
        cmd += ["--cuda-visible-devices", cuda]
    if mr_root is not None:
        cmd += ["--mr-rate-root", mr_root]
    log(f"stage {stage['step']}: {stage['skill']} ({mode}) on {input_csv.name}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"stage {stage['step']} failed (exit {proc.returncode}): {proc.stderr.strip()[-500:]}"
        )
    try:
        out_json = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"stage {stage['step']} produced unparseable JSON: {e}")
    return out_json


def _metric(out_json: dict, path: list[str]):
    cur = out_json
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def run_pipeline(
    cfg: dict,
    raw_csv: Path,
    work_dir: Path,
    mode: str,
    model: str | None,
    limit: int,
    cuda: str | None,
    mr_root: str | None,
    mock_steps: set | None = None,
) -> tuple[list[dict], dict[str, Path]]:
    steps = cfg["pipeline"]["steps"]
    mock_steps = mock_steps or set()
    stage_results: list[dict] = []
    outputs: dict[str, Path] = {}
    current_input = raw_csv
    for step in steps:
        stage = STAGE_BY_STEP.get(step)
        if stage is None:
            raise ValueError(f"unknown pipeline step: {step!r}")
        stage_mode = "mock" if step in mock_steps else mode
        stage_out = work_dir / "stages" / step
        out_json = run_stage(
            stage, current_input, stage_out, stage_mode, model, limit, cuda, mr_root
        )
        out_file = stage_out / stage["out_file"]
        outputs[step] = out_file
        stage_results.append(
            {
                "step": step,
                "skill": stage["skill"],
                "status": "ok",
                "mode": stage_mode,
                "n_reports": out_json.get("n_reports"),
                "metric": stage["metric_label"],
                "value": _metric(out_json, stage["metric"]),
                "output": str(out_file),
            }
        )
        current_input = out_file
    return stage_results, outputs


# ---------------------------------------------------------------------------
# Assemble AI-ready dataset (join structured + labels by study id)
# ---------------------------------------------------------------------------
def _read_csv(path: Path) -> tuple[list[str], list[dict]]:
    if not path or not path.exists():
        return [], []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return (reader.fieldnames or []), list(reader)


def assemble_datalist(
    outputs: dict[str, Path], images_by_uid: dict[str, str], modality: str, ai_dir: Path
) -> dict:
    ai_dir.mkdir(parents=True, exist_ok=True)
    _, structured = _read_csv(outputs.get("structure"))
    label_cols, labels = _read_csv(outputs.get("classify"))
    labels_by_uid = {r.get("study_uid", r.get("UID", "")): r for r in labels}
    pathology_cols = [c for c in label_cols if c != "study_uid"]

    records = []
    source_rows = structured if structured else [{"UID": uid} for uid in labels_by_uid]
    for row in source_rows:
        uid = row.get("UID") or row.get("study_uid") or ""
        lab_row = labels_by_uid.get(uid, {})
        labels_map = {c: int(lab_row.get(c, 0) or 0) for c in pathology_cols}
        rec = {
            "study_uid": uid,
            "findings": row.get("findings", ""),
            "impression": row.get("impression", ""),
            "clinical_information": row.get("clinical_information", ""),
            "technique": row.get("technique", ""),
            "labels": labels_map,
        }
        if uid in images_by_uid:
            rec["image"] = images_by_uid[uid]
            rec["modality"] = modality
        records.append(rec)

    has_images = any("image" in r for r in records)
    # MONAI-style datalist for the image-finetune hand-off (image track), plus
    # the full curated records (analysis track) keyed by study_uid.
    monai = {
        "training": [
            {
                "image": r["image"],
                "modality": r.get("modality", modality),
                "study_uid": r["study_uid"],
                "labels": r["labels"],
            }
            for r in records
            if "image" in r
        ]
    }
    (ai_dir / "datalist.json").write_text(json.dumps(monai, indent=2), encoding="utf-8")
    (ai_dir / "curated_records.json").write_text(
        json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {
        "datalist": str(ai_dir / "datalist.json"),
        "curated_records": str(ai_dir / "curated_records.json"),
        "n_records": len(records),
        "n_pathology_labels": len(pathology_cols),
        "has_labels": len(pathology_cols) > 0,
        "has_images": has_images,
        "n_image_records": sum(1 for r in records if "image" in r),
    }


def map_images(raw_dir: Path, images_glob: str) -> dict[str, str]:
    """Map study_uid -> image path. Convention: image dir/file name contains the
    study uid. Best-effort; empty when no images are present (text-only curation)."""
    out: dict[str, str] = {}
    if not raw_dir.exists():
        return out
    for ext in IMAGE_EXTS:
        for p in raw_dir.rglob(f"*{ext}"):
            out.setdefault(p.stem.split(".")[0], str(p))
    return out


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------
def summarize_curate(
    cfg: dict,
    stage_results: list[dict],
    ai_ready: dict,
    mode: str,
    inv: dict,
    elapsed: float,
    action: str,
) -> dict:
    steps_done = [s["step"] for s in stage_results]
    complete = steps_done == cfg["pipeline"]["steps"]
    task = cfg.get("task", {"type": "analysis"})
    want_finetune = task.get("type") == "finetune"
    handoff_ready = bool(ai_ready.get("has_images")) if want_finetune else True
    return {
        "skill": SKILL_NAME,
        "action": action,
        "datasource": cfg.get("name"),
        "mode": mode,
        "n_studies": ai_ready.get("n_records", 0),
        "inventory": inv,
        "stages": stage_results,
        "ai_ready": ai_ready,
        "pipeline_status": "complete" if complete else "partial",
        "task": {
            "type": task.get("type", "analysis"),
            "handoff": "nv-generate-mr-brain-finetune" if want_finetune else None,
            "ready": handoff_ready,
            "reason": (
                None
                if handoff_ready
                else "no image volumes joined; image track required for diffusion finetune"
            ),
        },
        "runtime": {"elapsed_seconds": round(elapsed, 4)},
    }


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------
def do_curate(cfg: dict, work_dir: Path, args: argparse.Namespace, action: str = "curate") -> dict:
    t0 = time.perf_counter()
    raw = cfg.get("raw_data", {})
    raw_dir = _resolve(cfg, raw.get("path"))
    reports_glob = raw.get("reports_glob", "*_reports*.csv")
    images_glob = raw.get("images_glob", "**/*.dcm")
    if raw_dir is None or not raw_dir.exists():
        raise FileNotFoundError(f"raw_data.path does not exist: {raw_dir}")
    report_files = sorted(raw_dir.glob(reports_glob))
    if not report_files:
        raise FileNotFoundError(f"no report CSVs matching {reports_glob!r} under {raw_dir}")

    inv = inventory_raw(raw_dir, reports_glob, images_glob)
    mode = args.mode or cfg["pipeline"].get("mode", "mock")
    model = args.model or cfg["pipeline"].get("model")
    raw_csv = report_files[0]  # one curation run per source CSV (extend per-file as needed)

    mock_steps = {
        s.strip() for s in (getattr(args, "mock_steps", "") or "").split(",") if s.strip()
    }
    stage_results, outputs = run_pipeline(
        cfg,
        raw_csv,
        work_dir,
        mode,
        model,
        args.limit,
        args.cuda_visible_devices,
        args.mr_rate_root,
        mock_steps,
    )
    images_by_uid = map_images(raw_dir, images_glob)
    modality = cfg.get("task", {}).get("modality", "mri_t1")
    target_dir = _resolve(cfg, cfg.get("target", {}).get("path")) or (work_dir / "ai_ready")
    ai_ready = assemble_datalist(outputs, images_by_uid, modality, target_dir)
    elapsed = time.perf_counter() - t0
    return summarize_curate(cfg, stage_results, ai_ready, mode, inv, elapsed, action)


def do_plan(cfg: dict, work_dir: Path, args: argparse.Namespace) -> dict:
    t0 = time.perf_counter()
    raw = cfg.get("raw_data", {})
    raw_dir = _resolve(cfg, raw.get("path")) or Path(args.fixture)
    reports_glob = raw.get("reports_glob", "*_reports*.csv")
    images_glob = raw.get("images_glob", "**/*.dcm")
    inv = inventory_raw(raw_dir, reports_glob, images_glob)
    plan = build_plan(cfg, inv)
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "datasources.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return {
        "skill": SKILL_NAME,
        "action": "plan",
        "datasource": cfg.get("name"),
        "inventory": inv,
        "plan": plan,
        "plan_file": str(work_dir / "datasources.json"),
        "runtime": {"elapsed_seconds": round(time.perf_counter() - t0, 4)},
    }


def do_finetune(cfg: dict, work_dir: Path, args: argparse.Namespace) -> dict:
    summary = do_curate(cfg, work_dir, args, action="finetune")
    summary["task"]["type"] = "finetune"
    ai = summary["ai_ready"]
    ready = bool(ai.get("has_images"))
    summary["finetune_handoff"] = {
        "skill": "nv-generate-mr-brain-finetune",
        "datalist": ai.get("datalist"),
        "ready": ready,
        "command": (
            "python skills/nv-generate-mr-brain-finetune/scripts/run_mr_brain_finetune.py "
            f"{ai.get('datalist')} --data-base-dir <DATA_ROOT> --output-dir runs/mr_brain_finetune "
            f"--modality {cfg.get('task', {}).get('modality', 'mri_t1')} --preflight"
        ),
        "reason": (
            None
            if ready
            else "datalist has no image volumes; join NIfTI images by study_uid before finetuning"
        ),
    }
    summary["task"]["ready"] = ready
    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="nv-curate: orchestrate the MR-RATE report-curation pipeline."
    )
    p.add_argument(
        "fixture", type=Path, help="datasources.json config (or a raw dir for --action plan)"
    )
    p.add_argument("--out", type=Path, default=None, help="evidence/work dir for artifacts")
    p.add_argument("--action", choices=["plan", "curate", "finetune"], default="curate")
    p.add_argument("--mode", choices=["mock", "live"], default=None, help="override pipeline mode")
    p.add_argument(
        "--mock-steps",
        type=str,
        default="",
        help="comma-separated steps forced to mock even in live mode "
        "(e.g. 'structure' — its upstream hardcodes a model too large for one GPU)",
    )
    p.add_argument("--model", type=str, default=None, help="override LLM model id (live mode)")
    p.add_argument("--limit", type=int, default=0, help="cap reports processed per stage")
    p.add_argument("--cuda-visible-devices", type=str, default=None)
    p.add_argument("--mr-rate-root", type=str, default=None)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    work_dir = (args.out or Path.cwd()).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    # The plan action accepts either a datasources.json or a bare raw directory.
    if args.action == "plan" and args.fixture.is_dir():
        cfg = {
            "name": args.fixture.name,
            "raw_data": {"path": "."},
            "pipeline": {},
            "task": {"type": "analysis"},
            "_config_dir": str(args.fixture),
        }
        cfg["pipeline"].setdefault("steps", [s["step"] for s in STAGES])
        cfg["pipeline"].setdefault("mode", "mock")
    else:
        cfg = load_config(args.fixture)

    if args.action == "plan":
        summary = do_plan(cfg, work_dir, args)
    elif args.action == "finetune":
        summary = do_finetune(cfg, work_dir, args)
    else:
        summary = do_curate(cfg, work_dir, args)

    log(f"done: action={args.action}, status={summary.get('pipeline_status', 'n/a')}")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
