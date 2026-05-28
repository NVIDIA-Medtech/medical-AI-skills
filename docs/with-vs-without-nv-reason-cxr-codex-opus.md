# `nv_reason_cxr`: Codex/Opus LLM+SKILL.md vs LLM+README

Status: strict audit passed for refreshed artifacts on May 27, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

This report compares `LLM + SKILL.md` with `LLM + upstream README/guide`. The completed direct-API run used the corrected embedded-doc minimal prompt because those backends cannot read repo files. The fair NAT/tool-agent prompt artifact is A2-style: it gives a natural user request, a neutral staged input path, an output directory, and tells the agent which arm-specific document to read. It does not spell out operational details such as entrypoints, labels, model variants, or config filenames outside the documentation arm.

## Experiment Question

Does `LLM + SKILL.md` make an agent better at reading documentation and taking the right action than `LLM + upstream README/guide`?

## User Request Shape

The prompt request for the GPT-5.5 with-skill arm was:

> The CXR request is at runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json. Run a command-shape smoke test for the CXR reasoning workflow and write structured JSON under runs/with_vs_without_nv/nv_reason_cxr_codex_opus/gpt55/with/repeat_1. Do not grade clinical correctness.

The staged user input for every arm was `runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json`. The source fixture `skills/nv-reason-cxr/fixtures/synthetic_cxr_input.json` was used only to stage that neutral input path.

Fair path-prompt artifact: `tools/nat_audit/data/eval_nv_model_studies_nv_reason_cxr_prompts.json`

## Result

| Backend | Arm | Mean score | Passes | Steps | Exit | Tier 5 | Failed tiers |
|---|---|---:|---:|---|---|---|---|
| GPT-5.5 / Codex | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | response_text present (3) | none |
| GPT-5.5 / Codex | without | 4.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | 0 (3) | schema-like JSON response missing response_text (3) | T5: schema-like JSON response missing response_text (3) |
| Opus 4.7 | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | response_text present (3) | none |
| Opus 4.7 | without | 4.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | 0 (3) | schema-like JSON response missing response_text (3) | T5: schema-like JSON response missing response_text (3) |

## Analysis

SKILL.md paired advantage: the with-skill arms passed 6/6 backend-repeat trials with an average score of 5.0/5; the README-only arms passed 0/6 backend-repeat trials with an average score of 4.0/5.

SKILL.md paired advantage: SKILL.md wins 6/6 matched backend-repeat pairs, README-only wins 0/6, and 0/6 are ties. Pass/fail is the primary outcome; score breaks ties only when pass status is equal. Exact one-sided sign-test p=0.01562 across 6 decisive pair(s).

Outcome-support gate: Supports SKILL.md advantage. SKILL.md wins 6/6 matched pair(s); README-only wins 0/6; sign-test p=0.01562.

Each backend/arm/skill configuration was repeated three times. A repeat is independent: it has its own output directory, and each execution attempt inside the repeat creates a fresh venv before running the generated command. Dependency and model download caches are shared only as documented test-environment caches under `.workbench_data/with_vs_without_cache` (`PIP_CACHE_DIR=.workbench_data/with_vs_without_cache/pip`, `HF_HOME=.workbench_data/with_vs_without_cache/huggingface`, `HF_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `HUGGINGFACE_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `TRANSFORMERS_CACHE=.workbench_data/with_vs_without_cache/huggingface/transformers`, `TORCH_HOME=.workbench_data/with_vs_without_cache/torch`, `XDG_CACHE_HOME=.workbench_data/with_vs_without_cache/xdg`, `CONDA_PKGS_DIRS=.workbench_data/with_vs_without_cache/conda_pkgs`, `UV_CACHE_DIR=.workbench_data/with_vs_without_cache/uv`, `CUDA_CACHE_PATH=.workbench_data/with_vs_without_cache/cuda`, `NUMBA_CACHE_DIR=.workbench_data/with_vs_without_cache/numba`).

The main baseline uses `max_correction_steps=0`: each repeat sends one prompt, executes the extracted command once, and records pass/fail, runtime, tokens, and deterministic failure analysis. The repair-loop implementation remains available for separate diagnostic experiments, but it is not part of this comparison.

All with-skill repeats exited successfully and produced artifacts accepted by the deterministic grader. That means the final SKILL.md surface was repeatable for both tested agent backends.

The README-only commands did not pass tier 5. Typical failure modes were unsafe generated shell cleanup, missing schema fields, missing model/control details, or upstream commands that did not execute cleanly from Medical AI Skills root.

Tier 2 is intentionally strict: a command only earns it if it uses the staged user input path `runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json`.

## Token Profiling

