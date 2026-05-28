# `nv_generate_vae_finetune`: Codex/Opus LLM+SKILL.md vs LLM+README

Status: strict audit passed for refreshed artifacts on May 28, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

This report compares `LLM + SKILL.md` with `LLM + upstream README/guide`. The completed direct-API run used the corrected embedded-doc minimal prompt because those backends cannot read repo files. The fair NAT/tool-agent prompt artifact is A2-style: it gives a natural user request, a neutral staged input path, an output directory, and tells the agent which arm-specific document to read. It does not spell out operational details such as entrypoints, labels, model variants, or config filenames outside the documentation arm.

## Experiment Question

Does `LLM + SKILL.md` make an agent better at reading documentation and taking the right action than `LLM + upstream README/guide`?

## User Request Shape

The prompt request for the GPT-5.5 with-skill arm was:

> The VAE finetuning preflight input bundle is at runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset. Validate and stage the shortest preflight-scale workflow check, and write outputs under runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/gpt55/with/repeat_1.

The staged user input for every arm was `runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset`. The source fixture `skills/nv-generate-vae-finetune/fixtures` was used only to stage that neutral input path.

Fair path-prompt artifact: `tools/nat_audit/data/eval_nv_model_studies_nv_generate_vae_finetune_prompts.json`

## Result

| Backend | Arm | Mean score | Passes | Steps | Exit | Tier 5 | Failed tiers |
|---|---|---:|---:|---|---|---|---|
| GPT-5.5 / Codex | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | preflight payload reported (3) | none |
| GPT-5.5 / Codex | without | 3.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | None (3) | command does not reference an expected runnable surface (3) | T1: entrypoint marker (3); T5: command does not reference an expected runnable surface (3) |
| Opus 4.7 | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | preflight payload reported (3) | none |
| Opus 4.7 | without | 3.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | None (3) | command does not reference an expected runnable surface (3) | T1: entrypoint marker (3); T5: command does not reference an expected runnable surface (3) |

## Analysis

SKILL.md paired advantage: the with-skill arms passed 6/6 backend-repeat trials with an average score of 5.0/5; the README-only arms passed 0/6 backend-repeat trials with an average score of 3.0/5.

SKILL.md paired advantage: SKILL.md wins 6/6 matched backend-repeat pairs, README-only wins 0/6, and 0/6 are ties. Pass/fail is the primary outcome; score breaks ties only when pass status is equal. Exact one-sided sign-test p=0.01562 across 6 decisive pair(s).

Outcome-support gate: Supports SKILL.md advantage. SKILL.md wins 6/6 matched pair(s); README-only wins 0/6; sign-test p=0.01562.

Each backend/arm/skill configuration was repeated three times. A repeat is independent: it has its own output directory, and each execution attempt inside the repeat creates a fresh venv before running the generated command. Dependency and model download caches are shared only as documented test-environment caches under `.workbench_data/with_vs_without_cache` (`PIP_CACHE_DIR=.workbench_data/with_vs_without_cache/pip`, `HF_HOME=.workbench_data/with_vs_without_cache/huggingface`, `HF_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `HUGGINGFACE_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `TRANSFORMERS_CACHE=.workbench_data/with_vs_without_cache/huggingface/transformers`, `TORCH_HOME=.workbench_data/with_vs_without_cache/torch`, `XDG_CACHE_HOME=.workbench_data/with_vs_without_cache/xdg`, `CONDA_PKGS_DIRS=.workbench_data/with_vs_without_cache/conda_pkgs`, `UV_CACHE_DIR=.workbench_data/with_vs_without_cache/uv`, `CUDA_CACHE_PATH=.workbench_data/with_vs_without_cache/cuda`, `NUMBA_CACHE_DIR=.workbench_data/with_vs_without_cache/numba`).

The main baseline uses `max_correction_steps=0`: each repeat sends one prompt, executes the extracted command once, and records pass/fail, runtime, tokens, and deterministic failure analysis. The repair-loop implementation remains available for separate diagnostic experiments, but it is not part of this comparison.

All with-skill repeats exited successfully and produced artifacts accepted by the deterministic grader. That means the final SKILL.md surface was repeatable for both tested agent backends.

The README-only commands did not pass tier 5. Typical failure modes were unsafe generated shell cleanup, missing schema fields, missing model/control details, or upstream commands that did not execute cleanly from Medical AI Skills root.

Tier 2 is intentionally strict: a command only earns it if it uses the staged user input path `runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset`.

## Token Profiling

Token counts are provider-reported values saved in each repeat JSON. Reasoning tokens are shown only when the provider returned that subfield and are a subset of completion tokens, not an additional cost to add to total tokens. Execution time is averaged only across repeats that reached command execution; no-command-extracted repeats still count toward token totals.

