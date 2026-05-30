# `nv_generate_mr_brain`: Codex/Opus LLM+SKILL.md vs LLM+README

Status: strict audit passed for refreshed artifacts on May 29, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

This report compares `LLM + SKILL.md` with `LLM + upstream README/guide`. The completed direct-API run used the corrected embedded-doc minimal prompt because those backends cannot read repo files. The fair NAT/tool-agent prompt artifact is A2-style: it gives a natural user request, a neutral staged input path, an output directory, and tells the agent which arm-specific document to read. It does not spell out operational details such as entrypoints, labels, model variants, or config filenames outside the documentation arm.

## Experiment Question

Does `LLM + SKILL.md` make an agent better at reading documentation and taking the right action than `LLM + upstream README/guide`?

## User Request Shape

The prompt request for the GPT-5.5 with-skill arm was:

> The image-generation request is at runs/with_vs_without_nv/_inputs/nv_generate_mr_brain/request.json. Generate one T1 brain MR image and write generated NIfTI volumes under runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/gpt55/with/repeat_1.

The staged user input for every arm was `runs/with_vs_without_nv/_inputs/nv_generate_mr_brain/request.json`. The source fixture `skills/nv-generate-mr-brain/fixtures/default_mri_t1.json` was used only to stage that neutral input path.

Fair path-prompt artifact: `tools/nat_audit/data/eval_nv_model_studies_nv_generate_mr_brain_prompts.json`

## Result

| Backend | Arm | Mean score | Passes | Steps | Exit | Tier 5 | Failed tiers |
|---|---|---:|---:|---|---|---|---|
| GPT-5.5 / Codex | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | shape=(256, 256, 256) (3) | none |
| GPT-5.5 / Codex | without | 4.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | 1 (2); None (1) | exit 1 (2); blocked unsafe command fragment: rm (1) | T5: exit 1 (2); T5: blocked unsafe command fragment: rm (1) |
| Opus 4.7 | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | shape=(256, 256, 256) (3) | none |
| Opus 4.7 | without | 3.3/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | None (2); 1 (1) | command does not reference the neutral staged input path (2); exit 1 (1) | T2: user input path marker (2); T5: command does not reference the neutral staged input path (2); T5: exit 1 (1) |

## Analysis

SKILL.md paired advantage: the with-skill arms passed 6/6 backend-repeat trials with an average score of 5.0/5; the README-only arms passed 0/6 backend-repeat trials with an average score of 3.7/5.

SKILL.md paired advantage: SKILL.md wins 6/6 matched backend-repeat pairs, README-only wins 0/6, and 0/6 are ties. Pass/fail is the primary outcome; score breaks ties only when pass status is equal. Exact one-sided sign-test p=0.01562 across 6 decisive pair(s).

Outcome-support gate: Supports SKILL.md advantage. SKILL.md wins 6/6 matched pair(s); README-only wins 0/6; sign-test p=0.01562.

Each backend/arm/skill configuration was repeated three times. A repeat is independent: it has its own output directory, and each execution attempt inside the repeat creates a fresh venv before running the generated command. Dependency and model download caches are shared only as documented test-environment caches under `.workbench_data/with_vs_without_cache` (`PIP_CACHE_DIR=.workbench_data/with_vs_without_cache/pip`, `HF_HOME=.workbench_data/with_vs_without_cache/huggingface`, `HF_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `HUGGINGFACE_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `TRANSFORMERS_CACHE=.workbench_data/with_vs_without_cache/huggingface/transformers`, `TORCH_HOME=.workbench_data/with_vs_without_cache/torch`, `XDG_CACHE_HOME=.workbench_data/with_vs_without_cache/xdg`, `CONDA_PKGS_DIRS=.workbench_data/with_vs_without_cache/conda_pkgs`, `UV_CACHE_DIR=.workbench_data/with_vs_without_cache/uv`, `CUDA_CACHE_PATH=.workbench_data/with_vs_without_cache/cuda`, `NUMBA_CACHE_DIR=.workbench_data/with_vs_without_cache/numba`).

The main baseline uses `max_correction_steps=0`: each repeat sends one prompt, executes the extracted command once, and records pass/fail, runtime, tokens, and deterministic failure analysis. The repair-loop implementation remains available for separate diagnostic experiments, but it is not part of this comparison.

