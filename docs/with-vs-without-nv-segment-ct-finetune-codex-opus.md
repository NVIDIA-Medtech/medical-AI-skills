# `nv_segment_ct_finetune`: Codex/Opus LLM+SKILL.md vs LLM+README

Status: strict audit passed for refreshed artifacts on May 29, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

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
| GPT-5.5 / Codex | without | 4.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | 1 (2); None (1) | exit 1 (2); blocked unsafe command fragment: rm (1) | T5: exit 1 (2); T5: blocked unsafe command fragment: rm (1) |
| Opus 4.7 | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | checkpoint reported (3) | none |
| Opus 4.7 | without | 2.7/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | None (2); 1 (1) | command does not reference the expected output directory (2); exit 1 (1) | T2: user input path marker (2); T4: output dir marker (2); T5: command does not reference the expected output directory (2) |

## Analysis

SKILL.md paired advantage: the with-skill arms passed 6/6 backend-repeat trials with an average score of 5.0/5; the README-only arms passed 0/6 backend-repeat trials with an average score of 3.3/5.

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
| GPT-5.5 / Codex | with | 3 | 3 | 3 | 7,560 | 1,205 | 818 | 8,765 | 2,921.7 | 3 | 78.5 |
| GPT-5.5 / Codex | without | 3 | 0 | 3 | 9,219 | 22,960 | 17,794 | 32,179 | 10,726.3 | 2 | 1.1 |
| Opus 4.7 | with | 3 | 3 | 3 | 12,747 | 591 | 0 | 13,338 | 4,446.0 | 3 | 77.9 |
| Opus 4.7 | without | 3 | 0 | 3 | 13,692 | 3,300 | 0 | 16,992 | 5,664.0 | 1 | 0.0 |

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
| 1 | 0 | 2/5 | no | None | T2: user input path marker; T4: output dir marker; T5: command does not reference the expected output directory | tier_2: user input path marker Repair: Use the staged user input path under runs/with_vs_without_nv/_inputs/.<br>tier_4: output dir marker Repair: Write outputs under the exact arm-specific output directory.<br>tier_5: command does not reference the expected output directory Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference the expected output directory Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
| 2 | 0 | 2/5 | no | None | T2: user input path marker; T4: output dir marker; T5: command does not reference the expected output directory | tier_2: user input path marker Repair: Use the staged user input path under runs/with_vs_without_nv/_inputs/.<br>tier_4: output dir marker Repair: Write outputs under the exact arm-specific output directory.<br>tier_5: command does not reference the expected output directory Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference the expected output directory Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
| 3 | 0 | 4/5 | no | 1 | T5: exit 1 | tier_5: exit 1 Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>nonzero_exit: Command exited 1. Repair: Use stderr/stdout to repair setup, paths, arguments, or runtime package installation. |

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
OUT="runs/with_vs_without_nv/nv_segment_ct_finetune_codex_opus/gpt55/without/repeat_1" && DATA="runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset" && SRC="${NV_SEGMENT_CTMR_ROOT:-}" && if [ -z "$SRC" ]; then SRC="$(find .workbench_data/upstreams -type f -path '*/configs/train_continual.json' -print -quit | sed 's#/configs/train_continual.json$##')"; elif [ ! -f "$SRC/configs/train_continual.json" ]; then SRC="$(find "$SRC" -type f -path '*/configs/train_continual.json' -print -quit | sed 's#/configs/train_continual.json$##')"; fi && [ -n "$SRC" ] && [ -f "$SRC/configs/train.json" ] && [ -f "$SRC/configs/train_continual.json" ] && rm -rf "$OUT" && mkdir -p "$OUT/bundle" && cp -a "$SRC"/. "$OUT/bundle"/ && BUNDLE="$OUT/bundle" && export OUT DATA BUNDLE && python - <<'PY' &&
import json, os, re
from pathlib import Path

import nibabel as nib
import numpy as np

root = Path(os.environ["DATA"]).resolve()
out = Path(os.environ["OUT"]).resolve()
bundle = Path(os.environ["BUNDLE"]).resolve()

def is_nifti(p: Path) -> bool:
    n = p.name.lower()
    return n.endswith(".nii") or n.endswith(".nii.gz")

all_nii = sorted(p for p in root.rglob("*") if p.is_file() and is_nifti(p))
if not all_nii:
    raise SystemExit(f"No NIfTI files found under {root}")

