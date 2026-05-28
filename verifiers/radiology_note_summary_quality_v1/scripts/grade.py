#!/usr/bin/env python3
"""Verify radiology_note_summarizer evidence packs."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from verifiers._shared.verifier_kit import load_pack_json, make_check, run_grader  # noqa: E402

VERIFIER_ID = "medagent.verifiers.radiology_note_summary_quality_v1"
VERIFIER_VERSION = "0.1.0"
TARGET_SKILL_IDS = {"radiology_note_summarizer"}
TARGET_SKILL_DIR = REPO_ROOT / "skills" / "radiology-note-summarizer"
EXPECTED_MODEL = "nvidia/openai/gpt-oss-20b"
EXPECTED_ENDPOINT = "https://inference-api.nvidia.com/v1"
EXPECTED_TEMPERATURE = 0.0


def _public_path(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        resolved = path.resolve()
    except (OSError, ValueError):
        return str(path)
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        home = Path.home()
        try:
            return "~/" + str(resolved.relative_to(home))
        except ValueError:
            return str(resolved)


def _resolve_repo_path(raw: Any) -> Path | None:
    if not isinstance(raw, str) or not raw:
        return None
    path = Path(raw.replace("<repo>", str(REPO_ROOT)))
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _read_fixture(manifest: dict[str, Any]) -> tuple[Path | None, dict[str, Any]]:
    fixture = manifest.get("fixture") or {}
    path = _resolve_repo_path(fixture.get("path") if isinstance(fixture, dict) else None)
    if path is None or not path.is_file():
        return path, {}
    try:
        payload = json.loads(path.read_text())
    except Exception:
        return path, {}
    return path, payload if isinstance(payload, dict) else {}


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_forbidden_patterns() -> list[dict[str, str]]:
    path = TARGET_SKILL_DIR / "validators" / "forbidden_runtime_phrases.yaml"
    try:
        payload = yaml.safe_load(path.read_text()) or []
    except Exception:
        return []
    patterns: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        pattern = item.get("pattern")
        label = item.get("label")
        if isinstance(pattern, str) and isinstance(label, str):
            patterns.append({"pattern": pattern, "label": label})
    return patterns


def _output_text(output: dict[str, Any]) -> str:
    fields = output.get("findings") or []
    parts = [str(item) for item in fields if isinstance(item, str)]
    impressions = output.get("impressions")
    if isinstance(impressions, str):
        parts.append(impressions)
    flags = output.get("flags_for_followup") or []
    parts.extend(str(item) for item in flags if isinstance(item, str))
    return "\n".join(parts)


def _forbidden_findings(output: dict[str, Any]) -> list[dict[str, str]]:
    text = _output_text(output)
    findings: list[dict[str, str]] = []
    for item in _load_forbidden_patterns():
        try:
            match = re.search(item["pattern"], text, flags=re.IGNORECASE)
        except re.error:
            findings.append({
                "label": item["label"],
                "pattern": item["pattern"],
                "match": "<invalid regex>",
            })
            continue
        if match:
            findings.append({
                "label": item["label"],
                "pattern": item["pattern"],
                "match": match.group(0),
            })
    return findings


def _contains_case_insensitive(haystack: str, needle: Any) -> bool:
    if not isinstance(needle, str) or not needle:
        return False
    return needle.lower() in haystack.lower()


def _prompt_hash(path: Path) -> str | None:
    if not path.is_file():
        return None
    return _sha256_text(path.read_text())


def grade(pack_dir: Path) -> dict[str, Any]:
    pack_dir = pack_dir.resolve()
    output_payload = load_pack_json(pack_dir, "output.json")
    validation = load_pack_json(pack_dir, "validation_summary.json")
    manifest = load_pack_json(pack_dir, "manifest.json")

    skill_id = str(manifest.get("skill_id") or "")
    output = output_payload.get("output") or {}
    runtime = output_payload.get("runtime") or {}
    fixture_path, fixture = _read_fixture(manifest)
    metadata = fixture.get("dicom_metadata") if isinstance(fixture, dict) else {}
    metadata = metadata if isinstance(metadata, dict) else {}
    study_uid = metadata.get("StudyInstanceUID")
    modality = metadata.get("Modality")
    body_part = metadata.get("BodyPartExamined")
    prose = _output_text(output)
    forbidden = _forbidden_findings(output)
    prompt_template_sha = _prompt_hash(TARGET_SKILL_DIR / "prompts" / "user_template.md")
    system_prompt_sha = _prompt_hash(TARGET_SKILL_DIR / "prompts" / "system.md")

    checks = [
        make_check("target_skill_matches", skill_id in TARGET_SKILL_IDS, f"skill_id={skill_id!r}"),
        make_check(
            "source_pack_passed",
            validation.get("overall_status") == "passed",
            f"source pack overall={validation.get('overall_status')!r}",
        ),
        make_check(
            "fixture_loaded",
            bool(metadata),
            f"fixture={_public_path(fixture_path)}",
        ),
        make_check(
            "study_uid_echoed",
            output.get("study_instance_uid") == study_uid,
            f"output={output.get('study_instance_uid')!r}, fixture={study_uid!r}",
        ),
        make_check(
            "modality_echoed_in_prose",
            _contains_case_insensitive(prose, modality),
            f"modality={modality!r}",
        ),
        make_check(
            "body_part_echoed_in_prose",
            _contains_case_insensitive(prose, body_part),
            f"body_part={body_part!r}",
        ),
        make_check(
            "findings_nonempty",
            isinstance(output.get("findings"), list) and len(output.get("findings") or []) > 0,
            f"findings={len(output.get('findings') or [])}",
        ),
        make_check(
            "impressions_nonempty",
            isinstance(output.get("impressions"), str) and output.get("impressions").strip() != "",
            "impressions must be a non-empty string",
        ),
        make_check(
            "flags_for_followup_list",
            isinstance(output.get("flags_for_followup"), list),
            "flags_for_followup must be present as a list",
        ),
        make_check(
            "model_identity_matches",
            runtime.get("model") == EXPECTED_MODEL,
            f"runtime.model={runtime.get('model')!r}",
        ),
        make_check(
            "endpoint_matches",
            runtime.get("endpoint") == EXPECTED_ENDPOINT,
            f"runtime.endpoint={runtime.get('endpoint')!r}",
        ),
        make_check(
            "temperature_matches",
            runtime.get("temperature") == EXPECTED_TEMPERATURE,
            f"runtime.temperature={runtime.get('temperature')!r}",
        ),
        make_check(
            "prompt_template_hash_matches",
            prompt_template_sha is not None
            and runtime.get("prompt_template_sha256") == prompt_template_sha,
            "runtime prompt template hash matches committed prompt",
        ),
        make_check(
            "system_prompt_hash_matches",
            system_prompt_sha is not None and runtime.get("system_prompt_sha256") == system_prompt_sha,
            "runtime system prompt hash matches committed prompt",
        ),
        make_check(
            "forbidden_phrases_absent",
            not forbidden,
            "no clinical/regulatory overreach phrases found" if not forbidden else f"matches={forbidden}",
        ),
    ]

    hard_fail = any(check["status"] == "fail" for check in checks)
    overall = "fail" if hard_fail else "pass"

    return {
        "verifier": {"id": VERIFIER_ID, "version": VERIFIER_VERSION},
        "target": {
            "evidence_pack": _public_path(pack_dir),
            "skill_id": skill_id,
            "source_overall_status": validation.get("overall_status"),
            "fixture_path": _public_path(fixture_path),
        },
        "summary_quality": {
            "verdict": overall,
            "acceptable": overall == "pass",
            "mock_mode": bool(runtime.get("mock")),
            "forbidden_finding_count": len(forbidden),
            "forbidden_findings": forbidden,
            "study_instance_uid": output.get("study_instance_uid"),
            "model": runtime.get("model"),
        },
        "checks": checks,
        "overall": overall,
    }


if __name__ == "__main__":
    run_grader(grade, sort_keys=True)
