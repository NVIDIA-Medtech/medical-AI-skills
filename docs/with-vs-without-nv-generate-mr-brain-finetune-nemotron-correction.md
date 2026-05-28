# `nv_generate_mr_brain_finetune`: Nemotron LLM+SKILL.md vs LLM+README Baseline Study

Status: strict audit passed for refreshed artifacts on May 28, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

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
| Nemotron | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | preflight payload reported (3) | none |
| Nemotron | without | 3.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | None (3) | command does not reference an expected runnable surface (3) | T1: entrypoint marker (3); T5: command does not reference an expected runnable surface (3) |

## Analysis

SKILL.md paired advantage: the with-skill repeats passed 3/3 with mean score 5.0/5 and steps mean 0.0; unresolved 0; values [0, 0, 0]. The README-only repeats passed 0/3 with mean score 3.0/5 and steps all unresolved; values [unresolved, unresolved, unresolved].

SKILL.md paired advantage: SKILL.md wins 3/3 matched backend-repeat pairs, README-only wins 0/3, and 0/3 are ties. Pass/fail is the primary outcome; score breaks ties only when pass status is equal. Exact one-sided sign-test p=0.125 across 3 decisive pair(s).

Outcome-support gate: Supports SKILL.md advantage. SKILL.md wins 3/3 matched pair(s); README-only wins 0/3; sign-test p=0.125.

Each backend/arm/skill configuration was repeated three times. A repeat is independent: it has its own output directory, and each execution attempt inside the repeat creates a fresh venv before running the generated command. Dependency and model download caches are shared only as documented test-environment caches under `.workbench_data/with_vs_without_cache` (`PIP_CACHE_DIR=.workbench_data/with_vs_without_cache/pip`, `HF_HOME=.workbench_data/with_vs_without_cache/huggingface`, `HF_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `HUGGINGFACE_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `TRANSFORMERS_CACHE=.workbench_data/with_vs_without_cache/huggingface/transformers`, `TORCH_HOME=.workbench_data/with_vs_without_cache/torch`, `XDG_CACHE_HOME=.workbench_data/with_vs_without_cache/xdg`, `CONDA_PKGS_DIRS=.workbench_data/with_vs_without_cache/conda_pkgs`, `UV_CACHE_DIR=.workbench_data/with_vs_without_cache/uv`, `CUDA_CACHE_PATH=.workbench_data/with_vs_without_cache/cuda`, `NUMBA_CACHE_DIR=.workbench_data/with_vs_without_cache/numba`).

No correction feedback was sent in this baseline. Deterministic failure analysis is saved with each repeat so repair behavior can be studied separately later.

## Token Profiling

Token counts are provider-reported values saved in each repeat JSON. Reasoning tokens are shown only when the provider returned that subfield and are a subset of completion tokens, not an additional cost to add to total tokens. Execution time is averaged only across repeats that reached command execution; no-command-extracted repeats still count toward token totals.

| Backend | Arm | Repeats | Passes | Attempts | Prompt tokens | Completion tokens | Reasoning tokens | Total tokens | Mean total/repeat | Executed | Mean exec s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Nemotron | with | 3 | 3 | 3 | 5,310 | 2,985 | 0 | 8,295 | 2,765.0 | 3 | 0.0 |
| Nemotron | without | 3 | 0 | 3 | 3,414 | 16,704 | 0 | 20,118 | 6,706.0 | 0 | n/a |

## Nemotron Diagnostics

These diagnostics are Nemotron-only and do not change the main score. The strict result still requires exactly one valid fenced bash block. The recoverable-command columns ask whether a deterministic format adapter could have recovered command-like text without another LLM call or any domain repair.

| Arm | Repeats | Passed strict | Strict command | Recoverable malformed command | Unrecoverable formatting | Guard-ready after tolerant extraction | Static guard blocked | Format categories | Guard reasons |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| with | 3 | 3 | 3 | 0 | 0 | 0 | 0 | strict 3 | none |
| without | 3 | 0 | 3 | 0 | 0 | 0 | 0 | strict 3 | none |

Protocol-compliance failure buckets, counted per repeat and not mutually exclusive:

