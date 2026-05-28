#!/usr/bin/env python3
"""radiology_note_summarizer — reference LLM-using skill.

Reads a JSON fixture {dicom_metadata, radiologist_note}, calls a
NIM-hosted LLM at inference-api.nvidia.com via the OpenAI-compatible
chat-completions API, and emits structured JSON on stdout. The eval_engine
audits the output against skill_manifest.yaml.

Env vars:
  NV_INFER_TOKEN   API key variable for a real NVIDIA NIM call.
  MOCK_LLM         if "1", skips the network call and returns a
                   deterministic canned response derived from the input.

Output shape: see validators/output_schema.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SYSTEM_PROMPT_PATH = SKILL_DIR / "prompts" / "system.md"
USER_TEMPLATE_PATH = SKILL_DIR / "prompts" / "user_template.md"

# Defaults match what skill_manifest.yaml declares as the spec.
# LLM_MODEL / LLM_ENDPOINT / LLM_TEMPERATURE env-vars override these so the
# same skill can be probed against multiple inference.nvidia.com backends
# without forking. The model_identity gate then catches any swap that was
# not accompanied by a manifest update — which is the entire point.
ENDPOINT = os.environ.get("LLM_ENDPOINT", "https://inference-api.nvidia.com/v1")
MODEL = os.environ.get("LLM_MODEL", "nvidia/openai/gpt-oss-20b")
TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.0"))
TOP_P = 1.0
MAX_TOKENS = int("1024")
SEED = int("42")
TIMEOUT_SECONDS = int("60")


def _err(msg: str) -> None:
    sys.stderr.write(msg + "\n")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_fixture(path: Path) -> dict:
    if not path.is_file():
        _err(f"fixture not found: {path}")
        sys.exit(2)
    try:
        data = json.loads(path.read_text())
    except Exception as e:
        _err(f"fixture is not valid JSON ({path}): {e}")
        sys.exit(2)
    if not isinstance(data, dict) or "dicom_metadata" not in data or "radiologist_note" not in data:
        _err("fixture must be a JSON object with 'dicom_metadata' and 'radiologist_note' keys")
        sys.exit(2)
    # `segmentation_summary` is optional. When present (e.g. when this skill
    # is run as the third step of a workflow that fed VISTA3D output into the
    # composed fixture), it is interpolated into the LLM prompt verbatim.
    return data


def _build_messages(fixture: dict, system_prompt: str, user_template: str) -> list[dict]:
    seg = fixture.get("segmentation_summary")
    if seg:
        seg_block = (
            "Segmentation summary (from prior workflow step):\n"
            + json.dumps(seg, indent=2)
            + "\n\n"
        )
    else:
        seg_block = ""
    user_filled = (
        user_template
        .replace("{dicom_metadata_json}", json.dumps(fixture["dicom_metadata"], indent=2))
        .replace("{segmentation_summary_block}", seg_block)
        .replace("{radiologist_note}", fixture["radiologist_note"])
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_filled},
    ]


def _call_nim(api_key: str, messages: list[dict]) -> dict:
    body = {
        "model": MODEL,
        "messages": messages,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "max_tokens": MAX_TOKENS,
        "seed": SEED,
    }
    req = urllib.request.Request(
        ENDPOINT.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_excerpt = e.read()[:int("500")].decode("utf-8", errors="replace")
        _err(f"NIM HTTP {e.code} {e.reason}: {body_excerpt}")
        sys.exit(2)
    except urllib.error.URLError as e:
        _err(f"NIM network error: {e.reason}")
        sys.exit(2)


def _parse_model_json(text: str) -> dict:
    # The model is instructed to return JSON only. Strip code fences if it
    # disobeys, then parse strictly.
    s = text.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        _err(f"model did not return parseable JSON: {e}\n--- model output (first 500 chars) ---\n{text[:int("500")]}")
        sys.exit(2)


def _normalize_model_output(output: dict) -> dict:
    """Coerce common LLM shape drift back to the published schema."""
    if not isinstance(output, dict):
        return output

    normalized = dict(output)

    findings = normalized.get("findings")
    if isinstance(findings, str):
        normalized["findings"] = [findings]
    elif isinstance(findings, list):
        normalized["findings"] = [
            item if isinstance(item, str) else json.dumps(item, sort_keys=True)
            for item in findings
        ]

    impressions = normalized.get("impressions")
    if isinstance(impressions, list):
        normalized["impressions"] = " ".join(str(item) for item in impressions)

    flags = normalized.get("flags_for_followup")
    if flags is None and "flags_for_followup" in normalized:
        normalized["flags_for_followup"] = []
    elif isinstance(flags, str):
        normalized["flags_for_followup"] = [flags]
    elif isinstance(flags, list):
        normalized["flags_for_followup"] = [
            item if isinstance(item, str) else json.dumps(item, sort_keys=True)
            for item in flags
        ]

    return normalized


def _mock_response(fixture: dict, mode: str = "pass") -> dict:
    """Deterministic canned response. Used when MOCK_LLM is set.

    `mode` selects a fault-injection variant so Medical AI Skills can prove
    each output-side gate actually fires:

      pass                  → response that passes every manifest gate
      fail_factual_echo     → drop Modality / BodyPart from prose so the
                              factual_echo gate fails
      fail_runtime_integrity→ emit a forbidden clinical phrase so the
                              runtime_integrity gate flags
      fail_sanity           → empty findings list so the sanity gate fails
      fail_schema           → omit a required field so the schema gate fails

    `fail_model_identity` is handled outside this function: it tampers
    with `runtime.model` after the response is built.

    The pass-mode response was historically tuned to make every gate green
    on the committed fixtures. That makes MOCK_LLM=1 a tautology unless
    the negative modes are exercised alongside it. See SKILL.md.
    """
    md = fixture["dicom_metadata"]
    note = fixture["radiologist_note"]
    modality = md.get("Modality", "")
    body_part = md.get("BodyPartExamined", "")
    findings = [
        f"{modality.upper()} of the {body_part.lower()} performed with contrast",
        "mild hepatic steatosis noted",
        "small simple right renal cyst, approximately 1.5 cm, likely incidental",
        "no acute findings",
    ]
    impressions = (
        f"{modality.upper()} {body_part.lower()}: mild hepatic steatosis and "
        f"a small incidental right renal cyst. No acute process."
    )
    flags = []
    if "follow up" in note.lower() or "follow-up" in note.lower():
        flags.append("clinical follow-up if symptoms persist")

    if mode == "fail_factual_echo":
        # Strip Modality and BodyPartExamined references entirely. The
        # factual_echo gate (any_contains, case_insensitive) should fail.
        findings = [
            "imaging study performed",
            "mild hepatic steatosis noted",
            "small simple right renal cyst, approximately 1.5 cm, likely incidental",
            "no acute findings",
        ]
        impressions = (
            "study reviewed: mild hepatic steatosis and a small incidental "
            "right renal cyst. No acute process."
        )
    elif mode == "fail_runtime_integrity":
        # Emit a phrase from validators/forbidden_runtime_phrases.yaml.
        impressions = (
            f"{modality.upper()} {body_part.lower()}: imaging supports a "
            f"diagnosis of hepatic steatosis. Patient should follow up."
        )
    elif mode == "fail_sanity":
        # Empty findings array trips length_gte:1.
        findings = []
    elif mode == "fail_schema":
        # Return an object missing the required `study_instance_uid` field.
        return {
            "findings": findings,
            "impressions": impressions,
            "flags_for_followup": flags,
        }

    return {
        "study_instance_uid": md.get("StudyInstanceUID", ""),
        "findings": findings,
        "impressions": impressions,
        "flags_for_followup": flags,
    }


def main() -> int:
    if len(sys.argv) < 2:
        _err("usage: summarize.py <fixture.json>")
        return 2
    fixture_path = Path(sys.argv[1]).resolve()
    fixture = _load_fixture(fixture_path)

    system_prompt = SYSTEM_PROMPT_PATH.read_text()
    user_template = USER_TEMPLATE_PATH.read_text()
    sys_hash = _sha256_text(system_prompt)
    tpl_hash = _sha256_text(user_template)

    mock_raw = os.environ.get("MOCK_LLM", "")
    mock = mock_raw != ""
    # MOCK_LLM=1 and MOCK_LLM=pass both select the gate-passing mock.
    # MOCK_LLM=fail_<gate> selects a fault-injection variant for proving
    # each spec gate fires (see _mock_response and SKILL.md).
    mock_mode = "pass" if mock_raw in ("", "1", "pass") else mock_raw
    valid_modes = {"pass", "fail_factual_echo", "fail_runtime_integrity",
                   "fail_sanity", "fail_schema", "fail_model_identity"}
    if mock and mock_mode not in valid_modes:
        _err(f"MOCK_LLM={mock_raw!r} not recognised; expected one of {sorted(valid_modes)} or '1'.")
        return 2
    api_key = os.environ.get("NV_INFER_TOKEN", "")
    if not mock and not api_key:
        _err("NV_INFER_TOKEN is not set. Export it (see SKILL.md) or run with MOCK_LLM=1 for a dry run.")
        return 2

    t0 = time.perf_counter()
    served_model: str | None = None
    system_fingerprint: str | None = None
    if mock:
        model_output = _mock_response(fixture, mode=mock_mode)
        request_id = "mock-" + _sha256_text(json.dumps(fixture, sort_keys=True))[:int("12")]
        prompt_tokens = sum(len(m["content"]) for m in _build_messages(fixture, system_prompt, user_template)) // int("4")
        completion_tokens = len(json.dumps(model_output)) // int("4")
        # In mock mode, served == requested — there is no server.
        # `fail_model_identity` overrides this so the model_identity gate
        # sees a runtime.model that does not match the manifest spec.
        if mock_mode == "fail_model_identity":
            served_model = "nvidia/some-other-model"
        else:
            served_model = MODEL
    else:
        messages = _build_messages(fixture, system_prompt, user_template)
        resp = _call_nim(api_key, messages)
        try:
            content = resp["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            _err(f"unexpected NIM response shape: {json.dumps(resp)[:int("500")]}")
            return 2
        model_output = _normalize_model_output(_parse_model_json(content))
        usage = resp.get("usage", {}) or {}
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
        request_id = str(resp.get("id", ""))
        # OpenAI-compatible servers return `model` set to whatever the
        # backend actually served — that is the load-bearing identity for
        # the model_identity gate. The client's request body is only
        # intent; the response is fact. system_fingerprint is the
        # sub-version field (OpenAI uses it; NVIDIA does not yet expose it,
        # so it is captured as None here for forward compatibility).
        served_model = resp.get("model")
        system_fingerprint = resp.get("system_fingerprint")
    elapsed = time.perf_counter() - t0

    runtime_block = {
        # Server-reported model is what the model_identity gate compares
        # against the manifest spec. Falls back to the requested model
        # only if the server did not return a `model` field.
        "model": served_model or MODEL,
        "requested_model": MODEL,
        "system_fingerprint": system_fingerprint,
        "endpoint": ENDPOINT,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "seed": SEED,
        "request_id": request_id,
        "prompt_template_sha256": tpl_hash,
        "system_prompt_sha256": sys_hash,
        "llm_tokens_input": prompt_tokens,
        "llm_tokens_output": completion_tokens,
        "elapsed_seconds": round(elapsed, int("4")),
    }
    if mock:
        runtime_block["mock"] = True

    print(json.dumps({"output": model_output, "runtime": runtime_block}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
