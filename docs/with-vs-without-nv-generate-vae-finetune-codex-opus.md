# `nv_generate_vae_finetune`: Codex/Opus LLM+SKILL.md vs LLM+README

Status: strict audit passed for refreshed artifacts on May 29, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

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
| GPT-5.5 / Codex | with | 3 | 3 | 3 | 10,143 | 1,111 | 676 | 11,254 | 3,751.3 | 3 | 0.0 |
| GPT-5.5 / Codex | without | 3 | 0 | 3 | 3,015 | 12,505 | 6,858 | 15,520 | 5,173.3 | 0 | n/a |
| Opus 4.7 | with | 3 | 3 | 3 | 16,977 | 759 | 0 | 17,736 | 5,912.0 | 3 | 0.0 |
| Opus 4.7 | without | 3 | 0 | 3 | 5,055 | 3,879 | 0 | 8,934 | 2,978.0 | 0 | n/a |

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
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python skills/nv-generate-vae-finetune/scripts/run_vae_finetune.py runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_datalist.json --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_dataset --output-dir runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/gpt55/with/repeat_1 --modality mri --preflight
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python skills/nv-generate-vae-finetune/scripts/run_vae_finetune.py runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_datalist.json --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_dataset --output-dir runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/gpt55/with/repeat_2 --modality mri --preflight
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python skills/nv-generate-vae-finetune/scripts/run_vae_finetune.py runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_datalist.json --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_dataset --output-dir runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/gpt55/with/repeat_3 --modality mri --preflight
```

### GPT-5.5 / Codex, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 3/5, passed=no, steps=unresolved, exit=None

```bash
python - <<'PY'
from pathlib import Path
import json, os, shutil, datetime

repo = Path.cwd()
data_root = repo / "runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset"
out = repo / "runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/gpt55/without/repeat_1"
stage = out / "staged_runtime"
cfg_out = stage / "configs"
summary_path = out / "preflight_summary.json"

out.mkdir(parents=True, exist_ok=True)
cfg_out.mkdir(parents=True, exist_ok=True)

upstream_candidates = []
if os.environ.get("NV_GENERATE_ROOT"):
    upstream_candidates.append(Path(os.environ["NV_GENERATE_ROOT"]))
upstream_candidates += [
    repo / ".workbench_data/upstreams/NV-Generate-CTMR",
    repo / "NV-Generate-CTMR",
]
needed_cfgs = [
    "configs/config_network_rflow.json",
    "configs/environment_maisi_vae_train.json",
    "configs/config_maisi_vae_train.json",
]
upstream = next((p for p in upstream_candidates if all((p / f).exists() for f in needed_cfgs)), None)
if upstream is None:
    raise SystemExit("Could not locate NV-Generate-CTMR upstream configs for read-only staging")

for rel in needed_cfgs:
    dst = cfg_out / Path(rel).name
    shutil.copy2(upstream / rel, dst)

json_candidates = sorted(data_root.rglob("*.json"))
datalist_path = None
datalist = None
for p in json_candidates:
    try:
        obj = json.loads(p.read_text())
    except Exception:
        continue
    if isinstance(obj, dict) and isinstance(obj.get("training"), list) and (isinstance(obj.get("validation"), list) or isinstance(obj.get("testing"), list)):
        datalist_path, datalist = p, obj
        break
if datalist_path is None:
    raise SystemExit(f"No MONAI-style datalist with training and validation/testing splits found under {data_root}")

val_key = "validation" if isinstance(datalist.get("validation"), list) else "testing"
errors = []
warnings = []
normalized_counts = {"ct": 0, "mri": 0}
checked = {"training": 0, val_key: 0}
staged_datalist = {"training": [], val_key: []}

def norm_modality(v):
    s = str(v or "").strip().lower()
    if s in {"ct", "computed_tomography"}:
        return "ct"
    if s in {"mri", "mr", "t1", "t1w", "t2", "t2w", "flair", "dwi", "adc", "pd", "proton_density"}:
        return "mri"
    return None

