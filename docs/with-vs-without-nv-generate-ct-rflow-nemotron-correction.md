# `nv_generate_ct_rflow`: Nemotron LLM+SKILL.md vs LLM+README Baseline Study

Status: strict audit passed for refreshed artifacts on May 29, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

This report uses the same direct-API embedded-doc no-repair baseline protocol as the Codex/Opus comparison, but runs `nvidia/nvidia/nemotron-3-super-v3`. The linked prompt artifact is the fair A2-style path prompt for tool-enabled/NAT replication.

## Experiment Question

Does `LLM + SKILL.md` let Nemotron produce a runnable command on the first try, and how does that compare with `LLM + upstream README/guide` under the same `max_correction_steps=0` baseline?

## User Request Shape

The prompt request for the with-skill arm was:

> The case request is at runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json. Synthesize one paired 3D CT image and segmentation mask for a chest case with a lung tumor, and write the output pair under runs/with_vs_without_nv/nv_generate_ct_rflow_nemotron_correction/with/repeat_1.

The staged user input for every arm was `runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json`. The source fixture `skills/nv-generate-ct-rflow/fixtures/chest_lung_tumor_controllable.json` was used only to stage that neutral input path.

Fair path-prompt artifact: `tools/nat_audit/data/eval_nv_model_studies_nv_generate_ct_rflow_prompts.json`

## Result

| Backend | Arm | Mean score | Passes | Steps | Exit | Tier 5 | Failed tiers |
|---|---|---:|---:|---|---|---|---|
| Nemotron | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | image shape=(256, 256, 256); label shape=(256, 256, 256) (3) | none |
| Nemotron | without | 1.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | None (3) | no command extracted (2); command does not reference the neutral staged input path (1) | T2: user input path marker (3); T1: entrypoint marker (2); T3: model/modality/control marker (2) |

## Analysis

SKILL.md paired advantage: the with-skill repeats passed 3/3 with mean score 5.0/5 and steps mean 0.0; unresolved 0; values [0, 0, 0]. The README-only repeats passed 0/3 with mean score 1.0/5 and steps all unresolved; values [unresolved, unresolved, unresolved].

SKILL.md paired advantage: SKILL.md wins 3/3 matched backend-repeat pairs, README-only wins 0/3, and 0/3 are ties. Pass/fail is the primary outcome; score breaks ties only when pass status is equal. Exact one-sided sign-test p=0.125 across 3 decisive pair(s).

Outcome-support gate: Supports SKILL.md advantage. SKILL.md wins 3/3 matched pair(s); README-only wins 0/3; sign-test p=0.125.

Each backend/arm/skill configuration was repeated three times. A repeat is independent: it has its own output directory, and each execution attempt inside the repeat creates a fresh venv before running the generated command. Dependency and model download caches are shared only as documented test-environment caches under `.workbench_data/with_vs_without_cache` (`PIP_CACHE_DIR=.workbench_data/with_vs_without_cache/pip`, `HF_HOME=.workbench_data/with_vs_without_cache/huggingface`, `HF_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `HUGGINGFACE_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `TRANSFORMERS_CACHE=.workbench_data/with_vs_without_cache/huggingface/transformers`, `TORCH_HOME=.workbench_data/with_vs_without_cache/torch`, `XDG_CACHE_HOME=.workbench_data/with_vs_without_cache/xdg`, `CONDA_PKGS_DIRS=.workbench_data/with_vs_without_cache/conda_pkgs`, `UV_CACHE_DIR=.workbench_data/with_vs_without_cache/uv`, `CUDA_CACHE_PATH=.workbench_data/with_vs_without_cache/cuda`, `NUMBA_CACHE_DIR=.workbench_data/with_vs_without_cache/numba`).

No correction feedback was sent in this baseline. Deterministic failure analysis is saved with each repeat so repair behavior can be studied separately later.

## Token Profiling

Token counts are provider-reported values saved in each repeat JSON. Reasoning tokens are shown only when the provider returned that subfield and are a subset of completion tokens, not an additional cost to add to total tokens. Execution time is averaged only across repeats that reached command execution; no-command-extracted repeats still count toward token totals.

