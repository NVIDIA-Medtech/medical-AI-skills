# `nv_generate_ct_rflow`: Codex/Opus LLM+SKILL.md vs LLM+README

Status: strict audit passed for refreshed artifacts on May 28, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

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
| GPT-5.5 / Codex | without | 4.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | None (2); 1 (1) | blocked unsafe command fragment: rm (2); exit 1 (1) | T5: blocked unsafe command fragment: rm (2); T5: exit 1 (1) |
| Opus 4.7 | with | 4.3/5 | 1/3 | mean 0.0; unresolved 2; values [unresolved, unresolved, 0] | 1 (2); 0 (1) | exit 1 (2); image shape=(256, 256, 256); label shape=(256, 256, 256) (1) | T5: exit 1 (2) |
| Opus 4.7 | without | 2.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | None (3) | command does not reference the expected output directory (3) | T2: user input path marker (3); T4: output dir marker (3); T5: command does not reference the expected output directory (3) |

## Analysis

SKILL.md paired advantage: the with-skill arms passed 4/6 backend-repeat trials with an average score of 4.7/5; the README-only arms passed 0/6 backend-repeat trials with an average score of 3.0/5.

SKILL.md paired advantage: SKILL.md wins 6/6 matched backend-repeat pairs, README-only wins 0/6, and 0/6 are ties. Pass/fail is the primary outcome; score breaks ties only when pass status is equal. Exact one-sided sign-test p=0.01562 across 6 decisive pair(s).

Outcome-support gate: Supports SKILL.md advantage. SKILL.md wins 6/6 matched pair(s); README-only wins 0/6; sign-test p=0.01562.

Each backend/arm/skill configuration was repeated three times. A repeat is independent: it has its own output directory, and each execution attempt inside the repeat creates a fresh venv before running the generated command. Dependency and model download caches are shared only as documented test-environment caches under `.workbench_data/with_vs_without_cache` (`PIP_CACHE_DIR=.workbench_data/with_vs_without_cache/pip`, `HF_HOME=.workbench_data/with_vs_without_cache/huggingface`, `HF_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `HUGGINGFACE_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `TRANSFORMERS_CACHE=.workbench_data/with_vs_without_cache/huggingface/transformers`, `TORCH_HOME=.workbench_data/with_vs_without_cache/torch`, `XDG_CACHE_HOME=.workbench_data/with_vs_without_cache/xdg`, `CONDA_PKGS_DIRS=.workbench_data/with_vs_without_cache/conda_pkgs`, `UV_CACHE_DIR=.workbench_data/with_vs_without_cache/uv`, `CUDA_CACHE_PATH=.workbench_data/with_vs_without_cache/cuda`, `NUMBA_CACHE_DIR=.workbench_data/with_vs_without_cache/numba`).

The main baseline uses `max_correction_steps=0`: each repeat sends one prompt, executes the extracted command once, and records pass/fail, runtime, tokens, and deterministic failure analysis. The repair-loop implementation remains available for separate diagnostic experiments, but it is not part of this comparison.

With-skill failures: Opus 4.7: T5: exit 1 (2).

The README-only commands did not pass tier 5. Typical failure modes were unsafe generated shell cleanup, missing schema fields, missing model/control details, or upstream commands that did not execute cleanly from Medical AI Skills root.

Tier 2 is intentionally strict: a command only earns it if it uses the staged user input path `runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json`.

## Token Profiling

Token counts are provider-reported values saved in each repeat JSON. Reasoning tokens are shown only when the provider returned that subfield and are a subset of completion tokens, not an additional cost to add to total tokens. Execution time is averaged only across repeats that reached command execution; no-command-extracted repeats still count toward token totals.