for split in ["training", val_key]:
    items = datalist.get(split, [])
    if not items:
        errors.append(f"{split} split is empty")
        continue
    for i, item in enumerate(items):
        checked[split] += 1
        if not isinstance(item, dict):
            errors.append(f"{split}[{i}] is not an object")
            continue
        image = item.get("image")
        if not image or not isinstance(image, str):
            errors.append(f"{split}[{i}] missing string image path")
            continue
        if Path(image).is_absolute() or ".." in Path(image).parts:
            errors.append(f"{split}[{i}] image path must be relative and stay under data root: {image}")
            continue
        if not (data_root / image).exists():
            errors.append(f"{split}[{i}] image file does not exist under data root: {image}")
        cls = norm_modality(item.get("class", item.get("modality", item.get("label"))))
        if cls is None:
            errors.append(f"{split}[{i}] modality/class must normalize to ct or mri")
            cls = str(item.get("class", item.get("modality", item.get("label", "")))).lower()
        else:
            normalized_counts[cls] += 1
        staged_item = dict(item)
        staged_item["class"] = cls
        staged_datalist[split].append(staged_item)

staged_datalist_path = stage / "datalist_vae_preflight.json"
staged_datalist_path.write_text(json.dumps(staged_datalist, indent=2) + "\n")

def rewrite_paths(obj):
    if isinstance(obj, dict):
        out_obj = {}
        for k, v in obj.items():
            lk = str(k).lower()
            if lk in {"data_root", "dataroot", "data_dir", "dataset_dir", "root_dir", "root"}:
                out_obj[k] = str(data_root)
            elif lk in {"json_list", "jsonlist", "datalist", "data_list", "dataset_json"}:
                out_obj[k] = str(staged_datalist_path)
            elif lk in {"output_dir", "output_path", "model_dir", "ckpt_dir", "checkpoint_dir", "log_dir", "tfevent_path", "tensorboard_dir"}:
                out_obj[k] = str(out / k)
            elif isinstance(v, (dict, list)):
                out_obj[k] = rewrite_paths(v)
            else:
                out_obj[k] = v
        return out_obj
    if isinstance(obj, list):
        return [rewrite_paths(x) for x in obj]
    return obj

staged_configs = []
for p in sorted(cfg_out.glob("*.json")):
    try:
        obj = json.loads(p.read_text())
        obj = rewrite_paths(obj)
        p.write_text(json.dumps(obj, indent=2) + "\n")
        staged_configs.append(str(p.relative_to(repo)))
    except Exception as e:
        warnings.append(f"Copied but did not JSON-rewrite {p}: {e}")
        staged_configs.append(str(p.relative_to(repo)))

summary = {
    "status": "pass" if not errors else "fail",
    "scope": "preflight_only_no_training",
    "timestamp_utc": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
    "input_data_root": str(data_root.relative_to(repo)),
    "source_datalist": str(datalist_path.relative_to(repo)),
    "staged_datalist": str(staged_datalist_path.relative_to(repo)),
    "validation_split": val_key,
    "checked_counts": checked,
    "normalized_modality_counts": normalized_counts,
    "staged_configs": staged_configs,
    "expected_preflight_boundaries": [
        "non-empty training and validation/testing splits",
        "relative image paths exist under data root",
        "modalities normalize to ct or mri",
        "runtime files staged under requested output directory",
        "no placeholder training executed"
    ],
    "errors": errors,
    "warnings": warnings,
}
summary_path.write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
if errors:
    raise SystemExit(1)
PY
```

Repeat 2: score 3/5, passed=no, steps=unresolved, exit=None

```bash
python3 - <<'PY'
import json, os, re, shutil, sys
from pathlib import Path

input_root = Path("runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset")
out = Path("runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/gpt55/without/repeat_2")
cfg_out = out / "configs"
dl_out = out / "datalists"
ckpt_out = out / "checkpoints"
tb_out = out / "tensorboard"
summary_path = out / "preflight_summary.json"

for d in (out, cfg_out, dl_out, ckpt_out, tb_out):
    d.mkdir(parents=True, exist_ok=True)

