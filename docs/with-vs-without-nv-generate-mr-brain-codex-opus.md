# `nv_generate_mr_brain`: Codex/Opus LLM+SKILL.md vs LLM+README

Status: strict audit passed for refreshed artifacts on May 27, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

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
| GPT-5.5 / Codex | without | 3.7/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | None (3) | blocked unsafe command fragment: rm (2); command does not reference the neutral staged input path (1) | T5: blocked unsafe command fragment: rm (2); T2: user input path marker (1); T5: command does not reference the neutral staged input path (1) |
| Opus 4.7 | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | shape=(256, 256, 256) (3) | none |
| Opus 4.7 | without | 3.7/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | 1 (2); None (1) | exit 1 (2); command does not reference the neutral staged input path (1) | T5: exit 1 (2); T2: user input path marker (1); T5: command does not reference the neutral staged input path (1) |

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
| GPT-5.5 / Codex | with | 3 | 3 | 3 | 6,132 | 1,691 | 1,259 | 7,823 | 2,607.7 | 3 | 49.0 |
| GPT-5.5 / Codex | without | 3 | 0 | 3 | 8,895 | 16,961 | 14,317 | 25,856 | 8,618.7 | 0 | n/a |
| Opus 4.7 | with | 3 | 3 | 3 | 10,554 | 678 | 0 | 11,232 | 3,744.0 | 3 | 48.6 |
| Opus 4.7 | without | 3 | 0 | 3 | 13,194 | 2,851 | 0 | 16,045 | 5,348.3 | 2 | 0.0 |

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
| 1 | 0 | 3/5 | no | None | T2: user input path marker; T5: command does not reference the neutral staged input path | tier_2: user input path marker Repair: Use the staged user input path under runs/with_vs_without_nv/_inputs/.<br>tier_5: command does not reference the neutral staged input path Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference the neutral staged input path Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
| 2 | 0 | 4/5 | no | None | T5: blocked unsafe command fragment: rm | tier_5: blocked unsafe command fragment: rm Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: blocked unsafe command fragment: rm Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
| 3 | 0 | 4/5 | no | None | T5: blocked unsafe command fragment: rm | tier_5: blocked unsafe command fragment: rm Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: blocked unsafe command fragment: rm Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |

### Opus 4.7, with arm

| Repeat | Step | Score | Passed | Exit | Failed tiers | Why it did not work |
|---:|---:|---:|---|---|---|---|
| 1 | 0 | 5/5 | yes | 0 | none | none |
| 2 | 0 | 5/5 | yes | 0 | none | none |
| 3 | 0 | 5/5 | yes | 0 | none | none |

### Opus 4.7, without arm

| Repeat | Step | Score | Passed | Exit | Failed tiers | Why it did not work |
|---:|---:|---:|---|---|---|---|
| 1 | 0 | 4/5 | no | 1 | T5: exit 1 | tier_5: exit 1 Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>nonzero_exit: Command exited 1. Repair: Use stderr/stdout to repair setup, paths, arguments, or runtime package installation. |
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
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-mr-brain/scripts/run_mr_brain.py runs/with_vs_without_nv/_inputs/nv_generate_mr_brain/request.json --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/gpt55/with/repeat_1 --modality mri_t1 --random-seed 1234
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
mkdir -p runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/gpt55/with/repeat_2 && export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-mr-brain/scripts/run_mr_brain.py runs/with_vs_without_nv/_inputs/nv_generate_mr_brain/request.json --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/gpt55/with/repeat_2 --modality mri_t1 --random-seed 2 --yes
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-mr-brain/scripts/run_mr_brain.py runs/with_vs_without_nv/_inputs/nv_generate_mr_brain/request.json --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/gpt55/with/repeat_3 --modality mri_t1 --random-seed 3
```

### GPT-5.5 / Codex, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 3/5, passed=no, steps=unresolved, exit=None

```bash
WB_ROOT="$PWD" && OUT="$WB_ROOT/runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/gpt55/without/repeat_1" && RUNTIME="$OUT/nv_generate_runtime" && CFGDIR="$OUT/configs" && NV_ROOT="${NV_GENERATE_ROOT:?NV_GENERATE_ROOT must point to the NV-Generate-CTMR repo}" && mkdir -p "$OUT" "$RUNTIME" "$CFGDIR" && PYTHONPATH="$NV_ROOT${PYTHONPATH:+:$PYTHONPATH}" python -m scripts.download_model_data --version rflow-mr-brain --root_dir "$RUNTIME" --model_only && cp "$NV_ROOT/configs/config_network_rflow.json" "$CFGDIR/" && cp "$NV_ROOT/configs/environment_maisi_diff_model_rflow-mr-brain.json" "$CFGDIR/" && cp "$NV_ROOT/configs/config_maisi_diff_model_rflow-mr-brain.json" "$CFGDIR/" && python - "$OUT" "$CFGDIR/environment_maisi_diff_model_rflow-mr-brain.json" "$CFGDIR/config_maisi_diff_model_rflow-mr-brain.json" <<'PY' && cd "$RUNTIME" && PYTHONPATH="$NV_ROOT${PYTHONPATH:+:$PYTHONPATH}" python -m scripts.diff_model_infer -t "$CFGDIR/config_network_rflow.json" -e "$CFGDIR/environment_maisi_diff_model_rflow-mr-brain.json" -c "$CFGDIR/config_maisi_diff_model_rflow-mr-brain.json"
import json, sys
out, env_path, cfg_path = sys.argv[1:4]

