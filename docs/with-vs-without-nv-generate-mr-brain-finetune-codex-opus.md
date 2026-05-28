# `nv_generate_mr_brain_finetune`: Codex/Opus LLM+SKILL.md vs LLM+README

Status: strict audit passed for refreshed artifacts on May 28, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

This report compares `LLM + SKILL.md` with `LLM + upstream README/guide`. The completed direct-API run used the corrected embedded-doc minimal prompt because those backends cannot read repo files. The fair NAT/tool-agent prompt artifact is A2-style: it gives a natural user request, a neutral staged input path, an output directory, and tells the agent which arm-specific document to read. It does not spell out operational details such as entrypoints, labels, model variants, or config filenames outside the documentation arm.

## Experiment Question

Does `LLM + SKILL.md` make an agent better at reading documentation and taking the right action than `LLM + upstream README/guide`?

## User Request Shape

The prompt request for the GPT-5.5 with-skill arm was:

> The MR-brain finetuning preflight input bundle is at runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset. Validate and stage the shortest preflight-scale workflow check, and write outputs under runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/gpt55/with/repeat_1.

The staged user input for every arm was `runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset`. The source fixture `skills/nv-generate-mr-brain-finetune/fixtures` was used only to stage that neutral input path.

Fair path-prompt artifact: `tools/nat_audit/data/eval_nv_model_studies_nv_generate_mr_brain_finetune_prompts.json`

## Result

| Backend | Arm | Mean score | Passes | Steps | Exit | Tier 5 | Failed tiers |
|---|---|---:|---:|---|---|---|---|
| GPT-5.5 / Codex | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | preflight payload reported (3) | none |
| GPT-5.5 / Codex | without | 4.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | 1 (3) | exit 1 (3) | T5: exit 1 (3) |
| Opus 4.7 | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | preflight payload reported (3) | none |
| Opus 4.7 | without | 1.7/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | None (3) | command does not reference the expected output directory (2); command does not reference an expected runnable surface (1) | T1: entrypoint marker (3); T2: user input path marker (2); T4: output dir marker (2) |

## Analysis

SKILL.md paired advantage: the with-skill arms passed 6/6 backend-repeat trials with an average score of 5.0/5; the README-only arms passed 0/6 backend-repeat trials with an average score of 2.8/5.

SKILL.md paired advantage: SKILL.md wins 6/6 matched backend-repeat pairs, README-only wins 0/6, and 0/6 are ties. Pass/fail is the primary outcome; score breaks ties only when pass status is equal. Exact one-sided sign-test p=0.01562 across 6 decisive pair(s).

Outcome-support gate: Supports SKILL.md advantage. SKILL.md wins 6/6 matched pair(s); README-only wins 0/6; sign-test p=0.01562.

Each backend/arm/skill configuration was repeated three times. A repeat is independent: it has its own output directory, and each execution attempt inside the repeat creates a fresh venv before running the generated command. Dependency and model download caches are shared only as documented test-environment caches under `.workbench_data/with_vs_without_cache` (`PIP_CACHE_DIR=.workbench_data/with_vs_without_cache/pip`, `HF_HOME=.workbench_data/with_vs_without_cache/huggingface`, `HF_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `HUGGINGFACE_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `TRANSFORMERS_CACHE=.workbench_data/with_vs_without_cache/huggingface/transformers`, `TORCH_HOME=.workbench_data/with_vs_without_cache/torch`, `XDG_CACHE_HOME=.workbench_data/with_vs_without_cache/xdg`, `CONDA_PKGS_DIRS=.workbench_data/with_vs_without_cache/conda_pkgs`, `UV_CACHE_DIR=.workbench_data/with_vs_without_cache/uv`, `CUDA_CACHE_PATH=.workbench_data/with_vs_without_cache/cuda`, `NUMBA_CACHE_DIR=.workbench_data/with_vs_without_cache/numba`).

The main baseline uses `max_correction_steps=0`: each repeat sends one prompt, executes the extracted command once, and records pass/fail, runtime, tokens, and deterministic failure analysis. The repair-loop implementation remains available for separate diagnostic experiments, but it is not part of this comparison.

All with-skill repeats exited successfully and produced artifacts accepted by the deterministic grader. That means the final SKILL.md surface was repeatable for both tested agent backends.

The README-only commands did not pass tier 5. Typical failure modes were unsafe generated shell cleanup, missing schema fields, missing model/control details, or upstream commands that did not execute cleanly from Medical AI Skills root.

Tier 2 is intentionally strict: a command only earns it if it uses the staged user input path `runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset`.

## Token Profiling

Token counts are provider-reported values saved in each repeat JSON. Reasoning tokens are shown only when the provider returned that subfield and are a subset of completion tokens, not an additional cost to add to total tokens. Execution time is averaged only across repeats that reached command execution; no-command-extracted repeats still count toward token totals.

