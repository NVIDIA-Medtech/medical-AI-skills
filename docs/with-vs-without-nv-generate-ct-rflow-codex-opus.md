# `nv_generate_ct_rflow`: Codex/Opus LLM+SKILL.md vs LLM+README

Status: strict audit passed for refreshed artifacts on May 27, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

This report compares `LLM + SKILL.md` with `LLM + upstream README/guide`. The completed direct-API run used the corrected embedded-doc minimal prompt because those backends cannot read repo files. The fair NAT/tool-agent prompt artifact is A2-style: it gives a natural user request, a neutral staged input path, an output directory, and tells the agent which arm-specific document to read. It does not spell out operational details such as entrypoints, labels, model variants, or config filenames outside the documentation arm.

## Experiment Question

Does `LLM + SKILL.md` make an agent better at reading documentation and taking the right action than `LLM + upstream README/guide`?

## User Request Shape

The prompt request for the GPT-5.5 with-skill arm was:

> The case request is at runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json. Synthesize one paired 3D CT image and segmentation mask for a chest case with a lung tumor, and write the output pair under runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/with/repeat_1.

The staged user input for every arm was `runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json`. The source fixture `skills/nv-generate-ct-rflow/fixtures/chest_lung_tumor_controllable.json` was used only to stage that neutral input path.

Fair path-prompt artifact: `tools/nat_audit/data/eval_nv_model_studies_nv_generate_ct_rflow_prompts.json`

## Result

| Backend | Arm | Mean score | Passes | Steps | Exit | Tier 5 | Failed tiers |
|---|---|---:|---:|---|---|---|---|
| GPT-5.5 / Codex | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | image shape=(256, 256, 256); label shape=(256, 256, 256) (3) | none |
| GPT-5.5 / Codex | without | 4.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | 1 (2); None (1) | exit 1 (2); blocked unsafe command fragment: rm (1) | T5: exit 1 (2); T5: blocked unsafe command fragment: rm (1) |
| Opus 4.7 | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | image shape=(256, 256, 256); label shape=(256, 256, 256) (3) | none |
| Opus 4.7 | without | 2.7/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | None (2); 1 (1) | command does not reference the expected output directory (2); exit 1 (1) | T2: user input path marker (2); T4: output dir marker (2); T5: command does not reference the expected output directory (2) |

## Analysis

SKILL.md paired advantage: the with-skill arms passed 6/6 backend-repeat trials with an average score of 5.0/5; the README-only arms passed 0/6 backend-repeat trials with an average score of 3.3/5.

SKILL.md paired advantage: SKILL.md wins 6/6 matched backend-repeat pairs, README-only wins 0/6, and 0/6 are ties. Pass/fail is the primary outcome; score breaks ties only when pass status is equal. Exact one-sided sign-test p=0.01562 across 6 decisive pair(s).

Outcome-support gate: Supports SKILL.md advantage. SKILL.md wins 6/6 matched pair(s); README-only wins 0/6; sign-test p=0.01562.

Each backend/arm/skill configuration was repeated three times. A repeat is independent: it has its own output directory, and each execution attempt inside the repeat creates a fresh venv before running the generated command. Dependency and model download caches are shared only as documented test-environment caches under `.workbench_data/with_vs_without_cache` (`PIP_CACHE_DIR=.workbench_data/with_vs_without_cache/pip`, `HF_HOME=.workbench_data/with_vs_without_cache/huggingface`, `HF_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `HUGGINGFACE_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `TRANSFORMERS_CACHE=.workbench_data/with_vs_without_cache/huggingface/transformers`, `TORCH_HOME=.workbench_data/with_vs_without_cache/torch`, `XDG_CACHE_HOME=.workbench_data/with_vs_without_cache/xdg`, `CONDA_PKGS_DIRS=.workbench_data/with_vs_without_cache/conda_pkgs`, `UV_CACHE_DIR=.workbench_data/with_vs_without_cache/uv`, `CUDA_CACHE_PATH=.workbench_data/with_vs_without_cache/cuda`, `NUMBA_CACHE_DIR=.workbench_data/with_vs_without_cache/numba`).

