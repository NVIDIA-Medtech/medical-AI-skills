# `nv_segment_ct`: Codex/Opus LLM+SKILL.md vs LLM+README

Status: strict audit passed for refreshed artifacts on May 28, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

This report compares `LLM + SKILL.md` with `LLM + upstream README/guide`. The completed direct-API run used the corrected embedded-doc minimal prompt because those backends cannot read repo files. The fair NAT/tool-agent prompt artifact is A2-style: it gives a natural user request, a neutral staged input path, an output directory, and tells the agent which arm-specific document to read. It does not spell out operational details such as entrypoints, labels, model variants, or config filenames outside the documentation arm.

## Experiment Question

Does `LLM + SKILL.md` make an agent better at reading documentation and taking the right action than `LLM + upstream README/guide`?

## User Request Shape

The prompt request for the GPT-5.5 with-skill arm was:

> The input CT volume is at runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz. Segment the spleen, liver, right kidney, and left kidney, and write outputs under runs/with_vs_without_nv/nv_segment_ct_codex_opus/gpt55/with/repeat_1.

The staged user input for every arm was `runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz`. The source fixture `skills/nv-segment-ct/fixtures/spleen_03.nii.gz` was used only to stage that neutral input path.

Fair path-prompt artifact: `tools/nat_audit/data/eval_nv_model_studies_nv_segment_ct_prompts.json`

## Result

| Backend | Arm | Mean score | Passes | Steps | Exit | Tier 5 | Failed tiers |
|---|---|---:|---:|---|---|---|---|
| GPT-5.5 / Codex | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | shape=(512, 512, 40) (3) | none |
| GPT-5.5 / Codex | without | 3.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | None (3) | blocked unsafe command fragment: rm (3) | T3: model/modality/control marker (3); T5: blocked unsafe command fragment: rm (3) |
| Opus 4.7 | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | shape=(512, 512, 40) (3) | none |
| Opus 4.7 | without | 4.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | 1 (3) | exit 1 (3) | T5: exit 1 (3) |

## Analysis

SKILL.md paired advantage: the with-skill arms passed 6/6 backend-repeat trials with an average score of 5.0/5; the README-only arms passed 0/6 backend-repeat trials with an average score of 3.5/5.

SKILL.md paired advantage: SKILL.md wins 6/6 matched backend-repeat pairs, README-only wins 0/6, and 0/6 are ties. Pass/fail is the primary outcome; score breaks ties only when pass status is equal. Exact one-sided sign-test p=0.01562 across 6 decisive pair(s).

Outcome-support gate: Supports SKILL.md advantage. SKILL.md wins 6/6 matched pair(s); README-only wins 0/6; sign-test p=0.01562.

Each backend/arm/skill configuration was repeated three times. A repeat is independent: it has its own output directory, and each execution attempt inside the repeat creates a fresh venv before running the generated command. Dependency and model download caches are shared only as documented test-environment caches under `.workbench_data/with_vs_without_cache` (`PIP_CACHE_DIR=.workbench_data/with_vs_without_cache/pip`, `HF_HOME=.workbench_data/with_vs_without_cache/huggingface`, `HF_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `HUGGINGFACE_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `TRANSFORMERS_CACHE=.workbench_data/with_vs_without_cache/huggingface/transformers`, `TORCH_HOME=.workbench_data/with_vs_without_cache/torch`, `XDG_CACHE_HOME=.workbench_data/with_vs_without_cache/xdg`, `CONDA_PKGS_DIRS=.workbench_data/with_vs_without_cache/conda_pkgs`, `UV_CACHE_DIR=.workbench_data/with_vs_without_cache/uv`, `CUDA_CACHE_PATH=.workbench_data/with_vs_without_cache/cuda`, `NUMBA_CACHE_DIR=.workbench_data/with_vs_without_cache/numba`).

The main baseline uses `max_correction_steps=0`: each repeat sends one prompt, executes the extracted command once, and records pass/fail, runtime, tokens, and deterministic failure analysis. The repair-loop implementation remains available for separate diagnostic experiments, but it is not part of this comparison.

All with-skill repeats exited successfully and produced artifacts accepted by the deterministic grader. That means the final SKILL.md surface was repeatable for both tested agent backends.

The README-only commands did not pass tier 5. Typical failure modes were unsafe generated shell cleanup, missing schema fields, missing model/control details, or upstream commands that did not execute cleanly from Medical AI Skills root.

Tier 2 is intentionally strict: a command only earns it if it uses the staged user input path `runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz`.

## Token Profiling