def walk_set(obj, key, val):
    if isinstance(obj, dict):
        for k in list(obj):
            if k == key:
                obj[k] = val
            else:
                walk_set(obj[k], key, val)
    elif isinstance(obj, list):
        for x in obj:
            walk_set(x, key, val)

with open(env_path) as f:
    env = json.load(f)
walk_set(env, "output_dir", out)
with open(env_path, "w") as f:
    json.dump(env, f, indent=2)

with open(cfg_path) as f:
    cfg = json.load(f)

dui = cfg.setdefault("diffusion_unet_inference", {})
if "dim" in dui:
    dui["dim"] = [256, 256, 256]
if "spacing" in dui:
    dui["spacing"] = [1.0, 1.0, 1.0]
if "modality" in dui:
    dui["modality"] = 9
if "num_output_samples" in dui:
    dui["num_output_samples"] = 1
if "num_inference_steps" in dui:
    dui["num_inference_steps"] = 30

walk_set(cfg, "modality", 9)
for k in ("num_output_samples", "num_samples", "num_images"):
    walk_set(cfg, k, 1)
walk_set(cfg, "num_inference_steps", 30)

with open(cfg_path, "w") as f:
    json.dump(cfg, f, indent=2)
PY
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=None

```bash
set -euo pipefail && OUT="runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/gpt55/without/repeat_2" && REQ="runs/with_vs_without_nv/_inputs/nv_generate_mr_brain/request.json" && VARIANT="rflow-mr-brain" && NETWORK="rflow" && : "${NV_GENERATE_ROOT:?Set NV_GENERATE_ROOT to the NV-Generate-CTMR checkout root}" && NV_GENERATE_ROOT="$(cd "$NV_GENERATE_ROOT" && pwd)" && test -f "$REQ" && rm -rf "$OUT" && mkdir -p "$OUT/runtime/configs" "$OUT/runtime/model_root" && cp "$NV_GENERATE_ROOT/configs/config_network_${NETWORK}.json" "$OUT/runtime/configs/" && cp "$NV_GENERATE_ROOT/configs/environment_maisi_diff_model_${VARIANT}.json" "$OUT/runtime/configs/" && cp "$NV_GENERATE_ROOT/configs/config_maisi_diff_model_${VARIANT}.json" "$OUT/runtime/configs/" && python - "$REQ" "$OUT" "$OUT/runtime/configs/config_maisi_diff_model_${VARIANT}.json" "$OUT/runtime/configs/environment_maisi_diff_model_${VARIANT}.json" <<'PY' && (cd "$OUT/runtime/model_root" && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$NV_GENERATE_ROOT${PYTHONPATH:+:$PYTHONPATH}" python -m scripts.download_model_data --version "$VARIANT" --root_dir "./" --model_only && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$NV_GENERATE_ROOT${PYTHONPATH:+:$PYTHONPATH}" python -m scripts.diff_model_infer -t "../configs/config_network_${NETWORK}.json" -e "../configs/environment_maisi_diff_model_${VARIANT}.json" -c "../configs/config_maisi_diff_model_${VARIANT}.json")
import json, pathlib, sys
req_path, out_dir, cfg_path, env_path = map(pathlib.Path, sys.argv[1:5])
req = json.loads(req_path.read_text())

def first_scalar_by_key(obj, names):
    names = set(names)
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in names:
                if isinstance(v, (list, tuple)) and v:
                    return v[0]
                return v
        for v in obj.values():
            found = first_scalar_by_key(v, names)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = first_scalar_by_key(v, names)
            if found is not None:
                return found
    return None

def set_existing_key(obj, key, value):
    n = 0
    if isinstance(obj, dict):
        for k in list(obj):
            if k == key:
                obj[k] = value
                n += 1
            n += set_existing_key(obj[k], key, value)
    elif isinstance(obj, list):
        for v in obj:
            n += set_existing_key(v, key, value)
    return n

seed = first_scalar_by_key(req, ("random_seed", "seed"))
try:
    seed = int(seed) if seed is not None else 2
except Exception:
    seed = 2

cfg = json.loads(cfg_path.read_text())
du = cfg.setdefault("diffusion_unet_inference", {})
du["dim"] = [256, 256, 256]
du["spacing"] = [1.0, 1.0, 1.0]
du["modality"] = 9
du["num_output_samples"] = 1
du["random_seed"] = seed
set_existing_key(cfg, "dim", [256, 256, 256])
set_existing_key(cfg, "spacing", [1.0, 1.0, 1.0])
set_existing_key(cfg, "modality", 9)
set_existing_key(cfg, "num_output_samples", 1)
set_existing_key(cfg, "num_inference_steps", 30)
set_existing_key(cfg, "random_seed", seed)
cfg_path.write_text(json.dumps(cfg, indent=2) + "\n")

env = json.loads(env_path.read_text())
if set_existing_key(env, "output_dir", str(out_dir.resolve())) == 0:
    env["output_dir"] = str(out_dir.resolve())
env_path.write_text(json.dumps(env, indent=2) + "\n")
PY
```