def write_summary(status, **kwargs):
    payload = {
        "status": status,
        "workflow": "nv_generate_vae_finetune",
        "model_variant": "MAISI VAE finetuning preflight; real training would use autoencoder_v1.pt",
        "preflight_only": True,
        "input_dataset": str(input_root),
        "output_dir": str(out),
        **kwargs,
    }
    summary_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

def die(message, **kwargs):
    write_summary("failed", error=message, **kwargs)
    raise SystemExit(message)

if not input_root.is_dir():
    die("input dataset directory does not exist")

required_cfgs = [
    Path("configs/config_network_rflow.json"),
    Path("configs/environment_maisi_vae_train.json"),
    Path("configs/config_maisi_vae_train.json"),
]

roots = []
if os.environ.get("NV_GENERATE_ROOT"):
    roots.append(Path(os.environ["NV_GENERATE_ROOT"]))
roots.extend([Path("NV-Generate-CTMR"), Path(".workbench_data/upstreams/NV-Generate-CTMR")])
up = Path(".workbench_data/upstreams")
if up.is_dir():
    roots.extend(sorted([p for p in up.iterdir() if p.is_dir()]))
    roots.extend(sorted({p.parent.parent for p in up.rglob("configs/config_maisi_vae_train.json")}))

seen, unique_roots = set(), []
for r in roots:
    key = str(r)
    if key not in seen:
        seen.add(key)
        unique_roots.append(r)

src_root = None
for r in unique_roots:
    if all((r / f).is_file() for f in required_cfgs):
        src_root = r
        break
if src_root is None:
    die("could not locate required upstream VAE config files", required_configs=[str(p) for p in required_cfgs])

def load_json(p):
    with p.open() as f:
        return json.load(f)

def is_candidate_datalist(obj):
    if not isinstance(obj, dict) or not isinstance(obj.get("training"), list) or not obj.get("training"):
        return False
    val_key = "validation" if isinstance(obj.get("validation"), list) and obj.get("validation") else "testing" if isinstance(obj.get("testing"), list) and obj.get("testing") else None
    if val_key is None:
        return False
    return all(isinstance(e, dict) and "image" in e for e in obj["training"] + obj[val_key])

json_files = sorted(input_root.rglob("*.json"), key=lambda p: (len(p.relative_to(input_root).parts), p.name))
candidates = []
for p in json_files:
    try:
        obj = load_json(p)
    except Exception:
        continue
    if is_candidate_datalist(obj):
        name_score = 0 if p.name in {"dataset.json", "datalist.json", "data.json"} else 1
        candidates.append((name_score, len(p.relative_to(input_root).parts), str(p), p, obj))
if not candidates:
    die("no MONAI-style datalist with non-empty training and validation/testing splits was found under the input dataset")
candidates.sort()
_, _, _, datalist_path, datalist = candidates[0]
val_split = "validation" if isinstance(datalist.get("validation"), list) and datalist.get("validation") else "testing"

ct_aliases = {"ct", "computed_tomography", "computed tomography"}
mri_aliases = {"mri", "mr", "magnetic_resonance", "magnetic resonance", "t1", "t1w", "t2", "t2w", "flair", "dwi", "adc", "pd", "swi"}

def normalize_class(x):
    s = str(x).strip().lower().replace("-", "_")
    if s in ct_aliases:
        return "ct"
    if s in mri_aliases or s.startswith("mr_") or s.startswith("mri_"):
        return "mri"
    return None

errors, normalized, class_counts, original_labels, zero_byte_images = [], {"training": [], "validation": []}, {"ct": 0, "mri": 0}, {}, []
for src_split, dst_split in [("training", "training"), (val_split, "validation")]:
    for i, entry in enumerate(datalist[src_split]):
        img = entry.get("image")
        if not isinstance(img, str) or not img:
            errors.append(f"{src_split}[{i}] image must be a non-empty relative string")
            continue
        rel = Path(img)
        if rel.is_absolute() or ".." in rel.parts:
            errors.append(f"{src_split}[{i}] image path is not safely relative: {img}")
            continue
        f = input_root / rel
        if not f.exists():
            errors.append(f"{src_split}[{i}] image path does not exist under input dataset: {img}")
            continue
        if f.is_file() and f.stat().st_size == 0:
            zero_byte_images.append(img)
        label = entry.get("class")
        norm = normalize_class(label)
        if norm not in {"ct", "mri"}:
            errors.append(f"{src_split}[{i}] class label must normalize to ct or mri: {label!r}")
            continue
        original_labels.setdefault(str(label), norm)
        class_counts[norm] += 1
        staged_entry = dict(entry)
        staged_entry["class"] = norm
        normalized[dst_split].append(staged_entry)

