# `nv_segment_ct_finetune`: Codex/Opus LLM+SKILL.md vs LLM+README

Status: strict audit passed for refreshed artifacts on May 27, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

This report compares `LLM + SKILL.md` with `LLM + upstream README/guide`. The completed direct-API run used the corrected embedded-doc minimal prompt because those backends cannot read repo files. The fair NAT/tool-agent prompt artifact is A2-style: it gives a natural user request, a neutral staged input path, an output directory, and tells the agent which arm-specific document to read. It does not spell out operational details such as entrypoints, labels, model variants, or config filenames outside the documentation arm.

## Experiment Question

Does `LLM + SKILL.md` make an agent better at reading documentation and taking the right action than `LLM + upstream README/guide`?

## User Request Shape

The prompt request for the GPT-5.5 with-skill arm was:

> Fine-tune the CT segmentation workflow on the small dataset at runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset. Use the shortest smoke-scale run suitable for checking the workflow, and write outputs under runs/with_vs_without_nv/nv_segment_ct_finetune_codex_opus/gpt55/with/repeat_1.

The staged user input for every arm was `runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset`. The source fixture `skills/nv-segment-ct-finetune/fixtures/spleen_micro` was used only to stage that neutral input path.

Fair path-prompt artifact: `tools/nat_audit/data/eval_nv_model_studies_nv_segment_ct_finetune_prompts.json`

## Result

| Backend | Arm | Mean score | Passes | Steps | Exit | Tier 5 | Failed tiers |
|---|---|---:|---:|---|---|---|---|
| GPT-5.5 / Codex | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | checkpoint reported (3) | none |
| GPT-5.5 / Codex | without | 4.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | None (3) | blocked unsafe command fragment: rm (3) | T5: blocked unsafe command fragment: rm (3) |
| Opus 4.7 | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | checkpoint reported (3) | none |
| Opus 4.7 | without | 3.7/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | 1 (2); None (1) | exit 1 (2); command does not reference the expected output directory (1) | T5: exit 1 (2); T4: output dir marker (1); T5: command does not reference the expected output directory (1) |

## Analysis

SKILL.md paired advantage: the with-skill arms passed 6/6 backend-repeat trials with an average score of 5.0/5; the README-only arms passed 0/6 backend-repeat trials with an average score of 3.8/5.

SKILL.md paired advantage: SKILL.md wins 6/6 matched backend-repeat pairs, README-only wins 0/6, and 0/6 are ties. Pass/fail is the primary outcome; score breaks ties only when pass status is equal. Exact one-sided sign-test p=0.01562 across 6 decisive pair(s).

Outcome-support gate: Supports SKILL.md advantage. SKILL.md wins 6/6 matched pair(s); README-only wins 0/6; sign-test p=0.01562.

Each backend/arm/skill configuration was repeated three times. A repeat is independent: it has its own output directory, and each execution attempt inside the repeat creates a fresh venv before running the generated command. Dependency and model download caches are shared only as documented test-environment caches under `.workbench_data/with_vs_without_cache` (`PIP_CACHE_DIR=.workbench_data/with_vs_without_cache/pip`, `HF_HOME=.workbench_data/with_vs_without_cache/huggingface`, `HF_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `HUGGINGFACE_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `TRANSFORMERS_CACHE=.workbench_data/with_vs_without_cache/huggingface/transformers`, `TORCH_HOME=.workbench_data/with_vs_without_cache/torch`, `XDG_CACHE_HOME=.workbench_data/with_vs_without_cache/xdg`, `CONDA_PKGS_DIRS=.workbench_data/with_vs_without_cache/conda_pkgs`, `UV_CACHE_DIR=.workbench_data/with_vs_without_cache/uv`, `CUDA_CACHE_PATH=.workbench_data/with_vs_without_cache/cuda`, `NUMBA_CACHE_DIR=.workbench_data/with_vs_without_cache/numba`).

