#!/usr/bin/env python3
"""Render a compact Markdown review packet from an evidence pack.

This is an additive maintainer view: it reads existing pack files and does not
change the evidence-pack format.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - exercised only in stripped environments.
    yaml = None


REPO_ROOT = Path(__file__).resolve().parent.parent
PACK_DESCRIPTOR = REPO_ROOT / "spec" / "evidence_pack.schema.json"
MAX_LIST_ITEMS = 12
MAX_HASH_BYTES = 50 * 1024 * 1024


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        data = json.loads(path.read_text())
    except Exception as exc:
        return None, f"unreadable: {exc}"
    if not isinstance(data, dict):
        return None, "not a JSON object"
    return data, None


def _read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not path.exists():
        return [], ["missing"]
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for idx, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except Exception as exc:
            errors.append(f"line {idx}: {exc}")
            continue
        if isinstance(data, dict):
            records.append(data)
        else:
            errors.append(f"line {idx}: not a JSON object")
    return records, errors


def _load_pack_descriptor() -> dict[str, Any]:
    data, err = _read_json(PACK_DESCRIPTOR)
    if err or data is None:
        return {}
    return data


def _load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None or not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text())
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _display_path(path: Path, *, base: Path = REPO_ROOT) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _scalar(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        if not value:
            return "[]"
        return ", ".join(_scalar(v) for v in value[:MAX_LIST_ITEMS])
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    text = str(value).replace("\n", " ")
    return text if len(text) <= 180 else text[:177] + "..."


def _md_cell(value: Any) -> str:
    return _scalar(value).replace("|", "\\|")


def _bullet(text: str) -> str:
    return f"- {text}"


def _table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    if not rows:
        return ["_None._"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_md_cell(v) for v in row) + " |")
    return lines


def _resolve_repoish_path(raw: Any, *, pack_dir: Path) -> Path | None:
    if not isinstance(raw, str) or not raw:
        return None
    value = raw
    if value.startswith("<repo>/"):
        return REPO_ROOT / value[len("<repo>/") :]
    if value == "<repo>":
        return REPO_ROOT
    if value.startswith("<"):
        return None
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    pack_relative = pack_dir / path
    if pack_relative.exists():
        return pack_relative
    return REPO_ROOT / path


def _skill_manifest_from_run(run_manifest: dict[str, Any], *, pack_dir: Path) -> dict[str, Any]:
    skill_dir = _resolve_repoish_path(run_manifest.get("skill_dir"), pack_dir=pack_dir)
    if skill_dir is None:
        return {}
    return _load_yaml(skill_dir / "skill_manifest.yaml")


def _pack_kind(root: Path, trust_summary: dict[str, Any] | None, run_manifest: dict[str, Any] | None) -> str:
    if trust_summary is not None:
        return "trusted_run"
    if run_manifest:
        return str(run_manifest.get("pack_kind") or "legacy_skill_run")
    return "unknown"


def _main_pack_dir(root: Path, trust_summary: dict[str, Any] | None) -> Path:
    if trust_summary:
        skill_pack = trust_summary.get("skill_pack") or "skill_run"
        return root / str(skill_pack)
    return root


def _expected_file_gaps(pack_dir: Path) -> tuple[list[str], list[str]]:
    descriptor = _load_pack_descriptor()
    files = descriptor.get("files") if isinstance(descriptor, dict) else {}
    missing_required: list[str] = []
    missing_optional: list[str] = []
    if not isinstance(files, dict):
        return missing_required, missing_optional
    for name, meta in sorted(files.items()):
        if name.endswith("/") or "/" in name:
            continue
        required = bool(meta.get("required")) if isinstance(meta, dict) else False
        if not (pack_dir / name).exists():
            if required:
                missing_required.append(name)
            elif name in {"provenance.json", "llm_interaction.json", "dataset_run.jsonl", "trust_summary.json"}:
                missing_optional.append(name)
    return missing_required, missing_optional


def _validation_gate_rows(summary: dict[str, Any] | None) -> list[list[Any]]:
    if not summary:
        return []
    rows: list[list[Any]] = []
    gates = [
        ("preflight", "preflight_status", None),
        ("schema", "schema_status", None),
        ("sanity", "sanity_status", "sanity_results"),
        ("runtime", "runtime_status", "runtime_reason"),
        ("cost", "cost_status", "cost_results"),
        ("env_pin", "env_pin_status", "env_pin_results"),
        ("factual_echo", "factual_echo_status", "factual_echo_results"),
        ("model_identity", "model_identity_status", "model_identity_results"),
        ("runtime_integrity", "runtime_integrity_status", "runtime_integrity_findings"),
        ("integrity", "integrity_status", "integrity_n_findings"),
        ("overall", "overall_status", "errors"),
    ]
    for name, status_key, detail_key in gates:
        if status_key not in summary:
            continue
        detail = summary.get(detail_key) if detail_key else None
        if isinstance(detail, list):
            failed = [item for item in detail if isinstance(item, dict) and item.get("ok") is False]
            reason = f"{len(failed)} failed / {len(detail)} total" if failed else f"{len(detail)} total"
        elif detail:
            reason = detail
        else:
            reason = ""
        rows.append([name, summary.get(status_key), reason])
    return rows


def _validation_failures(summary: dict[str, Any] | None) -> list[str]:
    if not summary:
        return ["validation_summary.json is missing or unreadable"]
    failures: list[str] = []
    overall = summary.get("overall_status")
    if overall not in {"passed", "warn", "warning"}:
        failures.append(f"overall_status={overall}")
    for gate, status in summary.items():
        if not gate.endswith("_status"):
            continue
        if status in {None, "passed", "within_envelope", "clean", "skipped"}:
            continue
        if status in {"warn", "warning"}:
            continue
        failures.append(f"{gate}={status}")
    if summary.get("exit_code") not in {None, 0}:
        failures.append(f"exit_code={summary.get('exit_code')}")
    return sorted(set(failures))


def _validation_warnings(summary: dict[str, Any] | None) -> list[str]:
    if not summary:
        return []
    warnings: list[str] = []
    for gate, status in summary.items():
        if gate.endswith("_status") and status in {"warn", "warning"}:
            warnings.append(f"{gate}={status}")
    return warnings


def _source_supports_verifier_claims(summary: dict[str, Any] | None) -> bool:
    return not _validation_failures(summary)


def _paired_verifier_gaps(
    *,
    trust_summary: dict[str, Any] | None,
    skill_manifest: dict[str, Any],
    validation_summary: dict[str, Any] | None,
) -> list[str]:
    if trust_summary:
        return [
            f"{gap.get('id') or 'unknown'} ({gap.get('declared_status')}): {gap.get('reason')}"
            for gap in trust_summary.get("gaps", [])
            if isinstance(gap, dict)
        ]
    if not _source_supports_verifier_claims(validation_summary):
        return []
    paired = skill_manifest.get("paired_verifiers")
    if not paired:
        return []
    gaps: list[str] = []
    for entry in paired:
        if not isinstance(entry, dict):
            continue
        verifier_id = entry.get("id") or "unknown"
        status = entry.get("status") or "unknown"
        gaps.append(f"{verifier_id} ({status}) not bundled in a trusted-run summary")
    return gaps


def _derive_verdict(
    *,
    trust_summary: dict[str, Any] | None,
    validation_summary: dict[str, Any] | None,
    missing_required: list[str],
    evidence_gaps: list[str],
    warnings: list[str],
) -> str:
    failures = _validation_failures(validation_summary)
    if trust_summary and trust_summary.get("overall") == "failed":
        return "failed"
    if failures:
        return "failed"
    if trust_summary:
        overall = trust_summary.get("overall")
        if overall in {"passed", "failed", "warn", "gap", "no_verifiers"}:
            if overall == "passed" and (missing_required or evidence_gaps):
                return "gap"
            return str(overall)
    if missing_required or evidence_gaps:
        return "gap"
    if warnings:
        return "warn"
    return "passed"


def _artifact_paths(obj: Any, *, prefix: str = "") -> list[tuple[str, str]]:
    paths: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            key_l = str(key).lower()
            if key_l.endswith("path") and isinstance(value, str):
                paths.append((next_prefix, value))
            elif key_l.endswith("paths") and isinstance(value, list):
                for idx, item in enumerate(value):
                    if isinstance(item, str):
                        paths.append((f"{next_prefix}[{idx}]", item))
            paths.extend(_artifact_paths(value, prefix=next_prefix))
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            paths.extend(_artifact_paths(item, prefix=f"{prefix}[{idx}]"))
    return paths


def _sha256_if_small(path: Path | None) -> str:
    if path is None or not path.exists() or not path.is_file():
        return "-"
    try:
        size = path.stat().st_size
    except OSError:
        return "-"
    if size > MAX_HASH_BYTES:
        return f"skipped ({size} bytes)"
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _artifact_rows_and_gaps(
    *,
    output: dict[str, Any] | None,
    run_manifest: dict[str, Any] | None,
    pack_dir: Path,
) -> tuple[list[list[Any]], list[str]]:
    rows: list[list[Any]] = []
    gaps: list[str] = []
    if run_manifest:
        fixture = run_manifest.get("fixture") or {}
        if isinstance(fixture, dict):
            fixture_path = fixture.get("path")
            actual_path = _resolve_repoish_path(fixture_path, pack_dir=pack_dir)
            actual_hash = _sha256_if_small(actual_path)
            recorded_hash = fixture.get("sha256") or "-"
            if actual_hash not in {"-", recorded_hash}:
                gaps.append(
                    "local fixture hash differs from manifest fixture hash: "
                    f"{fixture_path}"
                )
            rows.append([
                "fixture",
                fixture_path,
                recorded_hash,
                fixture.get("size_bytes") or "-",
            ])
    if output:
        seen: set[tuple[str, str]] = set()
        for dotted_path, raw_path in _artifact_paths(output):
            key = (dotted_path, raw_path)
            if key in seen:
                continue
            seen.add(key)
            local = _resolve_repoish_path(raw_path, pack_dir=pack_dir)
            size = local.stat().st_size if local and local.exists() and local.is_file() else "-"
            rows.append([dotted_path, raw_path, _sha256_if_small(local), size])
            if len(rows) >= MAX_LIST_ITEMS:
                break
    return rows, gaps


def _trace_digest(trace_records: list[dict[str, Any]], trace_errors: list[str]) -> list[str]:
    if not trace_records and trace_errors:
        return [_bullet(f"Trace unavailable: {', '.join(trace_errors)}")]
    if not trace_records:
        return [_bullet("Trace has no records.")]
    event_counts = Counter(
        str(r.get("kind") or r.get("event_type") or r.get("type") or "unknown")
        for r in trace_records
    )
    tools = sorted(
        {
            str(r.get("tool"))
            for r in trace_records
            if r.get("tool")
        }
    )
    models = sorted(
        {
            str(r.get("model") or r.get("model_name"))
            for r in trace_records
            if r.get("model") or r.get("model_name")
        }
    )
    commands = [
        r.get("command")
        for r in trace_records
        if r.get("command")
    ][:MAX_LIST_ITEMS]
    files_read = sorted({str(v) for r in trace_records for v in _as_list(r.get("files_read"))})
    files_written = sorted({str(v) for r in trace_records for v in _as_list(r.get("files_written"))})
    approvals = [r for r in trace_records if r.get("approval_required") or r.get("approval_result")]

    lines = [
        _bullet(f"Records: `{len(trace_records)}`"),
        _bullet("Events: " + ", ".join(f"`{k}`={v}" for k, v in event_counts.items())),
    ]
    if tools:
        lines.append(_bullet("Tools: " + ", ".join(f"`{t}`" for t in tools[:MAX_LIST_ITEMS])))
    if models:
        lines.append(_bullet("Models: " + ", ".join(f"`{m}`" for m in models[:MAX_LIST_ITEMS])))
    if commands:
        lines.append(_bullet("Commands: " + "; ".join(_scalar(c) for c in commands)))
    if files_read:
        lines.append(_bullet("Files read: " + ", ".join(f"`{p}`" for p in files_read[:MAX_LIST_ITEMS])))
    if files_written:
        lines.append(_bullet("Files written: " + ", ".join(f"`{p}`" for p in files_written[:MAX_LIST_ITEMS])))
    if approvals:
        lines.append(_bullet(f"Approval events: `{len(approvals)}`"))
    if trace_errors:
        lines.append(_bullet("Trace parse gaps: " + "; ".join(trace_errors[:MAX_LIST_ITEMS])))
    return lines


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _provenance_lines(provenance: dict[str, Any] | None) -> tuple[list[str], list[str]]:
    if provenance is None:
        return ([_bullet("`provenance.json` is missing.")], ["provenance.json missing"])

    gaps: list[str] = []
    gpu = provenance.get("gpu") or {}
    container = provenance.get("container") or {}
    network = provenance.get("network") or {}
    side_effects = provenance.get("side_effects") or {}

    gpu_names = [g.get("name") or g.get("uuid") for g in gpu.get("gpus", []) if isinstance(g, dict)]
    lines = [
        _bullet(f"Captured at: `{provenance.get('captured_at', '-')}`"),
        _bullet(
            "GPU: "
            + (
                ", ".join(str(x) for x in gpu_names)
                if gpu_names
                else f"available={_scalar(gpu.get('available'))}, nvidia-smi={_scalar(gpu.get('have_nvidia_smi'))}, nvcc={_scalar(gpu.get('have_nvcc'))}"
            )
        ),
        _bullet(f"Container requires Docker: `{_scalar(container.get('requires_docker'))}`; digest: `{_scalar(container.get('image_digest_observed'))}`"),
        _bullet(
            "Network declared: "
            + (
                ", ".join(f"`{x}`" for x in network.get("declared_endpoints", []))
                if network.get("declared_endpoints")
                else "`none`"
            )
        ),
        _bullet(f"Side-effect findings: `{len(side_effects.get('findings') or [])}`"),
    ]
    if container.get("requires_docker") and not container.get("image_digest_observed"):
        gaps.append("container image digest not observed")
    if network.get("declared_endpoints") and network.get("observed_endpoints") is None:
        gaps.append("network observation not implemented")
    findings = side_effects.get("findings") or []
    for finding in findings[:MAX_LIST_ITEMS]:
        if isinstance(finding, dict):
            lines.append(_bullet("Side effect: " + _scalar(finding)))
    return lines, gaps


def _verifier_issue_summary(
    output: dict[str, Any] | None,
    verifier: dict[str, Any] | None = None,
) -> str:
    verifier = verifier or {}
    chunks: list[str] = []
    for key in ("hard_failure_count", "warning_count"):
        if key in verifier:
            chunks.append(f"{key}={verifier[key]}")
    for key in ("semantic_failure_count", "semantic_warning_count"):
        if verifier.get(key):
            chunks.append(f"{key}={verifier[key]}")
    verifier_semantic_overall = verifier.get("semantic_overall")
    if verifier_semantic_overall and verifier_semantic_overall not in {"pass", "passed"}:
        chunks.append(f"semantic_overall={verifier['semantic_overall']}")
    failure_findings = verifier.get("failure_findings")
    if isinstance(failure_findings, list) and failure_findings:
        chunks.append(f"failure_findings={len(failure_findings)}")
    warning_findings = verifier.get("warning_findings")
    if isinstance(warning_findings, list) and warning_findings:
        chunks.append(f"warning_findings={len(warning_findings)}")
    if not output:
        return "; ".join(chunks) if chunks else "-"
    for key in ("blocking_issues_count", "advisory_issues_count"):
        if key in output:
            chunks.append(f"{key}={output[key]}")
    for block_name, block in output.items():
        if not isinstance(block, dict) or not block.get("verdict"):
            continue
        if block_name == "domain_floor" or block_name.endswith("_metrics"):
            chunks.append(f"{block_name}={block.get('verdict')}")
    inventory = output.get("artifact_inventory")
    if isinstance(inventory, dict):
        for key in sorted(inventory):
            if key.endswith("_count") and isinstance(inventory[key], (int, float, str)):
                chunks.append(f"{key}={inventory[key]}")
    for key in ("findings", "warnings", "errors", "hard_failures", "soft_failures"):
        value = output.get(key)
        if isinstance(value, list):
            chunks.append(f"{key}={len(value)}")
    if (
        "overall" in output
        and output["overall"] not in {"pass", "passed"}
        and output["overall"] != verifier_semantic_overall
    ):
        chunks.append(f"semantic_overall={output['overall']}")
    return "; ".join(chunks) if chunks else "-"


def _hash_digest(hashes: dict[str, Any]) -> str:
    if not isinstance(hashes, dict) or not hashes:
        return "-"
    parts = []
    for name in sorted(hashes)[:MAX_LIST_ITEMS]:
        value = str(hashes[name])
        parts.append(f"{name}={value[:12]}")
    return ", ".join(parts)


def _trust_evidence_rows(trust_summary: dict[str, Any] | None) -> list[list[Any]]:
    if not trust_summary:
        return []
    rows: list[list[Any]] = []
    for pack in trust_summary.get("evidence_packs") or []:
        if not isinstance(pack, dict):
            continue
        rows.append([
            pack.get("role"),
            pack.get("id"),
            pack.get("pack"),
            pack.get("overall"),
            _hash_digest(pack.get("hashes") or {}),
        ])
    return rows


def _verifier_rows(root: Path, trust_summary: dict[str, Any] | None) -> tuple[list[list[Any]], list[str]]:
    if not trust_summary:
        return [], []
    rows: list[list[Any]] = []
    gaps: list[str] = []
    for verifier in trust_summary.get("verifiers", []):
        if not isinstance(verifier, dict):
            continue
        pack_rel = verifier.get("pack")
        vpack = root / str(pack_rel) if pack_rel else None
        vval, _ = _read_json(vpack / "validation_summary.json") if vpack else (None, "missing")
        vout, _ = _read_json(vpack / "output.json") if vpack else (None, "missing")
        rows.append([
            verifier.get("id"),
            verifier.get("overall"),
            verifier.get("declared_status"),
            pack_rel,
            _scalar(vval.get("overall_status") if vval else "-"),
            _verifier_issue_summary(vout, verifier),
        ])
    for gap in trust_summary.get("gaps", []):
        if isinstance(gap, dict):
            gaps.append(f"{gap.get('id') or 'unknown'} ({gap.get('declared_status')}): {gap.get('reason')}")
    return rows, gaps


def _reviewer_checklist(
    *,
    verdict: str,
    failures: list[str],
    evidence_gaps: list[str],
    provenance_gaps: list[str],
    trust_summary: dict[str, Any] | None,
    paired_verifier_obligations: bool,
) -> list[str]:
    items: list[str] = []
    if failures:
        items.append("Confirm each failing gate is expected for this pack, or regenerate/fix the skill before citing it.")
    else:
        items.append("Confirm the gate table matches the claim being reviewed.")
    if evidence_gaps:
        items.append("Resolve evidence gaps before treating this as a fully trusted run.")
    if trust_summary is None and paired_verifier_obligations:
        items.append("Use `make run-trusted` when paired verifier coverage is required.")
    elif trust_summary is None:
        items.append("No trusted-run summary is present; inspect the single-pack evidence directly.")
    else:
        items.append("Open verifier packs only for any failed, warning, skipped, or gap rows above.")
    if provenance_gaps:
        items.append("Inspect upstream logs or rerun with stronger instrumentation for provenance gaps.")
    if verdict == "passed":
        items.append("Check limitations before promoting this pack as reference evidence.")
    return [_bullet(item) for item in items]


def _limitations(skill_manifest: dict[str, Any]) -> list[str]:
    limitations = skill_manifest.get("limitations")
    if isinstance(limitations, list) and limitations:
        return [_bullet(_scalar(item)) for item in limitations[:MAX_LIST_ITEMS]]
    return [_bullet("No limitations found in the current skill manifest, or manifest unavailable.")]


def render_review_packet(pack_dir: Path | str) -> str:
    root = Path(pack_dir).resolve()
    trust_summary, trust_err = _read_json(root / "trust_summary.json")
    if trust_err:
        trust_summary = None
    main_pack = _main_pack_dir(root, trust_summary)

    run_manifest, manifest_err = _read_json(main_pack / "manifest.json")
    validation_summary, validation_err = _read_json(main_pack / "validation_summary.json")
    output, _ = _read_json(main_pack / "output.json")
    runtime_profile, _ = _read_json(main_pack / "runtime_profile.json")
    cost_profile, _ = _read_json(main_pack / "cost_profile.json")
    integrity, _ = _read_json(main_pack / "integrity_check.json")
    provenance, _ = _read_json(main_pack / "provenance.json")
    trace_records, trace_errors = _read_jsonl(main_pack / "agent_run_trace.jsonl")

    run_manifest = run_manifest or {}
    validation_summary = validation_summary or {}
    skill_manifest = _skill_manifest_from_run(run_manifest, pack_dir=main_pack)
    missing_required, missing_optional = _expected_file_gaps(main_pack)
    evidence_gaps: list[str] = []
    if manifest_err:
        evidence_gaps.append(f"manifest.json {manifest_err}")
    if validation_err:
        evidence_gaps.append(f"validation_summary.json {validation_err}")
    if missing_required:
        evidence_gaps.append("missing required pack files: " + ", ".join(missing_required))
    if "provenance.json" in missing_optional and validation_summary.get("overall_status") == "passed":
        evidence_gaps.append("provenance.json missing from passed pack")
    if not skill_manifest and run_manifest.get("skill_dir"):
        evidence_gaps.append("current skill_manifest.yaml could not be read; verifier obligations and limitations may be stale")
    source_supports_verifier_claims = _source_supports_verifier_claims(validation_summary)
    paired_verifier_obligations = (
        bool(skill_manifest.get("paired_verifiers")) and source_supports_verifier_claims
        if skill_manifest
        else False
    )
    artifact_rows, artifact_gaps = _artifact_rows_and_gaps(
        output=output,
        run_manifest=run_manifest,
        pack_dir=main_pack,
    )
    evidence_gaps.extend(artifact_gaps)

    warnings = _validation_warnings(validation_summary)
    failures = _validation_failures(validation_summary)
    provenance_lines, provenance_gaps = _provenance_lines(provenance)
    evidence_gaps.extend(
        _paired_verifier_gaps(
            trust_summary=trust_summary,
            skill_manifest=skill_manifest,
            validation_summary=validation_summary,
        )
    )
    verdict = _derive_verdict(
        trust_summary=trust_summary,
        validation_summary=validation_summary,
        missing_required=missing_required,
        evidence_gaps=evidence_gaps,
        warnings=warnings,
    )
    verifier_rows, trust_gaps = _verifier_rows(root, trust_summary)

    lines: list[str] = []
    lines.append(f"# Review Packet: {root.name}")
    lines.append("")
    lines.append("## Review Verdict")
    lines.append(_bullet(f"Review verdict: `{verdict}`"))
    lines.append(_bullet(f"Pack kind: `{_pack_kind(root, trust_summary, run_manifest)}`"))
    lines.append(_bullet(f"Gate overall: `{validation_summary.get('overall_status', 'unknown')}`"))
    if trust_summary:
        lines.append(_bullet(f"Trust overall: `{trust_summary.get('overall')}`"))
    if failures:
        lines.append(_bullet("Hard failures: " + "; ".join(f"`{f}`" for f in failures[:MAX_LIST_ITEMS])))
    if warnings:
        lines.append(_bullet("Warnings: " + "; ".join(f"`{w}`" for w in warnings[:MAX_LIST_ITEMS])))
    if evidence_gaps or trust_gaps:
        all_gaps = evidence_gaps + trust_gaps
        lines.append(_bullet("Evidence gaps: " + "; ".join(_scalar(g) for g in all_gaps[:MAX_LIST_ITEMS])))
    lines.append("")

    lines.append("## Capability And Invocation")
    invocation_rows = [
        ["skill_id", run_manifest.get("skill_id") or trust_summary.get("skill_id") if trust_summary else run_manifest.get("skill_id")],
        ["skill_version", run_manifest.get("skill_version") or (trust_summary.get("skill_version") if trust_summary else None)],
        ["pack_dir", _display_path(main_pack)],
        ["run_id", run_manifest.get("run_id")],
        ["repo_git_sha", run_manifest.get("repo_git_sha")],
        ["fixture", (run_manifest.get("fixture") or {}).get("path") if isinstance(run_manifest.get("fixture"), dict) else "-"],
        ["command", " ".join(str(x) for x in run_manifest.get("command", []))],
        ["replay", _display_path(main_pack / "replay.sh") if (main_pack / "replay.sh").exists() else "-"],
    ]
    if runtime_profile:
        invocation_rows.extend([
            ["elapsed_seconds", runtime_profile.get("elapsed_seconds")],
            ["runtime_exit_code", runtime_profile.get("exit_code")],
        ])
    if cost_profile:
        measured = cost_profile.get("measured") if isinstance(cost_profile.get("measured"), dict) else {}
        for key in ("wall_seconds", "cpu_seconds", "rss_mb_peak", "gpu_seconds", "gpu_memory_mb_peak"):
            if key in measured:
                invocation_rows.append([f"cost.{key}", measured.get(key)])
    lines.extend(_table(["Field", "Value"], invocation_rows))
    lines.append("")

    lines.append("## Gate Table")
    lines.extend(_table(["Gate", "Status", "Reason"], _validation_gate_rows(validation_summary)))
    if integrity and integrity.get("findings"):
        lines.append("")
        lines.append("Integrity findings:")
        for finding in integrity.get("findings", [])[:MAX_LIST_ITEMS]:
            lines.append(_bullet(_scalar(finding)))
    lines.append("")

    lines.append("## Verifier Findings")
    if verifier_rows:
        lines.extend(_table(["Verifier", "Overall", "Declared", "Pack", "Pack Gate", "Findings"], verifier_rows))
    elif trust_summary:
        lines.append("_No verifier packs were recorded._")
    else:
        paired = skill_manifest.get("paired_verifiers") if skill_manifest else None
        if paired:
            if not source_supports_verifier_claims:
                lines.append(
                    "_Verifier coverage skipped because the source pack did not pass._"
                )
                lines.append("")
            rows = [
                [entry.get("id"), entry.get("status"), entry.get("consumes"), entry.get("purpose")]
                for entry in paired
                if isinstance(entry, dict)
            ]
            lines.extend(_table(["Declared Verifier", "Status", "Consumes", "Purpose"], rows))
        else:
            lines.append("_No paired verifiers declared in the current manifest, or manifest unavailable._")
    if trust_gaps:
        lines.append("")
        lines.append("Verifier gaps:")
        for gap in trust_gaps[:MAX_LIST_ITEMS]:
            lines.append(_bullet(gap))
    lines.append("")

    if trust_summary:
        lines.append("## Trust Evidence")
        lines.extend(_table(["Role", "ID", "Pack", "Overall", "Hashes"], _trust_evidence_rows(trust_summary)))
        warning_findings = trust_summary.get("warning_findings") or []
        if warning_findings:
            lines.append("")
            lines.append("Warning findings:")
            for finding in warning_findings[:MAX_LIST_ITEMS]:
                lines.append(_bullet(_scalar(finding)))
        lines.append("")

    lines.append("## Provenance Deltas")
    lines.extend(provenance_lines)
    if provenance_gaps:
        lines.append("")
        lines.append("Provenance gaps:")
        for gap in provenance_gaps[:MAX_LIST_ITEMS]:
            lines.append(_bullet(gap))
    lines.append("")

    lines.append("## Trace Digest")
    lines.extend(_trace_digest(trace_records, trace_errors))
    lines.append("")

    lines.append("## Artifacts")
    lines.extend(_table(["Source", "Path", "SHA256", "Size bytes"], artifact_rows))
    lines.append("")

    lines.append("## Reviewer Checklist")
    lines.extend(
        _reviewer_checklist(
            verdict=verdict,
            failures=failures,
            evidence_gaps=evidence_gaps + trust_gaps,
            provenance_gaps=provenance_gaps,
            trust_summary=trust_summary,
            paired_verifier_obligations=paired_verifier_obligations,
        )
    )
    lines.append("")

    lines.append("## Known Limitations")
    lines.extend(_limitations(skill_manifest))
    lines.append("")
    return "\n".join(lines)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pack", type=Path, help="Evidence pack or trusted-run directory")
    parser.add_argument("--out", type=Path, help="Write Markdown to this path instead of stdout")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    if not args.pack.exists():
        print(f"error: pack does not exist: {args.pack}", file=sys.stderr)
        return 2
    markdown = render_review_packet(args.pack)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(markdown)
    else:
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
