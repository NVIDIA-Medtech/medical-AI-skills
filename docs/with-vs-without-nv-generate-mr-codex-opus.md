# `nv_generate_mr`: Codex/Opus LLM+SKILL.md vs LLM+README

Status: strict audit passed for refreshed artifacts on May 28, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

This report compares `LLM + SKILL.md` with `LLM + upstream README/guide`. The completed direct-API run used the corrected embedded-doc minimal prompt because those backends cannot read repo files. The fair NAT/tool-agent prompt artifact is A2-style: it gives a natural user request, a neutral staged input path, an output directory, and tells the agent which arm-specific document to read. It does not spell out operational details such as entrypoints, labels, model variants, or config filenames outside the documentation arm.

## Experiment Question

Does `LLM + SKILL.md` make an agent better at reading documentation and taking the right action than `LLM + upstream README/guide`?

## User Request Shape

The prompt request for the GPT-5.5 with-skill arm was:

> The image-generation request is at runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json. Generate one T1 MR image and write generated NIfTI volumes under runs/with_vs_without_nv/nv_generate_mr_codex_opus/gpt55/with/repeat_1.

The staged user input for every arm was `runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json`. The source fixture `skills/nv-generate-mr/fixtures/default_mri_t1.json` was used only to stage that neutral input path.

Fair path-prompt artifact: `tools/nat_audit/data/eval_nv_model_studies_nv_generate_mr_prompts.json`

## Result

| Backend | Arm | Mean score | Passes | Steps | Exit | Tier 5 | Failed tiers |
|---|---|---:|---:|---|---|---|---|
| GPT-5.5 / Codex | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | shape=(128, 256, 256) (3) | none |
| GPT-5.5 / Codex | without | 4.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | None (3) | blocked unsafe command fragment: rm (3) | T5: blocked unsafe command fragment: rm (3) |
| Opus 4.7 | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | shape=(128, 256, 256) (3) | none |
| Opus 4.7 | without | 4.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | 1 (3) | exit 1 (3) | T5: exit 1 (3) |

## Analysis

SKILL.md paired advantage: the with-skill arms passed 6/6 backend-repeat trials with an average score of 5.0/5; the README-only arms passed 0/6 backend-repeat trials with an average score of 4.0/5.

SKILL.md paired advantage: SKILL.md wins 6/6 matched backend-repeat pairs, README-only wins 0/6, and 0/6 are ties. Pass/fail is the primary outcome; score breaks ties only when pass status is equal. Exact one-sided sign-test p=0.01562 across 6 decisive pair(s).

Outcome-support gate: Supports SKILL.md advantage. SKILL.md wins 6/6 matched pair(s); README-only wins 0/6; sign-test p=0.01562.

Each backend/arm/skill configuration was repeated three times. A repeat is independent: it has its own output directory, and each execution attempt inside the repeat creates a fresh venv before running the generated command. Dependency and model download caches are shared only as documented test-environment caches under `.workbench_data/with_vs_without_cache` (`PIP_CACHE_DIR=.workbench_data/with_vs_without_cache/pip`, `HF_HOME=.workbench_data/with_vs_without_cache/huggingface`, `HF_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `HUGGINGFACE_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `TRANSFORMERS_CACHE=.workbench_data/with_vs_without_cache/huggingface/transformers`, `TORCH_HOME=.workbench_data/with_vs_without_cache/torch`, `XDG_CACHE_HOME=.workbench_data/with_vs_without_cache/xdg`, `CONDA_PKGS_DIRS=.workbench_data/with_vs_without_cache/conda_pkgs`, `UV_CACHE_DIR=.workbench_data/with_vs_without_cache/uv`, `CUDA_CACHE_PATH=.workbench_data/with_vs_without_cache/cuda`, `NUMBA_CACHE_DIR=.workbench_data/with_vs_without_cache/numba`).

