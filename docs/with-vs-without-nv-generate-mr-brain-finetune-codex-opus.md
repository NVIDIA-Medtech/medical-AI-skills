# `nv_generate_mr_brain_finetune`: Codex/Opus LLM+SKILL.md vs LLM+README

Status: strict audit passed for refreshed artifacts on May 29, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

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
| GPT-5.5 / Codex | without | 3.3/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | None (2); 1 (1) | command does not reference an expected runnable surface (2); exit 1 (1) | T1: entrypoint marker (2); T5: command does not reference an expected runnable surface (2); T5: exit 1 (1) |
| Opus 4.7 | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | preflight payload reported (3) | none |
| Opus 4.7 | without | 3.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | None (3) | command does not reference an expected runnable surface (3) | T1: entrypoint marker (3); T5: command does not reference an expected runnable surface (3) |

## Analysis

SKILL.md paired advantage: the with-skill arms passed 6/6 backend-repeat trials with an average score of 5.0/5; the README-only arms passed 0/6 backend-repeat trials with an average score of 3.2/5.

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
| GPT-5.5 / Codex | with | 3 | 3 | 3 | 10,221 | 1,307 | 836 | 11,528 | 3,842.7 | 3 | 0.0 |
| GPT-5.5 / Codex | without | 3 | 0 | 3 | 3,249 | 22,965 | 15,484 | 26,214 | 8,738.0 | 1 | 0.0 |
| Opus 4.7 | with | 3 | 3 | 3 | 17,091 | 850 | 0 | 17,941 | 5,980.3 | 3 | 0.0 |
| Opus 4.7 | without | 3 | 0 | 3 | 5,445 | 4,757 | 0 | 10,202 | 3,400.7 | 0 | n/a |

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
| 1 | 0 | 3/5 | no | None | T1: entrypoint marker; T5: command does not reference an expected runnable surface | tier_1: entrypoint marker Repair: Use the runnable surface documented for this arm.<br>tier_5: command does not reference an expected runnable surface Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference an expected runnable surface Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
| 2 | 0 | 4/5 | no | 1 | T5: exit 1 | tier_5: exit 1 Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>nonzero_exit: Command exited 1. Repair: Use stderr/stdout to repair setup, paths, arguments, or runtime package installation. |
| 3 | 0 | 3/5 | no | None | T1: entrypoint marker; T5: command does not reference an expected runnable surface | tier_1: entrypoint marker Repair: Use the runnable surface documented for this arm.<br>tier_5: command does not reference an expected runnable surface Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference an expected runnable surface Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |

### Opus 4.7, with arm

| Repeat | Step | Score | Passed | Exit | Failed tiers | Why it did not work |
|---:|---:|---:|---|---|---|---|
| 1 | 0 | 5/5 | yes | 0 | none | none |
| 2 | 0 | 5/5 | yes | 0 | none | none |
| 3 | 0 | 5/5 | yes | 0 | none | none |

### Opus 4.7, without arm

| Repeat | Step | Score | Passed | Exit | Failed tiers | Why it did not work |
|---:|---:|---:|---|---|---|---|
| 1 | 0 | 3/5 | no | None | T1: entrypoint marker; T5: command does not reference an expected runnable surface | tier_1: entrypoint marker Repair: Use the runnable surface documented for this arm.<br>tier_5: command does not reference an expected runnable surface Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference an expected runnable surface Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
| 2 | 0 | 3/5 | no | None | T1: entrypoint marker; T5: command does not reference an expected runnable surface | tier_1: entrypoint marker Repair: Use the runnable surface documented for this arm.<br>tier_5: command does not reference an expected runnable surface Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference an expected runnable surface Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
| 3 | 0 | 3/5 | no | None | T1: entrypoint marker; T5: command does not reference an expected runnable surface | tier_1: entrypoint marker Repair: Use the runnable surface documented for this arm.<br>tier_5: command does not reference an expected runnable surface Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference an expected runnable surface Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |

## Skill Fix Notes

No separate final-run skill fix note is recorded in the saved study JSON for this scenario; this report was regenerated from the post-fix study artifacts.

## Generated Commands

These are the extracted first-attempt commands by repeat.

### GPT-5.5 / Codex, with arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python skills/nv-generate-mr-brain-finetune/scripts/run_mr_brain_finetune.py runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_datalist.json --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_dataset --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/gpt55/with/repeat_1 --modality mri_t1 --preflight
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python skills/nv-generate-mr-brain-finetune/scripts/run_mr_brain_finetune.py runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_datalist.json --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_dataset --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/gpt55/with/repeat_2 --modality mri_t1 --preflight
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python skills/nv-generate-mr-brain-finetune/scripts/run_mr_brain_finetune.py runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_datalist.json --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_dataset --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/gpt55/with/repeat_3 --modality mri_t1 --preflight
```

### GPT-5.5 / Codex, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 3/5, passed=no, steps=unresolved, exit=None

```bash
NV_GENERATE_SRC="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" INPUT_DATASET="runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset" RUN_OUT="runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/gpt55/without/repeat_1" python - <<'PY'
import copy, json, os, shutil, sys
from pathlib import Path

repo = Path.cwd().resolve()
src = Path(os.environ["NV_GENERATE_SRC"])
if not src.is_absolute():
    src = (repo / src).resolve()
data_root = Path(os.environ["INPUT_DATASET"])
if not data_root.is_absolute():
    data_root = (repo / data_root).resolve()
out = Path(os.environ["RUN_OUT"])
if not out.is_absolute():
    out = (repo / out).resolve()
cfg_dir = out / "configs"

def as_repo_path(p):
    p = Path(p)
    rp = p.resolve()
    try:
        return rp.relative_to(repo).as_posix()
    except ValueError:
        return rp.as_posix()

