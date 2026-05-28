# `nv_generate_mr`: Nemotron LLM+SKILL.md vs LLM+README Baseline Study

Status: strict audit passed for refreshed artifacts on May 28, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

This report uses the same direct-API embedded-doc no-repair baseline protocol as the Codex/Opus comparison, but runs `nvidia/nvidia/nemotron-3-super-v3`. The linked prompt artifact is the fair A2-style path prompt for tool-enabled/NAT replication.

## Experiment Question

Does `LLM + SKILL.md` let Nemotron produce a runnable command on the first try, and how does that compare with `LLM + upstream README/guide` under the same `max_correction_steps=0` baseline?

## User Request Shape

The prompt request for the with-skill arm was:

> The image-generation request is at runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json. Generate one T1 MR image and write generated NIfTI volumes under runs/with_vs_without_nv/nv_generate_mr_nemotron_correction/with/repeat_1.

The staged user input for every arm was `runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json`. The source fixture `skills/nv-generate-mr/fixtures/default_mri_t1.json` was used only to stage that neutral input path.

Fair path-prompt artifact: `tools/nat_audit/data/eval_nv_model_studies_nv_generate_mr_prompts.json`

## Result

| Backend | Arm | Mean score | Passes | Steps | Exit | Tier 5 | Failed tiers |
|---|---|---:|---:|---|---|---|---|
| Nemotron | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | shape=(128, 256, 256) (3) | none |
| Nemotron | without | 3.3/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | None (2); 1 (1) | command does not reference the neutral staged input path (2); exit 1 (1) | T2: user input path marker (2); T5: command does not reference the neutral staged input path (2); T5: exit 1 (1) |

## Analysis

SKILL.md paired advantage: the with-skill repeats passed 3/3 with mean score 5.0/5 and steps mean 0.0; unresolved 0; values [0, 0, 0]. The README-only repeats passed 0/3 with mean score 3.3/5 and steps all unresolved; values [unresolved, unresolved, unresolved].

SKILL.md paired advantage: SKILL.md wins 3/3 matched backend-repeat pairs, README-only wins 0/3, and 0/3 are ties. Pass/fail is the primary outcome; score breaks ties only when pass status is equal. Exact one-sided sign-test p=0.125 across 3 decisive pair(s).

Outcome-support gate: Supports SKILL.md advantage. SKILL.md wins 3/3 matched pair(s); README-only wins 0/3; sign-test p=0.125.

Each backend/arm/skill configuration was repeated three times. A repeat is independent: it has its own output directory, and each execution attempt inside the repeat creates a fresh venv before running the generated command. Dependency and model download caches are shared only as documented test-environment caches under `.workbench_data/with_vs_without_cache` (`PIP_CACHE_DIR=.workbench_data/with_vs_without_cache/pip`, `HF_HOME=.workbench_data/with_vs_without_cache/huggingface`, `HF_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `HUGGINGFACE_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `TRANSFORMERS_CACHE=.workbench_data/with_vs_without_cache/huggingface/transformers`, `TORCH_HOME=.workbench_data/with_vs_without_cache/torch`, `XDG_CACHE_HOME=.workbench_data/with_vs_without_cache/xdg`, `CONDA_PKGS_DIRS=.workbench_data/with_vs_without_cache/conda_pkgs`, `UV_CACHE_DIR=.workbench_data/with_vs_without_cache/uv`, `CUDA_CACHE_PATH=.workbench_data/with_vs_without_cache/cuda`, `NUMBA_CACHE_DIR=.workbench_data/with_vs_without_cache/numba`).

No correction feedback was sent in this baseline. Deterministic failure analysis is saved with each repeat so repair behavior can be studied separately later.

## Token Profiling

Token counts are provider-reported values saved in each repeat JSON. Reasoning tokens are shown only when the provider returned that subfield and are a subset of completion tokens, not an additional cost to add to total tokens. Execution time is averaged only across repeats that reached command execution; no-command-extracted repeats still count toward token totals.