if errors:
    die("preflight validation failed", source_datalist=str(datalist_path), validation_errors=errors)

staged_datalist = dl_out / "dataset_preflight.json"
staged_datalist.write_text(json.dumps(normalized, indent=2, sort_keys=True) + "\n")

DATA_LIST_KEYS = {"json_data_list", "datalist", "datalist_json", "data_list_file_path", "data_list", "dataset_json"}
DATA_ROOT_KEYS = {"data_base_dir", "data_root", "data_dir", "dataset_root", "root_dir"}
OUTPUT_DIR_KEYS = {"output_dir", "output_path", "model_dir", "ckpt_dir", "checkpoint_dir", "checkpoints_dir", "save_dir"}
LOG_KEYS = {"tfevent_path", "log_dir", "logdir", "tensorboard_log_dir", "tensorboard_dir"}

def rewrite_config(obj):
    if isinstance(obj, dict):
        out_obj = {}
        for k, v in obj.items():
            lk = k.lower()
            if isinstance(v, str):
                if lk in DATA_LIST_KEYS or ("json" in lk and "list" in lk):
                    out_obj[k] = str(staged_datalist)
                elif lk in DATA_ROOT_KEYS:
                    out_obj[k] = str(input_root)
                elif lk == "trained_autoencoder_path":
                    out_obj[k] = str(ckpt_out / "autoencoder_v1.pt")
                elif lk in LOG_KEYS or "tensorboard" in lk or "tfevent" in lk:
                    out_obj[k] = str(tb_out)
                elif lk in OUTPUT_DIR_KEYS or ("checkpoint" in lk and "path" not in lk):
                    out_obj[k] = str(ckpt_out if "ckpt" in lk or "checkpoint" in lk or lk == "model_dir" else out)
                elif ("output" in lk or "save" in lk) and ("path" in lk or "dir" in lk):
                    out_obj[k] = str(out)
                else:
                    out_obj[k] = rewrite_config(v)
            else:
                out_obj[k] = rewrite_config(v)
        return out_obj
    if isinstance(obj, list):
        return [rewrite_config(x) for x in obj]
    return obj

staged_configs = []
for rel in required_cfgs:
    src = src_root / rel
    dst = cfg_out / rel.name
    cfg = load_json(src)
    cfg = rewrite_config(cfg)
    if rel.name == "environment_maisi_vae_train.json" and isinstance(cfg, dict):
        cfg.update({
            "data_base_dir": str(input_root),
            "json_data_list": str(staged_datalist),
            "model_dir": str(ckpt_out),
            "tfevent_path": str(tb_out),
            "output_dir": str(out),
            "trained_autoencoder_path": str(ckpt_out / "autoencoder_v1.pt"),
        })
    dst.write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n")
    staged_configs.append({"source": str(src), "staged": str(dst)})

write_summary(
    "passed",
    source_config_root=str(src_root),
    source_datalist=str(datalist_path),
    source_validation_split=val_split,
    staged_datalist=str(staged_datalist),
    staged_configs=staged_configs,
    split_counts={k: len(v) for k, v in normalized.items()},
    normalized_class_counts=class_counts,
    original_label_normalization=original_labels,
    zero_byte_existing_images=zero_byte_images,
    output_locations={
        "configs": str(cfg_out),
        "datalists": str(dl_out),
        "checkpoints": str(ckpt_out),
        "tensorboard": str(tb_out),
        "summary": str(summary_path),
    },
    checks=[
        "non-empty training split",
        "non-empty validation/testing split",
        "relative image paths exist under input dataset",
        "class labels normalize to ct or mri",
        "runtime configs staged under requested output directory",
        "no training or checkpoint download performed",
    ],
)
PY
```

Repeat 3: score 3/5, passed=no, steps=unresolved, exit=None

```bash
mkdir -p runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/gpt55/without/repeat_3 && python - <<'PY'
import json, os, shutil, sys
from pathlib import Path

