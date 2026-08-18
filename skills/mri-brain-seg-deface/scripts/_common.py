#!/usr/bin/env python3
"""Shared wrapper runtime for the MR-RATE MRI-preprocessing skills.

Every skill copies this verbatim to scripts/_common.py. It gives all skills an
identical, monitorable contract with NO mock path:

  * preflight()  — fail-fast execution-environment alignment: the exact upstream
    script exists, required deps import (with versions), dcm2niix is on PATH
    (when needed), and a usable CUDA GPU is visible (name/index/memory) for GPU
    steps. Exposed standalone via `--preflight` so dev/test/prod can gate a run
    before executing anything.
  * run_step() — runs the REAL upstream step via subprocess (never a stub),
    times each phase, collects the real artifacts, and emits ONE JSON object on
    stdout plus <out>/telemetry.json with a structured `telemetry` block
    (per-phase timings, environment facts incl. versions/GPU/host/timestamp,
    I/O counts, the exact command). Logs go to stderr; only JSON on stdout.

exit 0 == success/aligned; non-zero == misaligned or upstream failure.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def _pkg_version(mod: str) -> str:
    try:
        import importlib.metadata as md
        return md.version(mod)
    except Exception:  # noqa: BLE001
        try:
            return __import__(mod).__version__
        except Exception:  # noqa: BLE001
            return "unknown"


def _dep_report(deps) -> list[dict]:
    import importlib.util
    out = []
    for d in deps:
        ok = importlib.util.find_spec(d) is not None
        out.append({"name": d, "ok": ok, "version": _pkg_version(d) if ok else None})
    return out


def _dcm2niix_report() -> dict:
    path = shutil.which("dcm2niix")
    ver = None
    if path:
        try:
            r = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=30)
            ver = (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr) else None
        except Exception:  # noqa: BLE001
            ver = None
    return {"name": "dcm2niix", "ok": path is not None, "path": path, "version": ver}


def _gpu_report(device: str) -> dict:
    """Report the CUDA GPU the pipeline will actually see. Honors the caller's
    CUDA_DEVICE_ORDER/CUDA_VISIBLE_DEVICES; forces PCI order if unset."""
    os.environ.setdefault("CUDA_DEVICE_ORDER", "PCI_BUS_ID")
    rep = {"name": "cuda_gpu", "ok": False, "device_arg": device}
    try:
        import torch
        rep["torch_version"] = torch.__version__
        rep["cuda_available"] = bool(torch.cuda.is_available())
        if torch.cuda.is_available():
            idx = 0
            props = torch.cuda.get_device_properties(idx)
            free = total = None
            try:
                free_b, total_b = torch.cuda.mem_get_info(idx)
                free, total = free_b // (1024 * 1024), total_b // (1024 * 1024)
            except Exception:  # noqa: BLE001
                total = props.total_memory // (1024 * 1024)
            rep.update({
                "ok": True,
                "visible_device_index": idx,
                "device_name": props.name,
                "compute_capability": f"{props.major}.{props.minor}",
                "memory_total_mb": total,
                "memory_free_mb": free,
                "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
            })
        else:
            rep["detail"] = "torch.cuda.is_available() is False"
    except Exception as e:  # noqa: BLE001
        rep["detail"] = f"torch import/query failed: {e}"
    return rep


def _environment(deps, need_dcm2niix: bool, need_gpu: bool, device: str,
                 mr_rate_root: str, upstream_rel: str) -> dict:
    env = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "mr_rate_root": str(mr_rate_root),
        "upstream_script": str(Path(mr_rate_root) / upstream_rel),
        "packages": {d["name"]: d["version"] for d in _dep_report(deps)},
    }
    if need_dcm2niix:
        env["dcm2niix"] = _dcm2niix_report()
    if need_gpu:
        env["gpu"] = _gpu_report(device)
    return env


def preflight(mr_rate_root, upstream_rel, deps=(), need_dcm2niix=False,
              need_gpu=False, device="0") -> dict:
    """Return {aligned: bool, checks: [...]} for execution-environment alignment."""
    checks = []
    script = Path(mr_rate_root) / upstream_rel
    checks.append({"name": "upstream_script_exists", "ok": script.is_file(),
                   "detail": str(script)})
    for d in _dep_report(deps):
        checks.append({"name": f"dep:{d['name']}", "ok": d["ok"],
                       "detail": d["version"]})
    if need_dcm2niix:
        d = _dcm2niix_report()
        checks.append({"name": "dcm2niix_on_path", "ok": d["ok"], "detail": d["version"]})
    if need_gpu:
        g = _gpu_report(device)
        checks.append({"name": "cuda_gpu_available", "ok": g["ok"],
                       "detail": g.get("device_name") or g.get("detail")})
    aligned = all(c["ok"] for c in checks)
    return {"aligned": aligned, "checks": checks}


def _emit(payload: dict, out: Path | None) -> None:
    if out is not None:
        try:
            (Path(out) / "telemetry.json").write_text(
                json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    print(json.dumps(payload))


def run_step(skill, step, *, mr_rate_root, fixtures, out, upstream_rel, build_args,
             deps=(), need_dcm2niix=False, need_gpu=False, device="0",
             preflight_only=False, io_summary=None) -> int:
    """Run the real upstream step with preflight + telemetry. build_args is a
    callable(fixtures:Path, out:Path, device:str) -> list[str] of args placed
    AFTER the upstream script path. io_summary is an optional callable(out)->dict."""
    t0 = time.perf_counter()
    fixtures = Path(fixtures)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    mr_rate_root = str(mr_rate_root)

    pf = preflight(mr_rate_root, upstream_rel, deps, need_dcm2niix, need_gpu, device)
    env_facts = _environment(deps, need_dcm2niix, need_gpu, device, mr_rate_root, upstream_rel)
    preflight_s = round(time.perf_counter() - t0, 3)

    def log(m):
        print(f"[{skill}] {m}", file=sys.stderr, flush=True)

    if preflight_only or not pf["aligned"]:
        status = "ok" if pf["aligned"] else "failed"
        payload = {
            "skill": skill, "step": step, "mode": "preflight", "status": status,
            "preflight": pf, "outputs": {},
            "telemetry": {"wall_seconds": preflight_s,
                          "phases": {"preflight_s": preflight_s},
                          "environment": env_facts},
        }
        if not pf["aligned"]:
            payload["error"] = "environment not aligned: " + ", ".join(
                c["name"] for c in pf["checks"] if not c["ok"])
            log(payload["error"])
        _emit(payload, out)
        return 0 if pf["aligned"] else 1

    # --- real execution ---
    script = Path(mr_rate_root) / upstream_rel
    penv = dict(os.environ)
    penv["PYTHONPATH"] = str(Path(mr_rate_root) / "src") + os.pathsep + penv.get("PYTHONPATH", "")
    penv["PATH"] = str(Path(sys.executable).parent) + os.pathsep + penv.get("PATH", "")
    if need_gpu:
        penv.setdefault("CUDA_DEVICE_ORDER", "PCI_BUS_ID")
    argv = [sys.executable, str(script)] + [str(a) for a in build_args(fixtures, out, device)]
    log(f"running upstream: {' '.join(argv)}")
    t1 = time.perf_counter()
    proc = subprocess.run(argv, capture_output=True, text=True, env=penv, timeout=1800)
    upstream_s = round(time.perf_counter() - t1, 3)
    if proc.stderr:
        sys.stderr.write(proc.stderr[-4000:])

    produced = sorted(str(p) for p in out.rglob("*") if p.is_file() and p.name != "telemetry.json")
    io = {"n_output_files": len(produced)}
    if io_summary:
        try:
            io.update(io_summary(out) or {})
        except Exception as e:  # noqa: BLE001
            io["io_summary_error"] = str(e)

    status = "ok" if proc.returncode == 0 else "failed"
    payload = {
        "skill": skill, "step": step, "mode": "real", "status": status,
        "outputs": {"produced_files": produced, "out_dir": str(out)},
        "preflight": pf,
        "telemetry": {
            "wall_seconds": round(time.perf_counter() - t0, 3),
            "phases": {"preflight_s": preflight_s, "upstream_s": upstream_s},
            "environment": env_facts,
            "io": io,
            "command": argv,
            "upstream_returncode": proc.returncode,
        },
    }
    if proc.returncode != 0:
        payload["error"] = f"upstream exited {proc.returncode}: {proc.stderr.strip()[-500:]}"
        log(payload["error"])
    _emit(payload, out)
    return 0 if proc.returncode == 0 else 1


ORCH_DEPS = ["pandas", "numpy", "nibabel", "pydicom", "SimpleITK", "scipy",
             "torch", "brainles_hd_bet", "openpyxl", "yaml"]


def _batch_yaml(fixtures: Path, out: Path, device: str) -> str:
    return f"""batch_id: batchTEST