def looks_label(p: Path) -> bool:
    parts = [x.lower() for x in p.relative_to(root).parts]
    name = p.name.lower()
    return (
        any(("label" in x) or (x in {"mask", "masks", "seg", "segs", "segmentations"}) for x in parts)
        or re.search(r"(^|[_\-.])(label|labels|mask|masks|seg|segs)([_\-.]|$)", name) is not None
    )

label_files = sorted(p for p in all_nii if looks_label(p))
image_files = sorted(p for p in all_nii if p not in set(label_files))
if not label_files or not image_files:
    raise SystemExit(f"Could not infer image/label NIfTI pairs under {root}: {len(image_files)} images, {len(label_files)} labels")

def strip_ext(name: str) -> str:
    name = name.lower()
    if name.endswith(".nii.gz"):
        return name[:-7]
    if name.endswith(".nii"):
        return name[:-4]
    return name

def norm_key(p: Path) -> str:
    s = strip_ext(p.name)
    s = re.sub(r"(_|-)?000[0-9]$", "", s)
    s = re.sub(r"^(image|images|img|ct|label|labels|mask|masks|seg|segs|segmentation|segmentations)[_\-.]*", "", s)
    s = re.sub(r"[_\-.]*(image|images|img|ct|label|labels|mask|masks|seg|segs|segmentation|segmentations)$", "", s)
    return re.sub(r"[^a-z0-9]+", "", s)

image_by_key = {}
for img in image_files:
    image_by_key.setdefault(norm_key(img), img)

pairs = []
used_images = set()
for lab in label_files:
    candidates = []
    rel = lab.relative_to(root)
    rel_s = str(rel)
    repls = [
        ("labelsTr", "imagesTr"), ("labelsTs", "imagesTs"),
        ("labels", "images"), ("label", "image"),
        ("masks", "images"), ("mask", "image"),
        ("segs", "images"), ("seg", "image"),
        ("segmentations", "images"), ("segmentation", "image"),
    ]
    for a, b in repls:
        candidates.append(root / rel_s.replace(a, b))
        candidates.append(root / rel_s.replace(a.lower(), b.lower()))
    base = strip_ext(lab.name)
    for prefix in ["label", "labels", "mask", "masks", "seg", "segs", "segmentation", "segmentations"]:
        candidates.append(lab.with_name(re.sub(f"^{prefix}[_\\-.]*", "image_", base, flags=re.I) + ".nii.gz"))
        candidates.append(lab.with_name(re.sub(f"^{prefix}[_\\-.]*", "img_", base, flags=re.I) + ".nii.gz"))
    img = next((c for c in candidates if c.exists() and c.is_file() and is_nifti(c) and c in image_files), None)
    if img is None:
        img = image_by_key.get(norm_key(lab))
    if img is None:
        remaining = [p for p in image_files if p not in used_images]
        if len(label_files) == len(image_files) and remaining:
            img = remaining[0]
    if img is None:
        raise SystemExit(f"Could not match label to image: {lab}")
    used_images.add(img)
    pairs.append((img, lab))

label_values = set()
for _, lab in pairs:
    arr = np.asanyarray(nib.load(str(lab)).dataobj)
    for v in np.unique(arr):
        iv = int(round(float(v)))
        if iv > 0:
            label_values.add(iv)
if not label_values:
    raise SystemExit("No positive label values found in label volumes")

used_mapped = set()
next_free = 1
label_mappings = []
for src in sorted(label_values):
    if 0 < src < 255 and src not in used_mapped:
        dst = src
    else:
        while next_free in used_mapped or next_free >= 255:
            next_free += 1
        if next_free >= 255:
            raise SystemExit("Too many labels to map below 255 for smoke run")
        dst = next_free
    used_mapped.add(dst)
    label_mappings.append([int(src), int(dst)])

entries = []
if len(pairs) == 1:
    img, lab = pairs[0]
    entries = [
        {"image": str(img.relative_to(root)), "label": str(lab.relative_to(root)), "fold": 1},
        {"image": str(img.relative_to(root)), "label": str(lab.relative_to(root)), "fold": 0},
    ]
else:
    for i, (img, lab) in enumerate(pairs):
        entries.append({"image": str(img.relative_to(root)), "label": str(lab.relative_to(root)), "fold": 0 if i == 0 else 1})

