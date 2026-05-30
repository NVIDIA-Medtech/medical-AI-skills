# `nv_generate_ct_rflow`: Codex/Opus LLM+SKILL.md vs LLM+README

Status: strict audit passed for refreshed artifacts on May 29, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

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
| GPT-5.5 / Codex | with | 3 | 3 | 3 | 9,378 | 1,292 | 911 | 10,670 | 3,556.7 | 3 | 113.1 |
| GPT-5.5 / Codex | without | 3 | 0 | 3 | 8,994 | 18,638 | 14,246 | 27,632 | 9,210.7 | 1 | 0.0 |
| Opus 4.7 | with | 3 | 3 | 3 | 15,960 | 685 | 0 | 16,645 | 5,548.3 | 3 | 132.3 |
| Opus 4.7 | without | 3 | 0 | 3 | 14,301 | 2,974 | 0 | 17,275 | 5,758.3 | 1 | 0.0 |

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
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-$HOME/nv-generate-ctmr}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-ct-rflow/scripts/run_rflow_ct.py runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json --output-dir runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/with/repeat_2 --random-seed 2 --version rflow-ct --yes
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-$HOME/nv-generate-ctmr}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-ct-rflow/scripts/run_rflow_ct.py runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json --output-dir runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/with/repeat_3 --random-seed 3 --version rflow-ct --yes
```

### GPT-5.5 / Codex, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 4/5, passed=no, steps=unresolved, exit=None

```bash
OUT="runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/without/repeat_1" && NV_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && NV_ROOT="$(python -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())' "$NV_ROOT")" && rm -rf "$OUT" && mkdir -p "$OUT/runtime" "$OUT/monai_data" && python - "$NV_ROOT" "$OUT" <<'PY' && SEED="$(cat "$OUT/runtime/random_seed.txt")" && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$NV_ROOT:${PYTHONPATH:-}" MONAI_DATA_DIRECTORY="$(pwd)/$OUT/monai_data" python -m scripts.inference -t "$NV_ROOT/configs/config_network_rflow.json" -i "$OUT/runtime/config_infer.json" -e "$OUT/runtime/environment_rflow-ct.json" --random-seed "$SEED" --version rflow-ct && python - "$OUT" <<'PY'
import json, os, re, shutil, sys
from pathlib import Path

nv = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2])
runtime = out / "runtime"
req_path = Path("runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json")

if not nv.exists():
    raise FileNotFoundError(f"NV-Generate-CTMR root not found: {nv}")

request = json.loads(req_path.read_text()) if req_path.exists() else {}
if req_path.exists():
    shutil.copy2(req_path, runtime / "request.json")

def recursive_find(obj, keys):
    if isinstance(obj, dict):
        for k in keys:
            if k in obj:
                return obj[k]
        for v in obj.values():
            found = recursive_find(v, keys)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = recursive_find(v, keys)
            if found is not None:
                return found
    return None

seed = recursive_find(request, ["random_seed", "seed"])
seed = 0 if seed is None else int(seed)
(runtime / "random_seed.txt").write_text(f"{seed}\n")

def norm(s):
    return re.sub(r"\s+", " ", str(s).replace("_", " ").replace("-", " ").lower()).strip()

def collect_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str):
                yield k
            yield from collect_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from collect_strings(v)

label_dict = json.loads((nv / "configs/label_dict.json").read_text())
label_names = sorted(set(collect_strings(label_dict)))
by_norm = {norm(n): n for n in label_names}

tumor = None
for candidate in ["lung tumor", "lung_tumor", "pulmonary tumor", "chest tumor", "tumor"]:
    if norm(candidate) in by_norm and "lung" in norm(by_norm[norm(candidate)]) and "tumor" in norm(by_norm[norm(candidate)]):
        tumor = by_norm[norm(candidate)]
        break
if tumor is None:
    for n in label_names:
        nn = norm(n)
        if "lung" in nn and ("tumor" in nn or "neoplasm" in nn or "mass" in nn):
            tumor = n
            break
if tumor is None:
    raise ValueError("Could not find a lung tumor label in configs/label_dict.json")

