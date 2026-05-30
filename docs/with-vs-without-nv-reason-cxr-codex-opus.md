# `nv_reason_cxr`: Codex/Opus LLM+SKILL.md vs LLM+README

Status: strict audit passed for refreshed artifacts on May 29, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

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
| Opus 4.7 | without | 4.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | 0 (2); 1 (1) | schema-like JSON response missing response_text (2); exit 1 (1) | T5: schema-like JSON response missing response_text (2); T5: exit 1 (1) |

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
| GPT-5.5 / Codex | with | 3 | 3 | 3 | 7,020 | 1,548 | 1,301 | 8,568 | 2,856.0 | 3 | 0.1 |
| GPT-5.5 / Codex | without | 3 | 0 | 3 | 10,419 | 6,135 | 2,048 | 16,554 | 5,518.0 | 3 | 0.0 |
| Opus 4.7 | with | 3 | 3 | 3 | 12,141 | 454 | 0 | 12,595 | 4,198.3 | 3 | 0.1 |
| Opus 4.7 | without | 3 | 0 | 3 | 16,887 | 3,805 | 0 | 20,692 | 6,897.3 | 3 | 0.0 |

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
| 2 | 0 | 4/5 | no | 1 | T5: exit 1 | tier_5: exit 1 Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>nonzero_exit: Command exited 1. Repair: Use stderr/stdout to repair setup, paths, arguments, or runtime package installation. |
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
mkdir -p runs/with_vs_without_nv/nv_reason_cxr_codex_opus/gpt55/with/repeat_2 && python skills/nv-reason-cxr/scripts/run_nv_reason_cxr.py runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json --mock --out-dir runs/with_vs_without_nv/nv_reason_cxr_codex_opus/gpt55/with/repeat_2
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
python skills/nv-reason-cxr/scripts/run_nv_reason_cxr.py runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json --mock --out-dir runs/with_vs_without_nv/nv_reason_cxr_codex_opus/gpt55/with/repeat_3
```

### GPT-5.5 / Codex, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 4/5, passed=no, steps=unresolved, exit=0

```bash
mkdir -p runs/with_vs_without_nv/nv_reason_cxr_codex_opus/gpt55/without/repeat_1 && python - <<'PY'
import json
import os
from pathlib import Path

request_path = Path("runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json")
out_dir = Path("runs/with_vs_without_nv/nv_reason_cxr_codex_opus/gpt55/without/repeat_1")
out_path = out_dir / "command_shape_smoke_test.json"

def find_image_like_paths(obj, hits=None):
    if hits is None:
        hits = []
    image_exts = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp", ".dicom", ".dcm"}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = str(k).lower()
            if isinstance(v, str):
                suffix = Path(v).suffix.lower()
                if "image" in key or suffix in image_exts:
                    hits.append(v)
            else:
                find_image_like_paths(v, hits)
    elif isinstance(obj, list):
        for v in obj:
            find_image_like_paths(v, hits)
    return hits

request_exists = request_path.exists()
request = None
request_load_error = None
if request_exists:
    try:
        request = json.loads(request_path.read_text())
    except Exception as e:
        request_load_error = f"{type(e).__name__}: {e}"

image_candidates = find_image_like_paths(request) if isinstance(request, (dict, list)) else []
image_checks = []
for p in image_candidates:
    pp = Path(p)
    if not pp.is_absolute():
        pp = Path(p)
    image_checks.append({"path": p, "exists": pp.exists()})