Token counts are provider-reported values saved in each repeat JSON. Reasoning tokens are shown only when the provider returned that subfield and are a subset of completion tokens, not an additional cost to add to total tokens. Execution time is averaged only across repeats that reached command execution; no-command-extracted repeats still count toward token totals.

| Backend | Arm | Repeats | Passes | Attempts | Prompt tokens | Completion tokens | Reasoning tokens | Total tokens | Mean total/repeat | Executed | Mean exec s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GPT-5.5 / Codex | with | 3 | 3 | 3 | 5,673 | 1,555 | 1,153 | 7,228 | 2,409.3 | 3 | 37.0 |
| GPT-5.5 / Codex | without | 3 | 0 | 3 | 7,338 | 12,471 | 10,751 | 19,809 | 6,603.0 | 0 | n/a |
| Opus 4.7 | with | 3 | 3 | 3 | 9,477 | 591 | 0 | 10,068 | 3,356.0 | 3 | 43.1 |
| Opus 4.7 | without | 3 | 0 | 3 | 11,724 | 760 | 0 | 12,484 | 4,161.3 | 3 | 0.5 |

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
| 1 | 0 | 3/5 | no | None | T3: model/modality/control marker; T5: blocked unsafe command fragment: rm | tier_3: model/modality/control marker Repair: Choose the model, modality, labels, anatomy controls, or smoke mode required by the task.<br>tier_5: blocked unsafe command fragment: rm Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: blocked unsafe command fragment: rm Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
| 2 | 0 | 3/5 | no | None | T3: model/modality/control marker; T5: blocked unsafe command fragment: rm | tier_3: model/modality/control marker Repair: Choose the model, modality, labels, anatomy controls, or smoke mode required by the task.<br>tier_5: blocked unsafe command fragment: rm Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: blocked unsafe command fragment: rm Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
| 3 | 0 | 3/5 | no | None | T3: model/modality/control marker; T5: blocked unsafe command fragment: rm | tier_3: model/modality/control marker Repair: Choose the model, modality, labels, anatomy controls, or smoke mode required by the task.<br>tier_5: blocked unsafe command fragment: rm Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: blocked unsafe command fragment: rm Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |

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

Before the final rerun, `SKILL.md` was tightened to name `scripts/run_vista3d.py` as the exact runnable surface and to state the required label IDs for the requested spleen/liver/kidney task.

## Generated Commands

These are the extracted first-attempt commands by repeat.

### GPT-5.5 / Codex, with arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
pip install -r skills/nv-segment-ct/requirements.txt && huggingface-cli download nvidia/NV-Segment-CT --local-dir skills/nv-segment-ct/bundle/ && python skills/nv-segment-ct/scripts/run_vista3d.py runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz --label-prompts "1,3,5,14" --output-dir runs/with_vs_without_nv/nv_segment_ct_codex_opus/gpt55/with/repeat_1
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
pip install -r skills/nv-segment-ct/requirements.txt && huggingface-cli download nvidia/NV-Segment-CT --local-dir skills/nv-segment-ct/bundle/ && python skills/nv-segment-ct/scripts/run_vista3d.py runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz --label-prompts "1,3,5,14" --output-dir runs/with_vs_without_nv/nv_segment_ct_codex_opus/gpt55/with/repeat_2
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
mkdir -p runs/with_vs_without_nv/nv_segment_ct_codex_opus/gpt55/with/repeat_3 && pip install -r skills/nv-segment-ct/requirements.txt && huggingface-cli download nvidia/NV-Segment-CT --local-dir skills/nv-segment-ct/bundle/ && python skills/nv-segment-ct/scripts/run_vista3d.py runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz --label-prompts "1,3,5,14" --output-dir runs/with_vs_without_nv/nv_segment_ct_codex_opus/gpt55/with/repeat_3
```

### GPT-5.5 / Codex, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 3/5, passed=no, steps=unresolved, exit=None

```bash
source "$(conda info --base)/etc/profile.d/conda.sh" && conda activate vista3d-nv && WB_ROOT="$PWD" && OUT="runs/with_vs_without_nv/nv_segment_ct_codex_opus/gpt55/without/repeat_1" && RUNTIME="$WB_ROOT/$OUT/_runtime/NV-Segment-CT" && mkdir -p "$WB_ROOT/$OUT/_runtime" && rm -rf "$RUNTIME" && cp -a "$NV_SEGMENT_CTMR_ROOT/NV-Segment-CT" "$RUNTIME" && cd "$RUNTIME" && python -m monai.bundle run --config_file configs/inference.json --input_dict "{'image':'$WB_ROOT/runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz','label_prompt':[1,2,3,5]}" --output_dir "$WB_ROOT/$OUT"
```

Repeat 2: score 3/5, passed=no, steps=unresolved, exit=None

```bash
bash -lc 'set -euo pipefail && source "$(conda info --base)/etc/profile.d/conda.sh" && conda activate vista3d-nv && OUT="runs/with_vs_without_nv/nv_segment_ct_codex_opus/gpt55/without/repeat_2" && SRC="${NV_SEGMENT_CTMR_ROOT:-.workbench_data/upstreams/NV-Segment-CTMR}/NV-Segment-CT" && RUNTIME="$OUT/_runtime/NV-Segment-CT" && rm -rf "$RUNTIME" && mkdir -p "$RUNTIME" && tar --exclude="./models" -C "$SRC" -cf - . | tar -C "$RUNTIME" -xf - && PROMPT="$(python - "$RUNTIME/configs/label_dict.json" <<'"'"'PY'"'"'
import json, re, sys
p = sys.argv[1]
data = json.load(open(p))