inp = Path("runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset")
out = Path("runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/gpt55/without/repeat_3")
cfg_out = out / "configs"
dl_out = out / "datalists"
ckpt_out = out / "checkpoints"
tb_out = out / "tensorboard"
summary_path = out / "preflight_summary.json"
for p in (cfg_out, dl_out, ckpt_out, tb_out):
    p.mkdir(parents=True, exist_ok=True)

summary = {
    "workflow": "nv_generate_vae_finetune",
    "mode": "preflight_only_no_training",
    "input_dataset": str(inp),
    "output_dir": str(out),
    "model_variant": "MAISI VAE autoencoder",
    "expected_modalities": ["ct", "mri"],
    "status": "failed",
    "errors": [],
    "warnings": [],
    "staged_files": [],
}

def fail(msg):
    summary["errors"].append(msg)

try:
    if not inp.is_dir():
        fail(f"input dataset directory not found: {inp}")

    candidates = []
    if inp.exists():
        for j in sorted(inp.rglob("*.json")):
            try:
                obj = json.loads(j.read_text())
            except Exception:
                continue
            if isinstance(obj, dict) and isinstance(obj.get("training"), list) and (isinstance(obj.get("validation"), list) or isinstance(obj.get("testing"), list)):
                candidates.append((j, obj))
    if not candidates:
        fail("no MONAI-style datalist JSON with training and validation/testing splits was found under the input dataset")
        datalist_path, datalist = None, None
    else:
        datalist_path, datalist = candidates[0]
        if len(candidates) > 1:
            summary["warnings"].append("multiple candidate datalists found; using " + str(datalist_path))
        staged_datalist = dl_out / datalist_path.name
        shutil.copy2(datalist_path, staged_datalist)
        summary["datalist"] = str(datalist_path)
        summary["staged_files"].append(str(staged_datalist))

        train = datalist.get("training") or []
        val_key = "validation" if isinstance(datalist.get("validation"), list) else "testing"
        val = datalist.get(val_key) or []
        if not train:
            fail("training split is empty")
        if not val:
            fail(f"{val_key} split is empty")

        def norm_mod(x):
            s = str(x or "").strip().lower().replace("-", "_").replace(" ", "_")
            if s == "ct" or s.endswith("_ct") or s.startswith("ct_"):
                return "ct"
            if s in {"mri", "mr", "t1", "t1w", "t1ce", "t1c", "t2", "t2w", "flair", "dwi", "adc", "pd"} or s.startswith("mr_") or s.startswith("mri_"):
                return "mri"
            return None

        counts = {"training": len(train), val_key: len(val)}
        normalized = {"ct": 0, "mri": 0}
        checked = []
        for split_name, rows in (("training", train), (val_key, val)):
            for i, row in enumerate(rows):
                if not isinstance(row, dict):
                    fail(f"{split_name}[{i}] is not an object")
                    continue
                img = row.get("image")
                if not isinstance(img, str) or not img:
                    fail(f"{split_name}[{i}] missing non-empty image field")
                    continue
                img_path = Path(img)
                if img_path.is_absolute():
                    fail(f"{split_name}[{i}] image path must be relative, got absolute path: {img}")
                    resolved = img_path
                else:
                    resolved = inp / img_path
                if not resolved.exists():
                    fail(f"{split_name}[{i}] image does not exist under data root: {resolved}")
                elif resolved.is_file() and resolved.stat().st_size == 0:
                    summary["warnings"].append(f"{split_name}[{i}] image is zero bytes, treated as placeholder/preflight-only: {resolved}")
                mod = norm_mod(row.get("class"))
                if mod is None:
                    fail(f"{split_name}[{i}] class label does not normalize to ct or mri: {row.get('class')!r}")
                else:
                    normalized[mod] += 1
                checked.append({"split": split_name, "image": img, "class": row.get("class"), "normalized_class": mod, "exists": resolved.exists()})
        summary["split_counts"] = counts
        summary["normalized_modality_counts"] = normalized
        summary["checked_items"] = checked

    root_env = os.environ.get("NV_GENERATE_ROOT")
    upstream_root = Path(root_env) if root_env else Path(".workbench_data/upstreams/NV-Generate-CTMR")
    summary["upstream_root_read_only"] = str(upstream_root)
    required = [
        "configs/config_network_rflow.json",
        "configs/environment_maisi_vae_train.json",
        "configs/config_maisi_vae_train.json",
    ]
    for rel in required:
        src = upstream_root / rel
        dst = cfg_out / Path(rel).name
        if not src.is_file():
            fail(f"required upstream config not found for staging: {src}")
            continue
        data = json.loads(src.read_text())
        def rewrite(obj):
            if isinstance(obj, dict):
                new = {}
                for k, v in obj.items():
                    lk = k.lower()
                    if isinstance(v, str) and any(tok in lk for tok in ["output", "log", "checkpoint", "ckpt", "model_dir", "save", "tensorboard"]):
                        if "tensorboard" in lk or "log" in lk:
                            new[k] = str(tb_out)
                        elif "checkpoint" in lk or "ckpt" in lk or "model" in lk:
                            new[k] = str(ckpt_out)
                        else:
                            new[k] = str(out)
                    else:
                        new[k] = rewrite(v)
                return new
            if isinstance(obj, list):
                return [rewrite(x) for x in obj]
            return obj
        staged = rewrite(data)
        staged["_medical_ai_skills_preflight_overrides"] = {
            "mode": "preflight_only_no_training",
            "data_root": str(inp),
            "datalist": str(dl_out / datalist_path.name) if candidates else None,
            "output_dir": str(out),
            "checkpoint_dir": str(ckpt_out),
            "tensorboard_log_dir": str(tb_out),
            "note": "runtime artifact paths are staged under the requested output directory; upstream files were read only",
        }
        dst.write_text(json.dumps(staged, indent=2, sort_keys=True) + "\n")
        summary["staged_files"].append(str(dst))

    runtime_manifest = out / "preflight_runtime_manifest.json"
    runtime_manifest.write_text(json.dumps({
        "command_intent": "validate datalist, normalize ct/mri labels, stage VAE finetuning configs, and stop before training",
        "runnable_training_command": None,
        "reason_training_not_run": "preflight-scale check only; placeholder inputs must not be trained on",
        "staged_config_dir": str(cfg_out),
        "checkpoint_dir": str(ckpt_out),
        "tensorboard_log_dir": str(tb_out),
    }, indent=2, sort_keys=True) + "\n")
    summary["staged_files"].append(str(runtime_manifest))

    summary["status"] = "ok" if not summary["errors"] else "failed"