| Bucket | Count |
|---|---:|
| No strict command extracted | 0 |
| Wrong or missing runnable surface | 3 |
| Missing staged input path | 0 |
| Missing model/modality/control marker | 0 |
| Missing output directory | 0 |
| Unsafe/static guard block | 3 |
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
| 1 | 0 | 3/5 | no | None | T1: entrypoint marker; T5: command does not reference an expected runnable surface | tier_1: entrypoint marker Repair: Use the runnable surface documented for this arm.<br>tier_5: command does not reference an expected runnable surface Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference an expected runnable surface Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
| 2 | 0 | 3/5 | no | None | T1: entrypoint marker; T5: command does not reference an expected runnable surface | tier_1: entrypoint marker Repair: Use the runnable surface documented for this arm.<br>tier_5: command does not reference an expected runnable surface Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference an expected runnable surface Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
| 3 | 0 | 3/5 | no | None | T1: entrypoint marker; T5: command does not reference an expected runnable surface | tier_1: entrypoint marker Repair: Use the runnable surface documented for this arm.<br>tier_5: command does not reference an expected runnable surface Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference an expected runnable surface Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |

## Generated Commands

These are the extracted first-attempt commands by repeat.

### With-skill arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && \
python skills/nv-generate-mr-brain-finetune/scripts/run_mr_brain_finetune.py \
  runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_datalist.json \
  --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_dataset \
  --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_finetune_nemotron_correction/with/repeat_1 \
  --preflight
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python skills/nv-generate-mr-brain-finetune/scripts/run_mr_brain_finetune.py runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_datalist.json --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_dataset --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_finetune_nemotron_correction/with/repeat_2 --preflight
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && \
python skills/nv-generate-mr-brain-finetune/scripts/run_mr_brain_finetune.py \
  runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_datalist.json \
  --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/preflight_dataset \
  --output-dir runs/with_vs_without_nv/nv_generate_mr_brain_finetune_nemotron_correction/with/repeat_3 \
  --preflight
```

### README-only arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 3/5, passed=no, steps=unresolved, exit=None

```bash
OUTPUT_DIR=runs/with_vs_without_nv/nv_generate_mr_brain_finetune_nemotron_correction/without/repeat_1 && \
INPUT_DATASET=runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset && \
mkdir -p "$OUTPUT_DIR" && \
cp "$INPUT_DATASET" "$OUTPUT_DIR/datalist.json" && \
cp "$NV_GENERATE_ROOT/configs/config_network_rflow.json" "$OUTPUT_DIR/" && \
cp "$NV_GENERATE_ROOT/configs/environment_maisi_diff_model_rflow-mr-brain.json" "$OUTPUT_DIR/" && \
cp "$NV_GENERATE_ROOT/configs/config_maisi_diff_model_rflow-mr-brain.json" "$OUTPUT_DIR/" && \
cp "$NV_GENERATE_ROOT/configs/modality_mapping.json" "$OUTPUT_DIR/" && \
python3 -c '
import os, json, sys
out_dir = os.environ["OUTPUT_DIR"]
datalist_path = os.path.join(out_dir, "datalist.json")
env_path = os.path.join(out_dir, "environment_maisi_diff_model_rflow-mr-brain.json")
model_path = os.path.join(out_dir, "config_maisi_diff_model_rflow-mr-brain.json")
modality_path = os.path.join(out_dir, "modality_mapping.json")
try:
    with open(datalist_path) as f:
        datalist = json.load(f)
except Exception as e:
    print(f"Failed to load datalist: {e}", file=sys.stderr)
    sys.exit(1)
if not isinstance(datalist, dict):
    print("Datalist is not a dict", file=sys.stderr); sys.exit(1)
training = datalist.get("training", [])
if not isinstance(training, list) or len(training) == 0:
    print("Training list missing or empty", file=sys.stderr); sys.exit(1)
data_base_dir = os.path.dirname(datalist_path)
supported_prefix = "mri_"
for i, entry in enumerate(training):
    if not isinstance(entry, dict):
        print(f"Training entry {i} not a dict", file=sys.stderr); sys.exit(1)
    img_rel = entry.get("image")
    modality = entry.get("modality")
    if not img_rel or not isinstance(img_rel, str):
        print(f"Training entry {i} missing or invalid image", file=sys.stderr); sys.exit(1)
    if not modality or not isinstance(modality, str):
        print(f"Training entry {i} missing or invalid modality", file=sys.stderr); sys.exit(1)
    if not modality.startswith(supported_prefix):
        print(f"Training entry {i} modality not supported: {modality}", file=sys.stderr); sys.exit(1)
    img_path = os.path.join(data_base_dir, img_rel)
    if not os.path.exists(img_path):
        print(f"Training entry {i} image not found: {img_path}", file=sys.stderr); sys.exit(1)
try:
    with open(env_path) as f:
        env_cfg = json.load(f)
except Exception as e:
    print(f"Failed to load env config: {e}", file=sys.stderr); sys.exit(1)