log_dir: {out}/logs
verbose: true
dcm2nii:
  input_csv: {fixtures}/dicom_folder_paths.csv
  output_dir: {out}/raw_niftis
  max_workers: 2
pacs_metadata_filtering:
  input_csv: {fixtures}/pacs_metadata.csv
  output_csv: {out}/interim/raw_metadata.csv
series_classification: {{}}
modality_filtering:
  output_json: {out}/interim/modalities.json
  output_csv: {out}/interim/mod_meta.csv
  num_processes: 1
brain_segmentation:
  output_dir: {out}/processed
  device: "{device}"
zip_and_upload:
  output_dir: {out}/zips
  repo_id: dummy/repo
  num_zip_workers: 1
  num_hf_workers: 1
  skip_upload: true
  delete_zips: false
  hf_timeout: 120
  xet_high_perf: false
prepare_metadata:
  patient_mapping_csv: {fixtures}/patient_mapping.xlsx
  study_date_mapping: {fixtures}/study_date_mapping.xlsx
  output_csv: {out}/processed/batchTEST_metadata.csv
  repo_id: dummy/repo
  skip_upload: true
  num_hf_workers: 1
  hf_timeout: 120
"""


def run_pipeline(skill, step, *, mr_rate_root, fixtures, out, device="0",
                 preflight_only=False) -> int:
    """Orchestrator: drive the real run_mri_preprocessing.py + run_mri_upload.py
    runners end to end, with the same preflight + telemetry contract."""
    t0 = time.perf_counter()
    fixtures, out = Path(fixtures), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "logs").mkdir(parents=True, exist_ok=True)
    mr_rate_root = str(mr_rate_root)
    runners = ["run/run_mri_preprocessing.py", "run/run_mri_upload.py"]

    checks = [{"name": f"runner_exists:{r}", "ok": (Path(mr_rate_root) / r).is_file(),
               "detail": str(Path(mr_rate_root) / r)} for r in runners]
    pf_dep = preflight(mr_rate_root, runners[0], ORCH_DEPS, need_dcm2niix=True,
                       need_gpu=True, device=device)
    checks += pf_dep["checks"]
    pf = {"aligned": all(c["ok"] for c in checks), "checks": checks}
    env_facts = _environment(ORCH_DEPS, True, True, device, mr_rate_root, runners[0])
    preflight_s = round(time.perf_counter() - t0, 3)

    def log(m):
        print(f"[{skill}] {m}", file=sys.stderr, flush=True)

    if preflight_only or not pf["aligned"]:
        status = "ok" if pf["aligned"] else "failed"
        payload = {"skill": skill, "step": step, "mode": "preflight", "status": status,
                   "preflight": pf, "outputs": {},
                   "telemetry": {"wall_seconds": preflight_s,
                                 "phases": {"preflight_s": preflight_s},
                                 "environment": env_facts}}
        if not pf["aligned"]:
            payload["error"] = "environment not aligned: " + ", ".join(
                c["name"] for c in pf["checks"] if not c["ok"])
        _emit(payload, out)
        return 0 if pf["aligned"] else 1

    yaml_path = out / "batch.yaml"
    yaml_path.write_text(_batch_yaml(fixtures, out, device), encoding="utf-8")
    penv = dict(os.environ)
    penv["PATH"] = str(Path(sys.executable).parent) + os.pathsep + penv.get("PATH", "")
    penv.setdefault("CUDA_DEVICE_ORDER", "PCI_BUS_ID")
    phases = {"preflight_s": preflight_s}
    rc = 0
    for r in runners:
        argv = [sys.executable, r, "--config", str(yaml_path)]
        log(f"running {r}")
        t1 = time.perf_counter()
        proc = subprocess.run(argv, capture_output=True, text=True, env=penv,
                              cwd=mr_rate_root, timeout=1800)
        phases[Path(r).stem + "_s"] = round(time.perf_counter() - t1, 3)
        if proc.stderr:
            sys.stderr.write(proc.stderr[-3000:])
        if proc.returncode != 0:
            rc = proc.returncode
            log(f"{r} exited {proc.returncode}: {proc.stderr.strip()[-400:]}")
            break

    produced = sorted(str(p) for p in out.rglob("*") if p.is_file())
    io = {
        "n_defaced_images": len(list(out.rglob("processed/**/img/*.nii.gz"))),
        "n_zips": len(list(out.rglob("*.zip"))),
        "n_metadata_csv": len(list(out.rglob("*metadata*.csv"))),
        "n_output_files": len(produced),
    }
    status = "ok" if rc == 0 else "failed"
    payload = {"skill": skill, "step": step, "mode": "real", "status": status,
               "outputs": {"out_dir": str(out), "produced_files": produced[:200]},
               "preflight": pf,
               "telemetry": {"wall_seconds": round(time.perf_counter() - t0, 3),
                             "phases": phases, "environment": env_facts, "io": io,
                             "config": str(yaml_path)}}
    if rc != 0:
        payload["error"] = f"pipeline runner exited {rc}"
    _emit(payload, out)
    return 0 if rc == 0 else 1
