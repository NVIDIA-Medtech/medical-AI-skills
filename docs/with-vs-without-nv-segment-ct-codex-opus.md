# `nv_segment_ct`: Codex/Opus LLM+SKILL.md vs LLM+README

Status: strict audit passed for refreshed artifacts on May 29, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

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
| GPT-5.5 / Codex | without | 2.3/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | None (3) | command does not reference the neutral staged input path (2); blocked unsafe command fragment: rm (1) | T3: model/modality/control marker (3); T2: user input path marker (2); T5: command does not reference the neutral staged input path (2) |
| Opus 4.7 | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | shape=(512, 512, 40) (3) | none |
| Opus 4.7 | without | 4.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | 1 (3) | exit 1 (3) | T5: exit 1 (3) |

## Analysis

SKILL.md paired advantage: the with-skill arms passed 6/6 backend-repeat trials with an average score of 5.0/5; the README-only arms passed 0/6 backend-repeat trials with an average score of 3.2/5.

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
| GPT-5.5 / Codex | with | 3 | 3 | 3 | 5,652 | 1,280 | 878 | 6,932 | 2,310.7 | 3 | 69.3 |
| GPT-5.5 / Codex | without | 3 | 0 | 3 | 7,344 | 10,625 | 8,700 | 17,969 | 5,989.7 | 0 | n/a |
| Opus 4.7 | with | 3 | 3 | 3 | 9,492 | 637 | 0 | 10,129 | 3,376.3 | 3 | 40.6 |
| Opus 4.7 | without | 3 | 0 | 3 | 11,754 | 759 | 0 | 12,513 | 4,171.0 | 3 | 0.6 |

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
| 2 | 0 | 2/5 | no | None | T2: user input path marker; T3: model/modality/control marker; T5: command does not reference the neutral staged input path | tier_2: user input path marker Repair: Use the staged user input path under runs/with_vs_without_nv/_inputs/.<br>tier_3: model/modality/control marker Repair: Choose the model, modality, labels, anatomy controls, or smoke mode required by the task.<br>tier_5: command does not reference the neutral staged input path Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference the neutral staged input path Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
| 3 | 0 | 2/5 | no | None | T2: user input path marker; T3: model/modality/control marker; T5: command does not reference the neutral staged input path | tier_2: user input path marker Repair: Use the staged user input path under runs/with_vs_without_nv/_inputs/.<br>tier_3: model/modality/control marker Repair: Choose the model, modality, labels, anatomy controls, or smoke mode required by the task.<br>tier_5: command does not reference the neutral staged input path Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference the neutral staged input path Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |

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
mkdir -p runs/with_vs_without_nv/nv_segment_ct_codex_opus/gpt55/with/repeat_2 && pip install -r skills/nv-segment-ct/requirements.txt && huggingface-cli download nvidia/NV-Segment-CT --local-dir skills/nv-segment-ct/bundle/ && python skills/nv-segment-ct/scripts/run_vista3d.py runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz --label-prompts "1,3,5,14" --output-dir runs/with_vs_without_nv/nv_segment_ct_codex_opus/gpt55/with/repeat_2
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
pip install -r skills/nv-segment-ct/requirements.txt && huggingface-cli download nvidia/NV-Segment-CT --local-dir skills/nv-segment-ct/bundle/ && python skills/nv-segment-ct/scripts/run_vista3d.py runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz --label-prompts "1,3,5,14" --output-dir runs/with_vs_without_nv/nv_segment_ct_codex_opus/gpt55/with/repeat_3
```

### GPT-5.5 / Codex, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 3/5, passed=no, steps=unresolved, exit=None

```bash
REPO_ROOT="$PWD" && OUT="$REPO_ROOT/runs/with_vs_without_nv/nv_segment_ct_codex_opus/gpt55/without/repeat_1" && INPUT="$REPO_ROOT/runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz" && SRC="${NV_SEGMENT_CTMR_ROOT:-$REPO_ROOT/.workbench_data/upstreams/NV-Segment-CTMR}/NV-Segment-CT" && rm -rf "$OUT" && mkdir -p "$OUT/runtime" "$OUT/input_dir" "$OUT/hf_home" "$OUT/segmentations" && cp -a "$SRC" "$OUT/runtime/NV-Segment-CT" && cp "$INPUT" "$OUT/input_dir/input.nii.gz" && RUNTIME="$OUT/runtime/NV-Segment-CT" python -c 'import json, os, pathlib, re; rt=pathlib.Path(os.environ["RUNTIME"]); ld=json.load(open(rt/"configs/label_dict.json")); pairs=[]; norm=lambda s: re.sub(r"[^a-z0-9]+","",str(s).lower()); def to_int(x):\n    try: return int(x)\n    except Exception: return None\ndef walk(o):\n    if isinstance(o, dict):\n        for k,v in o.items():\n            ki=to_int(k); vi=to_int(v)\n            if ki is not None and isinstance(v,str): pairs.append((norm(v),ki,v))\n            if vi is not None and isinstance(k,str) and norm(k) not in {"id","index","label","value"}: pairs.append((norm(k),vi,k))\n        names=[]; ids=[]\n        for k,v in o.items():\n            nk=norm(k)\n            if isinstance(v,str) and nk in {"name","label","class","classname","class_name"}: names.append(v)\n            iv=to_int(v)\n            if iv is not None and nk in {"id","index","label","labelid","label_id","value"}: ids.append(iv)\n        for n in names:\n            for i in ids: pairs.append((norm(n),i,n))\n        for v in o.values(): walk(v)\n    elif isinstance(o, list):\n        for v in o: walk(v)\nwalk(ld); targets=[("spleen",["spleen"]),("liver",["liver"]),("right kidney",["rightkidney","kidneyright","kidneyr"]),("left kidney",["leftkidney","kidneyleft","kidneyl"])]; labels=[]\nfor human, aliases in targets:\n    hits=[]\n    for n,i,raw in pairs:\n        if n in aliases or any(a in n or n in a for a in aliases): hits.append(i)\n    if not hits: raise SystemExit(f"Could not find label for {human} in configs/label_dict.json")\n    labels.append(hits[0])\ncfg_path=rt/"configs/inference.json"; cfg=json.load(open(cfg_path)); cfg["everything_labels"]=labels; json.dump(cfg, open(cfg_path,"w"), indent=2); print("Configured everything_labels:", labels)' && source "$(conda info --base)/etc/profile.d/conda.sh" && conda activate vista3d-nv && cd "$OUT/runtime/NV-Segment-CT" && HF_HOME="$OUT/hf_home" python -m monai.bundle run --config_file="['configs/inference.json', 'configs/batch_inference.json']" --input_dir="$OUT/input_dir" --output_dir="$OUT/segmentations"
```

Repeat 2: score 2/5, passed=no, steps=unresolved, exit=None

```bash
bash -lc 'set -euo pipefail; repo="$(pwd)"; out="runs/with_vs_without_nv/nv_segment_ct_codex_opus/gpt55/without/repeat_2"; runtime="$repo/$out/runtime"; results="$repo/$out/outputs"; src="${NV_SEGMENT_CTMR_ROOT:?NV_SEGMENT_CTMR_ROOT must point to the NV-Segment-CTMR clone}/NV-Segment-CT"; source "$(conda info --base)/etc/profile.d/conda.sh"; conda activate vista3d-nv; rm -rf "$runtime" "$results"; mkdir -p "$runtime" "$results"; cp -a "$src/." "$runtime/"; cd "$runtime"; python -c "import json, pathlib; p=pathlib.Path(\"configs/inference.json\"); d=json.loads(p.read_text()); d[\"everything_labels\"]=[1,6,2,3]; p.write_text(json.dumps(d, indent=2)+\"\\n\"); p=pathlib.Path(\"configs/batch_inference.json\"); d=json.loads(p.read_text()); d[\"batch_resume_skip_existing\"]=False; p.write_text(json.dumps(d, indent=2)+\"\\n\")"; python -m monai.bundle run --config_file="[\"configs/inference.json\", \"configs/batch_inference.json\"]" --input_dir="$repo/runs/with_vs_without_nv/_inputs/nv_segment_ct" --output_dir="$results"'
```

Repeat 3: score 2/5, passed=no, steps=unresolved, exit=None

```bash
out="runs/with_vs_without_nv/nv_segment_ct_codex_opus/gpt55/without/repeat_3" && src="${NV_SEGMENT_CTMR_ROOT:?NV_SEGMENT_CTMR_ROOT is not set}/NV-Segment-CT" && mkdir -p "$out" && rm -rf "$out/NV-Segment-CT_runtime" && cp -a "$src" "$out/NV-Segment-CT_runtime" && python - <<'PY' "$out/NV-Segment-CT_runtime/configs/label_dict.json" "$out/label_prompt.json"
import json, re, sys
label_path, out_path = sys.argv[1], sys.argv[2]
data = json.load(open(label_path))
items = []
if isinstance(data, dict):
    for k, v in data.items():
        if isinstance(v, str):
            items.append((int(k), v))
        elif isinstance(v, dict):
            name = v.get("name") or v.get("label") or v.get("class_name") or v.get("description") or ""
            idx = v.get("index", k)
            items.append((int(idx), str(name)))