| Backend | Arm | Repeats | Passes | Attempts | Prompt tokens | Completion tokens | Reasoning tokens | Total tokens | Mean total/repeat | Executed | Mean exec s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GPT-5.5 / Codex | with | 3 | 3 | 3 | 5,070 | 1,847 | 1,308 | 6,917 | 2,305.7 | 3 | 0.0 |
| GPT-5.5 / Codex | without | 3 | 0 | 3 | 3,249 | 15,730 | 8,614 | 18,979 | 6,326.3 | 3 | 0.0 |
| Opus 4.7 | with | 3 | 3 | 3 | 8,811 | 895 | 0 | 9,706 | 3,235.3 | 3 | 0.0 |
| Opus 4.7 | without | 3 | 0 | 3 | 5,445 | 3,920 | 0 | 9,365 | 3,121.7 | 0 | n/a |

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
| 1 | 0 | 4/5 | no | 1 | T5: exit 1 | tier_5: exit 1 Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>nonzero_exit: Command exited 1. Repair: Use stderr/stdout to repair setup, paths, arguments, or runtime package installation. |
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
| 1 | 0 | 1/5 | no | None | T1: entrypoint marker; T2: user input path marker; T4: output dir marker; T5: command does not reference the expected output directory | tier_1: entrypoint marker Repair: Use the runnable surface documented for this arm.<br>tier_2: user input path marker Repair: Use the staged user input path under runs/with_vs_without_nv/_inputs/.<br>tier_4: output dir marker Repair: Write outputs under the exact arm-specific output directory.<br>tier_5: command does not reference the expected output directory Repair: Make the command execute cleanly and produce verifier-accepted artifacts. |
| 2 | 0 | 1/5 | no | None | T1: entrypoint marker; T2: user input path marker; T4: output dir marker; T5: command does not reference the expected output directory | tier_1: entrypoint marker Repair: Use the runnable surface documented for this arm.<br>tier_2: user input path marker Repair: Use the staged user input path under runs/with_vs_without_nv/_inputs/.<br>tier_4: output dir marker Repair: Write outputs under the exact arm-specific output directory.<br>tier_5: command does not reference the expected output directory Repair: Make the command execute cleanly and produce verifier-accepted artifacts. |
| 3 | 0 | 3/5 | no | None | T1: entrypoint marker; T5: command does not reference an expected runnable surface | tier_1: entrypoint marker Repair: Use the runnable surface documented for this arm.<br>tier_5: command does not reference an expected runnable surface Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference an expected runnable surface Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |

## Skill Fix Notes

No separate final-run skill fix note is recorded in the saved study JSON for this scenario; this report was regenerated from the post-fix study artifacts.

## Generated Commands

These are the extracted first-attempt commands by repeat.

### GPT-5.5 / Codex, with arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
mkdir -p runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/gpt55/with/repeat_1 && export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && PYTHONDONTWRITEBYTECODE=1 python skills/nv-generate-mr-brain-finetune/scripts/run_mr_brain_finetune.py runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_datalist.json --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_dataset --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/gpt55/with/repeat_1 --modality mri_t1 --preflight
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
mkdir -p runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/gpt55/with/repeat_2 && export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python skills/nv-generate-mr-brain-finetune/scripts/run_mr_brain_finetune.py runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_datalist.json --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_dataset --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/gpt55/with/repeat_2 --modality mri_t1 --preflight
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python skills/nv-generate-mr-brain-finetune/scripts/run_mr_brain_finetune.py runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_datalist.json --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_dataset --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/gpt55/with/repeat_3 --preflight
```

### GPT-5.5 / Codex, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 4/5, passed=no, steps=unresolved, exit=1

```bash
python - <<'PY'
import json, os, shutil, sys
from pathlib import Path

data_root = Path("runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset")
out = Path("runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/gpt55/without/repeat_1")
cfg_out = out / "configs"
emb_out = out / "embeddings"
model_out = out / "checkpoints"
infer_out = out / "inference"
summary_path = out / "preflight_summary.json"

nv_root = Path(os.environ.get("NV_GENERATE_ROOT", ".workbench_data/upstreams/NV-Generate-CTMR"))
src_cfg = nv_root / "configs"

required = {
    "config_network_rflow.json": "config_maisi.json",
    "environment_maisi_diff_model_rflow-mr-brain.json": "environment_maisi_diff_model.json",
    "config_maisi_diff_model_rflow-mr-brain.json": "config_maisi_diff_model.json",
    "modality_mapping.json": "modality_mapping.json",
}

errors, warnings = [], []
out.mkdir(parents=True, exist_ok=True)
cfg_out.mkdir(parents=True, exist_ok=True)
emb_out.mkdir(parents=True, exist_ok=True)
model_out.mkdir(parents=True, exist_ok=True)
infer_out.mkdir(parents=True, exist_ok=True)

for src_name, dst_name in required.items():
    src = src_cfg / src_name
    dst = cfg_out / dst_name
    if src.exists():
        shutil.copy2(src, dst)
        if src_name != dst_name:
            shutil.copy2(src, cfg_out / src_name)
    else:
        errors.append(f"missing upstream config: {src}")

# Locate a MONAI-style datalist in the input bundle.
datalist = None
if data_root.exists():
    for p in sorted(data_root.rglob("*.json")):
        try:
            obj = json.loads(p.read_text())
        except Exception:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("training"), list):
            datalist = p
            datalist_obj = obj
            break
else:
    errors.append(f"missing data root: {data_root}")

if datalist is None:
    datalist_obj = {"training": [], "testing": []}
    errors.append(f"no MONAI-style datalist with a training list found under {data_root}")

staged_datalist = cfg_out / "dataset.json"
staged_datalist.write_text(json.dumps(datalist_obj, indent=2) + "\n")

# Load modality mapping and derive supported labels conservatively from the documented MR-brain labels plus mapping strings.
supported = {"mri_t1", "mri_t2", "mri_flair", "mri_swi"}
mapping_path = cfg_out / "modality_mapping.json"
if mapping_path.exists():
    try:
        mapping = json.loads(mapping_path.read_text())
        def collect_strings(x):
            vals = set()
            if isinstance(x, dict):
                vals |= {str(k) for k in x.keys()}
                for v in x.values():
                    vals |= collect_strings(v)
            elif isinstance(x, list):
                for v in x:
                    vals |= collect_strings(v)
            elif isinstance(x, str):
                vals.add(x)
            return vals
        supported |= collect_strings(mapping)
    except Exception as e:
        errors.append(f"could not parse staged modality mapping {mapping_path}: {e}")

# Validate datalist.
training = datalist_obj.get("training")
if not isinstance(training, list) or not training:
    errors.append("datalist training list is empty or missing")