| Backend | Arm | Repeats | Passes | Attempts | Prompt tokens | Completion tokens | Reasoning tokens | Total tokens | Mean total/repeat | Executed | Mean exec s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Nemotron | with | 3 | 3 | 3 | 6,309 | 4,572 | 0 | 10,881 | 3,627.0 | 3 | 43.3 |
| Nemotron | without | 3 | 0 | 3 | 9,642 | 17,532 | 0 | 27,174 | 9,058.0 | 1 | 0.0 |

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
| Missing staged input path | 2 |
| Missing model/modality/control marker | 0 |
| Missing output directory | 0 |
| Unsafe/static guard block | 2 |
| Nonzero execution exit | 1 |
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
| 2 | 0 | 3/5 | no | None | T2: user input path marker; T5: command does not reference the neutral staged input path | tier_2: user input path marker Repair: Use the staged user input path under runs/with_vs_without_nv/_inputs/.<br>tier_5: command does not reference the neutral staged input path Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference the neutral staged input path Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
| 3 | 0 | 3/5 | no | None | T2: user input path marker; T5: command does not reference the neutral staged input path | tier_2: user input path marker Repair: Use the staged user input path under runs/with_vs_without_nv/_inputs/.<br>tier_5: command does not reference the neutral staged input path Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference the neutral staged input path Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |

## Generated Commands

These are the extracted first-attempt commands by repeat.

### With-skill arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && \
python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && \
python skills/nv-generate-mr/scripts/run_mr.py runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json --output-dir runs/with_vs_without_nv/nv_generate_mr_nemotron_correction/with/repeat_1 --modality mri_t1 --random-seed 0
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-mr/scripts/run_mr.py runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json --output-dir runs/with_vs_without_nv/nv_generate_mr_nemotron_correction/with/repeat_2 --modality mri_t1 --random-seed 0
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && \
python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && \
python skills/nv-generate-mr/scripts/run_mr.py runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json --output-dir runs/with_vs_without_nv/nv_generate_mr_nemotron_correction/with/repeat_3 --modality mri_t1 --random-seed 0
```

### README-only arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 4/5, passed=no, steps=unresolved, exit=1

```bash
set -e
REQUEST_JSON="runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json"
OUTPUT_DIR="runs/with_vs_without_nv/nv_generate_mr_nemotron_correction/without/repeat_1"

if [ -f "$REQUEST_JSON" ]; then
    DIM_ARR=$(python -c "import json, sys; data=json.load(open('$REQUEST_JSON')); dim=data.get('dim', [256,256,256]); print(json.dumps(dim))" 2>/dev/null || echo '[256,256,256]')
    SPACING_ARR=$(python -c "import json, sys; data=json.load(open('$REQUEST_JSON')); spacing=data.get('spacing', [1.0,1.0,1.0]); print(json.dumps(spacing))" 2>/dev/null || echo '[1.0,1.0,1.0]')
    MODALITY=$(python -c "import json, sys; data=json.load(open('$REQUEST_JSON')); print(data.get('modality', 9))" 2>/dev/null || echo 9)
else
    DIM_ARR='[256,256,256]'
    SPACING_ARR='[1.0,1.0,1.0]'
    MODALITY=9
fi

mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

python -m scripts.download_model_data --version rflow-mr-brain --root_dir "./" --model_only

cp ../../../../../configs/config_network_rflow.json .
cp ../../../../../configs/environment_maisi_diff_model_rflow-mr-brain.json .
cp ../../../../../configs/config_maisi_diff_model_rflow-mr-brain.json .

python -c "
import json, sys
dim_arr = sys.argv[1]
spacing_arr = sys.argv[2]
modality = int(sys.argv[3])
with open('config_maisi_diff_model_rflow-mr-brain.json', 'r') as f:
    config = json.load(f)
config['diffusion_unet_inference']['dim'] = json.loads(dim_arr)
config['diffusion_unet_inference']['spacing'] = json.loads(spacing_arr)
config['modality'] = modality
with open('config_maisi_diff_model_rflow-mr-brain.json', 'w') as f:
    json.dump(config, f, indent=4)