The main baseline uses `max_correction_steps=0`: each repeat sends one prompt, executes the extracted command once, and records pass/fail, runtime, tokens, and deterministic failure analysis. The repair-loop implementation remains available for separate diagnostic experiments, but it is not part of this comparison.

All with-skill repeats exited successfully and produced artifacts accepted by the deterministic grader. That means the final SKILL.md surface was repeatable for both tested agent backends.

The README-only commands did not pass tier 5. Typical failure modes were unsafe generated shell cleanup, missing schema fields, missing model/control details, or upstream commands that did not execute cleanly from Medical AI Skills root.

Tier 2 is intentionally strict: a command only earns it if it uses the staged user input path `runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json`.

## Token Profiling

Token counts are provider-reported values saved in each repeat JSON. Reasoning tokens are shown only when the provider returned that subfield and are a subset of completion tokens, not an additional cost to add to total tokens. Execution time is averaged only across repeats that reached command execution; no-command-extracted repeats still count toward token totals.

| Backend | Arm | Repeats | Passes | Attempts | Prompt tokens | Completion tokens | Reasoning tokens | Total tokens | Mean total/repeat | Executed | Mean exec s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GPT-5.5 / Codex | with | 3 | 3 | 3 | 8,943 | 2,242 | 1,739 | 11,185 | 3,728.3 | 3 | 114.3 |
| GPT-5.5 / Codex | without | 3 | 0 | 3 | 8,988 | 20,673 | 16,894 | 29,661 | 9,887.0 | 2 | 0.0 |
| Opus 4.7 | with | 3 | 3 | 3 | 15,240 | 672 | 0 | 15,912 | 5,304.0 | 3 | 113.9 |
| Opus 4.7 | without | 3 | 0 | 3 | 14,271 | 2,743 | 0 | 17,014 | 5,671.3 | 1 | 0.0 |

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
| 1 | 0 | 2/5 | no | None | T2: user input path marker; T4: output dir marker; T5: command does not reference the expected output directory | tier_2: user input path marker Repair: Use the staged user input path under runs/with_vs_without_nv/_inputs/.<br>tier_4: output dir marker Repair: Write outputs under the exact arm-specific output directory.<br>tier_5: command does not reference the expected output directory Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference the expected output directory Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
| 2 | 0 | 4/5 | no | 1 | T5: exit 1 | tier_5: exit 1 Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>nonzero_exit: Command exited 1. Repair: Use stderr/stdout to repair setup, paths, arguments, or runtime package installation. |
| 3 | 0 | 2/5 | no | None | T2: user input path marker; T4: output dir marker; T5: command does not reference the expected output directory | tier_2: user input path marker Repair: Use the staged user input path under runs/with_vs_without_nv/_inputs/.<br>tier_4: output dir marker Repair: Write outputs under the exact arm-specific output directory.<br>tier_5: command does not reference the expected output directory Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference the expected output directory Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |

## Skill Fix Notes

No separate final-run skill fix note is recorded in the saved study JSON for this scenario; this report was regenerated from the post-fix study artifacts.

## Generated Commands

These are the extracted first-attempt commands by repeat.

### GPT-5.5 / Codex, with arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-$HOME/nv-generate-ctmr}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-ct-rflow/scripts/run_rflow_ct.py runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json --output-dir runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/with/repeat_1 --random-seed 1 --version rflow-ct --yes
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
OUT="runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/with/repeat_2" && mkdir -p "$OUT" && python -c 'import json, pathlib; src=pathlib.Path("runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json"); out=pathlib.Path("runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/with/repeat_2"); cfg=json.loads(src.read_text()); cfg["num_output_samples"]=1; dst=out/"config_infer_override.one_sample.json"; dst.write_text(json.dumps(cfg, indent=2) + "\n")' && export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-$HOME/nv-generate-ctmr}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-ct-rflow/scripts/run_rflow_ct.py "$OUT/config_infer_override.one_sample.json" --output-dir "$OUT" --random-seed 2 --version rflow-ct --yes
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-$HOME/nv-generate-ctmr}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-ct-rflow/scripts/run_rflow_ct.py runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json --output-dir runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/with/repeat_3 --random-seed 3 --version rflow-ct --yes
```

### GPT-5.5 / Codex, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 4/5, passed=no, steps=unresolved, exit=1

```bash
OUT="runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/without/repeat_1" && \
REQ="runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json" && \
NV_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && \
export OUT REQ NV_ROOT && \
OUT_ABS="$(python -c 'import os; print(os.path.abspath(os.environ["OUT"]))')" && \
NV_ROOT_ABS="$(python -c 'import os; print(os.path.abspath(os.environ["NV_ROOT"]))')" && \
export OUT_ABS NV_ROOT="$NV_ROOT_ABS" PYTHONDONTWRITEBYTECODE=1 MONAI_DATA_DIRECTORY="$OUT_ABS/_runtime/monai_data" && \
mkdir -p "$OUT/_runtime/monai_data" && \
python - <<'PY_PREP' && \
(cd "$NV_ROOT" && python -B -m scripts.inference -t ./configs/config_network_rflow.json -i "$OUT_ABS/_runtime/config_infer.json" -e ./configs/environment_rflow-ct.json --random-seed 0 --version rflow-ct) && \
python - <<'PY_CLEAN'
import json, os, re, shutil
from pathlib import Path