else:
    for i, item in enumerate(training):
        if not isinstance(item, dict):
            errors.append(f"training[{i}] is not an object")
            continue
        image = item.get("image")
        modality = item.get("modality")
        if not image or not isinstance(image, str):
            errors.append(f"training[{i}] missing string image")
        else:
            img_path = data_root / image
            if not img_path.exists():
                errors.append(f"training[{i}] image does not exist under data root: {img_path}")
        if not modality or not isinstance(modality, str):
            errors.append(f"training[{i}] missing string modality")
        elif modality not in supported:
            errors.append(f"training[{i}] unsupported modality {modality!r}")

# Patch staged environment config.
env_path = cfg_out / "environment_maisi_diff_model.json"
autoencoder_path = None
diff_ckpt_path = None
if env_path.exists():
    try:
        env = json.loads(env_path.read_text())
    except Exception as e:
        env = {}
        errors.append(f"could not parse staged environment config {env_path}: {e}")

    # Preserve an existing usable autoencoder path if present; otherwise record the missing requirement.
    for key in ("trained_autoencoder_path",):
        val = env.get(key)
        if isinstance(val, str) and val:
            p = Path(val)
            if p.exists():
                autoencoder_path = str(p)
            elif (nv_root / val).exists():
                autoencoder_path = str(nv_root / val)
    if autoencoder_path is None:
        errors.append("no existing trained_autoencoder_path found in staged/source environment config")

    val = env.get("existing_ckpt_filepath")
    if isinstance(val, str) and val:
        p = Path(val)
        if p.exists():
            diff_ckpt_path = str(p)
        elif (nv_root / val).exists():
            diff_ckpt_path = str(nv_root / val)
        else:
            warnings.append(f"existing_ckpt_filepath not found; staging null for preflight: {val}")

    env.update({
        "data_base_dir": str(data_root),
        "json_data_list": str(staged_datalist),
        "embedding_base_dir": str(emb_out),
        "model_dir": str(model_out),
        "output_dir": str(infer_out),
        "modality_mapping_path": str(mapping_path),
        "trained_autoencoder_path": autoencoder_path or env.get("trained_autoencoder_path"),
        "existing_ckpt_filepath": diff_ckpt_path,
    })
    env_path.write_text(json.dumps(env, indent=2) + "\n")
    shutil.copy2(env_path, cfg_out / "environment_maisi_diff_model_rflow-mr-brain.json")

# Patch staged model config for preflight-scale settings without launching GPU training.
model_cfg_path = cfg_out / "config_maisi_diff_model.json"
if model_cfg_path.exists():
    try:
        model_cfg = json.loads(model_cfg_path.read_text())
    except Exception as e:
        model_cfg = {}
        errors.append(f"could not parse staged model config {model_cfg_path}: {e}")
    train_cfg = model_cfg.setdefault("diffusion_unet_train", {})
    if isinstance(train_cfg, dict):
        train_cfg["n_epochs"] = 1
        train_cfg["batch_size"] = 1
        train_cfg["learning_rate"] = train_cfg.get("learning_rate", 1e-5)
        train_cfg["cache_rate"] = 0.0
    else:
        errors.append("diffusion_unet_train is not an object in staged model config")
    model_cfg_path.write_text(json.dumps(model_cfg, indent=2) + "\n")
    shutil.copy2(model_cfg_path, cfg_out / "config_maisi_diff_model_rflow-mr-brain.json")

# Ensure output-local runtime work directories are represented in the staged env.
if env_path.exists():
    try:
        env2 = json.loads(env_path.read_text())
        for k in ("embedding_base_dir", "model_dir", "output_dir"):
            v = Path(env2.get(k, ""))
            if not str(v).startswith(str(out)):
                errors.append(f"{k} is not output-local: {v}")
    except Exception:
        pass

summary = {
    "ok": not errors,
    "data_root": str(data_root),
    "source_nv_generate_root": str(nv_root),
    "staged_configs_dir": str(cfg_out),
    "staged_datalist": str(staged_datalist),
    "training_count": len(training) if isinstance(training, list) else 0,
    "supported_modalities_checked": sorted(supported),
    "preflight_only": True,
    "gpu_training_launched": False,
    "runnable_upstream_commands_not_executed": [
        f"python -m scripts.diff_model_create_training_data -e {env_path} -c {model_cfg_path} -t {cfg_out / 'config_maisi.json'} -g 1",
        f"python -m scripts.diff_model_train -e {env_path} -c {model_cfg_path} -t {cfg_out / 'config_maisi.json'} -g 1",
    ],
    "warnings": warnings,
    "errors": errors,
}
summary_path.write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
sys.exit(0 if not errors else 1)
PY
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=1