datalist = out / "smoke_dataset_folds.json"
datalist.write_text(json.dumps({"training": entries}, indent=2) + "\n")

def mutate(obj):
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if k == "data_list_file_path":
                obj[k] = str(datalist)
            elif k == "dataset_dir":
                obj[k] = str(root)
            elif k == "label_mappings":
                obj[k] = {"default": label_mappings}
            elif k == "patch_size":
                obj[k] = [96, 96, 96]
            elif k in {"n_train_samples", "n_val_samples", "max_epochs", "num_epochs", "epoch_length", "val_interval", "validation_interval"}:
                obj[k] = 1
            elif k in {"train_dataset_cache_rate", "val_dataset_cache_rate"}:
                obj[k] = 0.0
            elif k == "val_at_start":
                obj[k] = False
            elif k == "num_workers":
                obj[k] = 0
            elif k == "drop_point_prob":
                obj[k] = 1
            elif k == "drop_label_prob":
                obj[k] = 0
            else:
                mutate(v)
    elif isinstance(obj, list):
        for x in obj:
            mutate(x)

for rel in ["configs/train.json", "configs/train_continual.json"]:
    path = bundle / rel
    cfg = json.loads(path.read_text())
    mutate(cfg)
    if rel.endswith("train_continual.json"):
        cfg["data_list_file_path"] = str(datalist)
        cfg["dataset_dir"] = str(root)
        cfg["label_mappings"] = {"default": label_mappings}
        cfg["patch_size"] = [96, 96, 96]
        cfg["n_train_samples"] = 1
        cfg["n_val_samples"] = 1
        cfg["train_dataset_cache_rate"] = 0.0
        cfg["val_dataset_cache_rate"] = 0.0
        cfg["val_at_start"] = False
    path.write_text(json.dumps(cfg, indent=2) + "\n")

print(f"Prepared smoke fine-tune bundle at {bundle}")
print(f"Prepared datalist at {datalist}")
print(f"Using label_mappings={label_mappings}")
PY
cd "$BUNDLE" && python -m monai.bundle run --config_file="['configs/train.json','configs/train_continual.json']"
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=1

