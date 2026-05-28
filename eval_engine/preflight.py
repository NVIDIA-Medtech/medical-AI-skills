"""Input and host-environment preflight checks for single-skill runs."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from eval_engine.common import _path_size, _public_path
from eval_engine.skill_runtime import _first_input


def _check_dicom_file(path: Path) -> dict:
    try:
        import pydicom

        ds = pydicom.dcmread(str(path), stop_before_pixels=True)
        return {
            "name": "dicom_readable",
            "path": _public_path(path),
            "status": "passed",
            "modality": str(getattr(ds, "Modality", "")),
            "series_instance_uid": str(getattr(ds, "SeriesInstanceUID", "")),
        }
    except Exception as e:
        return {
            "name": "dicom_readable",
            "path": _public_path(path),
            "status": "failed",
            "error": str(e),
        }


def _check_dicom_series(path: Path) -> list[dict]:
    checks: list[dict] = []
    if not path.is_dir():
        return [{"name": "dicom_series_readable", "path": _public_path(path), "status": "failed",
                 "error": "fixture is not a directory"}]

    try:
        import pydicom

        readable = []
        for p in sorted(path.rglob("*")):
            if not p.is_file():
                continue
            try:
                readable.append(pydicom.dcmread(str(p), stop_before_pixels=True))
            except Exception:
                continue
        if not readable:
            return [{"name": "dicom_series_readable", "path": _public_path(path), "status": "failed",
                     "error": "no readable DICOM files found"}]

        series_uids = {str(getattr(ds, "SeriesInstanceUID", "")) for ds in readable}
        series_uids.discard("")
        modalities = {str(getattr(ds, "Modality", "")) for ds in readable}
        modalities.discard("")
        checks.append({
            "name": "dicom_series_readable",
            "path": _public_path(path),
            "status": "passed",
            "readable_files": len(readable),
        })
        checks.append({
            "name": "dicom_series_single_series",
            "status": "passed" if len(series_uids) <= 1 else "failed",
            "series_instance_uid_count": len(series_uids),
        })
        checks.append({
            "name": "dicom_series_modality_consistent",
            "status": "passed" if len(modalities) <= 1 else "failed",
            "modalities": sorted(modalities),
        })
        return checks
    except Exception as e:
        return [{"name": "dicom_series_readable", "path": _public_path(path), "status": "failed", "error": str(e)}]


def _check_gxf_replayer_dir(path: Path) -> dict:
    """Validate a GXF Stream Replayer fixture directory.

    HoloHub's VideoStreamReplayerOp requires a `<clip>.gxf_index` + matching
    `<clip>.gxf_entities` pair. The committed `example_clip_stub/` fixture
    contains only a README so the boundary check has something to grip on;
    this preflight surfaces the fixture-shape failure honestly (and the
    skill's `fixture_help` will then be shown to the user).
    """
    if not path.is_dir():
        return {
            "name": "gxf_replayer_readable",
            "path": _public_path(path),
            "status": "failed",
            "error": "fixture is not a directory",
        }
    index_stems: set[Path] = set()
    entities_stems: set[Path] = set()
    for child in path.rglob("*.gxf_*"):
        if child.suffix == ".gxf_index":
            index_stems.add(child.with_suffix(""))
        elif child.suffix == ".gxf_entities":
            entities_stems.add(child.with_suffix(""))
    pairs = index_stems & entities_stems
    if not pairs:
        return {
            "name": "gxf_replayer_readable",
            "path": _public_path(path),
            "status": "failed",
            "n_gxf_index": len(index_stems),
            "n_gxf_entities": len(entities_stems),
            "error": (
                "no <clip>.gxf_index + <clip>.gxf_entities pair found; "
                "this fixture is a stub. See the skill's fixture_help."
            ),
        }
    return {
        "name": "gxf_replayer_readable",
        "path": _public_path(path),
        "status": "passed",
        "n_pairs": len(pairs),
    }


def _check_nifti_file(path: Path) -> dict:
    try:
        import nibabel as nib

        img = nib.load(str(path))
        return {
            "name": "nifti_readable",
            "path": _public_path(path),
            "status": "passed",
            "shape": list(img.shape),
        }
    except Exception as e:
        return {
            "name": "nifti_readable",
            "path": _public_path(path),
            "status": "failed",
            "error": str(e),
        }


def _cuda_available() -> bool:
    """Cheap host-side CUDA probe."""
    try:
        proc = subprocess.run(["nvidia-smi", "-L"], capture_output=True,
                              text=True, timeout=5)
        if proc.returncode == 0 and proc.stdout.strip():
            return True
    except Exception:
        pass
    try:
        import torch  # type: ignore
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def _docker_daemon_reachable() -> bool:
    """Cheap host-side Docker daemon probe.

    The skill manifests that declare requires_docker need a *running* daemon,
    not just the docker CLI. `docker info` returns non-zero when the daemon is
    unreachable; we treat any failure as "no daemon".
    """
    try:
        proc = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True, text=True, timeout=5,
        )
        return proc.returncode == 0 and bool(proc.stdout.strip())
    except Exception:
        return False


def _env_required(manifest: dict) -> list[str]:
    """Union of runtime.env_required and side_effects.env_required (deduped).

    Accepts the same shapes as `common._env_replay_lines` so a manifest using
    the dict form (`{"name": "FOO"}`) does not silently bypass preflight.
    """
    runtime = manifest.get("runtime", {}) or {}
    side_effects = runtime.get("side_effects", {}) or {}
    seen: list[str] = []
    for source in (runtime.get("env_required") or [],
                   side_effects.get("env_required") or []):
        for entry in source:
            if isinstance(entry, str):
                name = entry
            elif isinstance(entry, dict) and entry.get("name"):
                name = str(entry["name"])
            else:
                continue
            if name and name not in seen:
                seen.append(name)
    return seen


def _environment_preflight(manifest: dict) -> tuple[str, str, list[dict]]:
    """Check host environment against manifest declarations.

    Returns:
        (status, reason, checks) where status is one of "ok" (proceed),
        "skip" (honest skip, e.g. no GPU + no fallback), or "failed" (a
        declared requirement is unmet and there is no fallback path).
    """
    runtime = manifest.get("runtime", {}) or {}
    side_effects = runtime.get("side_effects", {}) or {}
    requires_gpu = side_effects.get("requires_gpu", "none")
    gpu_fallback = side_effects.get("gpu_fallback")
    requires_docker = bool(side_effects.get("requires_docker", False))
    checks: list[dict] = []

    if requires_gpu not in (None, "none", False):
        have_cuda = _cuda_available()
        checks.append({
            "name": "host_has_cuda",
            "requires_gpu": requires_gpu,
            "gpu_fallback": gpu_fallback,
            "have_cuda": have_cuda,
            "status": "passed" if have_cuda else ("passed" if gpu_fallback else "skipped"),
        })
        if not have_cuda and not gpu_fallback:
            return "skip", (
                f"manifest declares requires_gpu={requires_gpu!r} with no "
                f"gpu_fallback; host has no CUDA. Skipping skill execution "
                f"honestly rather than forcing a CUDA-deserialization failure."
            ), checks

    # Docker daemon check. The CLI binary alone is not enough — the daemon
    # has to be reachable for `./holohub run` and any container-mode wrapper.
    if requires_docker:
        have_docker = _docker_daemon_reachable()
        checks.append({
            "name": "docker_daemon_reachable",
            "have_docker": have_docker,
            "status": "passed" if have_docker else "failed",
        })
        if not have_docker:
            return "failed", (
                "manifest declares requires_docker=true but the Docker "
                "daemon is not reachable on this host. Start it (e.g. "
                "`sudo systemctl start docker`) or run the skill on a host "
                "with Docker available."
            ), checks

    # Required environment variables — both runtime.env_required and
    # side_effects.env_required are valid declaration sites.
    missing_env: list[str] = []
    for name in _env_required(manifest):
        present = os.environ.get(name) not in (None, "")
        checks.append({
            "name": f"env_required:{name}",
            "env_var": name,
            "present": present,
            "status": "passed" if present else "failed",
        })
        if not present:
            missing_env.append(name)
    if missing_env:
        return "failed", (
            "manifest declares runtime.env_required="
            + repr(missing_env)
            + " but those environment variables are not set. Export them "
              "before invoking the skill (see SKILL.md for usage)."
        ), checks

    return "ok", "", checks


def _preflight_checks(manifest: dict, fixture: Path) -> tuple[str, list[dict]]:
    """Validate the declared input boundary before invoking the skill."""
    inp = _first_input(manifest)
    checks: list[dict] = []
    formats = set(inp.get("formats", []) or [])

    if "default_sentinel" in formats and str(fixture) == "default":
        checks.append({
            "name": "fixture_default_sentinel",
            "path": "default",
            "status": "passed",
        })
        return "passed", checks

    exists = fixture.exists()
    checks.append({"name": "fixture_exists", "path": _public_path(fixture), "status": "passed" if exists else "failed"})
    if not exists:
        return "failed", checks

    input_type = inp.get("type")
    if input_type in ("file", "file_path"):
        checks.append({"name": "fixture_is_file", "path": _public_path(fixture),
                       "status": "passed" if fixture.is_file() else "failed"})
    elif input_type in ("directory", "directory_path"):
        checks.append({"name": "fixture_is_directory", "path": _public_path(fixture),
                       "status": "passed" if fixture.is_dir() else "failed"})

    max_size = inp.get("max_size_bytes")
    if max_size is not None:
        size = _path_size(fixture)
        checks.append({
            "name": "fixture_size_budget",
            "size_bytes": size,
            "max_size_bytes": max_size,
            "status": "passed" if size <= max_size else "failed",
        })

    if "dicom_series" in formats:
        checks.extend(_check_dicom_series(fixture))
    elif "dicom" in formats:
        if fixture.is_dir():
            checks.extend(_check_dicom_series(fixture))
        else:
            checks.append(_check_dicom_file(fixture))
    if "nifti" in formats:
        checks.append(_check_nifti_file(fixture))
    if "gxf_replayer_dir" in formats:
        checks.append(_check_gxf_replayer_dir(fixture))

    status = "failed" if any(c.get("status") == "failed" for c in checks) else "passed"
    return status, checks