lung_names = []
if "lung" in by_norm:
    lung_names = [by_norm["lung"]]
else:
    for candidate in ["right lung", "left lung"]:
        if norm(candidate) in by_norm:
            lung_names.append(by_norm[norm(candidate)])
if not lung_names:
    lung_names = [n for n in label_names if "lung" in norm(n) and "tumor" not in norm(n)][:2]
if not lung_names:
    raise ValueError("Could not find a lung label in configs/label_dict.json")

anatomy_list = []
for n in lung_names + [tumor]:
    if n not in anatomy_list:
        anatomy_list.append(n)

supported_size_names = set()
size_json = nv / "configs/all_anatomy_size_conditions.json"
if size_json.exists():
    supported_size_names = {norm(s) for s in collect_strings(json.loads(size_json.read_text()))}

control = []
for n in lung_names[:2]:
    if not supported_size_names or norm(n) in supported_size_names:
        control.append([n, 0.70])
if not supported_size_names or norm(tumor) in supported_size_names:
    control.append([tumor, 0.35])
if not any(norm(x[0]) == norm(tumor) for x in control):
    control.append([tumor, 0.35])

infer = json.loads((nv / "configs/config_infer.json").read_text())
infer.update({
    "body_region": ["chest"],
    "anatomy_list": anatomy_list,
    "controllable_anatomy_size": control,
    "output_size": [256, 256, 256],
    "spacing": [1.5, 1.5, 1.5],
    "modality": 1,
    "num_inference_steps": 30,
    "mask_generation_num_inference_steps": 1000,
    "cfg_guidance_scale": 3.0,
    "output_dir": str(out),
})
for k in ("num_output_samples", "num_samples", "n_samples", "num_images"):
    if k in infer:
        infer[k] = 1
(runtime / "config_infer.json").write_text(json.dumps(infer, indent=2) + "\n")

env = json.loads((nv / "configs/environment_rflow-ct.json").read_text())
def absolutize_existing_paths(x):
    if isinstance(x, str):
        p = Path(x)
        if not p.is_absolute():
            candidate = nv / p
            if candidate.exists():
                return str(candidate.resolve())
        return x
    if isinstance(x, list):
        return [absolutize_existing_paths(v) for v in x]
    if isinstance(x, dict):
        return {k: absolutize_existing_paths(v) for k, v in x.items()}
    return x
env = absolutize_existing_paths(env)
(runtime / "environment_rflow-ct.json").write_text(json.dumps(env, indent=2) + "\n")
PY
from pathlib import Path
import sys

out = Path(sys.argv[1])
pairs = []
for img in sorted(out.glob("*_image.nii.gz")):
    lbl = Path(str(img).replace("_image.nii.gz", "_label.nii.gz"))
    if lbl.exists():
        pairs.append((img, lbl))

if not pairs:
    raise RuntimeError(f"No paired *_image.nii.gz and *_label.nii.gz outputs found in {out}")

keep = max(pairs, key=lambda p: p[0].stat().st_mtime)
keep_set = {keep[0].resolve(), keep[1].resolve()}

for f in list(out.glob("*_image.nii.gz")) + list(out.glob("*_label.nii.gz")):
    if f.resolve() not in keep_set:
        f.unlink()

final_pairs = []
for img in sorted(out.glob("*_image.nii.gz")):
    lbl = Path(str(img).replace("_image.nii.gz", "_label.nii.gz"))
    if lbl.exists():
        final_pairs.append((img, lbl))

if len(final_pairs) != 1:
    raise RuntimeError(f"Expected exactly one image/label pair in {out}, found {len(final_pairs)}")
PY
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=None

