# `nv_segment_ctmr`: Codex/Opus LLM+SKILL.md vs LLM+README

Status: strict audit passed for refreshed artifacts on May 29, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

This report compares `LLM + SKILL.md` with `LLM + upstream README/guide`. The completed direct-API run used the corrected embedded-doc minimal prompt because those backends cannot read repo files. The fair NAT/tool-agent prompt artifact is A2-style: it gives a natural user request, a neutral staged input path, an output directory, and tells the agent which arm-specific document to read. It does not spell out operational details such as entrypoints, labels, model variants, or config filenames outside the documentation arm.

## Experiment Question

Does `LLM + SKILL.md` make an agent better at reading documentation and taking the right action than `LLM + upstream README/guide`?

## User Request Shape

The prompt request for the GPT-5.5 with-skill arm was:

> The input CT volume is at runs/with_vs_without_nv/_inputs/nv_segment_ctmr/input.nii.gz. Run the CT body segmentation workflow and write the label map under runs/with_vs_without_nv/nv_segment_ctmr_codex_opus/gpt55/with/repeat_1.

The staged user input for every arm was `runs/with_vs_without_nv/_inputs/nv_segment_ctmr/input.nii.gz`. The source fixture `skills/nv-segment-ct/fixtures/spleen_03.nii.gz` was used only to stage that neutral input path.

Fair path-prompt artifact: `tools/nat_audit/data/eval_nv_model_studies_nv_segment_ctmr_prompts.json`

## Result

| Backend | Arm | Mean score | Passes | Steps | Exit | Tier 5 | Failed tiers |
|---|---|---:|---:|---|---|---|---|
| GPT-5.5 / Codex | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | shape=(512, 512, 40) (3) | none |
| GPT-5.5 / Codex | without | 4.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | None (2); 1 (1) | blocked unsafe command fragment: rm (2); exit 1 (1) | T5: blocked unsafe command fragment: rm (2); T5: exit 1 (1) |
| Opus 4.7 | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | shape=(512, 512, 40) (3) | none |
| Opus 4.7 | without | 4.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | 1 (3) | exit 1 (3) | T5: exit 1 (3) |

## Analysis

SKILL.md paired advantage: the with-skill arms passed 6/6 backend-repeat trials with an average score of 5.0/5; the README-only arms passed 0/6 backend-repeat trials with an average score of 4.0/5.

SKILL.md paired advantage: SKILL.md wins 6/6 matched backend-repeat pairs, README-only wins 0/6, and 0/6 are ties. Pass/fail is the primary outcome; score breaks ties only when pass status is equal. Exact one-sided sign-test p=0.01562 across 6 decisive pair(s).

Outcome-support gate: Supports SKILL.md advantage. SKILL.md wins 6/6 matched pair(s); README-only wins 0/6; sign-test p=0.01562.

Each backend/arm/skill configuration was repeated three times. A repeat is independent: it has its own output directory, and each execution attempt inside the repeat creates a fresh venv before running the generated command. Dependency and model download caches are shared only as documented test-environment caches under `.workbench_data/with_vs_without_cache` (`PIP_CACHE_DIR=.workbench_data/with_vs_without_cache/pip`, `HF_HOME=.workbench_data/with_vs_without_cache/huggingface`, `HF_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `HUGGINGFACE_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `TRANSFORMERS_CACHE=.workbench_data/with_vs_without_cache/huggingface/transformers`, `TORCH_HOME=.workbench_data/with_vs_without_cache/torch`, `XDG_CACHE_HOME=.workbench_data/with_vs_without_cache/xdg`, `CONDA_PKGS_DIRS=.workbench_data/with_vs_without_cache/conda_pkgs`, `UV_CACHE_DIR=.workbench_data/with_vs_without_cache/uv`, `CUDA_CACHE_PATH=.workbench_data/with_vs_without_cache/cuda`, `NUMBA_CACHE_DIR=.workbench_data/with_vs_without_cache/numba`).

The main baseline uses `max_correction_steps=0`: each repeat sends one prompt, executes the extracted command once, and records pass/fail, runtime, tokens, and deterministic failure analysis. The repair-loop implementation remains available for separate diagnostic experiments, but it is not part of this comparison.

