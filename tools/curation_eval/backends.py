# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""LLM backends for the without-skill arm (and live with-skill classification).

Two kinds:

* ``mock`` -- a deterministic, network-free stand-in that makes a good-faith
  literal attempt at whatever the prompt asks. It lets the whole harness run and
  be graded in-sandbox. It is NOT a language model; a mock run is a methodology
  / plumbing proof, not a skill-value claim.
* ``openai`` -- an OpenAI-compatible chat endpoint (local Ollama / vLLM
  ``serve`` / any ``/v1/chat/completions`` server). Following the reference
  protocol, each request sends only ``model`` + ``messages`` (service defaults;
  no sampling knobs), and provider-reported token usage is captured verbatim.

Backends are declared in a small registry so the CLI can select them by name.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field


@dataclass
class ChatResult:
    text: str
    usage: dict = field(default_factory=dict)
    ok: bool = True
    error: str | None = None
    latency_s: float = 0.0


class Backend:
    """Base backend interface."""

    def __init__(self, name: str, model: str, kind: str):
        self.name = name
        self.model = model
        self.kind = kind

    def chat(self, system: str, user: str) -> ChatResult:  # pragma: no cover - interface
        raise NotImplementedError

    def describe(self) -> dict:
        return {"name": self.name, "kind": self.kind, "model": self.model}


