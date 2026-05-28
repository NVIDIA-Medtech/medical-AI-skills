"""Docker/container provenance capture for HoloHub and container-backed skills."""
# Skill-side mirror: skills/_shared/docker_capture.py (subset, no eval_engine import).
# Duplication is intentional: lint rule E4 forbids skills from importing eval_engine.
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def _run(cmd: list[str], timeout_s: float = 30.0) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return 127, "", repr(e)


def capture_docker_image_inspect(image_ref: str) -> dict[str, Any]:
    """Best-effort ``docker image inspect`` summary for one image ref."""
    out: dict[str, Any] = {"image_ref": image_ref, "status": "skipped"}
    if not image_ref:
        out["reason"] = "no image ref"
        return out
    rc, stdout, stderr = _run(
        ["docker", "image", "inspect", image_ref, "--format", "{{json .}}"],
        timeout_s=15.0,
    )
    if rc != 0 or not stdout.strip():
        out.update({"status": "failed", "stderr": stderr[:2000]})
        return out
    try:
        rows = json.loads(stdout)
        row = rows[0] if isinstance(rows, list) and rows else rows
    except json.JSONDecodeError:
        out.update({"status": "failed", "reason": "inspect json parse error"})
        return out
    if not isinstance(row, dict):
        out.update({"status": "failed", "reason": "unexpected inspect shape"})
        return out
    config = row.get("Config") or {}
    out.update({
        "status": "ok",
        "id": row.get("Id"),
        "repo_tags": row.get("RepoTags") or [],
        "created": row.get("Created"),
        "architecture": row.get("Architecture"),
        "os": row.get("Os"),
        "labels": config.get("Labels") or {},
        "env": config.get("Env") or [],
        "entrypoint": config.get("Entrypoint"),
        "cmd": config.get("Cmd"),
    })
    return out


def capture_container_pip_freeze(image_ref: str, *, timeout_s: float = 60.0) -> dict[str, Any]:
    """Run ``pip freeze`` inside a one-shot container from ``image_ref``."""
    out: dict[str, Any] = {"image_ref": image_ref, "status": "skipped"}
    if not image_ref:
        out["reason"] = "no image ref"
        return out
    rc, stdout, stderr = _run(
        [
            "docker",
            "run",
            "--rm",
            "--entrypoint",
            "python3",
            image_ref,
            "-m",
            "pip",
            "freeze",
        ],
        timeout_s=timeout_s,
    )
    if rc != 0:
        out.update({
            "status": "failed",
            "exit_code": rc,
            "stderr_tail": stderr[-4000:] if stderr else "",
        })
        return out
    lines = [ln for ln in stdout.splitlines() if ln.strip()]
    out.update({
        "status": "ok",
        "pip_freeze_lines": len(lines),
        "pip_freeze_text": stdout,
    })
    return out


def capture_container_provenance(
    image_ref: str | None,
    *,
    include_pip_freeze: bool = True,
) -> dict[str, Any]:
    """Full container block for provenance.json / skill output.json."""
    if not image_ref:
        return {"status": "skipped", "reason": "no container image ref"}
    inspect = capture_docker_image_inspect(image_ref)
    pip = (
        capture_container_pip_freeze(image_ref)
        if include_pip_freeze
        else {"status": "skipped", "reason": "pip freeze not requested"}
    )
    return {
        "image_ref": image_ref,
        "inspect": inspect,
        "pip_freeze": pip,
    }


def write_container_environment_lock(out_dir: Path, pip_block: dict[str, Any]) -> Path | None:
    """Write ``container_environment.lock`` when in-container pip freeze succeeded."""
    if pip_block.get("status") != "ok":
        return None
    text = pip_block.get("pip_freeze_text")
    if not isinstance(text, str) or not text.strip():
        return None
    path = out_dir / "container_environment.lock"
    path.write_text(text)
    return path


def _apply_capture_block(
    container: dict,
    block: dict,
    image_id: str | None,
    *,
    prefer_existing_image_id: bool = False,
) -> None:
    inspect = block.get("inspect") or {}
    if inspect.get("status") == "ok":
        if prefer_existing_image_id:
            container["image_digest_observed"] = image_id or inspect.get("id")
        else:
            container["image_digest_observed"] = inspect.get("id") or image_id
        container["repo_tags"] = inspect.get("repo_tags")
        container["labels"] = inspect.get("labels")
        container["env"] = inspect.get("env")
    pip = block.get("pip_freeze") or {}
    if pip.get("status") == "ok":
        container["pip_freeze_lines"] = pip.get("pip_freeze_lines")


def merge_container_into_provenance(
    provenance: dict[str, Any],
    *,
    image_ref: str | None,
    image_id: str | None,
    skill_container_block: dict[str, Any] | None,
) -> dict[str, Any]:
    """Merge skill-side and engine-side container capture into provenance['container']."""
    container = provenance.setdefault("container", {})
    if image_ref:
        container["image_ref"] = image_ref
    if image_id:
        container["image_digest_observed"] = image_id

    block = skill_container_block or {}
    if block:
        container["skill_capture"] = block
        _apply_capture_block(container, block, image_id)
    elif image_ref:
        engine_block = capture_container_provenance(image_ref)
        container["engine_capture"] = engine_block
        _apply_capture_block(
            container,
            engine_block,
            image_id,
            prefer_existing_image_id=True,
        )

    container["note"] = (
        "Container image inspect and optional in-container pip freeze "
        "(HoloHub docker workflow)."
    )
    return provenance