out = Path(os.environ["OUT_ABS"])
runtime = out / "_runtime"
req = Path(os.environ["REQ"])
nv = Path(os.environ["NV_ROOT"])

if not req.is_file():
    raise SystemExit(f"Missing request JSON: {req}")
if not (nv / "configs" / "config_infer.json").is_file():
    raise SystemExit(f"Missing upstream config_infer.json under: {nv}")
if not (nv / "configs" / "label_dict.json").is_file():
    raise SystemExit(f"Missing upstream label_dict.json under: {nv}")

runtime.mkdir(parents=True, exist_ok=True)
shutil.copyfile(req, runtime / "request.json")

def load_json(p):
    with open(p, "r") as f:
        return json.load(f)

def dump_json(obj, p):
    with open(p, "w") as f:
        json.dump(obj, f, indent=2, sort_keys=True)

def collect_label_names(obj):
    names = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and not k.strip().lstrip("-").isdigit():
                names.append(k)
            if isinstance(v, str):
                names.append(v)
            else:
                names.extend(collect_label_names(v))
    elif isinstance(obj, list):
        for v in obj:
            if isinstance(v, str):
                names.append(v)
            else:
                names.extend(collect_label_names(v))
    seen, out_names = set(), []
    for n in names:
        if n not in seen:
            seen.add(n)
            out_names.append(n)
    return out_names

def norm(s):
    return re.sub(r"\s+", " ", str(s).replace("_", " ").replace("-", " ").lower()).strip()

labels = collect_label_names(load_json(nv / "configs" / "label_dict.json"))
lung_exact = [n for n in labels if norm(n) == "lung"]
lung_candidates = lung_exact or [n for n in labels if "lung" in norm(n) and not any(x in norm(n) for x in ("tumor", "nodule", "cancer"))]
if not lung_candidates:
    raise SystemExit("Could not resolve a lung anatomy label from configs/label_dict.json")
lung_labels = lung_candidates[:1] if lung_exact else lung_candidates[:6]

tumor_exact = [n for n in labels if norm(n) in ("lung tumor", "lung tumour")]
tumor_candidates = tumor_exact or [n for n in labels if "lung" in norm(n) and any(x in norm(n) for x in ("tumor", "tumour", "cancer", "nodule"))]
tumor_candidates = tumor_candidates or [n for n in labels if norm(n) in ("tumor", "tumour")]
tumor_candidates = tumor_candidates or [n for n in labels if any(x in norm(n) for x in ("tumor", "tumour", "cancer", "nodule"))]
if not tumor_candidates:
    raise SystemExit("Could not resolve a tumor anatomy label from configs/label_dict.json")
tumor_label = tumor_candidates[0]

anatomy_list = []
for name in [*lung_labels, tumor_label]:
    if name not in anatomy_list:
        anatomy_list.append(name)

cfg = load_json(nv / "configs" / "config_infer.json")
for k in list(cfg.keys()):
    if k.lower() in {
        "num_output_samples", "num_outputs", "num_samples", "n_samples",
        "num_images", "n_images", "num_volumes", "n_volumes", "number_of_images",
        "num_generated_images"
    }:
        cfg[k] = 1