```bash
set -euo pipefail && : "${NV_GENERATE_ROOT:?Set NV_GENERATE_ROOT to the NV-Generate-CTMR checkout}" && OUT_REL="runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/without/repeat_2" && REQ_REL="runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json" && REPO_ROOT="$(pwd)" && OUT_ABS="${REPO_ROOT}/${OUT_REL}" && RUNTIME="${OUT_ABS}/_runtime" && MONAI_DIR="${OUT_ABS}/_monai_data" && CACHE_DIR="${OUT_ABS}/_cache" && rm -rf "${OUT_ABS}" && mkdir -p "${RUNTIME}" "${MONAI_DIR}" "${CACHE_DIR}" "${OUT_ABS}/_mplconfig" && cp "${NV_GENERATE_ROOT}/configs/config_network_rflow.json" "${RUNTIME}/config_network_rflow.json" && cp "${NV_GENERATE_ROOT}/configs/config_infer.json" "${RUNTIME}/config_infer.json" && cp "${NV_GENERATE_ROOT}/configs/environment_rflow-ct.json" "${RUNTIME}/environment_rflow-ct.json" && python - "${RUNTIME}/config_infer.json" "${REQ_REL}" "${OUT_ABS}" "${NV_GENERATE_ROOT}/configs/label_dict.json" <<'PY' && (cd "${NV_GENERATE_ROOT}" && PYTHONDONTWRITEBYTECODE=1 MONAI_DATA_DIRECTORY="${MONAI_DIR}" XDG_CACHE_HOME="${CACHE_DIR}" MPLCONFIGDIR="${OUT_ABS}/_mplconfig" python -m scripts.inference -t "${RUNTIME}/config_network_rflow.json" -i "${RUNTIME}/config_infer.json" -e "${RUNTIME}/environment_rflow-ct.json" --random-seed 2 --version rflow-ct) && python - "${OUT_ABS}" <<'PY'
import json, re, shutil, sys
from pathlib import Path

cfg_path = Path(sys.argv[1])
request_path = Path(sys.argv[2])
out_dir = Path(sys.argv[3])
label_dict_path = Path(sys.argv[4])

runtime_dir = cfg_path.parent
if request_path.exists():
    shutil.copy2(request_path, runtime_dir / "request.json")

def norm(s):
    return re.sub(r"\s+", " ", str(s).lower().replace("_", " ").replace("-", " ")).strip()

raw = json.loads(label_dict_path.read_text())
names = []
if isinstance(raw, dict):
    for k, v in raw.items():
        if isinstance(k, str) and not k.isdigit():
            names.append(k)
        if isinstance(v, str):
            names.append(v)
elif isinstance(raw, list):
    names.extend(x for x in raw if isinstance(x, str))

lookup = {norm(n): n for n in names}
def choose(candidates):
    for c in candidates:
        if norm(c) in lookup:
            return lookup[norm(c)]
    raise SystemExit(f"Could not find any of {candidates!r} in {label_dict_path}")

lung = choose(["lung"])
lung_tumor = choose(["lung tumor", "lung_tumor", "lung tumour"])

cfg = json.loads(cfg_path.read_text())
cfg.update({
    "body_region": ["chest"],
    "anatomy_list": [lung, lung_tumor],
    "controllable_anatomy_size": [[lung, 0.75], [lung_tumor, 0.25]],
    "output_size": [256, 256, 256],
    "spacing": [1.5, 1.5, 1.5],
    "modality": 1,
    "num_inference_steps": 30,
    "mask_generation_num_inference_steps": 1000,
    "cfg_guidance_scale": 3.0,
    "output_dir": str(out_dir),
})
for k in ("num_output_samples", "num_samples", "n_samples", "num_images", "sample_num", "batch_size"):
    if k in cfg:
        cfg[k] = 1
if "if_aug" in cfg:
    cfg["if_aug"] = False
cfg_path.write_text(json.dumps(cfg, indent=2) + "\n")
PY
import sys
from pathlib import Path

out = Path(sys.argv[1])
images = sorted(out.glob("sample_*_image.nii.gz"))
labels = sorted(out.glob("sample_*_label.nii.gz"))
if len(images) != 1 or len(labels) != 1:
    raise SystemExit(f"Expected exactly one generated image and one label in {out}; found {len(images)} images and {len(labels)} labels")
if images[0].name.replace("_image.nii.gz", "") != labels[0].name.replace("_label.nii.gz", ""):
    raise SystemExit(f"Generated image/label names do not form a pair: {images[0].name}, {labels[0].name}")
print(images[0])
print(labels[0])
PY
```