Token counts are provider-reported values saved in each repeat JSON. Reasoning tokens are shown only when the provider returned that subfield and are a subset of completion tokens, not an additional cost to add to total tokens. Execution time is averaged only across repeats that reached command execution; no-command-extracted repeats still count toward token totals.

| Backend | Arm | Repeats | Passes | Attempts | Prompt tokens | Completion tokens | Reasoning tokens | Total tokens | Mean total/repeat | Executed | Mean exec s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GPT-5.5 / Codex | with | 3 | 3 | 3 | 7,035 | 1,119 | 872 | 8,154 | 2,718.0 | 3 | 0.1 |
| GPT-5.5 / Codex | without | 3 | 0 | 3 | 10,413 | 11,114 | 5,497 | 21,527 | 7,175.7 | 3 | 0.0 |
| Opus 4.7 | with | 3 | 3 | 3 | 12,108 | 360 | 0 | 12,468 | 4,156.0 | 3 | 0.1 |
| Opus 4.7 | without | 3 | 0 | 3 | 16,857 | 3,331 | 0 | 20,188 | 6,729.3 | 3 | 0.0 |

## Repair Attempts and Failure Reasons

The tables below explain why each generated command failed and how many follow-up prompting steps were needed. For this baseline, only step 0 is sent; unresolved means the first command did not pass.

### GPT-5.5 / Codex, with arm

| Repeat | Step | Score | Passed | Exit | Failed tiers | Why it did not work |
|---:|---:|---:|---|---|---|---|
| 1 | 0 | 5/5 | yes | 0 | none | none |
| 2 | 0 | 5/5 | yes | 0 | none | none |
| 3 | 0 | 5/5 | yes | 0 | none | none |

### GPT-5.5 / Codex, without arm

| Repeat | Step | Score | Passed | Exit | Failed tiers | Why it did not work |
|---:|---:|---:|---|---|---|---|
| 1 | 0 | 4/5 | no | 0 | T5: schema-like JSON response missing response_text | tier_5: schema-like JSON response missing response_text Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>artifact_verification: schema-like JSON response missing response_text Repair: Adjust the command so it produces the expected output files and schema for the task. |
| 2 | 0 | 4/5 | no | 0 | T5: schema-like JSON response missing response_text | tier_5: schema-like JSON response missing response_text Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>artifact_verification: schema-like JSON response missing response_text Repair: Adjust the command so it produces the expected output files and schema for the task. |
| 3 | 0 | 4/5 | no | 0 | T5: schema-like JSON response missing response_text | tier_5: schema-like JSON response missing response_text Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>artifact_verification: schema-like JSON response missing response_text Repair: Adjust the command so it produces the expected output files and schema for the task. |

### Opus 4.7, with arm

| Repeat | Step | Score | Passed | Exit | Failed tiers | Why it did not work |
|---:|---:|---:|---|---|---|---|
| 1 | 0 | 5/5 | yes | 0 | none | none |
| 2 | 0 | 5/5 | yes | 0 | none | none |
| 3 | 0 | 5/5 | yes | 0 | none | none |

### Opus 4.7, without arm

| Repeat | Step | Score | Passed | Exit | Failed tiers | Why it did not work |
|---:|---:|---:|---|---|---|---|
| 1 | 0 | 4/5 | no | 0 | T5: schema-like JSON response missing response_text | tier_5: schema-like JSON response missing response_text Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>artifact_verification: schema-like JSON response missing response_text Repair: Adjust the command so it produces the expected output files and schema for the task. |
| 2 | 0 | 4/5 | no | 0 | T5: schema-like JSON response missing response_text | tier_5: schema-like JSON response missing response_text Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>artifact_verification: schema-like JSON response missing response_text Repair: Adjust the command so it produces the expected output files and schema for the task. |
| 3 | 0 | 4/5 | no | 0 | T5: schema-like JSON response missing response_text | tier_5: schema-like JSON response missing response_text Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>artifact_verification: schema-like JSON response missing response_text Repair: Adjust the command so it produces the expected output files and schema for the task. |

## Skill Fix Notes

Before the final rerun, `SKILL.md` was tightened to name `scripts/run_nv_reason_cxr.py` as the exact command-shape smoke-test surface and to reserve live model inference for explicit user requests.

## Generated Commands

These are the extracted first-attempt commands by repeat.