smoke = {
    "smoke_test_type": "command_shape_only",
    "status": "passed" if request_exists and request_load_error is None else "failed",
    "clinical_correctness_graded": False,
    "input_request": {
        "path": str(request_path),
        "exists": request_exists,
        "json_load_error": request_load_error,
    },
    "output_directory": str(out_dir),
    "upstream_documentation_used": [
        "tools/with_vs_without/upstream_docs/nv_reason_cxr_NV-Reason-CXR_README.md"
    ],
    "workflow": {
        "name": "NV-Reason-CXR inference",
        "model_name_or_path": "nvidia/NV-Reason-CXR-3B",
        "architecture_family": "Qwen2.5-VL-3B-based vision-language model",
        "task_prompt_from_docs": "Find abnormalities and support devices.",
        "max_new_tokens_from_docs": 2048,
        "dtype_from_docs": "torch.float16",
        "device_from_docs": "cuda",
        "processor_class_from_docs": "AutoProcessor",
        "model_class_from_docs": "AutoModelForImageTextToText",
    },
    "dependencies_from_docs": {
        "minimal_inference_install_command": "pip install torch==2.7.1 torchvision==0.22.1 transformers==4.56.1",
        "python_packages": {
            "torch": "2.7.1",
            "torchvision": "0.22.1",
            "transformers": "4.56.1",
            "PIL": "provided by Pillow dependency as used in README snippet"
        }
    },
    "labels_or_outputs_from_docs": {
        "fixed_label_list": None,
        "reason": "The inference documentation requests free-text reasoning for abnormalities and support devices rather than defining a fixed label list.",
        "documented_output_style": [
            "main findings",
            "step-by-step reasoning pathway",
            "differential diagnoses",
            "recommendations or clinical correlation",
            "structured report generation"
        ]
    },
    "config_files_from_docs": {
        "inference_config_file": None,
        "training_configs_mentioned_but_not_used_for_inference_smoke_test": [
            "accelerate/zero2.yaml",
            "configs/vlm_sft_config.yaml",
            "configs/vlm_grpo_config.yaml"
        ]
    },
    "request_image_path_checks": image_checks,
    "command_shape": {
        "setup": "pip install torch==2.7.1 torchvision==0.22.1 transformers==4.56.1",
        "inference_python_shape": [
            "from transformers import AutoModelForImageTextToText, AutoProcessor",
            "from PIL import Image",
            "model = AutoModelForImageTextToText.from_pretrained('nvidia/NV-Reason-CXR-3B', torch_dtype=torch.float16).eval().to('cuda')",
            "processor = AutoProcessor.from_pretrained('nvidia/NV-Reason-CXR-3B')",
            "image = Image.open(<request image path>)",
            "messages = [{'role': 'user', 'content': [{'type': 'image', 'image': image}, {'type': 'text', 'text': 'Find abnormalities and support devices.'}]}]",
            "text = processor.apply_chat_template(messages, add_generation_prompt=True)",
            "inputs = processor(text=text, images=[image], return_tensors='pt').to(model.device)",
            "generated_ids = model.generate(**inputs, max_new_tokens=2048)",
            "decode only generated tokens with processor.batch_decode(..., skip_special_tokens=True, clean_up_tokenization_spaces=False)"
        ]
    },
    "side_effect_policy": {
        "writes_only_under_requested_output_directory": True,
        "did_not_write_upstreams_or_nv_roots": True,
        "model_execution_performed_by_this_smoke_test": False
    }
}

out_path.write_text(json.dumps(smoke, indent=2, sort_keys=True) + "\n")
print(str(out_path))
PY
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=0