```bash
OUT="runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/gpt55/without/repeat_2" IN="runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset" NVROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" python3 - <<'PY'
import json, os, shutil, sys
from pathlib import Path

out = Path(os.environ["OUT"])
inp = Path(os.environ["IN"])
nvroot = Path(os.environ["NVROOT"])
cfg_out = out / "configs"
summary_path = out / "preflight_summary.json"

errors, warnings = [], []
out.mkdir(parents=True, exist_ok=True)
cfg_out.mkdir(parents=True, exist_ok=True)
(out / "embeddings").mkdir(exist_ok=True)
(out / "checkpoints").mkdir(exist_ok=True)
(out / "inference").mkdir(exist_ok=True)

def write_summary(extra=None, exit_code=0):
    summary = {
        "workflow": "nv_generate_mr_brain_finetune",
        "model_variant": "MR-brain diffusion-UNet rflow finetuning preflight",
        "preflight_only": True,
        "training_launched": False,
        "input_dataset": str(inp),
        "output_dir": str(out),
        "staged_config_dir": str(cfg_out),
        "errors": errors,
        "warnings": warnings,
    }
    if extra:
        summary.update(extra)
    summary["valid"] = not errors
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(str(summary_path))
    raise SystemExit(exit_code)

if not inp.is_dir():
    errors.append(f"input data root does not exist or is not a directory: {inp}")
if not nvroot.is_dir():
    errors.append(f"NV-Generate-CTMR checkout not found: {nvroot}")
if errors:
    write_summary(exit_code=1)

required_cfgs = [
    "configs/config_network_rflow.json",
    "configs/environment_maisi_diff_model_rflow-mr-brain.json",
    "configs/config_maisi_diff_model_rflow-mr-brain.json",
    "configs/modality_mapping.json",
]
staged = {}
for rel in required_cfgs:
    src = nvroot / rel
    dst = cfg_out / Path(rel).name
    if not src.is_file():
        errors.append(f"required upstream config missing: {src}")
    else:
        shutil.copy2(src, dst)
        staged[Path(rel).name] = dst
if errors:
    write_summary(exit_code=1)

def load_json(p):
    try:
        return json.loads(p.read_text())
    except Exception as e:
        errors.append(f"invalid JSON in {p}: {e}")
        return None

def dump_json(p, obj):
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")

def find_datalist(root):
    preferred = []
    for p in sorted(root.rglob("*.json")):
        data = load_json(p)
        if isinstance(data, dict) and isinstance(data.get("training"), list):
            rank = 0 if p.name in {"dataset.json", "datalist.json", "data.json"} else 1
            preferred.append((rank, len(str(p)), p, data))
    if not preferred:
        return None, None
    preferred.sort(key=lambda x: (x[0], x[1], str(x[2])))
    return preferred[0][2], preferred[0][3]

datalist_src, datalist = find_datalist(inp)
if datalist_src is None:
    errors.append(f"no MONAI-style JSON datalist with a 'training' list found under {inp}")
    write_summary(exit_code=1)

datalist_staged = cfg_out / "datalist.json"
dump_json(datalist_staged, datalist)

mapping = load_json(staged["modality_mapping.json"]) or {}
def collect_modalities(obj):
    vals = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and k.startswith("mri_"):
                vals.add(k)
            vals |= collect_modalities(v)
    elif isinstance(obj, list):
        for v in obj:
            vals |= collect_modalities(v)
    elif isinstance(obj, str) and obj.startswith("mri_"):
        vals.add(obj)
    return vals

supported_modalities = collect_modalities(mapping)
if not supported_modalities:
    supported_modalities = {"mri_t1", "mri_t2", "mri_flair", "mri_swi"}
    warnings.append("could not infer MR modality labels from modality_mapping.json; used documented fallback labels")

training = datalist.get("training")
if not isinstance(training, list) or not training:
    errors.append("datalist 'training' must be a non-empty list")
else:
    for i, item in enumerate(training):
        if not isinstance(item, dict):
            errors.append(f"training[{i}] is not an object")
            continue
        image = item.get("image")
        modality = item.get("modality")
        if not isinstance(image, str) or not image:
            errors.append(f"training[{i}].image is missing or not a non-empty string")
        else:
            img_path = Path(image)
            if img_path.is_absolute():
                errors.append(f"training[{i}].image must be relative, got absolute path: {image}")
            elif not (inp / img_path).is_file():
                errors.append(f"training[{i}].image does not exist under data root: {inp / img_path}")
        if not isinstance(modality, str) or not modality:
            errors.append(f"training[{i}].modality is missing or not a non-empty string")
        elif modality not in supported_modalities:
            errors.append(f"training[{i}].modality '{modality}' is not in staged modality_mapping labels")

env_path = staged["environment_maisi_diff_model_rflow-mr-brain.json"]
model_path = staged["config_maisi_diff_model_rflow-mr-brain.json"]
network_path = staged["config_network_rflow.json"]
env_cfg = load_json(env_path) or {}
model_cfg = load_json(model_path) or {}

def set_key_recursive(obj, key, value):
    found = False
    if isinstance(obj, dict):
        if key in obj:
            obj[key] = value
            found = True
        for v in obj.values():
            found = set_key_recursive(v, key, value) or found
    elif isinstance(obj, list):
        for v in obj:
            found = set_key_recursive(v, key, value) or found
    return found

def get_key_recursive(obj, key):
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = get_key_recursive(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = get_key_recursive(v, key)
            if r is not None:
                return r
    return None

def resolve_existing_path(value):
    if not isinstance(value, str) or not value:
        return None
    p = Path(value)
    candidates = [p] if p.is_absolute() else [Path.cwd() / p, nvroot / p]
    for c in candidates:
        if c.exists():
            return str(c if c.is_absolute() else c)
    return None

def find_checkpoint(kind):
    suffixes = {".pt", ".pth", ".ckpt"}
    terms = ["autoencoder"] if kind == "autoencoder" else ["diff", "unet", "model"]
    try:
        for p in sorted(nvroot.rglob("*")):
            name = p.name.lower()
            if p.is_file() and p.suffix.lower() in suffixes and any(t in name for t in terms):
                return str(p)
    except Exception as e:
        warnings.append(f"checkpoint scan skipped/failed under {nvroot}: {e}")
    return None

env_updates = {
    "data_base_dir": str(inp),
    "json_data_list": str(datalist_staged),
    "embedding_base_dir": str(out / "embeddings"),
    "model_dir": str(out / "checkpoints"),
    "output_dir": str(out / "inference"),
    "modality_mapping_path": str(staged["modality_mapping.json"]),
}
for k, v in env_updates.items():
    if not set_key_recursive(env_cfg, k, v):
        env_cfg[k] = v

ae_existing = resolve_existing_path(get_key_recursive(env_cfg, "trained_autoencoder_path")) or find_checkpoint("autoencoder")
if ae_existing:
    if not set_key_recursive(env_cfg, "trained_autoencoder_path", ae_existing):
        env_cfg["trained_autoencoder_path"] = ae_existing
else:
    warnings.append("no existing autoencoder checkpoint was found; staged preflight config keeps/uses null trained_autoencoder_path")
    if not set_key_recursive(env_cfg, "trained_autoencoder_path", None):
        env_cfg["trained_autoencoder_path"] = None

diff_existing = resolve_existing_path(get_key_recursive(env_cfg, "existing_ckpt_filepath")) or find_checkpoint("diffusion")
if not set_key_recursive(env_cfg, "existing_ckpt_filepath", diff_existing):
    env_cfg["existing_ckpt_filepath"] = diff_existing
if diff_existing is None:
    warnings.append("no pretrained diffusion checkpoint found; existing_ckpt_filepath staged as null for from-scratch/non-training preflight")

def update_diffusion_train(obj):
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "diffusion_unet_train" and isinstance(v, dict):
                hits.append(v)
            hits.extend(update_diffusion_train(v))
    elif isinstance(obj, list):
        for v in obj:
            hits.extend(update_diffusion_train(v))
    return hits

train_blocks = update_diffusion_train(model_cfg)
if not train_blocks:
    model_cfg["diffusion_unet_train"] = {}
    train_blocks = [model_cfg["diffusion_unet_train"]]
for block in train_blocks:
    block["n_epochs"] = 1
    block["batch_size"] = 1
    block["learning_rate"] = 1e-5
    block["cache_rate"] = 0.0

dump_json(env_path, env_cfg)
dump_json(model_path, model_cfg)

for k in ["embedding_base_dir", "model_dir", "output_dir"]:
    v = get_key_recursive(env_cfg, k)
    if not isinstance(v, str) or not v.startswith(str(out)):
        errors.append(f"staged env config {k} does not point under output dir: {v}")
for k in ["json_data_list", "modality_mapping_path"]:
    v = get_key_recursive(env_cfg, k)
    if not isinstance(v, str) or not v.startswith(str(cfg_out)):
        errors.append(f"staged env config {k} does not point under staged config dir: {v}")

extra = {
    "selected_datalist": str(datalist_src),
    "staged_datalist": str(datalist_staged),
    "training_items": len(training) if isinstance(training, list) else 0,
    "supported_mr_modalities_detected": sorted(supported_modalities),
    "staged_configs": {k: str(v) for k, v in staged.items()},
    "preflight_train_settings": {
        "diffusion_unet_train.n_epochs": 1,
        "batch_size": 1,
        "learning_rate": 1e-5,
        "cache_rate": 0.0,
    },
    "not_run_upstream_commands": [
        f"python -m scripts.diff_model_create_training_data -e {env_path} -c {model_path} -t {network_path} -g 1",
        f"python -m scripts.diff_model_train -e {env_path} -c {model_path} -t {network_path} -g 1",
    ],
}
write_summary(extra=extra, exit_code=1 if errors else 0)
PY
```