| Backend | Arm | Repeats | Passes | Attempts | Prompt tokens | Completion tokens | Reasoning tokens | Total tokens | Mean total/repeat | Executed | Mean exec s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Nemotron | with | 3 | 3 | 3 | 9,831 | 5,664 | 0 | 15,495 | 5,165.0 | 3 | 138.2 |
| Nemotron | without | 3 | 0 | 3 | 9,630 | 19,533 | 0 | 29,163 | 9,721.0 | 0 | n/a |

## Nemotron Diagnostics

These diagnostics are Nemotron-only and do not change the main score. The strict result still requires exactly one valid fenced bash block. The recoverable-command columns ask whether a deterministic format adapter could have recovered command-like text without another LLM call or any domain repair.

| Arm | Repeats | Passed strict | Strict command | Recoverable malformed command | Unrecoverable formatting | Guard-ready after tolerant extraction | Static guard blocked | Format categories | Guard reasons |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| with | 3 | 3 | 3 | 0 | 0 | 0 | 0 | strict 3 | none |
| without | 3 | 0 | 1 | 2 | 0 | 0 | 2 | strict 1; raw_shell 2 | command does not reference the neutral staged input path (2) |

Protocol-compliance failure buckets, counted per repeat and not mutually exclusive:

| Bucket | Count |
|---|---:|
| No strict command extracted | 2 |
| Wrong or missing runnable surface | 2 |
| Missing staged input path | 3 |
| Missing model/modality/control marker | 2 |
| Missing output directory | 2 |
| Unsafe/static guard block | 1 |
| Nonzero execution exit | 0 |
| Artifact contract failure after execution | 0 |

## Attempt Trace

### With-skill arm

| Repeat | Step | Score | Passed | Exit | Failed tiers | Why it did not work |
|---:|---:|---:|---|---|---|---|
| 1 | 0 | 5/5 | yes | 0 | none | none |
| 2 | 0 | 5/5 | yes | 0 | none | none |
| 3 | 0 | 5/5 | yes | 0 | none | none |

### README-only arm

| Repeat | Step | Score | Passed | Exit | Failed tiers | Why it did not work |
|---:|---:|---:|---|---|---|---|
| 1 | 0 | 3/5 | no | None | T2: user input path marker; T5: command does not reference the neutral staged input path | tier_2: user input path marker Repair: Use the staged user input path under runs/with_vs_without_nv/_inputs/.<br>tier_5: command does not reference the neutral staged input path Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference the neutral staged input path Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
| 2 | 0 | 0/5 | no | None | T1: entrypoint marker; T2: user input path marker; T3: model/modality/control marker; T4: output dir marker; T5: no command extracted | no_command: No executable bash command was extracted from the model response. Repair: Return exactly one fenced bash block containing the command to run.<br>tier_1: entrypoint marker Repair: Use the runnable surface documented for this arm.<br>tier_2: user input path marker Repair: Use the staged user input path under runs/with_vs_without_nv/_inputs/.<br>tier_3: model/modality/control marker Repair: Choose the model, modality, labels, anatomy controls, or smoke mode required by the task. |
| 3 | 0 | 0/5 | no | None | T1: entrypoint marker; T2: user input path marker; T3: model/modality/control marker; T4: output dir marker; T5: no command extracted | no_command: No executable bash command was extracted from the model response. Repair: Return exactly one fenced bash block containing the command to run.<br>tier_1: entrypoint marker Repair: Use the runnable surface documented for this arm.<br>tier_2: user input path marker Repair: Use the staged user input path under runs/with_vs_without_nv/_inputs/.<br>tier_3: model/modality/control marker Repair: Choose the model, modality, labels, anatomy controls, or smoke mode required by the task. |

## Generated Commands

These are the extracted first-attempt commands by repeat.

### With-skill arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-$HOME/nv-generate-ctmr}" && \
python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && \
python skills/nv-generate-ct-rflow/scripts/run_rflow_ct.py \
  runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json \
  --output-dir runs/with_vs_without_nv/nv_generate_ct_rflow_nemotron_correction/with/repeat_1 \
  --random-seed 0 \
  --version rflow-ct
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-$HOME/nv-generate-ctmr}" && \
python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && \
python skills/nv-generate-ct-rflow/scripts/run_rflow_ct.py \
  runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json \
  --output-dir runs/with_vs_without_nv/nv_generate_ct_rflow_nemotron_correction/with/repeat_2 \
  --random-seed 0 \
  --version rflow-ct
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-$HOME/nv-generate-ctmr}" && \
python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && \
python skills/nv-generate-ct-rflow/scripts/run_rflow_ct.py \
    runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/request.json \
    --output-dir runs/with_vs_without_nv/nv_generate_ct_rflow_nemotron_correction/with/repeat_3 \
    --random-seed 42 \
    --version rflow-ct