The main baseline uses `max_correction_steps=0`: each repeat sends one prompt, executes the extracted command once, and records pass/fail, runtime, tokens, and deterministic failure analysis. The repair-loop implementation remains available for separate diagnostic experiments, but it is not part of this comparison.

All with-skill repeats exited successfully and produced artifacts accepted by the deterministic grader. That means the final SKILL.md surface was repeatable for both tested agent backends.

The README-only commands did not pass tier 5. Typical failure modes were unsafe generated shell cleanup, missing schema fields, missing model/control details, or upstream commands that did not execute cleanly from Medical AI Skills root.

Tier 2 is intentionally strict: a command only earns it if it uses the staged user input path `runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json`.

## Token Profiling

Token counts are provider-reported values saved in each repeat JSON. Reasoning tokens are shown only when the provider returned that subfield and are a subset of completion tokens, not an additional cost to add to total tokens. Execution time is averaged only across repeats that reached command execution; no-command-extracted repeats still count toward token totals.

| Backend | Arm | Repeats | Passes | Attempts | Prompt tokens | Completion tokens | Reasoning tokens | Total tokens | Mean total/repeat | Executed | Mean exec s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GPT-5.5 / Codex | with | 3 | 3 | 3 | 6,042 | 1,309 | 934 | 7,351 | 2,450.3 | 3 | 43.3 |
| GPT-5.5 / Codex | without | 3 | 0 | 3 | 8,874 | 16,681 | 13,314 | 25,555 | 8,518.3 | 0 | n/a |
| Opus 4.7 | with | 3 | 3 | 3 | 10,419 | 643 | 0 | 11,062 | 3,687.3 | 3 | 43.5 |
| Opus 4.7 | without | 3 | 0 | 3 | 13,161 | 3,149 | 0 | 16,310 | 5,436.7 | 3 | 0.0 |

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
| 3 | 0 | 4/5 | no | 1 | T5: exit 1 | tier_5: exit 1 Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>nonzero_exit: Command exited 1. Repair: Use stderr/stdout to repair setup, paths, arguments, or runtime package installation. |

## Skill Fix Notes

Before the final rerun, `SKILL.md` was tightened to name `scripts/run_mr.py` as the exact runnable surface, preserve the staged request path, and avoid invented module or shell entrypoints.

## Generated Commands

These are the extracted first-attempt commands by repeat.

### GPT-5.5 / Codex, with arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-mr/scripts/run_mr.py runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json --output-dir runs/with_vs_without_nv/nv_generate_mr_codex_opus/gpt55/with/repeat_1 --modality mri_t1 --random-seed 0
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-mr/scripts/run_mr.py runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json --output-dir runs/with_vs_without_nv/nv_generate_mr_codex_opus/gpt55/with/repeat_2 --modality mri_t1 --random-seed 2
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-mr/scripts/run_mr.py runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json --output-dir runs/with_vs_without_nv/nv_generate_mr_codex_opus/gpt55/with/repeat_3 --modality mri_t1 --random-seed 3
```

### GPT-5.5 / Codex, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 4/5, passed=no, steps=unresolved, exit=None

```bash
OUT='runs/with_vs_without_nv/nv_generate_mr_codex_opus/gpt55/without/repeat_1' && REQ='runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json' && NV_ROOT="$(cd "${NV_GENERATE_ROOT:?NV_GENERATE_ROOT must point to the NV-Generate-CTMR repo root}" && pwd -P)" && STAGE="$OUT/_nv_generate_mr_runtime" && rm -rf "$STAGE" && mkdir -p "$STAGE" && cp -a "$NV_ROOT/configs" "$STAGE/" && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$NV_ROOT${PYTHONPATH:+:$PYTHONPATH}" python -m scripts.download_model_data --version rflow-mr-brain --root_dir "$STAGE" --model_only && PYTHONDONTWRITEBYTECODE=1 python - "$REQ" "$STAGE/configs/config_maisi_diff_model_rflow-mr-brain.json" "$STAGE/configs/environment_maisi_diff_model_rflow-mr-brain.json" <<'PY' && (cd "$STAGE" && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$NV_ROOT${PYTHONPATH:+:$PYTHONPATH}" python -m scripts.diff_model_infer -t ./configs/config_network_rflow.json -e ./configs/environment_maisi_diff_model_rflow-mr-brain.json -c ./configs/config_maisi_diff_model_rflow-mr-brain.json)
import json, sys
from pathlib import Path

