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

"""Shared eval_engine helpers.

These are deliberately small and dependency-light so the CLI runners can share
evidence-pack bookkeeping without coupling to a specific skill.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FENCE = chr(96) * 3
EXCLUDED_SKILL_FILE_PARTS = ("__pycache__", ".pytest_cache", "bundle", "bundles")
SECRET_ENV_MARKERS = ("TOKEN", "KEY", "SECRET", "PASSWORD", "PASSWD", "AUTH", "CRED", "PRIVATE")
_REPLAY_ENV_REF_RE = re.compile(
    r"\$\{[A-Za-z_][A-Za-z0-9_]*:\?[A-Za-z_][A-Za-z0-9_]* is required for replay\}"
)

# Bumped on every breaking change to the evidence-pack contract. Additive field
# changes do not require a bump; see spec/versioning_policy.md and
# spec/evidence_pack.schema.json (supported_pack_format_versions).
PACK_FORMAT_VERSION = "1.0.0"


def _sha256_path(path: Path) -> str:
    """Hash a file by content, or a directory by sorted (relative_path, sha256) listing."""
    h = hashlib.sha256()
    if path.is_file():
        h.update(path.read_bytes())
        return h.hexdigest()
    if path.is_dir():
        for p in sorted(path.rglob("*")):
            if p.is_file():
                rel = str(p.relative_to(path))
                h.update(rel.encode())
                h.update(b"\0")
                file_h = hashlib.sha256()
                file_h.update(p.read_bytes())
                h.update(file_h.digest())
        return h.hexdigest()
    return ""


def _path_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    if path.is_dir():
        return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())
    return 0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_git_sha() -> str | None:
    """Capture the current HEAD commit SHA for evidence-pack traceability.

    Returns the full 40-char SHA, or None if the checkout is not in a git
    repo or git is unavailable. Best-effort by design: a pack written from a
    tarball or from outside any git tree should still produce a valid pack
    with `repo_git_sha: null`.
    """
    repo_root = Path(__file__).resolve().parent.parent
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode != 0:
            return None
        sha = proc.stdout.strip()
        return sha if len(sha) == 40 and all(c in "0123456789abcdef" for c in sha) else None
    except Exception:
        return None


def _read_json_or_empty(path: Path) -> dict | None:
    """Read a JSON file, returning None if absent or unparseable.

    Shared by run_trusted and run_workflow for reading per-step or per-verifier
    artifacts. Returns None (rather than {}) so callers can distinguish 'file
    missing or unreadable' from 'valid but empty object'.
    """
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def _runtime_summary() -> dict:
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "executable": Path(sys.executable).name,
    }


def _pip_freeze() -> str:
    """Capture pip freeze output for env-lock reproducibility. Best-effort."""
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True, timeout=30
        )
        return _sanitize_pip_freeze(proc.stdout) if proc.returncode == 0 else ""
    except Exception:
        return ""


def _sanitize_pip_freeze(text: str) -> str:
    """Remove host-local build paths from pip freeze direct references."""
    return re.sub(r" @ file://\S+", " @ file://<local-build-path-redacted>", text)


def _sanitize_public_text(text: str) -> str:
    """Remove checkout-local and user-home absolute paths from public pack text."""
    sanitized = text.replace(str(REPO_ROOT) + "/", "")
    sanitized = sanitized.replace(str(REPO_ROOT), ".")
    home = str(Path.home())
    if home and home != str(REPO_ROOT):
        sanitized = sanitized.replace(home + "/", "<HOME>/")
        sanitized = sanitized.replace(home, "<HOME>")
    return sanitized


def _env_lock_fingerprint(pip_freeze_text: str) -> str:
    """Hash of pip freeze for quick drift detection."""
    return hashlib.sha256(pip_freeze_text.encode()).hexdigest()[:16]


def _skill_dir_files(skill_dir: Path) -> list[str]:
    files = []
    for p in skill_dir.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(skill_dir)
        if any(part in rel.parts for part in EXCLUDED_SKILL_FILE_PARTS):
            continue
        files.append(str(rel))
    return sorted(files)


def _public_path(path: Path | str) -> str:
    """Render repo paths without embedding the current user's checkout root."""
    raw = str(path)
    if "://" in raw:
        return raw
    try:
        p = Path(raw).expanduser()
        resolved = p.resolve()
    except (OSError, ValueError):
        return raw
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        home = Path.home()
        try:
            return "~/" + str(resolved.relative_to(home))
        except ValueError:
            return str(resolved)


