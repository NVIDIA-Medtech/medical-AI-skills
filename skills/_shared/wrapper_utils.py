"""Shared helpers for HoloHub-family wrapper scripts.

These skills shell out to upstream Holoscan/HoloHub CLIs and emit JSON evidence
payloads. The helpers here capture the generic plumbing — file hashing, group
inventory, git/docker probes, log truncation, JSON emit, and a fail-with-stderr
exit path — without leaking into domain logic.

This module deliberately does NOT import `eval_engine`. Skill scripts must
remain portable: they should run in any environment where the upstream CLI is
installed, regardless of whether the eval_engine harness is on PYTHONPATH.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            buf = f.read(chunk)
            if not buf:
                break
            h.update(buf)
    return h.hexdigest()


def file_sha256_safe(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return sha256_file(path)
    except Exception:
        return ""


def file_record(path: Path, root: Path) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(root)),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def collect_group(paths: list[Path], root: Path) -> dict[str, Any]:
    files = [file_record(p, root) for p in sorted(paths)]
    return {
        "count": len(files),
        "total_bytes": sum(f["bytes"] for f in files),
        "files": files,
    }


def git_commit(root: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root),
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return ""


def docker_image_id(image_ref: str) -> str | None:
    try:
        out = subprocess.run(
            ["docker", "image", "inspect", "--format", "{{.Id}}", image_ref],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return None


def tail(s: str, n_chars: int = 4000) -> str:
    if len(s) <= n_chars:
        return s
    return "..." + s[-n_chars:]


def emit(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, indent=2))
    sys.stdout.flush()


def fail_with(message: str, exit_code: int = 2) -> int:
    sys.stderr.write(message + ("\n" if not message.endswith("\n") else ""))
    return exit_code