req_path, cfg_path, env_path = map(Path, sys.argv[1:4])
req = json.loads(req_path.read_text())

def find_key(obj, names):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() in names:
                return v
        for v in obj.values():
            found = find_key(v, names)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = find_key(v, names)
            if found is not None:
                return found
    return None

def numeric_triplet(v):
    if isinstance(v, (list, tuple)) and len(v) == 3:
        try:
            return [int(x) if float(x).is_integer() else float(x) for x in v]
        except Exception:
            return None
    return None

def valid_mr_dim(dim):
    if not (isinstance(dim, list) and len(dim) == 3):
        return False
    if sum(dim.count(x) >= 2 for x in set(dim)) < 1:
        return False
    if dim[2] == 128:
        return dim[0] == dim[1] and dim[0] in {128, 256, 384, 512}
    if dim[2] == 256:
        return dim in ([128, 256, 256], [256, 128, 256], [256, 256, 256])
    return False

def valid_mr_spacing(spacing):
    return isinstance(spacing, list) and len(spacing) == 3 and all(0.4 <= float(x) <= 5.0 for x in spacing)

dim = numeric_triplet(find_key(req, {"dim", "dims", "dimension", "dimensions", "image_size", "spatial_size"})) or [256, 256, 256]
spacing = numeric_triplet(find_key(req, {"spacing", "voxel_spacing", "pixdim"})) or [1.0, 1.0, 1.0]
if not valid_mr_dim(dim):
    dim = [256, 256, 256]
if not valid_mr_spacing(spacing):
    spacing = [1.0, 1.0, 1.0]

seed = find_key(req, {"seed", "random_seed"})
try:
    seed = int(seed)
except Exception:
    seed = 1

cfg = json.loads(cfg_path.read_text())
env = json.loads(env_path.read_text())

diff = cfg.setdefault("diffusion_unet_inference", {})
diff["dim"] = dim
diff["spacing"] = spacing
diff["modality"] = 9
diff["num_inference_steps"] = 30
diff["random_seed"] = seed
diff.setdefault("num_output_samples", 1)