Repeat 3: score 4/5, passed=no, steps=unresolved, exit=1

```bash
python - <<'PY'
import json, os, re, shutil, sys
from pathlib import Path

inp = Path("runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset")
out = Path("runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/gpt55/without/repeat_3")
up = Path(os.environ.get("NV_GENERATE_ROOT", ".workbench_data/upstreams/NV-Generate-CTMR"))

cfg_out = out / "configs"
staged_inputs = out / "staged_inputs"
for d in [out, cfg_out, staged_inputs, out / "embeddings", out / "checkpoints", out / "inference", out / "logs"]:
    d.mkdir(parents=True, exist_ok=True)

errors, warnings = [], []

required_sources = {
    "config_network_rflow.json": cfg_out / "config_maisi.json",
    "environment_maisi_diff_model_rflow-mr-brain.json": cfg_out / "environment_maisi_diff_model.json",
    "config_maisi_diff_model_rflow-mr-brain.json": cfg_out / "config_maisi_diff_model.json",
    "modality_mapping.json": cfg_out / "modality_mapping.json",
}
for src_name, dst in required_sources.items():
    src = up / "configs" / src_name
    if not src.exists():
        errors.append(f"missing upstream config: {src}")
    else:
        shutil.copy2(src, dst)

def load_json(p):
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def dump_json(p, obj):
    with p.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")

datalist_candidates = []
if inp.is_file() and inp.suffix == ".json":
    datalist_candidates = [inp]
elif inp.is_dir():
    jsons = sorted(inp.rglob("*.json"))
    preferred = []
    for p in jsons:
        try:
            o = load_json(p)
            if isinstance(o, dict) and isinstance(o.get("training"), list):
                preferred.append(p)
        except Exception:
            pass
    name_rank = {"datalist.json": 0, "dataset.json": 1, "data.json": 2}
    datalist_candidates = sorted(preferred, key=lambda p: (name_rank.get(p.name, 99), len(str(p)), str(p)))
if not datalist_candidates:
    errors.append(f"could not find a MONAI-style datalist JSON with a training list under {inp}")
    datalist = {}
    datalist_src = None
else:
    datalist_src = datalist_candidates[0]
    try:
        datalist = load_json(datalist_src)
    except Exception as e:
        datalist = {}
        errors.append(f"invalid datalist JSON {datalist_src}: {e}")

staged_datalist = staged_inputs / "datalist.json"
if datalist_src and datalist:
    shutil.copy2(datalist_src, staged_datalist)

supported_modalities = {"mri_t1", "mri_t2", "mri_flair", "mri_swi"}
modality_mapping_path = cfg_out / "modality_mapping.json"
if modality_mapping_path.exists():
    try:
        mm = load_json(modality_mapping_path)
        def collect_modalities(x):
            vals = set()
            if isinstance(x, dict):
                for k, v in x.items():
                    if isinstance(k, str) and re.match(r"^mri_", k):
                        vals.add(k)
                    vals |= collect_modalities(v)
            elif isinstance(x, list):
                for v in x:
                    vals |= collect_modalities(v)
            elif isinstance(x, str) and re.match(r"^mri_", x):
                vals.add(x)
            return vals
        supported_modalities |= collect_modalities(mm)
    except Exception as e:
        errors.append(f"invalid staged modality mapping JSON {modality_mapping_path}: {e}")

training = datalist.get("training") if isinstance(datalist, dict) else None
seen_modalities = []
if not isinstance(training, list) or not training:
    errors.append("datalist must contain a non-empty training list")
else:
    for i, item in enumerate(training):
        if not isinstance(item, dict):
            errors.append(f"training[{i}] is not an object")
            continue
        image = item.get("image")
        modality = item.get("modality")
        if not isinstance(image, str) or not image:
            errors.append(f"training[{i}].image must be a non-empty relative path")
        else:
            if Path(image).is_absolute():
                errors.append(f"training[{i}].image is absolute, expected path relative to data root: {image}")
            elif not (inp / image).exists():
                errors.append(f"training[{i}].image does not exist under data root: {inp / image}")
        if not isinstance(modality, str) or not modality:
            errors.append(f"training[{i}].modality must be a non-empty string")
        else:
            seen_modalities.append(modality)
            if modality not in supported_modalities:
                errors.append(f"training[{i}].modality is not supported by staged modality mapping: {modality}")

env_path = cfg_out / "environment_maisi_diff_model.json"
model_path = cfg_out / "config_maisi_diff_model.json"
network_path = cfg_out / "config_maisi.json"

def resolve_existing(raw):
    if raw in (None, "", "null"):
        return None
    p = Path(str(raw))
    candidates = [p] if p.is_absolute() else [p, up / p]
    for c in candidates:
        if c.exists():
            return str(c)
    return str(p)

if env_path.exists():
    try:
        env_cfg = load_json(env_path)
        if not isinstance(env_cfg, dict):
            errors.append("staged environment config is not a JSON object")
            env_cfg = {}
    except Exception as e:
        errors.append(f"could not parse staged environment config {env_path}: {e}")
        env_cfg = {}

    old_auto = env_cfg.get("trained_autoencoder_path")
    old_diff = env_cfg.get("existing_ckpt_filepath")
    trained_autoencoder_path = resolve_existing(old_auto)
    existing_ckpt_filepath = resolve_existing(old_diff)
    if existing_ckpt_filepath and not Path(existing_ckpt_filepath).exists():
        existing_ckpt_filepath = None
    if not trained_autoencoder_path:
        warnings.append("trained_autoencoder_path was absent in upstream environment config; staged config leaves it null for preflight-only validation")
    elif not Path(trained_autoencoder_path).exists():
        warnings.append(f"trained_autoencoder_path does not exist locally; not required for this no-training preflight: {trained_autoencoder_path}")

    updates = {
        "data_base_dir": str(inp),
        "json_data_list": str(staged_datalist),
        "embedding_base_dir": str(out / "embeddings"),
        "model_dir": str(out / "checkpoints"),
        "output_dir": str(out / "inference"),
        "modality_mapping_path": str(modality_mapping_path),
        "trained_autoencoder_path": trained_autoencoder_path,
        "existing_ckpt_filepath": existing_ckpt_filepath,
    }

    def set_key_everywhere(obj, key, value):
        found = False
        if isinstance(obj, dict):
            if key in obj:
                obj[key] = value
                found = True
            for v in obj.values():
                found = set_key_everywhere(v, key, value) or found
        elif isinstance(obj, list):
            for v in obj:
                found = set_key_everywhere(v, key, value) or found
        return found

    for k, v in updates.items():
        set_key_everywhere(env_cfg, k, v)
        env_cfg[k] = v
    dump_json(env_path, env_cfg)

if model_path.exists():
    try:
        model_cfg = load_json(model_path)
        if not isinstance(model_cfg, dict):
            errors.append("staged diffusion model config is not a JSON object")
            model_cfg = {}
    except Exception as e:
        errors.append(f"could not parse staged diffusion model config {model_path}: {e}")
        model_cfg = {}

    train_cfg = model_cfg.get("diffusion_unet_train")
    if not isinstance(train_cfg, dict):
        train_cfg = {}
        model_cfg["diffusion_unet_train"] = train_cfg
    train_cfg.update({
        "n_epochs": 1,
        "batch_size": 1,
        "learning_rate": 1e-5,
        "cache_rate": 0.0,
    })
    dump_json(model_path, model_cfg)

for p in [env_path, model_path, network_path, modality_mapping_path]:
    if not p.exists():
        errors.append(f"required staged config was not written: {p}")

output_local_expected = [out / "embeddings", out / "checkpoints", out / "inference"]
for p in output_local_expected:
    try:
        p.relative_to(out)
    except ValueError:
        errors.append(f"work directory is not output-local: {p}")

commands = [
    f'PYTHONPATH="{up}" python -m scripts.diff_model_create_training_data -e "{env_path}" -c "{model_path}" -t "{network_path}" -g 1',
    f'PYTHONPATH="{up}" python -m scripts.diff_model_train -e "{env_path}" -c "{model_path}" -t "{network_path}" -g 1',
]
(out / "upstream_stage_commands_not_run.sh").write_text("# Reference only; not run by this preflight.\n" + "\n".join(commands) + "\n", encoding="utf-8")

summary = {
    "status": "passed" if not errors else "failed",
    "workflow_check": "mr-brain diffusion-UNet rflow finetune preflight: stage configs and validate datalist only; no GPU training launched",
    "input_data_root": str(inp),
    "selected_datalist": str(datalist_src) if datalist_src else None,
    "staged_datalist": str(staged_datalist) if staged_datalist.exists() else None,
    "output_dir": str(out),
    "upstream_checkout_read_only": str(up),
    "model_variant": "MR-brain diffusion-UNet rflow finetuning",
    "observed_training_modalities": sorted(set(seen_modalities)),
    "supported_modalities_from_mapping": sorted(supported_modalities),
    "training_items": len(training) if isinstance(training, list) else 0,
    "staged_configs": {
        "environment": str(env_path),
        "diffusion_model": str(model_path),
        "network": str(network_path),
        "modality_mapping": str(modality_mapping_path),
    },
    "preflight_parameters": {
        "diffusion_unet_train.n_epochs": 1,
        "diffusion_unet_train.batch_size": 1,
        "diffusion_unet_train.learning_rate": 1e-5,
        "diffusion_unet_train.cache_rate": 0.0,
    },
    "normal_upstream_stage_commands_not_run": commands,
    "errors": errors,
    "warnings": warnings,
}
dump_json(out / "preflight_summary.json", summary)
print(out / "preflight_summary.json")
sys.exit(1 if errors else 0)
PY
```

