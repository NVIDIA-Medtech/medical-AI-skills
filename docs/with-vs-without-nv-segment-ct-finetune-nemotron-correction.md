# `nv_segment_ct_finetune`: Nemotron LLM+SKILL.md vs LLM+README Baseline Study

Status: strict audit passed for refreshed artifacts on May 29, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

This report uses the same direct-API embedded-doc no-repair baseline protocol as the Codex/Opus comparison, but runs `nvidia/nvidia/nemotron-3-super-v3`. The linked prompt artifact is the fair A2-style path prompt for tool-enabled/NAT replication.

## Experiment Question

Does `LLM + SKILL.md` let Nemotron produce a runnable command on the first try, and how does that compare with `LLM + upstream README/guide` under the same `max_correction_steps=0` baseline?

## User Request Shape

The prompt request for the with-skill arm was:

> Fine-tune the CT segmentation workflow on the small dataset at runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset. Use the shortest smoke-scale run suitable for checking the workflow, and write outputs under runs/with_vs_without_nv/nv_segment_ct_finetune_nemotron_correction/with/repeat_1.

The staged user input for every arm was `runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset`. The source fixture `skills/nv-segment-ct-finetune/fixtures/spleen_micro` was used only to stage that neutral input path.

Fair path-prompt artifact: `tools/nat_audit/data/eval_nv_model_studies_nv_segment_ct_finetune_prompts.json`

## Result

| Backend | Arm | Mean score | Passes | Steps | Exit | Tier 5 | Failed tiers |
|---|---|---:|---:|---|---|---|---|
| Nemotron | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | checkpoint reported (3) | none |
| Nemotron | without | 4.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | 1 (2); None (1) | exit 1 (2); without-skill command references forbidden Medical AI Skills skill marker (1) | T5: exit 1 (2); T5: without-skill command references forbidden Medical AI Skills skill marker (1) |

## Analysis

SKILL.md paired advantage: the with-skill repeats passed 3/3 with mean score 5.0/5 and steps mean 0.0; unresolved 0; values [0, 0, 0]. The README-only repeats passed 0/3 with mean score 4.0/5 and steps all unresolved; values [unresolved, unresolved, unresolved].

SKILL.md paired advantage: SKILL.md wins 3/3 matched backend-repeat pairs, README-only wins 0/3, and 0/3 are ties. Pass/fail is the primary outcome; score breaks ties only when pass status is equal. Exact one-sided sign-test p=0.125 across 3 decisive pair(s).

Outcome-support gate: Supports SKILL.md advantage. SKILL.md wins 3/3 matched pair(s); README-only wins 0/3; sign-test p=0.125.

Each backend/arm/skill configuration was repeated three times. A repeat is independent: it has its own output directory, and each execution attempt inside the repeat creates a fresh venv before running the generated command. Dependency and model download caches are shared only as documented test-environment caches under `.workbench_data/with_vs_without_cache` (`PIP_CACHE_DIR=.workbench_data/with_vs_without_cache/pip`, `HF_HOME=.workbench_data/with_vs_without_cache/huggingface`, `HF_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `HUGGINGFACE_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `TRANSFORMERS_CACHE=.workbench_data/with_vs_without_cache/huggingface/transformers`, `TORCH_HOME=.workbench_data/with_vs_without_cache/torch`, `XDG_CACHE_HOME=.workbench_data/with_vs_without_cache/xdg`, `CONDA_PKGS_DIRS=.workbench_data/with_vs_without_cache/conda_pkgs`, `UV_CACHE_DIR=.workbench_data/with_vs_without_cache/uv`, `CUDA_CACHE_PATH=.workbench_data/with_vs_without_cache/cuda`, `NUMBA_CACHE_DIR=.workbench_data/with_vs_without_cache/numba`).

No correction feedback was sent in this baseline. Deterministic failure analysis is saved with each repeat so repair behavior can be studied separately later.

## Token Profiling

Token counts are provider-reported values saved in each repeat JSON. Reasoning tokens are shown only when the provider returned that subfield and are a subset of completion tokens, not an additional cost to add to total tokens. Execution time is averaged only across repeats that reached command execution; no-command-extracted repeats still count toward token totals.

| Backend | Arm | Repeats | Passes | Attempts | Prompt tokens | Completion tokens | Reasoning tokens | Total tokens | Mean total/repeat | Executed | Mean exec s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Nemotron | with | 3 | 3 | 3 | 8,001 | 5,373 | 0 | 13,374 | 4,458.0 | 3 | 76.5 |
| Nemotron | without | 3 | 0 | 3 | 9,660 | 27,288 | 0 | 36,948 | 12,316.0 | 2 | 0.0 |

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
| Wrong or missing runnable surface | 0 |
| Missing staged input path | 0 |
| Missing model/modality/control marker | 0 |
| Missing output directory | 0 |
| Unsafe/static guard block | 1 |
| Nonzero execution exit | 2 |
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
| 1 | 0 | 4/5 | no | 1 | T5: exit 1 | tier_5: exit 1 Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>nonzero_exit: Command exited 1. Repair: Use stderr/stdout to repair setup, paths, arguments, or runtime package installation. |
| 2 | 0 | 4/5 | no | 1 | T5: exit 1 | tier_5: exit 1 Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>nonzero_exit: Command exited 1. Repair: Use stderr/stdout to repair setup, paths, arguments, or runtime package installation. |
| 3 | 0 | 4/5 | no | None | T5: without-skill command references forbidden Medical AI Skills skill marker | tier_5: without-skill command references forbidden Medical AI Skills skill marker Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: without-skill command references forbidden Medical AI Skills skill marker Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |

## Generated Commands

These are the extracted first-attempt commands by repeat.

### With-skill arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
python -m pip install "monai==1.4.0" "numpy<2" pytorch-ignite einops nibabel scipy typer PyYAML fire huggingface_hub && python skills/nv-segment-ct-finetune/scripts/run_finetune.py runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset --smoke --patch-size '[64,64,64]' --output-dir runs/with_vs_without_nv/nv_segment_ct_finetune_nemotron_correction/with/repeat_1
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
python -m pip install "monai==1.4.0" "numpy<2" pytorch-ignite einops nibabel scipy typer PyYAML fire huggingface_hub && python skills/nv-segment-ct-finetune/scripts/run_finetune.py runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset --smoke --patch-size '[64,64,64]' --output-dir runs/with_vs_without_nv/nv_segment_ct_finetune_nemotron_correction/with/repeat_2
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
python -m pip install "monai==1.4.0" "numpy<2" pytorch-ignite einops nibabel scipy typer PyYAML fire huggingface_hub && \
python skills/nv-segment-ct-finetune/scripts/run_finetune.py \
  runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset \
  --smoke \
  --patch-size '[64,64,64]' \
  --output-dir runs/with_vs_without_nv/nv_segment_ct_finetune_nemotron_correction/with/repeat_3
```

### README-only arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 4/5, passed=no, steps=unresolved, exit=1

```bash
mkdir -p runs/with_vs_without_nv/nv_segment_ct_finetune_nemotron_correction/without/repeat_1 && \
base_dir="runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset" && \
output_dir="runs/with_vs_without_nv/nv_segment_ct_finetune_nemotron_correction/without/repeat_1" && \
img1=$(ls $base_dir/img*.nii.gz 2>/dev/null | head -1) && \
label1=$(ls $base_dir/label*.nii.gz 2>/dev/null | head -1) && \
img2=$(ls $base_dir/img*.nii.gz 2>/dev/null | head -2 | tail -1) && \
label2=$(ls $base_dir/label*.nii.gz 2>/dev/null | head -2 | tail -1) && \
if [ -z "$img1" ] || [ -z "$label1" ] || [ -z "$img2" ] || [ -z "$label2" ]; then \
    echo "Error: Not enough files found in $base_dir" >&2; \
    exit 1; \
fi && \
cat > $output_dir/dataset.json <<EOF
{
  "training": [
    {"image": "$(basename $img1)", "label": "$(basename $label1)", "fold": 0},
    {"image": "$(basename $img2)", "label": "$(basename $label2)", "fold": 1}
  ],
  "testing": []
}
EOF && \
BUNDLE_DIR=$(python -c "import monai.bundle; import os; print(os.path.dirname(monai.bundle.__file__))") && \
cp -r $BUNDLE_DIR/configs $output_dir/ && \
sed -i 's|"data_list_file_path":.*|"data_list_file_path": "'"$output_dir/dataset.json"'",|' $output_dir/configs/train_continual.json && \
sed -i 's|"dataset_dir":.*|"dataset_dir": "runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset",|' $output_dir/configs/train_continual.json && \
sed -i 's|"n_train_samples":.*|"n_train_samples": 1,|' $output_dir/configs/train_continual.json && \
sed -i 's|"n_val_samples":.*|"n_val_samples": 1,|' $output_dir/configs/train_continual.json && \
sed -i 's|"val_at_start":.*|"val_at_start": false,|' $output_dir/configs/train_continual.json && \
sed -i 's|"input_channels":.*|"input_channels": 1,|' $output_dir/configs/train_continual.json && \
sed -i 's|"patch_size":.*|"patch_size": [64,64,64],|' $output_dir/configs/train_continual.json && \
sed -i '/"label_mappings": {/,/}/ {
    c\
    "label_mappings": {\
        "default": [\
            [1, 1]\
        ]\
    }
}' $output_dir/configs/train_continual.json && \
cd $output_dir && \
python -m monai.bundle run --config_file="['configs/train.json','configs/train_continual.json']"
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=1