| Backend | Arm | Repeats | Passes | Attempts | Prompt tokens | Completion tokens | Reasoning tokens | Total tokens | Mean total/repeat | Executed | Mean exec s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GPT-5.5 / Codex | with | 3 | 3 | 3 | 9,102 | 1,906 | 1,519 | 11,008 | 3,669.3 | 3 | 114.7 |
| GPT-5.5 / Codex | without | 3 | 0 | 3 | 8,994 | 17,924 | 14,335 | 26,918 | 8,972.7 | 1 | 0.0 |
| Opus 4.7 | with | 3 | 1 | 3 | 15,501 | 608 | 0 | 16,109 | 5,369.7 | 3 | 37.9 |
| Opus 4.7 | without | 3 | 0 | 3 | 14,301 | 2,675 | 0 | 16,976 | 5,658.7 | 0 | n/a |

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
| 2 | 0 | 4/5 | no | None | T5: blocked unsafe command fragment: rm | tier_5: blocked unsafe command fragment: rm Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: blocked unsafe command fragment: rm Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
| 3 | 0 | 4/5 | no | None | T5: blocked unsafe command fragment: rm | tier_5: blocked unsafe command fragment: rm Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: blocked unsafe command fragment: rm Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |

### Opus 4.7, with arm

| Repeat | Step | Score | Passed | Exit | Failed tiers | Why it did not work |
|---:|---:|---:|---|---|---|---|
| 1 | 0 | 4/5 | no | 1 | T5: exit 1 | tier_5: exit 1 Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>nonzero_exit: Command exited 1. Repair: Use stderr/stdout to repair setup, paths, arguments, or runtime package installation. |
| 2 | 0 | 4/5 | no | 1 | T5: exit 1 | tier_5: exit 1 Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>nonzero_exit: Command exited 1. Repair: Use stderr/stdout to repair setup, paths, arguments, or runtime package installation. |
| 3 | 0 | 5/5 | yes | 0 | none | none |

### Opus 4.7, without arm

| Repeat | Step | Score | Passed | Exit | Failed tiers | Why it did not work |
|---:|---:|---:|---|---|---|---|
| 1 | 0 | 2/5 | no | None | T2: user input path marker; T4: output dir marker; T5: command does not reference the expected output directory | tier_2: user input path marker Repair: Use the staged user input path under runs/with_vs_without_nv/_inputs/.<br>tier_4: output dir marker Repair: Write outputs under the exact arm-specific output directory.<br>tier_5: command does not reference the expected output directory Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference the expected output directory Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
| 2 | 0 | 2/5 | no | None | T2: user input path marker; T4: output dir marker; T5: command does not reference the expected output directory | tier_2: user input path marker Repair: Use the staged user input path under runs/with_vs_without_nv/_inputs/.<br>tier_4: output dir marker Repair: Write outputs under the exact arm-specific output directory.<br>tier_5: command does not reference the expected output directory Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference the expected output directory Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
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
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-$HOME/nv-generate-ctmr}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-ct-rflow/scripts/run_rflow_ct.py runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json --output-dir runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/with/repeat_2 --random-seed 2 --version rflow-ct --yes
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-$HOME/nv-generate-ctmr}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-ct-rflow/scripts/run_rflow_ct.py runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json --output-dir runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/with/repeat_3 --random-seed 3 --version rflow-ct --yes
```

### GPT-5.5 / Codex, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 4/5, passed=no, steps=unresolved, exit=1

```bash
REPO_ROOT="$PWD" && REQUEST="runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json" && OUT="runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/without/repeat_1" && GEN_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && test -f "$REQUEST" && test -d "$GEN_ROOT" && mkdir -p "$OUT/runtime" "$OUT/monai_data" && find "$OUT" -maxdepth 1 -type f \( -name 'sample_*_image.nii.gz' -o -name 'sample_*_label.nii.gz' \) -delete && GEN_ROOT="$GEN_ROOT" OUT="$OUT" REQUEST="$REQUEST" REPO_ROOT="$REPO_ROOT" python - <<'PY' && (cd "$GEN_ROOT" && PYTHONDONTWRITEBYTECODE=1 MONAI_DATA_DIRECTORY="$REPO_ROOT/$OUT/monai_data" python -m scripts.inference -t ./configs/config_network_rflow.json -i "$REPO_ROOT/$OUT/runtime/config_infer_chest_lung_tumor.json" -e ./configs/environment_rflow-ct.json --random-seed 0 --version rflow-ct)
import json, os, re
from pathlib import Path