### GPT-5.5 / Codex, with arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
python skills/nv-reason-cxr/scripts/run_nv_reason_cxr.py runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json --mock --out-dir runs/with_vs_without_nv/nv_reason_cxr_codex_opus/gpt55/with/repeat_1
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
python skills/nv-reason-cxr/scripts/run_nv_reason_cxr.py runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json --mock --out-dir runs/with_vs_without_nv/nv_reason_cxr_codex_opus/gpt55/with/repeat_2
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
mkdir -p runs/with_vs_without_nv/nv_reason_cxr_codex_opus/gpt55/with/repeat_3 && python skills/nv-reason-cxr/scripts/run_nv_reason_cxr.py runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json --mock --out-dir runs/with_vs_without_nv/nv_reason_cxr_codex_opus/gpt55/with/repeat_3
```

### GPT-5.5 / Codex, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 4/5, passed=no, steps=unresolved, exit=0

```bash
mkdir -p runs/with_vs_without_nv/nv_reason_cxr_codex_opus/gpt55/without/repeat_1 && cat > runs/with_vs_without_nv/nv_reason_cxr_codex_opus/gpt55/without/repeat_1/nv_reason_cxr_command_shape_smoke.py <<'PY' && python runs/with_vs_without_nv/nv_reason_cxr_codex_opus/gpt55/without/repeat_1/nv_reason_cxr_command_shape_smoke.py --request runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json --output-json runs/with_vs_without_nv/nv_reason_cxr_codex_opus/gpt55/without/repeat_1/command_shape_smoke.json --dry-run
import argparse, datetime, hashlib, importlib.util, json, os, pathlib, sys

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def walk(obj, path="$"):
    yield path, obj
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, f"{path}[{i}]")

def is_image_like(s):
    return isinstance(s, str) and pathlib.Path(s).suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--request", required=True)
    ap.add_argument("--output-json", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    repo_root = pathlib.Path(".").resolve()
    req_path = pathlib.Path(args.request)
    out_path = pathlib.Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    checks = []
    request_obj = None
    if req_path.exists():
        request_obj = json.loads(req_path.read_text())
        checks.append({"name": "request_json_exists_and_parses", "status": "pass", "path": str(req_path)})
    else:
        checks.append({"name": "request_json_exists_and_parses", "status": "fail", "path": str(req_path)})

    image_candidates = []
    prompt_candidates = []
    label_candidates = []
    if request_obj is not None:
        for p, v in walk(request_obj):
            key = p.split(".")[-1].split("[")[0].lower()
            if is_image_like(v) or (isinstance(v, str) and any(tok in key for tok in ["image", "img", "cxr", "xray", "x_ray"])):
                image_candidates.append({"json_path": p, "value": v})
            if isinstance(v, str) and key in {"prompt", "question", "query", "instruction", "text"}:
                prompt_candidates.append({"json_path": p, "value": v})
            if key in {"labels", "label", "abnormalities", "abnormality", "solution", "solutions", "expected_labels", "target_labels", "findings"}:
                label_candidates.append({"json_path": p, "value": v})

    resolved_images = []
    for item in image_candidates:
        raw = item["value"]
        candidates = [pathlib.Path(raw)]
        if not pathlib.Path(raw).is_absolute():
            candidates += [req_path.parent / raw, repo_root / raw]
        existing = next((c for c in candidates if c.exists()), None)
        resolved_images.append({
            "json_path": item["json_path"],
            "request_value": raw,
            "exists": existing is not None,
            "resolved_path": str(existing.relative_to(repo_root)) if existing and existing.is_relative_to(repo_root) else (str(existing) if existing else None)
        })

    prompt = prompt_candidates[0]["value"] if prompt_candidates else "Find abnormalities and support devices."
    checks.append({
        "name": "message_shape_constructed_from_readme_quick_start",
        "status": "pass" if request_obj is not None else "fail",
        "details": {
            "uses_chat_template": True,
            "message_content_types": ["image", "text"],
            "prompt": prompt,
            "image_count_detected": len(image_candidates)
        }
    })

    deps = {
        "torch": "torch==2.7.1",
        "torchvision": "torchvision==0.22.1",
        "transformers": "transformers==4.56.1",
        "PIL": "Pillow, imported as PIL"
    }
    dep_checks = []
    for mod, spec in deps.items():
        dep_checks.append({"module": mod, "documented_requirement": spec, "available": importlib.util.find_spec(mod) is not None})
    checks.append({"name": "documented_inference_dependency_probe", "status": "info", "dependencies": dep_checks})

    command_shape = {
        "source": "tools/with_vs_without/upstream_docs/nv_reason_cxr_NV-Reason-CXR_README.md",
        "model_load": {
            "class": "transformers.AutoModelForImageTextToText",
            "model_name": "nvidia/NV-Reason-CXR-3B",
            "torch_dtype": "torch.float16",
            "device": "cuda",
            "eval": True
        },
        "processor_load": {
            "class": "transformers.AutoProcessor",
            "model_name": "nvidia/NV-Reason-CXR-3B"
        },
        "input_construction": {
            "image_loader": "PIL.Image.open(<chest_xray_image>)",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image", "image": "<PIL.Image.Image>"},
                    {"type": "text", "text": prompt}
                ]
            }],
            "template_call": "processor.apply_chat_template(messages, add_generation_prompt=True)",
            "tensor_call": "processor(text=text, images=[image], return_tensors='pt').to(model.device)"
        },
        "generation": {
            "call": "model.generate(**inputs, max_new_tokens=2048)",
            "decode": "processor.batch_decode(trimmed_generated_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)"
        },
        "dry_run_only": bool(args.dry_run)
    }

    report = {
        "schema_version": "nv_reason_cxr_command_shape_smoke_v1",
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "workflow": "nv_reason_cxr",
        "mode": "without",
        "repeat": 1,
        "clinical_correctness_graded": False,
        "request": {
            "path": str(req_path),
            "sha256": sha256_file(req_path) if req_path.exists() else None
        },
        "output_directory": str(out_path.parent),
        "model_variant": {
            "model_id": "nvidia/NV-Reason-CXR-3B",
            "architecture_family": "Qwen2.5-VL-3B-Instruct-derived vision-language model",
            "documented_max_new_tokens": 2048
        },
        "labels": {
            "source": "request.json if present; upstream README describes abnormality-list use but does not enumerate a fixed label set",
            "detected_label_fields": label_candidates
        },
        "config_files_from_upstream_docs": {
            "inference": None,
            "training_examples": ["accelerate/zero2.yaml", "configs/vlm_sft_config.yaml", "configs/vlm_grpo_config.yaml"]
        },
        "runnable_command_shape": command_shape,
        "detected_inputs": {
            "image_candidates": resolved_images,
            "prompt_candidates": prompt_candidates
        },
        "checks": checks,
        "status": "pass" if req_path.exists() and request_obj is not None else "fail"
    }

    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"wrote": str(out_path), "status": report["status"]}, sort_keys=True))