Repeat 3: score 4/5, passed=no, steps=unresolved, exit=1

```bash
set -euo pipefail && REQ="runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json" && OUT="runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/without/repeat_3" && UP="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && mkdir -p "$OUT/runtime" "$OUT/monai_data" && python - <<'PY' && MONAI_DATA_DIRECTORY="$(pwd)/runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/without/repeat_3/monai_data" PYTHONPATH="$(pwd)/${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" python -m scripts.inference -t "$(pwd)/runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/without/repeat_3/runtime/config_network_rflow.json" -i "$(pwd)/runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/without/repeat_3/runtime/config_infer.json" -e "$(pwd)/runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/without/repeat_3/runtime/environment_rflow-ct.json" --random-seed "$(python - <<'PY2'
import json
from pathlib import Path
req=Path("runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json")
seed=3
if req.exists():
    try:
        j=json.loads(req.read_text())
        seed=j.get("random_seed", j.get("seed", seed))
    except Exception:
        pass
print(seed)
PY2
)" --version rflow-ct && python - <<'PY'
from pathlib import Path
out = Path("runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/without/repeat_3")
pairs = []
for img in sorted(out.glob("*_image.nii.gz")):
    lab = img.with_name(img.name.replace("_image.nii.gz", "_label.nii.gz"))
    if lab.exists():
        pairs.append((img, lab))
if not pairs:
    raise SystemExit(f"No paired *_image.nii.gz and *_label.nii.gz files were produced in {out}")
keep = pairs[0]
for img, lab in pairs[1:]:
    img.unlink()
    lab.unlink()
print(f"Kept one paired output: {keep[0]} and {keep[1]}")
PY
import json, os, shutil
from pathlib import Path

repo = Path.cwd()
req_path = repo / "runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json"
out = repo / "runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/gpt55/without/repeat_3"
up = repo / os.environ.get("NV_GENERATE_ROOT", ".workbench_data/upstreams/NV-Generate-CTMR")
rt = out / "runtime"
rt.mkdir(parents=True, exist_ok=True)

shutil.copy2(up / "configs/config_network_rflow.json", rt / "config_network_rflow.json")
shutil.copy2(up / "configs/config_infer.json", rt / "config_infer.json")
shutil.copy2(up / "configs/environment_rflow-ct.json", rt / "environment_rflow-ct.json")

request = {}
if req_path.exists():
    try:
        request = json.loads(req_path.read_text())
    except Exception:
        request = {}

def names_from_label_dict(p):
    data = json.loads(p.read_text())
    names = []
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(k, str) and not k.isdigit():
                names.append(k)
            if isinstance(v, str):
                names.append(v)
    return list(dict.fromkeys(names))

label_names = names_from_label_dict(up / "configs/label_dict.json")
lower = {n.lower(): n for n in label_names}
lung_name = lower.get("lung") or lower.get("lungs") or next((n for n in label_names if "lung" in n.lower() and "tumor" not in n.lower()), "lung")
tumor_name = next((n for n in label_names if "lung" in n.lower() and ("tumor" in n.lower() or "cancer" in n.lower() or "lesion" in n.lower())), None)
if tumor_name is None:
    tumor_name = next((n for n in label_names if "tumor" in n.lower() or "cancer" in n.lower() or "lesion" in n.lower()), "tumor")

cfg_path = rt / "config_infer.json"
cfg = json.loads(cfg_path.read_text())

cfg["body_region"] = request.get("body_region", ["chest", "thorax"])
cfg["anatomy_list"] = request.get("anatomy_list", [lung_name, tumor_name])
cfg["controllable_anatomy_size"] = request.get("controllable_anatomy_size", [[lung_name, 0.5], [tumor_name, 0.2]])
cfg["output_size"] = request.get("output_size", [256, 256, 256])
cfg["spacing"] = request.get("spacing", [1.5, 1.5, 1.5])
cfg["modality"] = request.get("modality", 1)
cfg["num_inference_steps"] = request.get("num_inference_steps", 30)
cfg["mask_generation_num_inference_steps"] = request.get("mask_generation_num_inference_steps", 1000)
cfg["cfg_guidance_scale"] = request.get("cfg_guidance_scale", cfg.get("cfg_guidance_scale", 1.0))
cfg["output_dir"] = str(out)
for k in ("num_output_samples", "num_samples", "n_samples", "num_images", "batch_size"):
    if k in cfg:
        cfg[k] = 1
cfg_path.write_text(json.dumps(cfg, indent=2) + "\n")

env_path = rt / "environment_rflow-ct.json"
env = json.loads(env_path.read_text())

def absolutize(x):
    if isinstance(x, dict):
        return {k: absolutize(v) for k, v in x.items()}
    if isinstance(x, list):
        return [absolutize(v) for v in x]
    if isinstance(x, str):
        if x.startswith(("http://", "https://")) or os.path.isabs(x):
            return x
        candidate = up / x
        if candidate.exists() or x.startswith(("models/", "configs/", "data/")):
            return str(candidate)
    return x

env_path.write_text(json.dumps(absolutize(env), indent=2) + "\n")
PY
```