Repeat 3: score 4/5, passed=no, steps=unresolved, exit=None

```bash
OUT="runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/gpt55/without/repeat_3" && RUNTIME="$OUT/_runtime/NV-Generate-CTMR" && mkdir -p "$OUT" && find "$OUT" -maxdepth 1 -type f \( -name "*.nii" -o -name "*.nii.gz" \) -delete && rm -rf "$RUNTIME" && mkdir -p "$OUT/_runtime" && cp -aL ".workbench_data/upstreams/NV-Generate-CTMR" "$RUNTIME" && cp "runs/with_vs_without_nv/_inputs/nv_generate_mr_brain/request.json" "$OUT/_runtime/request.json" && python -c $'import json, sys\nfrom pathlib import Path\nruntime = Path(sys.argv[1])\nreq_path = Path(sys.argv[2])\nrequest = json.loads(req_path.read_text())\ndef first_key(obj, keys):\n    if isinstance(obj, dict):\n        for k in keys:\n            if k in obj:\n                return obj[k]\n        for v in obj.values():\n            found = first_key(v, keys)\n            if found is not None:\n                return found\n    elif isinstance(obj, list):\n        for v in obj:\n            found = first_key(v, keys)\n            if found is not None:\n                return found\n    return None\nseed = first_key(request, ("random_seed", "seed"))\ntry:\n    seed = int(seed) if seed is not None else 3\nexcept Exception:\n    seed = 3\ndef replace_key(obj, key, value):\n    hit = False\n    if isinstance(obj, dict):\n        for k in list(obj.keys()):\n            if k == key:\n                obj[k] = value\n                hit = True\n            else:\n                hit = replace_key(obj[k], key, value) or hit\n    elif isinstance(obj, list):\n        for v in obj:\n            hit = replace_key(v, key, value) or hit\n    return hit\ncfg_path = runtime / "configs/config_maisi_diff_model_rflow-mr-brain.json"\nenv_path = runtime / "configs/environment_maisi_diff_model_rflow-mr-brain.json"\ncfg = json.loads(cfg_path.read_text())\nenv = json.loads(env_path.read_text())\nsettings = {"dim": [256, 256, 256], "spacing": [1.0, 1.0, 1.0], "modality": 9, "num_output_samples": 1, "num_inference_steps": 30, "random_seed": seed}\nfor k, v in settings.items():\n    replace_key(cfg, k, v)\nblock = cfg.setdefault("diffusion_unet_inference", {})\nblock.update(settings)\nfor k in ("num_samples", "num_images", "n_samples"):\n    replace_key(cfg, k, 1)\nreplace_key(cfg, "image_output_ext", ".nii.gz")\nif not replace_key(env, "output_dir", "../.."):\n    env["output_dir"] = "../.."\ncfg_path.write_text(json.dumps(cfg, indent=4) + "\\n")\nenv_path.write_text(json.dumps(env, indent=4) + "\\n")\n' "$RUNTIME" "runs/with_vs_without_nv/_inputs/nv_generate_mr_brain/request.json" && (cd "$RUNTIME" && python -m scripts.download_model_data --version rflow-mr-brain --root_dir "./" --model_only && python -m scripts.diff_model_infer -t ./configs/config_network_rflow.json -e ./configs/environment_maisi_diff_model_rflow-mr-brain.json -c ./configs/config_maisi_diff_model_rflow-mr-brain.json)
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

Repeat 1: score 4/5, passed=no, steps=unresolved, exit=1

```bash
set -euo pipefail && OUT=runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/opus/without/repeat_1 && REQ=runs/with_vs_without_nv/_inputs/nv_generate_mr_brain/request.json && SRC="${NV_GENERATE_ROOT:?NV_GENERATE_ROOT must be set}" && mkdir -p "$OUT/configs" "$OUT/output" && cp "$SRC/configs/config_network_rflow.json" "$OUT/configs/" && cp "$SRC/configs/config_maisi_diff_model_rflow-mr-brain.json" "$OUT/configs/" && cp "$SRC/configs/environment_maisi_diff_model_rflow-mr-brain.json" "$OUT/configs/" && python -c "
import json, os, pathlib
req = json.load(open('$REQ'))
cfg_path = '$OUT/configs/config_maisi_diff_model_rflow-mr-brain.json'
env_path = '$OUT/configs/environment_maisi_diff_model_rflow-mr-brain.json'
cfg = json.load(open(cfg_path))
env = json.load(open(env_path))
infer = cfg['diffusion_unet_inference']
infer['dim'] = req.get('dim', [256,256,256])
infer['spacing'] = req.get('spacing', [1.0,1.0,1.0])
infer['modality'] = req.get('modality', 9)
infer['num_output_samples'] = req.get('num_output_samples', 1)
if 'random_seed' in req: infer['random_seed'] = req['random_seed']
if 'num_inference_steps' in req: infer['num_inference_steps'] = req['num_inference_steps']
if 'cfg_guidance_scale' in req: infer['cfg_guidance_scale'] = req['cfg_guidance_scale']
out_abs = str(pathlib.Path('$OUT/output').resolve())
for k in ('output_dir','prediction_dir','results_dir'):
    if k in env: env[k] = out_abs