| Backend | Arm | Repeats | Passes | Attempts | Prompt tokens | Completion tokens | Reasoning tokens | Total tokens | Mean total/repeat | Executed | Mean exec s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GPT-5.5 / Codex | with | 3 | 3 | 3 | 5,088 | 1,863 | 1,374 | 6,951 | 2,317.0 | 3 | 0.0 |
| GPT-5.5 / Codex | without | 3 | 0 | 3 | 3,015 | 16,128 | 9,727 | 19,143 | 6,381.0 | 0 | n/a |
| Opus 4.7 | with | 3 | 3 | 3 | 8,832 | 744 | 0 | 9,576 | 3,192.0 | 3 | 0.0 |
| Opus 4.7 | without | 3 | 0 | 3 | 5,055 | 4,325 | 0 | 9,380 | 3,126.7 | 0 | n/a |

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
| 2 | 0 | 3/5 | no | None | T1: entrypoint marker; T5: command does not reference an expected runnable surface | tier_1: entrypoint marker Repair: Use the runnable surface documented for this arm.<br>tier_5: command does not reference an expected runnable surface Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference an expected runnable surface Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
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
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python skills/nv-generate-vae-finetune/scripts/run_vae_finetune.py runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_datalist.json --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_dataset --output-dir runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/gpt55/with/repeat_1 --preflight
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
mkdir -p runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/gpt55/with/repeat_2 && export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python skills/nv-generate-vae-finetune/scripts/run_vae_finetune.py runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_datalist.json --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_dataset --output-dir runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/gpt55/with/repeat_2 --preflight
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
mkdir -p runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/gpt55/with/repeat_3 && PYTHONDONTWRITEBYTECODE=1 NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" python skills/nv-generate-vae-finetune/scripts/run_vae_finetune.py runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_datalist.json --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_dataset --output-dir runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/gpt55/with/repeat_3 --preflight
```

### GPT-5.5 / Codex, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 3/5, passed=no, steps=unresolved, exit=None

```bash
python - <<'PY'
from pathlib import Path
import os, json, shutil, datetime, sys

inp = Path("runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset")
out = Path("runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/gpt55/without/repeat_1")
cfg_dir = out / "configs"
orig_dir = out / "upstream_configs_original"
log_dir = out / "logs"
ckpt_dir = out / "checkpoints"
summary_path = out / "preflight_summary.json"

for p in (out, cfg_dir, orig_dir, log_dir, ckpt_dir):
    p.mkdir(parents=True, exist_ok=True)

if not inp.is_dir():
    raise SystemExit(f"Input data root not found: {inp}")

upstream_candidates = []
if os.environ.get("NV_GENERATE_ROOT"):
    upstream_candidates.append(Path(os.environ["NV_GENERATE_ROOT"]))
upstream_candidates += [
    Path(".workbench_data/upstreams/NV-Generate-CTMR"),
    Path(".workbench_data/upstreams/nv-generate-ctmr"),
]
matches = list(Path(".workbench_data/upstreams").glob("**/configs/config_maisi_vae_train.json")) if Path(".workbench_data/upstreams").exists() else []
upstream_candidates += [m.parents[1] for m in matches]
upstream = None
required = [
    "configs/config_network_rflow.json",
    "configs/environment_maisi_vae_train.json",
    "configs/config_maisi_vae_train.json",
]
for cand in dict.fromkeys(upstream_candidates):
    if all((cand / r).is_file() for r in required):
        upstream = cand
        break
if upstream is None:
    raise SystemExit("Could not locate NV-Generate-CTMR upstream configs required for VAE preflight staging.")

def load_json(p):
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def safe_rel_image(s):
    pp = Path(s)
    return (not pp.is_absolute()) and (".." not in pp.parts)

mri_aliases = {
    "mri", "mr", "t1", "t1w", "t1ce", "t1c", "t2", "t2w", "flair",
    "dwi", "adc", "pd", "pdw", "swi", "mprage"
}
ct_aliases = {"ct", "cta"}
def norm_class(v):
    c = str(v).strip().lower().replace("-", "_").replace(" ", "_")
    if c in ct_aliases or c.startswith("ct_"):
        return "ct"
    if c in mri_aliases or c.startswith("mr_") or c.startswith("mri_") or "mri" in c:
        return "mri"
    return None

json_candidates = sorted(inp.glob("*.json")) + sorted(inp.glob("**/*.json"))
seen, ordered = set(), []
for p in json_candidates:
    if p not in seen:
        seen.add(p); ordered.append(p)

selected = None
selected_data = None
selected_val_key = None
errors = []
for p in ordered:
    try:
        d = load_json(p)
    except Exception as e:
        errors.append(f"{p}: not JSON: {e}")
        continue
    if not isinstance(d, dict):
        errors.append(f"{p}: top-level JSON is not an object")
        continue
    train = d.get("training") or []
    val_key = "validation" if d.get("validation") else ("testing" if d.get("testing") else None)
    val = d.get(val_key) if val_key else []
    if isinstance(train, list) and isinstance(val, list) and train and val:
        selected, selected_data, selected_val_key = p, d, val_key
        break
    errors.append(f"{p}: missing non-empty training and validation/testing splits")

if selected is None:
    raise SystemExit("No valid MONAI-style datalist found under input_dataset. Checked: " + "; ".join(errors[:10]))