cfg.update({
    "body_region": ["chest", "thorax"],
    "anatomy_list": anatomy_list,
    "controllable_anatomy_size": [[tumor_label, 0.5]],
    "output_size": [256, 256, 256],
    "spacing": [1.5, 1.5, 1.5],
    "modality": 1,
    "output_dir": str(out),
    "num_inference_steps": 30,
    "mask_generation_num_inference_steps": 1000,
    "cfg_guidance_scale": 1.0
})
if "dim" in cfg:
    cfg["dim"] = [256, 256, 256]

dump_json(cfg, runtime / "config_infer.json")
dump_json({"lung_labels": lung_labels, "tumor_label": tumor_label, "anatomy_list": anatomy_list}, runtime / "resolved_labels.json")
PY_PREP
import json, os
from pathlib import Path

out = Path(os.environ["OUT_ABS"])
pairs = []
for img in sorted(out.glob("sample_*_image.nii.gz")):
    lab = out / img.name.replace("_image.nii.gz", "_label.nii.gz")
    if lab.exists():
        pairs.append((img, lab))

if not pairs:
    raise SystemExit(f"No generated image/label pair found in {out}")

keep = {pairs[0][0].resolve(), pairs[0][1].resolve()}
for p in out.glob("sample_*.nii.gz"):
    if p.resolve() not in keep:
        p.unlink()

manifest = {
    "image": pairs[0][0].name,
    "label": pairs[0][1].name,
    "output_dir": str(out),
    "model_variant": "rflow-ct",
    "network": "rflow"
}
with open(out / "_runtime" / "manifest.json", "w") as f:
    json.dump(manifest, f, indent=2, sort_keys=True)
PY_CLEAN
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=1

```bash
bash -lc 'set -euo pipefail; WB_ROOT="$PWD"; OUT="runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/without/repeat_2"; REQ="runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json"; NV_ROOT="${NV_GENERATE_ROOT:-$WB_ROOT/.workbench_data/upstreams/NV-Generate-CTMR}"; mkdir -p "$OUT/runtime_configs" "$OUT/monai_data"; PYTHONDONTWRITEBYTECODE=1 python - <<'"'"'PY'"'"'
import json, os, shutil
from pathlib import Path
wb = Path(os.environ.get("WB_ROOT", ".")).resolve()
out = wb / "runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/without/repeat_2"
req_path = wb / "runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json"
nv = Path(os.environ.get("NV_GENERATE_ROOT", wb / ".workbench_data/upstreams/NV-Generate-CTMR")).resolve()
runtime = out / "runtime_configs"
runtime.mkdir(parents=True, exist_ok=True)
req = json.loads(req_path.read_text()) if req_path.exists() else {}
src_infer = nv / "configs/config_infer.json"
cfg = json.loads(src_infer.read_text())
label_dict = json.loads((nv / "configs/label_dict.json").read_text())
label_names = [str(k) for k in label_dict.keys()]
def pick(candidates, fallback):
    low = {n.lower(): n for n in label_names}
    for c in candidates:
        if c.lower() in low:
            return low[c.lower()]
    for n in label_names:
        ln = n.lower()
        if all(tok in ln for tok in candidates[0].lower().split()):
            return n
    return fallback
lung = pick(["lung", "lungs"], "lung")
tumor = pick(["lung tumor", "lung tumour", "tumor", "tumour"], "lung tumor")
cfg.update({
    "body_region": req.get("body_region", ["chest"]),
    "anatomy_list": req.get("anatomy_list", [lung, tumor]),
    "controllable_anatomy_size": req.get("controllable_anatomy_size", []),
    "output_size": req.get("output_size", [256, 256, 256]),
    "spacing": req.get("spacing", [1.5, 1.5, 1.5]),
    "modality": req.get("modality", 1),
    "output_dir": str(out),
    "num_inference_steps": req.get("num_inference_steps", 30),
    "mask_generation_num_inference_steps": req.get("mask_generation_num_inference_steps", 1000),
    "cfg_guidance_scale": req.get("cfg_guidance_scale", cfg.get("cfg_guidance_scale", 0))
})
for k in ("num_samples", "num_images", "num_output_samples", "n_samples", "batch_size"):
    if k in cfg:
        cfg[k] = 1
(runtime / "config_infer.json").write_text(json.dumps(cfg, indent=2) + "\n")
PY
export MONAI_DATA_DIRECTORY="$WB_ROOT/$OUT/monai_data"; cd "$NV_ROOT"; PYTHONDONTWRITEBYTECODE=1 python -m scripts.inference -t ./configs/config_network_rflow.json -i "$WB_ROOT/$OUT/runtime_configs/config_infer.json" -e ./configs/environment_rflow-ct.json --random-seed 0 --version rflow-ct; cd "$WB_ROOT"; python - <<'"'"'PY'"'"'
from pathlib import Path
out = Path("runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/without/repeat_2")
pairs = []
for img in sorted(out.glob("*_image.nii.gz")):
    lab = out / img.name.replace("_image.nii.gz", "_label.nii.gz")
    if lab.exists():
        pairs.append((img, lab))
if not pairs:
    raise SystemExit("No paired image/label outputs found")
keep = set(map(str, pairs[0]))
for p in list(out.glob("*_image.nii.gz")) + list(out.glob("*_label.nii.gz")):
    if str(p) not in keep:
        p.unlink()
PY'
```