All with-skill repeats exited successfully and produced artifacts accepted by the deterministic grader. That means the final SKILL.md surface was repeatable for both tested agent backends.

The README-only commands did not pass tier 5. Typical failure modes were unsafe generated shell cleanup, missing schema fields, missing model/control details, or upstream commands that did not execute cleanly from Medical AI Skills root.

Tier 2 is intentionally strict: a command only earns it if it uses the staged user input path `runs/with_vs_without_nv/_inputs/nv_generate_mr_brain/request.json`.

## Token Profiling

Token counts are provider-reported values saved in each repeat JSON. Reasoning tokens are shown only when the provider returned that subfield and are a subset of completion tokens, not an additional cost to add to total tokens. Execution time is averaged only across repeats that reached command execution; no-command-extracted repeats still count toward token totals.

| Backend | Arm | Repeats | Passes | Attempts | Prompt tokens | Completion tokens | Reasoning tokens | Total tokens | Mean total/repeat | Executed | Mean exec s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GPT-5.5 / Codex | with | 3 | 3 | 3 | 6,423 | 1,380 | 986 | 7,803 | 2,601.0 | 3 | 60.4 |
| GPT-5.5 / Codex | without | 3 | 0 | 3 | 8,901 | 10,502 | 8,193 | 19,403 | 6,467.7 | 2 | 0.0 |
| Opus 4.7 | with | 3 | 3 | 3 | 11,100 | 678 | 0 | 11,778 | 3,926.0 | 3 | 62.4 |
| Opus 4.7 | without | 3 | 0 | 3 | 13,224 | 2,545 | 0 | 15,769 | 5,256.3 | 1 | 0.0 |

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
| 1 | 0 | 4/5 | no | None | T5: blocked unsafe command fragment: rm | tier_5: blocked unsafe command fragment: rm Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: blocked unsafe command fragment: rm Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
| 2 | 0 | 4/5 | no | 1 | T5: exit 1 | tier_5: exit 1 Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>nonzero_exit: Command exited 1. Repair: Use stderr/stdout to repair setup, paths, arguments, or runtime package installation. |
| 3 | 0 | 4/5 | no | 1 | T5: exit 1 | tier_5: exit 1 Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>nonzero_exit: Command exited 1. Repair: Use stderr/stdout to repair setup, paths, arguments, or runtime package installation. |

### Opus 4.7, with arm

| Repeat | Step | Score | Passed | Exit | Failed tiers | Why it did not work |
|---:|---:|---:|---|---|---|---|
| 1 | 0 | 5/5 | yes | 0 | none | none |
| 2 | 0 | 5/5 | yes | 0 | none | none |
| 3 | 0 | 5/5 | yes | 0 | none | none |

### Opus 4.7, without arm

| Repeat | Step | Score | Passed | Exit | Failed tiers | Why it did not work |
|---:|---:|---:|---|---|---|---|
| 1 | 0 | 3/5 | no | None | T2: user input path marker; T5: command does not reference the neutral staged input path | tier_2: user input path marker Repair: Use the staged user input path under runs/with_vs_without_nv/_inputs/.<br>tier_5: command does not reference the neutral staged input path Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference the neutral staged input path Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
| 2 | 0 | 4/5 | no | 1 | T5: exit 1 | tier_5: exit 1 Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>nonzero_exit: Command exited 1. Repair: Use stderr/stdout to repair setup, paths, arguments, or runtime package installation. |
| 3 | 0 | 3/5 | no | None | T2: user input path marker; T5: command does not reference the neutral staged input path | tier_2: user input path marker Repair: Use the staged user input path under runs/with_vs_without_nv/_inputs/.<br>tier_5: command does not reference the neutral staged input path Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference the neutral staged input path Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |

## Skill Fix Notes

Before the final rerun, `SKILL.md` was tightened to name `scripts/run_mr_brain.py` as the exact runnable surface, preserve the staged request path, and avoid invented module or shell entrypoints.

## Generated Commands

These are the extracted first-attempt commands by repeat.