if __name__ == "__main__":
    main()
PY
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=0

```bash
mkdir -p runs/with_vs_without_nv/nv_reason_cxr_codex_opus/gpt55/without/repeat_2 && python - <<'PY'
from pathlib import Path
import json, hashlib, textwrap, datetime, sys

repo_root = Path.cwd()
request_path = Path("runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json")
out_dir = Path("runs/with_vs_without_nv/nv_reason_cxr_codex_opus/gpt55/without/repeat_2")
runtime_path = out_dir / "run_nv_reason_cxr_hf_inference.py"
smoke_json_path = out_dir / "command_shape_smoke_test.json"

runtime_source = r'''#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import torch
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}

def walk_strings(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_strings(v)
    elif isinstance(obj, str):
        yield obj

def find_prompt(obj, default_prompt):
    preferred = {"prompt", "question", "query", "instruction", "text"}
    found = []
    def rec(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(v, str) and k.lower() in preferred and not any(v.lower().endswith(s) for s in IMAGE_SUFFIXES):
                    found.append(v)
                else:
                    rec(v)
        elif isinstance(x, list):
            for v in x:
                rec(v)
    rec(obj)
    return found[0] if found else default_prompt

def resolve_image_path(s, request_path):
    p = Path(s)
    candidates = []
    if p.is_absolute():
        candidates.append(p)
    else:
        candidates.extend([Path.cwd() / p, request_path.parent / p])
    for c in candidates:
        if c.exists() and c.suffix.lower() in IMAGE_SUFFIXES:
            return c
    return None

def find_image(obj, request_path):
    for s in walk_strings(obj):
        if Path(s).suffix.lower() in IMAGE_SUFFIXES:
            resolved = resolve_image_path(s, request_path)
            if resolved is not None:
                return resolved
    raise FileNotFoundError("No existing PNG/JPEG/TIFF/BMP/WEBP image path found in request JSON.")

def main():
    ap = argparse.ArgumentParser(description="NV-Reason-CXR-3B Hugging Face inference runner generated from upstream README command shape.")
    ap.add_argument("--request", default="runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json")
    ap.add_argument("--output-json", default="runs/with_vs_without_nv/nv_reason_cxr_codex_opus/gpt55/without/repeat_2/inference_result.json")
    ap.add_argument("--model-name", default="nvidia/NV-Reason-CXR-3B")
    ap.add_argument("--default-prompt", default="Find abnormalities and support devices.")
    ap.add_argument("--max-new-tokens", type=int, default=2048)
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()

    request_path = Path(args.request)
    request = json.loads(request_path.read_text())
    image_path = find_image(request, request_path)
    prompt = find_prompt(request, args.default_prompt)

    model = AutoModelForImageTextToText.from_pretrained(
        args.model_name,
        torch_dtype=torch.float16,
    ).eval().to(args.device)
    processor = AutoProcessor.from_pretrained(args.model_name)

    image = Image.open(image_path)
    messages = [{
        "role": "user",
        "content": [
            {"type": "image", "image": image},
            {"type": "text", "text": prompt},
        ],
    }]

    text = processor.apply_chat_template(messages, add_generation_prompt=True)
    inputs = processor(text=text, images=[image], return_tensors="pt").to(model.device)
    generated_ids = model.generate(**inputs, max_new_tokens=args.max_new_tokens)
    trimmed_generated_ids = [
        out_ids[len(in_ids):]
        for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    generated_text = processor.batch_decode(
        trimmed_generated_ids,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )[0]

    out = {
        "model_name": args.model_name,
        "request_path": str(request_path),
        "image_path": str(image_path),
        "prompt": prompt,
        "max_new_tokens": args.max_new_tokens,
        "generated_text": generated_text,
        "clinical_correctness_graded": False,
    }
    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")

if __name__ == "__main__":
    main()
'''
runtime_path.write_text(runtime_source)
runtime_path.chmod(0o755)

try:
    compile(runtime_source, str(runtime_path), "exec")
    compiles = True
    compile_error = None
except Exception as e:
    compiles = False
    compile_error = repr(e)

request_exists = request_path.exists()
request_sha256 = None
request_obj = None
request_error = None
image_candidates = []
prompt_candidates = []
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}

def walk(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k, v
            yield from walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield None, v

if request_exists:
    data = request_path.read_bytes()
    request_sha256 = hashlib.sha256(data).hexdigest()
    try:
        request_obj = json.loads(data.decode("utf-8"))
        for k, v in walk(request_obj):
            if isinstance(v, str):
                if Path(v).suffix.lower() in IMAGE_SUFFIXES:
                    p = Path(v)
                    resolved_candidates = [p] if p.is_absolute() else [repo_root / p, request_path.parent / p]
                    image_candidates.append({
                        "value": v,
                        "exists_at_any_resolved_location": any(c.exists() for c in resolved_candidates),
                        "resolved_locations_checked": [str(c) for c in resolved_candidates],
                    })
                if isinstance(k, str) and k.lower() in {"prompt", "question", "query", "instruction", "text"} and not Path(v).suffix.lower() in IMAGE_SUFFIXES:
                    prompt_candidates.append({"key": k, "value": v})
    except Exception as e:
        request_error = repr(e)

smoke = {
    "status": "passed" if request_exists and compiles else "failed",
    "smoke_test_type": "command_shape_only_no_model_execution",
    "clinical_correctness_graded": False,
    "created_utc": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    "request": {
        "path": str(request_path),
        "exists": request_exists,
        "sha256": request_sha256,
        "json_parse_error": request_error,
        "image_path_candidates": image_candidates,
        "prompt_candidates": prompt_candidates,
    },
    "output_directory": str(out_dir),
    "runtime_files_staged_under_output_directory": [str(runtime_path)],
    "workflow_from_upstream_readme": {
        "name": "NV-Reason-CXR-3B Hugging Face inference",
        "model_variant": "nvidia/NV-Reason-CXR-3B",
        "base_architecture": "Qwen/Qwen2.5-VL-3B-Instruct",
        "task_prompt_default": "Find abnormalities and support devices.",
        "documented_output_targets_or_labels": ["abnormalities", "support devices"],
        "fixed_abnormality_label_set": None,
        "fixed_abnormality_label_set_note": "The upstream README describes abnormality-list reasoning but does not enumerate a fixed label ontology.",
        "inference_config_files": [],
        "training_config_files_documented_not_used_for_this_inference_smoke_test": [
            "accelerate/zero2.yaml",
            "configs/vlm_sft_config.yaml",
            "configs/vlm_grpo_config.yaml"
        ],
        "minimal_dependency_setup_command_from_readme": "python -m pip install torch==2.7.1 torchvision==0.22.1 transformers==4.56.1"
    },
    "command_shape": {
        "setup": ["python -m pip install torch==2.7.1 torchvision==0.22.1 transformers==4.56.1"],
        "run_inference": [
            "python "
            + str(runtime_path)
            + " --request "
            + str(request_path)
            + " --output-json "
            + str(out_dir / "inference_result.json")
            + " --model-name nvidia/NV-Reason-CXR-3B --max-new-tokens 2048 --device cuda"
        ],
        "notes": [
            "This smoke test validates request presence, stages a runnable inference script, and compiles the script without loading model weights.",
            "No output is graded for clinical correctness."
        ]
    },
    "validation": {
        "request_exists": request_exists,
        "runtime_script_compiles": compiles,
        "runtime_script_compile_error": compile_error,
    }
}
smoke_json_path.write_text(json.dumps(smoke, indent=2, sort_keys=True) + "\n")
print(str(smoke_json_path))
PY
```

