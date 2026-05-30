# `nv_generate_vae_finetune`: Nemotron LLM+SKILL.md vs LLM+README Baseline Study

Status: strict audit passed for refreshed artifacts on May 29, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

This report uses the same direct-API embedded-doc no-repair baseline protocol as the Codex/Opus comparison, but runs `nvidia/nvidia/nemotron-3-super-v3`. The linked prompt artifact is the fair A2-style path prompt for tool-enabled/NAT replication.

## Experiment Question

Does `LLM + SKILL.md` let Nemotron produce a runnable command on the first try, and how does that compare with `LLM + upstream README/guide` under the same `max_correction_steps=0` baseline?

## User Request Shape

The prompt request for the with-skill arm was:

> The VAE finetuning preflight input bundle is at runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset. Validate and stage the shortest preflight-scale workflow check, and write outputs under runs/with_vs_without_nv/nv_generate_vae_finetune_nemotron_correction/with/repeat_1.

The staged user input for every arm was `runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset`. The source fixture `skills/nv-generate-vae-finetune/fixtures` was used only to stage that neutral input path.

Fair path-prompt artifact: `tools/nat_audit/data/eval_nv_model_studies_nv_generate_vae_finetune_prompts.json`

## Result

| Backend | Arm | Mean score | Passes | Steps | Exit | Tier 5 | Failed tiers |
|---|---|---:|---:|---|---|---|---|
| Nemotron | with | 3.3/5 | 2/3 | mean 0.0; unresolved 1; values [unresolved, 0, 0] | 0 (2); None (1) | preflight payload reported (2); no command extracted (1) | T1: entrypoint marker (1); T2: user input path marker (1); T3: model/modality/control marker (1) |
| Nemotron | without | 2.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | None (3) | command does not reference an expected runnable surface (2); no command extracted (1) | T1: entrypoint marker (3); T5: command does not reference an expected runnable surface (2); T2: user input path marker (1) |

## Analysis

SKILL.md paired advantage: the with-skill repeats passed 2/3 with mean score 3.3/5 and steps mean 0.0; unresolved 1; values [unresolved, 0, 0]. The README-only repeats passed 0/3 with mean score 2.0/5 and steps all unresolved; values [unresolved, unresolved, unresolved].

SKILL.md paired advantage: SKILL.md wins 2/3 matched backend-repeat pairs, README-only wins 1/3, and 0/3 are ties. Pass/fail is the primary outcome; score breaks ties only when pass status is equal. Exact one-sided sign-test p=0.5 across 3 decisive pair(s).

Outcome-support gate: Supports SKILL.md advantage. SKILL.md wins 2/3 matched pair(s); README-only wins 1/3; sign-test p=0.5.

Each backend/arm/skill configuration was repeated three times. A repeat is independent: it has its own output directory, and each execution attempt inside the repeat creates a fresh venv before running the generated command. Dependency and model download caches are shared only as documented test-environment caches under `.workbench_data/with_vs_without_cache` (`PIP_CACHE_DIR=.workbench_data/with_vs_without_cache/pip`, `HF_HOME=.workbench_data/with_vs_without_cache/huggingface`, `HF_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `HUGGINGFACE_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `TRANSFORMERS_CACHE=.workbench_data/with_vs_without_cache/huggingface/transformers`, `TORCH_HOME=.workbench_data/with_vs_without_cache/torch`, `XDG_CACHE_HOME=.workbench_data/with_vs_without_cache/xdg`, `CONDA_PKGS_DIRS=.workbench_data/with_vs_without_cache/conda_pkgs`, `UV_CACHE_DIR=.workbench_data/with_vs_without_cache/uv`, `CUDA_CACHE_PATH=.workbench_data/with_vs_without_cache/cuda`, `NUMBA_CACHE_DIR=.workbench_data/with_vs_without_cache/numba`).

No correction feedback was sent in this baseline. Deterministic failure analysis is saved with each repeat so repair behavior can be studied separately later.

## Token Profiling