" "$DIM_ARR" "$SPACING_ARR" "$MODALITY"

python -c "
import json, sys
output_dir = sys.argv[1]
with open('environment_maisi_diff_model_rflow-mr-brain.json', 'r') as f:
    config = json.load(f)
config['output_dir'] = output_dir
with open('environment_maisi_diff_model_rflow-mr-brain.json', 'w') as f:
    json.dump(config, f, indent=4)
" "."

python -m scripts.diff_model_infer \
    -t config_network_rflow.json \
    -e environment_maisi_diff_model_rflow-mr-brain.json \
    -c config_maisi_diff_model_rflow-mr-brain.json
```

Repeat 2: score 3/5, passed=no, steps=unresolved, exit=None

```bash
mkdir -p runs/with_vs_without_nv/nv_generate_mr_nemotron_correction/without/repeat_2 && \
cd runs/with_vs_without_nv/nv_generate_mr_nemotron_correction/without/repeat_2 && \
cp ../../../configs/config_network_rflow.json . && \
cp ../../../configs/environment_maisi_diff_model_rflow-mr-brain.json . && \
cp ../../../configs/config_maisi_diff_model_rflow-mr-brain.json . && \
sed -i 's/"dim": \[[^]]*\]/"dim": [256, 256, 256]/' config_maisi_diff_model_rflow-mr-brain.json && \
sed -i 's/"spacing": \[[^]]*\]/"spacing": [1.0, 1.0, 1.0]/' config_maisi_diff_model_rflow-mr-brain.json && \
sed -i 's/"modality": [0-9]\+/"modality": 9/' config_maisi_diff_model_rflow-mr-brain.json && \
sed -i 's/"output_dir": "[^"]*"/"output_dir": "."/' environment_maisi_diff_model_rflow-mr-brain.json && \
python -m scripts.download_model_data --version rflow-mr-brain --root_dir ./ --model_only && \
python -m scripts.diff_model_infer -t ./config_network_rflow.json -e ./environment_maisi_diff_model_rflow-mr-brain.json -c ./config_maisi_diff_model_rflow-mr-brain.json
```

Repeat 3: score 3/5, passed=no, steps=unresolved, exit=None

```bash
mkdir -p runs/with_vs_without_nv/nv_generate_mr_nemotron_correction/without/repeat_3 && \
cd runs/with_vs_without_nv/nv_generate_mr_nemotron_correction/without/repeat_3 && \
python -m scripts.download_model_data --version rflow-mr-brain --root_dir ./ --model_only && \
mkdir -p configs && \
cp ../../../../../configs/config_network_rflow.json ./configs/ && \
cp ../../../../../configs/environment_maisi_diff_model_rflow-mr-brain.json ./configs/ && \
cp ../../../../../configs/config_maisi_diff_model_rflow-mr-brain.json ./configs/ && \
sed -i 's/"dim": \[[0-9]*, [0-9]*, [0-9]*\]/"dim": [256, 256, 256]/' ./configs/config_maisi_diff_model_rflow-mr-brain.json && \
sed -i 's/"spacing": \[[0-9.]*, [0-9.]*, [0-9.]*\]/"spacing": [1.0, 1.0, 1.0]/' ./configs/config_maisi_diff_model_rflow-mr-brain.json && \
sed -i 's/"modality": [0-9]*/"modality": 9/' ./configs/config_maisi_diff_model_rflow-mr-brain.json && \
python -m scripts.diff_model_infer \
    -t ./configs/config_network_rflow.json \
    -e ./configs/environment_maisi_diff_model_rflow-mr-brain.json \
    -c ./configs/config_maisi_diff_model_rflow-mr-brain.json
```

## Skill Fix Notes

Before the final rerun, `SKILL.md` was tightened to name `scripts/run_mr.py` as the exact runnable surface, preserve the staged request path, and avoid invented module or shell entrypoints.

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `examples/studies/with_vs_without_skill/nv_generate_mr_nemotron_correction/` |
| Generated outputs | `runs/with_vs_without_nv/nv_generate_mr_nemotron_correction/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_generate_mr_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
