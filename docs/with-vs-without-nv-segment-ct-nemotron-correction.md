# `nv_segment_ct`: Nemotron LLM+SKILL.md vs LLM+README Baseline Study

Status: strict audit passed for refreshed artifacts on May 28, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

This report uses the same direct-API embedded-doc no-repair baseline protocol as the Codex/Opus comparison, but runs `nvidia/nvidia/nemotron-3-super-v3`. The linked prompt artifact is the fair A2-style path prompt for tool-enabled/NAT replication.

## Experiment Question

Does `LLM + SKILL.md` let Nemotron produce a runnable command on the first try, and how does that compare with `LLM + upstream README/guide` under the same `max_correction_steps=0` baseline?

## User Request Shape

The prompt request for the with-skill arm was:

> The input CT volume is at runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz. Segment the spleen, liver, right kidney, and left kidney, and write outputs under runs/with_vs_without_nv/nv_segment_ct_nemotron_correction/with/repeat_1.

The staged user input for every arm was `runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz`. The source fixture `skills/nv-segment-ct/fixtures/spleen_03.nii.gz` was used only to stage that neutral input path.

Fair path-prompt artifact: `tools/nat_audit/data/eval_nv_model_studies_nv_segment_ct_prompts.json`

## Result

| Backend | Arm | Mean score | Passes | Steps | Exit | Tier 5 | Failed tiers |
|---|---|---:|---:|---|---|---|---|
| Nemotron | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | shape=(512, 512, 40) (3) | none |
| Nemotron | without | 2.3/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | None (2); 1 (1) | command does not reference the neutral staged input path (2); exit 1 (1) | T3: model/modality/control marker (3); T2: user input path marker (2); T5: command does not reference the neutral staged input path (2) |

## Analysis

SKILL.md paired advantage: the with-skill repeats passed 3/3 with mean score 5.0/5 and steps mean 0.0; unresolved 0; values [0, 0, 0]. The README-only repeats passed 0/3 with mean score 2.3/5 and steps all unresolved; values [unresolved, unresolved, unresolved].

SKILL.md paired advantage: SKILL.md wins 3/3 matched backend-repeat pairs, README-only wins 0/3, and 0/3 are ties. Pass/fail is the primary outcome; score breaks ties only when pass status is equal. Exact one-sided sign-test p=0.125 across 3 decisive pair(s).

Outcome-support gate: Supports SKILL.md advantage. SKILL.md wins 3/3 matched pair(s); README-only wins 0/3; sign-test p=0.125.

Each backend/arm/skill configuration was repeated three times. A repeat is independent: it has its own output directory, and each execution attempt inside the repeat creates a fresh venv before running the generated command. Dependency and model download caches are shared only as documented test-environment caches under `.workbench_data/with_vs_without_cache` (`PIP_CACHE_DIR=.workbench_data/with_vs_without_cache/pip`, `HF_HOME=.workbench_data/with_vs_without_cache/huggingface`, `HF_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `HUGGINGFACE_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `TRANSFORMERS_CACHE=.workbench_data/with_vs_without_cache/huggingface/transformers`, `TORCH_HOME=.workbench_data/with_vs_without_cache/torch`, `XDG_CACHE_HOME=.workbench_data/with_vs_without_cache/xdg`, `CONDA_PKGS_DIRS=.workbench_data/with_vs_without_cache/conda_pkgs`, `UV_CACHE_DIR=.workbench_data/with_vs_without_cache/uv`, `CUDA_CACHE_PATH=.workbench_data/with_vs_without_cache/cuda`, `NUMBA_CACHE_DIR=.workbench_data/with_vs_without_cache/numba`).

No correction feedback was sent in this baseline. Deterministic failure analysis is saved with each repeat so repair behavior can be studied separately later.

## Token Profiling

Token counts are provider-reported values saved in each repeat JSON. Reasoning tokens are shown only when the provider returned that subfield and are a subset of completion tokens, not an additional cost to add to total tokens. Execution time is averaged only across repeats that reached command execution; no-command-extracted repeats still count toward token totals.

| Backend | Arm | Repeats | Passes | Attempts | Prompt tokens | Completion tokens | Reasoning tokens | Total tokens | Mean total/repeat | Executed | Mean exec s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Nemotron | with | 3 | 3 | 3 | 5,943 | 4,445 | 0 | 10,388 | 3,462.7 | 3 | 48.8 |
| Nemotron | without | 3 | 0 | 3 | 7,761 | 21,493 | 0 | 29,254 | 9,751.3 | 1 | 0.2 |

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
| Missing model/modality/control marker | 3 |
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
| 1 | 0 | 2/5 | no | None | T2: user input path marker; T3: model/modality/control marker; T5: command does not reference the neutral staged input path | tier_2: user input path marker Repair: Use the staged user input path under runs/with_vs_without_nv/_inputs/.<br>tier_3: model/modality/control marker Repair: Choose the model, modality, labels, anatomy controls, or smoke mode required by the task.<br>tier_5: command does not reference the neutral staged input path Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference the neutral staged input path Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
| 2 | 0 | 2/5 | no | None | T2: user input path marker; T3: model/modality/control marker; T5: command does not reference the neutral staged input path | tier_2: user input path marker Repair: Use the staged user input path under runs/with_vs_without_nv/_inputs/.<br>tier_3: model/modality/control marker Repair: Choose the model, modality, labels, anatomy controls, or smoke mode required by the task.<br>tier_5: command does not reference the neutral staged input path Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference the neutral staged input path Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
| 3 | 0 | 3/5 | no | 1 | T3: model/modality/control marker; T5: exit 1 | tier_3: model/modality/control marker Repair: Choose the model, modality, labels, anatomy controls, or smoke mode required by the task.<br>tier_5: exit 1 Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>nonzero_exit: Command exited 1. Repair: Use stderr/stdout to repair setup, paths, arguments, or runtime package installation. |