sample_keys = {"num_output_samples", "num_samples", "n_samples", "num_images", "num_generated_images", "batch_size"}
def force_one(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() in sample_keys and isinstance(v, int):
                obj[k] = 1
            else:
                force_one(v)
    elif isinstance(obj, list):
        for v in obj:
            force_one(v)

def set_output_dir(obj):
    n = 0
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() == "output_dir":
                obj[k] = ".."
                n += 1
            else:
                n += set_output_dir(v)
    elif isinstance(obj, list):
        for v in obj:
            n += set_output_dir(v)
    return n

force_one(cfg)
force_one(env)
if set_output_dir(env) == 0:
    env["output_dir"] = ".."
set_output_dir(cfg)

cfg_path.write_text(json.dumps(cfg, indent=4) + "\n")
env_path.write_text(json.dumps(env, indent=4) + "\n")
PY
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=None

```bash
ROOT="$(pwd)" && OUT="runs/with_vs_without_nv/nv_generate_mr_codex_opus/gpt55/without/repeat_2" && REQ="runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json" && NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && NV_GENERATE_ROOT="$(cd "$NV_GENERATE_ROOT" && pwd)" && rm -rf "$OUT" && mkdir -p "$OUT" && python - "$REQ" "$OUT" "$NV_GENERATE_ROOT" <<'PY' && . "$OUT/run.env" && (cd "$OUT" && PYTHONPATH="$NV_GENERATE_ROOT${PYTHONPATH:+:$PYTHONPATH}" python -m scripts.download_model_data --version "$generate_version" --root_dir "./" --model_only && PYTHONPATH="$NV_GENERATE_ROOT${PYTHONPATH:+:$PYTHONPATH}" python -m scripts.diff_model_infer -t "./configs/config_network_${network}.json" -e "./configs/environment_maisi_diff_model_${generate_version}.json" -c "./configs/config_maisi_diff_model_${generate_version}.json")
import json, os, re, shutil, sys
from pathlib import Path

req_path = Path(sys.argv[1])
out = Path(sys.argv[2])
src = Path(sys.argv[3])
req = json.loads(req_path.read_text()) if req_path.exists() else {}

def walk_values(x):
    if isinstance(x, dict):
        for v in x.values():
            yield from walk_values(v)
    elif isinstance(x, list):
        for v in x:
            yield from walk_values(v)
    else:
        yield x

text = " ".join(str(v).lower() for v in walk_values(req))
generate_version = "rflow-mr-brain"
network = "rflow"
dim = [256, 256, 256]
spacing = [1.0, 1.0, 1.0]
modality = 9
if "skull" in text and "strip" in text:
    modality = 29

def first_key(obj, names):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in names:
                return v
            got = first_key(v, names)
            if got is not None:
                return got
    elif isinstance(obj, list):
        for v in obj:
            got = first_key(v, names)
            if got is not None:
                return got
    return None

seed = first_key(req, {"seed", "random_seed"})
try:
    seed = int(seed)
except Exception:
    seed = 2

cfgdir = out / "configs"
cfgdir.mkdir(parents=True, exist_ok=True)
for name in [
    "config_network_rflow.json",
    f"environment_maisi_diff_model_{generate_version}.json",
    f"config_maisi_diff_model_{generate_version}.json",
]:
    shutil.copy2(src / "configs" / name, cfgdir / name)

cfg_path = cfgdir / f"config_maisi_diff_model_{generate_version}.json"
cfg = json.loads(cfg_path.read_text())
infer = cfg.setdefault("diffusion_unet_inference", {})
infer["dim"] = dim
infer["spacing"] = spacing
infer["modality"] = modality
infer["num_output_samples"] = 1
infer["num_inference_steps"] = 30
infer["random_seed"] = seed
cfg_path.write_text(json.dumps(cfg, indent=2) + "\n")

env_path = cfgdir / f"environment_maisi_diff_model_{generate_version}.json"
env = json.loads(env_path.read_text())
def set_output_dirs(x):
    if isinstance(x, dict):
        for k, v in list(x.items()):
            if k == "output_dir":
                x[k] = "."
            else:
                set_output_dirs(v)
    elif isinstance(x, list):
        for v in x:
            set_output_dirs(v)
set_output_dirs(env)
env.setdefault("output_dir", ".")
env_path.write_text(json.dumps(env, indent=2) + "\n")

(out / "run.env").write_text(f'network="{network}"\ngenerate_version="{generate_version}"\n')
PY
```

Repeat 3: score 4/5, passed=no, steps=unresolved, exit=None

```bash
export PYTHONDONTWRITEBYTECODE=1 && export REPO_ROOT="$(pwd)" && export NVG_ROOT_ABS="$(python -c 'import os, pathlib; print(pathlib.Path(os.environ.get("NV_GENERATE_ROOT", ".workbench_data/upstreams/NV-Generate-CTMR")).resolve())')" && export OUT="runs/with_vs_without_nv/nv_generate_mr_codex_opus/gpt55/without/repeat_3" && rm -rf "$OUT" && mkdir -p "$OUT/runtime/configs" && python - <<'PY' && (cd "$NVG_ROOT_ABS" && PYTHONPATH="$NVG_ROOT_ABS" python -m scripts.download_model_data --version rflow-mr-brain --root_dir "$REPO_ROOT/$OUT/runtime" --model_only && PYTHONPATH="$NVG_ROOT_ABS" python -m scripts.diff_model_infer -t "$REPO_ROOT/$OUT/runtime/configs/config_network_rflow.json" -e "$REPO_ROOT/$OUT/runtime/configs/environment_maisi_diff_model_rflow-mr-brain.json" -c "$REPO_ROOT/$OUT/runtime/configs/config_maisi_diff_model_rflow-mr-brain.json")
import json, os, shutil
from pathlib import Path

repo = Path(os.environ["REPO_ROOT"])
src_root = Path(os.environ["NVG_ROOT_ABS"])
out = repo / os.environ["OUT"]
runtime = out / "runtime"
cfg_dir = runtime / "configs"
request_path = repo / "runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json"

for name in [
    "config_network_rflow.json",
    "environment_maisi_diff_model_rflow-mr-brain.json",
    "config_maisi_diff_model_rflow-mr-brain.json",
]:
    shutil.copy2(src_root / "configs" / name, cfg_dir / name)

try:
    request = json.loads(request_path.read_text())
except FileNotFoundError:
    request = {}

def find_key(obj, names):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in names:
                return v
        for v in obj.values():
            found = find_key(v, names)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = find_key(v, names)
            if found is not None:
                return found
    return None

seed = find_key(request, {"seed", "random_seed", "randomSeed"})
try:
    seed = int(seed)
except Exception:
    seed = 3

config_path = cfg_dir / "config_maisi_diff_model_rflow-mr-brain.json"
config = json.loads(config_path.read_text())

def update_generation_config(obj):
    if isinstance(obj, dict):
        if isinstance(obj.get("diffusion_unet_inference"), dict):
            d = obj["diffusion_unet_inference"]
            d["dim"] = [256, 256, 256]
            d["spacing"] = [1.0, 1.0, 1.0]
            d["modality"] = 9
            d["num_inference_steps"] = 30
            d["num_output_samples"] = 1
            d["random_seed"] = seed
            if "output_size" in d:
                d["output_size"] = [256, 256, 256]
        for k in list(obj):
            if k in {"modality"}:
                obj[k] = 9
            elif k in {"num_inference_steps"}:
                obj[k] = 30
            elif k in {"num_output_samples", "num_samples", "n_samples", "batch_size"}:
                obj[k] = 1
            elif k in {"random_seed", "seed"}:
                obj[k] = seed
            update_generation_config(obj[k])
    elif isinstance(obj, list):
        for v in obj:
            update_generation_config(v)

update_generation_config(config)
config_path.write_text(json.dumps(config, indent=2) + "\n")

env_path = cfg_dir / "environment_maisi_diff_model_rflow-mr-brain.json"
env = json.loads(env_path.read_text())

def rewrite_env_paths(obj):
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            kl = k.lower()
            if isinstance(v, str):
                if kl in {"output_dir", "output_path", "save_dir", "save_path"}:
                    obj[k] = str(out)
                elif (
                    any(tok in kl for tok in ["model", "ckpt", "checkpoint", "trained", "autoencoder"])
                    and not v.startswith(("http://", "https://", "/"))
                    and ("/" in v or "\\" in v or v.startswith(".") or kl.endswith("_dir") or v.endswith((".pt", ".pth", ".ckpt", ".json")))
                ):
                    obj[k] = str(runtime / v)
            else:
                rewrite_env_paths(v)
    elif isinstance(obj, list):
        for v in obj:
            rewrite_env_paths(v)

rewrite_env_paths(env)
env["output_dir"] = str(out)
env_path.write_text(json.dumps(env, indent=2) + "\n")
PY
```

### Opus 4.7, with arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-mr/scripts/run_mr.py runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json --output-dir runs/with_vs_without_nv/nv_generate_mr_codex_opus/opus/with/repeat_1 --modality mri_t1 --random-seed 0
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-mr/scripts/run_mr.py runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json --output-dir runs/with_vs_without_nv/nv_generate_mr_codex_opus/opus/with/repeat_2 --modality mri_t1 --random-seed 0 --yes
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-mr/scripts/run_mr.py runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json --output-dir runs/with_vs_without_nv/nv_generate_mr_codex_opus/opus/with/repeat_3 --modality mri_t1 --random-seed 0
```

### Opus 4.7, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 4/5, passed=no, steps=unresolved, exit=1

```bash
set -euo pipefail && REQ=runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json && OUT=runs/with_vs_without_nv/nv_generate_mr_codex_opus/opus/without/repeat_1 && NV_ROOT="${NV_GENERATE_ROOT:?set NV_GENERATE_ROOT}" && mkdir -p "$OUT/configs" "$OUT/output" && cd "$NV_ROOT" && python -m scripts.download_model_data --version rflow-mr-brain --root_dir ./ --model_only && cd - >/dev/null && cp "$NV_ROOT/configs/config_network_rflow.json" "$OUT/configs/" && cp "$NV_ROOT/configs/environment_maisi_diff_model_rflow-mr-brain.json" "$OUT/configs/environment.json" && cp "$NV_ROOT/configs/config_maisi_diff_model_rflow-mr-brain.json" "$OUT/configs/config.json" && python -c "
import json, os, pathlib
req = json.load(open('$REQ'))
out = pathlib.Path('$OUT').resolve()
env_p = out/'configs'/'environment.json'
cfg_p = out/'configs'/'config.json'
env = json.load(open(env_p))
env['output_dir'] = str(out/'output')
json.dump(env, open(env_p,'w'), indent=2)
cfg = json.load(open(cfg_p))
inf = cfg['diffusion_unet_inference']
inf['dim'] = req.get('dim', [256,256,256])
inf['spacing'] = req.get('spacing', [1.0,1.0,1.0])
inf['modality'] = req.get('modality', 9)
inf['num_output_samples'] = 1
if 'random_seed' in req: inf['random_seed'] = req['random_seed']
if 'num_inference_steps' in req: inf['num_inference_steps'] = req['num_inference_steps']
if 'cfg_guidance_scale' in req: inf['cfg_guidance_scale'] = req['cfg_guidance_scale']
json.dump(cfg, open(cfg_p,'w'), indent=2)
print('staged:', cfg_p, env_p)
" && cd "$NV_ROOT" && python -m scripts.diff_model_infer -t ./configs/config_network_rflow.json -e "$OLDPWD/$OUT/configs/environment.json" -c "$OLDPWD/$OUT/configs/config.json"
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=1

```bash
mkdir -p runs/with_vs_without_nv/nv_generate_mr_codex_opus/opus/without/repeat_2 && cp .workbench_data/upstreams/NV-Generate-CTMR/configs/config_network_rflow.json runs/with_vs_without_nv/nv_generate_mr_codex_opus/opus/without/repeat_2/config_network_rflow.json && cp .workbench_data/upstreams/NV-Generate-CTMR/configs/environment_maisi_diff_model_rflow-mr.json runs/with_vs_without_nv/nv_generate_mr_codex_opus/opus/without/repeat_2/environment_maisi_diff_model_rflow-mr.json && cp .workbench_data/upstreams/NV-Generate-CTMR/configs/config_maisi_diff_model_rflow-mr.json runs/with_vs_without_nv/nv_generate_mr_codex_opus/opus/without/repeat_2/config_maisi_diff_model_rflow-mr.json && python -c "import json,os; req=json.load(open('runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json')); cfg_path='runs/with_vs_without_nv/nv_generate_mr_codex_opus/opus/without/repeat_2/config_maisi_diff_model_rflow-mr.json'; cfg=json.load(open(cfg_path)); cfg['diffusion_unet_inference']['dim']=req.get('dim',cfg['diffusion_unet_inference'].get('dim')); cfg['diffusion_unet_inference']['spacing']=req.get('spacing',cfg['diffusion_unet_inference'].get('spacing')); cfg['diffusion_unet_inference']['num_output_samples']=1; cfg['modality']=9; json.dump(cfg,open(cfg_path,'w'),indent=2); env_path='runs/with_vs_without_nv/nv_generate_mr_codex_opus/opus/without/repeat_2/environment_maisi_diff_model_rflow-mr.json'; env=json.load(open(env_path)); out=os.path.abspath('runs/with_vs_without_nv/nv_generate_mr_codex_opus/opus/without/repeat_2'); env['output_dir']=out; json.dump(env,open(env_path,'w'),indent=2); print('staged',req)" && (cd "$NV_GENERATE_ROOT" && python -m scripts.download_model_data --version rflow-mr --root_dir "./" --model_only && python -m scripts.diff_model_infer -t "$OLDPWD/runs/with_vs_without_nv/nv_generate_mr_codex_opus/opus/without/repeat_2/config_network_rflow.json" -e "$OLDPWD/runs/with_vs_without_nv/nv_generate_mr_codex_opus/opus/without/repeat_2/environment_maisi_diff_model_rflow-mr.json" -c "$OLDPWD/runs/with_vs_without_nv/nv_generate_mr_codex_opus/opus/without/repeat_2/config_maisi_diff_model_rflow-mr.json")
```

Repeat 3: score 4/5, passed=no, steps=unresolved, exit=1

```bash
OUT=runs/with_vs_without_nv/nv_generate_mr_codex_opus/opus/without/repeat_3 && REQ=runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json && mkdir -p "$OUT" && cd .workbench_data/upstreams/NV-Generate-CTMR && python -m scripts.download_model_data --version rflow-mr-brain --root_dir ./ --model_only && cd - && STAGE="$OUT/configs" && mkdir -p "$STAGE" && cp .workbench_data/upstreams/NV-Generate-CTMR/configs/config_network_rflow.json "$STAGE/" && cp .workbench_data/upstreams/NV-Generate-CTMR/configs/environment_maisi_diff_model_rflow-mr-brain.json "$STAGE/environment_maisi_diff_model_rflow-mr-brain.json" && cp .workbench_data/upstreams/NV-Generate-CTMR/configs/config_maisi_diff_model_rflow-mr-brain.json "$STAGE/config_maisi_diff_model_rflow-mr-brain.json" && python -c "
import json, os, sys
req = json.load(open('$REQ'))
env_p = '$STAGE/environment_maisi_diff_model_rflow-mr-brain.json'
cfg_p = '$STAGE/config_maisi_diff_model_rflow-mr-brain.json'
env = json.load(open(env_p))
cfg = json.load(open(cfg_p))
out_abs = os.path.abspath('$OUT')
env['output_dir'] = out_abs
inf = cfg.get('diffusion_unet_inference', cfg)
inf['dim'] = req.get('dim', [256,256,256])
inf['spacing'] = req.get('spacing', [1.0,1.0,1.0])
inf['num_output_samples'] = 1
cfg['modality'] = 9
if 'random_seed' in req: cfg['random_seed'] = req['random_seed']
json.dump(env, open(env_p,'w'), indent=2)
json.dump(cfg, open(cfg_p,'w'), indent=2)
print('staged configs ->', out_abs)
" && cd .workbench_data/upstreams/NV-Generate-CTMR && python -m scripts.diff_model_infer -t "$OLDPWD/$STAGE/config_network_rflow.json" -e "$OLDPWD/$STAGE/environment_maisi_diff_model_rflow-mr-brain.json" -c "$OLDPWD/$STAGE/config_maisi_diff_model_rflow-mr-brain.json"
```

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `examples/studies/with_vs_without_skill/nv_generate_mr_codex_opus/` |
| Generated outputs | `runs/with_vs_without_nv/nv_generate_mr_codex_opus/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_generate_mr_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