def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()

pairs = []
def walk(x):
    if isinstance(x, dict):
        for k, v in x.items():
            if isinstance(v, (int, float)) and float(v).is_integer():
                pairs.append((norm(k), int(v)))
            elif isinstance(v, str) and str(k).lstrip("-").isdigit():
                pairs.append((norm(v), int(k)))
            else:
                walk(v)
    elif isinstance(x, list):
        for v in x:
            walk(v)
walk(data)

aliases = {
    "spleen": ["spleen"],
    "liver": ["liver"],
    "right kidney": ["right kidney", "kidney right", "right renal", "renal right", "kidney r"],
    "left kidney": ["left kidney", "kidney left", "left renal", "renal left", "kidney l"],
}

ids = []
missing = []
for target, names in aliases.items():
    found = None
    nnames = [norm(n) for n in names]
    for name, idx in pairs:
        if name in nnames:
            found = idx
            break
    if found is None:
        missing.append(target)
    else:
        ids.append(found)

if missing:
    raise SystemExit(f"Could not resolve labels in {p}: {missing}")
print(ids)
PY
)" && WB="$PWD" && cd "$RUNTIME" && python -m monai.bundle run --config_file configs/inference.json --input_dict "{'"'"'image'"'"':'"'"'$WB/runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz'"'"','"'"'label_prompt'"'"':$PROMPT}" --output_dir "$WB/$OUT"'
```

Repeat 3: score 3/5, passed=no, steps=unresolved, exit=None

```bash
set -euo pipefail && source "$(conda info --base)/etc/profile.d/conda.sh" && conda activate vista3d-nv && WB="$PWD" && OUT="runs/with_vs_without_nv/nv_segment_ct_codex_opus/gpt55/without/repeat_3" && SRC="${NV_SEGMENT_CTMR_ROOT:?NV_SEGMENT_CTMR_ROOT is not set}/NV-Segment-CT" && RUNTIME="$WB/$OUT/NV-Segment-CT_runtime" && mkdir -p "$WB/$OUT/batch_input" "$WB/$OUT/segmentations" && rm -rf "$RUNTIME" && mkdir -p "$RUNTIME" && cp -a "$SRC/." "$RUNTIME/" && ln -sfn "$WB/runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz" "$WB/$OUT/batch_input/input.nii.gz" && python - "$RUNTIME" <<'PY' && cd "$RUNTIME" && python -m monai.bundle run --config_file="['configs/inference.json','configs/batch_inference.json']" --input_dir="$WB/$OUT/batch_input" --output_dir="$WB/$OUT/segmentations"
import json, pathlib, re, sys
rt = pathlib.Path(sys.argv[1])
label_path = rt / "configs" / "label_dict.json"
infer_path = rt / "configs" / "inference.json"
data = json.loads(label_path.read_text())

pairs = []
def as_int(x):
    try:
        return int(x)
    except Exception:
        return None

def add_pair(label, name):
    lab = as_int(label)
    if lab is not None and isinstance(name, str) and name.strip():
        pairs.append((lab, name.strip()))

def walk(obj, parent_key=None):
    if isinstance(obj, dict):
        if parent_key is not None:
            for key in ("name", "label", "class_name", "label_name", "organ", "value"):
                if isinstance(obj.get(key), str):
                    add_pair(parent_key, obj[key])
        for k, v in obj.items():
            if isinstance(v, str):
                add_pair(k, v)
            elif isinstance(v, int):
                add_pair(v, k)
            else:
                walk(v, k)
    elif isinstance(obj, list):
        for item in obj:
            walk(item, parent_key)