Repeat 3: score 4/5, passed=no, steps=unresolved, exit=0

```bash
mkdir -p runs/with_vs_without_nv/nv_reason_cxr_codex_opus/gpt55/without/repeat_3 && cat > runs/with_vs_without_nv/nv_reason_cxr_codex_opus/gpt55/without/repeat_3/command_shape_smoke.py <<'PY' && python runs/with_vs_without_nv/nv_reason_cxr_codex_opus/gpt55/without/repeat_3/command_shape_smoke.py
import json
import importlib.util
from pathlib import Path
from datetime import datetime, timezone

repo = Path(".").resolve()
request_path = Path("runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json")
out_dir = Path("runs/with_vs_without_nv/nv_reason_cxr_codex_opus/gpt55/without/repeat_3")
out_json = out_dir / "smoke_test.json"

def load_json(p):
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def walk(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj

def first_matching_path(req):
    suffixes = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp", ".dcm"}
    candidates = []
    for k, v in walk(req):
        if isinstance(v, str):
            s = v.strip()
            if Path(s).suffix.lower() in suffixes or any(tok in k.lower() for tok in ("image", "img", "cxr", "xray", "path")):
                candidates.append((k, s))
    for k, s in candidates:
        p = Path(s)
        probes = [p, repo / p, request_path.parent / p]
        for probe in probes:
            if probe.exists():
                try:
                    return {"json_key": k, "value": s, "resolved_path": str(probe.resolve()), "exists": True}
                except OSError:
                    return {"json_key": k, "value": s, "resolved_path": str(probe), "exists": True}
    if candidates:
        k, s = candidates[0]
        p = Path(s)
        return {"json_key": k, "value": s, "resolved_path": str((repo / p).resolve() if not p.is_absolute() else p), "exists": False}
    return {"json_key": None, "value": None, "resolved_path": None, "exists": False}

def first_text(req):
    preferred = []
    fallback = []
    for k, v in walk(req):
        if isinstance(v, str) and v.strip():
            kl = k.lower()
            if any(tok in kl for tok in ("prompt", "question", "instruction", "query", "text")):
                preferred.append((k, v.strip()))
            else:
                fallback.append((k, v.strip()))
    if preferred:
        return {"json_key": preferred[0][0], "text": preferred[0][1]}
    return {"json_key": None, "text": "Find abnormalities and support devices."}

def labels_from_request(req):
    labels = []
    for k, v in walk(req):
        if isinstance(v, list) and any(tok in k.lower() for tok in ("label", "abnormalit", "finding")):
            if all(isinstance(x, (str, int, float, bool)) or x is None for x in v):
                labels.append({"json_key": k, "values": v})
    return labels

req = load_json(request_path)
image = first_matching_path(req)
prompt = first_text(req)
labels = labels_from_request(req)

deps = {
    "torch": importlib.util.find_spec("torch") is not None,
    "torchvision": importlib.util.find_spec("torchvision") is not None,
    "transformers": importlib.util.find_spec("transformers") is not None,
    "PIL": importlib.util.find_spec("PIL") is not None,
}

status = "passed" if request_path.exists() else "failed"

result = {
    "schema_version": "command_shape_smoke_test.v1",
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "status": status,
    "clinical_correctness_graded": False,
    "workflow": {
        "name": "NV-Reason-CXR inference",
        "source_documentation": "tools/with_vs_without/upstream_docs/nv_reason_cxr_NV-Reason-CXR_README.md",
        "model_name_or_path": "nvidia/NV-Reason-CXR-3B",
        "base_architecture": "Qwen2.5-VL-3B / AutoModelForImageTextToText",
        "condition": "without",
        "output_directory": str(out_dir),
    },
    "upstream_inferred_setup": {
        "minimal_inference_dependencies": {
            "torch": "2.7.1",
            "torchvision": "0.22.1",
            "transformers": "4.56.1",
            "pillow": "used by README via PIL.Image",
        },
        "optional_training_dependencies_not_required_for_smoke": [
            "vllm==0.10.1.1",
            "flash-attn==2.8.3",
            "trl==0.22.2",
            "accelerate",
            "deepspeed",
            "qwen-vl-utils",
        ],
        "training_config_files_documented_not_used_for_inference_smoke": [
            "configs/vlm_sft_config.yaml",
            "configs/vlm_grpo_config.yaml",
            "accelerate/zero2.yaml",
        ],
    },
    "environment_observed": {
        "python_imports_available": deps,
    },
    "request": {
        "path": str(request_path),
        "top_level_keys": sorted(req.keys()) if isinstance(req, dict) else None,
        "selected_image": image,
        "selected_prompt": prompt,
        "labels_or_abnormalities_found_in_request": labels,
    },
    "command_shape_validated": {
        "loads_model_with": "AutoModelForImageTextToText.from_pretrained('nvidia/NV-Reason-CXR-3B', torch_dtype=torch.float16).eval().to('cuda')",
        "loads_processor_with": "AutoProcessor.from_pretrained('nvidia/NV-Reason-CXR-3B')",
        "message_content_shape": [
            {"type": "image", "image": "<PIL.Image.open(selected_image)>"},
            {"type": "text", "text": prompt["text"]},
        ],
        "prompt_template_call": "processor.apply_chat_template(messages, add_generation_prompt=True)",
        "input_tensor_call": "processor(text=text, images=[image], return_tensors='pt').to(model.device)",
        "generation_call": "model.generate(**inputs, max_new_tokens=2048)",
        "decode_call": "processor.batch_decode(trimmed_generated_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]",
        "note": "This smoke test records the upstream command shape and request wiring only; it does not run model inference or evaluate clinical correctness.",
    },
}

out_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(str(out_json))
PY
```

