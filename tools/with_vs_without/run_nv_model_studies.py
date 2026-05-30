#!/usr/bin/env python3
"""Run per-skill NV model with-vs-without studies.

This runner covers the planned docs that do not yet have bespoke NAT
orchestrators. It writes generated study JSON/Markdown and generated
volumes/checkpoints under runs/ so refreshed LLM records remain gitignored.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_ROOT = REPO_ROOT / "runs/with_vs_without_nv"
STUDY_ROOT = RUN_ROOT / "studies"
PROMPT_ARTIFACT_ROOT = REPO_ROOT / "tools/nat_audit/data"
CACHE_ROOT = REPO_ROOT / ".workbench_data/with_vs_without_cache"

BASH_BLOCK_RE = re.compile(r"```(?:bash|sh|shell)?\s*\n(.*?)```", re.DOTALL)
PYTHON_LINE_RE = re.compile(r"(^|\n)\s*(?:[A-Za-z_][A-Za-z0-9_]*=.*\s+)*python[0-9.]*\s+.+", re.DOTALL)
LOCAL_HOME_PATH_RE = re.compile(r"/(?:home|Users)/[^\s\"']+")
SHELLISH_START_RE = re.compile(
    r"^\s*(?:(?:[A-Za-z_][A-Za-z0-9_]*=.*\s+)+)?"
    r"(?:python[0-9.]*|pip|uv|conda|mamba|export|mkdir|cd|test|"
    r"huggingface-cli|hf|monai\.bundle|bash)\b",
    re.DOTALL,
)
CHAT_ATTEMPT_TIMEOUT_S = 420
CHAT_RETRY_ATTEMPTS = 4
CHAT_URLOPEN_TIMEOUT_S = 300
CHAT_RETRYABLE_HTTP_STATUSES = (429, 500, 502, 503, 504)
EXTERNAL_LLM_DATA_TRANSFER_FLAG = "--confirm-external-llm-data-transfer"
EXTERNAL_LLM_DATA_TRANSFER_NOTICE = (
    "Direct API modes send the scenario task prompt, the selected SKILL.md or "
    "upstream README text, neutral staged input path, generated commands, and "
    "bounded verifier failure summaries to the configured external LLM API."
)
DIRECT_SYSTEM_PROMPT = (
    "You produce reproducible medical-imaging engineering commands. "
    "Do not make clinical claims."
)
PROMPT_ARTIFACT_ANSWER = (
    "Backend response is captured in runs/with_vs_without_nv/studies; "
    "expected response shape is exactly one bash code block containing one "
    "command or an &&-chained command sequence."
)
DIRECT_REPEATS = 3
DIRECT_MAX_CORRECTION_STEPS = 0
PROTECTED_UPSTREAM_ENV_VARS = ("NV_GENERATE_ROOT", "NV_SEGMENT_CTMR_ROOT")


@contextlib.contextmanager
def _hard_timeout(seconds: int, label: str):
    """Bound API reads even if the underlying TLS socket does not time out."""
    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.getitimer(signal.ITIMER_REAL)

    def _raise_timeout(_signum, _frame):
        raise TimeoutError(f"{label} timed out after {seconds}s")

    signal.signal(signal.SIGALRM, _raise_timeout)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        if previous_timer[0] > 0:
            signal.setitimer(signal.ITIMER_REAL, *previous_timer)


@dataclass(frozen=True)
class Backend:
    key: str
    label: str
    base_url: str
    model: str
    env_var: str


BACKENDS = {
    "nemotron": Backend(
        key="nemotron",
        label="Nemotron",
        base_url="https://inference-api.nvidia.com/v1",
        model="nvidia/nvidia/nemotron-3-super-v3",
        env_var="NV_INFER_TOKEN",
    ),
    "gpt55": Backend(
        key="gpt55",
        label="GPT-5.5 / Codex",
        base_url="https://inference-api.nvidia.com/v1",
        model="openai/openai/gpt-5.5",
        env_var="NV_INFER_TOKEN",
    ),
    "opus": Backend(
        key="opus",
        label="Opus 4.7",
        base_url="https://inference-api.nvidia.com/v1",
        model="aws/anthropic/bedrock-claude-opus-4-7",
        env_var="NV_INFER_TOKEN",
    ),
}


def _backend_protocol(backend: Backend) -> dict[str, Any]:
    """Serializable backend settings that define the fair comparison protocol."""
    protocol = {
        "base_url": backend.base_url,
        "model": backend.model,
        "api_request_parameters": ["model", "messages"],
        "provider_defaults": True,
        "retry_attempts": CHAT_RETRY_ATTEMPTS,
        "retryable_http_statuses": list(CHAT_RETRYABLE_HTTP_STATUSES),
        "chat_attempt_timeout_seconds": CHAT_ATTEMPT_TIMEOUT_S,
        "urlopen_timeout_seconds": CHAT_URLOPEN_TIMEOUT_S,
    }
    return protocol


@dataclass(frozen=True)
class Scenario:
    skill: str
    title: str
    fixture: str
    kind: str
    task: str
    user_goal: str
    with_doc: tuple[str, ...]
    without_doc: tuple[str, ...]
    tier1: tuple[str, ...]
    tier2: tuple[str, ...]
    tier3: tuple[str, ...]
    timeout_s: int = 1800
    env: dict[str, str] | None = None


def _p(path: str) -> str:
    return str(REPO_ROOT / path)


def _skill_doc_dir(s: Scenario) -> str:
    for doc in s.with_doc:
        if doc.startswith("skills/"):
            return Path(doc).parent.as_posix()
    return f"skills/{s.skill.replace('_', '-')}"


def _manifest_entrypoint_from_skill_doc(doc: str) -> str | None:
    if not doc.startswith("skills/"):
        return None
    manifest_path = REPO_ROOT / Path(doc).parent / "skill_manifest.yaml"
    if not manifest_path.exists():
        return None
    match = re.search(r"(?m)^\s*entrypoint:\s*([^\n#]+)", manifest_path.read_text())
    if not match:
        return None
    return match.group(1).strip().strip("'\"")


def _repair_feedback_forbidden_markers(s: Scenario, arm: str) -> tuple[str, ...]:
    """Markers that must not be echoed into bounded repair prompts.

    The README-only arm may see upstream docs and its own generated errors, but
    repair feedback must not introduce hidden Medical AI Skills skill paths or wrapper
    names. The with-skill arm is allowed to see its skill docs, so only the
    without arm has extra markers here.
    """
    if arm != "without":
        return ()
    markers: list[str] = []
    for doc in s.with_doc:
        if not doc.startswith("skills/"):
            continue
        skill_dir = Path(doc).parent.as_posix()
        markers.extend([doc, f"{skill_dir}/", f"{skill_dir}/skill_manifest.yaml"])
        entrypoint = _manifest_entrypoint_from_skill_doc(doc)
        if entrypoint:
            markers.extend([entrypoint, Path(entrypoint).name])
    return tuple(dict.fromkeys(marker for marker in markers if marker))


def _sanitize_feedback_text(text: str, s: Scenario, arm: str) -> str:
    sanitized = text.replace(str(REPO_ROOT) + "/", "")
    sanitized = sanitized.replace(str(REPO_ROOT), ".")
    home = str(Path.home())
    if home and home != str(REPO_ROOT):
        sanitized = sanitized.replace(home + "/", "<HOME>/")
        sanitized = sanitized.replace(home, "<HOME>")
    for marker in _repair_feedback_forbidden_markers(s, arm):
        sanitized = sanitized.replace(marker, "<REDACTED_WORKBENCH_SKILL_MARKER>")
    return sanitized


def _sanitize_feedback_detail(value: Any, s: Scenario, arm: str) -> Any:
    if isinstance(value, str):
        return _sanitize_feedback_text(value, s, arm)
    if isinstance(value, list):
        return [_sanitize_feedback_detail(item, s, arm) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_feedback_detail(item, s, arm) for key, item in value.items()}
    return value


SCENARIOS: dict[str, Scenario] = {
    "nv_segment_ct": Scenario(
        skill="nv_segment_ct",
        title="NV-Segment-CT",
        fixture="skills/nv-segment-ct/fixtures/spleen_03.nii.gz",
        kind="segmentation",
        task="Segment liver, spleen, right kidney, and left kidney from the CT NIfTI fixture. The required label IDs are 1,3,5,14.",
        user_goal=(
            "The input CT volume is at {input_path}. Segment the spleen, liver, "
            "right kidney, and left kidney, and write outputs under {out_dir}."
        ),
        with_doc=("skills/nv-segment-ct/SKILL.md",),
        without_doc=("tools/with_vs_without/upstream_docs/nv_segment_ct_NV-Segment-CTMR_README.md",),
        tier1=("run_vista3d.py", "monai.bundle", "configs/inference.json"),
        tier2=("spleen_03.nii.gz",),
        tier3=("1", "3", "5", "14"),
        timeout_s=2400,
    ),
    "nv_segment_ctmr": Scenario(
        skill="nv_segment_ctmr",
        title="NV-Segment-CTMR",
        fixture="skills/nv-segment-ct/fixtures/spleen_03.nii.gz",
        kind="segmentation",
        task="Run CT_BODY segmentation on the CT NIfTI fixture.",
        user_goal=(
            "The input CT volume is at {input_path}. Run the CT body segmentation "
            "workflow and write the label map under {out_dir}."
        ),
        with_doc=("skills/nv-segment-ctmr/SKILL.md",),
        without_doc=("tools/with_vs_without/upstream_docs/nv_segment_ctmr_NV-Segment-CTMR_README.md",),
        tier1=("run_ctmr.py", "monai.bundle", "configs/inference.json"),
        tier2=("spleen_03.nii.gz",),
        tier3=("CT_BODY",),
        timeout_s=2400,
        env={"NV_SEGMENT_CTMR_ROOT": _p(".workbench_data/upstreams/NV-Segment-CTMR/NV-Segment-CTMR")},
    ),
    "nv_segment_ct_finetune": Scenario(
        skill="nv_segment_ct_finetune",
        title="NV-Segment-CT Finetune",
        fixture="skills/nv-segment-ct-finetune/fixtures/spleen_micro",
        kind="finetune",
        task="Run the smoke finetune preset on the spleen_micro fixture. Use a short smoke run, not a full clinical training run.",
        user_goal=(
            "Fine-tune the CT segmentation workflow on the small dataset at "
            "{input_path}. Use the shortest smoke-scale run suitable for checking "
            "the workflow, and write outputs under {out_dir}."
        ),
        with_doc=("skills/nv-segment-ct-finetune/SKILL.md",),
        without_doc=("tools/with_vs_without/upstream_docs/nv_segment_ct_finetune_NV-Segment-CT_finetune.md",),
        tier1=("run_finetune.py", "monai.bundle", "train_continual"),
        tier2=("spleen_micro", "datalist"),
        tier3=("smoke", "train_continual", "configs/train.json"),
        timeout_s=2400,
    ),
    "nv_generate_ct_rflow": Scenario(
        skill="nv_generate_ct_rflow",
        title="NV-Generate CT RFlow",
        fixture="skills/nv-generate-ct-rflow/fixtures/chest_lung_tumor_controllable.json",
        kind="ct_pair",
        task="Synthesize one paired 3D CT image and 132-class mask for chest with lung tumor.",
        user_goal=(
            "The case request is at {input_path}. Synthesize one paired 3D CT "
            "image and segmentation mask for a chest case with a lung tumor, and "
            "write the output pair under {out_dir}."
        ),
        with_doc=("skills/nv-generate-ct-rflow/SKILL.md",),
        without_doc=("tools/with_vs_without/upstream_docs/nv_generate_ct_rflow_NV-Generate-CTMR_infer_mask-image-paired.md",),
        tier1=("run_rflow_ct.py", "scripts.inference"),
        tier2=("chest_lung_tumor_controllable.json", "config_infer.json"),
        tier3=("rflow-ct", "lung tumor", "chest"),
        timeout_s=2400,
        env={"NV_GENERATE_ROOT": _p(".workbench_data/upstreams/NV-Generate-CTMR")},
    ),
    "nv_generate_mr": Scenario(
        skill="nv_generate_mr",
        title="NV-Generate MR",
        fixture="skills/nv-generate-mr/fixtures/default_mri_t1.json",
        kind="image",
        task="Generate one T1 MR image-only NIfTI volume.",
        user_goal=(
            "The image-generation request is at {input_path}. Generate one T1 MR "
            "image and write generated NIfTI volumes under {out_dir}."
        ),
        with_doc=("skills/nv-generate-mr/SKILL.md",),
        without_doc=("tools/with_vs_without/upstream_docs/nv_generate_mr_NV-Generate-CTMR_infer_image-only.md",),
        tier1=("run_mr.py", "scripts.diff_model_infer"),
        tier2=("default_mri_t1.json", "config_maisi_diff_model_rflow-mr.json"),
        tier3=("rflow-mr", "mri_t1"),
        timeout_s=1800,
        env={"NV_GENERATE_ROOT": _p(".workbench_data/upstreams/NV-Generate-CTMR")},
    ),
    "nv_generate_mr_brain": Scenario(
        skill="nv_generate_mr_brain",
        title="NV-Generate MR Brain",
        fixture="skills/nv-generate-mr-brain/fixtures/default_mri_t1.json",
        kind="image",
        task="Generate one T1 brain MR image-only NIfTI volume.",
        user_goal=(
            "The image-generation request is at {input_path}. Generate one T1 "
            "brain MR image and write generated NIfTI volumes under {out_dir}."
        ),
        with_doc=("skills/nv-generate-mr-brain/SKILL.md",),
        without_doc=("tools/with_vs_without/upstream_docs/nv_generate_mr_NV-Generate-CTMR_infer_image-only.md",),
        tier1=("run_mr_brain.py", "scripts.diff_model_infer"),
        tier2=("default_mri_t1.json", "config_maisi_diff_model_rflow-mr-brain.json"),
        tier3=("rflow-mr-brain", "mri_t1"),
        timeout_s=1800,
        env={"NV_GENERATE_ROOT": _p(".workbench_data/upstreams/NV-Generate-CTMR")},
    ),
    "nv_generate_mr_brain_finetune": Scenario(
        skill="nv_generate_mr_brain_finetune",
        title="NV-Generate MR Brain Finetune",
        fixture="skills/nv-generate-mr-brain-finetune/fixtures",
        kind="preflight",
        task=(
            "Validate and stage the MR-brain diffusion-UNet finetuning workflow "
            "from the bundled preflight datalist. Do not launch full GPU training."
        ),
        user_goal=(
            "The MR-brain finetuning preflight input bundle is at {input_path}. "
            "Validate and stage the shortest preflight-scale workflow check, and "
            "write outputs under {out_dir}."
        ),
        with_doc=("skills/nv-generate-mr-brain-finetune/SKILL.md",),
        without_doc=(
            "tools/with_vs_without/upstream_docs/"
            "nv_generate_mr_brain_finetune_NV-Generate-CTMR_train_diff_unet.md",
        ),
        tier1=("run_mr_brain_finetune.py", "scripts.diff_model_train", "scripts.diff_model_create_training_data"),
        tier2=("preflight_datalist.json", "preflight_dataset"),
        tier3=("rflow-mr-brain", "mri_t1", "--preflight"),
        timeout_s=900,
        env={"NV_GENERATE_ROOT": _p(".workbench_data/upstreams/NV-Generate-CTMR")},
    ),
    "nv_generate_vae_finetune": Scenario(
        skill="nv_generate_vae_finetune",
        title="NV-Generate VAE Finetune",
        fixture="skills/nv-generate-vae-finetune/fixtures",
        kind="preflight",
        task=(
            "Validate and stage the MAISI VAE finetuning workflow from the "
            "bundled CT/MRI preflight datalist. Do not launch full GPU training."
        ),
        user_goal=(
            "The VAE finetuning preflight input bundle is at {input_path}. "
            "Validate and stage the shortest preflight-scale workflow check, and "
            "write outputs under {out_dir}."
        ),
        with_doc=("skills/nv-generate-vae-finetune/SKILL.md",),
        without_doc=(
            "tools/with_vs_without/upstream_docs/"
            "nv_generate_vae_finetune_NV-Generate-CTMR_train_vae.md",
        ),
        tier1=("run_vae_finetune.py", "train_vae_tutorial.ipynb", "VAE_Transform"),
        tier2=("preflight_datalist.json", "preflight_dataset"),
        tier3=("maisi-vae", "mri", "--preflight"),
        timeout_s=900,
        env={"NV_GENERATE_ROOT": _p(".workbench_data/upstreams/NV-Generate-CTMR")},
    ),
    "nv_reason_cxr": Scenario(
        skill="nv_reason_cxr",
        title="NV-Reason-CXR",
        fixture="skills/nv-reason-cxr/fixtures/synthetic_cxr_input.json",
        kind="json",
        task="Run the synthetic CXR fixture through a command-shape smoke test and write schema-valid JSON. Use mock mode if available; do not grade clinical correctness.",
        user_goal=(
            "The CXR request is at {input_path}. Run a command-shape smoke test "
            "for the CXR reasoning workflow and write structured JSON under "
            "{out_dir}. Do not grade clinical correctness."
        ),
        with_doc=("skills/nv-reason-cxr/SKILL.md",),
        without_doc=("tools/with_vs_without/upstream_docs/nv_reason_cxr_NV-Reason-CXR_README.md",),
        tier1=("run_nv_reason_cxr.py", "transformers", "AutoModel"),
        tier2=("synthetic_cxr_input.json", ".png", ".jpg"),
        tier3=("NV-Reason-CXR-3B", "mock", "nvidia/NV-Reason-CXR-3B"),
        timeout_s=900,
        env={"MOCK_NV_REASON_CXR": "1"},
    ),
}


def _read_env_value(name: str) -> str:
    if os.environ.get(name):
        return os.environ[name]
    aliases = {"NVIDIA_API_KEY": "NVIDIA_BUILD_KEY"}
    alias = aliases.get(name)
    if alias and os.environ.get(alias):
        return os.environ[alias]
    bashrc = Path.home() / ".bashrc"
    if bashrc.is_file():
        names = [name] + ([alias] if alias else [])
        for line in bashrc.read_text().splitlines():
            stripped = line.strip()
            for candidate in names:
                prefix = f"export {candidate}="
                if stripped.startswith(prefix):
                    val = stripped.split("=", 1)[1].split("#", 1)[0].strip()
                    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                        val = val[1:-1]
                    if val:
                        return val
    raise RuntimeError(f"missing API key env: {name}")


def _read_doc(path: str) -> str:
    p = REPO_ROOT / path
    if not p.is_file():
        return f"[missing document: {path}]"
    return p.read_text(errors="replace")


def _documentation_records(docs: tuple[str, ...]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for doc in docs:
        p = REPO_ROOT / doc
        if not p.is_file():
            records.append(
                {
                    "path": doc,
                    "exists": False,
                    "byte_count": 0,
                    "sha256": None,
                }
            )
            continue
        data = p.read_bytes()
        records.append(
            {
                "path": doc,
                "exists": True,
                "byte_count": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return records


def _staged_input_path(s: Scenario) -> Path:
    source = REPO_ROOT / s.fixture
    if source.is_dir():
        neutral_name = "input_dataset"
    elif source.name.endswith(".nii.gz"):
        neutral_name = "input.nii.gz"
    elif source.suffix == ".nii":
        neutral_name = "input.nii"
    elif source.suffix == ".json":
        neutral_name = "request.json"
    elif source.suffix:
        neutral_name = f"input{source.suffix}"
    else:
        neutral_name = "input"
    return RUN_ROOT / "_inputs" / s.skill / neutral_name


def _stage_input(s: Scenario) -> Path:
    source = REPO_ROOT / s.fixture
    target = _staged_input_path(s)
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
    else:
        shutil.copy2(source, target)
    return target


def _message_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, list):
        text_parts = [
            str(part.get("text", part))
            for part in content
            if isinstance(part, dict)
        ]
        if text_parts:
            return "\n".join(text_parts)
    if content:
        return str(content)

    # Some NIM reasoning routes return the visible answer in reasoning_content
    # when content is empty.
    reasoning_content = message.get("reasoning_content")
    if isinstance(reasoning_content, list):
        text_parts = [
            str(part.get("text", part))
            for part in reasoning_content
            if isinstance(part, dict)
        ]
        if text_parts:
            return "\n".join(text_parts)
    return str(reasoning_content or "")


def _chat(backend: Backend, messages: list[dict[str, str]]) -> tuple[str, dict[str, Any]]:
    key = _read_env_value(backend.env_var)
    payload: dict[str, Any] = {
        "model": backend.model,
        "messages": messages,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        backend.base_url.rstrip("/") + "/chat/completions",
        data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    raw = ""
    last_error: Exception | None = None
    for attempt in range(CHAT_RETRY_ATTEMPTS):
        try:
            with _hard_timeout(CHAT_ATTEMPT_TIMEOUT_S, f"{backend.key} chat attempt {attempt + 1}"):
                with urllib.request.urlopen(req, timeout=CHAT_URLOPEN_TIMEOUT_S) as resp:
                    raw = resp.read().decode()
            break
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            last_error = RuntimeError(f"{backend.key} HTTP {e.code}: {body[:1200]}")
            if e.code not in CHAT_RETRYABLE_HTTP_STATUSES or attempt == CHAT_RETRY_ATTEMPTS - 1:
                raise last_error from e
            time.sleep(5 * (attempt + 1))
        except Exception as e:  # noqa: BLE001
            last_error = e
            if attempt == CHAT_RETRY_ATTEMPTS - 1:
                raise
            time.sleep(5 * (attempt + 1))
    if not raw and last_error:
        raise last_error
    obj = json.loads(raw)
    text = _message_text(obj["choices"][0]["message"])
    return text, obj.get("usage") or {}


def _guarded_prompt(s: Scenario, arm: str, out_dir: Path) -> str:
    docs = s.with_doc if arm == "with" else s.without_doc
    doc_text = "\n\n".join(f"--- {path} ---\n{_read_doc(path)}" for path in docs)
    constraints = [
        "Produce exactly one bash code block containing one command or an &&-chained command sequence.",
        "Do not run the command yourself.",
        "Use paths relative to the Medical AI Skills repo root unless an environment variable is explicitly provided.",
        f"The expected output directory is {out_dir.relative_to(REPO_ROOT)}.",
        f"The fixture/input is {s.fixture}.",
        "Do not write to or modify .workbench_data/upstreams, $NV_GENERATE_ROOT, or $NV_SEGMENT_CTMR_ROOT; stage any edited runtime files under the requested output directory.",
    ]
    if s.env:
        env_lines = ", ".join(f"{k}={v}" for k, v in s.env.items())
        constraints.append(f"Available runtime environment variables: {env_lines}.")
    if arm == "with":
        constraints.append(f"Use Medical AI Skills skill {s.skill}; do not inspect unrelated skill internals.")
    else:
        constraints.append(f"Do not use or mention files under {_skill_doc_dir(s)}/; use only the upstream documentation.")
    return (
        f"You are helping run an engineering reproducibility experiment for {s.title}.\n"
        f"Task: {s.task}\n\n"
        + "\n".join(f"- {c}" for c in constraints)
        + "\n\nDocumentation available to you:\n"
        + doc_text
    )


def _minimal_prompt(s: Scenario, arm: str, out_dir: Path) -> str:
    docs = s.with_doc if arm == "with" else s.without_doc
    doc_text = "\n\n".join(f"--- {path} ---\n{_read_doc(path)}" for path in docs)
    input_path = _staged_input_path(s).relative_to(REPO_ROOT)
    output_path = out_dir.relative_to(REPO_ROOT)
    user_goal = s.user_goal.format(input_path=input_path, out_dir=output_path)
    constraints = [
        "Produce exactly one bash code block containing one command or an &&-chained command sequence.",
        "Do not run the command yourself.",
        "Use the documentation below to infer setup steps, model variant, labels, config files, and runnable commands.",
        "Use paths relative to the Medical AI Skills repo root unless the documentation itself tells you otherwise.",
        "Do not write to or modify .workbench_data/upstreams, $NV_GENERATE_ROOT, or $NV_SEGMENT_CTMR_ROOT; stage any edited runtime files under the requested output directory.",
    ]
    if arm == "with":
        constraints.append(f"Use Medical AI Skills skill documentation for {s.skill}; do not inspect unrelated skill internals.")
    else:
        constraints.append(
            f"Use only the upstream documentation below; do not use or mention files under {_skill_doc_dir(s)}/."
        )
    return (
        "You are helping a medical-imaging engineer who has cloned the Medical AI Skills repo.\n"
        f"User request: {user_goal}\n\n"
        + "\n".join(f"- {c}" for c in constraints)
        + "\n\nDocumentation available to you:\n"
        + doc_text
    )


def _path_prompt(s: Scenario, arm: str, out_dir: Path) -> str:
    """A2-style prompt for tool-enabled agents that can read repo files."""
    input_path = _staged_input_path(s).relative_to(REPO_ROOT)
    output_path = out_dir.relative_to(REPO_ROOT)
    user_goal = s.user_goal.format(input_path=input_path, out_dir=output_path)
    doc_path = s.with_doc[0] if arm == "with" else s.without_doc[0]
    if arm == "with":
        forbidden_instruction = f"Do not inspect any other files under {_skill_doc_dir(s)}/."
    else:
        forbidden_instruction = f"Do not read or use any files under {_skill_doc_dir(s)}/."
    return (
        "You are helping a medical-imaging engineer who has cloned "
        "https://github.com/NVIDIA-Medtech/medical-AI-skills. "
        f"{user_goal} "
        "Tier-5 execution will occur in a fresh per-arm Python environment "
        "with no runtime dependencies preinstalled, so include any setup steps "
        "the documentation says are required. "
        f"The only workflow document available to you is {doc_path}. "
        f"Read that document. {forbidden_instruction} "
        "Use list_directory only if you need to confirm paths. "
        "Do not write to or modify .workbench_data/upstreams or NV upstream root environment variables; stage edited runtime files under the requested output directory. "
        "Then produce a SINGLE shell command (or `&&`-chained sequence) "
        "inside one ```bash code block. Follow the bash block with a brief "
        "one-line explanation. Do not run the command yourself."
    )


def _prompt(s: Scenario, arm: str, out_dir: Path, prompt_style: str = "minimal") -> str:
    if prompt_style == "path":
        return _path_prompt(s, arm, out_dir)
    if prompt_style == "guarded":
        return _guarded_prompt(s, arm, out_dir)
    return _minimal_prompt(s, arm, out_dir)


def _extract_command(text: str) -> str | None:
    matches = BASH_BLOCK_RE.findall(text or "")
    if len(matches) == 1:
        cmd = matches[0].strip()
        return re.sub(r"\n?```+\s*$", "", cmd).strip()
    raw = (text or "").strip()
    if not matches and re.match(r"^\s*(?:bash|sh|shell)\s*\n", raw, flags=re.IGNORECASE):
        candidate = re.sub(
            r"^\s*(?:bash|sh|shell)\s*\n",
            "",
            raw,
            count=1,
            flags=re.IGNORECASE,
        ).strip()
        candidate = re.sub(r"\n?```+\s*$", "", candidate).strip()
        if candidate and SHELLISH_START_RE.search(candidate):
            return candidate
    return None


def _protected_upstream_defaults() -> dict[str, str]:
    return {
        "NV_GENERATE_ROOT": _p(".workbench_data/upstreams/NV-Generate-CTMR"),
        "NV_SEGMENT_CTMR_ROOT": _p(".workbench_data/upstreams/NV-Segment-CTMR/NV-Segment-CTMR"),
    }


def _protected_upstream_env(s: Scenario) -> dict[str, str]:
    env = _protected_upstream_defaults()
    env.update(s.env or {})
    return {name: env[name] for name in PROTECTED_UPSTREAM_ENV_VARS if env.get(name)}


def _is_protected_upstream_target(token: str) -> bool:
    target = token.strip().strip("'\"")
    if not target:
        return False
    upstream_root = REPO_ROOT / ".workbench_data/upstreams"
    protected_prefixes = [
        ".workbench_data/upstreams",
        "./.workbench_data/upstreams",
        str(upstream_root),
    ]
    for name in PROTECTED_UPSTREAM_ENV_VARS:
        protected_prefixes.extend((f"${name}", f"${{{name}}}"))
    return any(target == prefix or target.startswith(f"{prefix}/") for prefix in protected_prefixes)


def _shell_segments(cmd: str) -> list[str]:
    return [segment.strip() for segment in re.split(r"(?:&&|\|\||[;&|\n])", cmd) if segment.strip()]


def _shell_tokens(segment: str) -> list[str]:
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


def _skip_env_assignments(tokens: list[str]) -> list[str]:
    index = 0
    while index < len(tokens) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[index]):
        index += 1
    return tokens[index:]


def _redirection_targets(tokens: list[str]) -> list[str]:
    targets: list[str] = []
    redirect_ops = {">", ">>", "1>", "1>>", "2>", "2>>", "&>", "&>>"}
    for index, token in enumerate(tokens):
        if token in redirect_ops and index + 1 < len(tokens):
            targets.append(tokens[index + 1])
            continue
        match = re.fullmatch(r"(?:[12]?>>?|&>>?)(.+)", token)
        if match:
            targets.append(match.group(1))
    return targets


def _protected_upstream_write_reason(cmd: str) -> str | None:
    inplace_editors = {"sed", "perl"}
    for segment in _shell_segments(cmd):
        tokens = _skip_env_assignments(_shell_tokens(segment))
        if not tokens:
            continue
        command_name = Path(tokens[0]).name
        for target in _redirection_targets(tokens):
            if _is_protected_upstream_target(target):
                return "command redirects output into a protected upstream checkout"
        if command_name in {"cp", "mv", "install", "rsync"}:
            if len(tokens) > 1 and _is_protected_upstream_target(tokens[-1]):
                return f"command attempts to write to protected upstream checkout via {command_name}"
        elif command_name in {"tee", "touch", "mkdir"}:
            targets = [token for token in tokens[1:] if not token.startswith("-")]
            if any(_is_protected_upstream_target(target) for target in targets):
                return f"command attempts to write to protected upstream checkout via {command_name}"
        elif command_name in inplace_editors and any(token.startswith("-i") for token in tokens[1:]):
            targets = [token for token in tokens[1:] if not token.startswith("-")]
            if any(_is_protected_upstream_target(target) for target in targets):
                return f"command attempts in-place editing inside a protected upstream checkout via {command_name}"
    return None


def _safe_to_execute(s: Scenario, arm: str, cmd: str | None, out_dir: Path) -> tuple[bool, str]:
    if not cmd:
        return False, "no command extracted"
    if len(cmd) > 12000:
        return False, "command too long for guarded execution"
    rel_out = str(out_dir.relative_to(REPO_ROOT))
    if rel_out not in cmd and str(out_dir) not in cmd:
        return False, "command does not reference the expected output directory"
    rel_input = str(_staged_input_path(s).relative_to(REPO_ROOT))
    if rel_input not in cmd and str(_staged_input_path(s)) not in cmd:
        return False, "command does not reference the neutral staged input path"
    if not any(marker in cmd for marker in s.tier1):
        return False, "command does not reference an expected runnable surface"
    if arm == "without" and any(marker and marker in cmd for marker in _repair_feedback_forbidden_markers(s, arm)):
        return False, "without-skill command references forbidden Medical AI Skills skill marker"
    # Guard against high-blast-radius shell operations. The experiment still
    # intentionally executes generated commands, but only if they stay within
    # the expected install/inference surfaces.
    banned_re = re.compile(
        r"(^|[;&|]\s*)"
        r"(sudo|rm|dd|mkfs|mount|umount|docker|podman|systemctl|apt|apt-get|"
        r"dnf|yum|scp|ssh|chmod|chown|curl|wget)\b"
    )
    m = banned_re.search(cmd)
    if m:
        return False, f"blocked unsafe command fragment: {m.group(2)}"
    upstream_write_reason = _protected_upstream_write_reason(cmd)
    if upstream_write_reason:
        return False, upstream_write_reason
    return True, "ok"


def _exec_env_path(out_dir: Path) -> Path:
    try:
        rel = out_dir.resolve().relative_to(RUN_ROOT.resolve())
    except ValueError:
        rel = Path(re.sub(r"[^A-Za-z0-9_.-]+", "_", str(out_dir.resolve())))
    return RUN_ROOT / "_exec_envs" / rel / "venv"


def _shared_cache_env_paths() -> dict[str, Path]:
    return {
        "PIP_CACHE_DIR": CACHE_ROOT / "pip",
        "HF_HOME": CACHE_ROOT / "huggingface",
        "HF_HUB_CACHE": CACHE_ROOT / "huggingface" / "hub",
        "HUGGINGFACE_HUB_CACHE": CACHE_ROOT / "huggingface" / "hub",
        "TRANSFORMERS_CACHE": CACHE_ROOT / "huggingface" / "transformers",
        "TORCH_HOME": CACHE_ROOT / "torch",
        "XDG_CACHE_HOME": CACHE_ROOT / "xdg",
        "CONDA_PKGS_DIRS": CACHE_ROOT / "conda_pkgs",
        "UV_CACHE_DIR": CACHE_ROOT / "uv",
        "CUDA_CACHE_PATH": CACHE_ROOT / "cuda",
        "NUMBA_CACHE_DIR": CACHE_ROOT / "numba",
    }


def _shared_cache_env_records() -> dict[str, str]:
    return {
        name: str(path.relative_to(REPO_ROOT))
        for name, path in _shared_cache_env_paths().items()
    }


def _protected_upstream_config_files(s: Scenario) -> list[Path]:
    files: list[Path] = []
    for root_text in _protected_upstream_env(s).values():
        config_dir = Path(root_text) / "configs"
        if not config_dir.is_dir():
            continue
        files.extend(path for path in sorted(config_dir.rglob("*")) if path.is_file())
    return files


def _snapshot_protected_upstream_configs(s: Scenario) -> dict[str, bytes]:
    snapshot: dict[str, bytes] = {}
    for path in _protected_upstream_config_files(s):
        try:
            snapshot[str(path)] = path.read_bytes()
        except OSError:
            continue
    return snapshot


def _restore_protected_upstream_configs(
    s: Scenario,
    snapshot: dict[str, bytes],
) -> list[str]:
    changes: list[str] = []
    snapshot_paths = {Path(path) for path in snapshot}
    current_paths = set(_protected_upstream_config_files(s))
    for path in sorted(current_paths - snapshot_paths):
        try:
            path.unlink()
            changes.append(str(path.relative_to(REPO_ROOT)))
        except (OSError, ValueError):
            changes.append(str(path))
    for path_text, expected in snapshot.items():
        path = Path(path_text)
        try:
            current = path.read_bytes() if path.is_file() else None
        except OSError:
            current = None
        if current == expected:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(expected)
        try:
            changes.append(str(path.relative_to(REPO_ROOT)))
        except ValueError:
            changes.append(str(path))
    return sorted(dict.fromkeys(changes))


def _build_isolated_exec_env(out_dir: Path) -> tuple[dict[str, str], Path, Path, bool]:
    """Create a clean per-attempt venv so python/pip do not inherit host packages."""
    resolved_python = os.environ.get("A2_AGENT_PYTHON") or sys.executable
    exec_venv = _exec_env_path(out_dir)
    bin_dir = exec_venv / "bin"
    shutil.rmtree(exec_venv, ignore_errors=True)
    exec_venv.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [resolved_python, "-m", "venv", str(exec_venv)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"{resolved_python} -m venv failed with exit {proc.returncode}: "
            f"{proc.stderr[-800:] or proc.stdout[-800:]}"
        )

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["VIRTUAL_ENV"] = str(exec_venv)
    env["PYTHONNOUSERSITE"] = "1"
    env.pop("PYTHONPATH", None)
    shared_caches = _shared_cache_env_paths()
    for cache_dir in shared_caches.values():
        cache_dir.mkdir(parents=True, exist_ok=True)
    for name, cache_dir in shared_caches.items():
        env[name] = str(cache_dir)
    env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    return env, exec_venv, bin_dir / "python", True


def _maybe_json(stdout: str) -> dict[str, Any] | None:
    text = stdout.strip()
    if not text:
        return None
    for candidate in (text, text.splitlines()[-1]):
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            obj = json.loads(text[start : end + 1])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            return None
    return None


def _execute(s: Scenario, arm: str, cmd: str | None, out_dir: Path) -> dict[str, Any]:
    ok, reason = _safe_to_execute(s, arm, cmd, out_dir)
    if not ok:
        return {"executed": False, "exit_code": None, "reason": reason}
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    env, exec_venv, exec_python, fresh_env_created = _build_isolated_exec_env(out_dir)
    env.update(s.env or {})
    env.update({name: value for name, value in _protected_upstream_defaults().items() if name not in env})
    env.setdefault("PYTHONUNBUFFERED", "1")
    protected_snapshot = _snapshot_protected_upstream_configs(s)
    t0 = time.time()
    proc = subprocess.run(
        ["bash", "-lc", cmd or ""],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=s.timeout_s,
    )
    upstream_mutation_paths = _restore_protected_upstream_configs(s, protected_snapshot)
    generated_files = []
    if out_dir.exists():
        generated_files = [
            str(p.relative_to(REPO_ROOT))
            for p in sorted(out_dir.rglob("*"))
            if p.is_file()
        ][:80]
    return {
        "executed": True,
        "exit_code": proc.returncode,
        "elapsed_seconds": time.time() - t0,
        "isolated_exec_env": True,
        "fresh_exec_env_created": fresh_env_created,
        "exec_env_path": str(exec_venv.relative_to(REPO_ROOT)),
        "exec_python": str(exec_python),
        "shared_cache_env": _shared_cache_env_records(),
        "protected_upstream_env": {
            name: str(Path(value).relative_to(REPO_ROOT))
            for name, value in _protected_upstream_env(s).items()
            if Path(value).is_relative_to(REPO_ROOT)
        },
        "upstream_mutation_detected": bool(upstream_mutation_paths),
        "upstream_mutation_restored": bool(upstream_mutation_paths),
        "upstream_mutation_paths": upstream_mutation_paths[:80],
        "generated_files": generated_files,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
        "json": _maybe_json(proc.stdout),
    }


def _load_nifti(path: Path) -> tuple[bool, str]:
    try:
        import nibabel as nib
        import numpy as np

        arr = nib.load(str(path)).get_fdata()
        if arr.size == 0:
            return False, "empty array"
        if not np.isfinite(arr).all():
            return False, "non-finite voxels"
        if float(np.nanmax(arr)) == float(np.nanmin(arr)):
            return False, "constant image"
        return True, f"shape={arr.shape}"
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def _nifti_stem(path: Path) -> str:
    name = path.name
    if name.endswith(".nii.gz"):
        return name[: -len(".nii.gz")]
    if name.endswith(".nii"):
        return name[: -len(".nii")]
    return path.stem


def _ct_pair_key(path: Path, role: str) -> str | None:
    stem = _nifti_stem(path)
    suffix = f"_{role}"
    prefix = f"{role}_"
    if stem.endswith(suffix):
        return stem[: -len(suffix)] or "default"
    if stem.startswith(prefix):
        return stem[len(prefix) :] or "default"
    if stem == role:
        return "default"
    return None


def _ct_pair_candidates(out_dir: Path) -> list[tuple[Path, Path]]:
    images: dict[str, list[Path]] = {}
    labels: dict[str, list[Path]] = {}
    for path in sorted(out_dir.rglob("*.nii")) + sorted(out_dir.rglob("*.nii.gz")):
        image_key = _ct_pair_key(path, "image")
        if image_key is not None:
            images.setdefault(image_key, []).append(path)
        label_key = _ct_pair_key(path, "label")
        if label_key is not None:
            labels.setdefault(label_key, []).append(path)
    pairs: list[tuple[Path, Path]] = []
    for key in sorted(set(images) & set(labels)):
        pairs.append((images[key][-1], labels[key][-1]))
    return pairs


def _verify_outputs(s: Scenario, out_dir: Path, exec_result: dict[str, Any]) -> tuple[bool, str]:
    if not exec_result.get("executed"):
        return False, exec_result.get("reason", "not executed")
    if exec_result.get("upstream_mutation_detected"):
        paths = exec_result.get("upstream_mutation_paths") or []
        detail = ", ".join(paths[:5])
        suffix = f": {detail}" if detail else ""
        return False, f"protected upstream config mutation detected and restored{suffix}"
    if exec_result.get("exit_code") != 0:
        return False, f"exit {exec_result.get('exit_code')}"
    payload = exec_result.get("json") or {}
    if s.kind == "json":
        if payload.get("output", {}).get("response_text") or payload.get("response_text"):
            return True, "response_text present"
        return False, "schema-like JSON response missing response_text"
    if s.kind == "preflight":
        runtime = payload.get("runtime") if isinstance(payload, dict) else None
        if isinstance(runtime, dict) and runtime.get("preflight_only") is True:
            return True, "preflight payload reported"
        generated = exec_result.get("generated_files") or []
        staged_json = [path for path in generated if str(path).endswith(".json")]
        return (bool(staged_json), f"{len(staged_json)} staged JSON artifact(s)")
    if s.kind == "finetune":
        if payload.get("output", {}).get("finetuned_ckpt_exists") is True:
            return True, "checkpoint reported"
        ckpts = list(out_dir.rglob("*.pt")) + list(out_dir.rglob("*.pth"))
        return (bool(ckpts), f"{len(ckpts)} checkpoint candidates")
    if s.kind == "segmentation":
        output = payload.get("output") if isinstance(payload, dict) else None
        if isinstance(output, dict) and output.get("label_set_valid") is False:
            requested = output.get("label_prompts_requested")
            unexpected = output.get("unexpected_label_ids")
            return False, f"label set invalid; requested={requested}; unexpected={unexpected}"
    if s.kind == "ct_pair":
        pairs = _ct_pair_candidates(out_dir)
        if not pairs:
            return False, "missing image/label NIfTI pair"
        image_path, label_path = pairs[-1]
        ok_img, why_img = _load_nifti(image_path)
        ok_lbl, why_lbl = _load_nifti(label_path)
        return ok_img and ok_lbl, f"image {why_img}; label {why_lbl}"
    nifti = sorted(out_dir.rglob("*.nii")) + sorted(out_dir.rglob("*.nii.gz"))
    if not nifti:
        return False, "no NIfTI outputs found"
    ok_n, why_n = _load_nifti(nifti[-1])
    return ok_n, why_n


def _tier3_pass(s: Scenario, cmd_text: str, exec_result: dict[str, Any]) -> bool:
    if s.skill == "nv_segment_ct":
        expected_labels = {1, 3, 5, 14}
        payload = exec_result.get("json") or {}
        output = payload.get("output") if isinstance(payload, dict) else None
        requested = output.get("label_prompts_requested") if isinstance(output, dict) else None
        if isinstance(requested, list):
            return set(requested) == expected_labels
        return all(re.search(rf"(?<!\d){label}(?!\d)", cmd_text) for label in expected_labels)
    if s.skill == "nv_generate_ct_rflow":
        payload = exec_result.get("json") or {}
        input_payload = payload.get("input") if isinstance(payload, dict) else None
        if isinstance(input_payload, dict):
            version = input_payload.get("version")
            anatomies = input_payload.get("anatomy_list_requested") or []
            regions = input_payload.get("body_region_requested") or []
            if (
                version == "rflow-ct"
                and any(str(item).lower() == "lung tumor" for item in anatomies)
                and any(str(item).lower() == "chest" for item in regions)
            ):
                return True
        return any(m in cmd_text for m in s.tier3)
    return any(m in cmd_text for m in s.tier3)


def _score(s: Scenario, cmd: str | None, out_dir: Path, exec_result: dict[str, Any]) -> dict[str, Any]:
    cmd_text = cmd or ""
    rel_input = str(_staged_input_path(s).relative_to(REPO_ROOT))
    abs_input = str(_staged_input_path(s))
    tiers: list[dict[str, Any]] = []
    tiers.append({"tier": 1, "pass": any(m in cmd_text for m in s.tier1), "reason": "entrypoint marker"})
    tiers.append(
        {
            "tier": 2,
            "pass": rel_input in cmd_text or abs_input in cmd_text,
            "reason": "user input path marker",
        }
    )
    tiers.append({"tier": 3, "pass": _tier3_pass(s, cmd_text, exec_result), "reason": "model/modality/control marker"})
    rel_out = str(out_dir.relative_to(REPO_ROOT))
    tiers.append({"tier": 4, "pass": rel_out in cmd_text or str(out_dir) in cmd_text, "reason": "output dir marker"})
    verified, why = _verify_outputs(s, out_dir, exec_result)
    tiers.append({"tier": 5, "pass": verified, "reason": why})
    return {
        "score": sum(1 for t in tiers if t["pass"]),
        "tiers": tiers,
        "passed": all(t["pass"] for t in tiers),
    }


def _feedback(score: dict[str, Any], exec_result: dict[str, Any], *, scenario: Scenario, arm: str) -> str:
    failed = [t for t in score["tiers"] if not t["pass"]]
    detail = {
        "failed_tiers": failed,
        "exit_code": exec_result.get("exit_code"),
        "not_executed_reason": exec_result.get("reason"),
        "upstream_mutation_detected": exec_result.get("upstream_mutation_detected", False),
        "upstream_mutation_paths": exec_result.get("upstream_mutation_paths", [])[:20],
        "generated_files": exec_result.get("generated_files", [])[:40],
        "stderr_tail": exec_result.get("stderr_tail", "")[-1500:],
        "stdout_tail": exec_result.get("stdout_tail", "")[-800:],
    }
    detail = _sanitize_feedback_detail(detail, scenario, arm)
    return (
        "The previous command did not pass verification. "
        "Use only the failure details below to repair the bash command. "
        "Return a replacement single bash code block.\n"
        + json.dumps(detail, indent=2)
    )


def _failure_analysis(
    scenario: Scenario,
    command: str | None,
    score: dict[str, Any],
    exec_result: dict[str, Any],
) -> list[dict[str, Any]]:
    """Human-readable failure reasons saved with every attempt."""
    if score.get("passed"):
        return []

    reasons: list[dict[str, Any]] = []
    if not command:
        reasons.append(
            {
                "kind": "no_command",
                "reason": "No executable bash command was extracted from the model response.",
                "repair_hint": "Return exactly one fenced bash block containing the command to run.",
            }
        )

    for tier in score.get("tiers", []):
        if tier.get("pass"):
            continue
        tier_id = tier.get("tier")
        hint = {
            1: "Use the runnable surface documented for this arm.",
            2: "Use the staged user input path under runs/with_vs_without_nv/_inputs/.",
            3: "Choose the model, modality, labels, anatomy controls, or smoke mode required by the task.",
            4: "Write outputs under the exact arm-specific output directory.",
            5: "Make the command execute cleanly and produce verifier-accepted artifacts.",
        }.get(tier_id, "Repair the failed deterministic check.")
        reasons.append(
            {
                "kind": f"tier_{tier_id}",
                "reason": tier.get("reason"),
                "repair_hint": hint,
            }
        )

    if exec_result.get("executed") is False:
        reasons.append(
            {
                "kind": "not_executed",
                "reason": exec_result.get("reason"),
                "repair_hint": "Remove unsafe shell fragments and keep the command within the documented workflow surface.",
            }
        )
    elif exec_result.get("upstream_mutation_detected"):
        reasons.append(
            {
                "kind": "isolation_violation",
                "reason": "Command mutated protected upstream config files; the harness restored them after execution.",
                "upstream_mutation_paths": exec_result.get("upstream_mutation_paths", [])[:20],
                "repair_hint": "Do not copy, redirect, or edit files under .workbench_data/upstreams or $NV_*_ROOT; stage edited runtime files under the repeat output directory.",
            }
        )
    elif exec_result.get("exit_code") not in (None, 0):
        reasons.append(
            {
                "kind": "nonzero_exit",
                "reason": f"Command exited {exec_result.get('exit_code')}.",
                "stderr_tail": (exec_result.get("stderr_tail") or "")[-1800:],
                "stdout_tail": (exec_result.get("stdout_tail") or "")[-800:],
                "repair_hint": "Use stderr/stdout to repair setup, paths, arguments, or runtime package installation.",
            }
        )
    else:
        failed_t5 = [t for t in score.get("tiers", []) if t.get("tier") == 5 and not t.get("pass")]
        if failed_t5:
            reasons.append(
                {
                    "kind": "artifact_verification",
                    "reason": failed_t5[0].get("reason"),
                    "generated_files": exec_result.get("generated_files", [])[:40],
                    "repair_hint": "Adjust the command so it produces the expected output files and schema for the task.",
                }
            )

    return reasons


def _run_attempt(
    *,
    scenario: Scenario,
    backend: Backend,
    arm: str,
    out_dir: Path,
    messages: list[dict[str, str]],
) -> dict[str, Any]:
    text, usage = _chat(backend, messages)
    cmd = _extract_command(text)
    exec_result = _execute(scenario, arm, cmd, out_dir)
    score = _score(scenario, cmd, out_dir, exec_result)
    return {
        "backend": backend.key,
        "model": backend.model,
        "backend_protocol": _backend_protocol(backend),
        "arm": arm,
        "messages": json.loads(json.dumps(messages)),
        "response": text,
        "command": cmd,
        "usage": usage,
        "execution": exec_result,
        "score": score,
        "failure_analysis": _failure_analysis(scenario, cmd, score, exec_result),
    }


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            _sanitize_artifact(obj),
            indent=2,
            default=lambda value: _sanitize_text(str(value)),
        )
        + "\n"
    )


def _write_compact_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            _sanitize_artifact(obj),
            separators=(",", ":"),
            default=lambda value: _sanitize_text(str(value)),
        )
        + "\n"
    )


def _sanitize_artifact(obj: Any) -> Any:
    """Remove machine-local absolute paths before writing public study artifacts."""
    if isinstance(obj, dict):
        return {key: _sanitize_artifact(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_artifact(value) for value in obj]
    if isinstance(obj, tuple):
        return tuple(_sanitize_artifact(value) for value in obj)
    if isinstance(obj, Path):
        return _sanitize_text(str(obj))
    if isinstance(obj, str):
        return _sanitize_text(obj)
    return obj


def _sanitize_text(text: str) -> str:
    repo = str(REPO_ROOT)
    home = str(Path.home())
    if repo:
        text = text.replace(repo + "/", "")
        text = text.replace(repo, ".")
    if home:
        text = text.replace(home + "/", "<HOME>/")
        text = text.replace(home, "<HOME>")
    return text


def _comparison_markdown(title: str, rows: list[dict[str, Any]]) -> str:
    lines = [
        f"# {title}",
        "",
        "| Backend | Arm | Repeats | Passes | Mean score | Steps |",
        "|---|---|---:|---:|---:|---|",
    ]
    for r in rows:
        if "repeats" in r:
            summary = r["summary"]
            step_summary = summary["steps_to_pass"]
            if step_summary["resolved_count"]:
                steps = (
                    f"mean {step_summary['mean_resolved']:.1f}; "
                    f"unresolved {step_summary['unresolved_count']}"
                )
            else:
                steps = "all unresolved"
            lines.append(
                f"| {r.get('backend_label', r['backend'])} | {r['arm']} | "
                f"{r['repeat_count']} | {summary['pass_count']} | "
                f"{summary['mean_score']:.1f}/5 | {steps} |"
            )
            continue
        score = r["score"]
        steps = r.get("steps_to_pass", 0)
        if isinstance(steps, float) and math.isinf(steps):
            steps = "unresolved"
        lines.append(
            f"| {r.get('backend_label', r['backend'])} | {r['arm']} | 1 | "
            f"{int(score['passed'])} | {score['score']}/5 | {steps} |"
        )
    return "\n".join(lines) + "\n"


def _write_md(path: Path, title: str, rows: list[dict[str, Any]]) -> None:
    path.write_text(_comparison_markdown(title, rows))


def _prompt_artifact_records(
    skill: str,
    prompt_style: str,
    *,
    max_steps: int,
    repeats: int,
) -> list[dict[str, Any]]:
    s = SCENARIOS[skill]
    records: list[dict[str, Any]] = []
    if max_steps:
        repair_prompt = (
            "After each failed execution, the next prompt receives only failed "
            "tier names, exit code, generated files, and stdout/stderr tails, "
            "then asks for a replacement single bash code block. Local home "
            "paths and hidden Medical AI Skills skill markers are redacted before "
            "feedback is sent."
        )
    else:
        repair_prompt = (
            "Repair prompts are disabled for the baseline comparison. Failed "
            "first commands are recorded as pass/fail outcomes with deterministic "
            "failure analysis."
        )
    plan = [
        ("codex-opus", "codex_opus", (BACKENDS["gpt55"], BACKENDS["opus"])),
        ("nemotron-correction", "nemotron_correction", (BACKENDS["nemotron"],)),
    ]
    for mode, run_mode, backends in plan:
        for backend in backends:
            for arm in ("with", "without"):
                for repeat in range(1, repeats + 1):
                    out_dir = _repeat_out_dir(skill, run_mode, backend, arm, repeat)
                    records.append(
                        {
                            "id": f"{skill}_{mode}_{backend.key}_{arm}_repeat_{repeat}",
                            "skill": skill,
                            "mode": mode,
                            "backend": backend.key,
                            "backend_label": backend.label,
                            "backend_model": backend.model,
                            "backend_protocol": _backend_protocol(backend),
                            "arm": arm,
                            "repeat": repeat,
                            "prompt_style": prompt_style,
                            "system": DIRECT_SYSTEM_PROMPT,
                            "question": _prompt(s, arm, out_dir, prompt_style),
                            "answer": PROMPT_ARTIFACT_ANSWER,
                            "prompt_source": f"tools/with_vs_without/run_nv_model_studies.py::_{prompt_style}_prompt",
                            "runner": "tools/with_vs_without/run_nv_model_studies.py",
                            "expected_output_dir": str(out_dir.relative_to(REPO_ROOT)),
                            "staged_user_input": str(_staged_input_path(s).relative_to(REPO_ROOT)),
                            "source_fixture_used_only_for_staging": s.fixture,
                            "documentation_arm": list(s.with_doc if arm == "with" else s.without_doc),
                            "documentation": _documentation_records(s.with_doc if arm == "with" else s.without_doc),
                            "correction_budget_steps": max_steps,
                            "repeat_count": repeats,
                            "repair_prompt": repair_prompt,
                        }
                    )
    return records


def write_prompt_artifacts(
    skills: list[str],
    prompt_style: str,
    out_dir: Path,
    *,
    max_steps: int,
    repeats: int,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for skill in skills:
        path = out_dir / f"eval_nv_model_studies_{skill}_prompts.json"
        _write_compact_json(
            path,
            _prompt_artifact_records(
                skill,
                prompt_style,
                max_steps=max_steps,
                repeats=repeats,
            ),
        )


def _path_like(value: str) -> bool:
    return "/" in value or value.startswith(".") or value.startswith("~")


def _expected_skill_doc(skill: str) -> str:
    return f"skills/{skill.replace('_', '-')}/SKILL.md"


def _scenario_contract_errors(skill: str, scenario: Scenario) -> list[str]:
    errors: list[str] = []
    missing_placeholders = [
        placeholder
        for placeholder in ("{input_path}", "{out_dir}")
        if placeholder not in scenario.user_goal
    ]
    if missing_placeholders:
        errors.append(
            f"{skill}: user_goal is missing required placeholder(s): "
            + ", ".join(missing_placeholders)
        )
    expected_with_doc = _expected_skill_doc(skill)
    if scenario.with_doc != (expected_with_doc,):
        errors.append(
            f"{skill}: with_doc must be exactly ({expected_with_doc!r},), "
            f"got {scenario.with_doc!r}"
        )
    if not (
        len(scenario.without_doc) == 1
        and scenario.without_doc[0].startswith("tools/with_vs_without/upstream_docs/")
    ):
        errors.append(
            f"{skill}: without_doc must be exactly one repo-local upstream "
            "snapshot under tools/with_vs_without/upstream_docs/"
        )
    return errors


def _fixture_ready(path: Path) -> bool:
    if path.is_file():
        return path.stat().st_size > 0
    if path.is_dir():
        return any(child.is_file() for child in path.rglob("*"))
    return False


def _backends_for_cli_mode(mode: str) -> tuple[Backend, ...]:
    if mode == "codex-opus":
        return (BACKENDS["gpt55"], BACKENDS["opus"])
    if mode == "nemotron":
        return (BACKENDS["nemotron"],)
    if mode == "all":
        return (BACKENDS["gpt55"], BACKENDS["opus"], BACKENDS["nemotron"])
    return ()


def _direct_run_preflight_errors(
    *,
    skills: list[str],
    mode: str,
    repeats: int,
    max_steps: int,
    prompt_artifact_dir: Path,
) -> list[str]:
    errors: list[str] = []
    if shutil.which("bash") is None:
        errors.append("bash is required for guarded command execution")
    for backend in _backends_for_cli_mode(mode):
        try:
            _read_env_value(backend.env_var)
        except RuntimeError as exc:
            errors.append(str(exc))

    for skill in skills:
        scenario = SCENARIOS[skill]
        errors.extend(_scenario_contract_errors(skill, scenario))
        fixture = REPO_ROOT / scenario.fixture
        if not _fixture_ready(fixture):
            errors.append(f"{skill}: fixture is missing or empty: {scenario.fixture}")
        for doc in scenario.with_doc + scenario.without_doc:
            path = REPO_ROOT / doc
            if not path.is_file() or path.stat().st_size <= 0:
                errors.append(f"{skill}: selected documentation is missing or empty: {doc}")
        for key, value in (scenario.env or {}).items():
            if not _path_like(value):
                continue
            path = Path(value).expanduser()
            if not path.exists():
                errors.append(f"{skill}: runtime cache for {key} is missing: {value}")

        prompt_path = prompt_artifact_dir / f"eval_nv_model_studies_{skill}_prompts.json"
        if not prompt_path.is_file():
            try:
                prompt_path_text = str(prompt_path.relative_to(REPO_ROOT))
            except ValueError:
                prompt_path_text = str(prompt_path)
            errors.append(f"{skill}: prompt artifact is missing: {prompt_path_text}")
            continue
        try:
            current = json.loads(prompt_path.read_text())
        except json.JSONDecodeError as exc:
            errors.append(f"{skill}: prompt artifact is invalid JSON: {exc}")
            continue
        expected = _sanitize_artifact(
            _prompt_artifact_records(
                skill,
                "path",
                max_steps=max_steps,
                repeats=repeats,
            )
        )
        if current != expected:
            errors.append(
                f"{skill}: prompt artifact is stale; regenerate with "
                "python tools/with_vs_without/run_nv_model_studies.py "
                f"--skills {skill} --mode prompts --prompt-style path --repeats {repeats}"
            )
    return errors


def _run_repair_loop(
    *,
    scenario: Scenario,
    backend: Backend,
    arm: str,
    out_dir: Path,
    prompt_style: str,
    max_steps: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    messages = [
        {"role": "system", "content": DIRECT_SYSTEM_PROMPT},
        {"role": "user", "content": _prompt(scenario, arm, out_dir, prompt_style)},
    ]
    attempts: list[dict[str, Any]] = []
    for step in range(max_steps + 1):
        result = _run_attempt(scenario=scenario, backend=backend, arm=arm, out_dir=out_dir, messages=messages)
        # Keep the saved transcript and the next repair prompt in the same
        # sanitized coordinate system. Otherwise long stderr/stdout tails can
        # cross a different truncation boundary after path redaction.
        result = _sanitize_artifact(result)
        result["step"] = step
        attempts.append(result)
        if result["score"]["passed"]:
            break
        messages.append({"role": "assistant", "content": result["response"]})
        messages.append({
            "role": "user",
            "content": _feedback(result["score"], result["execution"], scenario=scenario, arm=arm),
        })

    final = dict(attempts[-1])
    final["backend_label"] = backend.label
    final["attempts"] = attempts
    final["steps_to_pass"] = next((a["step"] for a in attempts if a["score"]["passed"]), math.inf)
    final["max_correction_steps"] = max_steps
    return attempts, final


def _steps_to_pass(result: dict[str, Any]) -> int | float:
    return result.get("steps_to_pass", math.inf)


def _steps_summary(repeats: list[dict[str, Any]]) -> dict[str, Any]:
    resolved = [
        int(_steps_to_pass(r))
        for r in repeats
        if not (isinstance(_steps_to_pass(r), float) and math.isinf(_steps_to_pass(r)))
    ]
    return {
        "resolved_count": len(resolved),
        "unresolved_count": len(repeats) - len(resolved),
        "mean_resolved": (sum(resolved) / len(resolved)) if resolved else None,
        "min_resolved": min(resolved) if resolved else None,
        "max_resolved": max(resolved) if resolved else None,
        "values": [
            ("unresolved" if isinstance(_steps_to_pass(r), float) and math.isinf(_steps_to_pass(r)) else int(_steps_to_pass(r)))
            for r in repeats
        ],
    }


def _aggregate_repeats(
    *,
    backend: Backend,
    arm: str,
    skill: str,
    mode: str,
    repeats: list[dict[str, Any]],
    max_steps: int,
    prompt_style: str,
) -> dict[str, Any]:
    scores = [r["score"]["score"] for r in repeats]
    pass_count = sum(1 for r in repeats if r["score"]["passed"])
    return {
        "backend": backend.key,
        "backend_label": backend.label,
        "model": backend.model,
        "backend_protocol": _backend_protocol(backend),
        "arm": arm,
        "skill": skill,
        "mode": mode,
        "repeat_count": len(repeats),
        "max_correction_steps": max_steps,
        "prompt_style": prompt_style,
        "clean_environment": {
            "per_repeat_output_dir": True,
            "per_attempt_fresh_venv": True,
            "python_user_site_disabled": True,
            "host_pythonpath_removed": True,
            "output_dir_cleaned_before_each_attempt": True,
            "dependency_and_model_caches_may_be_shared": True,
            "shared_cache_root": str(CACHE_ROOT.relative_to(REPO_ROOT)),
            "shared_cache_env": _shared_cache_env_records(),
        },
        "summary": {
            "pass_count": pass_count,
            "fail_count": len(repeats) - pass_count,
            "mean_score": (sum(scores) / len(scores)) if scores else None,
            "scores": scores,
            "steps_to_pass": _steps_summary(repeats),
        },
        "repeats": repeats,
    }


def _repeat_out_dir(skill: str, mode: str, backend: Backend, arm: str, repeat: int) -> Path:
    if mode == "codex_opus":
        return RUN_ROOT / f"{skill}_codex_opus" / backend.key / arm / f"repeat_{repeat}"
    return RUN_ROOT / f"{skill}_nemotron_correction" / arm / f"repeat_{repeat}"


def _repeat_artifact_path(study: Path, mode: str, backend: Backend, arm: str, repeat: int) -> Path:
    if mode == "codex_opus":
        return study / "repeats" / f"{backend.key}_{arm}_repeat_{repeat}.json"
    return study / "repeats" / f"{arm}_repeat_{repeat}.json"


def _scores_match(left: Any, right: Any) -> bool:
    return (
        isinstance(left, dict)
        and isinstance(right, dict)
        and left.get("passed") == right.get("passed")
        and left.get("score") == right.get("score")
    )


def _steps_unresolved(value: Any) -> bool:
    return value == "unresolved" or (isinstance(value, float) and math.isinf(value))


def _repeat_trace_is_current(
    data: dict[str, Any],
    *,
    scenario: Scenario,
    skill: str,
    mode: str,
    backend: Backend,
    arm: str,
    repeat: int,
    prompt_style: str,
    max_steps: int,
) -> bool:
    attempts = data.get("attempts")
    if not isinstance(attempts, list) or not attempts or len(attempts) > max_steps + 1:
        return False
    actual_steps = [attempt.get("step") if isinstance(attempt, dict) else None for attempt in attempts]
    if actual_steps != list(range(len(attempts))):
        return False

    expected_out_dir = _repeat_out_dir(skill, mode, backend, arm, repeat)
    expected_user = _prompt(scenario, arm, expected_out_dir, prompt_style)
    for index, attempt in enumerate(attempts):
        if not isinstance(attempt, dict):
            return False
        if attempt.get("backend") != backend.key or attempt.get("arm") != arm:
            return False
        if attempt.get("model") != backend.model:
            return False
        if attempt.get("backend_protocol") != _backend_protocol(backend):
            return False
        if "command" not in attempt or not isinstance(attempt.get("score"), dict):
            return False
        if not isinstance(attempt.get("response"), str):
            return False
        if attempt.get("command") != _extract_command(attempt["response"]):
            return False
        if not isinstance(attempt.get("usage"), dict):
            return False
        if not isinstance(attempt.get("execution"), dict):
            return False
        safe, reason = _safe_to_execute(scenario, arm, attempt.get("command"), expected_out_dir)
        if not safe:
            if attempt["execution"].get("executed") is not False:
                return False
            if attempt["execution"].get("reason") != reason:
                return False
        elif attempt["execution"].get("executed") is False:
            return False
        messages = attempt.get("messages")
        if not isinstance(messages, list) or len(messages) != 2 + 2 * index:
            return False
        roles = [msg.get("role") if isinstance(msg, dict) else None for msg in messages]
        if roles != ["system", "user"] + ["assistant", "user"] * index:
            return False
        if index == 0:
            system_msg, user_msg = messages[0], messages[1]
            if not isinstance(system_msg, dict) or not isinstance(user_msg, dict):
                return False
            if system_msg.get("content") != DIRECT_SYSTEM_PROMPT:
                return False
            if user_msg.get("content") != expected_user:
                return False
            continue

        previous_attempt = attempts[index - 1]
        previous_response = previous_attempt.get("response") if isinstance(previous_attempt, dict) else None
        assistant_msg = messages[-2] if len(messages) >= 2 else None
        if not isinstance(previous_response, str):
            return False
        if not isinstance(assistant_msg, dict) or assistant_msg.get("content") != previous_response:
            return False
        last_msg = messages[-1] if messages else None
        if not isinstance(last_msg, dict) or last_msg.get("role") != "user":
            return False
        previous_score = previous_attempt.get("score") if isinstance(previous_attempt, dict) else None
        previous_execution = previous_attempt.get("execution") if isinstance(previous_attempt, dict) else None
        if not isinstance(previous_score, dict) or not isinstance(previous_execution, dict):
            return False
        try:
            expected_feedback = _feedback(previous_score, previous_execution, scenario=scenario, arm=arm)
        except Exception:  # noqa: BLE001
            return False
        if last_msg.get("content") != expected_feedback:
            return False
        content = str(last_msg.get("content") or "")
        required_fragments = (
            "The previous command did not pass verification",
            "failed_tiers",
            "exit_code",
            "stderr_tail",
            "stdout_tail",
            "replacement single bash code block",
        )
        if any(fragment not in content for fragment in required_fragments):
            return False
        if LOCAL_HOME_PATH_RE.search(content):
            return False
        if any(marker and marker in content for marker in _repair_feedback_forbidden_markers(scenario, arm)):
            return False

    final_attempt = attempts[-1]
    if not isinstance(final_attempt, dict):
        return False
    if not _scores_match(data.get("score"), final_attempt.get("score")):
        return False
    if data.get("command") != final_attempt.get("command"):
        return False
    if data.get("execution") != final_attempt.get("execution"):
        return False

    pass_steps = [
        attempt.get("step")
        for attempt in attempts
        if isinstance(attempt, dict)
        and isinstance(attempt.get("score"), dict)
        and attempt["score"].get("passed") is True
    ]
    steps_to_pass = data.get("steps_to_pass")
    if pass_steps:
        return steps_to_pass == min(pass_steps)
    return _steps_unresolved(steps_to_pass)


def _load_existing_repeat(
    path: Path,
    *,
    skill: str,
    mode: str,
    backend: Backend,
    arm: str,
    repeat: int,
    prompt_style: str,
    max_steps: int,
) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    expected_out_dir = str(_repeat_out_dir(skill, mode, backend, arm, repeat).relative_to(REPO_ROOT))
    if data.get("backend") != backend.key:
        return None
    if data.get("backend_label") != backend.label:
        return None
    if data.get("model") != backend.model:
        return None
    if data.get("backend_protocol") != _backend_protocol(backend):
        return None
    if data.get("arm") != arm:
        return None
    if data.get("repeat") != repeat:
        return None
    if data.get("output_dir") != expected_out_dir:
        return None
    if data.get("prompt_style") != prompt_style:
        return None
    if data.get("max_correction_steps") != max_steps:
        return None
    expected_input = str(_staged_input_path(SCENARIOS[skill]).relative_to(REPO_ROOT))
    if data.get("staged_user_input") != expected_input:
        return None
    if not isinstance(data.get("score"), dict):
        return None
    if not _repeat_trace_is_current(
        data,
        scenario=SCENARIOS[skill],
        skill=skill,
        mode=mode,
        backend=backend,
        arm=arm,
        repeat=repeat,
        prompt_style=prompt_style,
        max_steps=max_steps,
    ):
        return None
    return data


def _load_or_run_repeat(
    *,
    scenario: Scenario,
    skill: str,
    study: Path,
    mode: str,
    backend: Backend,
    arm: str,
    repeat: int,
    repeats: int,
    prompt_style: str,
    max_steps: int,
    resume_missing: bool,
) -> dict[str, Any]:
    repeat_path = _repeat_artifact_path(study, mode, backend, arm, repeat)
    if resume_missing:
        existing = _load_existing_repeat(
            repeat_path,
            skill=skill,
            mode=mode,
            backend=backend,
            arm=arm,
            repeat=repeat,
            prompt_style=prompt_style,
            max_steps=max_steps,
        )
        if existing is not None:
            print(
                f"[with-vs-without] reuse {mode} {skill} {backend.key} {arm} repeat={repeat}/{repeats}",
                file=sys.stderr,
                flush=True,
            )
            return existing

    out_dir = _repeat_out_dir(skill, mode, backend, arm, repeat)
    print(
        f"[with-vs-without] run {mode} {skill} {backend.key} {arm} repeat={repeat}/{repeats}",
        file=sys.stderr,
        flush=True,
    )
    _attempts, result = _run_repair_loop(
        scenario=scenario,
        backend=backend,
        arm=arm,
        out_dir=out_dir,
        prompt_style=prompt_style,
        max_steps=max_steps,
    )
    result["repeat"] = repeat
    result["output_dir"] = str(out_dir.relative_to(REPO_ROOT))
    result["staged_user_input"] = str(_staged_input_path(scenario).relative_to(REPO_ROOT))
    result["prompt_style"] = prompt_style
    _write_json(repeat_path, result)
    return result


def run_codex_opus(
    skills: list[str],
    prompt_style: str,
    max_steps: int,
    repeats: int,
    *,
    resume_missing: bool = False,
) -> None:
    backends = [BACKENDS["gpt55"], BACKENDS["opus"]]
    for skill in skills:
        s = SCENARIOS[skill]
        study = STUDY_ROOT / f"{skill}_codex_opus"
        rows: list[dict[str, Any]] = []
        for backend in backends:
            for arm in ("with", "without"):
                repeat_results: list[dict[str, Any]] = []
                for repeat in range(1, repeats + 1):
                    result = _load_or_run_repeat(
                        scenario=s,
                        skill=skill,
                        study=study,
                        mode="codex_opus",
                        backend=backend,
                        arm=arm,
                        repeat=repeat,
                        repeats=repeats,
                        prompt_style=prompt_style,
                        max_steps=max_steps,
                        resume_missing=resume_missing,
                    )
                    repeat_results.append(result)
                aggregate = _aggregate_repeats(
                    backend=backend,
                    arm=arm,
                    skill=skill,
                    mode="codex-opus",
                    repeats=repeat_results,
                    max_steps=max_steps,
                    prompt_style=prompt_style,
                )
                rows.append(aggregate)
                _write_json(study / f"{backend.key}_{arm}.json", aggregate)
        _write_md(study / "comparison.md", f"{skill}: Codex/Opus with-vs-without", rows)


def run_nemotron(
    skills: list[str],
    max_steps: int,
    prompt_style: str,
    repeats: int,
    *,
    resume_missing: bool = False,
) -> None:
    backend = BACKENDS["nemotron"]
    for skill in skills:
        s = SCENARIOS[skill]
        study = STUDY_ROOT / f"{skill}_nemotron_correction"
        rows: list[dict[str, Any]] = []
        for arm in ("with", "without"):
            repeat_results: list[dict[str, Any]] = []
            for repeat in range(1, repeats + 1):
                result = _load_or_run_repeat(
                    scenario=s,
                    skill=skill,
                    study=study,
                    mode="nemotron_correction",
                    backend=backend,
                    arm=arm,
                    repeat=repeat,
                    repeats=repeats,
                    prompt_style=prompt_style,
                    max_steps=max_steps,
                    resume_missing=resume_missing,
                )
                repeat_results.append(result)
            aggregate = _aggregate_repeats(
                backend=backend,
                arm=arm,
                skill=skill,
                mode="nemotron-correction",
                repeats=repeat_results,
                max_steps=max_steps,
                prompt_style=prompt_style,
            )
            rows.append(aggregate)
            _write_json(study / f"{arm}.json", aggregate)
        _write_md(study / "comparison.md", f"{skill}: Nemotron baseline study", rows)


def run_all_interleaved(
    skills: list[str],
    prompt_style: str,
    max_steps: int,
    repeats: int,
    *,
    resume_missing: bool = False,
) -> None:
    codex_backends = (BACKENDS["gpt55"], BACKENDS["opus"])
    nemotron_backend = BACKENDS["nemotron"]
    backend_plan = (*codex_backends, nemotron_backend)
    for skill in skills:
        s = SCENARIOS[skill]
        codex_study = STUDY_ROOT / f"{skill}_codex_opus"
        nemotron_study = STUDY_ROOT / f"{skill}_nemotron_correction"
        codex_results: dict[tuple[str, str], list[dict[str, Any]]] = {
            (backend.key, arm): []
            for backend in codex_backends
            for arm in ("with", "without")
        }
        nemotron_results: dict[str, list[dict[str, Any]]] = {
            "with": [],
            "without": [],
        }

        for repeat in range(1, repeats + 1):
            for arm in ("with", "without"):
                for backend in backend_plan:
                    if backend.key == nemotron_backend.key:
                        study = nemotron_study
                        mode = "nemotron_correction"
                        target_results = nemotron_results[arm]
                    else:
                        study = codex_study
                        mode = "codex_opus"
                        target_results = codex_results[(backend.key, arm)]
                    result = _load_or_run_repeat(
                        scenario=s,
                        skill=skill,
                        study=study,
                        mode=mode,
                        backend=backend,
                        arm=arm,
                        repeat=repeat,
                        repeats=repeats,
                        prompt_style=prompt_style,
                        max_steps=max_steps,
                        resume_missing=resume_missing,
                    )
                    target_results.append(result)

        codex_rows: list[dict[str, Any]] = []
        for backend in codex_backends:
            for arm in ("with", "without"):
                aggregate = _aggregate_repeats(
                    backend=backend,
                    arm=arm,
                    skill=skill,
                    mode="codex-opus",
                    repeats=codex_results[(backend.key, arm)],
                    max_steps=max_steps,
                    prompt_style=prompt_style,
                )
                codex_rows.append(aggregate)
                _write_json(codex_study / f"{backend.key}_{arm}.json", aggregate)
        _write_md(codex_study / "comparison.md", f"{skill}: Codex/Opus with-vs-without", codex_rows)

        nemotron_rows: list[dict[str, Any]] = []
        for arm in ("with", "without"):
            aggregate = _aggregate_repeats(
                backend=nemotron_backend,
                arm=arm,
                skill=skill,
                mode="nemotron-correction",
                repeats=nemotron_results[arm],
                max_steps=max_steps,
                prompt_style=prompt_style,
            )
            nemotron_rows.append(aggregate)
            _write_json(nemotron_study / f"{arm}.json", aggregate)
        _write_md(nemotron_study / "comparison.md", f"{skill}: Nemotron baseline study", nemotron_rows)


def main(argv: list[str] | None = None) -> None:
    global RUN_ROOT, STUDY_ROOT

    parser = argparse.ArgumentParser()
    parser.add_argument("--skills", nargs="*", default=sorted(SCENARIOS), choices=sorted(SCENARIOS))
    parser.add_argument("--mode", choices=["codex-opus", "nemotron", "all", "prompts"], default="all")
    parser.add_argument("--max-correction-steps", type=int, default=DIRECT_MAX_CORRECTION_STEPS)
    parser.add_argument(
        "--repeats",
        type=int,
        default=DIRECT_REPEATS,
        help="independent repeats per skill/backend/arm; each repeat gets its own output directory and fresh venvs",
    )
    parser.add_argument(
        "--prompt-style",
        choices=["path", "minimal", "guarded"],
        default="minimal",
        help=(
            "path writes A2-style prompts for tool-enabled agents to read docs by path; "
            "minimal embeds the arm-specific docs for direct chat APIs; guarded is the "
            "older evaluator-shaped prompt. Direct API modes run the same bounded "
            "correction loop for every backend and arm."
        ),
    )
    parser.add_argument(
        "--write-prompt-artifacts",
        action="store_true",
        help=(
            "write fair path prompt records under tools/nat_audit/data for "
            "NAT/tool-agent artifacts"
        ),
    )
    parser.add_argument(
        "--resume-missing",
        action="store_true",
        help=(
            "reuse valid per-repeat JSON artifacts and run only missing or invalid "
            "repeats before rebuilding aggregate JSON and comparison Markdown"
        ),
    )
    parser.add_argument(
        "--prompt-artifact-dir",
        type=Path,
        default=PROMPT_ARTIFACT_ROOT,
        help="directory for --write-prompt-artifacts",
    )
    parser.add_argument(
        "--study-root",
        type=Path,
        default=STUDY_ROOT,
        help="directory for compact study JSON/Markdown artifacts",
    )
    parser.add_argument(
        "--run-root",
        type=Path,
        default=RUN_ROOT,
        help="directory for generated run outputs and per-repeat execution environments",
    )
    parser.add_argument(
        EXTERNAL_LLM_DATA_TRANSFER_FLAG,
        action="store_true",
        help=(
            "Required for direct API modes. Confirms the operator has approved "
            "sending study prompts and fixture-derived task context to external LLM APIs."
        ),
    )
    parser.add_argument(
        "--skip-local-preflight",
        action="store_true",
        help=(
            "Developer/debug escape hatch for direct modes. Does not bypass "
            f"{EXTERNAL_LLM_DATA_TRANSFER_FLAG}."
        ),
    )
    parser.add_argument(
        "--allow-debug-budget",
        action="store_true",
        help=(
            "Developer/debug escape hatch for non-protocol direct runs with "
            "reduced repeats or correction steps. Artifacts from such runs are "
            "not strict-audit publishable."
        ),
    )
    args = parser.parse_args(argv)
    STUDY_ROOT = args.study_root
    RUN_ROOT = args.run_root
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")
    non_protocol_repeats = args.mode != "prompts" and args.repeats != DIRECT_REPEATS
    non_protocol_steps = args.max_correction_steps != DIRECT_MAX_CORRECTION_STEPS
    if non_protocol_repeats and not args.allow_debug_budget:
        parser.error(
            "current direct with-vs-without protocol requires "
            f"--repeats {DIRECT_REPEATS}; use --allow-debug-budget only for "
            "non-publishable diagnostic runs"
        )
    if non_protocol_steps and not args.allow_debug_budget:
        parser.error(
            "current with-vs-without protocol requires "
            f"--max-correction-steps {DIRECT_MAX_CORRECTION_STEPS}; use "
            "--allow-debug-budget only for non-publishable diagnostic runs"
        )
    if args.allow_debug_budget and args.mode != "prompts" and (non_protocol_repeats or non_protocol_steps):
        print(
            "[with-vs-without] debug budget enabled: artifacts from this run "
            "are diagnostic only and will not satisfy strict audit.",
            file=sys.stderr,
            flush=True,
        )
    if args.mode == "prompts" and args.prompt_style != "path":
        parser.error("--mode prompts writes fair NAT/tool-agent prompt artifacts and requires --prompt-style path.")
    if args.mode != "prompts" and args.prompt_style == "path":
        parser.error("--prompt-style path is only for prompt artifacts/tool-agent runs; use minimal for direct API runs.")
    if args.mode != "prompts" and args.prompt_style != "minimal":
        parser.error(
            "direct API study modes require --prompt-style minimal; "
            "legacy guarded prompts are not part of the current fair comparison protocol."
        )
    if args.mode != "prompts" and not args.confirm_external_llm_data_transfer:
        parser.error(
            EXTERNAL_LLM_DATA_TRANSFER_NOTICE
            + f" Re-run with {EXTERNAL_LLM_DATA_TRANSFER_FLAG} only after explicit approval."
        )
    if args.write_prompt_artifacts or args.mode == "prompts":
        write_prompt_artifacts(
            args.skills,
            "path",
            args.prompt_artifact_dir,
            max_steps=args.max_correction_steps,
            repeats=args.repeats,
        )
    if args.mode == "prompts":
        return
    if args.mode != "prompts" and not args.skip_local_preflight:
        preflight_errors = _direct_run_preflight_errors(
            skills=args.skills,
            mode=args.mode,
            repeats=args.repeats,
            max_steps=args.max_correction_steps,
            prompt_artifact_dir=args.prompt_artifact_dir,
        )
        if preflight_errors:
            parser.error(
                "local preflight failed before direct external LLM study run:\n  - "
                + "\n  - ".join(preflight_errors)
                + "\nRun `make preflight-with-vs-without` for the full readiness report."
            )
    for skill in args.skills:
        _stage_input(SCENARIOS[skill])
    if args.mode == "all":
        run_all_interleaved(
            args.skills,
            args.prompt_style,
            args.max_correction_steps,
            args.repeats,
            resume_missing=args.resume_missing,
        )
    elif args.mode == "codex-opus":
        run_codex_opus(
            args.skills,
            args.prompt_style,
            args.max_correction_steps,
            args.repeats,
            resume_missing=args.resume_missing,
        )
    elif args.mode == "nemotron":
        run_nemotron(
            args.skills,
            args.max_correction_steps,
            args.prompt_style,
            args.repeats,
            resume_missing=args.resume_missing,
        )


if __name__ == "__main__":
    main()