gen = Path(os.environ["GEN_ROOT"]).resolve()
out = Path(os.environ["OUT"]).resolve()
runtime = out / "runtime"
runtime.mkdir(parents=True, exist_ok=True)

src_cfg = gen / "configs" / "config_infer.json"
label_json = gen / "configs" / "label_dict.json"

cfg = json.loads(src_cfg.read_text())
label_obj = json.loads(label_json.read_text())

names = set()
def collect_strings(x):
    if isinstance(x, dict):
        for k, v in x.items():
            if isinstance(k, str) and not k.strip().lstrip("-").isdigit():
                names.add(k)
            collect_strings(v)
    elif isinstance(x, list):
        for v in x:
            collect_strings(v)
    elif isinstance(x, str) and not x.strip().lstrip("-").isdigit():
        names.add(x)

collect_strings(label_obj)

def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

by_norm = {}
for n in sorted(names):
    by_norm.setdefault(norm(n), n)

lung_priority = ["lung", "lungs", "left lung", "right lung", "lung left", "lung right", "lung l", "lung r"]
lung_names = []
for p in lung_priority:
    if p in by_norm and by_norm[p] not in lung_names:
        lung_names.append(by_norm[p])
if not lung_names:
    lung_names = [n for n in sorted(names) if "lung" in norm(n).split() and not any(t in norm(n).split() for t in ("tumor", "tumour", "lesion", "mass"))]

tumor_names = [
    n for n in sorted(names)
    if "lung" in norm(n).split() and any(t in norm(n).split() for t in ("tumor", "tumour", "lesion", "mass"))
]
if not tumor_names:
    tumor_names = [
        n for n in sorted(names)
        if any(t in norm(n).split() for t in ("tumor", "tumour", "lesion", "mass"))
    ]

if not lung_names:
    raise SystemExit("Could not identify a lung label in configs/label_dict.json")
if not tumor_names:
    raise SystemExit("Could not identify a tumor/lesion label in configs/label_dict.json")

tumor_name = tumor_names[0]
anatomy_list = []
for n in lung_names + [tumor_name]:
    if n not in anatomy_list:
        anatomy_list.append(n)

cfg["body_region"] = ["chest", "thorax"]
cfg["anatomy_list"] = anatomy_list
cfg["controllable_anatomy_size"] = [[tumor_name, 0.5]]
cfg["output_size"] = [256, 256, 256]
cfg["spacing"] = [1.5, 1.5, 1.5]
cfg["modality"] = 1
cfg["num_inference_steps"] = 30
cfg["mask_generation_num_inference_steps"] = 1000
cfg["cfg_guidance_scale"] = 1.0
cfg["output_dir"] = str(out)

for k in ("num_output_samples", "num_samples", "n_samples", "num_images", "num_pairs"):
    if k in cfg:
        cfg[k] = 1

(runtime / "config_infer_chest_lung_tumor.json").write_text(json.dumps(cfg, indent=2) + "\n")
PY
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=None

