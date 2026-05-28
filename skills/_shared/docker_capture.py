"""Docker metadata capture for HoloHub wrapper scripts (no eval_engine import)."""
# Canonical counterpart: eval_engine/container_provenance.py (richer API).
# Kept separate because lint rule E4 forbids skills from importing eval_engine.
from __future__ import annotations

import json
import subprocess
from typing import Any


def capture_container_provenance(image_ref: str | None, *, pip_freeze: bool = True) -> dict[str, Any]:
    if not image_ref:
        return {"status": "skipped", "reason": "no image ref"}
    inspect = _image_inspect(image_ref)
    pip = _pip_freeze(image_ref) if pip_freeze else {"status": "skipped"}
    return {"image_ref": image_ref, "inspect": inspect, "pip_freeze": pip}


def _image_inspect(image_ref: str) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            ["docker", "image", "inspect", image_ref, "--format", "{{json .}}"],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return {"status": "failed", "reason": repr(e)}
    if proc.returncode != 0:
        return {"status": "failed", "stderr": (proc.stderr or "")[:2000]}
    try:
        rows = json.loads(proc.stdout)
        row = rows[0] if isinstance(rows, list) else rows
    except json.JSONDecodeError:
        return {"status": "failed", "reason": "parse error"}
    config = (row or {}).get("Config") or {}
    return {
        "status": "ok",
        "id": row.get("Id"),
        "repo_tags": row.get("RepoTags") or [],
        "labels": config.get("Labels") or {},
        "env": config.get("Env") or [],
    }


def _pip_freeze(image_ref: str) -> dict[str, Any]:
    try:
        proc = subprocess.run(
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
            capture_output=True,
            text=True,
            timeout=90,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return {"status": "failed", "reason": repr(e)}
    if proc.returncode != 0:
        return {"status": "failed", "exit_code": proc.returncode, "stderr": (proc.stderr or "")[-2000:]}
    text = proc.stdout or ""
    return {"status": "ok", "pip_freeze_lines": len(text.splitlines()), "pip_freeze_text": text}