env_cfg["data_base_dir"] = data_base_dir
env_cfg["json_data_list"] = datalist_path
env_cfg["embedding_base_dir"] = os.path.join(out_dir, "embeddings")
env_cfg["model_dir"] = os.path.join(out_dir, "models")
env_cfg["output_dir"] = os.path.join(out_dir, "inference")
env_cfg["modality_mapping_path"] = modality_path
env_cfg["trained_autoencoder_path"] = ""
env_cfg["existing_ckpt_filepath"] = ""
with open(env_path, "w") as f:
    json.dump(env_cfg, f, indent=2)
try:
    with open(model_path) as f:
        model_cfg = json.load(f)
except Exception as e:
    print(f"Failed to load model config: {e}", file=sys.stderr); sys.exit(1)
if "diffusion_unet_train" not in model_cfg:
    model_cfg["diffusion_unet_train"] = {}
train = model_cfg["diffusion_unet_train"]
train["n_epochs"] = 1
train["batch_size"] = 2
train["learning_rate"] = 0.0001
train["cache_rate"] = 0.0
with open(model_path, "w") as f:
    json.dump(model_cfg, f, indent=2)
summary = {
    "status": "preflight_ok",
    "checks": {
        "datalist_valid": True,
        "training_count": len(training),
        "data_base_dir": data_base_dir,
        "env_config_updated": True,
        "model_config_updated": True
    }
}
summary_path = os.path.join(out_dir, "preflight_summary.json")
with open(summary_path, "w") as f:
    json.dump(summary, f, indent=2)