### Opus 4.7, with arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-$HOME/nv-generate-ctmr}" && \
python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && \
python skills/nv-generate-ct-rflow/scripts/run_rflow_ct.py \
  runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json \
  --output-dir runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/opus/with/repeat_1 \
  --random-seed 0 \
  --version rflow-ct
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
mkdir -p runs/with_vs_without/nv_generate_ct_rflow_codex_opus/opus/without/repeat_1/configs && cd "$NV_GENERATE_ROOT" && REQ="$OLDPWD/runs/with_vs_without/_inputs/nv_generate_ct_rflow/request.json" && OUT="$OLDPWD/runs/with_vs_without/nv_generate_ct_rflow_codex_opus/opus/without/repeat_1" && CFG_DIR="$OUT/configs" && cp ./configs/config_infer.json "$CFG_DIR/config_infer.json" && python -c "
import json
req = json.load(open('$REQ'))
cfg = json.load(open('$CFG_DIR/config_infer.json'))
cfg['body_region'] = ['chest']
cfg['anatomy_list'] = ['lung', 'lung tumor']
cfg['controllable_anatomy_size'] = [['lung tumor', 0.3]]
cfg['output_size'] = [256, 256, 256]
cfg['spacing'] = [1.5, 1.5, 1.5]
cfg['modality'] = 'ct'
cfg['num_inference_steps'] = 30
cfg['mask_generation_num_inference_steps'] = 1000
cfg['num_output_samples'] = 1
cfg['output_dir'] = '$OUT'
for k,v in req.items():
    if k in ('body_region','anatomy_list','controllable_anatomy_size','output_size','spacing','modality','num_output_samples'):
        cfg[k] = v
json.dump(cfg, open('$CFG_DIR/config_infer.json','w'), indent=2)
" && export MONAI_DATA_DIRECTORY="$OUT/temp_work_dir" && mkdir -p "$MONAI_DATA_DIRECTORY" && python -m scripts.inference -t ./configs/config_network_rflow.json -i "$CFG_DIR/config_infer.json" -e ./configs/environment_rflow-ct.json --random-seed 0 --version rflow-ct
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=1