json.dump(cfg, open(cfg_path,'w'), indent=2)
json.dump(env, open(env_path,'w'), indent=2)
print('output_dir =', out_abs)
" && cd "$SRC" && (ls models/*rflow-mr-brain* >/dev/null 2>&1 || python -m scripts.download_model_data --version rflow-mr-brain --root_dir ./ --model_only) && cd - >/dev/null && (cd "$SRC" && python -m scripts.diff_model_infer -t "$OLDPWD/$OUT/configs/config_network_rflow.json" -e "$OLDPWD/$OUT/configs/environment_maisi_diff_model_rflow-mr-brain.json" -c "$OLDPWD/$OUT/configs/config_maisi_diff_model_rflow-mr-brain.json")
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=1

```bash
mkdir -p runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/opus/without/repeat_2 && OUT_DIR="$(pwd)/runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/opus/without/repeat_2" && STAGE_DIR="${OUT_DIR}/_staged_configs" && mkdir -p "${STAGE_DIR}" && cd "${NV_GENERATE_ROOT}" && python -m scripts.download_model_data --version rflow-mr-brain --root_dir "./" --model_only && python - <<'PY'
import json, os, shutil
req = json.load(open(os.path.join(os.environ['OLDPWD'], 'runs/with_vs_without_nv/_inputs/nv_generate_mr_brain/request.json')))
stage = os.environ['STAGE_DIR']
src_env = 'configs/environment_maisi_diff_model_rflow-mr-brain.json'
src_cfg = 'configs/config_maisi_diff_model_rflow-mr-brain.json'
dst_env = os.path.join(stage, 'environment_maisi_diff_model_rflow-mr-brain.json')
dst_cfg = os.path.join(stage, 'config_maisi_diff_model_rflow-mr-brain.json')
shutil.copy(src_env, dst_env)
shutil.copy(src_cfg, dst_cfg)
env = json.load(open(dst_env))
env['output_dir'] = os.environ['OUT_DIR']
json.dump(env, open(dst_env, 'w'), indent=2)
cfg = json.load(open(dst_cfg))
dmi = cfg['diffusion_unet_inference']
dmi['dim'] = [256, 256, 256]
dmi['spacing'] = [1.0, 1.0, 1.0]
dmi['num_output_samples'] = 1
cfg['modality'] = 9
for k in ('random_seed','num_inference_steps','cfg_guidance_scale','modality','dim','spacing','num_output_samples'):
    if k in req:
        if k in ('dim','spacing','num_output_samples','num_inference_steps','cfg_guidance_scale','random_seed'):
            dmi[k] = req[k]
        else:
            cfg[k] = req[k]
json.dump(cfg, open(dst_cfg, 'w'), indent=2)
PY
 export OLDPWD && python -m scripts.diff_model_infer -t ./configs/config_network_rflow.json -e "${STAGE_DIR}/environment_maisi_diff_model_rflow-mr-brain.json" -c "${STAGE_DIR}/config_maisi_diff_model_rflow-mr-brain.json"
```