```bash
set -euo pipefail && IN="runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset" && OUT="runs/with_vs_without_nv/nv_segment_ct_finetune_codex_opus/gpt55/without/repeat_2" && RUNTIME="$OUT/bundle_runtime" && python - "$IN" "$OUT" "$RUNTIME" "${NV_SEGMENT_CTMR_ROOT:?NV_SEGMENT_CTMR_ROOT must point to the NV-Segment-CT bundle root}" <<'PY' && cd "$RUNTIME" && python -m monai.bundle run --config_file="['configs/train.json','configs/train_continual.json','configs/codex_smoke.json']"
import json, os, shutil, sys
from pathlib import Path

inp = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
runtime = Path(sys.argv[3]).resolve()
upstream = Path(sys.argv[4]).resolve()

if not inp.is_dir():
    raise SystemExit(f"input dataset not found: {inp}")
if not upstream.is_dir():
    raise SystemExit(f"upstream bundle root not found: {upstream}")

out.mkdir(parents=True, exist_ok=True)
if runtime.exists():
    shutil.rmtree(runtime)
shutil.copytree(upstream, runtime, symlinks=True, ignore=shutil.ignore_patterns("mlruns", "__pycache__", "*.pyc"))

def is_nii(p: Path) -> bool:
    n = p.name.lower()
    return n.endswith(".nii") or n.endswith(".nii.gz")

def stem_nii(p: Path) -> str:
    n = p.name
    if n.lower().endswith(".nii.gz"):
        return n[:-7]
    if n.lower().endswith(".nii"):
        return n[:-4]
    return p.stem

all_nii = sorted([p for p in inp.rglob("*") if p.is_file() and is_nii(p)])
label_candidates = sorted([
    p for p in all_nii
    if any(part.lower() in {"label", "labels", "labelstr", "labelsval", "seg", "segs", "mask", "masks"} for part in p.parts)
    or any(tok in p.name.lower() for tok in ("label", "seg", "mask"))
])
if (inp / "labelsTr").is_dir():
    label_candidates = sorted([p for p in (inp / "labelsTr").rglob("*") if p.is_file() and is_nii(p)])
if not label_candidates:
    raise SystemExit("could not identify label NIfTI files in the input dataset")

label_set = set(label_candidates)
image_candidates = sorted([p for p in all_nii if p not in label_set])

def norm_key(p: Path) -> str:
    s = stem_nii(p).lower()
    for pref in ("label_", "labels_", "label", "seg_", "seg", "mask_", "mask", "image_", "images_", "image", "img_", "img"):
        if s.startswith(pref):
            s = s[len(pref):]
    for suff in ("_label", "_labels", "-label", "-labels", "_seg", "-seg", "_mask", "-mask", "_image", "-image", "_img", "-img"):
        if s.endswith(suff):
            s = s[:-len(suff)]
    return s

by_key = {}
 for_img = image_candidates
for img in for_img:
    by_key.setdefault(norm_key(img), []).append(img)

pairs = []
used_images = set()
for lbl in label_candidates:
    tries = []
    rel = lbl.relative_to(inp)
    parts = list(rel.parts)
    for i, part in enumerate(parts[:-1]):
        low = part.lower()
        if low in {"labelstr", "labelsval", "labels", "label"}:
            repl = "imagesTr" if low == "labelstr" else "imagesVal" if low == "labelsval" else "images"
            cand = inp.joinpath(*parts[:i], repl, *parts[i+1:])
            tries.append(cand)
    lname = lbl.name
    for a, b in [("label", "img"), ("labels", "images"), ("seg", "img"), ("mask", "img")]:
        tries.append(lbl.with_name(lname.replace(a, b, 1)))
        tries.append(lbl.with_name(lname.replace(a.capitalize(), b.capitalize(), 1)))
    tries.extend(by_key.get(norm_key(lbl), []))
    img = next((c for c in tries if c.exists() and c.is_file() and is_nii(c) and c != lbl and c not in used_images), None)
    if img is None and len(image_candidates) == len(label_candidates):
        img = image_candidates[label_candidates.index(lbl)]
    if img is None:
        raise SystemExit(f"could not match image for label: {lbl}")
    used_images.add(img)
    pairs.append((img, lbl))

pairs = sorted(pairs, key=lambda x: str(x[0]))
entries = []
if len(pairs) == 1:
    img, lbl = pairs[0]
    entries.append({"image": str(img.relative_to(inp)), "label": str(lbl.relative_to(inp)), "fold": 1})
    entries.append({"image": str(img.relative_to(inp)), "label": str(lbl.relative_to(inp)), "fold": 0})
else:
    for i, (img, lbl) in enumerate(pairs):
        entries.append({"image": str(img.relative_to(inp)), "label": str(lbl.relative_to(inp)), "fold": 0 if i == 0 else 1})

vals = set()
try:
    import nibabel as nib
    import numpy as np
    for _, lbl in pairs[: min(3, len(pairs))]:
        arr = np.asanyarray(nib.load(str(lbl)).dataobj)
        for v in np.unique(arr):
            iv = int(v)
            if iv > 0 and float(v) == float(iv):
                vals.add(iv)
except Exception:
    vals = {1}
if not vals:
    vals = {1}

mappings = [[v, 3 if vals == {1} and v == 1 else v] for v in sorted(vals)]

datalist = out / "codex_smoke_datalist.json"
datalist.write_text(json.dumps({"training": entries}, indent=2) + "\n")

cfg = {
    "bundle_root": str(runtime),
    "data_list_file_path": str(datalist),
    "dataset_dir": str(inp),
    "label_mappings": {"default": mappings},
    "patch_size": [64, 64, 64],
    "n_train_samples": 1,
    "n_val_samples": 1,
    "val_at_start": False,
    "max_epochs": 1,
    "val_interval": 1,
    "num_workers": 0,
    "train_num_workers": 0,
    "val_num_workers": 0,
    "train_dataset_cache_rate": 0.0,
    "val_dataset_cache_rate": 0.0,
    "use_mlflow": False,
    "drop_point_prob": 1.0,
    "drop_label_prob": 0.0
}
(runtime / "configs" / "codex_smoke.json").write_text(json.dumps(cfg, indent=2) + "\n")
print(f"Prepared smoke finetune bundle at {runtime}")
print(f"Datalist: {datalist}")
print(f"Label mappings: {mappings}")
PY
```

