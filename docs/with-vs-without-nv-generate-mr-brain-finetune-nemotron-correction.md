# `nv_generate_mr_brain_finetune`: Nemotron LLM+SKILL.md vs LLM+README Baseline Study

Status: strict audit passed for refreshed artifacts on May 29, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

This report uses the same direct-API embedded-doc no-repair baseline protocol as the Codex/Opus comparison, but runs `nvidia/nvidia/nemotron-3-super-v3`. The linked prompt artifact is the fair A2-style path prompt for tool-enabled/NAT replication.

## Experiment Question

Does `LLM + SKILL.md` let Nemotron produce a runnable command on the first try, and how does that compare with `LLM + upstream README/guide` under the same `max_correction_steps=0` baseline?

## User Request Shape

The prompt request for the with-skill arm was:

> The MR-brain finetuning preflight input bundle is at runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset. Validate and stage the shortest preflight-scale workflow check, and write outputs under runs/with_vs_without_nv/nv_generate_mr_brain_finetune_nemotron_correction/with/repeat_1.

The staged user input for every arm was `runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset`. The source fixture `skills/nv-generate-mr-brain-finetune/fixtures` was used only to stage that neutral input path.

Fair path-prompt artifact: `tools/nat_audit/data/eval_nv_model_studies_nv_generate_mr_brain_finetune_prompts.json`

## Result

| Backend | Arm | Mean score | Passes | Steps | Exit | Tier 5 | Failed tiers |
|---|---|---:|---:|---|---|---|---|
| Nemotron | with | 3.3/5 | 2/3 | mean 0.0; unresolved 1; values [unresolved, 0, 0] | 0 (2); None (1) | preflight payload reported (2); no command extracted (1) | T1: entrypoint marker (1); T2: user input path marker (1); T3: model/modality/control marker (1) |
| Nemotron | without | 1.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | None (3) | no command extracted (2); command does not reference an expected runnable surface (1) | T1: entrypoint marker (3); T2: user input path marker (2); T3: model/modality/control marker (2) |

## Analysis

SKILL.md paired advantage: the with-skill repeats passed 2/3 with mean score 3.3/5 and steps mean 0.0; unresolved 1; values [unresolved, 0, 0]. The README-only repeats passed 0/3 with mean score 1.0/5 and steps all unresolved; values [unresolved, unresolved, unresolved].

SKILL.md paired advantage: SKILL.md wins 2/3 matched backend-repeat pairs, README-only wins 0/3, and 1/3 are ties. Pass/fail is the primary outcome; score breaks ties only when pass status is equal. Exact one-sided sign-test p=0.25 across 2 decisive pair(s).

Outcome-support gate: Supports SKILL.md advantage. SKILL.md wins 2/3 matched pair(s); README-only wins 0/3; sign-test p=0.25.

Each backend/arm/skill configuration was repeated three times. A repeat is independent: it has its own output directory, and each execution attempt inside the repeat creates a fresh venv before running the generated command. Dependency and model download caches are shared only as documented test-environment caches under `.workbench_data/with_vs_without_cache` (`PIP_CACHE_DIR=.workbench_data/with_vs_without_cache/pip`, `HF_HOME=.workbench_data/with_vs_without_cache/huggingface`, `HF_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `HUGGINGFACE_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `TRANSFORMERS_CACHE=.workbench_data/with_vs_without_cache/huggingface/transformers`, `TORCH_HOME=.workbench_data/with_vs_without_cache/torch`, `XDG_CACHE_HOME=.workbench_data/with_vs_without_cache/xdg`, `CONDA_PKGS_DIRS=.workbench_data/with_vs_without_cache/conda_pkgs`, `UV_CACHE_DIR=.workbench_data/with_vs_without_cache/uv`, `CUDA_CACHE_PATH=.workbench_data/with_vs_without_cache/cuda`, `NUMBA_CACHE_DIR=.workbench_data/with_vs_without_cache/numba`).

No correction feedback was sent in this baseline. Deterministic failure analysis is saved with each repeat so repair behavior can be studied separately later.

## Token Profiling

Token counts are provider-reported values saved in each repeat JSON. Reasoning tokens are shown only when the provider returned that subfield and are a subset of completion tokens, not an additional cost to add to total tokens. Execution time is averaged only across repeats that reached command execution; no-command-extracted repeats still count toward token totals.