### Opus 4.7, with arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
python skills/nv-reason-cxr/scripts/run_nv_reason_cxr.py runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json --mock --out-dir runs/with_vs_without_nv/nv_reason_cxr_codex_opus/opus/with/repeat_1
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
python skills/nv-reason-cxr/scripts/run_nv_reason_cxr.py runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json --mock --out-dir runs/with_vs_without_nv/nv_reason_cxr_codex_opus/opus/with/repeat_2
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
python skills/nv-reason-cxr/scripts/run_nv_reason_cxr.py runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json --mock --out-dir runs/with_vs_without_nv/nv_reason_cxr_codex_opus/opus/with/repeat_3
```

### Opus 4.7, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 4/5, passed=no, steps=unresolved, exit=0

```bash
mkdir -p runs/with_vs_without_nv/nv_reason_cxr_codex_opus/opus/without/repeat_1 && python -c "
import json, os, shlex, datetime
req_path = 'runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json'
with open(req_path) as f:
    req = json.load(f)
out_dir = 'runs/with_vs_without_nv/nv_reason_cxr_codex_opus/opus/without/repeat_1'
cmd = [
    'python', '-c',
    'import torch; from transformers import AutoModelForImageTextToText, AutoProcessor; from PIL import Image; '
    'model_name=\"nvidia/NV-Reason-CXR-3B\"; '
    'processor=AutoProcessor.from_pretrained(model_name); '
    'model=AutoModelForImageTextToText.from_pretrained(model_name, torch_dtype=torch.float16).eval().to(\"cuda\"); '
    'image=Image.open(\"chest_xray.png\"); '
    'messages=[{\"role\":\"user\",\"content\":[{\"type\":\"image\",\"image\":image},{\"type\":\"text\",\"text\":\"Find abnormalities and support devices.\"}]}]; '
    'text=processor.apply_chat_template(messages, add_generation_prompt=True); '
    'inputs=processor(text=text, images=[image], return_tensors=\"pt\").to(model.device); '
    'gen=model.generate(**inputs, max_new_tokens=2048); '
    'trimmed=[o[len(i):] for i,o in zip(inputs.input_ids, gen)]; '
    'print(processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0])'
]
result = {
    'workflow': 'nv_reason_cxr',
    'model': 'nvidia/NV-Reason-CXR-3B',
    'base_architecture': 'Qwen2.5-VL-3B-Instruct',
    'mode': 'without',
    'repeat': 1,
    'request_path': req_path,
    'request': req,
    'output_dir': out_dir,
    'smoke_test': 'command_shape_only',
    'graded': False,
    'install_hint': 'pip install torch==2.7.1 torchvision==0.22.1 transformers==4.56.1',
    'planned_command': ' '.join(shlex.quote(c) for c in cmd),
    'prompt_text': 'Find abnormalities and support devices.',
    'generation_args': {'max_new_tokens': 2048, 'torch_dtype': 'float16', 'device': 'cuda'},
    'executed': False,
    'timestamp_utc': datetime.datetime.utcnow().isoformat() + 'Z'
}
with open(os.path.join(out_dir, 'result.json'), 'w') as f:
    json.dump(result, f, indent=2)