```bash
OUT="runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/without/repeat_2" && UP=".workbench_data/upstreams/NV-Generate-CTMR" && REQ="runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json" && test -f "$REQ" && rm -rf "$OUT" && mkdir -p "$OUT/runtime" "$OUT/monai_data" && python - "$UP" "$OUT" <<'PY' && MONAI_DATA_DIRECTORY="$OUT/monai_data" PYTHONPATH="$UP${PYTHONPATH:+:$PYTHONPATH}" python -m scripts.inference -t "$OUT/runtime/config_network_rflow.json" -i "$OUT/runtime/config_infer.json" -e "$OUT/runtime/environment_rflow-ct.json" --random-seed 0 --version rflow-ct
import json, os, shutil, sys
up, out = sys.argv[1], sys.argv[2]
rt = os.path.join(out, "runtime")
shutil.copyfile(os.path.join(up, "configs", "config_network_rflow.json"), os.path.join(rt, "config_network_rflow.json"))

with open(os.path.join(up, "configs", "config_infer.json")) as f:
    infer = json.load(f)
infer.update({
    "num_output_samples": 1,
    "body_region": ["chest", "thorax"],
    "anatomy_list": ["lung", "lung tumor"],
    "controllable_anatomy_size": [["lung", 0.5], ["lung tumor", 0.35]],
    "output_size": [256, 256, 256],
    "spacing": [1.5, 1.5, 1.5],
    "modality": 1,
    "num_inference_steps": 30,
    "mask_generation_num_inference_steps": 1000,
    "cfg_guidance_scale": 1.0,
    "output_dir": out
})
with open(os.path.join(rt, "config_infer.json"), "w") as f:
    json.dump(infer, f, indent=2)

with open(os.path.join(up, "configs", "environment_rflow-ct.json")) as f:
    env = json.load(f)

def stage_path(v):
    if not isinstance(v, str) or os.path.isabs(v):
        return v
    vv = v[2:] if v.startswith("./") else v
    if vv.startswith(("models/", "configs/", "data/", "dataset/", "datasets/")) or vv.endswith((".pt", ".pth", ".json", ".nii.gz")):
        return os.path.join(up, vv)
    return v

def walk(x):
    if isinstance(x, dict):
        return {k: walk(stage_path(v)) for k, v in x.items()}
    if isinstance(x, list):
        return [walk(v) for v in x]
    return stage_path(x)

env = walk(env)
with open(os.path.join(rt, "environment_rflow-ct.json"), "w") as f:
    json.dump(env, f, indent=2)
PY
```

Repeat 3: score 4/5, passed=no, steps=unresolved, exit=None

