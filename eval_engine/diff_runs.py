#!/usr/bin/env python3
"""Diff two evidence packs to surface drift between runs.

Compares: environment fingerprint, validation gate statuses, output payload
key fields, runtime profiles. Writes a `drift_report.md` to a chosen out dir.
"""
import json
import re
from pathlib import Path

import typer

app = typer.Typer(add_completion=False)


def _load(pack: Path, name: str):
    p = pack / name
    if not p.exists():
        return None
    if name.endswith(".json"):
        return json.loads(p.read_text())
    return p.read_text()


# Paths that vary across runs without semantic meaning (timing jitter, run-id, etc.)
IGNORE_PATTERNS = [
    re.compile(r"runtime\."),               # all runtime timings
    re.compile(r".*\.elapsed_seconds"),
    re.compile(r"run_id"),
    re.compile(r"started_at"),
    re.compile(r"finished_at"),
    re.compile(r"sha256"),
    re.compile(r"(^|\.)path$"),              # filesystem paths (/<home>/...)
    # DICOM SEG outputs carry a fresh SOPInstanceUID per invocation and
    # the file body embeds ContentDate/ContentTime, so the per-file
    # entries and total_bytes jitter run-to-run without telling us
    # anything about model behaviour. The file *count* is still checked
    # by sanity_checks; only suppress the noisy fields here.
    re.compile(r"^output\.dicom_seg\.files$"),
    re.compile(r"^output\.dicom_seg\.total_bytes$"),
]


def _is_ignored(path: str) -> bool:
    return any(p.search(path) for p in IGNORE_PATTERNS)


def _dotted_diff(d1: dict, d2: dict, prefix: str = ""):
    """Return list of (path, val_a, val_b) for divergent leaves; skip ignored paths."""
    diffs = []
    keys = set(d1.keys()) | set(d2.keys())
    for k in sorted(keys):
        path = f"{prefix}{k}"
        v1, v2 = d1.get(k), d2.get(k)
        if isinstance(v1, dict) and isinstance(v2, dict):
            diffs.extend(_dotted_diff(v1, v2, path + "."))
        elif v1 != v2 and not _is_ignored(path):
            diffs.append((path, v1, v2))
    return diffs


@app.command()
def main(
    pack_a: Path = typer.Argument(..., exists=True, file_okay=False),
    pack_b: Path = typer.Argument(..., exists=True, file_okay=False),
    out: Path = typer.Option(None, "--out", help="output drift_report.md path"),
    ignore_env: bool = typer.Option(False, "--ignore-env", help="Do not fail when only the environment fingerprint changed."),
) -> None:
    """Diff two evidence packs and emit drift_report.md."""
    if out is None:
        out = pack_b / "drift_report.md"
    out = out.resolve()

    man_a = _load(pack_a, "manifest.json") or {}
    man_b = _load(pack_b, "manifest.json") or {}
    val_a = _load(pack_a, "validation_summary.json") or {}
    val_b = _load(pack_b, "validation_summary.json") or {}
    out_a = _load(pack_a, "output.json") or {}
    out_b = _load(pack_b, "output.json") or {}
    env_a = (pack_a / "environment.lock").read_text() if (pack_a / "environment.lock").exists() else ""
    env_b = (pack_b / "environment.lock").read_text() if (pack_b / "environment.lock").exists() else ""

    fp_a = man_a.get("environment", {}).get("fingerprint", "")
    fp_b = man_b.get("environment", {}).get("fingerprint", "")
    env_drift = fp_a != fp_b

    # Diff env lines
    lines_a = set(env_a.strip().split("\n")) if env_a else set()
    lines_b = set(env_b.strip().split("\n")) if env_b else set()
    only_a = sorted(lines_a - lines_b)
    only_b = sorted(lines_b - lines_a)

    # Status gate diffs
    gate_diffs = []
    for k in ("preflight_status", "schema_status", "sanity_status", "runtime_status", "integrity_status", "overall_status"):
        if val_a.get(k) != val_b.get(k):
            gate_diffs.append((k, val_a.get(k), val_b.get(k)))

    # Output payload diffs
    payload_diffs = _dotted_diff(out_a, out_b) if out_a and out_b else []

    drift_detected = bool((env_drift and not ignore_env) or gate_diffs or payload_diffs)

    lines = [
        "# Drift Report",
        "",
        f"- pack A: `{pack_a}`",
        f"- pack B: `{pack_b}`",
        f"- drift detected: **{'YES' if drift_detected else 'no'}**",
        "",
        "## Environment fingerprint",
        f"- A: `{fp_a or '(missing)'}`",
        f"- B: `{fp_b or '(missing)'}`",
        f"- env_drift: **{env_drift}**",
        f"- ignore_env: **{ignore_env}**",
        "",
    ]
    if only_a or only_b:
        lines.append("### Pip freeze diff")
        lines.append("")
        if only_a:
            lines.append("Only in A (removed in B):")
            for ln in only_a[:30]:
                lines.append(f"  - {ln}")
            if len(only_a) > 30:
                lines.append(f"  ... +{len(only_a)-30} more")
        if only_b:
            lines.append("Only in B (added in B):")
            for ln in only_b[:30]:
                lines.append(f"  - {ln}")
            if len(only_b) > 30:
                lines.append(f"  ... +{len(only_b)-30} more")
        lines.append("")

    lines.append("## Validation gate status")
    if gate_diffs:
        for k, va, vb in gate_diffs:
            lines.append(f"- `{k}`: A=`{va}` -> B=`{vb}`")
    else:
        lines.append("- (no gate-status drift)")
    lines.append("")

    lines.append("## Output payload diffs")
    if payload_diffs:
        for path, va, vb in payload_diffs[:30]:
            lines.append(f"- `{path}`: `{va!r}` -> `{vb!r}`")
        if len(payload_diffs) > 30:
            lines.append(f"... +{len(payload_diffs)-30} more")
    else:
        lines.append("- (no payload drift)")

    out.write_text("\n".join(lines))
    typer.echo(f"drift report: {out}")
    typer.echo(f"  drift detected: {drift_detected}")
    typer.echo(f"  env_drift: {env_drift}, gate_diffs: {len(gate_diffs)}, payload_diffs: {len(payload_diffs)}")
    if drift_detected:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