### GPT-5.5 / Codex, with arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-mr-brain/scripts/run_mr_brain.py runs/with_vs_without_nv/_inputs/nv_generate_mr_brain/request.json --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/gpt55/with/repeat_1 --modality mri_t1
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-mr-brain/scripts/run_mr_brain.py runs/with_vs_without_nv/_inputs/nv_generate_mr_brain/request.json --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/gpt55/with/repeat_2 --modality mri_t1 --random-seed 1234
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-mr-brain/scripts/run_mr_brain.py runs/with_vs_without_nv/_inputs/nv_generate_mr_brain/request.json --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/gpt55/with/repeat_3 --modality mri_t1 --random-seed 3
```

### GPT-5.5 / Codex, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 4/5, passed=no, steps=unresolved, exit=None

```bash
bash -lc 'set -euo pipefail; repo="$PWD"; up=".workbench_data/upstreams/NV-Generate-CTMR"; out="runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/gpt55/without/repeat_1"; stage="$out/runtime"; req="runs/with_vs_without_nv/_inputs/nv_generate_mr_brain/request.json"; rm -rf "$out"; mkdir -p "$stage"; cp -a "$up/configs" "$stage/configs"; python - "$req" "$stage" <<'"'"'PY'"'"'
import json, sys
from pathlib import Path

req_path = Path(sys.argv[1])
stage = Path(sys.argv[2])
request = json.loads(req_path.read_text()) if req_path.exists() else {}

def first_deep(obj, names):
    if isinstance(obj, dict):
        for n in names:
            if n in obj:
                return obj[n]
        for v in obj.values():
            got = first_deep(v, names)
            if got is not None:
                return got
    elif isinstance(obj, list):
        for v in obj:
            got = first_deep(v, names)
            if got is not None:
                return got
    return None

dim = first_deep(request, ["dim", "dims", "image_dim", "image_dims"]) or [256, 256, 256]
spacing = first_deep(request, ["spacing", "voxel_spacing"]) or [1.0, 1.0, 1.0]
seed = first_deep(request, ["random_seed", "seed"])
modality = 9  # mri_t1

cfg_path = stage / "configs" / "config_maisi_diff_model_rflow-mr-brain.json"
cfg = json.loads(cfg_path.read_text())
dui = cfg.setdefault("diffusion_unet_inference", {})
dui["dim"] = dim
dui["spacing"] = spacing
dui["modality"] = modality
dui["num_output_samples"] = 1
dui["num_inference_steps"] = 30
if seed is not None:
    dui["random_seed"] = seed
cfg_path.write_text(json.dumps(cfg, indent=4) + "\n")

env_path = stage / "configs" / "environment_maisi_diff_model_rflow-mr-brain.json"
env = json.loads(env_path.read_text())
def set_output_dir(obj):
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if k == "output_dir":
                obj[k] = "../"
            else:
                set_output_dir(v)
    elif isinstance(obj, list):
        for v in obj:
            set_output_dir(v)
set_output_dir(env)
env_path.write_text(json.dumps(env, indent=4) + "\n")
PY
cd "$stage" && PYTHONPATH="$repo/$up${PYTHONPATH:+:$PYTHONPATH}" python -m scripts.download_model_data --version rflow-mr-brain --root_dir "./" --model_only && PYTHONPATH="$repo/$up${PYTHONPATH:+:$PYTHONPATH}" python -m scripts.diff_model_infer -t ./configs/config_network_rflow.json -e ./configs/environment_maisi_diff_model_rflow-mr-brain.json -c ./configs/config_maisi_diff_model_rflow-mr-brain.json'
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=1

