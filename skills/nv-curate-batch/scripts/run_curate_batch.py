#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""nv-curate-batch — curate a tranche by calling nv-curate-study per study."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

SKILL_NAME = "nv-curate-batch"
SKILLS_DIR = Path(__file__).resolve().parents[2]
STUDY_ENTRY = SKILLS_DIR / "nv-curate-study" / "scripts" / "run_curate_study.py"


def log(msg: str) -> None:
    print(f"[{SKILL_NAME}] {msg}", file=sys.stderr, flush=True)


def load_batch(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"batch config not found: {path}")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if not cfg.get("batch_id"):
        raise ValueError("batch.json requires batch_id")
    if not cfg.get("studies"):
        raise ValueError("batch.json requires a non-empty studies list")
    cfg.setdefault("publish", {})
    cfg["publish"].setdefault("skip_upload", True)
    cfg.setdefault("fail_closed", True)
    cfg.setdefault("smoke_limit", 0)
    cfg["_config_dir"] = str(path.resolve().parent)
    return cfg


def materialize_study(item, config_dir: Path, work: Path, idx: int) -> tuple[str, Path]:
    """Return (study_uid, path_to_study_json)."""
    if isinstance(item, str):
        p = Path(item)
        if not p.is_absolute():
            p = config_dir / p
        cfg = json.loads(p.read_text(encoding="utf-8"))
        uid = str(cfg.get("study_uid") or p.stem)
        return uid, p

    if not isinstance(item, dict):
        raise TypeError(f"studies[{idx}] must be a path string or study object")
    uid = str(item.get("study_uid") or f"study-{idx:04d}")
    # Rewrite relative datasources paths against the batch config dir by dumping
    # a resolved copy under work/
    study_dir = work / "study_configs" / uid
    study_dir.mkdir(parents=True, exist_ok=True)
    study_cfg = dict(item)
    reports = dict(study_cfg.get("reports") or {})
    ds = reports.get("datasources")
    if ds and not Path(ds).is_absolute():
        src = config_dir / ds
        dst = study_dir / "datasources.json"
        if src.exists():
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            # also copy raw_data if relative beside datasources
            try:
                ds_obj = json.loads(src.read_text(encoding="utf-8"))
                raw_rel = (ds_obj.get("raw_data") or {}).get("path")
                if raw_rel and not Path(raw_rel).is_absolute():
                    import shutil

                    raw_src = src.parent / raw_rel
                    raw_dst = study_dir / raw_rel
                    if raw_src.exists() and not raw_dst.exists():
                        shutil.copytree(raw_src, raw_dst)
                    # datasources path stays relative to study_dir
                    ds_obj.setdefault("raw_data", {})["path"] = raw_rel
                    dst.write_text(json.dumps(ds_obj, indent=2) + "\n", encoding="utf-8")
            except Exception:  # noqa: BLE001
                pass
            reports["datasources"] = "datasources.json"
            study_cfg["reports"] = reports
        else:
            reports["datasources"] = str((config_dir / ds).resolve())
            study_cfg["reports"] = reports
    out_path = study_dir / "study.json"
    out_path.write_text(json.dumps(study_cfg, indent=2) + "\n", encoding="utf-8")
    return uid, out_path