def _public_command(command: list[str]) -> list[str]:
    """Render command argv for public evidence artifacts."""
    out: list[str] = []
    for i, token in enumerate(command):
        if i == 0 and Path(token).name.startswith("python"):
            out.append("python3")
            continue
        out.append(_public_path(token))
    return out


def _relative_to_repo(path: Path) -> Path:
    try:
        return path.resolve().relative_to(REPO_ROOT)
    except ValueError:
        return path


def _env_replay_lines(manifest: dict) -> list[str]:
    """Render declared env vars for replay.sh without leaking secret-shaped values."""
    env_required = manifest.get("runtime", {}).get("env_required", []) or []
    lines: list[str] = []
    for var in env_required:
        if isinstance(var, str):
            name = var
        elif isinstance(var, dict) and var.get("name"):
            name = var["name"]
        else:
            continue
        captured = os.environ.get(name, "")
        is_secret = any(marker in name.upper() for marker in SECRET_ENV_MARKERS)
        if is_secret:
            present_marker = "(was set at run time)" if captured else "(was NOT set at run time)"
            lines.append(f"# {name} {present_marker}; set it yourself before running replay.sh")
            lines.append(f'export {name}="${{{name}:?{name} is required for replay}}"')
        elif captured:
            lines.append(f"export {name}={shlex.quote(captured)}")
        else:
            lines.append(f"# {name} was not set at run time")
    return lines


_DOUBLE_QUOTE_ESCAPE = str.maketrans({"\\": "\\\\", '"': '\\"', "`": "\\`", "$": "\\$"})


def _quote_replay_token(token: str) -> str:
    """Quote one argv token while preserving redacted env refs for replay."""
    matches = list(_REPLAY_ENV_REF_RE.finditer(token))
    if not matches:
        return shlex.quote(token)

    pieces: list[str] = []
    pos = 0
    for match in matches:
        pieces.append(token[pos : match.start()].translate(_DOUBLE_QUOTE_ESCAPE))
        pieces.append(match.group(0))
        pos = match.end()
    pieces.append(token[pos:].translate(_DOUBLE_QUOTE_ESCAPE))
    return '"' + "".join(pieces) + '"'


def _rewrite_replay_token(tok: str, *, is_first: bool) -> str:
    """Rewrite one command token for replay.sh.

    The first token gets normalized to ``python3`` when it points at a Python
    interpreter (so replay does not pin the runner's conda path). Absolute
    paths inside the repo become repo-relative so replay works from a fresh
    clone. External absolute paths are left intact — replay will fail loudly
    if the data has moved, which is the correct signal.
    """
    if is_first and Path(tok).name.startswith("python"):
        return "python3"
    try:
        p = Path(tok)
    except (OSError, ValueError):
        return tok
    if not p.is_absolute() or not p.exists():
        return tok
    try:
        resolved = p.resolve()
        return str(resolved.relative_to(REPO_ROOT))
    except (OSError, ValueError):
        return tok


def _replay_script(
    script: Path,
    fixture: Path,
    manifest: dict,
    *,
    preflight_failed: bool = False,
    command: list[str] | None = None,
) -> str:
    heading = (
        "# Auto-generated replay (preflight-failed run). Best-effort.\n"
        if preflight_failed
        else (
            "# Auto-generated replay. Best-effort; may not reproduce across\n"
            "# pydicom/torch/Python version changes (compare environment.lock).\n"
        )
    )
    env_lines = _env_replay_lines(manifest)

    if command:
        rewritten = [_rewrite_replay_token(tok, is_first=(i == 0)) for i, tok in enumerate(command)]
        cmd_line = " ".join(_quote_replay_token(t) for t in rewritten)
    else:
        cmd_line = (
            "python3 "
            + shlex.quote(str(_relative_to_repo(script)))
            + " "
            + shlex.quote(str(_relative_to_repo(fixture)))
        )

    return (
        "#!/usr/bin/env bash\n"
        + heading
        + "set -euo pipefail\n"
        + 'SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"\n'
        + 'REPO_ROOT="$SCRIPT_DIR"\n'
        + 'while [ ! -e "$REPO_ROOT/Makefile" ] && [ "$REPO_ROOT" != "/" ]; do\n'
        + '  REPO_ROOT="$(dirname "$REPO_ROOT")"\n'
        + "done\n"
        + '[ -e "$REPO_ROOT/Makefile" ] || { echo "could not find repo root (looked for Makefile)"; exit 1; }\n'
        + 'cd "$REPO_ROOT"\n'
        + ("\n".join(env_lines) + "\n" if env_lines else "")
        + cmd_line
        + "\n"
    )