```bash
OUT="runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/gpt55/without/repeat_2" && REQ="runs/with_vs_without_nv/_inputs/nv_generate_mr_brain/request.json" && RUNTIME="${OUT}/nv_generate_runtime" && mkdir -p "${RUNTIME}/configs" "${OUT}/generated_nifti" && cp "${NV_GENERATE_ROOT:?NV_GENERATE_ROOT must point to the NV-Generate-CTMR checkout}/configs/config_network_rflow.json" "${RUNTIME}/configs/" && cp "${NV_GENERATE_ROOT}/configs/environment_maisi_diff_model_rflow-mr-brain.json" "${RUNTIME}/configs/" && cp "${NV_GENERATE_ROOT}/configs/config_maisi_diff_model_rflow-mr-brain.json" "${RUNTIME}/configs/" && cp "${REQ}" "${OUT}/request.json" && python - <<'PY'
import json
from pathlib import Path

out = Path("runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/gpt55/without/repeat_2")
runtime = out / "nv_generate_runtime"
cfg_path = runtime / "configs" / "config_maisi_diff_model_rflow-mr-brain.json"
env_path = runtime / "configs" / "environment_maisi_diff_model_rflow-mr-brain.json"
req_path = out / "request.json"

req = json.loads(req_path.read_text()) if req_path.exists() else {}

def set_existing_or_add(d, key, value):
    if isinstance(d, dict):
        if key in d:
            d[key] = value
            return True
        for v in d.values():
            if set_existing_or_add(v, key, value):
                return True
    elif isinstance(d, list):
        for v in d:
            if set_existing_or_add(v, key, value):
                return True
    return False

def set_all_existing(d, keys, value):
    if isinstance(d, dict):
        for k in list(d):
            if k in keys:
                d[k] = value
        for v in d.values():
            set_all_existing(v, keys, value)
    elif isinstance(d, list):
        for v in d:
            set_all_existing(v, keys, value)

cfg = json.loads(cfg_path.read_text())
dui = cfg.setdefault("diffusion_unet_inference", {})
dui["dim"] = req.get("dim", [256, 256, 256])
dui["spacing"] = req.get("spacing", [1.0, 1.0, 1.0])
dui["modality"] = req.get("modality", 9)
dui["num_inference_steps"] = req.get("num_inference_steps", 30)
if "random_seed" in req:
    dui["random_seed"] = req["random_seed"]
set_all_existing(cfg, {"num_output_samples", "num_samples", "n_samples", "num_images", "batch_size"}, 1)
cfg_path.write_text(json.dumps(cfg, indent=4) + "\n")

env = json.loads(env_path.read_text())
if not set_existing_or_add(env, "output_dir", "../generated_nifti"):
    env["output_dir"] = "../generated_nifti"
env_path.write_text(json.dumps(env, indent=4) + "\n")
PY
(cd "${RUNTIME}" && PYTHONPATH="${NV_GENERATE_ROOT}${PYTHONPATH:+:${PYTHONPATH}}" python -m scripts.download_model_data --version rflow-mr-brain --root_dir "./" --model_only && PYTHONPATH="${NV_GENERATE_ROOT}${PYTHONPATH:+:${PYTHONPATH}}" python -m scripts.diff_model_infer -t ./configs/config_network_rflow.json -e ./configs/environment_maisi_diff_model_rflow-mr-brain.json -c ./configs/config_maisi_diff_model_rflow-mr-brain.json)
```

Repeat 3: score 4/5, passed=no, steps=unresolved, exit=1

```bash
OUT="runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/gpt55/without/repeat_3" && REQ="runs/with_vs_without_nv/_inputs/nv_generate_mr_brain/request.json" && GEN_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && REPO_ROOT="$PWD" && mkdir -p "$OUT/runtime" && cp "$GEN_ROOT/configs/config_network_rflow.json" "$OUT/runtime/config_network_rflow.json" && cp "$GEN_ROOT/configs/environment_maisi_diff_model_rflow-mr-brain.json" "$OUT/runtime/environment_maisi_diff_model_rflow-mr-brain.json" && cp "$GEN_ROOT/configs/config_maisi_diff_model_rflow-mr-brain.json" "$OUT/runtime/config_maisi_diff_model_rflow-mr-brain.json" && python - "$REQ" "$OUT/runtime/environment_maisi_diff_model_rflow-mr-brain.json" "$OUT/runtime/config_maisi_diff_model_rflow-mr-brain.json" <<'PY' && cd "$OUT" && PYTHONPATH="$REPO_ROOT/$GEN_ROOT${PYTHONPATH:+:$PYTHONPATH}" python -m scripts.download_model_data --version rflow-mr-brain --root_dir "." --model_only && PYTHONPATH="$REPO_ROOT/$GEN_ROOT${PYTHONPATH:+:$PYTHONPATH}" python -m scripts.diff_model_infer -t runtime/config_network_rflow.json -e runtime/environment_maisi_diff_model_rflow-mr-brain.json -c runtime/config_maisi_diff_model_rflow-mr-brain.json
import json, sys
request_path, env_path, cfg_path = sys.argv[1:4]
with open(request_path, "r") as f:
    _request = json.load(f)
with open(env_path, "r") as f:
    env = json.load(f)
with open(cfg_path, "r") as f:
    cfg = json.load(f)

def set_key_recursive(obj, key, value):
    if isinstance(obj, dict):
        for k in list(obj.keys()):
            if k == key:
                obj[k] = value
            else:
                set_key_recursive(obj[k], key, value)
    elif isinstance(obj, list):
        for v in obj:
            set_key_recursive(v, key, value)

set_key_recursive(env, "output_dir", ".")
inf = cfg.setdefault("diffusion_unet_inference", {})
inf["dim"] = [256, 256, 256]
inf["spacing"] = [1.0, 1.0, 1.0]
inf["modality"] = 9
inf["num_inference_steps"] = 30
for container in (cfg, inf):
    for k in ("num_output_samples", "num_samples", "n_samples", "batch_size"):
        if k in container:
            container[k] = 1

with open(env_path, "w") as f:
    json.dump(env, f, indent=2)
with open(cfg_path, "w") as f:
    json.dump(cfg, f, indent=2)
PY
```