The main baseline uses `max_correction_steps=0`: each repeat sends one prompt, executes the extracted command once, and records pass/fail, runtime, tokens, and deterministic failure analysis. The repair-loop implementation remains available for separate diagnostic experiments, but it is not part of this comparison.

All with-skill repeats exited successfully and produced artifacts accepted by the deterministic grader. That means the final SKILL.md surface was repeatable for both tested agent backends.

The README-only commands did not pass tier 5. Typical failure modes were unsafe generated shell cleanup, missing schema fields, missing model/control details, or upstream commands that did not execute cleanly from Medical AI Skills root.

Tier 2 is intentionally strict: a command only earns it if it uses the staged user input path `runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset`.

## Token Profiling

Token counts are provider-reported values saved in each repeat JSON. Reasoning tokens are shown only when the provider returned that subfield and are a subset of completion tokens, not an additional cost to add to total tokens. Execution time is averaged only across repeats that reached command execution; no-command-extracted repeats still count toward token totals.

| Backend | Arm | Repeats | Passes | Attempts | Prompt tokens | Completion tokens | Reasoning tokens | Total tokens | Mean total/repeat | Executed | Mean exec s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GPT-5.5 / Codex | with | 3 | 3 | 3 | 7,566 | 1,271 | 884 | 8,837 | 2,945.7 | 3 | 59.0 |
| GPT-5.5 / Codex | without | 3 | 0 | 3 | 9,213 | 21,971 | 17,680 | 31,184 | 10,394.7 | 0 | n/a |
| Opus 4.7 | with | 3 | 3 | 3 | 12,720 | 591 | 0 | 13,311 | 4,437.0 | 3 | 63.3 |
| Opus 4.7 | without | 3 | 0 | 3 | 13,662 | 2,707 | 0 | 16,369 | 5,456.3 | 2 | 0.0 |

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
| 3 | 0 | 3/5 | no | None | T4: output dir marker; T5: command does not reference the expected output directory | tier_4: output dir marker Repair: Write outputs under the exact arm-specific output directory.<br>tier_5: command does not reference the expected output directory Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference the expected output directory Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |

## Skill Fix Notes

Before the final rerun, `SKILL.md` was tightened to name `scripts/run_finetune.py` as the smoke-scale finetune surface and to require the user's staged dataset path.

## Generated Commands

These are the extracted first-attempt commands by repeat.

### GPT-5.5 / Codex, with arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
python -m pip install "monai==1.4.0" "numpy<2" pytorch-ignite einops nibabel scipy typer PyYAML fire huggingface_hub && python skills/nv-segment-ct-finetune/scripts/run_finetune.py runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset --smoke --patch-size '[64,64,64]' --output-dir runs/with_vs_without_nv/nv_segment_ct_finetune_codex_opus/gpt55/with/repeat_1
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
python -m pip install "monai==1.4.0" "numpy<2" pytorch-ignite einops nibabel scipy typer PyYAML fire huggingface_hub && python skills/nv-segment-ct-finetune/scripts/run_finetune.py runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset --smoke --patch-size '[64,64,64]' --output-dir runs/with_vs_without_nv/nv_segment_ct_finetune_codex_opus/gpt55/with/repeat_2
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
python -m pip install "monai==1.4.0" "numpy<2" pytorch-ignite einops nibabel scipy typer PyYAML fire huggingface_hub && python skills/nv-segment-ct-finetune/scripts/run_finetune.py runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset --smoke --patch-size '[64,64,64]' --output-dir runs/with_vs_without_nv/nv_segment_ct_finetune_codex_opus/gpt55/with/repeat_3
```

### GPT-5.5 / Codex, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 4/5, passed=no, steps=unresolved, exit=None

```bash
OUT="runs/with_vs_without_nv/nv_segment_ct_finetune_codex_opus/gpt55/without/repeat_1" && DATA="runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset" && BUNDLE="$OUT/bundle" && ABS_OUT="$(pwd)/$OUT" && ABS_DATA="$(pwd)/$DATA" && rm -rf "$OUT" && mkdir -p "$BUNDLE" "$OUT/configs" "$OUT/.cache" && export OUT DATA BUNDLE ABS_OUT ABS_DATA MPLCONFIGDIR="$ABS_OUT/.cache/matplotlib" XDG_CACHE_HOME="$ABS_OUT/.cache" TORCH_HOME="$ABS_OUT/.cache/torch" CUDA_CACHE_PATH="$ABS_OUT/.cache/cuda" && cp -aL "${NV_SEGMENT_CTMR_ROOT:?NV_SEGMENT_CTMR_ROOT must point to the NV-Segment-CT bundle root}/." "$BUNDLE" && python - <<'PY' && (cd "$BUNDLE" && python -m monai.bundle run --config_file="['configs/train.json','configs/train_continual.json','../configs/smoke_continual.json']")
from pathlib import Path
import json, os, re