# ---------------------------------------------------------------------------
# Deterministic mock backend
# ---------------------------------------------------------------------------
_DATE_RE = re.compile(r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b")
_ACCESSION_RE = re.compile(r"\bA\d{4,6}\b")
_DOCTOR_RE = re.compile(r"(?:Prof\.|Dr\.)\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){1,2}")
_PHONE_RE = re.compile(r"\b(?:\+?\d[\d ().-]{7,}\d)\b")

# Tiny free-text disease vocabulary the mock "knows" WITHOUT being handed the
# skill's fixed pathology list. Deliberately partial and free-form, so its
# labelling output does not conform to the fixed 0/1 schema the grader expects.
_FREE_DISEASE_TERMS = {
    "infarct": "infarction",
    "gliosis": "gliosis",
    "atrophy": "atrophy",
    "meningioma": "meningioma",
    "aneurysm": "aneurysm",
    "hemorrhage": "hemorrhage",
    "cyst": "cyst",
    "edema": "edema",
    "tumor": "tumor",
    "stenosis": "stenosis",
}

_REPORT_BLOCK_RE = re.compile(r"<report>(.*?)</report>", re.DOTALL | re.IGNORECASE)


def _approx_tokens(text: str) -> int:
    # Rough parity-only estimate for the mock (real backends report exact usage).
    return max(1, len((text or "").split()))


class MockBackend(Backend):
    """Deterministic literal responder used for offline plumbing proofs."""

    def __init__(self, name: str = "mock", model: str = "synthetic-mock-deterministic"):
        super().__init__(name=name, model=model, kind="mock")

    def _extract_report(self, user: str) -> str:
        m = _REPORT_BLOCK_RE.search(user or "")
        return m.group(1).strip() if m else (user or "")

    def chat(self, system: str, user: str) -> ChatResult:
        prompt = f"{system}\n{user}"
        low = prompt.lower()
        report = self._extract_report(user)
        text: str

        if "pii_present" in low or ("pii" in low and "json" in low):
            # PII yes/no is easy; the mock makes a competent literal attempt.
            has_pii = bool(
                _DATE_RE.search(report)
                or _ACCESSION_RE.search(report)
                or _DOCTOR_RE.search(report)
                or _PHONE_RE.search(report)
            )
            text = json.dumps({"pii_present": has_pii})
        elif "disease" in low or "patholog" in low or "diagnos" in low or "label" in low:
            # No fixed vocabulary was provided, so the mock emits free-text
            # disease names -- plausible, but NOT the fixed 0/1 label schema.
            low_report = report.lower()
            found = sorted({v for k, v in _FREE_DISEASE_TERMS.items() if k in low_report})
            if not found:
                found = ["no significant abnormality"]
            text = json.dumps({"diseases": found})
        else:
            text = "OK."

        usage = {
            "prompt_tokens": _approx_tokens(prompt),
            "completion_tokens": _approx_tokens(text),
            "total_tokens": _approx_tokens(prompt) + _approx_tokens(text),
            "reasoning_tokens": 0,
            "estimated": True,
        }
        return ChatResult(text=text, usage=usage, ok=True, latency_s=0.0)


# ---------------------------------------------------------------------------
# OpenAI-compatible HTTP backend
# ---------------------------------------------------------------------------
class OpenAIChatBackend(Backend):
    """Minimal OpenAI-compatible /chat/completions client (service defaults)."""

    def __init__(
        self,
        name: str,
        model: str,
        base_url: str,
        api_key: str | None = None,
        timeout: float = 120.0,
        max_retries: int = 2,
    ):
        super().__init__(name=name, model=model, kind="openai")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries

    def _endpoint(self) -> str:
        base = self.base_url
        if not base.endswith("/chat/completions"):
            base = base + "/chat/completions"
        return base

    def chat(self, system: str, user: str) -> ChatResult:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        last_err = None
        for attempt in range(self.max_retries + 1):
            t0 = time.perf_counter()
            try:
                req = urllib.request.Request(
                    self._endpoint(), data=data, headers=headers, method="POST"
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                latency = time.perf_counter() - t0
                text = (
                    body.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
                )
                raw_usage = body.get("usage", {}) or {}
                details = raw_usage.get("completion_tokens_details", {}) or {}
                usage = {
                    "prompt_tokens": raw_usage.get("prompt_tokens", 0),
                    "completion_tokens": raw_usage.get("completion_tokens", 0),
                    "total_tokens": raw_usage.get("total_tokens", 0),
                    "reasoning_tokens": details.get("reasoning_tokens", 0),
                    "estimated": False,
                }
                return ChatResult(text=text, usage=usage, ok=True, latency_s=latency)
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
                last_err = str(exc)
                time.sleep(min(2.0 * (attempt + 1), 5.0))
            except (ValueError, KeyError) as exc:  # malformed JSON / shape
                last_err = f"bad response: {exc}"
                break
        return ChatResult(text="", usage={}, ok=False, error=last_err)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
# Named live backends. base_url/model mirror the values verified in the repo's
# handoff notes and the existing structuring harness. Reachability is probed at
# run time; unreachable backends are reported, not silently skipped.
LIVE_BACKENDS: dict[str, dict] = {
    "ollama-nemotron": {
        "model": "nemotron-super-16k:latest",
        "base_url": "http://172.20.0.1:11434/v1",
    },
    "ollama-qwen": {
        "model": "qwen3.6:35b-a3b-q8_0",
        "base_url": "http://172.20.0.1:11434/v1",
    },
    "ollama-medgemma": {
        "model": "medgemma:27b",
        "base_url": "http://172.20.0.1:11434/v1",
    },
    "ollama-nemotron120": {
        "model": "nemotron-3-super:120b",
        "base_url": "http://172.20.0.1:11434/v1",
    },
    # Remote NVIDIA-hosted Nemotron-3-Super-120B-A12B (build.nvidia.com).
    # Auth: set the NVIDIA_API_KEY environment variable.
    "nemotron120-remote": {
        "model": "nvidia/nemotron-3-super-120b-a12b",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key_env": "NVIDIA_API_KEY",
    },
    # Default gpt-oss-120b on build.nvidia.com (the anonymizer's default LLM), as a
    # command backend. Auth: NVIDIA_API_KEY.
    "gptoss": {
        "model": "openai/gpt-oss-120b",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key_env": "NVIDIA_API_KEY",
    },
    "vllm-nemotron-nano": {
        "model": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8",
        "base_url": "http://127.0.0.1:8000/v1",
    },
    # --- inference-api.nvidia.com gateway (OpenAI-compatible proxy to many
    #     frontier models: OpenAI, AWS/Azure Bedrock Anthropic, etc.). Model IDs
    #     are the gateway's "<provider>/<vendor>/<model>" identifiers (verified via
    #     GET /v1/models). Auth: set NVIDIA_INFERENCE_API_KEY (an `sk-...` key).
    "gpt-5.5": {
        "model": "openai/openai/gpt-5.5",
        "base_url": "https://inference-api.nvidia.com/v1",
        "api_key_env": "NVIDIA_INFERENCE_API_KEY",
    },
    "claude-opus-4-8": {
        "model": "aws/anthropic/bedrock-claude-opus-4-8",
        "base_url": "https://inference-api.nvidia.com/v1",
        "api_key_env": "NVIDIA_INFERENCE_API_KEY",
    },
    "claude-opus-4-6": {
        "model": "aws/anthropic/bedrock-claude-opus-4-6",
        "base_url": "https://inference-api.nvidia.com/v1",
        "api_key_env": "NVIDIA_INFERENCE_API_KEY",
    },
}


def make_backend(spec: str) -> Backend:
    """Build a backend from a name or an inline spec.

    * ``mock`` -> deterministic mock backend.
    * a key in ``LIVE_BACKENDS`` -> that configured OpenAI-compatible endpoint;
      if the entry declares ``api_key_env``, the key is read from that env var.
    * ``name=base_url=model`` (optionally ``=API_KEY_ENV``) -> an ad-hoc
      OpenAI-compatible endpoint; the 4th field names an env var holding the key.
    """
    if spec == "mock":
        return MockBackend()
    if spec in LIVE_BACKENDS:
        cfg = LIVE_BACKENDS[spec]
        api_key = None
        env_name = cfg.get("api_key_env")
        if env_name:
            api_key = os.environ.get(env_name)
            if not api_key:
                raise ValueError(
                    f"backend '{spec}' needs the {env_name} environment variable set"
                )
        return OpenAIChatBackend(name=spec, model=cfg["model"], base_url=cfg["base_url"],
                                 api_key=api_key)
    if spec.count("=") >= 2:
        parts = spec.split("=", 3)
        name, base_url, model = parts[0], parts[1], parts[2]
        api_key = os.environ.get(parts[3]) if len(parts) == 4 and parts[3] else None
        return OpenAIChatBackend(name=name, model=model, base_url=base_url, api_key=api_key)
    raise ValueError(
        f"unknown backend spec '{spec}'; use 'mock', one of {sorted(LIVE_BACKENDS)}, "
        "or 'name=base_url=model[=API_KEY_ENV]'"
    )


def probe(backend: Backend) -> ChatResult:
    """Cheap reachability check; returns the ChatResult of a tiny ping."""
    return backend.chat("You are a health check.", "Reply with the single word: ok")
