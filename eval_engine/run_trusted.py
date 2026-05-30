#!/usr/bin/env python3
"""Trusted-run path: skill + paired verifiers in one directory.

Layout:

    <out>/
      trust_summary.json
      skill_run/                  # full skill evidence pack
      verifiers/<verifier_dir>/   # full verifier evidence pack(s)

Steps:
  1. Run the target skill (eval_engine.run) into ``<out>/skill_run``.
  2. For every paired_verifier with status=="implemented", resolve the
     verifier directory under verifiers/ and run it with skill_run as fixture.
  3. Record planned verifiers as explicit gaps so missing coverage is visible.
  4. Write trust_summary.json that links the skill pack and verifier packs.

Each step spawns a fresh ``python eval_engine/run.py`` subprocess so a verifier
crash cannot pollute the parent's interpreter. For N implemented verifiers
that's N+1 Python cold-starts; acceptable for trust gates that run rarely.

Usage:
    python -m eval_engine.run_trusted skills/<name> --fixture <path> --out <dir>
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import typer

from eval_engine.common import (
    PACK_FORMAT_VERSION,
    REPO_ROOT,
    _now_iso,
    _read_json_or_empty,
    _sha256_path,
)
from eval_engine.evidence import SKILL_RUN_SUBDIR
from eval_engine.manifest import paired_verifier_dir
from eval_engine.skill_runtime import _load_skill

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TRUST_FORMAT_VERSION = "1.2.0"

app = typer.Typer(add_completion=False)


def _resolve_verifier_dir(verifier_id: str) -> Path | None:
    candidate = paired_verifier_dir(verifier_id)
    if (candidate / "skill_manifest.yaml").exists():
        return candidate
    return None


def _read_pack_overall(pack_dir: Path) -> str:
    data = _read_json_or_empty(pack_dir / "validation_summary.json")
    if data is None:
        return "missing" if not (pack_dir / "validation_summary.json").exists() else "unreadable"
    return data.get("overall_status", "unknown")


PACK_HASH_FILES = (
    "manifest.json",
    "validation_summary.json",
    "output.json",
    "provenance.json",
    "agent_run_trace.jsonl",
)


def _pack_hashes(pack_dir: Path) -> dict[str, str]:
    """Return hashes for stable evidence files that exist in a pack."""
    hashes: dict[str, str] = {}
    for name in PACK_HASH_FILES:
        path = pack_dir / name
        if path.exists():
            hashes[name] = _sha256_path(path)
    return hashes


def _pack_record(
    *,
    role: str,
    pack_id: str | None,
    pack: str,
    pack_dir: Path,
    overall: str,
    exit_code: int | None,
) -> dict:
    record = {
        "role": role,
        "id": pack_id,
        "pack": pack,
        "overall": overall,
        "hashes": _pack_hashes(pack_dir),
    }
    if exit_code is not None:
        record["exit_code"] = exit_code
    return record


def _listify(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _issue_count(output: dict, *, count_keys: tuple[str, ...], list_keys: tuple[str, ...]) -> int:
    count = 0
    for key in count_keys:
        value = output.get(key)
        if isinstance(value, int):
            count += value
    for key in list_keys:
        value = output.get(key)
        if isinstance(value, list):
            count += len(value)
    return count


def _count_key_total(output: dict, count_keys: tuple[str, ...]) -> int:
    count = 0
    for key in count_keys:
        value = output.get(key)
        if isinstance(value, int):
            count += value
    return count


def _iter_check_records(value, *, prefix: str = ""):
    if isinstance(value, dict):
        checks = value.get("checks")
        if isinstance(checks, list):
            for check in checks:
                if isinstance(check, dict):
                    yield prefix or "checks", check
        for key, child in value.items():
            if key == "checks":
                continue
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            yield from _iter_check_records(child, prefix=child_prefix)
    elif isinstance(value, list):
        for idx, item in enumerate(value):
            yield from _iter_check_records(item, prefix=f"{prefix}[{idx}]")


def _check_finding(path: str, check: dict) -> str:
    name = check.get("name") or path
    reason = check.get("reason")
    if reason:
        return f"{path}.{name}: {reason}"
    return f"{path}.{name}"


def _add_distinct_finding(items: list[str], item: str) -> None:
    """Append a finding unless it repeats the same reason with or without path context."""
    item_tail = item.split(": ", 1)[-1]
    item_prefix = item.split(": ", 1)[0]
    for idx, existing in enumerate(items):
        existing_tail = existing.split(": ", 1)[-1]
        existing_prefix = existing.split(": ", 1)[0]
        if (
            item == existing
            or item_tail == existing_tail
            or item.endswith(existing)
            or existing.endswith(item_tail)
        ):
            # Prefer the path-qualified finding when it is available.
            if "." in item_prefix and "." not in existing_prefix:
                items[idx] = item
            return
    items.append(item)


def _semantic_findings(output: dict) -> dict:
    semantic_overall = output.get("overall")
    failed: list[str] = []
    warnings: list[str] = []
    for path, check in _iter_check_records(output):
        status = str(check.get("status") or "").lower()
        if status in {"fail", "failed"} or check.get("ok") is False:
            failed.append(_check_finding(path, check))
        elif status in {"warn", "warning"}:
            warnings.append(_check_finding(path, check))

    if semantic_overall in {"fail", "failed"} and not failed:
        failed.append(f"overall={semantic_overall}")
    if semantic_overall in {"warn", "warning"} and not warnings:
        warnings.append(f"overall={semantic_overall}")

    return {
        "semantic_overall": semantic_overall if isinstance(semantic_overall, str) else None,
        "semantic_failure_count": len(failed),
        "semantic_warning_count": len(warnings),
        "failure_findings": failed[:20],
        "semantic_warning_findings": warnings[:20],
    }


def _verifier_findings(vpack: Path) -> dict:
    output = _read_json_or_empty(vpack / "output.json") or {}
    semantic = _semantic_findings(output)
    warning_items: list[str] = []
    for key in ("warnings", "advisory_issues", "soft_failures"):
        for item in _listify(output.get(key)):
            _add_distinct_finding(warning_items, str(item))
    for item in semantic["semantic_warning_findings"]:
        _add_distinct_finding(warning_items, str(item))
    hard_failure_count = _issue_count(
        output,
        count_keys=("blocking_issues_count", "hard_failures_count", "errors_count"),
        list_keys=("blocking_issues", "hard_failures", "errors"),
    ) + len(semantic["failure_findings"])
    warning_count = _count_key_total(
        output,
        count_keys=("advisory_issues_count", "warning_count", "warnings_count"),
    ) + len(warning_items)
    return {
        "hard_failure_count": hard_failure_count,
        "warning_count": warning_count,
        "semantic_overall": semantic["semantic_overall"],
        "semantic_failure_count": semantic["semantic_failure_count"],
        "semantic_warning_count": semantic["semantic_warning_count"],
        "failure_findings": semantic["failure_findings"],
        "warning_findings": warning_items[:20],
    }


_VERIFIER_OUTPUT_NORMALIZATION = {"pass": "passed", "fail": "failed", "warn": "warn"}


def _read_verifier_overall(vpack: Path) -> str:
    """Normalize a verifier's semantic ``overall`` to pack vocabulary (passed/warn/failed).

    Falls back to the pack-level validation_summary when the verifier did not
    emit a semantic verdict.
    """
    data = _read_json_or_empty(vpack / "output.json") or {}
    normalized = _VERIFIER_OUTPUT_NORMALIZATION.get(data.get("overall"))
    if normalized is not None:
        return normalized
    return _read_pack_overall(vpack)


def _run_pack(target_dir: Path, fixture: Path, out: Path) -> int:
    """Spawn `eval_engine.run` on a skill or verifier directory."""
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "eval_engine" / "run.py"),
            str(target_dir),
            "--fixture",
            str(fixture),
            "--out",
            str(out),
        ],
        cwd=REPO_ROOT,
    )
    return proc.returncode


VERIFIER_ENV_SKIP = "skipped (env_unavailable)"
VERIFIER_PASS_STATES = ("passed", VERIFIER_ENV_SKIP, "warn")


def _verdict(skill_overall: str, verifier_results: list[dict], gaps: list[dict]) -> str:
    if skill_overall != "passed":
        return "failed"
    if any(v["overall"] not in VERIFIER_PASS_STATES for v in verifier_results):
        return "failed"
    env_skipped = any(v["overall"] == VERIFIER_ENV_SKIP for v in verifier_results)
    if gaps or env_skipped:
        return "gap"
    if any(v["overall"] == "warn" for v in verifier_results):
        return "warn"
    if not verifier_results:
        return "no_verifiers"
    return "passed"


@app.command()
def main(
    skill_dir: Path = typer.Argument(..., exists=True, file_okay=False),
    fixture: Path = typer.Option(..., "--fixture"),
    out: Path = typer.Option(..., "--out", help="trusted-run output directory"),
) -> None:
    fixture_arg = fixture
    skill_dir = skill_dir.resolve()
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    skill = _load_skill(skill_dir)
    manifest = skill["manifest"]
    first_input = (manifest.get("inputs") or [{}])[0]
    input_formats = set(first_input.get("formats", []) or [])
    if "default_sentinel" in input_formats and str(fixture_arg) == "default":
        fixture = fixture_arg
    else:
        fixture = fixture_arg.expanduser().resolve()
    skill_id = manifest.get("id", skill_dir.name)
    skill_version = manifest.get("version")

    typer.echo(f"trusted-run: {skill_id} -> {out}")

    skill_pack = out / SKILL_RUN_SUBDIR
    typer.echo(f"  [1/2] running skill into {skill_pack.relative_to(out)}/")
    skill_rc = _run_pack(skill_dir, fixture, skill_pack)
    skill_overall = _read_pack_overall(skill_pack)

    paired = manifest.get("paired_verifiers") or []
    implemented = [v for v in paired if v.get("status") == "implemented"]
    planned = [v for v in paired if v.get("status") != "implemented"]

    verifiers_root = out / "verifiers"
    if implemented:
        verifiers_root.mkdir(exist_ok=True)

    verifier_results: list[dict] = []
    gaps: list[dict] = []
    evidence_packs: list[dict] = [
        _pack_record(
            role="skill",
            pack_id=skill_id,
            pack=SKILL_RUN_SUBDIR,
            pack_dir=skill_pack,
            overall=skill_overall,
            exit_code=skill_rc,
        )
    ]

    typer.echo(f"  [2/2] running {len(implemented)} implemented verifier(s)")
    for entry in implemented:
        vid = entry.get("id")
        vdir = _resolve_verifier_dir(vid) if vid else None
        if vdir is None:
            gaps.append({
                "id": vid,
                "declared_status": "implemented",
                "reason": "verifier directory could not be resolved from id",
            })
            continue
        short = vdir.name
        vpack = verifiers_root / short
        vrc = _run_pack(vdir, skill_pack, vpack)
        voverall = _read_verifier_overall(vpack)
        findings = _verifier_findings(vpack)
        verifier_results.append({
            "id": vid,
            "declared_status": "implemented",
            "pack": str(vpack.relative_to(out)),
            "exit_code": vrc,
            "overall": voverall,
            "checks": entry.get("checks") or [],
            "hashes": _pack_hashes(vpack),
            **findings,
        })
        evidence_packs.append(
            _pack_record(
                role="verifier",
                pack_id=vid,
                pack=str(vpack.relative_to(out)),
                pack_dir=vpack,
                overall=voverall,
                exit_code=vrc,
            )
        )
        if voverall == VERIFIER_ENV_SKIP:
            gaps.append({
                "id": vid,
                "declared_status": "implemented",
                "reason": "verifier skipped because its declared environment was unavailable",
                "checks": entry.get("checks") or [],
            })

    for entry in planned:
        gaps.append({
            "id": entry.get("id"),
            "declared_status": entry.get("status", "planned"),
            "reason": entry.get("notes") or "verifier declared but not yet implemented",
            "checks": entry.get("checks") or [],
        })

    verdict = _verdict(skill_overall, verifier_results, gaps)
    planned_verifier_gaps = [
        g for g in gaps if g.get("declared_status") != "implemented"
    ]
    env_skipped_verifier_gaps = [
        g for g in gaps
        if g.get("declared_status") == "implemented"
        and "environment" in str(g.get("reason", "")).lower()
    ]
    warning_findings = [
        {
            "id": v["id"],
            "pack": v["pack"],
            "warning_count": v.get("warning_count", 0),
            "warnings": v.get("warning_findings", []),
        }
        for v in verifier_results
        if v.get("overall") == "warn" or v.get("warning_count", 0) > 0
    ]
    trust_summary = {
        "pack_format_version": PACK_FORMAT_VERSION,
        "trust_format_version": TRUST_FORMAT_VERSION,
        "run_id": uuid4().hex[:12],
        "produced_at": _now_iso(),
        "skill_id": skill_id,
        "skill_version": skill_version,
        "skill_pack": SKILL_RUN_SUBDIR,
        "skill_overall": skill_overall,
        "skill_exit_code": skill_rc,
        "verifiers": verifier_results,
        "gaps": gaps,
        "implemented_verifiers": [v["id"] for v in verifier_results],
        "planned_verifier_gaps": planned_verifier_gaps,
        "env_skipped_verifier_gaps": env_skipped_verifier_gaps,
        "warning_findings": warning_findings,
        "evidence_packs": evidence_packs,
        "overall": verdict,
    }
    (out / "trust_summary.json").write_text(json.dumps(trust_summary, indent=2))

    typer.echo("")
    typer.echo(f"skill:     {skill_overall}")
    for v in verifier_results:
        typer.echo(f"verifier:  {v['overall']} ({v['id']})")
    if gaps:
        typer.echo(f"gaps:      {len(gaps)}")
        for g in gaps:
            typer.echo(f"  - {g['id']} ({g['declared_status']}): {g['reason']}")
    typer.echo(f"overall:   {verdict}")
    typer.echo(f"summary:   {out / 'trust_summary.json'}")

    if verdict == "failed":
        raise typer.Exit(1)
    raise typer.Exit(0)


if __name__ == "__main__":
    app()