### Opus 4.7, with arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-mr-brain/scripts/run_mr_brain.py runs/with_vs_without_nv/_inputs/nv_generate_mr_brain/request.json --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/opus/with/repeat_1 --modality mri_t1 --random-seed 1234
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-mr-brain/scripts/run_mr_brain.py runs/with_vs_without_nv/_inputs/nv_generate_mr_brain/request.json --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/opus/with/repeat_2 --modality mri_t1 --random-seed 1234
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-mr-brain/scripts/run_mr_brain.py runs/with_vs_without_nv/_inputs/nv_generate_mr_brain/request.json --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/opus/with/repeat_3 --modality mri_t1 --random-seed 1234
```

### Opus 4.7, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 3/5, passed=no, steps=unresolved, exit=None

```bash
mkdir -p runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/opus/without/repeat_1 && OUT_DIR="$(pwd)/runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/opus/without/repeat_1" && STAGE="$OUT_DIR/_stage" && mkdir -p "$STAGE/configs" && cd "$NV_GENERATE_ROOT" && python -m scripts.download_model_data --version rflow-mr-brain --root_dir "./" --model_only && cp configs/config_network_rflow.json "$STAGE/configs/config_network_rflow.json" && cp configs/environment_maisi_diff_model_rflow-mr-brain.json "$STAGE/configs/environment_maisi_diff_model_rflow-mr-brain.json" && cp configs/config_maisi_diff_model_rflow-mr-brain.json "$STAGE/configs/config_maisi_diff_model_rflow-mr-brain.json" && python -c "import json,sys; p='$STAGE/configs/environment_maisi_diff_model_rflow-mr-brain.json'; d=json.load(open(p)); d['output_dir']='$OUT_DIR'; json.dump(d,open(p,'w'),indent=2)" && python -c "import json; p='$STAGE/configs/config_maisi_diff_model_rflow-mr-brain.json'; d=json.load(open(p)); d['diffusion_unet_inference']['dim']=[256,256,256]; d['diffusion_unet_inference']['spacing']=[1.0,1.0,1.0]; d['diffusion_unet_inference']['modality']=9; d['diffusion_unet_inference']['num_output_samples']=1; json.dump(d,open(p,'w'),indent=2)" && python -m scripts.diff_model_infer -t "$STAGE/configs/config_network_rflow.json" -e "$STAGE/configs/environment_maisi_diff_model_rflow-mr-brain.json" -c "$STAGE/configs/config_maisi_diff_model_rflow-mr-brain.json"
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=1