def run_one_study(
    study_json: Path,
    study_out: Path,
    mode: str,
    device: str,
    mr_rate_root: str | None,
) -> dict:
    if not STUDY_ENTRY.exists():
        raise FileNotFoundError(
            f"nv-curate-study entrypoint missing: {STUDY_ENTRY}. "
            "Install skills/nv-curate-study beside this skill."
        )
    study_out.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(STUDY_ENTRY),
        str(study_json),
        "--out",
        str(study_out),
        "--mode",
        mode,
        "--device",
        device,
    ]
    if mr_rate_root:
        cmd += ["--mr-rate-root", mr_rate_root]
    log(" ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    if not lines:
        return {
            "skill": "nv-curate-study",
            "status": "error",
            "error": f"no JSON from nv-curate-study (exit {proc.returncode})",
            "join": {"status": "rejected", "reason": "no_output"},
        }
    try:
        result = json.loads(lines[-1])
    except json.JSONDecodeError:
        return {
            "skill": "nv-curate-study",
            "status": "error",
            "error": "unparseable JSON from nv-curate-study",
            "join": {"status": "rejected", "reason": "bad_json"},
        }
    result["_exit_code"] = proc.returncode
    return result


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Curate a batch of MRI+report studies via nv-curate-study")
    p.add_argument("batch_json", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--mode", choices=["mock", "live"], default="mock")
    p.add_argument("--smoke", type=int, default=None, help="override batch.smoke_limit")
    p.add_argument("--device", default="0")
    p.add_argument("--mr-rate-root", default=None)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    t0 = time.time()
    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        cfg = load_batch(args.batch_json)
        config_dir = Path(cfg["_config_dir"])
        smoke_n = args.smoke if args.smoke is not None else int(cfg.get("smoke_limit") or 0)

        studies_meta: list[tuple[str, Path]] = []
        for i, item in enumerate(cfg["studies"]):
            studies_meta.append(materialize_study(item, config_dir, out_dir, i))

        order = list(range(len(studies_meta)))
        smoke_idx = order[:smoke_n] if smoke_n > 0 else []
        rest_idx = order[smoke_n:] if smoke_n > 0 else order

        matched: list[dict] = []
        rejected: list[dict] = []
        per_study: dict[str, dict] = {}

        def process(indices: list[int], phase: str) -> None:
            for i in indices:
                uid, study_path = studies_meta[i]
                study_out = out_dir / "studies" / uid
                log(f"{phase}: {uid}")
                result = run_one_study(study_path, study_out, args.mode, args.device, args.mr_rate_root)
                per_study[uid] = result
                join_status = (result.get("join") or {}).get("status")
                rec = {
                    "study_uid": uid,
                    "phase": phase,
                    "join": result.get("join"),
                    "out_dir": str(study_out),
                    "error": result.get("error"),
                }
                if join_status == "matched":
                    matched.append(rec)
                else:
                    rejected.append(rec)

        if smoke_idx:
            process(smoke_idx, "smoke")
            smoke_rejects = [r for r in rejected if r["phase"] == "smoke"]
            if smoke_rejects and cfg.get("fail_closed", True):
                summary = {
                    "skill": SKILL_NAME,
                    "batch_id": cfg["batch_id"],
                    "mode": args.mode,
                    "n_studies": len(studies_meta),
                    "n_matched": len(matched),
                    "n_rejected": len(rejected),
                    "matched": matched,
                    "rejected": rejected,
                    "smoke": {
                        "limit": smoke_n,
                        "status": "failed",
                        "reason": "smoke_cohort_had_rejects",
                    },
                    "publish": {
                        "skip_upload": True,
                        "blocked": True,
                        "repo_id": (cfg.get("publish") or {}).get("repo_id"),
                    },
                    "runtime": {"elapsed_seconds": round(time.time() - t0, 3)},
                    "note": "Stopped before full batch because smoke cohort had rejects (fail_closed).",
                }
                (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
                print(json.dumps(summary))
                return 2

        process(rest_idx, "full" if smoke_idx else "all")

        skip = bool((cfg.get("publish") or {}).get("skip_upload", True))
        blocked = skip or (bool(rejected) and bool(cfg.get("fail_closed", True)))
        summary = {
            "skill": SKILL_NAME,
            "batch_id": cfg["batch_id"],
            "mode": args.mode,
            "n_studies": len(studies_meta),
            "n_matched": len(matched),
            "n_rejected": len(rejected),
            "matched": matched,
            "rejected": rejected,
            "smoke": {"limit": smoke_n, "status": "ok" if smoke_idx else "skipped"},
            "publish": {
                "skip_upload": skip,
                "blocked": blocked,
                "repo_id": (cfg.get("publish") or {}).get("repo_id"),
            },
            "runtime": {"elapsed_seconds": round(time.time() - t0, 3)},
        }
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary))
        if rejected and cfg.get("fail_closed", True):
            return 2
        return 0
    except Exception as exc:  # noqa: BLE001
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