elif isinstance(data, list):
    for i, v in enumerate(data):
        if isinstance(v, str):
            items.append((i, v))
        elif isinstance(v, dict):
            name = v.get("name") or v.get("label") or v.get("class_name") or v.get("description") or ""
            idx = v.get("index", i)
            items.append((int(idx), str(name)))
def norm(s): return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")
lookup = {norm(name): idx for idx, name in items}
patterns = {
    "spleen": [r"^spleen$"],
    "liver": [r"^liver$"],
    "kidney_right": [r"^(kidney_right|right_kidney)$", r"kidney.*right|right.*kidney"],
    "kidney_left": [r"^(kidney_left|left_kidney)$", r"kidney.*left|left.*kidney"],
}
labels = []
resolved = {}
for target, pats in patterns.items():
    matches = []
    for key, idx in lookup.items():
        if any(re.search(p, key) for p in pats):
            matches.append((key, idx))
    if not matches:
        raise SystemExit(f"Could not resolve label for {target} from {label_path}")
    key, idx = sorted(matches, key=lambda x: (len(x[0]), x[0]))[0]
    resolved[target] = {"name": key, "index": idx}
    labels.append(idx)
json.dump({"label_prompt": labels, "resolved_labels": resolved}, open(out_path, "w"), indent=2)
print(labels)
PY
source "$(conda info --base)/etc/profile.d/conda.sh" && conda activate vista3d-nv && cd "$out/NV-Segment-CT_runtime" && python -m monai.bundle run --config_file configs/inference.json --input_dict "{'image':'../../../../with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz','label_prompt':$(python -c 'import json; print(json.load(open("../label_prompt.json"))["label_prompt"])')}" --output_dir="../outputs"
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
mkdir -p runs/with_vs_without_nv/nv_segment_ct_codex_opus/opus/with/repeat_3 && pip install -r skills/nv-segment-ct/requirements.txt && huggingface-cli download nvidia/NV-Segment-CT --local-dir skills/nv-segment-ct/bundle/ && python skills/nv-segment-ct/scripts/run_vista3d.py runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz --label-prompts "1,3,5,14" --output-dir runs/with_vs_without_nv/nv_segment_ct_codex_opus/opus/with/repeat_3
```

### Opus 4.7, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 4/5, passed=no, steps=unresolved, exit=1

```bash
mkdir -p runs/with_vs_without_nv/nv_segment_ct_codex_opus/opus/without/repeat_1 && cd "$NV_SEGMENT_CTMR_ROOT" && python -m monai.bundle run --config_file configs/inference.json --input_dict "{'image':'$(realpath $OLDPWD/runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz)','label_prompt':[1,3,5,14]}" --output_dir "$OLDPWD/runs/with_vs_without_nv/nv_segment_ct_codex_opus/opus/without/repeat_1"
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=1