```bash
OUT="runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/without/repeat_3" && REQ="runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json" && ROOT="$(pwd -P)" && UP="$(cd "${NV_GENERATE_ROOT:?NV_GENERATE_ROOT must point to the NV-Generate-CTMR upstream checkout}" && pwd -P)" && rm -rf "$OUT" && mkdir -p "$OUT/runtime" && { python - "$REQ" "$OUT" "$ROOT" "$UP" <<'PY'
import json, os, re, shutil, sys
from pathlib import Path

req_path, out_rel, root, up = map(Path, sys.argv[1:5])
if not req_path.is_file():
    raise FileNotFoundError(f"request.json not found: {req_path}")

out_abs = (root / out_rel).resolve()
runtime = out_abs / "runtime"
runtime.mkdir(parents=True, exist_ok=True)

with open(req_path) as f:
    request = json.load(f)

def find_key(obj, names):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower().replace("-", "_") in names:
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

def norm(s):
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())

label_dict_path = up / "configs" / "label_dict.json"
with open(label_dict_path) as f:
    raw_labels = json.load(f)

label_names = []
if isinstance(raw_labels, dict):
    for k, v in raw_labels.items():
        if isinstance(k, str) and not k.isdigit():
            label_names.append(k)
        if isinstance(v, str):
            label_names.append(v)
label_names = list(dict.fromkeys(label_names))
if not label_names:
    raise RuntimeError(f"Could not infer label names from {label_dict_path}")

def pick_label(pred, prefer_exact=()):
    exact = [name for name in label_names if norm(name) in {norm(x) for x in prefer_exact}]
    if exact:
        return exact[0]
    matches = [name for name in label_names if pred(norm(name))]
    if not matches:
        return None
    return sorted(matches, key=lambda x: (len(norm(x)), norm(x)))[0]

lung_label = pick_label(lambda n: ("lung" in n and not any(t in n for t in ("tumor", "lesion", "nodule", "mass"))), ("lung", "lungs"))
tumor_label = pick_label(lambda n: ("lung" in n and any(t in n for t in ("tumor", "lesion", "nodule", "mass"))), ("lung_tumor", "lung tumor", "pulmonary_tumor", "pulmonary tumor"))
if tumor_label is None:
    tumor_label = pick_label(lambda n: any(t in n for t in ("tumor", "lesion", "nodule", "mass")), ("tumor", "lesion"))
if lung_label is None or tumor_label is None or lung_label == tumor_label:
    raise RuntimeError(f"Could not select distinct lung/tumor labels from {label_dict_path}; selected lung={lung_label!r}, tumor={tumor_label!r}")

shutil.copy2(up / "configs" / "config_network_rflow.json", runtime / "config_network_rflow.json")

with open(up / "configs" / "environment_rflow-ct.json") as f:
    env = json.load(f)

def absolutize(x):
    if isinstance(x, dict):
        return {k: absolutize(v) for k, v in x.items()}
    if isinstance(x, list):
        return [absolutize(v) for v in x]
    if isinstance(x, str):
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", x) or os.path.isabs(x):
            return x
        if x.startswith(("./", "../")) or "/" in x:
            return str((up / x).resolve())
    return x

with open(runtime / "environment_rflow-ct.json", "w") as f:
    json.dump(absolutize(env), f, indent=2)

with open(up / "configs" / "config_infer.json") as f:
    infer = json.load(f)

output_size = find_key(request, {"output_size", "dim", "dims", "dimensions", "shape"}) or [256, 256, 256]
spacing = find_key(request, {"spacing", "voxel_spacing"}) or [1.5, 1.5, 1.5]
seed = find_key(request, {"random_seed", "seed"}) or 0

infer.update({
    "body_region": ["chest"],
    "anatomy_list": [lung_label, tumor_label],
    "controllable_anatomy_size": [[lung_label, 0.70], [tumor_label, 0.35]],
    "output_size": output_size,
    "spacing": spacing,
    "modality": 1,
    "num_inference_steps": 30,
    "mask_generation_num_inference_steps": 1000,
    "cfg_guidance_scale": infer.get("cfg_guidance_scale", 1.0) or 1.0,
    "output_dir": str(out_abs),
})
for k in ("num_samples", "num_sample", "n_samples", "num_images", "num_outputs", "num_output_images", "sample_num"):
    if k in infer:
        infer[k] = 1

with open(runtime / "config_infer.json", "w") as f:
    json.dump(infer, f, indent=2)
(runtime / "random_seed.txt").write_text(str(int(seed)))
PY
} && mkdir -p "$ROOT/$OUT/runtime/monai" && PYTHONDONTWRITEBYTECODE=1 MONAI_DATA_DIRECTORY="$ROOT/$OUT/runtime/monai" PYTHONPATH="$UP${PYTHONPATH:+:$PYTHONPATH}" python -m scripts.inference -t "$ROOT/$OUT/runtime/config_network_rflow.json" -i "$ROOT/$OUT/runtime/config_infer.json" -e "$ROOT/$OUT/runtime/environment_rflow-ct.json" --random-seed "$(cat "$ROOT/$OUT/runtime/random_seed.txt")" --version rflow-ct && { python - "$OUT" <<'PY'
import sys
from pathlib import Path

out = Path(sys.argv[1])
imgs = sorted(out.glob("*_image.nii.gz"))
labs = sorted(out.glob("*_label.nii.gz"))

def prefix(p, suffix):
    n = p.name
    return n[:-len(suffix)] if n.endswith(suffix) else None

lab_by_prefix = {prefix(p, "_label.nii.gz"): p for p in labs if prefix(p, "_label.nii.gz")}
pairs = [(prefix(i, "_image.nii.gz"), i, lab_by_prefix.get(prefix(i, "_image.nii.gz"))) for i in imgs if prefix(i, "_image.nii.gz") in lab_by_prefix]
pairs = [(pre, i, l) for pre, i, l in pairs if l is not None]
if not pairs:
    raise RuntimeError(f"No paired *_image.nii.gz and *_label.nii.gz outputs found in {out}")

pre, keep_img, keep_lab = max(pairs, key=lambda x: max(x[1].stat().st_mtime, x[2].stat().st_mtime))
for p in imgs + labs:
    if p not in {keep_img, keep_lab}:
        p.unlink()
print(f"kept paired output: {keep_img} and {keep_lab}")
PY
}
```