| Backend | Arm | Repeats | Passes | Attempts | Prompt tokens | Completion tokens | Reasoning tokens | Total tokens | Mean total/repeat | Executed | Mean exec s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Nemotron | with | 3 | 2 | 3 | 10,590 | 3,356 | 0 | 13,946 | 4,648.7 | 2 | 0.0 |
| Nemotron | without | 3 | 0 | 3 | 3,414 | 31,827 | 0 | 35,241 | 11,747.0 | 0 | n/a |

## Nemotron Diagnostics

These diagnostics are Nemotron-only and do not change the main score. The strict result still requires exactly one valid fenced bash block. The recoverable-command columns ask whether a deterministic format adapter could have recovered command-like text without another LLM call or any domain repair.

| Arm | Repeats | Passed strict | Strict command | Recoverable malformed command | Unrecoverable formatting | Guard-ready after tolerant extraction | Static guard blocked | Format categories | Guard reasons |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| with | 3 | 2 | 2 | 1 | 0 | 1 | 0 | strict 2; malformed_fence 1 | none |
| without | 3 | 0 | 1 | 2 | 0 | 0 | 2 | strict 1; raw_shell 2 | command does not reference an expected runnable surface (2) |

Protocol-compliance failure buckets, counted per repeat and not mutually exclusive:

| Bucket | Count |
|---|---:|
| No strict command extracted | 3 |
| Wrong or missing runnable surface | 4 |
| Missing staged input path | 3 |
| Missing model/modality/control marker | 3 |
| Missing output directory | 3 |
| Unsafe/static guard block | 1 |
| Nonzero execution exit | 0 |
| Artifact contract failure after execution | 0 |

## Attempt Trace

### With-skill arm

| Repeat | Step | Score | Passed | Exit | Failed tiers | Why it did not work |
|---:|---:|---:|---|---|---|---|
| 1 | 0 | 0/5 | no | None | T1: entrypoint marker; T2: user input path marker; T3: model/modality/control marker; T4: output dir marker; T5: no command extracted | no_command: No executable bash command was extracted from the model response. Repair: Return exactly one fenced bash block containing the command to run.<br>tier_1: entrypoint marker Repair: Use the runnable surface documented for this arm.<br>tier_2: user input path marker Repair: Use the staged user input path under runs/with_vs_without_nv/_inputs/.<br>tier_3: model/modality/control marker Repair: Choose the model, modality, labels, anatomy controls, or smoke mode required by the task. |
| 2 | 0 | 5/5 | yes | 0 | none | none |
| 3 | 0 | 5/5 | yes | 0 | none | none |

### README-only arm

| Repeat | Step | Score | Passed | Exit | Failed tiers | Why it did not work |
|---:|---:|---:|---|---|---|---|
| 1 | 0 | 0/5 | no | None | T1: entrypoint marker; T2: user input path marker; T3: model/modality/control marker; T4: output dir marker; T5: no command extracted | no_command: No executable bash command was extracted from the model response. Repair: Return exactly one fenced bash block containing the command to run.<br>tier_1: entrypoint marker Repair: Use the runnable surface documented for this arm.<br>tier_2: user input path marker Repair: Use the staged user input path under runs/with_vs_without_nv/_inputs/.<br>tier_3: model/modality/control marker Repair: Choose the model, modality, labels, anatomy controls, or smoke mode required by the task. |
| 2 | 0 | 0/5 | no | None | T1: entrypoint marker; T2: user input path marker; T3: model/modality/control marker; T4: output dir marker; T5: no command extracted | no_command: No executable bash command was extracted from the model response. Repair: Return exactly one fenced bash block containing the command to run.<br>tier_1: entrypoint marker Repair: Use the runnable surface documented for this arm.<br>tier_2: user input path marker Repair: Use the staged user input path under runs/with_vs_without_nv/_inputs/.<br>tier_3: model/modality/control marker Repair: Choose the model, modality, labels, anatomy controls, or smoke mode required by the task. |
| 3 | 0 | 3/5 | no | None | T1: entrypoint marker; T5: command does not reference an expected runnable surface | tier_1: entrypoint marker Repair: Use the runnable surface documented for this arm.<br>tier_5: command does not reference an expected runnable surface Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference an expected runnable surface Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |

## Generated Commands

These are the extracted first-attempt commands by repeat.

### With-skill arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 0/5, passed=no, steps=unresolved, exit=None