print("Preflight summary written to", summary_path)
' && \
echo "Preflight workflow completed."
```

Repeat 2: score 3/5, passed=no, steps=unresolved, exit=None

```bash
mkdir -p runs/with_vs_without_nv/nv_generate_mr_brain_finetune_nemotron_correction/without/repeat_2/{configs,embeddings,models,inference} && \
cp runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/datalist.json runs/with_vs_without_nv/nv_generate_mr_brain_finetune_nemotron_correction/without/repeat_2/datalist.json && \
cp -r upstream/NV-Generate-CTMR/configs/* runs/with_vs_without_nv/nv_generate_mr_brain_finetune_nemotron_correction/without/repeat_2/configs/ && \
TRAIN_COUNT=$(jq '.training | length' runs/with_vs_without_nv/nv_generate_mr_brain_finetune_nemotron_correction/without/repeat_2/datalist.json) && \
[ "$TRAIN_COUNT" -gt 0 ] && \
( jq -r '.training[].image' runs/with_vs_without_nv/nv_generate_mr_brain_finetune_nemotron_correction/without/repeat_2/datalist.json | while read img; do [ -f runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset/$img ] || { echo "Missing image $img"; exit 1; }; done ) && \
( jq -r '.training[].modality' runs/with_vs_without_nv/nv_generate_mr_brain_finetune_nemotron_correction/without/repeat_2/datalist.json | while read mod; do case "$mod" in mri_t1|mri_t2|mri_flair|mri_swi|mri_t1_skull_stripped|mri_t2_skull_stripped|mri_flair_skull_stripped|mri_swu_skull_stripped) ;; *) echo "Unsupported modality $mod"; exit 1;; esac; done ) && \
ENV_CFG=runs/with_vs_without_nv/nv_generate_mr_brain_finetune_nemotron_correction/without/repeat_2/configs/environment_maisi_diff_model_rflow-mr-brain.json && \
jq --arg data_base runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset \
   --arg json_data runs/with_vs_without_nv/nv_generate_mr_brain_finetune_nemotron_correction/without/repeat_2/datalist.json \
   --arg emb_base runs/with_vs_without_nv/nv_generate_mr_brain_finetune_nemotron_correction/without/repeat_2/embeddings \
   --arg model_dir runs/with_vs_without_nv/nv_generate_mr_brain_finetune_nemotron_correction/without/repeat_2/models \
   --arg out_dir runs/with_vs_without_nv/nv_generate_mr_brain_finetune_nemotron_correction/without/repeat_2/inference \
   --arg mod_map runs/with_vs_without_nv/nv_generate_mr_brain_finetune_nemotron_correction/without/repeat_2/configs/modality_mapping.json \
   --arg ae_path "" \
   --arg ckpt_path "" \
   '.data_base_dir = $data_base | .json_data_list = $json_data | .embedding_base_dir = $emb_base | .model_dir = $model_dir | .output_dir = $out_dir | .modality_mapping_path = $mod_map | .trained_autoencoder_path = $ae_path | .existing_ckpt_filepath = $ckpt_path' \
   "$ENV_CFG" > "$ENV_CFG".tmp && mv "$ENV_CFG".tmp "$ENV_CFG" && \
MODEL_CFG=runs/with_vs_without_nv/nv_generate_mr_brain_finetune_nemotron_correction/without/repeat_2/configs/config_maisi_diff_model_rflow-mr-brain.json && \
jq '.diffusion_unet_train.n_epochs = 1 | .diffusion_unet_train.batch_size = 1 | .diffusion_unet_train.learning_rate = 0.0001 | .diffusion_unet_train.cache_rate = 0.1' \
   "$MODEL_CFG" > "$MODEL_CFG".tmp && mv "$MODEL_CFG".tmp "$MODEL_CFG" && \
SUMMARY_FILE=runs/with_vs_without_nv/nv_generate_mr_brain_finetune_nemotron_correction/without/repeat_2/preflight_summary.json && \
jq -n \
   --argjson train_count "$TRAIN_COUNT" \
   --argjson missing 0 \
   --argjson unsupported 0 \
   '{datalist_training_count: $train_count, missing_files: $missing, unsupported_modalities: $unsupported, config_staged: true}' \
   > "$SUMMARY_FILE"
```

Repeat 3: score 3/5, passed=no, steps=unresolved, exit=None

```bash
INPUT_DIR=runs/with_vs_without_nv/_inputs/nv_generate_mr_brain_finetune/input_dataset
OUTPUT_DIR=runs/with_vs_without_nv/nv_generate_mr_brain_finetune_nemotron_correction/without/repeat_3 && \
mkdir -p "$OUTPUT_DIR" && \
cp configs/config_network_rflow.json "$OUTPUT_DIR"/ && \
cp configs/environment_maisi_diff_model_rflow-mr-brain.json "$OUTPUT_DIR"/ && \
cp configs/config_maisi_diff_model_rflow-mr-brain.json "$OUTPUT_DIR"/ && \
cp configs/modality_mapping.json "$OUTPUT_DIR"/ && \
cp "$INPUT_DIR"/dataset.json "$OUTPUT_DIR"/dataset.json && \
jq empty "$OUTPUT_DIR"/dataset.json >/dev/null && \
[ "$(jq '.training | length' "$OUTPUT_DIR"/dataset.json)" -gt 0 ] && \
jq '.training | all(.modality | IN("mri_t1","mri_t2","mri_flair","mri_swi","mri_t1_skull_stripped","mri_t2_skull_stripped","mri_flair_skull_stripped","mri_swi_skull_stripped"))' "$OUTPUT_DIR"/dataset.json | grep -q true && \
jq -r '.training[].image' "$OUTPUT_DIR"/dataset.json | while read img; do [ -f "$INPUT_DIR/$img" ] || exit 1; done && \
jq --arg data_base_dir "$(realpath "$INPUT_DIR")" \
   --arg json_data_list "$(realpath "$OUTPUT_DIR"/dataset.json)" \
   --arg embedding_base_dir "$(realpath "$OUTPUT_DIR"/embeddings)" \
   --arg model_dir "$(realpath "$OUTPUT_DIR"/models)" \
   --arg output_dir "$(realpath "$OUTPUT_DIR"/inference)" \
   --arg modality_mapping_path "$(realpath "$OUTPUT_DIR"/modality_mapping.json)" \
   '.data_base_dir = $data_base_dir | .json_data_list = $json_data_list | .embedding_base_dir = $embedding_base_dir | .model_dir = $model_dir | .output_dir = $output_dir | .modality_mapping_path = $modality_mapping_path | .trained_autoencoder_path = null | .existing_ckpt_filepath = null' \
   "$OUTPUT_DIR"/environment_maisi_diff_model_rflow-mr-brain.json > "$OUTPUT_DIR"/environment_tmp.json && \
mv "$OUTPUT_DIR"/environment_tmp.json "$OUTPUT_DIR"/environment_maisi_diff_model_rflow-mr-brain.json && \
echo '{"status":"preflight_ok","checked_at":"'"$(date -Iseconds)"'"}' > "$OUTPUT_DIR"/preflight_summary.json
```

## Skill Fix Notes

No separate final-run skill fix note is recorded in the saved study JSON for this scenario; this report was regenerated from the post-fix study artifacts.

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `examples/studies/with_vs_without_skill/nv_generate_mr_brain_finetune_nemotron_correction/` |
| Generated outputs | `runs/with_vs_without_nv/nv_generate_mr_brain_finetune_nemotron_correction/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_generate_mr_brain_finetune_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