```bash
OUT_DIR="runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/opus/without/repeat_2" && REQ="runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json" && REPO_ROOT="$(pwd)" && ABS_OUT="${REPO_ROOT}/${OUT_DIR}" && mkdir -p "${ABS_OUT}/configs" "${ABS_OUT}/output" && cp "${NV_GENERATE_ROOT}/configs/config_network_rflow.json" "${ABS_OUT}/configs/config_network_rflow.json" && cp "${NV_GENERATE_ROOT}/configs/environment_rflow-ct.json" "${ABS_OUT}/configs/environment_rflow-ct.json" && python -c "
import json, pathlib
req = json.load(open('${REPO_ROOT}/${REQ}'))
print('Request:', json.dumps(req, indent=2))
infer = json.load(open('${NV_GENERATE_ROOT}/configs/config_infer.json'))
infer['body_region'] = req.get('body_region', ['chest'])
infer['anatomy_list'] = req.get('anatomy_list', ['lung', 'lung tumor'])
infer['controllable_anatomy_size'] = req.get('controllable_anatomy_size', [['lung tumor', 0.3]])
infer['output_size'] = req.get('output_size', [256, 256, 256])
infer['spacing'] = req.get('spacing', [1.5, 1.5, 1.5])
infer['modality'] = req.get('modality', 1)
infer['num_inference_steps'] = 30
infer['mask_generation_num_inference_steps'] = 1000
infer['num_output_samples'] = req.get('num_output_samples', 1)
infer['output_dir'] = '${ABS_OUT}/output'
json.dump(infer, open('${ABS_OUT}/configs/config_infer.json', 'w'), indent=2)
env = json.load(open('${ABS_OUT}/configs/environment_rflow-ct.json'))
env['output_dir'] = '${ABS_OUT}/output'
json.dump(env, open('${ABS_OUT}/configs/environment_rflow-ct.json', 'w'), indent=2)
print('Staged configs at ${ABS_OUT}/configs')
" && cd "${NV_GENERATE_ROOT}" && MONAI_DATA_DIRECTORY="${ABS_OUT}/temp_work_dir" python -m scripts.inference -t "${ABS_OUT}/configs/config_network_rflow.json" -i "${ABS_OUT}/configs/config_infer.json" -e "${ABS_OUT}/configs/environment_rflow-ct.json" --random-seed 2 --version rflow-ct
```

Repeat 3: score 2/5, passed=no, steps=unresolved, exit=None

```bash
set -euo pipefail && OUT=runs/with_vs_without/nv_generate_ct_rflow_codex_opus/opus/without/repeat_3 && REQ=runs/with_vs_without/_inputs/nv_generate_ct_rflow/request.json && mkdir -p "$OUT" && STAGE="$OUT/_stage" && mkdir -p "$STAGE/configs" "$STAGE/output" && cd "$NV_GENERATE_ROOT" && cp configs/config_network_rflow.json configs/config_infer.json configs/environment_rflow-ct.json "$OLDPWD/$STAGE/configs/" && cd "$OLDPWD" && python -c "
import json, os
req = json.load(open('$REQ'))
print('Request:', json.dumps(req, indent=2))
infer = json.load(open('$STAGE/configs/config_infer.json'))
infer['body_region'] = ['chest']
infer['anatomy_list'] = ['lung tumor']
infer['controllable_anatomy_size'] = [['lung tumor', 0.3]]
infer['modality'] = 'ct'
infer['num_output_samples'] = 1
infer['output_size'] = [256, 256, 256]
infer['spacing'] = [1.5, 1.5, 1.5]
infer['num_inference_steps'] = 30
infer['mask_generation_num_inference_steps'] = 1000
json.dump(infer, open('$STAGE/configs/config_infer.json','w'), indent=2)
env = json.load(open('$STAGE/configs/environment_rflow-ct.json'))
env['output_dir'] = os.path.abspath('$STAGE/output')
json.dump(env, open('$STAGE/configs/environment_rflow-ct.json','w'), indent=2)
print('Staged configs at $STAGE/configs')
" && cd "$NV_GENERATE_ROOT" && MONAI_DATA_DIRECTORY="$OLDPWD/$STAGE/monai_tmp" python -m scripts.inference -t "$OLDPWD/$STAGE/configs/config_network_rflow.json" -i "$OLDPWD/$STAGE/configs/config_infer.json" -e "$OLDPWD/$STAGE/configs/environment_rflow-ct.json" --random-seed 3 --version rflow-ct && cd "$OLDPWD" && cp "$STAGE"/output/sample_*_image.nii.gz "$OUT/" && cp "$STAGE"/output/sample_*_label.nii.gz "$OUT/" && ls -la "$OUT"
```

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `runs/with_vs_without_nv/studies/nv_generate_ct_rflow_codex_opus/` |
| Generated outputs | `runs/with_vs_without_nv/nv_generate_ct_rflow_codex_opus/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_generate_ct_rflow_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