finally:
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

if summary["errors"]:
    print("Preflight failed; see", summary_path, file=sys.stderr)
    sys.exit(1)
print("Preflight OK; summary written to", summary_path)
PY
```

### Opus 4.7, with arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python skills/nv-generate-vae-finetune/scripts/run_vae_finetune.py runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_datalist.json --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_dataset --output-dir runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/opus/with/repeat_1 --modality mri --preflight
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python skills/nv-generate-vae-finetune/scripts/run_vae_finetune.py runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_datalist.json --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_dataset --output-dir runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/opus/with/repeat_2 --modality mri --preflight
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python skills/nv-generate-vae-finetune/scripts/run_vae_finetune.py runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_datalist.json --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_dataset --output-dir runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/opus/with/repeat_3 --modality mri --preflight
```

### Opus 4.7, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 3/5, passed=no, steps=unresolved, exit=None

```bash
IN=runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset && OUT=runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/opus/without/repeat_1 && mkdir -p "$OUT/configs" && DATALIST=$(find "$IN" -maxdepth 3 -type f \( -name 'datalist*.json' -o -name '*datalist.json' -o -name '*.json' \) | head -n1) && DATA_ROOT=$(dirname "$DATALIST") && UP=$(find .workbench_data/upstreams -type d -name 'NV-Generate-CTMR*' 2>/dev/null | head -n1) && for f in config_network_rflow.json environment_maisi_vae_train.json config_maisi_vae_train.json; do SRC=$(find "$UP" -type f -name "$f" 2>/dev/null | head -n1); [ -n "$SRC" ] && cp "$SRC" "$OUT/configs/$f"; done && cp "$DATALIST" "$OUT/configs/datalist_staged.json" && python3 -c "
import json, os, sys
dl=json.load(open('$DATALIST'))
root='$DATA_ROOT'
out='$OUT'
train=dl.get('training',[])
val=dl.get('validation') or dl.get('testing') or []
issues=[]
if not train: issues.append('empty training split')
if not val: issues.append('empty validation/testing split')
def check(entries,label):
    res=[]
    for e in entries:
        img=e.get('image','')
        cls=(e.get('class') or '').lower()
        norm='mri' if cls.startswith('mr') else ('ct' if cls=='ct' else cls)
        p=os.path.join(root,img)
        res.append({'image':img,'class':cls,'normalized':norm,'exists':os.path.exists(p),'class_ok':norm in ('ct','mri')})
    return res
tr=check(train,'training'); va=check(val,'validation')
for r in tr+va:
    if not r['exists']: issues.append('missing: '+r['image'])
    if not r['class_ok']: issues.append('bad class: '+r['image']+' -> '+r['class'])
staged_cfgs=sorted(os.listdir(os.path.join(out,'configs')))
summary={'mode':'preflight','datalist':'$DATALIST','data_root':root,'n_training':len(train),'n_validation':len(val),'training_entries':tr,'validation_entries':va,'staged_configs':staged_cfgs,'staged_configs_dir':os.path.join(out,'configs'),'issues':issues,'preflight_ok':len(issues)==0,'scope':'engineering plumbing only; no clinical claims'}
json.dump(summary,open(os.path.join(out,'preflight_summary.json'),'w'),indent=2)
print(json.dumps({'preflight_ok':summary['preflight_ok'],'issues':issues,'n_training':len(train),'n_validation':len(val)},indent=2))
"
```