def validate_split(name, rows):
    staged = []
    for i, item in enumerate(rows):
        if not isinstance(item, dict):
            raise SystemExit(f"{name}[{i}] is not an object")
        img = item.get("image")
        if not img or not isinstance(img, str):
            raise SystemExit(f"{name}[{i}] missing string image path")
        if not safe_rel_image(img):
            raise SystemExit(f"{name}[{i}] image path must be relative and stay within data root: {img}")
        if not (inp / img).is_file():
            raise SystemExit(f"{name}[{i}] image file not found under data root: {inp / img}")
        cls = norm_class(item.get("class", ""))
        if cls not in {"ct", "mri"}:
            raise SystemExit(f"{name}[{i}] unsupported/unknown class label {item.get('class')!r}; expected CT or MRI-normalizable label")
        out_item = dict(item)
        out_item["class"] = cls
        staged.append(out_item)
    return staged

staged_datalist = {
    "training": validate_split("training", selected_data["training"]),
    "validation": validate_split(selected_val_key, selected_data[selected_val_key]),
}
staged_datalist_path = cfg_dir / "datalist_maisi_vae_preflight.json"
with staged_datalist_path.open("w", encoding="utf-8") as f:
    json.dump(staged_datalist, f, indent=2)

link = out / "input_dataset"
if link.exists() or link.is_symlink():
    if link.is_symlink() and Path(os.readlink(link)) == Path(os.path.relpath(inp, link.parent)):
        pass
    elif link.is_dir() and not link.is_symlink():
        pass
    else:
        raise SystemExit(f"Refusing to replace existing staged input path: {link}")
else:
    link.symlink_to(os.path.relpath(inp, link.parent), target_is_directory=True)

def copy_and_patch_config(rel):
    src = upstream / rel
    shutil.copy2(src, orig_dir / Path(rel).name)
    data = load_json(src)
    if isinstance(data, dict):
        data.setdefault("_preflight_note", "Staged for MAISI VAE finetuning preflight only; no training launched.")
        for k, v in list(data.items()):
            lk = k.lower()
            if lk in {"data_base_dir", "data_root", "dataset_dir", "root_dir"}:
                data[k] = str(link)
            elif lk in {"json_data_list", "json_list", "datalist", "data_list_file", "data_list"}:
                data[k] = str(staged_datalist_path)
            elif lk in {"model_dir", "ckpt_dir", "checkpoint_dir", "output_dir", "save_dir", "results_dir"}:
                data[k] = str(ckpt_dir if "model" in lk or "ckpt" in lk or "checkpoint" in lk else out)
            elif lk in {"tfevent_path", "tensorboard_dir", "log_dir", "logging_dir"}:
                data[k] = str(log_dir)
            elif lk in {"trained_autoencoder_path", "resume_ckpt", "resume_checkpoint"} and (v in ("", None) or isinstance(v, str)):
                data[k] = None
        data["_preflight_paths"] = {
            "data_root": str(link),
            "datalist": str(staged_datalist_path),
            "output_dir": str(out),
            "checkpoint_dir": str(ckpt_dir),
            "log_dir": str(log_dir),
        }
    dst = cfg_dir / Path(rel).name
    with dst.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return dst

staged_configs = [copy_and_patch_config(r) for r in required]