### Opus 4.7, with arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 4/5, passed=no, steps=unresolved, exit=1

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-$HOME/nv-generate-ctmr}" && python skills/nv-generate-ct-rflow/scripts/run_rflow_ct.py runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json --output-dir runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/opus/with/repeat_1 --random-seed 1 --version rflow-ct --yes
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=1

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-$HOME/nv-generate-ctmr}" && python skills/nv-generate-ct-rflow/scripts/run_rflow_ct.py runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json --output-dir runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/opus/with/repeat_2 --random-seed 2 --version rflow-ct --yes
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-$HOME/nv-generate-ctmr}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-ct-rflow/scripts/run_rflow_ct.py runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json --output-dir runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/opus/with/repeat_3 --random-seed 3 --version rflow-ct --yes
```

### Opus 4.7, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 2/5, passed=no, steps=unresolved, exit=None

```bash
set -euo pipefail && OUT=runs/with_vs_without/nv_generate_ct_rflow_codex_opus/opus/without/repeat_1 && REQ=runs/with_vs_without/_inputs/nv_generate_ct_rflow/request.json && mkdir -p "$OUT/configs" "$OUT/output" && cat "$REQ" && cp "$NV_GENERATE_ROOT/configs/config_infer.json" "$OUT/configs/config_infer.json" && python -c "
import json, sys
req = json.load(open('$REQ'))
cfg = json.load(open('$OUT/configs/config_infer.json'))
cfg['body_region'] = req.get('body_region', ['chest'])
cfg['anatomy_list'] = req.get('anatomy_list', ['lung', 'lung tumor'])
cfg['controllable_anatomy_size'] = req.get('controllable_anatomy_size', [['lung tumor', 0.3]])
cfg['output_size'] = req.get('output_size', [256, 256, 256])
cfg['spacing'] = req.get('spacing', [1.5, 1.5, 1.5])
cfg['modality'] = req.get('modality', 'ct')
cfg['num_inference_steps'] = 30
cfg['mask_generation_num_inference_steps'] = 1000
cfg['num_output_samples'] = 1
json.dump(cfg, open('$OUT/configs/config_infer.json', 'w'), indent=2)
print(json.dumps(cfg, indent=2))
" && cp "$NV_GENERATE_ROOT/configs/environment_rflow-ct.json" "$OUT/configs/environment_rflow-ct.json" && python -c "
import json, os
p = '$OUT/configs/environment_rflow-ct.json'
env = json.load(open(p))
env['output_dir'] = os.path.abspath('$OUT/output')
json.dump(env, open(p, 'w'), indent=2)
" && cd "$NV_GENERATE_ROOT" && export MONAI_DATA_DIRECTORY="./temp_work_dir" && python -m scripts.inference -t ./configs/config_network_rflow.json -i "$OLDPWD/$OUT/configs/config_infer.json" -e "$OLDPWD/$OUT/configs/environment_rflow-ct.json" --random-seed 0 --version rflow-ct
```

Repeat 2: score 2/5, passed=no, steps=unresolved, exit=None

```bash
set -euo pipefail && OUT="runs/with_vs_without/nv_generate_ct_rflow_codex_opus/opus/without/repeat_2" && REQ="runs/with_vs_without/_inputs/nv_generate_ct_rflow/request.json" && mkdir -p "$OUT/configs" "$OUT/output" && cp "$NV_GENERATE_ROOT"/configs/*.json "$OUT/configs/" && python -c "
import json, sys
req = json.load(open('$REQ'))
cfg_path = '$OUT/configs/config_infer.json'
cfg = json.load(open(cfg_path))
cfg['body_region'] = req.get('body_region', ['chest'])
cfg['anatomy_list'] = req.get('anatomy_list', ['lung', 'lung tumor'])
cfg['controllable_anatomy_size'] = req.get('controllable_anatomy_size', [['lung tumor', 0.3]])
cfg['output_size'] = req.get('output_size', [256, 256, 256])
cfg['spacing'] = req.get('spacing', [1.5, 1.5, 1.5])
cfg['modality'] = req.get('modality', 1)
cfg['num_inference_steps'] = 30
cfg['mask_generation_num_inference_steps'] = 1000
cfg['num_output_samples'] = 1
json.dump(cfg, open(cfg_path, 'w'), indent=2)
env_path = '$OUT/configs/environment_rflow-ct.json'
env = json.load(open(env_path))
env['output_dir'] = '$OUT/output'
json.dump(env, open(env_path, 'w'), indent=2)
print('staged configs')
" && cd "$NV_GENERATE_ROOT" && export MONAI_DATA_DIRECTORY="$OLDPWD/$OUT/temp_work_dir" && mkdir -p "$MONAI_DATA_DIRECTORY" && python -m scripts.inference -t "$OLDPWD/$OUT/configs/config_network_rflow.json" -i "$OLDPWD/$OUT/configs/config_infer.json" -e "$OLDPWD/$OUT/configs/environment_rflow-ct.json" --random-seed 2 --version rflow-ct
```

Repeat 3: score 2/5, passed=no, steps=unresolved, exit=None

```bash
set -euo pipefail && OUT="runs/with_vs_without/nv_generate_ct_rflow_codex_opus/opus/without/repeat_3" && REQ="runs/with_vs_without/_inputs/nv_generate_ct_rflow/request.json" && mkdir -p "$OUT" && cat "$REQ" && cd "$NV_GENERATE_ROOT" && STAGE="$OLDPWD/$OUT/_stage" && mkdir -p "$STAGE/configs" "$OLDPWD/$OUT/output" && cp configs/config_network_rflow.json "$STAGE/configs/" && cp configs/environment_rflow-ct.json "$STAGE/configs/environment_rflow-ct.json" && python -c "
import json, os
infer = json.load(open('configs/config_infer.json'))
infer['body_region'] = ['chest']
infer['anatomy_list'] = ['lung tumor']
infer['controllable_anatomy_size'] = [['lung tumor', 0.3]]
infer['modality'] = 'ct'
infer['output_size'] = [256, 256, 256]
infer['spacing'] = [1.5, 1.5, 1.5]
infer['num_inference_steps'] = 30
infer['mask_generation_num_inference_steps'] = 1000
infer['num_output_samples'] = 1
json.dump(infer, open('$STAGE/configs/config_infer.json','w'), indent=2)
env = json.load(open('$STAGE/configs/environment_rflow-ct.json'))
env['output_dir'] = '$OLDPWD/$OUT/output'
json.dump(env, open('$STAGE/configs/environment_rflow-ct.json','w'), indent=2)
" && export MONAI_DATA_DIRECTORY="$OLDPWD/$OUT/temp_work_dir" && mkdir -p "$MONAI_DATA_DIRECTORY" && python -m scripts.inference -t "$STAGE/configs/config_network_rflow.json" -i "$STAGE/configs/config_infer.json" -e "$STAGE/configs/environment_rflow-ct.json" --random-seed 3 --version rflow-ct
```

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `examples/studies/with_vs_without_skill/nv_generate_ct_rflow_codex_opus/` |
| Generated outputs | `runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_generate_ct_rflow_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
