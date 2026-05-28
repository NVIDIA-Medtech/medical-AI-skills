"""Host-level provenance capture.

Measures what the manifest *promised* vs. what the host actually shows:

  - GPU identity from ``nvidia-smi`` (model, driver, compute cap, mem total,
    MIG mode) and CUDA toolkit from ``nvcc`` when present.
  - Declared side-effect path snapshots (before/after) for
    ``runtime.side_effects.local_writes`` and ``home_writes``.

Best-effort: missing nvidia-smi or unresolvable paths produce ``status:
skipped`` entries, never exceptions.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from eval_engine.common import REPO_ROOT, _now_iso, _public_path, _read_json_or_empty
from eval_engine.container_provenance import (
    merge_container_into_provenance,
    write_container_environment_lock,
)

_ENV_PATH_TOKEN_RE = re.compile(r"\$(?:\{[A-Za-z_][A-Za-z0-9_]*\}|[A-Za-z_][A-Za-z0-9_]*)")


def capture_gpu_snapshot() -> dict:
    info: dict = {
        "available": False,
        "have_nvidia_smi": shutil.which("nvidia-smi") is not None,
        "have_nvcc": shutil.which("nvcc") is not None,
        "gpus": [],
    }

    if info["have_nvidia_smi"]:
        try:
            proc = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=index,name,uuid,driver_version,compute_cap,memory.total,memory.free,memory.used,mig.mode.current",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                gpus = []
                for line in proc.stdout.strip().splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 9:
                        gpus.append({
                            "index": _int_or(parts[0]),
                            "name": parts[1],
                            "uuid": parts[2],
                            "driver_version": parts[3],
                            "compute_cap": parts[4],
                            "memory_total_mb": _float_or(parts[5]),
                            "memory_free_mb": _float_or(parts[6]),
                            "memory_used_mb": _float_or(parts[7]),
                            "mig_mode_current": parts[8],
                        })
                info["gpus"] = gpus
                info["available"] = bool(gpus)
        except (subprocess.SubprocessError, OSError) as e:
            info["nvidia_smi_error"] = repr(e)

    if info["have_nvcc"]:
        try:
            proc = subprocess.run(["nvcc", "--version"], capture_output=True, text=True, timeout=5)
            lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
            release_line = next((ln for ln in lines if "release" in ln.lower()), None)
            info["nvcc_release"] = release_line
        except (subprocess.SubprocessError, OSError) as e:
            info["nvcc_error"] = repr(e)

    return info


def _int_or(token: str) -> int | str:
    try:
        return int(token)
    except (TypeError, ValueError):
        return token


def _float_or(token: str) -> float | str:
    try:
        return float(token)
    except (TypeError, ValueError):
        return token


def _resolve_declared_path(
    spec: str,
    skill_dir: Path,
    *,
    out: Path | None = None,
) -> tuple[Path | None, str | None]:
    """Resolve a declared side-effect path, or return (None, reason) if untemplated."""
    if "<" in spec and ">" in spec:
        return None, "templated path; cannot resolve at engine level"
    if "${out}" in spec:
        if out is None:
            return None, "${out} path; output directory unavailable"
        spec = spec.replace("${out}", str(out))
    spec = spec.replace("${skill_dir}", str(skill_dir))
    spec = os.path.expandvars(spec)
    if _ENV_PATH_TOKEN_RE.search(spec):
        return None, "environment variable in path is unset"
    p = Path(spec)
    if str(p).startswith("~"):
        p = p.expanduser()
    elif not p.is_absolute():
        if (skill_dir / spec).exists() or spec.startswith(skill_dir.name + "/") or (REPO_ROOT / spec).exists():
            p = REPO_ROOT / spec
        else:
            p = skill_dir / spec
    return p.resolve(), None


_DIR_SCAN_ENTRY_CAP = 10_000


def _path_snapshot(p: Path) -> dict:
    if not p.exists():
        return {"exists": False}
    if p.is_symlink():
        return {"exists": True, "is_symlink": True, "target": str(p.readlink())}
    if p.is_file():
        st = p.stat()
        return {
            "exists": True,
            "is_file": True,
            "size_bytes": st.st_size,
            "mtime": st.st_mtime,
        }
    if p.is_dir():
        n_entries = 0
        total_bytes = 0
        truncated = False
        try:
            for sub in p.rglob("*"):
                if sub.is_file():
                    n_entries += 1
                    try:
                        total_bytes += sub.stat().st_size
                    except OSError:
                        pass
                if n_entries >= _DIR_SCAN_ENTRY_CAP:
                    truncated = True
                    break
        except OSError:
            pass
        snap = {
            "exists": True,
            "is_dir": True,
            "n_entries": n_entries,
            "total_bytes": total_bytes,
        }
        if truncated:
            snap["truncated"] = True
        return snap
    return {"exists": True, "unknown_type": True}


def _iter_declared(manifest: dict) -> list[tuple[str, str]]:
    side_effects = ((manifest.get("runtime") or {}).get("side_effects") or {})
    out: list[tuple[str, str]] = []
    for kind in ("local_writes", "home_writes"):
        for entry in side_effects.get(kind) or []:
            if isinstance(entry, str):
                out.append((kind, entry))
            elif isinstance(entry, dict) and entry.get("path"):
                out.append((kind, entry["path"]))
    return out


def capture_side_effects_snapshot(
    manifest: dict,
    skill_dir: Path,
    *,
    out: Path | None = None,
) -> list[dict]:
    records: list[dict] = []
    for kind, spec in _iter_declared(manifest):
        resolved, reason = _resolve_declared_path(spec, skill_dir, out=out)
        if resolved is None:
            records.append({
                "kind": kind,
                "declared": spec,
                "status": "skipped",
                "reason": reason,
            })
            continue
        snap = _path_snapshot(resolved)
        records.append({
            "kind": kind,
            "declared": spec,
            "resolved": _public_path(resolved),
            **snap,
        })
    return records


def diff_side_effects(before: list[dict], after: list[dict]) -> list[dict]:
    after_by_decl = {(s["kind"], s["declared"]): s for s in after}
    findings: list[dict] = []
    for b in before:
        if b.get("status") == "skipped":
            findings.append({**b, "change": "untracked"})
            continue
        a = after_by_decl.get((b["kind"], b["declared"]))
        if a is None:
            continue
        change = _classify(b, a)
        findings.append({
            "kind": b["kind"],
            "declared": b["declared"],
            "resolved": b.get("resolved"),
            "before_exists": b.get("exists", False),
            "after_exists": a.get("exists", False),
            "change": change,
            **({
                "size_delta_bytes": (a.get("size_bytes") or 0) - (b.get("size_bytes") or 0),
            } if a.get("is_file") else {}),
            **({
                "entries_delta": (a.get("n_entries") or 0) - (b.get("n_entries") or 0),
                "bytes_delta": (a.get("total_bytes") or 0) - (b.get("total_bytes") or 0),
            } if a.get("is_dir") else {}),
        })
    return findings


def _classify(before: dict, after: dict) -> str:
    if not before.get("exists") and after.get("exists"):
        return "created"
    if before.get("exists") and not after.get("exists"):
        return "removed"
    if not before.get("exists") and not after.get("exists"):
        return "absent"
    if after.get("is_file"):
        if (
            after.get("size_bytes") != before.get("size_bytes")
            or after.get("mtime") != before.get("mtime")
        ):
            return "modified"
        return "unchanged"
    if after.get("is_dir"):
        if (
            after.get("n_entries") != before.get("n_entries")
            or after.get("total_bytes") != before.get("total_bytes")
        ):
            return "grew"
        return "unchanged"
    return "unchanged"


def _wants_gpu(manifest: dict) -> bool:
    """True when the manifest's declared side_effects.requires_gpu is non-falsy.

    Skip the nvidia-smi/nvcc probes for CPU-only skills; they add ~150-500ms
    per run on fast wrappers like dicom_metadata_extract.
    """
    requires = ((manifest.get("runtime") or {}).get("side_effects") or {}).get("requires_gpu")
    if requires in (None, False, "", "none"):
        return False
    return True


_CONTAINER_INVOCATION_KEYS = (
    "container_image",
    "container_image_id",
    "container_provenance",
    "holohub_commit",
    "holohub_root",
)


def enrich_provenance_from_skill_output(out: Path, output_payload: dict | None) -> dict | None:
    """Merge HoloHub/container fields from skill ``output.json`` into provenance.json.

    No-op for CPU/non-container skills (their output.json carries none of the
    container-specific invocation keys), so this stays cheap on the hot path.
    """
    if not output_payload:
        return None
    inv = output_payload.get("invocation") or {}
    logs = output_payload.get("logs") or {}
    if not any(inv.get(k) for k in _CONTAINER_INVOCATION_KEYS) and not logs:
        return None
    prov_path = out / "provenance.json"
    payload = _read_json_or_empty(prov_path)
    if payload is None:
        return None
    image = inv.get("container_image")
    image_id = inv.get("container_image_id")
    skill_container = inv.get("container_provenance")

    merge_container_into_provenance(
        payload,
        image_ref=str(image) if image else None,
        image_id=str(image_id) if image_id else None,
        skill_container_block=skill_container if isinstance(skill_container, dict) else None,
    )
    container = payload.setdefault("container", {})
    if inv.get("holohub_commit"):
        container["holohub_commit"] = inv["holohub_commit"]
    if inv.get("holohub_root"):
        container["holohub_root"] = inv["holohub_root"]
    if inv.get("command"):
        container["outer_command"] = inv["command"]
    for key in (
        "stdout_tail",
        "stderr_tail",
        "container_stdout_tail",
        "container_stderr_tail",
        "benchmark_stdout_tail",
        "benchmark_stderr_tail",
        "build_stdout_tail",
        "build_stderr_tail",
    ):
        tail = logs.get(key)
        if isinstance(tail, str) and tail:
            container[key] = tail[:8000]

    pip_block = {}
    if isinstance(skill_container, dict):
        pip_block = skill_container.get("pip_freeze") or {}
    if pip_block.get("status") != "ok":
        engine = container.get("engine_capture") or {}
        pip_block = engine.get("pip_freeze") or pip_block
    write_container_environment_lock(out, pip_block if isinstance(pip_block, dict) else {})

    prov_path.write_text(json.dumps(payload, indent=2, default=str))
    return payload


def write_provenance(
    out: Path,
    manifest: dict,
    skill_dir: Path,
    side_effects_before: list[dict],
    run_out: Path | None = None,
) -> dict:
    gpu = capture_gpu_snapshot() if _wants_gpu(manifest) else {
        "available": False,
        "have_nvidia_smi": shutil.which("nvidia-smi") is not None,
        "have_nvcc": shutil.which("nvcc") is not None,
        "gpus": [],
        "note": "GPU probe skipped: manifest does not declare requires_gpu.",
    }
    side_effects_after = capture_side_effects_snapshot(
        manifest,
        skill_dir,
        out=run_out,
    )
    findings = diff_side_effects(side_effects_before, side_effects_after)

    declared_se = (manifest.get("runtime") or {}).get("side_effects") or {}
    payload = {
        "captured_at": _now_iso(),
        "gpu": gpu,
        "container": {
            "requires_docker": bool(declared_se.get("requires_docker", False)),
            "image_digest_observed": None,
            "note": (
                "Container digest/labels not captured by MVP provenance. "
                "Add via skill-side instrumentation when the wrapper spawns docker."
            ),
        },
        "network": {
            "declared_endpoints": declared_se.get("network_endpoints") or [],
            "observed_endpoints": None,
            "note": "Endpoint observation not implemented; tracked as planned work.",
        },
        "side_effects": {
            "before": side_effects_before,
            "after": side_effects_after,
            "findings": findings,
        },
    }
    (out / "provenance.json").write_text(json.dumps(payload, indent=2, default=str))
    return payload