data = Path(os.environ["ABS_DATA"])
out = Path(os.environ["ABS_OUT"])
cfg_dir = out / "configs"
cfg_dir.mkdir(parents=True, exist_ok=True)

def is_nii(p):
    n = p.name.lower()
    return n.endswith(".nii") or n.endswith(".nii.gz")

files = sorted(p for p in data.rglob("*") if p.is_file() and is_nii(p))
if not files:
    raise SystemExit(f"No NIfTI files found under {data}")

def looks_like_label(p):
    text = "/".join(part.lower() for part in p.relative_to(data).parts)
    return any(tok in text for tok in ("label", "labels", "labelstr", "seg", "mask"))

labels = sorted(p for p in files if looks_like_label(p))
images = sorted(p for p in files if p not in labels)
if not labels or not images:
    raise SystemExit(f"Could not infer image/label pairs under {data}; found {len(images)} images and {len(labels)} labels")

def strip_nii(name):
    name = name.lower()
    return name[:-7] if name.endswith(".nii.gz") else name[:-4] if name.endswith(".nii") else name

def key(p):
    s = strip_nii(p.name)
    s = re.sub(r"^(image|images|img|ct|label|labels|segmentation|seg|mask)[_\-\s]*", "", s)
    s = re.sub(r"[_\-\s]*(image|images|img|ct|label|labels|segmentation|seg|mask)$", "", s)
    return re.sub(r"[^a-z0-9]+", "", s)

image_keys = {}
for im in images:
    image_keys.setdefault(key(im), []).append(im)

pairs = []
used = set()
for lab in labels:
    lk = key(lab)
    candidates = image_keys.get(lk, [])
    if not candidates:
        candidates = [im for im in images if key(im) and (key(im) in lk or lk in key(im))]
    candidates = [im for im in candidates if im not in used]
    if candidates:
        im = candidates[0]
        used.add(im)
        pairs.append((im, lab))

if not pairs and len(images) == len(labels):
    pairs = list(zip(images, labels))
if not pairs:
    raise SystemExit("Could not pair images with labels")

records = [
    {"image": str(im.relative_to(data)), "label": str(lab.relative_to(data)), "fold": 0 if i == 0 else 1}
    for i, (im, lab) in enumerate(pairs)
]
if len(records) == 1:
    records = [dict(records[0], fold=0), dict(records[0], fold=1)]

datalist_path = cfg_dir / "dataset_folds.json"
datalist_path.write_text(json.dumps({"training": records}, indent=2) + "\n")

label_mappings = [[1, 3]]
try:
    import nibabel as nib
    import numpy as np
    vals = set()
    for _, lab in pairs[: min(3, len(pairs))]:
        arr = np.asanyarray(nib.load(str(lab)).dataobj)
        vals.update(int(v) for v in np.unique(arr) if float(v).is_integer() and 0 < int(v) < 255)
    if vals and vals != {1}:
        label_mappings = [[v, v] for v in sorted(vals)]