```bash
mkdir -p runs/with_vs_without_nv/nv_reason_cxr_codex_opus/gpt55/without/repeat_2 && python - <<'PY'
import json, os, platform, shlex, sys, textwrap, time
from pathlib import Path

repo_root = Path(".").resolve()
request_path = Path("runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json")
out_dir = Path("runs/with_vs_without_nv/nv_reason_cxr_codex_opus/gpt55/without/repeat_2")
out_dir.mkdir(parents=True, exist_ok=True)

request = json.loads(request_path.read_text()) if request_path.exists() else None

def find_image_refs(obj):
    refs = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                refs.extend(find_image_refs(v))
            elif isinstance(v, str) and (k.lower() in {"image", "image_path", "image_file", "path"} or v.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"))):
                refs.append(v)
    elif isinstance(obj, list):
        for v in obj:
            refs.extend(find_image_refs(v))
    return refs

def find_text_prompt(obj):
    candidates = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and k.lower() in {"prompt", "question", "text", "query", "instruction"}:
                candidates.append(v)
            elif isinstance(v, (dict, list)):
                candidates.extend(find_text_prompt(v))
    elif isinstance(obj, list):
        for v in obj:
            candidates.extend(find_text_prompt(v))
    return candidates

image_refs = find_image_refs(request) if request is not None else []
prompt_candidates = find_text_prompt(request) if request is not None else []
prompt = prompt_candidates[0] if prompt_candidates else "Find abnormalities and support devices."

smoke_script = out_dir / "nv_reason_cxr_command_shape_smoke.py"
smoke_script.write_text(textwrap.dedent(f'''
    """
    Command-shape smoke test for NV-Reason-CXR-3B inference.
    This file is staged under the requested output directory and is not intended
    to grade clinical correctness.
    """
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor
    from PIL import Image

    model_name = "nvidia/NV-Reason-CXR-3B"
    image_path = {repr(image_refs[0] if image_refs else "chest_xray.png")}
    prompt = {repr(prompt)}

    model = AutoModelForImageTextToText.from_pretrained(
        model_name,
        torch_dtype=torch.float16,
    ).eval().to("cuda")

    processor = AutoProcessor.from_pretrained(model_name)
    image = Image.open(image_path)

    messages = [
        {{
            "role": "user",
            "content": [
                {{"type": "image", "image": image}},
                {{"type": "text", "text": prompt}},
            ],
        }}
    ]

    text = processor.apply_chat_template(messages, add_generation_prompt=True)
    inputs = processor(text=text, images=[image], return_tensors="pt").to(model.device)
    generated_ids = model.generate(**inputs, max_new_tokens=2048)
    trimmed_generated_ids = [
        out_ids[len(in_ids):]
        for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    generated_text = processor.batch_decode(
        trimmed_generated_ids,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )[0]
    print(generated_text)
''').lstrip())

command_shape = [
    sys.executable,
    str(smoke_script),
]
result = {
    "schema_version": "1.0",
    "task": "nv_reason_cxr_command_shape_smoke_test",
    "status": "PASS" if request is not None else "FAIL",
    "clinical_correctness_graded": False,
    "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "inputs": {
        "request_json": str(request_path),
        "request_json_exists": request_path.exists(),
        "image_references": image_refs,
        "image_reference_existence": {
            p: Path(p).exists() for p in image_refs
        },
        "prompt_used_for_command_shape": prompt,
    },
    "upstream_documentation_inference_shape": {
        "model_name_or_path": "nvidia/NV-Reason-CXR-3B",
        "architecture_family": "Qwen2.5-VL-3B-based image-text-to-text VLM",
        "processor_class": "AutoProcessor",
        "model_class": "AutoModelForImageTextToText",
        "torch_dtype": "float16",
        "device": "cuda",
        "generation": {"max_new_tokens": 2048},
        "default_prompt_if_request_prompt_missing": "Find abnormalities and support devices.",
    },
    "smoke_test_scope": {
        "loads_model": False,
        "runs_generation": False,
        "validates_request_presence": True,
        "stages_runnable_inference_script": True,
        "writes_structured_json": True,
    },
    "staged_runtime_files": {
        "smoke_script": str(smoke_script),
    },
    "command_shape": {
        "argv": command_shape,
        "shell_escaped": " ".join(shlex.quote(x) for x in command_shape),
        "note": "Command shape only; this smoke test does not execute model inference.",
    },
    "environment": {
        "python": sys.version,
        "platform": platform.platform(),
        "cwd": str(repo_root),
    },
}
(out_dir / "command_shape_smoke_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps(result, indent=2, sort_keys=True))
PY
```