```

### README-only arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 3/5, passed=no, steps=unresolved, exit=None

```bash
mkdir -p runs/with_vs_without_nv/nv_generate_ct_rflow_nemotron_correction/without/repeat_1 && \
cp configs/config_network_rflow.json runs/with_vs_without_nv/nv_generate_ct_rflow_nemotron_correction/without/repeat_1/ && \
cp configs/config_infer.json runs/with_vs_without_nv/nv_generate_ct_rflow_nemotron_correction/without/repeat_1/ && \
cp configs/environment_rflow-ct.json runs/with_vs_without_nv/nv_generate_ct_rflow_nemotron_correction/without/repeat_1/ && \
sed -i 's/"body_region":.*/"body_region": ["chest"]/' runs/with_vs_without_nv/nv_generate_ct_rflow_nemotron_correction/without/repeat_1/config_infer.json && \
sed -i 's/"anatomy_list":.*/"anatomy_list": ["lung", "tumors"]/' runs/with_vs_without_nv/nv_generate_ct_rflow_nemotron_correction/without/repeat_1/config_infer.json && \
sed -i 's/"controllable_anatomy_size":.*/"controllable_anatomy_size": []/' runs/with_vs_without_nv/nv_generate_ct_rflow_nemotron_correction/without/repeat_1/config_infer.json && \
sed -i 's/"output_size":.*/"output_size": [256, 256, 256]/' runs/with_vs_without_nv/nv_generate_ct_rflow_nemotron_correction/without/repeat_1/config_infer.json && \
sed -i 's/"spacing":.*/"spacing": [1.5, 1.5, 1.5]/' runs/with_vs_without_nv/nv_generate_ct_rflow_nemotron_correction/without/repeat_1/config_infer.json && \
sed -i 's/"modality":.*/"modality": 1/' runs/with_vs_without_nv/nv_generate_ct_rflow_nemotron_correction/without/repeat_1/config_infer.json && \
sed -i 's/"mask_generation_num_inference_steps":.*/"mask_generation_num_inference_steps": 1000/' runs/with_vs_without_nv/nv_generate_ct_rflow_nemotron_correction/without/repeat_1/config_infer.json && \
sed -i 's/"cfg_guidance_scale":.*/"cfg_guidance_scale": 7.5/' runs/with_vs_without_nv/nv_generate_ct_rflow_nemotron_correction/without/repeat_1/config_infer.json && \
export MONAI_DATA_DIRECTORY=runs/with_vs_without_nv/nv_generate_ct_rflow_nemotron_correction/without/repeat_1/temp_work_dir && \
network="rflow" && \
generate_version="rflow-ct" && \
python -m scripts.inference \
    -t runs/with_vs_without_nv/nv_generate_ct_rflow_nemotron_correction/without/repeat_1/config_network_rflow.json \
    -i runs/with_vs_without_nv/nv_generate_ct_rflow_nemotron_correction/without/repeat_1/config_infer.json \
    -e runs/with_vs_without_nv/nv_generate_ct_rflow_nemotron_correction/without/repeat_1/environment_rflow-ct.json \
    --random-seed 0 --version ${generate_version}
```

Repeat 2: score 0/5, passed=no, steps=unresolved, exit=None

_No executable bash command was extracted._

Repeat 3: score 0/5, passed=no, steps=unresolved, exit=None

_No executable bash command was extracted._

## Skill Fix Notes

No separate final-run skill fix note is recorded in the saved study JSON for this scenario; this report was regenerated from the post-fix study artifacts.

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `runs/with_vs_without_nv/studies/nv_generate_ct_rflow_nemotron_correction/` |
| Generated outputs | `runs/with_vs_without_nv/nv_generate_ct_rflow_nemotron_correction/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_generate_ct_rflow_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
