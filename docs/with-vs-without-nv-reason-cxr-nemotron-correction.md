# `nv_reason_cxr`: Nemotron LLM+SKILL.md vs LLM+README Baseline Study

Status: strict audit passed for refreshed artifacts on May 28, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

This report uses the same direct-API embedded-doc no-repair baseline protocol as the Codex/Opus comparison, but runs `nvidia/nvidia/nemotron-3-super-v3`. The linked prompt artifact is the fair A2-style path prompt for tool-enabled/NAT replication.

## Experiment Question

Does `LLM + SKILL.md` let Nemotron produce a runnable command on the first try, and how does that compare with `LLM + upstream README/guide` under the same `max_correction_steps=0` baseline?

## User Request Shape

The prompt request for the with-skill arm was:

> The CXR request is at runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json. Run a command-shape smoke test for the CXR reasoning workflow and write structured JSON under runs/with_vs_without_nv/nv_reason_cxr_nemotron_correction/with/repeat_1. Do not grade clinical correctness.

The staged user input for every arm was `runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json`. The source fixture `skills/nv-reason-cxr/fixtures/synthetic_cxr_input.json` was used only to stage that neutral input path.

Fair path-prompt artifact: `tools/nat_audit/data/eval_nv_model_studies_nv_reason_cxr_prompts.json`

## Result

| Backend | Arm | Mean score | Passes | Steps | Exit | Tier 5 | Failed tiers |
|---|---|---:|---:|---|---|---|---|
| Nemotron | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | response_text present (3) | none |
| Nemotron | without | 4.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | 1 (2); 0 (1) | exit 1 (2); schema-like JSON response missing response_text (1) | T5: exit 1 (2); T5: schema-like JSON response missing response_text (1) |

## Analysis

SKILL.md paired advantage: the with-skill repeats passed 3/3 with mean score 5.0/5 and steps mean 0.0; unresolved 0; values [0, 0, 0]. The README-only repeats passed 0/3 with mean score 4.0/5 and steps all unresolved; values [unresolved, unresolved, unresolved].

SKILL.md paired advantage: SKILL.md wins 3/3 matched backend-repeat pairs, README-only wins 0/3, and 0/3 are ties. Pass/fail is the primary outcome; score breaks ties only when pass status is equal. Exact one-sided sign-test p=0.125 across 3 decisive pair(s).

Outcome-support gate: Supports SKILL.md advantage. SKILL.md wins 3/3 matched pair(s); README-only wins 0/3; sign-test p=0.125.

Each backend/arm/skill configuration was repeated three times. A repeat is independent: it has its own output directory, and each execution attempt inside the repeat creates a fresh venv before running the generated command. Dependency and model download caches are shared only as documented test-environment caches under `.workbench_data/with_vs_without_cache` (`PIP_CACHE_DIR=.workbench_data/with_vs_without_cache/pip`, `HF_HOME=.workbench_data/with_vs_without_cache/huggingface`, `HF_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `HUGGINGFACE_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `TRANSFORMERS_CACHE=.workbench_data/with_vs_without_cache/huggingface/transformers`, `TORCH_HOME=.workbench_data/with_vs_without_cache/torch`, `XDG_CACHE_HOME=.workbench_data/with_vs_without_cache/xdg`, `CONDA_PKGS_DIRS=.workbench_data/with_vs_without_cache/conda_pkgs`, `UV_CACHE_DIR=.workbench_data/with_vs_without_cache/uv`, `CUDA_CACHE_PATH=.workbench_data/with_vs_without_cache/cuda`, `NUMBA_CACHE_DIR=.workbench_data/with_vs_without_cache/numba`).

No correction feedback was sent in this baseline. Deterministic failure analysis is saved with each repeat so repair behavior can be studied separately later.

## Token Profiling

Token counts are provider-reported values saved in each repeat JSON. Reasoning tokens are shown only when the provider returned that subfield and are a subset of completion tokens, not an additional cost to add to total tokens. Execution time is averaged only across repeats that reached command execution; no-command-extracted repeats still count toward token totals.

| Backend | Arm | Repeats | Passes | Attempts | Prompt tokens | Completion tokens | Reasoning tokens | Total tokens | Mean total/repeat | Executed | Mean exec s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Nemotron | with | 3 | 3 | 3 | 7,497 | 5,444 | 0 | 12,941 | 4,313.7 | 3 | 0.1 |
| Nemotron | without | 3 | 0 | 3 | 11,019 | 11,100 | 0 | 22,119 | 7,373.0 | 3 | 0.0 |

## Nemotron Diagnostics

These diagnostics are Nemotron-only and do not change the main score. The strict result still requires exactly one valid fenced bash block. The recoverable-command columns ask whether a deterministic format adapter could have recovered command-like text without another LLM call or any domain repair.