Repeat 3: score 4/5, passed=no, steps=unresolved, exit=0

```bash
mkdir -p runs/with_vs_without_nv/nv_reason_cxr_codex_opus/gpt55/without/repeat_3 && python - <<'PY'
import json, os, platform, shlex, hashlib, textwrap
from pathlib import Path

repo = Path(".")
request_path = Path("runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json")
out_dir = Path("runs/with_vs_without_nv/nv_reason_cxr_codex_opus/gpt55/without/repeat_3")
out_dir.mkdir(parents=True, exist_ok=True)

request = json.loads(request_path.read_text())
request_sha256 = hashlib.sha256(request_path.read_bytes()).hexdigest()

def collect_strings(obj):
    vals = []
    if isinstance(obj, str):
        vals.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            vals.extend(collect_strings(v))
    elif isinstance(obj, list):
        for v in obj:
            vals.extend(collect_strings(v))
    return vals

strings = collect_strings(request)
image_exts = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff", ".dicom", ".dcm"}
image_candidates = []
for s in strings:
    p = Path(s)
    if p.suffix.lower() in image_exts:
        image_candidates.append(s)

prompt_candidates = []
for key in ("prompt", "question", "text", "instruction", "query"):
    if isinstance(request, dict) and isinstance(request.get(key), str):
        prompt_candidates.append(request[key])
prompt = prompt_candidates[0] if prompt_candidates else "Find abnormalities and support devices."

labels = None
for key in ("labels", "label_names", "abnormalities", "classes"):
    if isinstance(request, dict) and isinstance(request.get(key), list):
        labels = request[key]
        break

runtime_script = out_dir / "nv_reason_cxr_infer_runtime.py"
runtime_script.write_text(textwrap.dedent("""\
    import argparse
    import json
    from pathlib import Path

    import torch
    from PIL import Image
    from transformers import AutoModelForImageTextToText, AutoProcessor

    def main():
        ap = argparse.ArgumentParser(description="NV-Reason-CXR-3B single-request inference wrapper")
        ap.add_argument("--request", required=True)
        ap.add_argument("--image", required=True)
        ap.add_argument("--output", required=True)
        ap.add_argument("--prompt", default="Find abnormalities and support devices.")
        ap.add_argument("--model-name", default="nvidia/NV-Reason-CXR-3B")
        ap.add_argument("--max-new-tokens", type=int, default=2048)
        args = ap.parse_args()

        image = Image.open(args.image).convert("RGB")
        model = AutoModelForImageTextToText.from_pretrained(
            args.model_name,
            torch_dtype=torch.float16,
        ).eval().to("cuda")
        processor = AutoProcessor.from_pretrained(args.model_name)

        messages = [{
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": args.prompt},
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

        Path(args.output).write_text(json.dumps({
            "model_name": args.model_name,
            "prompt": args.prompt,
            "request_path": args.request,
            "image_path": args.image,
            "generated_text": generated_text,
            "clinical_correctness_graded": False,
        }, indent=2))

    if __name__ == "__main__":
        main()
    """))

first_image = image_candidates[0] if image_candidates else "<IMAGE_PATH_FROM_REQUEST>"
inference_cmd = (
    "python " + shlex.quote(str(runtime_script)) +
    " --request " + shlex.quote(str(request_path)) +
    " --image " + shlex.quote(first_image) +
    " --output " + shlex.quote(str(out_dir / "inference_output.json")) +
    " --prompt " + shlex.quote(prompt) +
    " --model-name nvidia/NV-Reason-CXR-3B --max-new-tokens 2048"
)

smoke = {
    "status": "passed_command_shape_smoke_test",
    "clinical_correctness_graded": False,
    "task": "CXR reasoning workflow",
    "request": {
        "path": str(request_path),
        "sha256": request_sha256,
        "loaded": True,
        "top_level_type": type(request).__name__,
        "top_level_keys": sorted(request.keys()) if isinstance(request, dict) else None,
        "image_candidates_found": image_candidates,
        "selected_image_argument": first_image,
        "prompt": prompt,
        "labels_from_request_if_present": labels,
    },
    "upstream_inference_spec": {
        "model_name": "nvidia/NV-Reason-CXR-3B",
        "architecture_base": "Qwen2.5-VL-3B-Instruct",
        "processor_class": "AutoProcessor",
        "model_class": "AutoModelForImageTextToText",
        "torch_dtype": "float16",
        "device": "cuda",
        "chat_message_content": ["image", "text"],
        "default_prompt_from_documentation": "Find abnormalities and support devices.",
        "max_new_tokens": 2048,
        "inference_config_files": [],
        "minimal_dependency_install_command": "pip install torch==2.7.1 torchvision==0.22.1 transformers==4.56.1",
    },
    "runtime_files_staged_under_output_dir": {
        "inference_wrapper": str(runtime_script),
        "smoke_json": str(out_dir / "smoke_test.json"),
    },
    "runnable_inference_command_not_executed_by_smoke_test": inference_cmd,
    "environment_observed": {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cwd": os.getcwd(),
    },
    "notes": [
        "This smoke test validates request loading and constructs the documented Hugging Face inference command shape only.",
        "It does not execute model inference and does not assess clinical correctness.",
        "No files are written under .workbench_data/upstreams, NV_GENERATE_ROOT, or NV_SEGMENT_CTMR_ROOT."
    ],
}
(out_dir / "smoke_test.json").write_text(json.dumps(smoke, indent=2))
print(json.dumps({"wrote": str(out_dir / "smoke_test.json"), "status": smoke["status"]}, indent=2))
PY
```