Repeat 3: score 4/5, passed=no, steps=unresolved, exit=None

```bash
export WBROOT="$PWD" OUT_REL="runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/without/repeat_3" REQ_REL="runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json" NVROOT="${NV_GENERATE_ROOT:?Set NV_GENERATE_ROOT to the NV-Generate-CTMR checkout}" && mkdir -p "$OUT_REL/runtime" "$OUT_REL/monai_data" "$OUT_REL/cache" && rm -f "$OUT_REL"/sample_*_image.nii.gz "$OUT_REL"/sample_*_label.nii.gz && python - <<'PY_STAGE' && (cd "$NVROOT" && MONAI_DATA_DIRECTORY="$WBROOT/$OUT_REL/monai_data" XDG_CACHE_HOME="$WBROOT/$OUT_REL/cache" PYTHONDONTWRITEBYTECODE=1 python -m scripts.inference -t "$WBROOT/$OUT_REL/runtime/config_network_rflow.json" -i "$WBROOT/$OUT_REL/runtime/config_infer.json" -e "$WBROOT/$OUT_REL/runtime/environment_rflow-ct.json" --random-seed "$(cat "$WBROOT/$OUT_REL/runtime/random_seed.txt")" --version rflow-ct) && python - <<'PY_CHECK'
import json, os, shutil
from pathlib import Path

wb = Path(os.environ["WBROOT"]).resolve()
nv = Path(os.environ["NVROOT"]).resolve()
out = wb / os.environ["OUT_REL"]
req_path = wb / os.environ["REQ_REL"]
runtime = out / "runtime"
runtime.mkdir(parents=True, exist_ok=True)

req = json.loads(req_path.read_text()) if req_path.exists() else {}
if req_path.exists():
    shutil.copy2(req_path, runtime / "request.json")

for name in ("config_network_rflow.json", "environment_rflow-ct.json"):
    shutil.copy2(nv / "configs" / name, runtime / name)

infer = json.loads((nv / "configs" / "config_infer.json").read_text())

def label_names_from_label_dict(path):
    obj = json.loads(path.read_text())
    names = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and not k.isdigit():
                names.append(k)
            if isinstance(v, str):
                names.append(v)
    elif isinstance(obj, list):
        names.extend(x for x in obj if isinstance(x, str))
    return list(dict.fromkeys(names))

names = label_names_from_label_dict(nv / "configs" / "label_dict.json")
def norm(s): return str(s).lower().replace("_", " ").replace("-", " ").strip()
def exact(w):
    for n in names:
        if norm(n) == norm(w):
            return n
    return None
def first_with(*words):
    for n in names:
        t = norm(n)
        if all(w in t for w in words):
            return n
    return None

lung = exact("lung")
lung_tumor = exact("lung tumor") or first_with("lung", "tumor") or exact("tumor") or first_with("tumor")
anatomy_list = []
 if False else None
if lung:
    anatomy_list.append(lung)
else:
    anatomy_list.extend([n for n in names if "lung" in norm(n) and "tumor" not in norm(n)][:6])
anatomy_list.append(lung_tumor or "lung tumor")
anatomy_list = list(dict.fromkeys(anatomy_list))

infer.update({
    "body_region": req.get("body_region", ["chest"]),
    "anatomy_list": req.get("anatomy_list", anatomy_list),
    "controllable_anatomy_size": req.get("controllable_anatomy_size", []),
    "output_size": req.get("output_size", req.get("dim", [256, 256, 256])),
    "spacing": req.get("spacing", [1.5, 1.5, 1.5]),
    "modality": req.get("modality", 1),
    "num_inference_steps": 30,
    "mask_generation_num_inference_steps": 1000,
    "output_dir": str(out),
})
for k in ("num_samples", "num_images", "num_output_samples", "n_samples", "n_outputs"):
    if k in infer:
        infer[k] = 1

(runtime / "config_infer.json").write_text(json.dumps(infer, indent=2) + "\n")
(runtime / "random_seed.txt").write_text(str(int(req.get("random_seed", req.get("seed", 3)))) + "\n")
PY_STAGE
import os
from pathlib import Path
out = Path(os.environ["WBROOT"]).resolve() / os.environ["OUT_REL"]
imgs = sorted(out.glob("sample_*_image.nii.gz"))
labs = sorted(out.glob("sample_*_label.nii.gz"))
if len(imgs) != 1 or len(labs) != 1:
    raise SystemExit(f"expected exactly one generated image and one label in {out}, found {len(imgs)} images and {len(labs)} labels")
print(f"generated image: {imgs[0]}")
print(f"generated label: {labs[0]}")
PY_CHECK
```