except Exception:
    pass

smoke_config = {
    "data_list_file_path": str(datalist_path),
    "dataset_dir": str(data),
    "label_mappings": {"default": label_mappings},
    "val_at_start": False,
    "max_epochs": 1,
    "val_interval": 1,
    "validate_interval": 1,
    "n_train_samples": 1,
    "n_val_samples": 1,
    "patch_size": [64, 64, 64],
    "train_dataset_cache_rate": 0.0,
    "val_dataset_cache_rate": 0.0,
    "num_workers": 0,
    "train_num_workers": 0,
    "val_num_workers": 0,
    "drop_point_prob": 1.0,
    "drop_label_prob": 0.0
}
(cfg_dir / "smoke_continual.json").write_text(json.dumps(smoke_config, indent=2) + "\n")
PY
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=None

```bash
set -euo pipefail && OUT="runs/with_vs_without_nv/nv_segment_ct_finetune_codex_opus/gpt55/without/repeat_2" && DATA="runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset" && SRC="${NV_SEGMENT_CTMR_ROOT:?NV_SEGMENT_CTMR_ROOT must point to the NV-Segment-CT bundle root}" && export OUT DATA SRC && rm -rf "$OUT" && mkdir -p "$OUT" && python - <<'PY' && (cd "$OUT/bundle" && MLFLOW_TRACKING_URI="file:$(pwd)/mlruns" PYTHONUNBUFFERED=1 python -m monai.bundle run --config_file="['configs/train.json','configs/train_continual.json','configs/smoke_runtime.json']")
import json, os, shutil
from pathlib import Path

out = Path(os.environ["OUT"]).resolve()
data = Path(os.environ["DATA"]).resolve()
src = Path(os.environ["SRC"]).resolve()
bundle = out / "bundle"

if not (src / "configs" / "train.json").is_file() or not (src / "configs" / "train_continual.json").is_file():
    raise FileNotFoundError(f"Expected configs/train.json and configs/train_continual.json under {src}")
if not data.is_dir():
    raise FileNotFoundError(f"Input dataset directory not found: {data}")

shutil.copytree(
    src,
    bundle,
    symlinks=False,
    ignore=shutil.ignore_patterns(".git", "mlruns", "__pycache__", "*.pyc"),
    dirs_exist_ok=True,
)

def nii_stem(p: Path) -> str:
    name = p.name
    if name.endswith(".nii.gz"):
        return name[:-7]
    if name.endswith(".nii"):
        return name[:-4]
    return p.stem

def norm_key(p: Path) -> str:
    s = nii_stem(p).lower()
    for token in ("label", "labels", "segmentation", "segment", "seg", "mask", "image", "images", "img"):
        s = s.replace(token, "")
    return "".join(ch for ch in s if ch.isalnum())

all_nii = sorted([p for p in data.rglob("*.nii")] + [p for p in data.rglob("*.nii.gz")])
if not all_nii:
    raise FileNotFoundError(f"No NIfTI files found under {data}")

def looks_like_label(p: Path) -> bool:
    rel = str(p.relative_to(data)).lower()
    parts = [part.lower() for part in p.relative_to(data).parts]
    return any(x in parts for x in ("labelstr", "labelsts", "labels", "label")) or any(x in rel for x in ("label", "seg", "mask"))

label_files = [p for p in all_nii if looks_like_label(p)]
image_files = [p for p in all_nii if p not in set(label_files)]
if not label_files:
    raise FileNotFoundError(f"Could not identify label NIfTI files under {data}")

image_by_key = {}
for p in image_files:
    image_by_key.setdefault(norm_key(p), p)

pairs = []
for lbl in label_files:
    candidates = []
    rel_parts = list(lbl.relative_to(data).parts)
    for old, new in (("labelsTr", "imagesTr"), ("labelsTs", "imagesTs"), ("labels", "images"), ("label", "image")):
        if old in rel_parts:
            cparts = [new if x == old else x for x in rel_parts]
            candidates.append(data.joinpath(*cparts))
    candidates.extend([data / "imagesTr" / lbl.name, data / "images" / lbl.name])
    for c in list(candidates):
        if c.name.lower().startswith("label"):
            candidates.append(c.with_name("img" + c.name[5:]))
    img = next((c for c in candidates if c.is_file()), None)
    if img is None:
        img = image_by_key.get(norm_key(lbl))
    if img is not None:
        pairs.append((img, lbl))

if not pairs:
    raise FileNotFoundError(f"Could not pair images with labels under {data}")

pairs = pairs[:2]
if len(pairs) == 1:
    pairs = [pairs[0], pairs[0]]

datalist = {
    "training": [
        {"image": str(pairs[0][0].relative_to(data)), "label": str(pairs[0][1].relative_to(data)), "fold": 0},
        {"image": str(pairs[1][0].relative_to(data)), "label": str(pairs[1][1].relative_to(data)), "fold": 1},
    ]
}
datalist_path = out / "smoke_folds.json"
datalist_path.write_text(json.dumps(datalist, indent=2) + "\n")

smoke = {
    "bundle_root": str(bundle),
    "data_list_file_path": str(datalist_path),
    "dataset_dir": str(data),
    "label_mappings": {"default": [[1, 3]]},
    "val_at_start": False,
    "n_train_samples": 1,
    "n_val_samples": 1,
    "patch_size": [64, 64, 64],
    "train_dataset_cache_rate": 0.0,
    "val_dataset_cache_rate": 0.0,
    "cache_rate": 0.0,
    "train_batch_size": 1,
    "val_batch_size": 1,
    "batch_size": 1,
    "num_epochs": 1,
    "max_epochs": 1,
    "num_iterations": 1,
    "max_iterations": 1,
    "val_interval": 1,
    "drop_point_prob": 1.0,
    "drop_label_prob": 0.0,
    "num_workers": 0,
    "train_num_workers": 0,
    "val_num_workers": 0
}
(bundle / "configs" / "smoke_runtime.json").write_text(json.dumps(smoke, indent=2) + "\n")
PY
```