### Opus 4.7, with arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
mkdir -p runs/with_vs_without_nv/nv_reason_cxr_codex_opus/opus/with/repeat_1 && python skills/nv-reason-cxr/scripts/run_nv_reason_cxr.py runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json --mock --out-dir runs/with_vs_without_nv/nv_reason_cxr_codex_opus/opus/with/repeat_1
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
mkdir -p runs/with_vs_without_nv/nv_reason_cxr_codex_opus/opus/with/repeat_2 && python skills/nv-reason-cxr/scripts/run_nv_reason_cxr.py runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json --mock --out-dir runs/with_vs_without_nv/nv_reason_cxr_codex_opus/opus/with/repeat_2
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
import json, os, sys, shlex
req_path = 'runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json'
out_dir = 'runs/with_vs_without_nv/nv_reason_cxr_codex_opus/opus/without/repeat_1'
with open(req_path) as f:
    req = json.load(f)
image = req.get('image') or req.get('image_path') or 'chest_xray.png'
prompt = req.get('prompt') or req.get('text') or 'Find abnormalities and support devices.'
model_name = 'nvidia/NV-Reason-CXR-3B'
script = os.path.join(out_dir, 'run_inference.py')
with open(script, 'w') as f:
    f.write('''import torch
from transformers import AutoModelForImageTextToText, AutoProcessor
from PIL import Image

model_name = %r
image_path = %r
prompt_text = %r

model = AutoModelForImageTextToText.from_pretrained(model_name, torch_dtype=torch.float16).eval().to(\"cuda\")
processor = AutoProcessor.from_pretrained(model_name)
image = Image.open(image_path)
messages = [{\"role\": \"user\", \"content\": [{\"type\": \"image\", \"image\": image}, {\"type\": \"text\", \"text\": prompt_text}]}]
text = processor.apply_chat_template(messages, add_generation_prompt=True)
inputs = processor(text=text, images=[image], return_tensors=\"pt\").to(model.device)
generated_ids = model.generate(**inputs, max_new_tokens=2048)
trimmed = [o[len(i):] for i, o in zip(inputs.input_ids, generated_ids)]
output = processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
print(output)
''' % (model_name, image, prompt))
cmd = ['accelerate', 'launch', '--num_processes', '1', script]
result = {
    'workflow': 'nv_reason_cxr',
    'mode': 'without',
    'variant': 'opus',
    'repeat': 1,
    'smoke_test': 'command_shape_only',
    'graded': False,
    'request_path': req_path,
    'request': req,
    'model': model_name,
    'base_model': 'Qwen/Qwen2.5-VL-3B-Instruct',
    'image_input': image,
    'prompt': prompt,
    'staged_script': script,
    'install_commands': [
        'pip install torch==2.7.1 torchvision==0.22.1 transformers==4.56.1'
    ],
    'inference_command': ' '.join(shlex.quote(c) for c in cmd),
    'inference_command_argv': cmd,
    'reference_python_snippet': 'See upstream README Quick start / Inference section',
    'notes': 'Command-shape smoke test only; no execution, no clinical grading performed.'
}
with open(os.path.join(out_dir, 'result.json'), 'w') as f:
    json.dump(result, f, indent=2)