Repeat 3: score 4/5, passed=no, steps=unresolved, exit=1

```bash
OUT='runs/with_vs_without_nv/nv_segment_ct_finetune_codex_opus/gpt55/without/repeat_3' && DATA='runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset' && python - "$OUT" "$DATA" "${NV_SEGMENT_CTMR_ROOT:?NV_SEGMENT_CTMR_ROOT is not set}" <<'PY' && cd "$OUT/bundle" && MLFLOW_TRACKING_URI="file:$(pwd)/mlruns" python -m monai.bundle run --config_file="['configs/train.json','configs/train_continual.json']"
from pathlib import Path
import json, re, shutil, sys

out = Path(sys.argv[1]).resolve()
data = Path(sys.argv[2]).resolve()
src = Path(sys.argv[3]).resolve()
bundle = out / "bundle"

if not data.is_dir():
    raise SystemExit(f"input dataset not found: {data}")
if not (src / "configs" / "train.json").is_file() or not (src / "configs" / "train_continual.json").is_file():
    raise SystemExit(f"bundle configs not found under: {src}")

out.mkdir(parents=True, exist_ok=True)
if bundle.exists():
    shutil.rmtree(bundle)
shutil.copytree(src, bundle, ignore=shutil.ignore_patterns("mlruns", "__pycache__", "*.pyc"))

def strip_nii(name):
    return name[:-7] if name.endswith(".nii.gz") else name[:-4] if name.endswith(".nii") else name

nii_files = sorted(p for p in data.rglob("*") if p.is_file() and (p.name.endswith(".nii.gz") or p.name.endswith(".nii")))

def is_label(p):
    rel_parts = [x.lower() for x in p.relative_to(data).parts]
    return any(("label" in x) or ("seg" in x) or ("mask" in x) for x in rel_parts)

label_files = [p for p in nii_files if is_label(p)]
image_files = [p for p in nii_files if p not in set(label_files)]
if not label_files or not image_files:
    raise SystemExit("could not infer image/label NIfTI pairs from the input dataset")

def norm_key(p):
    s = strip_nii(p.name).lower()
    s = re.sub(r"_0000$", "", s)
    s = re.sub(r"(labels?|segmentations?|segs?|masks?|images?|imgs?|ct)", "", s)
    return re.sub(r"[^a-z0-9]+", "", s)

by_name, by_key = {}, {}
for img in image_files:
    by_name.setdefault(img.name, []).append(img)
    by_key.setdefault(norm_key(img), []).append(img)

pairs, used = [], set()
for lab in label_files:
    candidates = by_name.get(lab.name, []) + by_key.get(norm_key(lab), [])
    candidates = [c for c in candidates if c not in used]
    if not candidates and len(image_files) == len(label_files):
        candidates = [image_files[label_files.index(lab)]]
    if candidates:
        img = sorted(candidates)[0]
        used.add(img)
        pairs.append((img, lab))

if not pairs:
    raise SystemExit("no image/label pairs could be inferred")

entries = []
if len(pairs) == 1:
    img, lab = pairs[0]
    entries = [
        {"image": img.relative_to(data).as_posix(), "label": lab.relative_to(data).as_posix(), "fold": 1},
        {"image": img.relative_to(data).as_posix(), "label": lab.relative_to(data).as_posix(), "fold": 0},
    ]
else:
    for i, (img, lab) in enumerate(pairs):
        entries.append({"image": img.relative_to(data).as_posix(), "label": lab.relative_to(data).as_posix(), "fold": 0 if i == 0 else 1})

datalist = bundle / "configs" / "smoke_datalist.json"
datalist.write_text(json.dumps({"training": entries}, indent=2) + "\n")

train_path = bundle / "configs" / "train.json"
cont_path = bundle / "configs" / "train_continual.json"
train_cfg = json.loads(train_path.read_text())
cont_cfg = json.loads(cont_path.read_text())

def recursive_update(obj, updates):
    if isinstance(obj, dict):
        for k in list(obj.keys()):
            if k in updates:
                obj[k] = updates[k]
            else:
                recursive_update(obj[k], updates)
    elif isinstance(obj, list):
        for v in obj:
            recursive_update(v, updates)

smoke_updates = {
    "max_epochs": 1,
    "num_epochs": 1,
    "val_interval": 1,
    "batch_size": 1,
    "num_workers": 0,
    "drop_point_prob": 1.0,
    "drop_label_prob": 0.0,
}
recursive_update(train_cfg, smoke_updates)
recursive_update(cont_cfg, smoke_updates)

train_cfg.update({"max_epochs": 1, "drop_point_prob": 1.0, "drop_label_prob": 0.0})
cont_cfg.update({
    "data_list_file_path": str(datalist),
    "dataset_dir": str(data),
    "label_mappings": {"default": [[1, 3]]},
    "val_at_start": False,
    "n_train_samples": 1,
    "n_val_samples": 1,
    "patch_size": [64, 64, 64],
    "train_dataset_cache_rate": 0.0,
    "val_dataset_cache_rate": 0.0,
    "max_epochs": 1,
    "drop_point_prob": 1.0,
    "drop_label_prob": 0.0,
})

train_path.write_text(json.dumps(train_cfg, indent=2) + "\n")
cont_path.write_text(json.dumps(cont_cfg, indent=2) + "\n")
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

Repeat 1: score 2/5, passed=no, steps=unresolved, exit=None

```bash
set -euo pipefail && BUNDLE_ROOT="${NV_SEGMENT_CTMR_ROOT}" && IN_DIR="$(pwd)/runs/with_vs_without/_inputs/nv_segment_ct_finetune/input_dataset" && OUT_DIR="$(pwd)/runs/with_vs_without/nv_segment_ct_finetune_codex_opus/opus/without/repeat_1" && mkdir -p "${OUT_DIR}" && DATALIST="$(find "${IN_DIR}" -maxdepth 3 -name '*.json' | head -n1)" && echo "Using datalist: ${DATALIST}" && cat > "${OUT_DIR}/smoke_override.json" <<EOF
{
    "bundle_root": "${OUT_DIR}",
    "ckpt_path": "${OUT_DIR}/model",
    "output_dir": "${OUT_DIR}/eval",
    "mlflow_tracking_uri": "${OUT_DIR}/mlruns",
    "data_list_file_path": "${DATALIST}",
    "dataset_dir": "${IN_DIR}",
    "label_mappings": {"default": [[1, 3]]},
    "patch_size": [96, 96, 96],
    "epochs": 1,
    "n_train_samples": 1,
    "n_val_samples": 1,
    "train_dataset_cache_rate": 0.0,
    "val_dataset_cache_rate": 0.0,
    "val_at_start": false,
    "use_mlflow": false
}
EOF
mkdir -p "${OUT_DIR}/model" "${OUT_DIR}/eval" && cd "${BUNDLE_ROOT}" && python -m monai.bundle run --config_file "['${BUNDLE_ROOT}/configs/train.json','${BUNDLE_ROOT}/configs/train_continual.json','${OUT_DIR}/smoke_override.json']" 2>&1 | tee "${OUT_DIR}/train.log"
```

Repeat 2: score 2/5, passed=no, steps=unresolved, exit=None

```bash
set -euo pipefail && OUT=runs/with_vs_without/nv_segment_ct_finetune_codex_opus/opus/without/repeat_2 && IN=runs/with_vs_without/_inputs/nv_segment_ct_finetune/input_dataset && BUNDLE="$NV_SEGMENT_CTMR_ROOT" && mkdir -p "$OUT/configs" && cp "$BUNDLE/configs/train.json" "$OUT/configs/train.json" && cp "$BUNDLE/configs/train_continual.json" "$OUT/configs/train_continual.json" && DATALIST=$(ls "$IN"/*.json 2>/dev/null | head -n1) && if [ -z "$DATALIST" ]; then DATALIST="$OUT/configs/datalist.json"; python -c "import os,json,glob; d='$IN'; imgs=sorted(glob.glob(os.path.join(d,'**','*image*.nii.gz'),recursive=True))+sorted(glob.glob(os.path.join(d,'imagesTr','*.nii.gz'))); lbls=sorted(glob.glob(os.path.join(d,'**','*label*.nii.gz'),recursive=True))+sorted(glob.glob(os.path.join(d,'labelsTr','*.nii.gz'))); imgs=list(dict.fromkeys(imgs)); lbls=list(dict.fromkeys(lbls)); pairs=list(zip(imgs,lbls)); tr=[{'image':os.path.relpath(i,d),'label':os.path.relpath(l,d),'fold':1} for i,l in pairs]; tr[0]['fold']=0; json.dump({'training':tr,'testing':[]}, open('$DATALIST','w'), indent=2); print('Wrote',len(tr),'items')"; fi && DATALIST_ABS=$(realpath "$DATALIST") && DATASET_DIR_ABS=$(realpath "$IN") && python -c "
import json
p='$OUT/configs/train_continual.json'
c=json.load(open(p))
c['data_list_file_path']='$DATALIST_ABS'
c['dataset_dir']='$DATASET_DIR_ABS'
c['epochs']=1
c['n_train_samples']=1
c['n_val_samples']=1
c['num_patches_per_iter']=1
c['val_at_start']=False
c['patch_size']=[96,96,96]
c['train_dataset_cache_rate']=0.0
c['val_dataset_cache_rate']=0.0
c['label_mappings']={'default':[[1,3]]}
c['ckpt_path']='$OUT/models'
c['output_dir']='$OUT/eval'
c['mlflow_tracking_uri']='$OUT/mlruns'
json.dump(c, open(p,'w'), indent=2)
" && cd "$BUNDLE" && python -m monai.bundle run --bundle_root "$BUNDLE" --config_file "['$BUNDLE/configs/train.json','$(realpath $OLDPWD/$OUT/configs/train_continual.json)']" 2>&1 | tee "$OLDPWD/$OUT/train.log"
```

Repeat 3: score 4/5, passed=no, steps=unresolved, exit=1

```bash
OUT=runs/with_vs_without_nv/nv_segment_ct_finetune_codex_opus/opus/without/repeat_3 && IN=runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset && BUNDLE="$NV_SEGMENT_CTMR_ROOT" && mkdir -p "$OUT/configs" && cp "$BUNDLE/configs/train.json" "$OUT/configs/train.json" && cp "$BUNDLE/configs/train_continual.json" "$OUT/configs/train_continual.json" && python -c "
import json, os, glob
in_dir = os.path.abspath('$IN')
imgs = sorted(glob.glob(os.path.join(in_dir, 'imagesTr', '*.nii.gz')) or glob.glob(os.path.join(in_dir, 'images', '*.nii.gz')))
lbls = sorted(glob.glob(os.path.join(in_dir, 'labelsTr', '*.nii.gz')) or glob.glob(os.path.join(in_dir, 'labels', '*.nii.gz')))
assert imgs and lbls and len(imgs)==len(lbls), f'imgs={len(imgs)} lbls={len(lbls)}'
training=[]
for i,(im,lb) in enumerate(zip(imgs,lbls)):
    training.append({'image': os.path.relpath(im,in_dir), 'label': os.path.relpath(lb,in_dir), 'fold': 0 if i==0 else 1})
json.dump({'training':training,'testing':[]}, open('$OUT/datalist.json','w'), indent=2)
" && python -c "
import json
p='$OUT/configs/train_continual.json'
c=json.load(open(p))
c['data_list_file_path']='$(pwd)/$OUT/datalist.json'
c['dataset_dir']='$(pwd)/$IN'
c['label_mappings']={'default':[[1,3]]}
c['epochs']=1
c['val_at_start']=False
c['n_train_samples']=1
c['n_val_samples']=1
c['patch_size']=[96,96,96]
c['train_dataset_cache_rate']=0.0
c['val_dataset_cache_rate']=0.0
json.dump(c, open(p,'w'), indent=2)
" && mkdir -p "$OUT/models" "$OUT/eval" "$OUT/mlruns" && cd "$BUNDLE" && python -m monai.bundle run --config_file="['$OLDPWD/$OUT/configs/train.json','$OLDPWD/$OUT/configs/train_continual.json']" --bundle_root "$OLDPWD/$OUT" --ckpt_path "$OLDPWD/$OUT/models/model.pt" --output_dir "$OLDPWD/$OUT/eval" --mlflow_tracking_uri "$OLDPWD/$OUT/mlruns" 2>&1 | tee "$OLDPWD/$OUT/train.log"
```

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `runs/with_vs_without_nv/studies/nv_segment_ct_finetune_codex_opus/` |
| Generated outputs | `runs/with_vs_without_nv/nv_segment_ct_finetune_codex_opus/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_segment_ct_finetune_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