Repeat 3: score 4/5, passed=no, steps=unresolved, exit=None

```bash
OUT="runs/with_vs_without_nv/nv_segment_ct_finetune_codex_opus/gpt55/without/repeat_3" && IN="runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset" && SRC="${NV_SEGMENT_CTMR_ROOT:-.workbench_data/upstreams/NV-Segment-CT}" && test -f "$SRC/configs/train.json" && test -f "$SRC/configs/train_continual.json" && mkdir -p "$OUT" && rm -rf "$OUT/runtime_bundle" && python - "$IN" "$OUT" "$SRC" <<'PY' && (cd "$OUT/runtime_bundle" && python -m monai.bundle run --config_file="['configs/train.json','configs/train_continual.json','../smoke_overrides.json']")
from pathlib import Path
from collections import defaultdict
import json, re, shutil, sys
import numpy as np
import nibabel as nib

inp = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
src = Path(sys.argv[3]).resolve()
runtime = out / "runtime_bundle"

shutil.copytree(src, runtime, ignore=shutil.ignore_patterns(".git", "mlruns", "__pycache__"), ignore_dangling_symlinks=True)
(out / "outputs").mkdir(parents=True, exist_ok=True)
(out / "checkpoints").mkdir(parents=True, exist_ok=True)

def is_nii(p):
    return p.name.endswith(".nii.gz") or p.name.endswith(".nii")

def nii_stem(name):
    return name[:-7] if name.endswith(".nii.gz") else (name[:-4] if name.endswith(".nii") else name)

def norm_key(p):
    s = nii_stem(p.name).lower()
    s = re.sub(r"(labels?|segmentations?|segs?|masks?|images?|imgs?|ct)", "", s)
    return re.sub(r"[^a-z0-9]+", "", s)

files = sorted([p for p in inp.rglob("*") if p.is_file() and is_nii(p)])
labels = []
for p in files:
    rel = "/".join(p.relative_to(inp).parts).lower()
    if any(tok in rel for tok in ("label", "seg", "mask")):
        labels.append(p)
images = [p for p in files if p not in set(labels)]

img_by_key = defaultdict(list)
for im in images:
    img_by_key[norm_key(im)].append(im)

pairs = []
for lab in labels:
    rel = lab.relative_to(inp)
    rel_s = rel.as_posix()
    candidates = []
    for a, b in [
        ("labelsTr/", "imagesTr/"), ("labelsTs/", "imagesTs/"), ("labels/", "images/"),
        ("labelTr/", "imageTr/"), ("labelTs/", "imageTs/"), ("label/", "image/"),
        ("segs/", "images/"), ("seg/", "image/"), ("masks/", "images/"), ("mask/", "image/")
    ]:
        if a in rel_s:
            candidates.append(inp / rel_s.replace(a, b, 1))
    base = lab.name
    for a, b in [("label", "image"), ("label", "img"), ("seg", "image"), ("mask", "image")]:
        if a in base.lower():
            candidates.append(lab.with_name(re.sub(a, b, base, count=1, flags=re.IGNORECASE)))
    im = next((c for c in candidates if c.exists() and c.is_file() and is_nii(c)), None)
    if im is None:
        matches = img_by_key.get(norm_key(lab), [])
        im = matches[0] if matches else None
    if im is not None:
        pairs.append((im, lab))

if not pairs:
    raise SystemExit(f"No image/label NIfTI pairs found under {inp}")

pairs = sorted(set(pairs), key=lambda x: (x[1].as_posix(), x[0].as_posix()))
smoke_pairs = pairs[:2] if len(pairs) >= 2 else [pairs[0], pairs[0]]

vals = set()
for _, lab in smoke_pairs:
    data = np.asanyarray(nib.load(str(lab)).dataobj)
    vals.update(int(v) for v in np.unique(data) if np.isfinite(v) and int(v) != 0)
if not vals:
    raise SystemExit("No nonzero label values found in the smoke labels")

used = set()
mappings = []
for v in sorted(vals):
    if 1 <= v < 255 and v not in used:
        m = v
    else:
        m = next(i for i in range(1, 255) if i not in used)
    used.add(m)
    mappings.append([v, m])

training = []
if len(smoke_pairs) == 1 or smoke_pairs[0] == smoke_pairs[1]:
    im, lab = smoke_pairs[0]
    training = [
        {"image": im.relative_to(inp).as_posix(), "label": lab.relative_to(inp).as_posix(), "fold": 1},
        {"image": im.relative_to(inp).as_posix(), "label": lab.relative_to(inp).as_posix(), "fold": 0},
    ]
else:
    for idx, (im, lab) in enumerate(smoke_pairs):
        training.append({"image": im.relative_to(inp).as_posix(), "label": lab.relative_to(inp).as_posix(), "fold": 0 if idx == 0 else 1})

datalist = {"training": training}
datalist_path = out / "smoke_datalist.json"
datalist_path.write_text(json.dumps(datalist, indent=2) + "\n")

overrides = {
    "data_list_file_path": str(datalist_path.resolve()),
    "dataset_dir": str(inp),
    "label_mappings": {"default": mappings},
    "val_at_start": False,
    "n_train_samples": 1,
    "n_val_samples": 1,
    "patch_size": [64, 64, 64],
    "train_dataset_cache_rate": 0.0,
    "val_dataset_cache_rate": 0.0,
    "max_epochs": 1,
    "num_epochs": 1,
    "val_interval": 1,
    "drop_point_prob": 1.0,
    "drop_label_prob": 0.0,
    "use_mlflow": False,
    "output_dir": str((out / "outputs").resolve()),
    "ckpt_dir": str((out / "checkpoints").resolve()),
    "train#trainer#max_epochs": 1,
    "train#trainer#val_interval": 1
}
(out / "smoke_overrides.json").write_text(json.dumps(overrides, indent=2) + "\n")
(out / "smoke_setup_summary.json").write_text(json.dumps({"input_dataset": str(inp), "source_bundle": str(src), "runtime_bundle": str(runtime), "label_mappings": mappings, "datalist": datalist}, indent=2) + "\n")
PY
```