_No executable bash command was extracted._

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && \
python skills/nv-generate-mr-brain-finetune/scripts/run_mr_brain_finetune.py \
  runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_datalist.json \
  --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_dataset \
  --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_finetune_nemotron_correction/with/repeat_2 \
  --modality mri_t1 \
  --preflight
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && \
python skills/nv-generate-mr-brain-finetune/scripts/run_mr_brain_finetune.py \
  runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_datalist.json \
  --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_dataset \
  --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_finetune_nemotron_correction/with/repeat_3 \
  --modality mri_t1 \
  --preflight
```

### README-only arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 0/5, passed=no, steps=unresolved, exit=None

_No executable bash command was extracted._

Repeat 2: score 0/5, passed=no, steps=unresolved, exit=None

_No executable bash command was extracted._

Repeat 3: score 3/5, passed=no, steps=unresolved, exit=None

```bash
bash -c '
OUTPUT_DIR=runs/with_vs_without_nv/nv_generate_mr_brain_finetune_nemotron_correction/without/repeat_3
INPUT_DATASET=runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset
DATA_ROOT=$(dirname "$INPUT_DATASET")
mkdir -p "$OUTPUT_DIR"
# Validate datalist: non-empty training array
if ! jq -e ".training | length > 0" "$INPUT_DATASET" >/dev/null 2>&1; then
  echo "Error: Datalist missing or empty training array" >&2; exit 1
fi
# Check each referenced image exists under data root
while IFS= read -r img; do
  if [ ! -f "$DATA_ROOT/$img" ]; then
    echo "Error: Missing image file: $img" >&2; exit 1
  fi
done < <(jq -r ".training[].image" "$INPUT_DATASET" 2>/dev/null)
# Check each modality is supported by modality_mapping.json
while IFS= read -r mod; do
  if ! grep -q "\"$mod\"" configs/modality_mapping.json; then
    echo "Error: Unsupported modality: $mod" >&2; exit 1
  fi
done < <(jq -r ".training[].modality" "$INPUT_DATASET" 2>/dev/null)
# Copy required config files to output directory
cp configs/config_network_rflow.json "$OUTPUT_DIR/"
cp configs/environment_maisi_diff_model_rflow-mr-brain.json "$OUTPUT_DIR/"
cp configs/config_maisi_diff_model_rflow-mr-brain.json "$OUTPUT_DIR/"
cp configs/modality_mapping.json "$OUTPUT_DIR/"
# Edit environment config with runtime paths
ENV_FILE="$OUTPUT_DIR/environment_maisi_diff_model_rflow-mr-brain.json"
jq --arg db "$DATA_ROOT" \
   --arg jdl "$INPUT_DATASET" \
   --arg eb "$OUTPUT_DIR/embeddings" \
   --arg md "$OUTPUT_DIR/models" \
   --arg od "$OUTPUT_DIR/inference" \
   --arg mm "$OUTPUT_DIR/modality_mapping.json" \
   ".data_base_dir = $db | .json_data_list = $jdl | .embedding_base_dir = $eb | .model_dir = $md | .output_dir = $od | .modality_mapping_path = $mm" \
   "$ENV_FILE" > "$ENV_FILE.tmp" && mv "$ENV_FILE.tmp" "$ENV_FILE"
# Edit model config for preflight-scale (tiny) training settings
MODEL_FILE="$OUTPUT_DIR/config_maisi_diff_model_rflow-mr-brain.json"
jq ".diffusion_unet_train.n_epochs = 1 |
    .diffusion_unet_train.batch_size = 2 |
    .diffusion_unet_train.learning_rate = 0.001 |
    .diffusion_unet_train.cache_rate = 0.1" \
   "$MODEL_FILE" > "$MODEL_FILE.tmp" && mv "$MODEL_FILE.tmp" "$MODEL_FILE"
# Write a small JSON summary of the validation/staging
SUMMARY_FILE="$OUTPUT_DIR/preflight_summary.json"
jq -n \
   --arg id "$INPUT_DATASET" \
   --arg dr "$DATA_ROOT" \
   --arg od "$OUTPUT_DIR" \
   '{input_dataset: $id, data_root: $dr, output_dir: $od, status: "validated"}' \
   > "$SUMMARY_FILE"
'
```

## Skill Fix Notes

No separate final-run skill fix note is recorded in the saved study JSON for this scenario; this report was regenerated from the post-fix study artifacts.

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `runs/with_vs_without_nv/studies/nv_generate_mr_brain_finetune_nemotron_correction/` |
| Generated outputs | `runs/with_vs_without_nv/nv_generate_mr_brain_finetune_nemotron_correction/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_generate_mr_brain_finetune_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