### Opus 4.7, with arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-$HOME/nv-generate-ctmr}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-ct-rflow/scripts/run_rflow_ct.py runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json --output-dir runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/opus/with/repeat_1 --random-seed 1 --version rflow-ct --yes
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-$HOME/nv-generate-ctmr}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-ct-rflow/scripts/run_rflow_ct.py runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json --output-dir runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/opus/with/repeat_2 --random-seed 2 --version rflow-ct --yes
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-$HOME/nv-generate-ctmr}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-ct-rflow/scripts/run_rflow_ct.py runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json --output-dir runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/opus/with/repeat_3 --random-seed 3 --version rflow-ct --yes
```

### Opus 4.7, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 2/5, passed=no, steps=unresolved, exit=None

```bash
set -euo pipefail && OUT="runs/with_vs_without/nv_generate_ct_rflow_codex_opus/opus/without/repeat_1" && REQ="runs/with_vs_without/_inputs/nv_generate_ct_rflow/request.json" && SRC="$NV_GENERATE_ROOT" && mkdir -p "$OUT/configs" "$OUT/output" && cat "$REQ" && cp "$SRC/configs/config_network_rflow.json" "$OUT/configs/config_network_rflow.json" && cp "$SRC/configs/environment_rflow-ct.json" "$OUT/configs/environment_rflow-ct.json" && python -c "
import json, os
src=os.environ['SRC']; out=os.environ['OUT']
cfg=json.load(open(os.path.join(src,'configs','config_infer.json')))
cfg['body_region']=['chest']
cfg['anatomy_list']=['lung','lung tumor']
cfg['controllable_anatomy_size']=[['lung tumor',0.3]]
cfg['output_size']=[256,256,256]
cfg['spacing']=[1.5,1.5,1.5]
cfg['modality']='ct'
cfg['num_inference_steps']=30
cfg['mask_generation_num_inference_steps']=1000
cfg['num_output_samples']=1
cfg['output_dir']=os.path.abspath(os.path.join(out,'output'))
json.dump(cfg, open(os.path.join(out,'configs','config_infer.json'),'w'), indent=2)
" && SRC="$SRC" OUT="$OUT" env MONAI_DATA_DIRECTORY="$OUT/temp_work_dir" PYTHONPATH="$SRC" python -m scripts.inference -t "$OUT/configs/config_network_rflow.json" -i "$OUT/configs/config_infer.json" -e "$OUT/configs/environment_rflow-ct.json" --random-seed 0 --version rflow-ct
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=1