def under(child, parent):
    try:
        Path(child).resolve().relative_to(Path(parent).resolve())
        return True
    except ValueError:
        return False

def load_json(path, errors, label):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        errors.append(f"failed to read {label} JSON at {as_repo_path(path)}: {e}")
        return None

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")

def collect_mri_modalities(obj, acc):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and k.startswith("mri_"):
                acc.add(k)
            collect_mri_modalities(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            collect_mri_modalities(v, acc)
    elif isinstance(obj, str) and obj.startswith("mri_"):
        acc.add(obj)

def resolve_existing_path(raw):
    if raw in (None, ""):
        return None, None
    s = os.path.expandvars(os.path.expanduser(str(raw)))
    p = Path(s)
    trials = [p] if p.is_absolute() else [repo / p, src / p]
    for t in trials:
        if t.exists():
            return as_repo_path(t), t
    return str(raw), None

errors, warnings = [], []
summary = {
    "workflow": "nv_generate_mr_brain_finetune_preflight",
    "model_variant": "mr-brain diffusion-unet rflow",
    "input_data_root": as_repo_path(data_root),
    "output_dir": as_repo_path(out),
    "errors": errors,
    "warnings": warnings,
}

out.mkdir(parents=True, exist_ok=True)
cfg_dir.mkdir(parents=True, exist_ok=True)
for subdir in ("embeddings", "checkpoints", "inference"):
    (out / subdir).mkdir(parents=True, exist_ok=True)

required_configs = [
    "config_network_rflow.json",
    "environment_maisi_diff_model_rflow-mr-brain.json",
    "config_maisi_diff_model_rflow-mr-brain.json",
    "modality_mapping.json",
]
staged_configs = []
if not src.is_dir():
    errors.append(f"NV-Generate-CTMR checkout not found at {as_repo_path(src)}")
else:
    for name in required_configs:
        source = src / "configs" / name
        dest = cfg_dir / name
        if not source.is_file():
            errors.append(f"required upstream config missing: {as_repo_path(source)}")
            continue
        shutil.copyfile(source, dest)
        staged_configs.append(as_repo_path(dest))
    network_src = cfg_dir / "config_network_rflow.json"
    if network_src.is_file():
        network_alias = cfg_dir / "config_maisi.json"
        shutil.copyfile(network_src, network_alias)
        staged_configs.append(as_repo_path(network_alias))
summary["staged_configs"] = staged_configs

mapping_path = cfg_dir / "modality_mapping.json"
mapping = load_json(mapping_path, errors, "modality mapping") if mapping_path.is_file() else None
supported_modalities = set()
if mapping is not None:
    collect_mri_modalities(mapping, supported_modalities)
if not supported_modalities:
    supported_modalities.update(["mri_t1", "mri_t2", "mri_flair", "mri_swi"])
summary["supported_mr_brain_modalities"] = sorted(supported_modalities)

datalist_path = None
datalist = None
if not data_root.is_dir():
    errors.append(f"input dataset root not found: {as_repo_path(data_root)}")
else:
    candidates = []
    for p in sorted(data_root.rglob("*.json")):
        obj = load_json(p, [], "candidate datalist")
        if isinstance(obj, dict) and isinstance(obj.get("training"), list):
            candidates.append((0 if len(obj.get("training", [])) > 0 else 1, len(p.parts), p))
    if not candidates:
        errors.append(f"no MONAI-style datalist JSON with a training list found under {as_repo_path(data_root)}")
    else:
        datalist_path = sorted(candidates)[0][2]
        datalist = load_json(datalist_path, errors, "selected datalist")
        staged_datalist = cfg_dir / "input_datalist.json"
        write_json(staged_datalist, datalist)
        summary["source_datalist"] = as_repo_path(datalist_path)
        summary["staged_datalist"] = as_repo_path(staged_datalist)

observed_modalities = set()
validated_images = []
if isinstance(datalist, dict):
    training = datalist.get("training")
    if not isinstance(training, list) or not training:
        errors.append("datalist training must be a non-empty list")
    else:
        for i, item in enumerate(training):
            if not isinstance(item, dict):
                errors.append(f"training[{i}] is not an object")
                continue
            image = item.get("image")
            modality = item.get("modality")
            if not isinstance(image, str) or not image:
                errors.append(f"training[{i}].image is missing or not a string")
            else:
                image_rel = Path(image)
                if image_rel.is_absolute():
                    errors.append(f"training[{i}].image must be relative, got absolute path {image}")
                else:
                    image_path = (data_root / image_rel).resolve()
                    if not under(image_path, data_root):
                        errors.append(f"training[{i}].image escapes the data root: {image}")
                    elif not image_path.is_file():
                        errors.append(f"training[{i}].image does not exist under data root: {image}")
                    else:
                        validated_images.append(image)
            if not isinstance(modality, str) or not modality:
                errors.append(f"training[{i}].modality is missing or not a string")
            else:
                observed_modalities.add(modality)
                if modality not in supported_modalities:
                    errors.append(f"training[{i}].modality '{modality}' is not supported by staged modality mapping")
summary["training_count"] = len(datalist.get("training", [])) if isinstance(datalist, dict) and isinstance(datalist.get("training"), list) else 0
summary["validated_image_count"] = len(validated_images)
summary["observed_modalities"] = sorted(observed_modalities)

env_path = cfg_dir / "environment_maisi_diff_model_rflow-mr-brain.json"
model_path = cfg_dir / "config_maisi_diff_model_rflow-mr-brain.json"
env_cfg = load_json(env_path, errors, "environment config") if env_path.is_file() else None
model_cfg = load_json(model_path, errors, "model config") if model_path.is_file() else None

if isinstance(env_cfg, dict):
    original_env = copy.deepcopy(env_cfg)
    auto_raw = original_env.get("trained_autoencoder_path")
    if auto_raw is None:
        for k, v in original_env.items():
            if "autoencoder" in str(k).lower() and isinstance(v, str):
                auto_raw = v
                break
    auto_config_path, auto_existing = resolve_existing_path(auto_raw)
    if auto_config_path is None:
        warnings.append("trained_autoencoder_path was not present in the upstream environment config; staged as null for preflight-only validation")
    elif auto_existing is None:
        warnings.append(f"trained_autoencoder_path did not resolve to an existing file during preflight: {auto_config_path}")
    ckpt_config_path, ckpt_existing = resolve_existing_path(original_env.get("existing_ckpt_filepath"))
    if original_env.get("existing_ckpt_filepath") and ckpt_existing is None:
        warnings.append(f"existing_ckpt_filepath did not resolve to an existing file and was staged as null: {ckpt_config_path}")

    env_cfg.update({
        "data_base_dir": as_repo_path(data_root),
        "json_data_list": as_repo_path(cfg_dir / "input_datalist.json"),
        "embedding_base_dir": as_repo_path(out / "embeddings"),
        "model_dir": as_repo_path(out / "checkpoints"),
        "output_dir": as_repo_path(out / "inference"),
        "modality_mapping_path": as_repo_path(mapping_path),
        "trained_autoencoder_path": auto_config_path,
        "existing_ckpt_filepath": ckpt_config_path if ckpt_existing is not None else None,
    })
    for key in ("embedding_base_dir", "model_dir", "output_dir"):
        v = Path(env_cfg[key])
        resolved = v if v.is_absolute() else repo / v
        if not under(resolved, out):
            errors.append(f"staged environment key {key} does not point under requested output directory: {env_cfg[key]}")
    write_json(env_path, env_cfg)

if isinstance(model_cfg, dict):
    train_cfg = model_cfg.setdefault("diffusion_unet_train", {})
    if isinstance(train_cfg, dict):
        train_cfg["n_epochs"] = 1
        train_cfg["batch_size"] = 1
        train_cfg["learning_rate"] = 1e-5
        train_cfg["cache_rate"] = 0.0
        if "lr" in train_cfg:
            train_cfg["lr"] = 1e-5
    else:
        errors.append("model config key diffusion_unet_train exists but is not an object")
    write_json(model_path, model_cfg)

summary["output_local_work_dirs"] = {
    "embedding_base_dir": as_repo_path(out / "embeddings"),
    "model_dir": as_repo_path(out / "checkpoints"),
    "output_dir": as_repo_path(out / "inference"),
}
summary["preflight_boundary"] = "validated datalist JSON, relative image existence, supported modality values, and output-local staged runtime config paths; no training or inference launched"
summary_path = out / "preflight_summary.json"
write_json(summary_path, summary)

if errors:
    print(f"preflight failed; see {as_repo_path(summary_path)}", file=sys.stderr)
    sys.exit(1)
print(f"preflight passed; summary written to {as_repo_path(summary_path)}")
PY
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=1

```bash
python3 - <<'PY'
import json, os, shutil, sys
from pathlib import Path

repo = Path.cwd()
in_dir = Path("runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset")
out = Path("runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/gpt55/without/repeat_2")
cfg_out = out / "configs"

def rel(p):
    p = Path(p)
    try:
        return str(p.resolve().relative_to(repo.resolve()))
    except Exception:
        return str(p)

def is_under(child, parent):
    try:
        Path(child).resolve().relative_to(Path(parent).resolve())
        return True
    except Exception:
        return False

up_candidates = []
if os.environ.get("NV_GENERATE_ROOT"):
    up_candidates.append(Path(os.environ["NV_GENERATE_ROOT"]))
up_candidates += [
    Path(".workbench_data/upstreams/NV-Generate-CTMR"),
    Path(".workbench_data/upstreams/NV-Generate-CTMR-main"),
]
up_candidates += sorted(Path(".workbench_data/upstreams").glob("*Generate*CTMR*")) if Path(".workbench_data/upstreams").exists() else []
up = next((p for p in up_candidates if (p / "configs").is_dir()), None)
if up is None:
    raise SystemExit("Could not locate readable NV-Generate-CTMR checkout configs; set NV_GENERATE_ROOT or populate .workbench_data/upstreams/NV-Generate-CTMR")

src_cfg = up / "configs"
required = [
    "config_network_rflow.json",
    "environment_maisi_diff_model_rflow-mr-brain.json",
    "config_maisi_diff_model_rflow-mr-brain.json",
    "modality_mapping.json",
]
missing = [str(src_cfg / f) for f in required if not (src_cfg / f).is_file()]
if missing:
    raise SystemExit("Missing upstream config file(s): " + ", ".join(missing))

cfg_out.mkdir(parents=True, exist_ok=True)
(out / "embeddings").mkdir(parents=True, exist_ok=True)
(out / "checkpoints").mkdir(parents=True, exist_ok=True)
(out / "infer").mkdir(parents=True, exist_ok=True)

staged = {}
for name in required:
    dst = cfg_out / name
    shutil.copy2(src_cfg / name, dst)
    staged[name] = dst

def load_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

errors, warnings = [], []
if not in_dir.is_dir():
    errors.append(f"input data root does not exist or is not a directory: {in_dir}")

datalist_candidates = []
if in_dir.is_dir():
    preferred_names = {"dataset.json": 0, "datalist.json": 1, "data_list.json": 2, "dataset_0.json": 3}
    for p in sorted(in_dir.rglob("*.json")):
        try:
            obj = load_json(p)
        except Exception:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("training"), list):
            datalist_candidates.append((preferred_names.get(p.name, 50), len(p.parts), str(p), p, obj))
datalist_src, datalist = None, None
if datalist_candidates:
    datalist_candidates.sort()
    datalist_src, datalist = datalist_candidates[0][3], datalist_candidates[0][4]
else:
    errors.append(f"no MONAI-style JSON datalist with a training list found under {in_dir}")

datalist_staged = cfg_out / "datalist.json"
if datalist is not None:
    with open(datalist_staged, "w", encoding="utf-8") as f:
        json.dump(datalist, f, indent=2)

modality_mapping = load_json(staged["modality_mapping.json"])
def recursive_mri_keys(x):
    found = set()
    if isinstance(x, dict):
        for k, v in x.items():
            if isinstance(k, str) and k.startswith("mri"):
                found.add(k)
            found |= recursive_mri_keys(v)
    elif isinstance(x, list):
        for v in x:
            found |= recursive_mri_keys(v)
    return found

supported_modalities = recursive_mri_keys(modality_mapping)
if not supported_modalities:
    for key in ("modality_mapping", "modality_map", "modality_dict"):
        if isinstance(modality_mapping, dict) and isinstance(modality_mapping.get(key), dict):
            supported_modalities = set(modality_mapping[key].keys())
            break
if not supported_modalities and isinstance(modality_mapping, dict):
    supported_modalities = set(modality_mapping.keys())
if not supported_modalities:
    errors.append("could not infer supported modality labels from staged modality_mapping.json")

training = datalist.get("training", []) if isinstance(datalist, dict) else []
used_modalities = sorted({x.get("modality") for x in training if isinstance(x, dict) and isinstance(x.get("modality"), str)})
if datalist is not None and not training:
    errors.append("datalist training list is empty")

checked_images = []
for i, item in enumerate(training):
    if not isinstance(item, dict):
        errors.append(f"training[{i}] is not an object")
        continue
    image = item.get("image")
    modality = item.get("modality")
    if not isinstance(image, str) or not image:
        errors.append(f"training[{i}].image is missing or not a non-empty string")
        continue
    image_path = Path(image)
    if image_path.is_absolute():
        errors.append(f"training[{i}].image is absolute, expected path relative to data root: {image}")
        continue
    resolved = (in_dir / image_path).resolve()
    if not is_under(resolved, in_dir):
        errors.append(f"training[{i}].image escapes data root: {image}")
    elif not resolved.is_file():
        errors.append(f"training[{i}].image does not exist under data root: {image}")
    else:
        checked_images.append(image)
    if not isinstance(modality, str) or not modality:
        errors.append(f"training[{i}].modality is missing or not a non-empty string")
    elif supported_modalities and modality not in supported_modalities:
        errors.append(f"training[{i}].modality is not supported by modality_mapping.json: {modality}")

env_path = staged["environment_maisi_diff_model_rflow-mr-brain.json"]
model_path = staged["config_maisi_diff_model_rflow-mr-brain.json"]
net_path = staged["config_network_rflow.json"]

env_cfg = load_json(env_path)
model_cfg = load_json(model_path)

def normalize_existing_path(value):
    if value in (None, ""):
        return value
    p = Path(str(value))
    if p.is_absolute():
        return str(p)
    if p.exists():
        return rel(p)
    up_rel = up / p
    if up_rel.exists():
        return rel(up_rel)
    return str(value)

env_cfg["data_base_dir"] = str(in_dir)
env_cfg["json_data_list"] = str(datalist_staged)
env_cfg["embedding_base_dir"] = str(out / "embeddings")
env_cfg["model_dir"] = str(out / "checkpoints")
env_cfg["output_dir"] = str(out / "infer")
env_cfg["modality_mapping_path"] = str(staged["modality_mapping.json"])
env_cfg["trained_autoencoder_path"] = normalize_existing_path(env_cfg.get("trained_autoencoder_path"))
env_cfg["existing_ckpt_filepath"] = normalize_existing_path(env_cfg.get("existing_ckpt_filepath"))

train_cfg = model_cfg.setdefault("diffusion_unet_train", {})
if not isinstance(train_cfg, dict):
    errors.append("config_maisi_diff_model_rflow-mr-brain.json diffusion_unet_train is not an object")
    train_cfg = {}
    model_cfg["diffusion_unet_train"] = train_cfg
train_cfg["n_epochs"] = 1
train_cfg["batch_size"] = 1
train_cfg["learning_rate"] = train_cfg.get("learning_rate", train_cfg.get("lr", 1e-5))
train_cfg["cache_rate"] = 0.0
train_cfg["num_workers"] = 0

for key in ("embedding_base_dir", "model_dir", "output_dir"):
    if not is_under(env_cfg[key], out):
        errors.append(f"environment config {key} is not output-local: {env_cfg[key]}")
for key in ("json_data_list", "modality_mapping_path"):
    if not is_under(env_cfg[key], out):
        errors.append(f"environment config {key} is not staged under output directory: {env_cfg[key]}")

if not env_cfg.get("trained_autoencoder_path"):
    warnings.append("trained_autoencoder_path is empty in the staged environment config")
elif not Path(str(env_cfg["trained_autoencoder_path"])).exists():
    warnings.append(f"trained_autoencoder_path does not exist from repo root; preflight did not launch training: {env_cfg['trained_autoencoder_path']}")
if env_cfg.get("existing_ckpt_filepath") and not Path(str(env_cfg["existing_ckpt_filepath"])).exists():
    warnings.append(f"existing_ckpt_filepath does not exist from repo root; preflight did not launch training: {env_cfg['existing_ckpt_filepath']}")

with open(env_path, "w", encoding="utf-8") as f:
    json.dump(env_cfg, f, indent=2)
with open(model_path, "w", encoding="utf-8") as f:
    json.dump(model_cfg, f, indent=2)

pyroot = rel(up)
runnable_commands = {
    "create_training_data": f"PYTHONPATH={pyroot} python -m scripts.diff_model_create_training_data -e {env_path} -c {model_path} -t {net_path} -g 1",
    "train": f"PYTHONPATH={pyroot} python -m scripts.diff_model_train -e {env_path} -c {model_path} -t {net_path} -g 1",
    "infer_optional": f"PYTHONPATH={pyroot} python -m scripts.diff_model_infer -e {env_path} -c {model_path} -t {net_path} -g 1",
}

summary = {
    "ok": not errors,
    "preflight_only": True,
    "model_variant": "rflow-mr-brain diffusion-UNet finetuning",
    "input_data_root": str(in_dir),
    "datalist_source": str(datalist_src) if datalist_src else None,
    "datalist_staged": str(datalist_staged) if datalist is not None else None,
    "training_count": len(training),
    "checked_image_count": len(checked_images),
    "modality_labels_used": used_modalities,
    "supported_modality_label_count": len(supported_modalities),
    "staged_configs": {k: str(v) for k, v in staged.items()},
    "output_local_dirs": {
        "embedding_base_dir": env_cfg.get("embedding_base_dir"),
        "model_dir": env_cfg.get("model_dir"),
        "output_dir": env_cfg.get("output_dir"),
    },
    "runtime_train_overrides": {
        "diffusion_unet_train.n_epochs": train_cfg.get("n_epochs"),
        "diffusion_unet_train.batch_size": train_cfg.get("batch_size"),
        "diffusion_unet_train.learning_rate": train_cfg.get("learning_rate"),
        "diffusion_unet_train.cache_rate": train_cfg.get("cache_rate"),
        "diffusion_unet_train.num_workers": train_cfg.get("num_workers"),
    },
    "runnable_commands_not_executed": runnable_commands,
    "warnings": warnings,
    "errors": errors,
}
summary_path = out / "preflight_summary.json"
with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)
print(f"wrote {summary_path}")
if errors:
    raise SystemExit(1)
PY
```

Repeat 3: score 3/5, passed=no, steps=unresolved, exit=None

```bash
python - <<'PY'
import json, os, re, shutil, sys
from pathlib import Path

out_dir = Path("runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/gpt55/without/repeat_3")
input_dir = Path("runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset")
config_dir = out_dir / "configs"
summary_path = out_dir / "preflight_summary.json"

required_sources = {
    "configs/config_network_rflow.json": config_dir / "config_maisi.json",
    "configs/environment_maisi_diff_model_rflow-mr-brain.json": config_dir / "environment_maisi_diff_model.json",
    "configs/config_maisi_diff_model_rflow-mr-brain.json": config_dir / "config_maisi_diff_model.json",
    "configs/modality_mapping.json": config_dir / "modality_mapping.json",
}

def under(child: Path, parent: Path) -> bool:
    child_r = child.resolve(strict=False)
    parent_r = parent.resolve(strict=False)
    return child_r == parent_r or parent_r in child_r.parents

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")

errors = []
warnings = []
out_dir.mkdir(parents=True, exist_ok=True)
config_dir.mkdir(parents=True, exist_ok=True)
for d in ["embeddings", "checkpoints", "inference", "logs"]:
    (out_dir / d).mkdir(parents=True, exist_ok=True)

nv_candidates = []
if os.environ.get("NV_GENERATE_ROOT"):
    nv_candidates.append(Path(os.environ["NV_GENERATE_ROOT"]))
nv_candidates.append(Path(".workbench_data/upstreams/NV-Generate-CTMR"))
upstreams = Path(".workbench_data/upstreams")
if upstreams.exists():
    nv_candidates.extend(sorted(upstreams.glob("*NV-Generate-CTMR*")))
nv_root = next((p for p in nv_candidates if all((p / src).is_file() for src in required_sources)), None)
if nv_root is None:
    errors.append("Could not find an NV-Generate-CTMR checkout containing the required config files.")
else:
    for src, dst in required_sources.items():
        shutil.copyfile(nv_root / src, dst)

datalist_src = None
datalist = None
if not input_dir.is_dir():
    errors.append(f"Input dataset directory does not exist: {input_dir}")
else:
    candidates = []
    for p in sorted(input_dir.rglob("*.json")):
        try:
            obj = load_json(p)
        except Exception:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("training"), list):
            candidates.append((p, obj))
    preferred = {"dataset.json", "datalist.json", "data_list.json", "dataset_0.json"}
    candidates.sort(key=lambda x: (0 if x[0].name in preferred else 1, len(x[0].parts), str(x[0])))
    if not candidates:
        errors.append(f"No MONAI-style datalist JSON with a 'training' list was found under {input_dir}.")
    else:
        datalist_src, datalist = candidates[0]
        if len(candidates) > 1:
            warnings.append("Multiple datalist-like JSON files found; selected the first preferred sorted candidate.")
        shutil.copyfile(datalist_src, out_dir / "input_datalist.json")

supported_modalities = set()
if (config_dir / "modality_mapping.json").is_file():
    try:
        modality_mapping = load_json(config_dir / "modality_mapping.json")
        def collect_modalities(x):
            if isinstance(x, dict):
                for k, v in x.items():
                    if isinstance(k, str) and k.startswith("mri_"):
                        supported_modalities.add(k)
                    collect_modalities(v)
            elif isinstance(x, list):
                for v in x:
                    collect_modalities(v)
            elif isinstance(x, str) and x.startswith("mri_"):
                supported_modalities.add(x)
        collect_modalities(modality_mapping)
    except Exception as e:
        errors.append(f"Could not parse staged modality mapping: {e}")
else:
    errors.append("Staged modality_mapping.json is missing.")

training_count = 0
modalities_seen = set()
if datalist is not None:
    training = datalist.get("training")
    if not isinstance(training, list) or not training:
        errors.append("Datalist 'training' must be a non-empty list.")
    else:
        training_count = len(training)
        for i, item in enumerate(training):
            if not isinstance(item, dict):
                errors.append(f"training[{i}] is not an object.")
                continue
            image = item.get("image")
            modality = item.get("modality")
            if not isinstance(image, str) or not image:
                errors.append(f"training[{i}] is missing a non-empty string 'image'.")
            else:
                image_path = Path(image)
                if image_path.is_absolute():
                    errors.append(f"training[{i}].image is absolute; expected a path relative to the input dataset root: {image}")
                resolved = (input_dir / image_path).resolve(strict=False)
                if not under(resolved, input_dir):
                    errors.append(f"training[{i}].image escapes the input dataset root: {image}")
                elif not resolved.exists():
                    errors.append(f"training[{i}].image does not exist under the input dataset root: {image}")
            if not isinstance(modality, str) or not modality:
                errors.append(f"training[{i}] is missing a non-empty string 'modality'.")
            else:
                modalities_seen.add(modality)
                if supported_modalities and modality not in supported_modalities:
                    errors.append(f"training[{i}].modality is not present in staged modality_mapping.json: {modality}")

if (config_dir / "environment_maisi_diff_model.json").is_file():
    env_cfg = load_json(config_dir / "environment_maisi_diff_model.json")
    ckpts = sorted([p for ext in ("*.pt", "*.pth", "*.ckpt") for p in input_dir.rglob(ext)]) if input_dir.exists() else []
    auto_ckpt = os.environ.get("NV_GENERATE_TRAINED_AUTOENCODER_PATH")
    if not auto_ckpt:
        auto_matches = [p for p in ckpts if re.search(r"(autoencoder|vae|auto)", p.name, re.I)]
        auto_ckpt = str(auto_matches[0]) if auto_matches else env_cfg.get("trained_autoencoder_path", "")
    diff_ckpt = os.environ.get("NV_GENERATE_DIFFUSION_CKPT_PATH")
    if not diff_ckpt:
        diff_matches = [p for p in ckpts if re.search(r"(diff|diffusion|unet|model)", p.name, re.I) and str(p) != str(auto_ckpt)]
        diff_ckpt = str(diff_matches[0]) if diff_matches else env_cfg.get("existing_ckpt_filepath", None)
    env_cfg.update({
        "data_base_dir": str(input_dir),
        "json_data_list": str(out_dir / "input_datalist.json"),
        "embedding_base_dir": str(out_dir / "embeddings"),
        "model_dir": str(out_dir / "checkpoints"),
        "output_dir": str(out_dir / "inference"),
        "modality_mapping_path": str(config_dir / "modality_mapping.json"),
        "trained_autoencoder_path": auto_ckpt,
        "existing_ckpt_filepath": diff_ckpt if diff_ckpt else None,
    })
    write_json(config_dir / "environment_maisi_diff_model.json", env_cfg)
    output_local_keys = ["json_data_list", "embedding_base_dir", "model_dir", "output_dir", "modality_mapping_path"]
    for k in output_local_keys:
        if not under(Path(env_cfg[k]), out_dir):
            errors.append(f"Environment config key '{k}' does not point under the requested output directory: {env_cfg[k]}")
else:
    env_cfg = {}
    errors.append("Staged environment config is missing.")

if (config_dir / "config_maisi_diff_model.json").is_file():
    model_cfg = load_json(config_dir / "config_maisi_diff_model.json")
    train_cfg = model_cfg.setdefault("diffusion_unet_train", {})
    train_cfg["n_epochs"] = 1
    train_cfg["batch_size"] = 1
    train_cfg["learning_rate"] = 1e-5
    train_cfg["cache_rate"] = 0.0
    write_json(config_dir / "config_maisi_diff_model.json", model_cfg)
else:
    errors.append("Staged diffusion model config is missing.")

summary = {
    "status": "failed" if errors else "passed",
    "input_dataset": str(input_dir),
    "selected_datalist": str(datalist_src) if datalist_src else None,
    "staged_datalist": str(out_dir / "input_datalist.json") if datalist_src else None,
    "training_count": training_count,
    "modalities_seen": sorted(modalities_seen),
    "supported_mr_modalities_from_mapping": sorted(supported_modalities),
    "staged_configs": {str(dst): str(nv_root / src) if nv_root else None for src, dst in required_sources.items()},
    "preflight_scope": "JSON/path/modality/config-staging validation only; no training or inference launched.",
    "environment_config_values": {k: env_cfg.get(k) for k in ["data_base_dir", "json_data_list", "embedding_base_dir", "model_dir", "output_dir", "modality_mapping_path", "trained_autoencoder_path", "existing_ckpt_filepath"]} if env_cfg else {},
    "warnings": warnings,
    "errors": errors,
}
write_json(summary_path, summary)
print(f"wrote {summary_path}")
if errors:
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
PY
```

### Opus 4.7, with arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && \
python skills/nv-generate-mr-brain-finetune/scripts/run_mr_brain_finetune.py \
  runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_datalist.json \
  --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_dataset \
  --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/opus/with/repeat_1 \
  --modality mri_t1 \
  --preflight
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && \
python skills/nv-generate-mr-brain-finetune/scripts/run_mr_brain_finetune.py \
  runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_datalist.json \
  --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_dataset \
  --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/opus/with/repeat_2 \
  --modality mri_t1 \
  --preflight
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python skills/nv-generate-mr-brain-finetune/scripts/run_mr_brain_finetune.py runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_datalist.json --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_dataset --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/opus/with/repeat_3 --modality mri_t1 --preflight
```

### Opus 4.7, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 3/5, passed=no, steps=unresolved, exit=None

```bash
mkdir -p runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/opus/without/repeat_1/configs && OUT=runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/opus/without/repeat_1 && IN=runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset && UPSTREAM="$NV_GENERATE_ROOT" && DATALIST=$(find "$IN" -maxdepth 3 -name "*.json" | head -1) && cp "$UPSTREAM/configs/config_network_rflow.json" "$OUT/configs/" && cp "$UPSTREAM/configs/environment_maisi_diff_model_rflow-mr-brain.json" "$OUT/configs/" && cp "$UPSTREAM/configs/config_maisi_diff_model_rflow-mr-brain.json" "$OUT/configs/" && cp "$UPSTREAM/configs/modality_mapping.json" "$OUT/configs/" && cp "$DATALIST" "$OUT/configs/datalist.json" && python -c "
import json, os, sys
out = '$OUT'
inp = '$IN'
datalist_path = os.path.join(out, 'configs', 'datalist.json')
mod_map_path = os.path.join(out, 'configs', 'modality_mapping.json')
env_path = os.path.join(out, 'configs', 'environment_maisi_diff_model_rflow-mr-brain.json')
cfg_path = os.path.join(out, 'configs', 'config_maisi_diff_model_rflow-mr-brain.json')
with open(datalist_path) as f: dl = json.load(f)
with open(mod_map_path) as f: mm = json.load(f)
supported = set(mm.keys()) if isinstance(mm, dict) else set(mm)
training = dl.get('training', [])
assert training, 'empty training'
data_root = inp
missing = []
bad_mod = []
for it in training:
    p = os.path.join(data_root, it['image'])
    if not os.path.exists(p): missing.append(it['image'])
    if it.get('modality') not in supported: bad_mod.append(it.get('modality'))
with open(env_path) as f: env = json.load(f)
env['data_base_dir'] = os.path.abspath(data_root)
env['json_data_list'] = os.path.abspath(datalist_path)
env['embedding_base_dir'] = os.path.abspath(os.path.join(out, 'embeddings'))
env['model_dir'] = os.path.abspath(os.path.join(out, 'models'))
env['output_dir'] = os.path.abspath(os.path.join(out, 'inference'))
env['modality_mapping_path'] = os.path.abspath(mod_map_path)
with open(env_path, 'w') as f: json.dump(env, f, indent=2)
with open(cfg_path) as f: cfg = json.load(f)
if 'diffusion_unet_train' in cfg:
    cfg['diffusion_unet_train']['n_epochs'] = 1
    if 'cache_rate' in cfg['diffusion_unet_train']: cfg['diffusion_unet_train']['cache_rate'] = 0.0
with open(cfg_path, 'w') as f: json.dump(cfg, f, indent=2)
summary = {
  'datalist': datalist_path,
  'training_count': len(training),
  'missing_paths': missing,
  'unsupported_modalities': bad_mod,
  'data_base_dir': env['data_base_dir'],
  'embedding_base_dir': env['embedding_base_dir'],
  'model_dir': env['model_dir'],
  'staged_configs': sorted(os.listdir(os.path.join(out, 'configs'))),
  'preflight_ok': not missing and not bad_mod,
}
with open(os.path.join(out, 'preflight_summary.json'), 'w') as f: json.dump(summary, f, indent=2)
print(json.dumps(summary, indent=2))
sys.exit(0 if summary['preflight_ok'] else 1)
"
```

Repeat 2: score 3/5, passed=no, steps=unresolved, exit=None

```bash
mkdir -p runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/opus/without/repeat_2/configs runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/opus/without/repeat_2/embeddings runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/opus/without/repeat_2/models runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/opus/without/repeat_2/output && IN=runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset && OUT=runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/opus/without/repeat_2 && DATALIST=$(find "$IN" -maxdepth 3 -name '*.json' | head -n1) && cp "$DATALIST" "$OUT/datalist.json" && python -c "
import json, os, sys
inp=os.environ['IN']; out=os.environ['OUT']
dl=json.load(open(os.environ['DATALIST']))
upstream=os.environ.get('NV_GENERATE_ROOT','.workbench_data/upstreams/NV-Generate-CTMR')
mm_path=None
for cand in [os.path.join(upstream,'configs/modality_mapping.json'), os.path.join('.workbench_data/upstreams/NV-Generate-CTMR/configs/modality_mapping.json')]:
    if os.path.exists(cand): mm_path=cand; break
supported=['mri_t1','mri_t2','mri_flair','mri_swi','mri_t1_ss','mri_t2_ss','mri_flair_ss','mri_swi_ss']
if mm_path:
    try:
        mm=json.load(open(mm_path))
        if isinstance(mm,dict): supported=list(mm.keys()) or supported
    except Exception: pass
training=dl.get('training',[])
errors=[]; checked=[]
if not training: errors.append('training list empty')
data_root=inp
for it in training:
    rel=it.get('image'); mod=it.get('modality')
    p=os.path.join(data_root, rel) if rel else None
    ok_path=bool(p and os.path.exists(p))
    ok_mod=mod in supported
    checked.append({'image':rel,'modality':mod,'path_exists':ok_path,'modality_supported':ok_mod,'resolved':p})
    if not ok_path: errors.append(f'missing:{rel}')
    if not ok_mod: errors.append(f'unsupported_modality:{mod}')
env_cfg={
  'data_base_dir': data_root,
  'json_data_list': os.path.join(out,'datalist.json'),
  'embedding_base_dir': os.path.join(out,'embeddings'),
  'model_dir': os.path.join(out,'models'),
  'output_dir': os.path.join(out,'output'),
  'modality_mapping_path': mm_path,
  'trained_autoencoder_path': None,
  'existing_ckpt_filepath': None
}
json.dump(env_cfg, open(os.path.join(out,'configs/environment_maisi_diff_model_rflow-mr-brain.json'),'w'), indent=2)
model_cfg={'diffusion_unet_train':{'n_epochs':1,'batch_size':1,'lr':1e-5,'cache_rate':0.0}}
json.dump(model_cfg, open(os.path.join(out,'configs/config_maisi_diff_model_rflow-mr-brain.json'),'w'), indent=2)
json.dump({'placeholder':'staged from upstream config_network_rflow.json'}, open(os.path.join(out,'configs/config_network_rflow.json'),'w'), indent=2)
summary={'datalist':os.environ['DATALIST'],'data_root':data_root,'num_training':len(training),'errors':errors,'items':checked,'preflight_ok':len(errors)==0,'staged_configs':sorted(os.listdir(os.path.join(out,'configs')))}
json.dump(summary, open(os.path.join(out,'preflight_summary.json'),'w'), indent=2)
print(json.dumps({'preflight_ok':summary['preflight_ok'],'num_training':summary['num_training'],'errors':errors[:5]},indent=2))
"
```

Repeat 3: score 3/5, passed=no, steps=unresolved, exit=None

```bash
mkdir -p runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/opus/without/repeat_3/configs && OUT=runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/opus/without/repeat_3 && IN=runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset && UP="$(if [ -n "$NV_GENERATE_ROOT" ] && [ -d "$NV_GENERATE_ROOT" ]; then echo "$NV_GENERATE_ROOT"; else find .workbench_data/upstreams -maxdepth 4 -type d -iname '*NV-Generate*CTMR*' -print -quit; fi)" && echo "Upstream: $UP" && for f in config_network_rflow.json environment_maisi_diff_model_rflow-mr-brain.json config_maisi_diff_model_rflow-mr-brain.json modality_mapping.json; do cp "$UP/configs/$f" "$OUT/configs/$f"; done && DATALIST="$(find "$IN" -maxdepth 3 -type f -name '*.json' | head -n1)" && DATAROOT="$(dirname "$DATALIST")" && cp "$DATALIST" "$OUT/configs/datalist.json" && python - <<'PY'
import json, os, sys
out = "runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/opus/without/repeat_3"
inp = "runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset"
dl_path = os.path.join(out, "configs", "datalist.json")
env_path = os.path.join(out, "configs", "environment_maisi_diff_model_rflow-mr-brain.json")
mm_path = os.path.join(out, "configs", "modality_mapping.json")
mcfg_path = os.path.join(out, "configs", "config_maisi_diff_model_rflow-mr-brain.json")
errors = []
with open(dl_path) as f:
    dl = json.load(f)
training = dl.get("training", [])
if not training: errors.append("empty training")
# pick data root: prefer dir of datalist, else input_dataset itself
candidates = [os.path.dirname(dl_path), inp]
data_root = None
for c in candidates:
    if all(os.path.exists(os.path.join(c, e["image"])) for e in training):
        data_root = c; break
if data_root is None:
    data_root = inp
    for e in training:
        p = os.path.join(data_root, e["image"])
        if not os.path.exists(p): errors.append(f"missing image: {p}")
with open(mm_path) as f:
    mm = json.load(f)
supported = set(mm.keys()) if isinstance(mm, dict) else set(mm)
modalities = sorted({e.get("modality","") for e in training})
unsupported = [m for m in modalities if m and m not in supported]
if unsupported: errors.append(f"unsupported modalities: {unsupported}")
# stage env config
with open(env_path) as f:
    env = json.load(f)
env["data_base_dir"] = data_root
env["json_data_list"] = dl_path
env["embedding_base_dir"] = os.path.join(out, "embeddings")
env["model_dir"] = os.path.join(out, "models")
env["output_dir"] = os.path.join(out, "predictions")
env["modality_mapping_path"] = mm_path
os.makedirs(env["embedding_base_dir"], exist_ok=True)
os.makedirs(env["model_dir"], exist_ok=True)
os.makedirs(env["output_dir"], exist_ok=True)
with open(env_path, "w") as f:
    json.dump(env, f, indent=2)
# minimal preflight tweak to model config
with open(mcfg_path) as f:
    mcfg = json.load(f)
if "diffusion_unet_train" in mcfg:
    mcfg["diffusion_unet_train"]["n_epochs"] = 1
    if "cache_rate" in mcfg["diffusion_unet_train"]:
        mcfg["diffusion_unet_train"]["cache_rate"] = 0.0
with open(mcfg_path, "w") as f:
    json.dump(mcfg, f, indent=2)
summary = {
    "ok": not errors,
    "errors": errors,
    "data_base_dir": data_root,
    "datalist": dl_path,
    "n_training": len(training),
    "modalities": modalities,
    "staged_configs": {
        "env": env_path, "model": mcfg_path,
        "modality_mapping": mm_path,
        "network": os.path.join(out, "configs", "config_network_rflow.json"),
    },
    "preflight": "no GPU training launched",
}
with open(os.path.join(out, "preflight_summary.json"), "w") as f:
    json.dump(summary, f, indent=2)
print(json.dumps(summary, indent=2))
sys.exit(0 if not errors else 1)
PY
```

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `runs/with_vs_without_nv/studies/nv_generate_mr_brain_finetune_codex_opus/` |
| Generated outputs | `runs/with_vs_without_nv/nv_generate_mr_brain_finetune_codex_opus/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_generate_mr_brain_finetune_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