walk(data)

def norm(s):
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", s.lower())).strip("_")

targets = [
    ("spleen", {"spleen"}),
    ("liver", {"liver"}),
    ("right kidney", {"kidney_right", "right_kidney", "kidney_r", "r_kidney"}),
    ("left kidney", {"kidney_left", "left_kidney", "kidney_l", "l_kidney"}),
]

selected = []
seen = set()
norm_pairs = [(lab, name, norm(name)) for lab, name in pairs]
for target, synonyms in targets:
    hit = None
    for lab, name, nn in norm_pairs:
        if nn in synonyms:
            hit = lab
            break
    if hit is None:
        raise SystemExit(f"Could not find label for {target} in {label_path}")
    if hit not in seen:
        selected.append(hit)
        seen.add(hit)

cfg = json.loads(infer_path.read_text())
cfg["everything_labels"] = selected
infer_path.write_text(json.dumps(cfg, indent=2) + "\n")
(rt / "configs" / "selected_labels.json").write_text(json.dumps({"requested": [t[0] for t in targets], "everything_labels": selected}, indent=2) + "\n")
PY
```

### Opus 4.7, with arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
pip install -r skills/nv-segment-ct/requirements.txt && huggingface-cli download nvidia/NV-Segment-CT --local-dir skills/nv-segment-ct/bundle/ && python skills/nv-segment-ct/scripts/run_vista3d.py runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz --label-prompts "1,3,5,14" --output-dir runs/with_vs_without_nv/nv_segment_ct_codex_opus/opus/with/repeat_1
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
pip install -r skills/nv-segment-ct/requirements.txt && huggingface-cli download nvidia/NV-Segment-CT --local-dir skills/nv-segment-ct/bundle/ && python skills/nv-segment-ct/scripts/run_vista3d.py runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz --label-prompts "1,3,5,14" --output-dir runs/with_vs_without_nv/nv_segment_ct_codex_opus/opus/with/repeat_2
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
pip install -r skills/nv-segment-ct/requirements.txt && huggingface-cli download nvidia/NV-Segment-CT --local-dir skills/nv-segment-ct/bundle/ && python skills/nv-segment-ct/scripts/run_vista3d.py runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz --label-prompts "1,3,5,14" --output-dir runs/with_vs_without_nv/nv_segment_ct_codex_opus/opus/with/repeat_3
```

### Opus 4.7, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 4/5, passed=no, steps=unresolved, exit=1

```bash
mkdir -p runs/with_vs_without_nv/nv_segment_ct_codex_opus/opus/without/repeat_1 && cd "$NV_SEGMENT_CTMR_ROOT" && conda run -n vista3d-nv --no-capture-output python -m monai.bundle run --config_file configs/inference.json --input_dict "{'image':'$(pwd -P)/../../runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz','label_prompt':[3,1,5,14]}" --output_dir "$(pwd -P)/../../runs/with_vs_without_nv/nv_segment_ct_codex_opus/opus/without/repeat_1"
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=1

```bash
mkdir -p runs/with_vs_without_nv/nv_segment_ct_codex_opus/opus/without/repeat_2 && cd "$NV_SEGMENT_CTMR_ROOT/NV-Segment-CT" && conda run -n vista3d-nv --no-capture-output python -m monai.bundle run --config_file configs/inference.json --input_dict "{'image':'$OLDPWD/runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz','label_prompt':[1,3,5,14]}" --output_dir "$OLDPWD/runs/with_vs_without_nv/nv_segment_ct_codex_opus/opus/without/repeat_2"
```

Repeat 3: score 4/5, passed=no, steps=unresolved, exit=1

```bash
mkdir -p runs/with_vs_without_nv/nv_segment_ct_codex_opus/opus/without/repeat_3 && cd "$NV_SEGMENT_CTMR_ROOT" && conda run -n vista3d-nv --no-capture-output python -m monai.bundle run --config_file configs/inference.json --input_dict "{'image':'$(realpath $OLDPWD/runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz)','label_prompt':[1,3,5,14]}" --output_dir "$OLDPWD/runs/with_vs_without_nv/nv_segment_ct_codex_opus/opus/without/repeat_3"
```

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `examples/studies/with_vs_without_skill/nv_segment_ct_codex_opus/` |
| Generated outputs | `runs/with_vs_without_nv/nv_segment_ct_codex_opus/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_segment_ct_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