| Arm | Repeats | Passed strict | Strict command | Recoverable malformed command | Unrecoverable formatting | Guard-ready after tolerant extraction | Static guard blocked | Format categories | Guard reasons |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| with | 3 | 3 | 3 | 0 | 0 | 0 | 0 | strict 3 | none |
| without | 3 | 0 | 3 | 0 | 0 | 0 | 0 | strict 3 | none |

Protocol-compliance failure buckets, counted per repeat and not mutually exclusive:

| Bucket | Count |
|---|---:|
| No strict command extracted | 0 |
| Wrong or missing runnable surface | 0 |
| Missing staged input path | 0 |
| Missing model/modality/control marker | 0 |
| Missing output directory | 0 |
| Unsafe/static guard block | 0 |
| Nonzero execution exit | 2 |
| Artifact contract failure after execution | 1 |

## Attempt Trace

### With-skill arm

| Repeat | Step | Score | Passed | Exit | Failed tiers | Why it did not work |
|---:|---:|---:|---|---|---|---|
| 1 | 0 | 5/5 | yes | 0 | none | none |
| 2 | 0 | 5/5 | yes | 0 | none | none |
| 3 | 0 | 5/5 | yes | 0 | none | none |

### README-only arm

| Repeat | Step | Score | Passed | Exit | Failed tiers | Why it did not work |
|---:|---:|---:|---|---|---|---|
| 1 | 0 | 4/5 | no | 1 | T5: exit 1 | tier_5: exit 1 Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>nonzero_exit: Command exited 1. Repair: Use stderr/stdout to repair setup, paths, arguments, or runtime package installation. |
| 2 | 0 | 4/5 | no | 0 | T5: schema-like JSON response missing response_text | tier_5: schema-like JSON response missing response_text Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>artifact_verification: schema-like JSON response missing response_text Repair: Adjust the command so it produces the expected output files and schema for the task. |
| 3 | 0 | 4/5 | no | 1 | T5: exit 1 | tier_5: exit 1 Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>nonzero_exit: Command exited 1. Repair: Use stderr/stdout to repair setup, paths, arguments, or runtime package installation. |

## Generated Commands

These are the extracted first-attempt commands by repeat.

### With-skill arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
python skills/nv-reason-cxr/scripts/run_nv_reason_cxr.py runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json --mock --out-dir runs/with_vs_without_nv/nv_reason_cxr_nemotron_correction/with/repeat_1
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
mkdir -p runs/with_vs_without_nv/nv_reason_cxr_nemotron_correction/with/repeat_2 && python skills/nv-reason-cxr/scripts/run_nv_reason_cxr.py runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json --mock --out-dir runs/with_vs_without_nv/nv_reason_cxr_nemotron_correction/with/repeat_2
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
mkdir -p runs/with_vs_without_nv/nv_reason_cxr_nemotron_correction/with/repeat_3 && python skills/nv-reason-cxr/scripts/run_nv_reason_cxr.py runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json --mock --out-dir runs/with_vs_without_nv/nv_reason_cxr_nemotron_correction/with/repeat_3
```

### README-only arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 4/5, passed=no, steps=unresolved, exit=1

```bash
mkdir -p runs/with_vs_without_nv/nv_reason_cxr_nemotron_correction/without/repeat_1 && python -c "
import json
import torch
from transformers import AutoModelForImageTextToText, AutoProcessor
from PIL import Image
import os

# Read input request
input_path = 'runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json'
with open(input_path, 'r') as f:
    request = json.load(f)

image_path = request.get('image_path')
prompt_text = request.get('prompt', 'Find abnormalities and support devices.')

# Load model and processor
model_name = 'nvidia/NV-Reason-CXR-3B'
model = AutoModelForImageTextToText.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
).eval().to('cuda')
processor = AutoProcessor.from_pretrained(model_name)

# Load and process image
image = Image.open(image_path)
messages = [{
    'role': 'user',
    'content': [
        {'type': 'image', 'image': image},
        {'type': 'text', 'text': prompt_text}
    ]
}]
text = processor.apply_chat_template(messages, add_generation_prompt=True)
inputs = processor(text=text, images=[image], return_tensors='pt').to(model.device)

# Generate output
generated_ids = model.generate(**inputs, max_new_tokens=2048)
trimmed_generated_ids = [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)]
generated_text = processor.batch_decode(trimmed_generated_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]

# Write structured JSON output
output_data = {
    'generated_text': generated_text,
    'input': request
}
output_dir = 'runs/with_vs_without_nv/nv_reason_cxr_nemotron_correction/without/repeat_1'
output_path = os.path.join(output_dir, 'output.json')
with open(output_path, 'w') as f:
    json.dump(output_data, f, indent=2)
"
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=0