```bash
set -euo pipefail && REQ=runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json && OUT=runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/opus/without/repeat_2 && mkdir -p "$OUT/configs" "$OUT/output" && : "${NV_GENERATE_ROOT:?must be set}" && cp "$NV_GENERATE_ROOT/configs/config_network_rflow.json" "$OUT/configs/config_network_rflow.json" && cp "$NV_GENERATE_ROOT/configs/environment_rflow-ct.json" "$OUT/configs/environment_rflow-ct.json" && python -c "
import json, os
req = json.load(open('$REQ'))
print('request:', json.dumps(req, indent=2))
cfg = json.load(open(os.path.join(os.environ['NV_GENERATE_ROOT'], 'configs/config_infer.json')))
cfg['body_region'] = ['chest']
cfg['anatomy_list'] = ['lung', 'lung tumor']
cfg['controllable_anatomy_size'] = [['lung tumor', 0.3]]
cfg['output_size'] = [256, 256, 256]
cfg['spacing'] = [1.5, 1.5, 1.5]
cfg['modality'] = 1
cfg['num_inference_steps'] = 30
cfg['mask_generation_num_inference_steps'] = 1000
cfg['num_output_samples'] = 1
json.dump(cfg, open('$OUT/configs/config_infer.json', 'w'), indent=2)
env = json.load(open('$OUT/configs/environment_rflow-ct.json'))
env['output_dir'] = os.path.abspath('$OUT/output')
json.dump(env, open('$OUT/configs/environment_rflow-ct.json', 'w'), indent=2)
" && export MONAI_DATA_DIRECTORY="$OUT/monai_tmp" && mkdir -p "$MONAI_DATA_DIRECTORY" && cd "$NV_GENERATE_ROOT" && python -m scripts.inference -t "$OLDPWD/$OUT/configs/config_network_rflow.json" -i "$OLDPWD/$OUT/configs/config_infer.json" -e "$OLDPWD/$OUT/configs/environment_rflow-ct.json" --random-seed 2 --version rflow-ct
```

Repeat 3: score 2/5, passed=no, steps=unresolved, exit=None

```bash
OUT=runs/with_vs_without/nv_generate_ct_rflow_codex_opus/opus/without/repeat_3 && REQ=runs/with_vs_without/_inputs/nv_generate_ct_rflow/request.json && NV_ROOT="${NV_GENERATE_ROOT:?set NV_GENERATE_ROOT to upstream NV-Generate-CTMR repo}" && mkdir -p "$OUT/configs" "$OUT/output" && cat "$REQ" && cp "$NV_ROOT/configs/config_infer.json" "$OUT/configs/config_infer.json" && python -c "import json,sys; p='$OUT/configs/config_infer.json'; c=json.load(open(p)); c['body_region']=['chest']; c['anatomy_list']=['lung','lung tumor']; c['controllable_anatomy_size']=[['lung tumor',0.3]]; c['output_size']=[256,256,256]; c['spacing']=[1.5,1.5,1.5]; c['modality']='ct'; c['num_inference_steps']=30; c['mask_generation_num_inference_steps']=1000; c['num_output_samples']=1; c['cfg_guidance_scale']=0; json.dump(c,open(p,'w'),indent=2)" && cp "$NV_ROOT/configs/environment_rflow-ct.json" "$OUT/configs/environment_rflow-ct.json" && python -c "import json,os; p='$OUT/configs/environment_rflow-ct.json'; e=json.load(open(p)); e['output_dir']=os.path.abspath('$OUT/output'); json.dump(e,open(p,'w'),indent=2)" && cd "$NV_ROOT" && MONAI_DATA_DIRECTORY="./temp_work_dir" python -m scripts.inference -t ./configs/config_network_rflow.json -i "$OLDPWD/$OUT/configs/config_infer.json" -e "$OLDPWD/$OUT/configs/environment_rflow-ct.json" --random-seed 0 --version rflow-ct
```

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `examples/studies/with_vs_without_skill/nv_generate_ct_rflow_codex_opus/` |
| Generated outputs | `runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_generate_ct_rflow_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