### Opus 4.7, with arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
python -m pip install "monai==1.4.0" "numpy<2" pytorch-ignite einops nibabel scipy typer PyYAML fire huggingface_hub && python skills/nv-segment-ct-finetune/scripts/run_finetune.py runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset --smoke --patch-size '[64,64,64]' --output-dir runs/with_vs_without_nv/nv_segment_ct_finetune_codex_opus/opus/with/repeat_1
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
python -m pip install "monai==1.4.0" "numpy<2" pytorch-ignite einops nibabel scipy typer PyYAML fire huggingface_hub && python skills/nv-segment-ct-finetune/scripts/run_finetune.py runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset --smoke --patch-size '[64,64,64]' --output-dir runs/with_vs_without_nv/nv_segment_ct_finetune_codex_opus/opus/with/repeat_2
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
python -m pip install "monai==1.4.0" "numpy<2" pytorch-ignite einops nibabel scipy typer PyYAML fire huggingface_hub && python skills/nv-segment-ct-finetune/scripts/run_finetune.py runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset --smoke --patch-size '[64,64,64]' --output-dir runs/with_vs_without_nv/nv_segment_ct_finetune_codex_opus/opus/with/repeat_3
```

### Opus 4.7, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 4/5, passed=no, steps=unresolved, exit=1

```bash
set -euo pipefail && OUT=runs/with_vs_without_nv/nv_segment_ct_finetune_codex_opus/opus/without/repeat_1 && IN=runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset && BUNDLE="$NV_SEGMENT_CTMR_ROOT" && mkdir -p "$OUT/configs" "$OUT/logs" "$OUT/models" "$OUT/mlruns" && cp "$BUNDLE/configs/train.json" "$BUNDLE/configs/train_continual.json" "$OUT/configs/" && DATALIST=$(ls "$IN"/*.json 2>/dev/null | head -n1) && if [ -z "$DATALIST" ]; then echo "ERROR: no datalist json found in $IN" >&2; exit 1; fi && DATALIST_ABS=$(readlink -f "$DATALIST") && DATASET_ABS=$(readlink -f "$IN") && OUT_ABS=$(readlink -f "$OUT") && python -c "
import json,sys
p='$OUT/configs/train_continual.json'
c=json.load(open(p))
c['data_list_file_path']='$DATALIST_ABS'
c['dataset_dir']='$DATASET_ABS'
c['bundle_root']='$OUT_ABS'
c['ckpt_path']='$OUT_ABS/models'
c['output_dir']='$OUT_ABS'
c['epochs']=1
c['val_at_start']=False
c['n_train_samples']=1
c['n_val_samples']=1
c['patch_size']=[96,96,96]
c['train_dataset_cache_rate']=0.0
c['val_dataset_cache_rate']=0.0
c['num_patches_per_iter']=1
c['num_patches_per_image']=1
json.dump(c,open(p,'w'),indent=2)
print('updated',p)
" && cd "$BUNDLE" && python -m monai.bundle run --bundle_root "$OUT_ABS" --config_file "['$BUNDLE/configs/train.json','$OUT_ABS/configs/train_continual.json']" 2>&1 | tee "$OUT_ABS/logs/finetune.log"
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=1

```bash
set -euo pipefail && OUT=runs/with_vs_without_nv/nv_segment_ct_finetune_codex_opus/opus/without/repeat_2 && IN=runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset && mkdir -p "$OUT/configs" "$OUT/logs" "$OUT/models" "$OUT/mlruns" && BUNDLE="$NV_SEGMENT_CTMR_ROOT" && DATALIST=$(find "$IN" -maxdepth 3 -name "*.json" | head -n 1) && echo "Using bundle: $BUNDLE"; echo "Using datalist: $DATALIST" && cat > "$OUT/configs/smoke_override.json" <<EOF
{
    "bundle_root": "$(pwd)/$OUT",
    "ckpt_path": "$(pwd)/$OUT/models",
    "output_dir": "$(pwd)/$OUT/eval",
    "mlflow_tracking_uri": "$(pwd)/$OUT/mlruns",
    "data_list_file_path": "$(pwd)/$DATALIST",
    "dataset_dir": "$(pwd)/$IN",
    "epochs": 1,
    "val_at_start": false,
    "n_train_samples": 1,
    "n_val_samples": 1,
    "train_dataset_cache_rate": 0.0,
    "val_dataset_cache_rate": 0.0,
    "patch_size": [96, 96, 96],
    "num_patches_per_image": 1,
    "num_patches_per_iter": 1,
    "train#dataloader#batch_size": 1,
    "train#dataloader#num_workers": 0,
    "validate#dataloader#num_workers": 0
}
EOF
cp "$BUNDLE/configs/train.json" "$OUT/configs/train.json" && cp "$BUNDLE/configs/train_continual.json" "$OUT/configs/train_continual.json" && cd "$BUNDLE" && python -m monai.bundle run --bundle_root "$(pwd -P)/../../$OUT" --config_file "['configs/train.json','configs/train_continual.json','$(pwd -P)/$(realpath --relative-to=. ../../$OUT/configs/smoke_override.json 2>/dev/null || echo ../../$OUT/configs/smoke_override.json)']" 2>&1 | tee "../../$OUT/logs/finetune.log"
```

Repeat 3: score 3/5, passed=no, steps=unresolved, exit=None

```bash
OUT=runs/with_vs_without/nv_segment_ct_finetune_codex_opus/opus/without/repeat_3 && IN=runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset && mkdir -p "$OUT/configs" "$OUT/mlruns" "$OUT/models" "$OUT/eval" && DATALIST=$(find "$IN" -maxdepth 3 -name "*.json" | head -n1) && echo "Using datalist: $DATALIST" && BUNDLE="$NV_SEGMENT_CTMR_ROOT" && cp "$BUNDLE/configs/train_continual.json" "$OUT/configs/train_continual.json" && python -c "
import json,os
p='$OUT/configs/smoke_override.json'
cfg={
  'bundle_root': '$BUNDLE',
  'ckpt_path': '$OUT/models',
  'output_dir': '$OUT/eval',
  'mlflow_tracking_uri': '$OUT/mlruns',
  'data_list_file_path': os.path.abspath('$DATALIST'),
  'dataset_dir': os.path.abspath('$IN'),
  'epochs': 1,
  'val_at_start': False,
  'n_train_samples': 1,
  'n_val_samples': 1,
  'train_dataset_cache_rate': 0.0,
  'val_dataset_cache_rate': 0.0,
  'patch_size': [96,96,96],
  'num_patches_per_image': 1,
  'num_patches_per_iter': 1
}
json.dump(cfg, open(p,'w'), indent=2)
print('wrote', p)
" && cd "$BUNDLE" && python -m monai.bundle run --config_file "['configs/train.json','$OLDPWD/$OUT/configs/train_continual.json','$OLDPWD/$OUT/configs/smoke_override.json']" --bundle_root "$BUNDLE"
```

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `examples/studies/with_vs_without_skill/nv_segment_ct_finetune_codex_opus/` |
| Generated outputs | `runs/with_vs_without_nv/nv_segment_ct_finetune_codex_opus/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_segment_ct_finetune_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