Token counts are provider-reported values saved in each repeat JSON. Reasoning tokens are shown only when the provider returned that subfield and are a subset of completion tokens, not an additional cost to add to total tokens. Execution time is averaged only across repeats that reached command execution; no-command-extracted repeats still count toward token totals.

| Backend | Arm | Repeats | Passes | Attempts | Prompt tokens | Completion tokens | Reasoning tokens | Total tokens | Mean total/repeat | Executed | Mean exec s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Nemotron | with | 3 | 2 | 3 | 10,623 | 4,942 | 0 | 15,565 | 5,188.3 | 2 | 0.0 |
| Nemotron | without | 3 | 0 | 3 | 3,213 | 14,695 | 0 | 17,908 | 5,969.3 | 0 | n/a |

## Nemotron Diagnostics

These diagnostics are Nemotron-only and do not change the main score. The strict result still requires exactly one valid fenced bash block. The recoverable-command columns ask whether a deterministic format adapter could have recovered command-like text without another LLM call or any domain repair.

| Arm | Repeats | Passed strict | Strict command | Recoverable malformed command | Unrecoverable formatting | Guard-ready after tolerant extraction | Static guard blocked | Format categories | Guard reasons |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| with | 3 | 2 | 2 | 1 | 0 | 1 | 0 | strict 2; raw_shell 1 | none |
| without | 3 | 0 | 2 | 1 | 0 | 0 | 1 | strict 2; raw_shell 1 | command does not reference an expected runnable surface (1) |

Protocol-compliance failure buckets, counted per repeat and not mutually exclusive:

| Bucket | Count |
|---|---:|
| No strict command extracted | 2 |
| Wrong or missing runnable surface | 4 |
| Missing staged input path | 2 |
| Missing model/modality/control marker | 2 |
| Missing output directory | 2 |
| Unsafe/static guard block | 2 |
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
| 1 | 0 | 3/5 | no | None | T1: entrypoint marker; T5: command does not reference an expected runnable surface | tier_1: entrypoint marker Repair: Use the runnable surface documented for this arm.<br>tier_5: command does not reference an expected runnable surface Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference an expected runnable surface Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
| 2 | 0 | 3/5 | no | None | T1: entrypoint marker; T5: command does not reference an expected runnable surface | tier_1: entrypoint marker Repair: Use the runnable surface documented for this arm.<br>tier_5: command does not reference an expected runnable surface Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference an expected runnable surface Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
| 3 | 0 | 0/5 | no | None | T1: entrypoint marker; T2: user input path marker; T3: model/modality/control marker; T4: output dir marker; T5: no command extracted | no_command: No executable bash command was extracted from the model response. Repair: Return exactly one fenced bash block containing the command to run.<br>tier_1: entrypoint marker Repair: Use the runnable surface documented for this arm.<br>tier_2: user input path marker Repair: Use the staged user input path under runs/with_vs_without_nv/_inputs/.<br>tier_3: model/modality/control marker Repair: Choose the model, modality, labels, anatomy controls, or smoke mode required by the task. |

## Generated Commands

These are the extracted first-attempt commands by repeat.

### With-skill arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 0/5, passed=no, steps=unresolved, exit=None

_No executable bash command was extracted._

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && \
python skills/nv-generate-vae-finetune/scripts/run_vae_finetune.py \
  runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_datalist.json \
  --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_dataset \
  --output-dir runs/with_vs_without_nv/nv_generate_vae_finetune_nemotron_correction/with/repeat_2 \
  --modality mri \
  --preflight
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && \
python skills/nv-generate-vae-finetune/scripts/run_vae_finetune.py \
  runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_datalist.json \
  --data-base-dir runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/preflight_dataset \
  --output-dir runs/with_vs_without_nv/nv_generate_vae_finetune_nemotron_correction/with/repeat_3 \
  --preflight