print('Wrote', os.path.join(out_dir, 'result.json'))
print('Wrote', script)
"
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=1

```bash
mkdir -p runs/with_vs_without_nv/nv_reason_cxr_codex_opus/opus/without/repeat_2 && python -c "
import json, os, shlex
req_path = 'runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json'
with open(req_path) as f:
    req = json.load(f)
image = req.get('image') or req.get('image_path') or req.get('input_image') or 'chest_xray.png'
prompt = req.get('prompt') or req.get('text') or 'Find abnormalities and support devices.'
model_name = 'nvidia/NV-Reason-CXR-3B'
script = '''import torch
from transformers import AutoModelForImageTextToText, AutoProcessor
from PIL import Image

model_name = ${MODEL!r}
image_path = ${IMAGE!r}
prompt = ${PROMPT!r}

model = AutoModelForImageTextToText.from_pretrained(model_name, torch_dtype=torch.float16).eval().to('cuda')
processor = AutoProcessor.from_pretrained(model_name)
image = Image.open(image_path)
messages = [{'role':'user','content':[{'type':'image','image':image},{'type':'text','text':prompt}]}]
text = processor.apply_chat_template(messages, add_generation_prompt=True)
inputs = processor(text=text, images=[image], return_tensors='pt').to(model.device)
generated_ids = model.generate(**inputs, max_new_tokens=2048)
trimmed = [o[len(i):] for i,o in zip(inputs.input_ids, generated_ids)]
out = processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
print(out)
'''
out_dir = 'runs/with_vs_without_nv/nv_reason_cxr_codex_opus/opus/without/repeat_2'
staged_script = os.path.join(out_dir, 'run_inference.py')
with open(staged_script, 'w') as f:
    f.write(script.replace('\${MODEL!r}', repr(model_name)).replace('\${IMAGE!r}', repr(image)).replace('\${PROMPT!r}', repr(prompt)))
cmd = ['python', staged_script]
result = {
    'workflow': 'nv_reason_cxr',
    'mode': 'without',
    'variant': 'NV-Reason-CXR-3B',
    'model_name': model_name,
    'base_model': 'Qwen/Qwen2.5-VL-3B-Instruct',
    'task': 'chest_xray_reasoning',
    'request_path': req_path,
    'request': req,
    'inputs': {'image': image, 'prompt': prompt},
    'install_steps': ['pip install torch==2.7.1 torchvision==0.22.1 transformers==4.56.1'],
    'staged_script': staged_script,
    'command': ' '.join(shlex.quote(c) for c in cmd),
    'command_argv': cmd,
    'generation_params': {'max_new_tokens': 2048, 'torch_dtype': 'float16', 'device': 'cuda'},
    'config_files': [],
    'labels': 'abnormalities and support devices (free-form, model-defined)',
    'executed': False,
    'note': 'Command-shape smoke test only; not executed and no clinical grading.'
}
with open(os.path.join(out_dir, 'result.json'), 'w') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=2))
"
```