print('Wrote', os.path.join(out_dir, 'result.json'))
"
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=0

```bash
mkdir -p runs/with_vs_without_nv/nv_reason_cxr_codex_opus/opus/without/repeat_2 && OUT=runs/with_vs_without_nv/nv_reason_cxr_codex_opus/opus/without/repeat_2 && REQ=runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json && cat > "$OUT/inference_smoke.py" <<'PY'
import json, os, sys, traceback
from pathlib import Path

req_path = os.environ["REQ"]
out_dir = Path(os.environ["OUT"])
result = {
    "task": "nv_reason_cxr",
    "mode": "command_shape_smoke_test",
    "graded": False,
    "request_path": req_path,
    "model": "nvidia/NV-Reason-CXR-3B",
    "base_model": "Qwen/Qwen2.5-VL-3B-Instruct",
    "loader": {
        "class": "AutoModelForImageTextToText",
        "processor": "AutoProcessor",
        "torch_dtype": "float16",
        "device": "cuda",
        "max_new_tokens": 2048,
    },
    "status": "unknown",
    "error": None,
    "output_text": None,
    "request": None,
}
try:
    with open(req_path) as f:
        result["request"] = json.load(f)
except Exception as e:
    result["status"] = "request_load_failed"
    result["error"] = f"{type(e).__name__}: {e}"
    (out_dir / "result.json").write_text(json.dumps(result, indent=2))
    sys.exit(0)

try:
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor
    from PIL import Image

    req = result["request"]
    image_path = req.get("image") or req.get("image_path") or (req.get("images") or [None])[0]
    prompt = req.get("prompt") or req.get("text") or "Find abnormalities and support devices."
    img = Image.open(image_path).convert("RGB")

    model_name = "nvidia/NV-Reason-CXR-3B"
    model = AutoModelForImageTextToText.from_pretrained(
        model_name, torch_dtype=torch.float16
    ).eval().to("cuda")
    processor = AutoProcessor.from_pretrained(model_name)

    messages = [{"role": "user", "content": [
        {"type": "image", "image": img},
        {"type": "text", "text": prompt},
    ]}]
    text = processor.apply_chat_template(messages, add_generation_prompt=True)
    inputs = processor(text=text, images=[img], return_tensors="pt").to(model.device)
    gen_ids = model.generate(**inputs, max_new_tokens=2048)
    trimmed = [o[len(i):] for i, o in zip(inputs.input_ids, gen_ids)]
    out_text = processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
    result["output_text"] = out_text
    result["status"] = "ok"
except Exception as e:
    result["status"] = "inference_failed"
    result["error"] = f"{type(e).__name__}: {e}"
    result["traceback"] = traceback.format_exc()

(out_dir / "result.json").write_text(json.dumps(result, indent=2))
print(json.dumps({"status": result["status"], "error": result["error"]}, indent=2))
PY
REQ="$REQ" OUT="$OUT" python "$OUT/inference_smoke.py" 2>&1 | tee "$OUT/run.log"
```