All with-skill repeats exited successfully and produced artifacts accepted by the deterministic grader. That means the final SKILL.md surface was repeatable for both tested agent backends.

The README-only commands did not pass tier 5. Typical failure modes were unsafe generated shell cleanup, missing schema fields, missing model/control details, or upstream commands that did not execute cleanly from Medical AI Skills root.

Tier 2 is intentionally strict: a command only earns it if it uses the staged user input path `runs/with_vs_without_nv/_inputs/nv_segment_ctmr/input.nii.gz`.

## Token Profiling

Token counts are provider-reported values saved in each repeat JSON. Reasoning tokens are shown only when the provider returned that subfield and are a subset of completion tokens, not an additional cost to add to total tokens. Execution time is averaged only across repeats that reached command execution; no-command-extracted repeats still count toward token totals.

| Backend | Arm | Repeats | Passes | Attempts | Prompt tokens | Completion tokens | Reasoning tokens | Total tokens | Mean total/repeat | Executed | Mean exec s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GPT-5.5 / Codex | with | 3 | 3 | 3 | 7,029 | 778 | 313 | 7,807 | 2,602.3 | 3 | 48.8 |
| GPT-5.5 / Codex | without | 3 | 0 | 3 | 11,457 | 11,229 | 10,243 | 22,686 | 7,562.0 | 1 | 2.4 |
| Opus 4.7 | with | 3 | 3 | 3 | 12,600 | 820 | 0 | 13,420 | 4,473.3 | 3 | 53.5 |
| Opus 4.7 | without | 3 | 0 | 3 | 18,705 | 743 | 0 | 19,448 | 6,482.7 | 3 | 0.7 |

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

Before the final rerun, `SKILL.md` was tightened to name `scripts/run_ctmr.py` as the exact runnable surface and to state the `CT_BODY` modality expected for this CT body segmentation task.

## Generated Commands

These are the extracted first-attempt commands by repeat.

### GPT-5.5 / Codex, with arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_SEGMENT_CTMR_ROOT="${NV_SEGMENT_CTMR_ROOT:-.workbench_data/upstreams/NV-Segment-CTMR/NV-Segment-CTMR}" && python -m pip install "monai>=1.5,<1.6" "numpy<2" nibabel scipy typer PyYAML fire huggingface_hub pytorch-ignite einops && python skills/nv-segment-ctmr/scripts/run_ctmr.py runs/with_vs_without_nv/_inputs/nv_segment_ctmr/input.nii.gz --modality CT_BODY --output-dir runs/with_vs_without_nv/nv_segment_ctmr_codex_opus/gpt55/with/repeat_1
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_SEGMENT_CTMR_ROOT="${NV_SEGMENT_CTMR_ROOT:-.workbench_data/upstreams/NV-Segment-CTMR/NV-Segment-CTMR}" && python -m pip install "monai>=1.5,<1.6" "numpy<2" nibabel scipy typer PyYAML fire huggingface_hub pytorch-ignite einops && python skills/nv-segment-ctmr/scripts/run_ctmr.py runs/with_vs_without_nv/_inputs/nv_segment_ctmr/input.nii.gz --modality CT_BODY --output-dir runs/with_vs_without_nv/nv_segment_ctmr_codex_opus/gpt55/with/repeat_2
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_SEGMENT_CTMR_ROOT="${NV_SEGMENT_CTMR_ROOT:-.workbench_data/upstreams/NV-Segment-CTMR/NV-Segment-CTMR}" && python -m pip install "monai>=1.5,<1.6" "numpy<2" nibabel scipy typer PyYAML fire huggingface_hub pytorch-ignite einops && python skills/nv-segment-ctmr/scripts/run_ctmr.py runs/with_vs_without_nv/_inputs/nv_segment_ctmr/input.nii.gz --modality CT_BODY --output-dir runs/with_vs_without_nv/nv_segment_ctmr_codex_opus/gpt55/with/repeat_3
```

### GPT-5.5 / Codex, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 4/5, passed=no, steps=unresolved, exit=1

```bash
source "$(conda info --base)/etc/profile.d/conda.sh" && conda activate vista3d-nv && REPO_ROOT="$PWD" && IN="$REPO_ROOT/runs/with_vs_without_nv/_inputs/nv_segment_ctmr/input.nii.gz" && OUT="$REPO_ROOT/runs/with_vs_without_nv/nv_segment_ctmr_codex_opus/gpt55/without/repeat_1" && RUNTIME="$OUT/runtime/NV-Segment-CTMR" && mkdir -p "$RUNTIME" && rsync -a --delete --exclude='.git' "${NV_SEGMENT_CTMR_ROOT:?NV_SEGMENT_CTMR_ROOT must point to the NV-Segment-CTMR/NV-Segment-CTMR upstream repo}/" "$RUNTIME/" && cd "$RUNTIME" && python -m monai.bundle run --config_file configs/inference.json --input_dict "{'image':'$IN'}" --output_dir="$OUT" --modality CT_BODY
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=None