Repeat 3: score 4/5, passed=no, steps=unresolved, exit=0

```bash
mkdir -p runs/with_vs_without_nv/nv_reason_cxr_codex_opus/opus/without/repeat_3 && python -c "
import json, os, sys, datetime, pathlib

req_path = 'runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json'
out_dir = 'runs/with_vs_without_nv/nv_reason_cxr_codex_opus/opus/without/repeat_3'
req = json.load(open(req_path))

result = {
    'workflow': 'nv-reason-cxr',
    'mode': 'command_shape_smoke_test',
    'graded': False,
    'timestamp_utc': datetime.datetime.utcnow().isoformat() + 'Z',
    'request_path': req_path,
    'request': req,
    'model': {
        'name': 'NV-Reason-CXR-3B',
        'hf_id': 'nvidia/NV-Reason-CXR-3B',
        'base': 'Qwen/Qwen2.5-VL-3B-Instruct',
        'architecture': 'Vision-Language Model (Transformer)',
    },
    'inference_setup': {
        'pip_install': ['torch==2.7.1', 'torchvision==0.22.1', 'transformers==4.56.1'],
        'loader': 'transformers.AutoModelForImageTextToText',
        'processor': 'transformers.AutoProcessor',
        'dtype': 'float16',
        'device': 'cuda',
        'max_new_tokens': 2048,
        'default_user_text': 'Find abnormalities and support devices.',
    },
    'training_configs': {
        'sft_config': 'configs/vlm_sft_config.yaml',
        'grpo_config': 'configs/vlm_grpo_config.yaml',
        'accelerate_config': 'accelerate/zero2.yaml',
        'sft_dataset': 'datalists/sft.jsonl',
        'grpo_dataset': 'datalists/grpo.jsonl',
    },
    'commands': {
        'inference_python_snippet': 'AutoModelForImageTextToText.from_pretrained(\"nvidia/NV-Reason-CXR-3B\", torch_dtype=torch.float16).eval().to(\"cuda\")',
        'sft_train': 'accelerate launch --config_file accelerate/zero2.yaml --gradient_accumulation_steps 8 --num_machines 1 --num_processes 8 train/vlm_sft_train.py --config configs/vlm_sft_config.yaml --model_name_or_path nvidia/NV-Reason-CXR-3B --output_dir data/output_sft_model --dataset_path datalists/sft.jsonl --num_train_epochs 1 --dataset_streaming false --gradient_accumulation_steps 8',
        'grpo_train': 'accelerate launch --config_file accelerate/zero2.yaml --gradient_accumulation_steps 8 --num_machines 1 --num_processes 8 train/vlm_grpo_train.py --config configs/vlm_grpo_config.yaml --model_name_or_path nvidia/NV-Reason-CXR-3B --output_dir data/output_grpo_model --dataset_path datalists/grpo.jsonl --num_train_epochs 16 --gradient_accumulation_steps 8',
    },
    'labels_note': 'Output is free-form chain-of-thought reasoning with abnormality list; no fixed label schema specified in upstream README.',
    'notes': [
        'Command-shape smoke test only; no model execution performed.',
        'No clinical correctness grading performed.',
        'Paths are relative to the Medical AI Skills repo root unless noted otherwise.',
    ],
}

out_path = os.path.join(out_dir, 'result.json')
with open(out_path, 'w') as f:
    json.dump(result, f, indent=2)
print('wrote', out_path)
" && ls -la runs/with_vs_without_nv/nv_reason_cxr_codex_opus/opus/without/repeat_3/
```

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `runs/with_vs_without_nv/studies/nv_reason_cxr_codex_opus/` |
| Generated outputs | `runs/with_vs_without_nv/nv_reason_cxr_codex_opus/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_reason_cxr_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