```

### README-only arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 3/5, passed=no, steps=unresolved, exit=None

```bash
mkdir -p runs/with_vs_without_nv/nv_generate_vae_finetune_nemotron_correction/without/repeat_1 && \
DATALIST=runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/dataset.json && \
[ -f "$DATALIST" ] || { echo "Datalist missing"; exit 1; } && \
TRAIN_COUNT=$(jq '.training | length' "$DATALIST") && \
VAL_COUNT=$(jq '( .validation // .testing ) | length' "$DATALIST") && \
[ "$TRAIN_COUNT" -gt 0 ] && [ "$VAL_COUNT" -gt 0 ] || { echo "Empty split"; exit 1; } && \
jq -e '.training[] | select(.class | IN("ct","mri") | not)' "$DATALIST" >/dev/null || { echo "Invalid class in training"; exit 1; } && \
jq -e '(.validation // .testing)[] | select(.class | IN("ct","mri") | not)' "$DATALIST" >/dev/null || { echo "Invalid class in validation"; exit 1; } && \
IMG_LIST=$(jq -r '( .training[] | .image ), ( (.validation // .testing)[] | .image )' "$DATALIST") && \
for img in $IMG_LIST; do [ -f "runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset/$img" ] || { echo "Missing image: $img"; exit 1; }; done && \
cp configs/config_network_rflow.json configs/environment_maisi_vae_train.json configs/config_maisi_vae_train.json runs/with_vs_without_nv/nv_generate_vae_finetune_nemotron_correction/without/repeat_1/ && \
jq -n --arg status "preflight_ok" --argjson train "$TRAIN_COUNT" --argjson val "$VAL_COUNT" '{status: $status, training_count: $train, validation_count: $val}' > runs/with_vs_without_nv/nv_generate_vae_finetune_nemotron_correction/without/repeat_1/preflight_summary.json
```

Repeat 2: score 3/5, passed=no, steps=unresolved, exit=None

```bash
mkdir -p ../../../../../runs/with_vs_without_nv/nv_generate_vae_finetune_nemotron_correction/without/repeat_2 && \
cd runs/with_vs_without_nv/_inputs/nv_generate_vae_finetune/input_dataset && \
[ -f datalist.json ] || { echo "datalist.json not found"; exit 1; } && \
RESULT=$(python3 - <<'END'
import json, os, sys
with open('datalist.json') as f:
    data = json.load(f)
train = data.get('training', [])
val = data.get('validation', data.get('testing', []))
if not train:
    sys.exit('training split empty')
if not val:
    sys.exit('validation/testing split empty')
missing = []
for split in (train, val):
    for entry in split:
        img = entry.get('image')
        if not img:
            continue
        p = os.path.join(os.getcwd(), img)
        if not os.path.isfile(p):
            missing.append(img)
if missing:
    sys.exit('missing images: ' + ', '.join(missing))
for split in (train, val):
    for entry in split:
        cls = entry.get('class', '').lower()
        if cls not in ('ct', 'mri'):
            sys.exit(f'invalid class {cls}')
result = {
    'training_count': len(train),
    'validation_count': len(val),
    'modalities_ok': True,
    'all_images_exist': len(missing)==0
}
print(json.dumps(result))
END
) || { echo "Validation failed: $RESULT"; exit 1; } && \
echo "$RESULT" > ../../../../../runs/with_vs_without_nv/nv_generate_vae_finetune_nemotron_correction/without/repeat_2/preflight_summary.json && \
cp -r ../../../../.. /configs ../../../../../runs/with_vs_without_nv/nv_generate_vae_finetune_nemotron_correction/without/repeat_2/ && \
cp -r ../../../../.. /scripts ../../../../../runs/with_vs_without_nv/nv_generate_vae_finetune_nemotron_correction/without/repeat_2/
```

Repeat 3: score 0/5, passed=no, steps=unresolved, exit=None

_No executable bash command was extracted._

## Skill Fix Notes

No separate final-run skill fix note is recorded in the saved study JSON for this scenario; this report was regenerated from the post-fix study artifacts.

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `runs/with_vs_without_nv/studies/nv_generate_vae_finetune_nemotron_correction/` |
| Generated outputs | `runs/with_vs_without_nv/nv_generate_vae_finetune_nemotron_correction/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_generate_vae_finetune_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