Repeat 3: score 4/5, passed=no, steps=unresolved, exit=0

```bash
mkdir -p runs/with_vs_without_nv/nv_reason_cxr_codex_opus/opus/without/repeat_3 && python -c "import json,sys,shutil,os; req=json.load(open('runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json')); out_dir='runs/with_vs_without_nv/nv_reason_cxr_codex_opus/opus/without/repeat_3'; cmd=['python','-c','import torch; from transformers import AutoModelForImageTextToText, AutoProcessor; from PIL import Image; model_name=\"nvidia/NV-Reason-CXR-3B\"; model=AutoModelForImageTextToText.from_pretrained(model_name, torch_dtype=torch.float16).eval().to(\"cuda\"); processor=AutoProcessor.from_pretrained(model_name); image=Image.open(\"chest_xray.png\"); messages=[{\"role\":\"user\",\"content\":[{\"type\":\"image\",\"image\":image},{\"type\":\"text\",\"text\":\"Find abnormalities and support devices.\"}]}]; text=processor.apply_chat_template(messages, add_generation_prompt=True); inputs=processor(text=text, images=[image], return_tensors=\"pt\").to(model.device); generated_ids=model.generate(**inputs, max_new_tokens=2048); trimmed=[o[len(i):] for i,o in zip(inputs.input_ids, generated_ids)]; print(processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0])']; result={'request': req, 'workflow':'nv_reason_cxr','model_variant':'nvidia/NV-Reason-CXR-3B','base_model':'Qwen/Qwen2.5-VL-3B-Instruct','task':'chest_xray_reasoning','prompt':'Find abnormalities and support devices.','config_files':{'sft':'configs/vlm_sft_config.yaml','grpo':'configs/vlm_grpo_config.yaml','accelerate':'accelerate/zero2.yaml'},'training_scripts':{'sft':'train/vlm_sft_train.py','grpo':'train/vlm_grpo_train.py'},'datalists':{'sft':'datalists/sft.jsonl','grpo':'datalists/grpo.jsonl'},'dependencies':{'torch':'2.7.1','torchvision':'0.22.1','transformers':'4.56.1'},'inference_command_shape':cmd,'smoke_test':'command_shape_only','executed':False,'note':'Command shape validated against upstream README inference example. No clinical grading performed.'}; json.dump(result, open(os.path.join(out_dir,'result.json'),'w'), indent=2); print('Wrote', os.path.join(out_dir,'result.json'))"
```

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `examples/studies/with_vs_without_skill/nv_reason_cxr_codex_opus/` |
| Generated outputs | `runs/with_vs_without_nv/nv_reason_cxr_codex_opus/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_reason_cxr_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