Repeat 3: score 3/5, passed=no, steps=unresolved, exit=None

```bash
set -euo pipefail && OUT=runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/opus/without/repeat_3 && mkdir -p "$OUT/configs" "$OUT/output" && cd "$NV_GENERATE_ROOT" && python -m scripts.download_model_data --version rflow-mr-brain --root_dir "./" --model_only && cd - >/dev/null && cp "$NV_GENERATE_ROOT/configs/config_network_rflow.json" "$OUT/configs/config_network_rflow.json" && cp "$NV_GENERATE_ROOT/configs/environment_maisi_diff_model_rflow-mr-brain.json" "$OUT/configs/environment_maisi_diff_model_rflow-mr-brain.json" && cp "$NV_GENERATE_ROOT/configs/config_maisi_diff_model_rflow-mr-brain.json" "$OUT/configs/config_maisi_diff_model_rflow-mr-brain.json" && python -c "import json,os; p='$OUT/configs/environment_maisi_diff_model_rflow-mr-brain.json'; d=json.load(open(p)); d['output_dir']=os.path.abspath('$OUT/output'); json.dump(d,open(p,'w'),indent=2)" && python -c "import json; p='$OUT/configs/config_maisi_diff_model_rflow-mr-brain.json'; d=json.load(open(p)); d['diffusion_unet_inference']['dim']=[256,256,256]; d['diffusion_unet_inference']['spacing']=[1.0,1.0,1.0]; d['diffusion_unet_inference']['modality']=9; d['diffusion_unet_inference']['num_output_samples']=1; json.dump(d,open(p,'w'),indent=2)" && cd "$NV_GENERATE_ROOT" && python -m scripts.diff_model_infer -t "$OLDPWD/$OUT/configs/config_network_rflow.json" -e "$OLDPWD/$OUT/configs/environment_maisi_diff_model_rflow-mr-brain.json" -c "$OLDPWD/$OUT/configs/config_maisi_diff_model_rflow-mr-brain.json"
```

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `examples/studies/with_vs_without_skill/nv_generate_mr_brain_codex_opus/` |
| Generated outputs | `runs/with_vs_without_nv/nv_generate_mr_brain_codex_opus/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_generate_mr_brain_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
