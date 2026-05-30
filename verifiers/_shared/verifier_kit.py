"""Shared scaffolding for verifier graders.

Verifiers grade evidence packs. The boilerplate (load pack JSON, build
``{name, status, reason, ...}`` check records, resolve declared artifact
paths against several candidate bases, and the ``argv`` CLI entry) is kept
inside ``verifiers/`` so verifier scripts stay independent of ``eval_engine``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_pack_json(pack_dir: Path, name: str) -> dict[str, Any]:
    """Read ``<pack_dir>/<name>`` as JSON, returning ``{}`` on missing/parse error."""
    try:
        return json.loads((pack_dir / name).read_text())
    except Exception:
        return {}


def make_check(
    name: str,
    passed: bool,
    reason: str,
    *,
    level: str = "fail",
    **extra: Any,
) -> dict[str, Any]:
    """Build one check record."""
    item: dict[str, Any] = {
        "name": name,
        "status": "pass" if passed else level,
        "reason": reason,
    }
    item.update(extra)
    return item


def resolve_pack_artifact(pack_dir: Path, rel: str, *extra_bases: Path) -> Path:
    """Resolve a declared artifact path against the pack and optional extra bases.

    Evidence packs may contain portable ``<repo>`` placeholders from older
    examples or absolute paths captured from another checkout. Verifiers should
    resolve those to the current checkout when the corresponding artifact exists,
    without requiring imports from ``eval_engine``.
    """
    rel_path = Path(rel.replace("<repo>", str(REPO_ROOT)))
    if rel_path.is_absolute():
        if rel_path.exists():
            return rel_path
        relocated = _relocate_checkout_path(rel_path)
        if relocated is not None and relocated.exists():
            return relocated
        return rel_path
    bases = (pack_dir, *extra_bases)
    for base in bases:
        candidate = base / rel_path
        if candidate.exists():
            return candidate
    return pack_dir / rel_path


def _relocate_checkout_path(path: Path) -> Path | None:
    """Map ``/.../<repo-name>/suffix`` from another checkout to this repo."""
    parts = path.parts
    for index in range(len(parts) - 1, -1, -1):
        if parts[index] == REPO_ROOT.name:
            suffix = Path(*parts[index + 1 :])
            return REPO_ROOT / suffix
    return None


def run_grader(grade_fn: Callable[[Path], dict[str, Any]], *, sort_keys: bool = False) -> None:
    """CLI entry-point. Usage: ``grade.py EVIDENCE_PACK_DIR``."""
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: grade.py EVIDENCE_PACK_DIR"}))
        raise SystemExit(2)
    pack_dir = Path(sys.argv[1])
    if not pack_dir.is_dir():
        print(json.dumps({"error": f"not a directory: {pack_dir}"}))
        raise SystemExit(2)
    print(json.dumps(grade_fn(pack_dir), indent=2, sort_keys=sort_keys))