```bash
set -euo pipefail && REPO_ROOT="$(pwd)" && OUT_DIR="runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/opus/without/repeat_2" && STAGE_DIR="${OUT_DIR}/_stage" && mkdir -p "${REPO_ROOT}/${OUT_DIR}" "${REPO_ROOT}/${STAGE_DIR}/configs" && cd "$NV_GENERATE_ROOT" && python -m scripts.download_model_data --version rflow-mr-brain --root_dir "./" --model_only && cp configs/config_network_rflow.json "${REPO_ROOT}/${STAGE_DIR}/configs/config_network_rflow.json" && cp configs/environment_maisi_diff_model_rflow-mr-brain.json "${REPO_ROOT}/${STAGE_DIR}/configs/environment_maisi_diff_model_rflow-mr-brain.json" && cp configs/config_maisi_diff_model_rflow-mr-brain.json "${REPO_ROOT}/${STAGE_DIR}/configs/config_maisi_diff_model_rflow-mr-brain.json" && python -c "
import json, os
repo='${REPO_ROOT}'; stage=os.path.join(repo,'${STAGE_DIR}'); out=os.path.join(repo,'${OUT_DIR}')
req=json.load(open(os.path.join(repo,'runs/with_vs_without_nv/_inputs/nv_generate_mr_brain/request.json')))
print('request:', req)
ep=os.path.join(stage,'configs/environment_maisi_diff_model_rflow-mr-brain.json')
e=json.load(open(ep)); e['output_dir']=out; json.dump(e,open(ep,'w'),indent=2)
cp=os.path.join(stage,'configs/config_maisi_diff_model_rflow-mr-brain.json')
c=json.load(open(cp))
c['diffusion_unet_inference']['dim']=[256,256,256]
c['diffusion_unet_inference']['spacing']=[1.0,1.0,1.0]
c['diffusion_unet_inference']['modality']=9
c['diffusion_unet_inference']['num_output_samples']=1
json.dump(c,open(cp,'w'),indent=2)
print('staged configs updated')
" && python -m scripts.diff_model_infer -t "${REPO_ROOT}/${STAGE_DIR}/configs/config_network_rflow.json" -e "${REPO_ROOT}/${STAGE_DIR}/configs/environment_maisi_diff_model_rflow-mr-brain.json" -c "${REPO_ROOT}/${STAGE_DIR}/configs/config_maisi_diff_model_rflow-mr-brain.json"
```

Repeat 3: score 3/5, passed=no, steps=unresolved, exit=None

```bash
mkdir -p runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/opus/without/repeat_3 && OUT_DIR="$(pwd)/runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/opus/without/repeat_3" && STAGE_DIR="${OUT_DIR}/_stage" && mkdir -p "${STAGE_DIR}/configs" && cd "${NV_GENERATE_ROOT}" && python -m scripts.download_model_data --version rflow-mr-brain --root_dir "./" --model_only && cp configs/config_network_rflow.json "${STAGE_DIR}/configs/config_network_rflow.json" && cp configs/environment_maisi_diff_model_rflow-mr-brain.json "${STAGE_DIR}/configs/environment_maisi_diff_model_rflow-mr-brain.json" && cp configs/config_maisi_diff_model_rflow-mr-brain.json "${STAGE_DIR}/configs/config_maisi_diff_model_rflow-mr-brain.json" && python -c "import json,sys; p='${STAGE_DIR}/configs/environment_maisi_diff_model_rflow-mr-brain.json'; d=json.load(open(p)); d['output_dir']='${OUT_DIR}'; json.dump(d,open(p,'w'),indent=4)" && python -c "import json; p='${STAGE_DIR}/configs/config_maisi_diff_model_rflow-mr-brain.json'; d=json.load(open(p)); d['diffusion_unet_inference']['dim']=[256,256,256]; d['diffusion_unet_inference']['spacing']=[1.0,1.0,1.0]; d['diffusion_unet_inference']['modality']=9; d['diffusion_unet_inference']['num_output_samples']=1; json.dump(d,open(p,'w'),indent=4)" && python -m scripts.diff_model_infer -t "${STAGE_DIR}/configs/config_network_rflow.json" -e "${STAGE_DIR}/configs/environment_maisi_diff_model_rflow-mr-brain.json" -c "${STAGE_DIR}/configs/config_maisi_diff_model_rflow-mr-brain.json"
```

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `runs/with_vs_without_nv/studies/nv_generate_mr_brain_codex_opus/` |
| Generated outputs | `runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_generate_mr_brain_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