```bash
ABS_REPO_ROOT=$(pwd) && ABS_INPUT_DATASET=$ABS_REPO_ROOT/runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset && ABS_OUTPUT_DIR=$ABS_REPO_ROOT/runs/with_vs_without_nv/nv_segment_ct_finetune_nemotron_correction/without/repeat_2 && mkdir -p $ABS_OUTPUT_DIR/configs && echo '{
    "training": [
        {"image": "img001.nii.gz", "label": "label001.nii.gz", "fold": 1},
        {"image": "img002.nii.gz", "label": "label002.nii.gz", "fold": 1}
    ],
    "testing": [
        {"image": "img003.nii.gz", "label": "label003.nii.gz", "fold": 0}
    ]
}' > $ABS_OUTPUT_DIR/data_split.json && cp $ABS_REPO_ROOT/configs/train_continual.json $ABS_OUTPUT_DIR/configs/train_continual.json && sed -i "s|\"data_list_file_path\":.*|\"data_list_file_path\": \"$ABS_OUTPUT_DIR/data_split.json\",|" $ABS_OUTPUT_DIR/configs/train_continual.json && sed -i "s|\"dataset_dir\":.*|\"dataset_dir\": \"$ABS_INPUT_DATASET\",|" $ABS_OUTPUT_DIR/configs/train_continual.json && sed -i '/"label_mappings": {/,/}/c\            "label_mappings": {\n                "default": [\n                    [1, 1]\n                ]\n            },' $ABS_OUTPUT_DIR/configs/train_continual.json && sed -i 's|\"n_train_samples\":.*|\"n_train_samples\": 2,|' $ABS_OUTPUT_DIR/configs/train_continual.json && sed -i 's|\"n_val_samples\":.*|\"n_val_samples\": 1,|' $ABS_OUTPUT_DIR/configs/train_continual.json && sed -i 's|\"patch_size\":.*|\"patch_size\": [64, 64, 64],|' $ABS_OUTPUT_DIR/configs/train_continual.json && cd $ABS_OUTPUT_DIR && python -m monai.bundle run --config_file="[$ABS_REPO_ROOT/configs/train.json,$ABS_OUTPUT_DIR/configs/train_continual.json]"
```

Repeat 3: score 4/5, passed=no, steps=unresolved, exit=None

```bash
mkdir -p runs/with_vs_without_nv/nv_segment_ct_finetune_nemotron_correction/without/repeat_3 && \
cp skills/nv-segment-ct-finetune/configs/train.json runs/with_vs_without_nv/nv_segment_ct_finetune_nemotron_correction/without/repeat_3/configs/train.json && \
cp skills/nv-segment-ct-finetune/configs/train_continual.json runs/with_vs_without_nv/nv_segment_ct_finetune_nemotron_correction/without/repeat_3/configs/train_continual.json && \
cd runs/with_vs_without_nv/_inputs/nv_segment_ct_finetune/input_dataset && \
printf '{\n    "training": [\n        {"image": "imagesTr/img001.nii.gz", "label": "labelsTr/img001.nii.gz", "fold": 1},\n        {"image": "imagesTr/img002.nii.gz", "label": "labelsTr/img002.nii.gz", "fold": 1}\n    ],\n    "testing": [\n        {"image": "imagesTr/img003.nii.gz", "label": "labelsTr/img003.nii.gz"}\n    ]\n}' > ../../../with_vs_without_nv/nv_segment_ct_finetune_nemotron_correction/without/repeat_3/dataset.json && \
cd ../../../with_vs_without_nv/nv_segment_ct_finetune_nemotron_correction/without/repeat_3 && \
sed -i 's|"data_list_file_path":.*|"data_list_file_path": "'"$(pwd)"'/dataset.json",|' configs/train_continual.json && \
sed -i 's|"dataset_dir":.*|"dataset_dir": "'"$(pwd)"'/../../../_inputs/nv_segment_ct_finetune/input_dataset",|' configs/train_continual.json && \
sed -i '/"label_mappings": {/,/}/c\  "label_mappings": {\n    "default": [\n        [1, 1]\n    ]\n  },' configs/train_continual.json && \
sed -i 's|"n_train_samples":.*|"n_train_samples": 2,|' configs/train_continual.json && \
sed -i 's|"n_val_samples":.*|"n_val_samples": 1,|' configs/train_continual.json && \
sed -i 's|"patch_size":.*|"patch_size": [64, 64, 64],|' configs/train_continual.json && \
sed -i 's|"max_epochs":.*|"max_epochs": 2,|' configs/train_continual.json && \
sed -i 's|"val_freq":.*|"val_freq": 1,|' configs/train_continual.json && \
python -m monai.bundle run --config_file="['configs/train.json','configs/train_continual.json']"
```

## Skill Fix Notes

Before the final rerun, `SKILL.md` was tightened to name `scripts/run_finetune.py` as the smoke-scale finetune surface and to require the user's staged dataset path.

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `runs/with_vs_without_nv/studies/nv_segment_ct_finetune_nemotron_correction/` |
| Generated outputs | `runs/with_vs_without_nv/nv_segment_ct_finetune_nemotron_correction/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_segment_ct_finetune_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