### Opus 4.7, with arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && mkdir -p runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/opus/with/repeat_1 && python skills/nv-generate-mr-brain-finetune/scripts/run_mr_brain_finetune.py runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_datalist.json --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_dataset --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/opus/with/repeat_1 --preflight
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && mkdir -p runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/opus/with/repeat_2 && python skills/nv-generate-mr-brain-finetune/scripts/run_mr_brain_finetune.py runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_datalist.json --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_dataset --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/opus/with/repeat_2 --preflight
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python skills/nv-generate-mr-brain-finetune/scripts/run_mr_brain_finetune.py runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_datalist.json --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_dataset --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/opus/with/repeat_3 --preflight
```

### Opus 4.7, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 1/5, passed=no, steps=unresolved, exit=None

```bash
mkdir -p runs/with_vs_without/nv_generate_mr_brain_finetune_codex_opus/opus/without/repeat_1/configs && OUT=runs/with_vs_without/nv_generate_mr_brain_finetune_codex_opus/opus/without/repeat_1 && IN=runs/with_vs_without/_inputs/nv_generate_mr_brain_finetune/input_dataset && UP=$(ls -d .workbench_data/upstreams/*NV-Generate-CTMR* 2>/dev/null | head -n1) && [ -n "$UP" ] || UP="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && for f in config_network_rflow.json environment_maisi_diff_model_rflow-mr-brain.json config_maisi_diff_model_rflow-mr-brain.json modality_mapping.json; do [ -f "$UP/configs/$f" ] && cp "$UP/configs/$f" "$OUT/configs/$f"; done && DATALIST=$(ls "$IN"/*.json 2>/dev/null | head -n1) && cp "$DATALIST" "$OUT/configs/datalist.json" && python -c "
import json, os, sys
out=os.environ['OUT']; in_dir=os.environ['IN']
dl=json.load(open(os.path.join(out,'configs','datalist.json')))
mm_path=os.path.join(out,'configs','modality_mapping.json')
mm=json.load(open(mm_path)) if os.path.exists(mm_path) else {}
supported=set(mm.keys()) if isinstance(mm,dict) else set(mm)
training=dl.get('training',[])
errors=[]
if not training: errors.append('empty training list')
missing=[]; bad_mod=[]
for e in training:
    p=os.path.join(in_dir,e['image'])
    if not os.path.exists(p): missing.append(e['image'])
    m=e.get('modality')
    if supported and m not in supported: bad_mod.append(m)
env_path=os.path.join(out,'configs','environment_maisi_diff_model_rflow-mr-brain.json')
env_ok=os.path.exists(env_path); cfg_ok=os.path.exists(os.path.join(out,'configs','config_maisi_diff_model_rflow-mr-brain.json')); net_ok=os.path.exists(os.path.join(out,'configs','config_network_rflow.json'))
if env_ok:
    env=json.load(open(env_path))
    env['data_base_dir']=os.path.abspath(in_dir)
    env['json_data_list']=os.path.abspath(os.path.join(out,'configs','datalist.json'))
    env['embedding_base_dir']=os.path.abspath(os.path.join(out,'embeddings'))
    env['model_dir']=os.path.abspath(os.path.join(out,'models'))
    env['output_dir']=os.path.abspath(os.path.join(out,'inference'))
    env['modality_mapping_path']=os.path.abspath(mm_path) if os.path.exists(mm_path) else env.get('modality_mapping_path')
    json.dump(env,open(env_path,'w'),indent=2)
summary={'datalist':os.path.relpath(os.path.join(out,'configs','datalist.json')),'n_training':len(training),'missing_images':missing,'unsupported_modalities':bad_mod,'configs_staged':{'environment':env_ok,'model_config':cfg_ok,'network':net_ok,'modality_mapping':os.path.exists(mm_path)},'errors':errors,'preflight_ok':(not errors and not missing and not bad_mod and env_ok and cfg_ok and net_ok)}
json.dump(summary,open(os.path.join(out,'preflight_summary.json'),'w'),indent=2)
print(json.dumps(summary,indent=2))
sys.exit(0 if summary['preflight_ok'] else 1)
" OUT=$OUT IN=$IN
```

Repeat 2: score 1/5, passed=no, steps=unresolved, exit=None

```bash
mkdir -p runs/with_vs_without/nv_generate_mr_brain_finetune_codex_opus/opus/without/repeat_2/configs && OUT=runs/with_vs_without/nv_generate_mr_brain_finetune_codex_opus/opus/without/repeat_2 && IN=runs/with_vs_without/_inputs/nv_generate_mr_brain_finetune/input_dataset && UP=$(find .workbench_data/upstreams -type d -name "NV-Generate-CTMR*" 2>/dev/null | head -1) && [ -z "$UP" ] && UP="${NV_GENERATE_ROOT}" ; cp "$UP/configs/config_network_rflow.json" "$OUT/configs/" && cp "$UP/configs/environment_maisi_diff_model_rflow-mr-brain.json" "$OUT/configs/" && cp "$UP/configs/config_maisi_diff_model_rflow-mr-brain.json" "$OUT/configs/" && cp "$UP/configs/modality_mapping.json" "$OUT/configs/" && DATALIST=$(find "$IN" -maxdepth 2 -name "*.json" | head -1) && cp "$DATALIST" "$OUT/configs/datalist.json" && DATA_ROOT=$(dirname "$DATALIST") && python -c "
import json, os, sys
out='$OUT'; data_root='$DATA_ROOT'
dl=json.load(open(os.path.join(out,'configs','datalist.json')))
mm=json.load(open(os.path.join(out,'configs','modality_mapping.json')))
supported=set(mm.keys()) if isinstance(mm,dict) else set()
training=dl.get('training',[])
assert training, 'training list empty'
missing=[e['image'] for e in training if not os.path.exists(os.path.join(data_root,e['image']))]
bad_mod=[e.get('modality') for e in training if supported and e.get('modality') not in supported]
env_p=os.path.join(out,'configs','environment_maisi_diff_model_rflow-mr-brain.json')
env=json.load(open(env_p))
env['data_base_dir']=data_root
env['json_data_list']=os.path.join(out,'configs','datalist.json')
env['embedding_base_dir']=os.path.join(out,'embeddings')
env['model_dir']=os.path.join(out,'models')
env['output_dir']=os.path.join(out,'inference')
env['modality_mapping_path']=os.path.join(out,'configs','modality_mapping.json')
os.makedirs(env['embedding_base_dir'],exist_ok=True)
os.makedirs(env['model_dir'],exist_ok=True)
os.makedirs(env['output_dir'],exist_ok=True)
json.dump(env,open(env_p,'w'),indent=2)
summary={'datalist_valid_json':True,'training_count':len(training),'missing_paths':missing,'unsupported_modalities':bad_mod,'data_root':data_root,'staged_env':env_p,'preflight_ok':not missing and not bad_mod}
json.dump(summary,open(os.path.join(out,'preflight_summary.json'),'w'),indent=2)
print(json.dumps(summary,indent=2))
sys.exit(0 if summary['preflight_ok'] else 1)
"
```

Repeat 3: score 3/5, passed=no, steps=unresolved, exit=None

```bash
mkdir -p runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/opus/without/repeat_3/configs runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/opus/without/repeat_3/embeddings runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/opus/without/repeat_3/models runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/opus/without/repeat_3/output && IN=runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset && OUT=runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/opus/without/repeat_3 && DATALIST=$(find "$IN" -maxdepth 3 -name '*.json' | head -n1) && DATA_ROOT=$(dirname "$DATALIST") && cp "$DATALIST" "$OUT/datalist.json" && python -c "
import json, os, sys
out=os.environ['OUT']; dl=os.environ['DATALIST']; root=os.environ['DATA_ROOT']
supported={'mri_t1','mri_t2','mri_flair','mri_swi','mri_t1_ss','mri_t2_ss','mri_flair_ss','mri_swi_ss'}
errors=[]; warnings=[]
with open(dl) as f: d=json.load(f)
training=d.get('training',[])
if not training: errors.append('empty training list')
missing=[]; bad_mod=[]
for it in training:
    p=os.path.join(root,it.get('image',''))
    if not os.path.exists(p): missing.append(it.get('image'))
    m=it.get('modality')
    if m and m not in supported: bad_mod.append(m)
if missing: errors.append(f'missing {len(missing)} image(s)')
if bad_mod: errors.append(f'unsupported modalities: {sorted(set(bad_mod))}')
env={'data_base_dir':root,'json_data_list':os.path.abspath(os.path.join(out,'datalist.json')),'embedding_base_dir':os.path.abspath(os.path.join(out,'embeddings')),'model_dir':os.path.abspath(os.path.join(out,'models')),'output_dir':os.path.abspath(os.path.join(out,'output')),'modality_mapping_path':'configs/modality_mapping.json','trained_autoencoder_path':None,'existing_ckpt_filepath':None}
with open(os.path.join(out,'configs','environment_maisi_diff_model_rflow-mr-brain.json'),'w') as f: json.dump(env,f,indent=2)
model_cfg={'diffusion_unet_train':{'n_epochs':1,'batch_size':1,'lr':1e-5,'cache_rate':0.0}}
with open(os.path.join(out,'configs','config_maisi_diff_model_rflow-mr-brain.json'),'w') as f: json.dump(model_cfg,f,indent=2)
with open(os.path.join(out,'configs','config_network_rflow.json'),'w') as f: json.dump({'note':'staged placeholder; populate from upstream before training'},f,indent=2)
summary={'datalist':dl,'data_root':root,'n_training':len(training),'n_missing':len(missing),'unsupported_modalities':sorted(set(bad_mod)),'errors':errors,'preflight_ok':not errors,'staged_configs':sorted(os.listdir(os.path.join(out,'configs'))),'note':'preflight only; no GPU training launched'}
with open(os.path.join(out,'preflight_summary.json'),'w') as f: json.dump(summary,f,indent=2)
print(json.dumps(summary,indent=2))
sys.exit(0 if not errors else 1)
"
```

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `examples/studies/with_vs_without_skill/nv_generate_mr_brain_finetune_codex_opus/` |
| Generated outputs | `runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_generate_mr_brain_finetune_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