```bash
mkdir -p runs/with_vs_without_nv/nv_reason_cxr_nemotron_correction/without/repeat_2 && \
cat > runs/with_vs_without_nv/nv_reason_cxr_nemotron_correction/without/repeat_2/smoke_test.py << 'EOF'
import json, os, torch
from transformers import AutoModelForImageTextToText, AutoProcessor
from PIL import Image

# Load request
req_path = "runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json"
with open(req_path) as f:
    req = json.load(f)

# Extract inputs (flexible key names)
image_path = req.get("image") or req.get("image_path") or ""
text_prompt = req.get("text") or req.get("prompt") or "Find abnormalities and support devices."

if not image_path or not os.path.exists(image_path):
    raise FileNotFoundError(f"Image not found or not specified: {image_path}")

# Load model and processor (as per upstream docs)
model_name = "nvidia/NV-Reason-CXR-3B"
model = AutoModelForImageTextToText.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
).eval().to("cuda")
processor = AutoProcessor.from_pretrained(model_name)

# Prepare image
image = Image.open(image_path).convert("RGB")

# Build chat template
messages = [
    {
        "role": "user",
        "content": [
            {"type": "image", "image": image},
            {"type": "text", "text": text_prompt},
        ],
    }
]
text = processor.apply_chat_template(messages, add_generation_prompt=True)

# Process inputs
inputs = processor(text=text, images=[image], return_tensors="pt").to(model.device)

# Generate
generated_ids = model.generate(**inputs, max_new_tokens=2048)

# Trim and decode
trimmed_generated_ids = [
    out_ids[len(in_ids):]
    for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
]
generated_text = processor.batch_decode(
    trimmed_generated_ids,
    skip_special_tokens=True,
    clean_up_tokenization_spaces=False,
)[0]

# Output JSON
out_dir = "runs/with_vs_without_nv/nv_reason_cxr_nemotron_correction/without/repeat_2"
os.makedirs(out_dir, exist_ok=True)
result = {"generated_text": generated_text}
with open(os.path.join(out_dir, "result.json"), "w") as f:
    json.dump(result, f, indent=2)
EOF && \
python3 runs/with_vs_without_nv/nv_reason_cxr_nemotron_correction/without/repeat_2/smoke_test.py
```

Repeat 3: score 4/5, passed=no, steps=unresolved, exit=1

```bash
mkdir -p runs/with_vs_without_nv/nv_reason_cxr_nemotron_correction/without/repeat_3 && python3 -c "
import json
import torch
from transformers import AutoModelForImageTextToText, AutoProcessor
from PIL import Image
import os

# Load request
with open('runs/with_vs_without_nv/_inputs/nv_reason_cxr/request.json', 'r') as f:
    request = json.load(f)

# Extract image path and prompt (adjust keys based on actual request.json structure)
image_path = request.get('image_path', request.get('image', ''))
prompt_text = request.get('prompt', request.get('text', 'Find abnormalities and support devices.'))

# Resolve image path relative to Medical AI Skills root if not absolute
if not os.path.isabs(image_path):
    image_path = os.path.join(os.getcwd(), image_path)

# Load model and processor
model_name = 'nvidia/NV-Reason-CXR-3B'
model = AutoModelForImageTextToText.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
).eval().to('cuda')
processor = AutoProcessor.from_pretrained(model_name)

# Load and process image
image = Image.open(image_path).convert('RGB')
messages = [{
    'role': 'user',
    'content': [
        {'type': 'image', 'image': image},
        {'type': 'text', 'text': prompt_text}
    ]
}]
text = processor.apply_chat_template(messages, add_generation_prompt=True)
inputs = processor(text=text, images=[image], return_tensors='pt').to(model.device)

# Generate output
with torch.no_grad():
    generated_ids = model.generate(**inputs, max_new_tokens=1024)
trimmed_generated_ids = [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)]
generated_text = processor.batch_decode(trimmed_generated_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]

# Save structured JSON output
output_data = {
    'input_request': request,
    'model_output': generated_text,
    'workflow': 'nv_reason_cxr_smoke_test',
    'status': 'completed'
}
output_dir = 'runs/with_vs_without_nv/nv_reason_cxr_nemotron_correction/without/repeat_3'
os.makedirs(output_dir, exist_ok=True)
with open(os.path.join(output_dir, 'output.json'), 'w') as f:
    json.dump(output_data, f, indent=2)
"
```

## Skill Fix Notes

Before the final rerun, `SKILL.md` was tightened to name `scripts/run_nv_reason_cxr.py` as the exact command-shape smoke-test surface and to reserve live model inference for explicit user requests.

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `examples/studies/with_vs_without_skill/nv_reason_cxr_nemotron_correction/` |
| Generated outputs | `runs/with_vs_without_nv/nv_reason_cxr_nemotron_correction/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_reason_cxr_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
