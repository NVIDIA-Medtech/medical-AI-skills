#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""nv-curate-study — curate one MRI + associated report for MR-RATE.

Composes sibling skills ``nv-curate-mri`` then ``nv-curate``, joins on
``study_uid``, and emits one JSON summary on stdout. Mock mode stubs MRI and
runs report curation in mock; live mode requires MR-RATE + GPU.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

SKILL_NAME = "nv-curate-study"
SKILLS_DIR = Path(__file__).resolve().parents[2]
NV_CURATE = SKILLS_DIR / "nv-curate" / "scripts" / "nv_curate.py"
NV_CURATE_MRI = SKILLS_DIR / "nv-curate-mri" / "scripts" / "run_mri_pipeline.py"


def log(msg: str) -> None:
    print(f"[{SKILL_NAME}] {msg}", file=sys.stderr, flush=True)


def load_study(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"study config not found: {path}")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if not cfg.get("study_uid"):
        raise ValueError("study.json requires study_uid")
    if not cfg.get("reports", {}).get("datasources"):
        raise ValueError("study.json requires reports.datasources")
    cfg.setdefault("join_key", "study_uid")
    cfg.setdefault("publish", {})
    cfg["publish"].setdefault("skip_upload", True)
    cfg.setdefault("mri", {})
    cfg["_config_dir"] = str(path.resolve().parent)
    return cfg


def resolve(cfg: dict, rel: str | None) -> Path | None:
    if not rel:
        return None
    p = Path(rel)
    if not p.is_absolute():
        p = Path(cfg["_config_dir"]) / p
    return p


def run_json(cmd: list[str], env: dict | None = None) -> dict:
    log(" ".join(cmd))
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stderr[-2000:]}"
        )
    # Last JSON object on stdout
    lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    if not lines:
        raise RuntimeError(f"no JSON on stdout from: {' '.join(cmd)}")
    return json.loads(lines[-1])


def run_mri(cfg: dict, out_dir: Path, mode: str, device: str, preflight: bool, mr_rate_root: str | None) -> dict:
    mri_cfg = cfg.get("mri") or {}
    if mode == "mock" or mri_cfg.get("skip"):
        stub = {
            "skill": "nv-curate-mri",
            "status": "mocked",
            "study_uid": cfg["study_uid"],
            "preflight": {"aligned": True, "mode": "mock"},
            "note": "MRI track stubbed in mock mode; not a real defacing/DICOM run",
        }
        (out_dir / "mri_stub.json").write_text(json.dumps(stub, indent=2) + "\n", encoding="utf-8")
        return stub

    if not NV_CURATE_MRI.exists():
        raise FileNotFoundError(f"missing sibling skill entrypoint: {NV_CURATE_MRI}")

    fixtures = resolve(cfg, mri_cfg.get("fixtures"))
    if fixtures is None or not fixtures.exists():
        raise FileNotFoundError(
            "live mode requires mri.fixtures pointing at prepared one-study MRI inputs"
        )
    root = mr_rate_root or mri_cfg.get("mr_rate_root") or ""
    if not root:
        import os

        root = os.environ.get("MR_RATE_ROOT", "")
    if not root:
        raise ValueError("live MRI requires --mr-rate-root, mri.mr_rate_root, or $MR_RATE_ROOT")

    mri_out = out_dir / "mri"
    mri_out.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(NV_CURATE_MRI),
        "--fixtures",
        str(fixtures),
        "--out",
        str(mri_out),
        "--mr-rate-root",
        root,
        "--device",
        device or mri_cfg.get("device") or "0",
    ]
    if preflight:
        cmd.append("--preflight")
    result = run_json(cmd)
    result["out_dir"] = str(mri_out)
    return result