Repeat 2: score 3/5, passed=no, steps=unresolved, exit=None

```bash
set -euo pipefail && IN=runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset && OUT=runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/opus/without/repeat_2 && mkdir -p "$OUT/configs" "$OUT/logs" && UP=$(find .workbench_data/upstreams -type d -name 'NV-Generate-CTMR*' -print -quit 2>/dev/null || true) && [ -n "${UP:-}" ] && [ -d "$UP" ] && echo "Upstream: $UP" && DL=$(find "$IN" -maxdepth 3 -type f \( -name 'datalist*.json' -o -name '*datalist.json' -o -name 'dataset*.json' \) | head -n1) && [ -n "$DL" ] && echo "Datalist: $DL" && DR=$(dirname "$DL") && [ -f "$IN/data_root" ] && DR=$(cat "$IN/data_root") || true && for f in config_network_rflow.json environment_maisi_vae_train.json config_maisi_vae_train.json; do cp "$UP/configs/$f" "$OUT/configs/$f"; done && python - <<PY
import json, os, sys
dl_path = "$DL"
in_dir = "$IN"
out_dir = "$OUT"
data_root = "$DR" if os.path.isdir("$DR") else in_dir
with open(dl_path) as f:
    dl = json.load(f)
train = dl.get("training", [])
val = dl.get("validation", dl.get("testing", []))
errors, missing, classes = [], [], set()
if not train: errors.append("empty training split")
if not val: errors.append("empty validation/testing split")
def check(entries, split):
    for e in entries:
        img = e.get("image","")
        cls = (e.get("class","") or "").lower()
        if cls in ("ct",): classes.add("ct")
        elif cls in ("mri","mr","t1","t2","flair","t1ce","dwi"): classes.add("mri")
        else: errors.append(f"{split}: bad class '{cls}' for {img}")
        p = img if os.path.isabs(img) else os.path.join(data_root, img)
        if not os.path.exists(p): missing.append(p)
check(train,"training"); check(val,"validation")
summary = {
    "datalist": dl_path, "data_root": data_root,
    "train_count": len(train), "val_count": len(val),
    "modalities": sorted(classes), "missing_images": missing[:20],
    "missing_count": len(missing), "errors": errors,
    "staged_configs": sorted(os.listdir(os.path.join(out_dir,"configs"))),
    "preflight_ok": (not errors) and (len(missing)==0),
    "scope": "preflight staging only; no training, no clinical claims",
}
with open(os.path.join(out_dir,"preflight_summary.json"),"w") as f:
    json.dump(summary, f, indent=2)
print(json.dumps(summary, indent=2))
PY
```