summary = {
    "status": "preflight_passed",
    "timestamp_utc": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
    "mode": "maisi_vae_finetune_preflight_only_no_training",
    "input_data_root": str(inp),
    "staged_output_dir": str(out),
    "upstream_root_read_only": str(upstream),
    "selected_datalist": str(selected),
    "validation_source_split": selected_val_key,
    "staged_datalist": str(staged_datalist_path),
    "staged_configs": [str(p) for p in staged_configs],
    "required_upstream_configs": required,
    "checks": {
        "non_empty_training": len(staged_datalist["training"]),
        "non_empty_validation": len(staged_datalist["validation"]),
        "all_image_paths_relative": True,
        "all_images_exist_under_data_root": True,
        "classes_normalized_to": sorted(set([r["class"] for r in staged_datalist["training"] + staged_datalist["validation"]])),
        "runtime_outputs_staged_under": str(out),
    },
}
with summary_path.open("w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)
print(json.dumps(summary, indent=2))
PY
```

Repeat 2: score 3/5, passed=no, steps=unresolved, exit=None

```bash
python - <<'PY'
import json, os, shutil, sys
from pathlib import Path

inp = Path("runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset")
out = Path("runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/gpt55/without/repeat_2")
up = Path(os.environ.get("NV_GENERATE_ROOT", ".workbench_data/upstreams/NV-Generate-CTMR"))

required = [
    Path("configs/config_network_rflow.json"),
    Path("configs/environment_maisi_vae_train.json"),
    Path("configs/config_maisi_vae_train.json"),
    Path("scripts/transforms.py"),
    Path("scripts/utils.py"),
    Path("scripts/download_model_data.py"),
]
config_rels = required[:3]

summary = {
    "workflow": "nv_generate_vae_finetune_preflight",
    "model_component": "MAISI VAE autoencoder finetuning preflight",
    "input_dataset": str(inp),
    "output_dir": str(out),
    "upstream_root_read_only": str(up),
    "status": "fail",
    "errors": [],
    "staged_files": [],
    "checked_upstream_files": [str(up / r) for r in required],
}

def err(msg):
    summary["errors"].append(msg)

def normalize_class(v):
    s = str(v).strip().lower().replace("_", "-")
    if s in {"ct", "computed-tomography", "computed tomography"}:
        return "ct"
    mri_aliases = {
        "mri", "mr", "magnetic-resonance", "magnetic resonance",
        "t1", "t1w", "t1-weighted", "t2", "t2w", "t2-weighted",
        "flair", "dwi", "adc", "pd", "pdw", "swi", "gre", "mprage", "tof",
    }
    if s in mri_aliases or s.startswith(("t1", "t2")) or any(tok in s for tok in ["mri", "magnetic resonance", "flair", "dwi", "adc", "swi", "mprage"]):
        return "mri"
    return None

def image_values(entry):
    im = entry.get("image")
    if isinstance(im, str):
        return [im]
    if isinstance(im, list) and all(isinstance(x, str) for x in im):
        return im
    return None

def rewrite_paths(obj, stage_data_root, staged_datalist):
    path_tokens = ("path", "dir", "root", "folder", "file", "log", "ckpt", "checkpoint")
    def repl(k, v):
        lk = k.lower()
        if not isinstance(v, str) or not any(t in lk for t in path_tokens):
            return v
        name = Path(v).name or "value"
        if "data" in lk and ("base" in lk or "root" in lk or "dir" in lk):
            return str(stage_data_root)
        if "list" in lk or name.endswith(".json"):
            return str(staged_datalist)
        if "tensor" in lk or "log" in lk:
            return str(out / "tensorboard")
        if "cache" in lk:
            return str(out / "cache")
        if "ckpt" in lk or "checkpoint" in lk or "model" in lk or "autoencoder" in lk:
            return str((out / "checkpoints" / name) if Path(name).suffix else (out / "checkpoints"))
        if "output" in lk or "result" in lk:
            return str(out)
        return str((out / "runtime_paths" / name) if Path(name).suffix else (out / name))
    if isinstance(obj, dict):
        return {k: rewrite_paths(repl(k, v), stage_data_root, staged_datalist) for k, v in obj.items()}
    if isinstance(obj, list):
        return [rewrite_paths(x, stage_data_root, staged_datalist) for x in obj]
    return obj

try:
    out.mkdir(parents=True, exist_ok=True)
    for d in ["configs", "checkpoints", "tensorboard", "cache", "runtime_paths"]:
        (out / d).mkdir(parents=True, exist_ok=True)

    if not inp.is_dir():
        err(f"input dataset directory not found: {inp}")

    for rel in required:
        if not (up / rel).exists():
            err(f"required upstream file not found: {up / rel}")

    datalist = None
    datalist_path = None
    if inp.is_dir():
        candidates = []
        for p in sorted(inp.rglob("*.json")):
            try:
                data = json.loads(p.read_text())
            except Exception:
                continue
            if isinstance(data, dict) and isinstance(data.get("training"), list) and (isinstance(data.get("validation"), list) or isinstance(data.get("testing"), list)):
                pri = {"dataset.json": 0, "datalist.json": 1, "dataset_0.json": 2}.get(p.name, 10)
                candidates.append((pri, len(p.parts), p, data))
        if candidates:
            _, _, datalist_path, datalist = sorted(candidates)[0]
        else:
            err(f"no MONAI-style datalist JSON with training and validation/testing splits found under {inp}")

    staged_datalist = out / "datalist_preflight.json"
    stage_data_root = out / "input_dataset"
    if inp.exists() and not stage_data_root.exists():
        os.symlink(os.path.relpath(inp, out), stage_data_root, target_is_directory=True)
    elif stage_data_root.exists():
        try:
            if stage_data_root.resolve() != inp.resolve():
                err(f"staged input_dataset path already exists and does not resolve to {inp}: {stage_data_root}")
        except Exception as e:
            err(f"could not verify staged input_dataset link {stage_data_root}: {e}")

    if datalist is not None:
        val_key = "validation" if isinstance(datalist.get("validation"), list) else "testing"
        if not datalist.get("training"):
            err("training split is empty")
        if not datalist.get(val_key):
            err(f"{val_key} split is empty")

        staged = {"training": [], "validation": []}
        counts = {"training": 0, val_key: 0}
        normalized_label_counts = {"ct": 0, "mri": 0}
        checked_images = 0

        for split in ["training", val_key]:
            out_split = "validation" if split == val_key else "training"
            for i, entry in enumerate(datalist.get(split, [])):
                if not isinstance(entry, dict):
                    err(f"{split}[{i}] is not an object")
                    continue
                imgs = image_values(entry)
                if imgs is None:
                    err(f"{split}[{i}] has invalid or missing image field")
                    continue
                norm = normalize_class(entry.get("class"))
                if norm not in {"ct", "mri"}:
                    err(f"{split}[{i}] class label {entry.get('class')!r} does not normalize to ct or mri")
                    continue
                new_entry = dict(entry)
                new_entry["class"] = norm
                staged[out_split].append(new_entry)
                counts[split] += 1
                normalized_label_counts[norm] += 1
                for rel in imgs:
                    rp = Path(rel)
                    checked_images += 1
                    if rp.is_absolute() or ".." in rp.parts:
                        err(f"{split}[{i}] image path is not a safe relative path: {rel}")
                    elif not (inp / rp).exists():
                        err(f"{split}[{i}] image path does not exist under data root: {rel}")

        if val_key == "testing":
            staged["testing"] = list(staged["validation"])

        staged_datalist.write_text(json.dumps(staged, indent=2, sort_keys=True) + "\n")
        summary.update({
            "datalist_source": str(datalist_path),
            "datalist_staged": str(staged_datalist),
            "validation_source_split": val_key,
            "split_counts": counts,
            "normalized_label_counts": normalized_label_counts,
            "relative_image_paths_checked": checked_images,
        })
        summary["staged_files"].append(str(staged_datalist))

    for rel in config_rels:
        src = up / rel
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            try:
                cfg = json.loads(src.read_text())
                cfg = rewrite_paths(cfg, stage_data_root, staged_datalist)
                if rel.name == "environment_maisi_vae_train.json":
                    cfg.update({
                        "data_base_dir": str(stage_data_root),
                        "json_data_list": str(staged_datalist),
                        "model_dir": str(out / "checkpoints"),
                        "tfevent_path": str(out / "tensorboard"),
                        "output_dir": str(out),
                    })
                dst.write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n")
                summary["staged_files"].append(str(dst))
            except Exception as e:
                err(f"failed to stage config {src}: {e}")

    summary["runtime_dirs"] = {
        "configs": str(out / "configs"),
        "checkpoints": str(out / "checkpoints"),
        "tensorboard": str(out / "tensorboard"),
        "cache": str(out / "cache"),
        "staged_data_root": str(stage_data_root),
    }
    summary["preflight_only"] = True
    summary["training_started"] = False
    summary["status"] = "pass" if not summary["errors"] else "fail"
finally:
    out.mkdir(parents=True, exist_ok=True)
    (out / "preflight_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

print(f"wrote {out / 'preflight_summary.json'}")
if summary["errors"]:
    print("\n".join(summary["errors"]), file=sys.stderr)
    sys.exit(1)
PY
```

Repeat 3: score 3/5, passed=no, steps=unresolved, exit=None

```bash
python3 - <<'PY'
import json, os, shutil, sys
from pathlib import Path
from collections import Counter

input_root = Path("runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset")
out = Path("runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/gpt55/without/repeat_3")
required_upstream = [
    "configs/config_network_rflow.json",
    "configs/environment_maisi_vae_train.json",
    "configs/config_maisi_vae_train.json",
    "scripts/transforms.py",
    "scripts/utils.py",
    "scripts/download_model_data.py",
]

def common_is_within(child: Path, parent: Path) -> bool:
    try:
        return os.path.commonpath([str(child.resolve()), str(parent.resolve())]) == str(parent.resolve())
    except Exception:
        return False

def find_upstream_root():
    candidates = []
    if os.environ.get("NV_GENERATE_ROOT"):
        candidates.append(Path(os.environ["NV_GENERATE_ROOT"]))
    candidates += [Path(".workbench_data/upstreams/NV-Generate-CTMR"), Path("NV-Generate-CTMR")]
    search_parent = Path(".workbench_data/upstreams")
    if search_parent.exists():
        candidates += [p for p in sorted(search_parent.iterdir()) if p.is_dir()]
    seen = set()
    for c in candidates:
        c = Path(c)
        key = str(c)
        if key in seen:
            continue
        seen.add(key)
        if all((c / rel).exists() for rel in required_upstream):
            return c
    raise RuntimeError("Could not locate NV-Generate-CTMR upstream root with required VAE files")

upstream_root = find_upstream_root()
for forbidden in [Path(".workbench_data/upstreams"), Path(os.environ["NV_GENERATE_ROOT"]) if os.environ.get("NV_GENERATE_ROOT") else None]:
    if forbidden and common_is_within(out, forbidden):
        raise RuntimeError(f"Refusing to write output under forbidden upstream path: {forbidden}")

summary = {
    "status": "failed",
    "input_dataset": str(input_root),
    "output_dir": str(out),
    "upstream_root_read_only": str(upstream_root),
    "preflight_only": True,
    "training_run": False,
    "errors": [],
}

try:
    if not input_root.is_dir():
        raise RuntimeError(f"Input dataset directory not found: {input_root}")

    if out.exists():
        shutil.rmtree(out)
    (out / "configs").mkdir(parents=True, exist_ok=True)
    (out / "datalists").mkdir(parents=True, exist_ok=True)
    (out / "runtime" / "checkpoints").mkdir(parents=True, exist_ok=True)
    (out / "runtime" / "tensorboard").mkdir(parents=True, exist_ok=True)

    datalist_candidates = []
    for p in sorted(input_root.rglob("*.json")):
        try:
            obj = json.loads(p.read_text())
        except Exception:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("training"), list) and (isinstance(obj.get("validation"), list) or isinstance(obj.get("testing"), list)):
            datalist_candidates.append((p, obj))
    if not datalist_candidates:
        raise RuntimeError("No MONAI-style datalist JSON found with non-empty-capable training and validation/testing keys")
    datalist_path, datalist = datalist_candidates[0]

    val_key = "validation" if isinstance(datalist.get("validation"), list) else "testing"
    if not datalist.get("training"):
        raise RuntimeError("Datalist training split is empty")
    if not datalist.get(val_key):
        raise RuntimeError(f"Datalist {val_key} split is empty")

    mri_aliases = {"mri", "mr", "t1", "t1w", "t1ce", "t1gd", "t2", "t2w", "flair", "adc", "dwi", "diffusion"}
    modality_counts = Counter()
    zero_byte_images = []
    staged = {}
    checked_images = []

    for split in ["training", val_key]:
        staged[split] = []
        for idx, item in enumerate(datalist[split]):
            if not isinstance(item, dict):
                raise RuntimeError(f"{split}[{idx}] is not an object")
            image = item.get("image")
            if not isinstance(image, str) or not image:
                raise RuntimeError(f"{split}[{idx}] missing non-empty image path")
            image_path = Path(image)
            if image_path.is_absolute() or ".." in image_path.parts:
                raise RuntimeError(f"{split}[{idx}] image path must be relative under data root: {image}")
            full_image = input_root / image_path
            if not full_image.exists():
                raise RuntimeError(f"{split}[{idx}] image file not found under data root: {image}")
            raw_class = str(item.get("class", "")).strip().lower()
            if raw_class == "ct":
                norm_class = "ct"
            elif raw_class in mri_aliases or raw_class.startswith("mri"):
                norm_class = "mri"
            else:
                raise RuntimeError(f"{split}[{idx}] class/modality must normalize to ct or mri, got: {item.get('class')!r}")
            staged_item = dict(item)
            staged_item["class"] = norm_class
            staged[split].append(staged_item)
            modality_counts[norm_class] += 1
            checked_images.append(str(full_image))
            try:
                if full_image.stat().st_size == 0:
                    zero_byte_images.append(str(full_image))
            except OSError:
                pass

    staged_datalist = out / "datalists" / "vae_preflight_datalist.json"
    staged_datalist.write_text(json.dumps(staged, indent=2, sort_keys=True) + "\n")

    def rewrite_runtime_paths(obj):
        if isinstance(obj, dict):
            new = {}
            for k, v in obj.items():
                lk = k.lower()
                if isinstance(v, str):
                    if lk in {"json_data_list", "datalist", "data_list", "data_list_file"} or ("json" in lk and "list" in lk):
                        new[k] = str(staged_datalist)
                    elif lk in {"data_base_dir", "data_root", "data_dir", "root_dir"} or ("data" in lk and ("base" in lk or "root" in lk)):
                        new[k] = str(input_root)
                    elif any(tok in lk for tok in ["output", "model_dir", "save_dir", "result", "checkpoint_dir", "ckpt_dir"]):
                        new[k] = str(out / "runtime" / "checkpoints")
                    elif any(tok in lk for tok in ["tensorboard", "tfevent", "logdir", "log_dir"]):
                        new[k] = str(out / "runtime" / "tensorboard")
                    else:
                        new[k] = v
                else:
                    new[k] = rewrite_runtime_paths(v)
            return new
        if isinstance(obj, list):
            return [rewrite_runtime_paths(x) for x in obj]
        return obj

    staged_configs = []
    for rel in required_upstream[:3]:
        src = upstream_root / rel
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        cfg = json.loads(src.read_text())
        cfg = rewrite_runtime_paths(cfg)
        if rel.endswith("environment_maisi_vae_train.json"):
            cfg["data_base_dir"] = str(input_root)
            cfg["json_data_list"] = str(staged_datalist)
            cfg["model_dir"] = str(out / "runtime" / "checkpoints")
            cfg["tfevent_path"] = str(out / "runtime" / "tensorboard")
            cfg["preflight_output_dir"] = str(out)
        if rel.endswith("config_maisi_vae_train.json"):
            cfg["preflight_only"] = True
        dst.write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n")
        staged_configs.append(str(dst))

    summary.update({
        "status": "ok",
        "selected_datalist": str(datalist_path),
        "staged_datalist": str(staged_datalist),
        "validation_split": val_key,
        "training_count": len(staged["training"]),
        f"{val_key}_count": len(staged[val_key]),
        "modalities_normalized": dict(sorted(modality_counts.items())),
        "checked_image_count": len(checked_images),
        "zero_byte_image_count": len(zero_byte_images),
        "zero_byte_images": zero_byte_images,
        "required_upstream_files_found": [str(upstream_root / rel) for rel in required_upstream],
        "staged_configs": staged_configs,
        "runtime_dirs": {
            "checkpoints": str(out / "runtime" / "checkpoints"),
            "tensorboard": str(out / "runtime" / "tensorboard"),
        },
    })
except Exception as e:
    summary["errors"].append(str(e))
    out.mkdir(parents=True, exist_ok=True)
    (out / "preflight_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    raise SystemExit(f"VAE finetune preflight failed; see {out / 'preflight_summary.json'}: {e}")

(out / "preflight_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
print(f"VAE finetune preflight staged successfully: {out / 'preflight_summary.json'}")
PY
```

### Opus 4.7, with arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python skills/nv-generate-vae-finetune/scripts/run_vae_finetune.py runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_datalist.json --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_dataset --output-dir runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/opus/with/repeat_1 --preflight
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python skills/nv-generate-vae-finetune/scripts/run_vae_finetune.py runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_datalist.json --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_dataset --output-dir runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/opus/with/repeat_2 --preflight
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python skills/nv-generate-vae-finetune/scripts/run_vae_finetune.py runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_datalist.json --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_dataset --output-dir runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/opus/with/repeat_3 --preflight
```

### Opus 4.7, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 3/5, passed=no, steps=unresolved, exit=None

```bash
OUT=runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/opus/without/repeat_1 && IN=runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset && mkdir -p "$OUT/configs" "$OUT/datalist" && DATALIST=$(find "$IN" -maxdepth 3 -name '*.json' | head -n1) && DATAROOT=$(dirname "$DATALIST") && cp "$DATALIST" "$OUT/datalist/datalist.json" && for f in config_network_rflow.json environment_maisi_vae_train.json config_maisi_vae_train.json; do SRC=$(find .workbench_data/upstreams -path "*/configs/$f" 2>/dev/null | head -n1); [ -n "$SRC" ] && cp "$SRC" "$OUT/configs/$f"; done && python -c "
import json, os, sys
out=os.environ['OUT']; dl=os.environ['DATALIST']; root=os.environ['DATAROOT']
d=json.load(open(dl))
tr=d.get('training',[]); va=d.get('validation') or d.get('testing') or []
errs=[]; checked=[]
if not tr: errs.append('empty training split')
if not va: errs.append('empty validation/testing split')
for split,items in (('training',tr),('validation',va)):
    for it in items:
        img=it.get('image',''); cls=(it.get('class') or '').lower()
        p=os.path.join(root,img)
        ok=os.path.exists(p)
        norm='mri' if 'mr' in cls else ('ct' if 'ct' in cls else None)
        if not ok: errs.append(f'missing:{p}')
        if norm is None: errs.append(f'bad-class:{cls}')
        checked.append({'split':split,'image':img,'exists':ok,'class':cls,'normalized':norm})
cfgs=sorted(os.listdir(os.path.join(out,'configs'))) if os.path.isdir(os.path.join(out,'configs')) else []
summary={'mode':'preflight','input_bundle':os.environ['IN'],'data_root':root,'datalist':dl,'n_training':len(tr),'n_validation':len(va),'staged_configs':cfgs,'staged_configs_dir':os.path.join(out,'configs'),'staged_datalist':os.path.join(out,'datalist','datalist.json'),'entries':checked,'errors':errs,'status':'ok' if not errs else 'failed'}
json.dump(summary, open(os.path.join(out,'preflight_summary.json'),'w'), indent=2)
print(json.dumps({'status':summary['status'],'errors':errs[:5],'n_training':len(tr),'n_validation':len(va)}, indent=2))
" OUT="$OUT" IN="$IN" DATALIST="$OUT/datalist/datalist.json" DATAROOT="$DATAROOT"
```

Repeat 2: score 3/5, passed=no, steps=unresolved, exit=None

```bash
OUT=runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/opus/without/repeat_2 && IN=runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset && mkdir -p "$OUT/configs" && UPSTREAM=$(find .workbench_data/upstreams -type d -name 'NV-Generate-CTMR*' 2>/dev/null | head -n1) && [ -z "$UPSTREAM" ] && UPSTREAM="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" || true && for f in config_network_rflow.json environment_maisi_vae_train.json config_maisi_vae_train.json; do if [ -f "$UPSTREAM/configs/$f" ]; then cp "$UPSTREAM/configs/$f" "$OUT/configs/$f"; fi; done && python - <<'PY'
import json, os, sys, glob
out = "runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/opus/without/repeat_2"
inp = "runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset"
summary = {"input_bundle": inp, "output_dir": out, "checks": {}, "errors": []}

# Locate datalist
candidates = []
for pat in ("*.json", "**/*.json"):
    candidates += glob.glob(os.path.join(inp, pat), recursive=True)
candidates = [c for c in candidates if "datalist" in os.path.basename(c).lower() or os.path.basename(c).lower() in ("dataset.json","data.json")]
if not candidates:
    candidates = sorted(glob.glob(os.path.join(inp, "*.json")))
summary["datalist_candidates"] = candidates

if not candidates:
    summary["errors"].append("no datalist json found")
    summary["status"] = "fail"
else:
    dl_path = candidates[0]
    summary["datalist"] = dl_path
    with open(dl_path) as f:
        dl = json.load(f)
    train = dl.get("training", [])
    val = dl.get("validation") or dl.get("testing") or []
    summary["checks"]["training_count"] = len(train)
    summary["checks"]["validation_count"] = len(val)
    if not train:
        summary["errors"].append("empty training split")
    if not val:
        summary["errors"].append("empty validation/testing split")
    data_root = os.path.dirname(dl_path)
    # try common roots
    roots_to_try = [data_root, inp]
    missing = []
    bad_class = []
    allowed = {"ct","mri"}
    for entry in train + val:
        img = entry.get("image","")
        cls = str(entry.get("class","")).lower()
        if cls not in allowed:
            bad_class.append({"image": img, "class": cls})
        found = False
        for r in roots_to_try:
            if os.path.exists(os.path.join(r, img)):
                found = True
                break
        if not found:
            missing.append(img)
    summary["checks"]["missing_images"] = missing
    summary["checks"]["non_normalized_classes"] = bad_class
    if missing:
        summary["errors"].append(f"{len(missing)} image paths missing under data root")
    if bad_class:
        summary["errors"].append(f"{len(bad_class)} entries not normalized to ct/mri")
    # stage datalist copy
    staged_dl = os.path.join(out, "datalist.json")
    with open(staged_dl, "w") as f:
        json.dump(dl, f, indent=2)
    summary["staged_datalist"] = staged_dl

# Edit env config to point under OUT if present
env_path = os.path.join(out, "configs", "environment_maisi_vae_train.json")
if os.path.exists(env_path):
    with open(env_path) as f:
        env = json.load(f)
    for k in list(env.keys()):
        if any(s in k.lower() for s in ("dir","path","root")) and isinstance(env[k], str):
            env[k] = os.path.join(out, os.path.basename(env[k].rstrip("/"))) if env[k] else env[k]
    with open(env_path, "w") as f:
        json.dump(env, f, indent=2)
    summary["staged_env_config"] = env_path

summary["staged_configs"] = sorted(glob.glob(os.path.join(out, "configs", "*.json")))
summary["status"] = "fail" if summary["errors"] else "pass"
summary["scope"] = "preflight staging only; no training, no clinical claims"

with open(os.path.join(out, "preflight_summary.json"), "w") as f:
    json.dump(summary, f, indent=2)
print(json.dumps(summary, indent=2))
PY
```

Repeat 3: score 3/5, passed=no, steps=unresolved, exit=None

```bash
OUT=runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/opus/without/repeat_3 && IN=runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset && UP=.workbench_data/upstreams/NV-Generate-CTMR && mkdir -p "$OUT/configs" "$OUT/datalist" "$OUT/logs" && (find "$UP" -path '*/configs/config_network_rflow.json' -print -quit | xargs -I{} cp {} "$OUT/configs/config_network_rflow.json" 2>/dev/null || true) && (find "$UP" -path '*/configs/environment_maisi_vae_train.json' -print -quit | xargs -I{} cp {} "$OUT/configs/environment_maisi_vae_train.json" 2>/dev/null || true) && (find "$UP" -path '*/configs/config_maisi_vae_train.json' -print -quit | xargs -I{} cp {} "$OUT/configs/config_maisi_vae_train.json" 2>/dev/null || true) && DATALIST=$(find "$IN" -maxdepth 3 -name '*.json' | head -n1) && cp "$DATALIST" "$OUT/datalist/datalist.json" && python -c "
import json, os, sys
inp_root = '$IN'
out = '$OUT'
dl_path = os.path.join(out, 'datalist', 'datalist.json')
with open(dl_path) as f:
    dl = json.load(f)
train = dl.get('training', [])
val = dl.get('validation') or dl.get('testing') or []
def check(entries, root):
    results = []
    for e in entries:
        img = e.get('image','')
        cls = (e.get('class') or '').lower()
        norm = 'mri' if cls and cls != 'ct' else ('ct' if cls == 'ct' else 'mri')
        full = os.path.join(root, img)
        results.append({'image': img, 'class_in': cls, 'class_norm': norm, 'exists': os.path.exists(full)})
    return results
tr = check(train, inp_root)
va = check(val, inp_root)
summary = {
    'input_root': inp_root,
    'datalist_staged': dl_path,
    'configs_staged_dir': os.path.join(out, 'configs'),
    'configs_present': sorted(os.listdir(os.path.join(out, 'configs'))),
    'training_count': len(tr),
    'validation_count': len(va),
    'training_nonempty': len(tr) > 0,
    'validation_nonempty': len(va) > 0,
    'training_entries': tr,
    'validation_entries': va,
    'all_train_exist': all(x['exists'] for x in tr),
    'all_val_exist': all(x['exists'] for x in va),
    'modalities_valid': all(x['class_norm'] in ('ct','mri') for x in tr+va),
    'preflight_only': True,
    'note': 'Preflight staging check only; no VAE training executed.'
}
ok = summary['training_nonempty'] and summary['validation_nonempty'] and summary['all_train_exist'] and summary['all_val_exist'] and summary['modalities_valid']
summary['preflight_passed'] = ok
with open(os.path.join(out, 'preflight_summary.json'), 'w') as f:
    json.dump(summary, f, indent=2)
print(json.dumps(summary, indent=2))
"
```

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `examples/studies/with_vs_without_skill/nv_generate_vae_finetune_codex_opus/` |
| Generated outputs | `runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_generate_vae_finetune_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