```bash
mkdir -p runs/with_vs_without_nv/nv_segment_ct_codex_opus/opus/without/repeat_2 && cd "$NV_SEGMENT_CTMR_ROOT" && conda run -n vista3d-nv --no-capture-output python -m monai.bundle run --config_file configs/inference.json --input_dict "{'image':'$(git rev-parse --show-toplevel 2>/dev/null || pwd)/../../runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz','label_prompt':[3,1,5,14]}" --output_dir "$OLDPWD/runs/with_vs_without_nv/nv_segment_ct_codex_opus/opus/without/repeat_2"
```

Repeat 3: score 4/5, passed=no, steps=unresolved, exit=1

```bash
mkdir -p runs/with_vs_without_nv/nv_segment_ct_codex_opus/opus/without/repeat_3 && cd "$NV_SEGMENT_CTMR_ROOT" && conda run -n vista3d-nv python -m monai.bundle run --config_file configs/inference.json --input_dict "{'image':'$(cd - >/dev/null && pwd)/runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz','label_prompt':[1,3,5,14]}" --output_dir "$(cd - >/dev/null && pwd)/runs/with_vs_without_nv/nv_segment_ct_codex_opus/opus/without/repeat_3"
```

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `runs/with_vs_without_nv/studies/nv_segment_ct_codex_opus/` |
| Generated outputs | `runs/with_vs_without_nv/nv_segment_ct_codex_opus/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_segment_ct_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