```bash
bash -lc 'set -euo pipefail; repo_root="$PWD"; input_rel="runs/with_vs_without_nv/_inputs/nv_segment_ctmr/input.nii.gz"; out_rel="runs/with_vs_without_nv/nv_segment_ctmr_codex_opus/gpt55/without/repeat_2"; out_abs="$repo_root/$out_rel"; [ -f "$repo_root/$input_rel" ]; mkdir -p "$out_abs/_runtime"; if [ -n "${NV_SEGMENT_CTMR_ROOT:-}" ] && [ -d "$NV_SEGMENT_CTMR_ROOT/NV-Segment-CTMR/configs" ]; then src="$NV_SEGMENT_CTMR_ROOT/NV-Segment-CTMR"; elif [ -n "${NV_SEGMENT_CTMR_ROOT:-}" ] && [ -d "$NV_SEGMENT_CTMR_ROOT/configs" ]; then src="$NV_SEGMENT_CTMR_ROOT"; else echo "NV_SEGMENT_CTMR_ROOT must point to the NV-Segment-CTMR checkout containing configs/inference.json" >&2; exit 1; fi; runtime="$out_abs/_runtime/NV-Segment-CTMR"; rm -rf "$runtime"; mkdir -p "$runtime"; cp -a "$src"/. "$runtime"/; source "$(conda info --base)/etc/profile.d/conda.sh"; conda activate vista3d-nv; cd "$runtime"; python -m pip install -r requirements.txt; python -m monai.bundle run --config_file configs/inference.json --input_dict "{\"image\":\"$repo_root/$input_rel\"}" --modality CT_BODY --output_dir "$out_abs"'
```

Repeat 3: score 4/5, passed=no, steps=unresolved, exit=None

```bash
bash -lc 'set -euo pipefail; source "$(conda info --base)/etc/profile.d/conda.sh"; conda activate vista3d-nv; REPO_ROOT="$PWD"; INPUT="$REPO_ROOT/runs/with_vs_without_nv/_inputs/nv_segment_ctmr/input.nii.gz"; OUT="$REPO_ROOT/runs/with_vs_without_nv/nv_segment_ctmr_codex_opus/gpt55/without/repeat_3"; SRC="${NV_SEGMENT_CTMR_ROOT:-}"; if [ -n "$SRC" ] && [ -d "$SRC/NV-Segment-CTMR/configs" ]; then SRC="$SRC/NV-Segment-CTMR"; fi; if [ -z "$SRC" ] || [ ! -d "$SRC/configs" ]; then CFG="$(find "$REPO_ROOT/.workbench_data/upstreams" -path "*/configs/inference.json" -print -quit)"; SRC="$(dirname "$(dirname "$CFG")")"; fi; RUNTIME="$OUT/_nv_segment_ctmr_runtime"; mkdir -p "$OUT"; rm -rf "$RUNTIME"; mkdir -p "$RUNTIME"; rsync -a --exclude ".git" "$SRC"/ "$RUNTIME"/; cd "$RUNTIME"; python -m monai.bundle run --config_file configs/inference.json --input_dict "{'\''image'\'':'\''$INPUT'\''}" --output_dir "$OUT" --modality CT_BODY'
```