def run_reports_mock(cfg: dict, out_dir: Path) -> dict:
    """Deterministic report stub when sibling nv-curate mock stages are unavailable."""
    import csv

    ds = resolve(cfg, cfg["reports"]["datasources"])
    if ds is None or not ds.exists():
        raise FileNotFoundError(f"reports.datasources not found: {cfg['reports']['datasources']}")
    ds_cfg = json.loads(ds.read_text(encoding="utf-8"))
    raw_rel = (ds_cfg.get("raw_data") or {}).get("path") or "."
    glob_pat = (ds_cfg.get("raw_data") or {}).get("reports_glob") or "*.csv"
    raw_dir = ds.parent / raw_rel
    csvs = sorted(raw_dir.glob(glob_pat))
    if not csvs:
        raise FileNotFoundError(f"no report CSVs under {raw_dir} matching {glob_pat}")

    id_col = (ds_cfg.get("pipeline") or {}).get("id_col") or "UID"
    text_col = (ds_cfg.get("pipeline") or {}).get("text_col") or "report"
    limit = int(cfg["reports"].get("limit") or 1)

    rows: list[dict] = []
    with csvs[0].open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if limit and i >= limit:
                break
            rows.append(row)

    reports_out = out_dir / "reports"
    stages = reports_out / "stages"
    stages.mkdir(parents=True, exist_ok=True)
    curated = []
    for row in rows:
        uid = str(row.get(id_col) or cfg["study_uid"])
        curated.append(
            {
                "UID": uid,
                "study_uid": uid,
                "report": row.get(text_col, ""),
                "Anonymized_Rapor": f"[MOCK_ANON]{row.get(text_col, '')[:80]}",
                "findings": "mock findings",
            }
        )

    out_csv = reports_out / "curated_mock.csv"
    if curated:
        with out_csv.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(curated[0].keys()))
            w.writeheader()
            w.writerows(curated)

    summary = {
        "skill": "nv-curate",
        "action": "curate",
        "mode": "mock",
        "pipeline_status": "complete",
        "n_studies": len(curated),
        "stages": [
            {"step": s, "skill": f"report-{s if s != 'classify' else 'pathology-classification'}", "status": "mocked"}
            for s in ("anonymize", "translate", "structure", "classify")
        ],
        "ai_ready": {
            "n_records": len(curated),
            "has_labels": True,
            "has_images": False,
            "curated_records": curated,
            "datalist": str(out_csv),
        },
        "note": "report track stubbed by nv-curate-study mock (sibling stage CLIs not required)",
        "out_dir": str(reports_out),
    }
    (reports_out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def run_reports(cfg: dict, out_dir: Path, mode: str) -> dict:
    if mode == "mock":
        # Prefer real nv-curate when its stage entrypoints exist; else local stub.
        anon_entry = SKILLS_DIR / "report-anonymization" / "scripts" / "run_anonymization.py"
        if not anon_entry.exists():
            log("sibling nv-curate mock stages unavailable; using local report stub")
            return run_reports_mock(cfg, out_dir)

    if not NV_CURATE.exists():
        raise FileNotFoundError(f"missing sibling skill entrypoint: {NV_CURATE}")
    ds = resolve(cfg, cfg["reports"]["datasources"])
    if ds is None or not ds.exists():
        raise FileNotFoundError(f"reports.datasources not found: {cfg['reports']['datasources']}")

    reports_out = out_dir / "reports"
    reports_out.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(NV_CURATE),
        str(ds),
        "--action",
        "curate",
        "--mode",
        mode,
        "--out",
        str(reports_out),
    ]
    limit = int(cfg["reports"].get("limit") or 0)
    if limit > 0:
        cmd += ["--limit", str(limit)]
    if mode == "mock" and limit <= 0:
        cmd += ["--limit", "1"]

    result = run_json(cmd)
    result["out_dir"] = str(reports_out)
    return result