Repeat 3: score 3/5, passed=no, steps=unresolved, exit=None

```bash
OUT=runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/opus/without/repeat_3 && IN=runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset && mkdir -p "$OUT/configs" && UPSTREAM=$(find .workbench_data/upstreams -type d -name 'NV-Generate-CTMR*' 2>/dev/null | head -n1) && [ -z "$UPSTREAM" ] && UPSTREAM="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" ; for f in config_network_rflow.json environment_maisi_vae_train.json config_maisi_vae_train.json; do if [ -f "$UPSTREAM/configs/$f" ]; then cp "$UPSTREAM/configs/$f" "$OUT/configs/$f"; else echo "{\"_missing\": \"$f\"}" > "$OUT/configs/$f"; fi; done && python3 -c "
import json, os, sys
inp = os.environ['IN']; out = os.environ['OUT']
summary = {'input_dir': inp, 'output_dir': out, 'checks': {}, 'status': 'unknown'}
errors = []
# Locate datalist
datalist_path = None
for cand in ['datalist.json','dataset.json','data.json']:
    p = os.path.join(inp, cand)
    if os.path.isfile(p): datalist_path = p; break
if datalist_path is None:
    for root,_,files in os.walk(inp):
        for f in files:
            if f.endswith('.json'): datalist_path = os.path.join(root,f); break
        if datalist_path: break
summary['datalist'] = datalist_path
if not datalist_path:
    errors.append('no datalist json found')
else:
    with open(datalist_path) as fh: dl = json.load(fh)
    train = dl.get('training', [])
    val = dl.get('validation') or dl.get('testing') or []
    summary['checks']['n_training'] = len(train)
    summary['checks']['n_validation'] = len(val)
    if not train: errors.append('empty training split')
    if not val: errors.append('empty validation/testing split')
    data_root = inp
    missing = []; classes = {}
    for entry in list(train)+list(val):
        img = entry.get('image'); cls = (entry.get('class') or '').lower()
        norm = 'mri' if cls and cls != 'ct' else ('ct' if cls=='ct' else 'unknown')
        classes[norm] = classes.get(norm,0)+1
        if img:
            ap = img if os.path.isabs(img) else os.path.join(data_root, img)
            if not os.path.exists(ap): missing.append(img)
    summary['checks']['classes'] = classes
    summary['checks']['missing_images'] = missing[:10]
    summary['checks']['n_missing'] = len(missing)
    if missing: errors.append(f'{len(missing)} image paths missing')
    if any(k=='unknown' for k in classes): errors.append('non ct/mri classes present')
# Staged configs
staged = sorted(os.listdir(os.path.join(out,'configs')))
summary['staged_configs'] = [os.path.join(out,'configs',f) for f in staged]
summary['errors'] = errors
summary['status'] = 'ok' if not errors else 'failed'
summary['scope'] = 'preflight workflow plumbing only; no training executed'
os.makedirs(out, exist_ok=True)
with open(os.path.join(out,'preflight_summary.json'),'w') as fh: json.dump(summary, fh, indent=2)
print(json.dumps(summary, indent=2))
"
```

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `runs/with_vs_without_nv/studies/nv_generate_vae_finetune_codex_opus/` |
| Generated outputs | `runs/with_vs_without_nv/nv_generate_vae_finetune_codex_opus/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_generate_vae_finetune_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