## Generated Commands

These are the extracted first-attempt commands by repeat.

### With-skill arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
pip install -r skills/nv-segment-ct/requirements.txt && huggingface-cli download nvidia/NV-Segment-CT --local-dir skills/nv-segment-ct/bundle/ && python skills/nv-segment-ct/scripts/run_vista3d.py runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz --label-prompts "1,3,5,14" --output-dir runs/with_vs_without_nv/nv_segment_ct_nemotron_correction/with/repeat_1
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
pip install -r skills/nv-segment-ct/requirements.txt && huggingface-cli download nvidia/NV-Segment-CT --local-dir skills/nv-segment-ct/bundle/ && python skills/nv-segment-ct/scripts/run_vista3d.py runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz --label-prompts "1,3,5,14" --output-dir runs/with_vs_without_nv/nv_segment_ct_nemotron_correction/with/repeat_2
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
pip install -r skills/nv-segment-ct/requirements.txt && huggingface-cli download nvidia/NV-Segment-CT --local-dir skills/nv-segment-ct/bundle/ && python skills/nv-segment-ct/scripts/run_vista3d.py runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz --label-prompts "1,3,5,14" --output-dir runs/with_vs_without_nv/nv_segment_ct_nemotron_correction/with/repeat_3
```

### README-only arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 2/5, passed=no, steps=unresolved, exit=None

```bash
conda activate vista3d-nv && cd NV-Segment-CT && mkdir -p ../runs/with_vs_without_nv/nv_segment_ct_nemotron_correction/without/repeat_1 && echo '{"everything_labels": [2,3,4,5]}' > ../runs/with_vs_without_nv/nv_segment_ct_nemotron_correction/without/repeat_1/override.json && python -m monai.bundle run --config_file="['configs/inference.json', 'configs/batch_inference.json', '../runs/with_vs_without_nv/nv_segment_ct_nemotron_correction/without/repeat_1/override.json']" --input_dir="../runs/with_vs_without_nv/_inputs/nv_segment_ct" --output_dir="../runs/with_vs_without_nv/nv_segment_ct_nemotron_correction/without/repeat_1"
```

Repeat 2: score 2/5, passed=no, steps=unresolved, exit=None

```bash
conda activate vista3d-nv && cd NV-Segment-CT && python -m monai.bundle run --config_file="['configs/inference.json', 'configs/batch_inference.json']" --input_dir="runs/with_vs_without_nv/_inputs/nv_segment_ct" --output_dir="runs/with_vs_without_nv/nv_segment_ct_nemotron_correction/without/repeat_2" --input_dict="{'everything_labels':[1,2,3,4]}"
```

Repeat 3: score 3/5, passed=no, steps=unresolved, exit=1

```bash
conda activate vista3d-nv && cd NV-Segment-CT && mkdir -p ../runs/with_vs_without_nv/nv_segment_ct_nemotron_correction/without/repeat_3 && cp ../runs/with_vs_without_nv/_inputs/nv_segment_ct/input.nii.gz ../runs/with_vs_without_nv/nv_segment_ct_nemotron_correction/without/repeat_3/ && spleen_label=$(python -c "import json; d=json.load(open('./configs/label_dict.json')); print(d['spleen'])") && liver_label=$(python -c "import json; d=json.load(open('./configs/label_dict.json')); print(d['liver'])") && right_kidney_label=$(python -c "import json; d=json.load(open('./configs/label_dict.json')); print(d['right kidney'])") && left_kidney_label=$(python -c "import json; d=json.load(open('./configs/label_dict.json')); print(d['left kidney'])") && labels="[$spleen_label,$liver_label,$right_kidney_label,$left_kidney_label]" && cp ./configs/inference.json ../runs/with_vs_without_nv/nv_segment_ct_nemotron_correction/without/repeat_3/inference.json && python -c "import json, sys; d=json.load(open('../runs/with_vs_without_nv/nv_segment_ct_nemotron_correction/without/repeat_3/inference.json')); d['everything_labels'] = $labels; json.dump(d, open('../runs/with_vs_without_nv/nv_segment_ct_nemotron_correction/without/repeat_3/inference.json', 'w'), indent=2)" && cp ./configs/batch_inference.json ../runs/with_vs_without_nv/nv_segment_ct_nemotron_correction/without/repeat_3/batch_inference.json && python -m monai.bundle run --config_file="['../runs/with_vs_without_nv/nv_segment_ct_nemotron_correction/without/repeat_3/inference.json', '../runs/with_vs_without_nv/nv_segment_ct_nemotron_correction/without/repeat_3/batch_inference.json']" --input_dir="../runs/with_vs_without_nv/nv_segment_ct_nemotron_correction/without/repeat_3" --output_dir="../runs/with_vs_without_nv/nv_segment_ct_nemotron_correction/without/repeat_3"
```

## Skill Fix Notes

Before the final rerun, `SKILL.md` was tightened to name `scripts/run_vista3d.py` as the exact runnable surface and to state the required label IDs for the requested spleen/liver/kidney task.

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `examples/studies/with_vs_without_skill/nv_segment_ct_nemotron_correction/` |
| Generated outputs | `runs/with_vs_without_nv/nv_segment_ct_nemotron_correction/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_segment_ct_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