def join_sides(cfg: dict, mri: dict, reports: dict) -> dict:
    join_key = cfg.get("join_key") or "study_uid"
    study_uid = str(cfg["study_uid"])
    mri_ok = mri.get("status") in {"ok", "mocked"}
    if mri.get("status") == "error":
        mri_ok = False
    reports_ok = reports.get("pipeline_status") == "complete" and int(reports.get("n_studies") or 0) > 0

    report_ids: set[str] = set()
    for rec in reports.get("ai_ready", {}).get("curated_records") or []:
        if isinstance(rec, dict):
            for k in (join_key, "study_uid", "UID", "uid"):
                if rec.get(k) is not None:
                    report_ids.add(str(rec[k]))

    if not mri_ok:
        return {"status": "rejected", "reason": "mri_failed_or_missing", "join_key": join_key}
    if not reports_ok:
        return {"status": "rejected", "reason": "reports_failed_or_empty", "join_key": join_key}
    if report_ids:
        if study_uid in report_ids:
            return {"status": "matched", "reason": "ok", "join_key": join_key}
        if len(report_ids) == 1 and cfg.get("allow_single_fixture_join", True):
            return {
                "status": "matched",
                "reason": "single_fixture_join",
                "join_key": join_key,
                "report_id": next(iter(report_ids)),
            }
        return {
            "status": "rejected",
            "reason": "study_uid_mismatch",
            "join_key": join_key,
            "report_ids": sorted(report_ids),
        }
    # Summary omitted curated_records — accept when both tracks succeeded
    return {"status": "matched", "reason": "ok_n_studies_fallback", "join_key": join_key}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Curate one MRI + report for MR-RATE")
    p.add_argument("study_json", type=Path, help="Path to study.json")
    p.add_argument("--out", type=Path, required=True, help="Output directory")
    p.add_argument("--mode", choices=["mock", "live"], default="mock")
    p.add_argument("--device", default="0")
    p.add_argument("--preflight", action="store_true", help="MRI preflight only (live)")
    p.add_argument("--mr-rate-root", default=None)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    t0 = time.time()
    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        cfg = load_study(args.study_json)
        mri = run_mri(cfg, out_dir, args.mode, args.device, args.preflight, args.mr_rate_root)
        if args.preflight and args.mode == "live":
            summary = {
                "skill": SKILL_NAME,
                "study_uid": cfg["study_uid"],
                "mode": args.mode,
                "action": "preflight",
                "mri": mri,
                "reports": {"status": "skipped"},
                "join": {"status": "rejected", "reason": "preflight_only"},
                "publish": {
                    "skip_upload": True,
                    "blocked": True,
                    "repo_id": (cfg.get("publish") or {}).get("repo_id"),
                },
                "runtime": {"elapsed_seconds": round(time.time() - t0, 3)},
            }
            (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(summary))
            return 0

        reports = run_reports(cfg, out_dir, args.mode)
        join = join_sides(cfg, mri, reports)
        skip = bool((cfg.get("publish") or {}).get("skip_upload", True))
        blocked = skip or join["status"] != "matched"
        summary = {
            "skill": SKILL_NAME,
            "study_uid": cfg["study_uid"],
            "mode": args.mode,
            "action": "curate",
            "mri": {
                "status": mri.get("status"),
                "out_dir": mri.get("out_dir"),
                "preflight": mri.get("preflight"),
                "note": mri.get("note"),
            },
            "reports": {
                "pipeline_status": reports.get("pipeline_status"),
                "n_studies": reports.get("n_studies"),
                "out_dir": reports.get("out_dir"),
                "summary": {
                    k: reports.get(k)
                    for k in ("skill", "action", "pipeline_status", "n_studies", "ai_ready")
                    if k in reports
                },
            },
            "join": join,
            "publish": {
                "skip_upload": skip,
                "blocked": blocked,
                "repo_id": (cfg.get("publish") or {}).get("repo_id"),
            },
            "runtime": {"elapsed_seconds": round(time.time() - t0, 3)},
        }
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary))
        return 0 if join["status"] == "matched" else 2
    except Exception as exc:  # noqa: BLE001 — surface as JSON for agents
        err = {
            "skill": SKILL_NAME,
            "status": "error",
            "error": str(exc),
            "runtime": {"elapsed_seconds": round(time.time() - t0, 3)},
        }
        print(json.dumps(err))
        log(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