### Opus 4.7, with arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_SEGMENT_CTMR_ROOT="${NV_SEGMENT_CTMR_ROOT:-.workbench_data/upstreams/NV-Segment-CTMR/NV-Segment-CTMR}" && \
python -m pip install "monai>=1.5,<1.6" "numpy<2" nibabel scipy typer PyYAML fire huggingface_hub pytorch-ignite einops && \
python skills/nv-segment-ctmr/scripts/run_ctmr.py runs/with_vs_without_nv/_inputs/nv_segment_ctmr/input.nii.gz \
  --modality CT_BODY \
  --output-dir runs/with_vs_without_nv/nv_segment_ctmr_codex_opus/opus/with/repeat_1
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_SEGMENT_CTMR_ROOT="${NV_SEGMENT_CTMR_ROOT:-.workbench_data/upstreams/NV-Segment-CTMR/NV-Segment-CTMR}" && python -m pip install "monai>=1.5,<1.6" "numpy<2" nibabel scipy typer PyYAML fire huggingface_hub pytorch-ignite einops && python skills/nv-segment-ctmr/scripts/run_ctmr.py runs/with_vs_without_nv/_inputs/nv_segment_ctmr/input.nii.gz --modality CT_BODY --output-dir runs/with_vs_without_nv/nv_segment_ctmr_codex_opus/opus/with/repeat_2
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_SEGMENT_CTMR_ROOT="${NV_SEGMENT_CTMR_ROOT:-.workbench_data/upstreams/NV-Segment-CTMR/NV-Segment-CTMR}" && python -m pip install "monai>=1.5,<1.6" "numpy<2" nibabel scipy typer PyYAML fire huggingface_hub pytorch-ignite einops && python skills/nv-segment-ctmr/scripts/run_ctmr.py runs/with_vs_without_nv/_inputs/nv_segment_ctmr/input.nii.gz --modality CT_BODY --output-dir runs/with_vs_without_nv/nv_segment_ctmr_codex_opus/opus/with/repeat_3
```

### Opus 4.7, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 4/5, passed=no, steps=unresolved, exit=1

```bash
mkdir -p runs/with_vs_without_nv/nv_segment_ctmr_codex_opus/opus/without/repeat_1 && cd "$NV_SEGMENT_CTMR_ROOT" && conda run -n vista3d-nv --no-capture-output python -m monai.bundle run --config_file configs/inference.json --input_dict "{'image':'$(realpath -m "$OLDPWD/runs/with_vs_without_nv/_inputs/nv_segment_ctmr/input.nii.gz")'}" --output_dir "$(realpath -m "$OLDPWD/runs/with_vs_without_nv/nv_segment_ctmr_codex_opus/opus/without/repeat_1")" --modality CT_BODY
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=1

```bash
mkdir -p runs/with_vs_without_nv/nv_segment_ctmr_codex_opus/opus/without/repeat_2 && cd "$NV_SEGMENT_CTMR_ROOT" && conda run -n vista3d-nv --no-capture-output python -m monai.bundle run --config_file configs/inference.json --input_dict "{'image':'$OLDPWD/runs/with_vs_without_nv/_inputs/nv_segment_ctmr/input.nii.gz'}" --modality CT_BODY --output_dir "$OLDPWD/runs/with_vs_without_nv/nv_segment_ctmr_codex_opus/opus/without/repeat_2"
```

Repeat 3: score 4/5, passed=no, steps=unresolved, exit=1

```bash
mkdir -p runs/with_vs_without_nv/nv_segment_ctmr_codex_opus/opus/without/repeat_3 && cd "$NV_SEGMENT_CTMR_ROOT" && python -m monai.bundle run --config_file configs/inference.json --input_dict "{'image':'$(realpath $OLDPWD/runs/with_vs_without_nv/_inputs/nv_segment_ctmr/input.nii.gz)'}" --modality CT_BODY --output_dir "$OLDPWD/runs/with_vs_without_nv/nv_segment_ctmr_codex_opus/opus/without/repeat_3"
```

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `runs/with_vs_without_nv/studies/nv_segment_ctmr_codex_opus/` |
| Generated outputs | `runs/with_vs_without_nv/nv_segment_ctmr_codex_opus/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_segment_ctmr_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
