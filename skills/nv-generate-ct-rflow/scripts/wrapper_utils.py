"""Local helpers for NV-Generate-CTMR wrapper scripts.

This module deliberately does not import `eval_engine`. Skill scripts must
remain portable in environments where only the upstream tool and Python
dependencies are installed.
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


def tail(s: str, n_chars: int = 4000) -> str:
    if len(s) <= n_chars:
        return s
    return "..." + s[-n_chars:]


def emit(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, indent=2))
    sys.stdout.flush()
