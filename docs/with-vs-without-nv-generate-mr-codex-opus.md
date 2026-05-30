# `nv_generate_mr`: Codex/Opus LLM+SKILL.md vs LLM+README

Status: strict audit passed for refreshed artifacts on May 29, 2026. Full run log: `not found`. Targeted rerun log: `not found`.

This report compares `LLM + SKILL.md` with `LLM + upstream README/guide`. The completed direct-API run used the corrected embedded-doc minimal prompt because those backends cannot read repo files. The fair NAT/tool-agent prompt artifact is A2-style: it gives a natural user request, a neutral staged input path, an output directory, and tells the agent which arm-specific document to read. It does not spell out operational details such as entrypoints, labels, model variants, or config filenames outside the documentation arm.

## Experiment Question

Does `LLM + SKILL.md` make an agent better at reading documentation and taking the right action than `LLM + upstream README/guide`?

## User Request Shape

The prompt request for the GPT-5.5 with-skill arm was:

> The image-generation request is at runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json. Generate one T1 MR image and write generated NIfTI volumes under runs/with_vs_without_nv/nv_generate_mr_codex_opus/gpt55/with/repeat_1.

The staged user input for every arm was `runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json`. The source fixture `skills/nv-generate-mr/fixtures/default_mri_t1.json` was used only to stage that neutral input path.

Fair path-prompt artifact: `tools/nat_audit/data/eval_nv_model_studies_nv_generate_mr_prompts.json`

## Result

| Backend | Arm | Mean score | Passes | Steps | Exit | Tier 5 | Failed tiers |
|---|---|---:|---:|---|---|---|---|
| GPT-5.5 / Codex | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | shape=(128, 256, 256) (3) | none |
| GPT-5.5 / Codex | without | 4.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | 1 (3) | exit 1 (3) | T5: exit 1 (3) |
| Opus 4.7 | with | 5.0/5 | 3/3 | mean 0.0; unresolved 0; values [0, 0, 0] | 0 (3) | shape=(128, 256, 256) (3) | none |
| Opus 4.7 | without | 3.0/5 | 0/3 | all unresolved; values [unresolved, unresolved, unresolved] | None (2); 1 (1) | command does not reference the expected output directory (2); exit 1 (1) | T4: output dir marker (2); T5: command does not reference the expected output directory (2); T2: user input path marker (1) |

## Analysis

SKILL.md paired advantage: the with-skill arms passed 6/6 backend-repeat trials with an average score of 5.0/5; the README-only arms passed 0/6 backend-repeat trials with an average score of 3.5/5.

SKILL.md paired advantage: SKILL.md wins 6/6 matched backend-repeat pairs, README-only wins 0/6, and 0/6 are ties. Pass/fail is the primary outcome; score breaks ties only when pass status is equal. Exact one-sided sign-test p=0.01562 across 6 decisive pair(s).

Outcome-support gate: Supports SKILL.md advantage. SKILL.md wins 6/6 matched pair(s); README-only wins 0/6; sign-test p=0.01562.

Each backend/arm/skill configuration was repeated three times. A repeat is independent: it has its own output directory, and each execution attempt inside the repeat creates a fresh venv before running the generated command. Dependency and model download caches are shared only as documented test-environment caches under `.workbench_data/with_vs_without_cache` (`PIP_CACHE_DIR=.workbench_data/with_vs_without_cache/pip`, `HF_HOME=.workbench_data/with_vs_without_cache/huggingface`, `HF_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `HUGGINGFACE_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `TRANSFORMERS_CACHE=.workbench_data/with_vs_without_cache/huggingface/transformers`, `TORCH_HOME=.workbench_data/with_vs_without_cache/torch`, `XDG_CACHE_HOME=.workbench_data/with_vs_without_cache/xdg`, `CONDA_PKGS_DIRS=.workbench_data/with_vs_without_cache/conda_pkgs`, `UV_CACHE_DIR=.workbench_data/with_vs_without_cache/uv`, `CUDA_CACHE_PATH=.workbench_data/with_vs_without_cache/cuda`, `NUMBA_CACHE_DIR=.workbench_data/with_vs_without_cache/numba`).

The main baseline uses `max_correction_steps=0`: each repeat sends one prompt, executes the extracted command once, and records pass/fail, runtime, tokens, and deterministic failure analysis. The repair-loop implementation remains available for separate diagnostic experiments, but it is not part of this comparison.

All with-skill repeats exited successfully and produced artifacts accepted by the deterministic grader. That means the final SKILL.md surface was repeatable for both tested agent backends.

The README-only commands did not pass tier 5. Typical failure modes were unsafe generated shell cleanup, missing schema fields, missing model/control details, or upstream commands that did not execute cleanly from Medical AI Skills root.

Tier 2 is intentionally strict: a command only earns it if it uses the staged user input path `runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json`.

## Token Profiling

Token counts are provider-reported values saved in each repeat JSON. Reasoning tokens are shown only when the provider returned that subfield and are a subset of completion tokens, not an additional cost to add to total tokens. Execution time is averaged only across repeats that reached command execution; no-command-extracted repeats still count toward token totals.

| Backend | Arm | Repeats | Passes | Attempts | Prompt tokens | Completion tokens | Reasoning tokens | Total tokens | Mean total/repeat | Executed | Mean exec s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GPT-5.5 / Codex | with | 3 | 3 | 3 | 6,333 | 1,321 | 946 | 7,654 | 2,551.3 | 3 | 56.4 |
| GPT-5.5 / Codex | without | 3 | 0 | 3 | 8,880 | 12,855 | 10,752 | 21,735 | 7,245.0 | 3 | 0.0 |
| Opus 4.7 | with | 3 | 3 | 3 | 10,965 | 647 | 0 | 11,612 | 3,870.7 | 3 | 69.9 |
| Opus 4.7 | without | 3 | 0 | 3 | 13,191 | 2,745 | 0 | 15,936 | 5,312.0 | 1 | 0.0 |

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
| 2 | 0 | 4/5 | no | 1 | T5: exit 1 | tier_5: exit 1 Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>nonzero_exit: Command exited 1. Repair: Use stderr/stdout to repair setup, paths, arguments, or runtime package installation. |
| 3 | 0 | 4/5 | no | 1 | T5: exit 1 | tier_5: exit 1 Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>nonzero_exit: Command exited 1. Repair: Use stderr/stdout to repair setup, paths, arguments, or runtime package installation. |

### Opus 4.7, with arm

| Repeat | Step | Score | Passed | Exit | Failed tiers | Why it did not work |
|---:|---:|---:|---|---|---|---|
| 1 | 0 | 5/5 | yes | 0 | none | none |
| 2 | 0 | 5/5 | yes | 0 | none | none |
| 3 | 0 | 5/5 | yes | 0 | none | none |

### Opus 4.7, without arm

| Repeat | Step | Score | Passed | Exit | Failed tiers | Why it did not work |
|---:|---:|---:|---|---|---|---|
| 1 | 0 | 3/5 | no | None | T4: output dir marker; T5: command does not reference the expected output directory | tier_4: output dir marker Repair: Write outputs under the exact arm-specific output directory.<br>tier_5: command does not reference the expected output directory Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference the expected output directory Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
| 2 | 0 | 2/5 | no | None | T2: user input path marker; T4: output dir marker; T5: command does not reference the expected output directory | tier_2: user input path marker Repair: Use the staged user input path under runs/with_vs_without_nv/_inputs/.<br>tier_4: output dir marker Repair: Write outputs under the exact arm-specific output directory.<br>tier_5: command does not reference the expected output directory Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>not_executed: command does not reference the expected output directory Repair: Remove unsafe shell fragments and keep the command within the documented workflow surface. |
| 3 | 0 | 4/5 | no | 1 | T5: exit 1 | tier_5: exit 1 Repair: Make the command execute cleanly and produce verifier-accepted artifacts.<br>nonzero_exit: Command exited 1. Repair: Use stderr/stdout to repair setup, paths, arguments, or runtime package installation. |

## Skill Fix Notes

Before the final rerun, `SKILL.md` was tightened to name `scripts/run_mr.py` as the exact runnable surface, preserve the staged request path, and avoid invented module or shell entrypoints.

## Generated Commands

These are the extracted first-attempt commands by repeat.

### GPT-5.5 / Codex, with arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-mr/scripts/run_mr.py runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json --output-dir runs/with_vs_without_nv/nv_generate_mr_codex_opus/gpt55/with/repeat_1 --modality mri_t1 --random-seed 0
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-mr/scripts/run_mr.py runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json --output-dir runs/with_vs_without_nv/nv_generate_mr_codex_opus/gpt55/with/repeat_2 --modality mri_t1 --random-seed 2
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-mr/scripts/run_mr.py runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json --output-dir runs/with_vs_without_nv/nv_generate_mr_codex_opus/gpt55/with/repeat_3 --modality mri_t1 --random-seed 3
```

### GPT-5.5 / Codex, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 4/5, passed=no, steps=unresolved, exit=1

```bash
OUT="runs/with_vs_without_nv/nv_generate_mr_codex_opus/gpt55/without/repeat_1" && REQ="runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json" && NVROOT="${NV_GENERATE_ROOT:?Set NV_GENERATE_ROOT to the NV-Generate-CTMR checkout}" && NVROOT="$(cd "$NVROOT" && pwd)" && mkdir -p "$OUT/configs" "$OUT/generated" && cp "$NVROOT/configs/config_network_rflow.json" "$OUT/configs/config_network_rflow.json" && cp "$NVROOT/configs/environment_maisi_diff_model_rflow-mr-brain.json" "$OUT/configs/environment_maisi_diff_model_rflow-mr-brain.json" && cp "$NVROOT/configs/config_maisi_diff_model_rflow-mr-brain.json" "$OUT/configs/config_maisi_diff_model_rflow-mr-brain.json" && python - "$OUT" "$REQ" <<'PY' && cd "$OUT" && PYTHONPATH="$NVROOT" python -m scripts.download_model_data --version rflow-mr-brain --root_dir ./ --model_only && PYTHONPATH="$NVROOT" python -m scripts.diff_model_infer -t ./configs/config_network_rflow.json -e ./configs/environment_maisi_diff_model_rflow-mr-brain.json -c ./configs/config_maisi_diff_model_rflow-mr-brain.json
import json, shutil, sys
from pathlib import Path

out = Path(sys.argv[1])
req = Path(sys.argv[2])
cfg_path = out / "configs" / "config_maisi_diff_model_rflow-mr-brain.json"
env_path = out / "configs" / "environment_maisi_diff_model_rflow-mr-brain.json"

request = {}
if req.exists():
    request = json.loads(req.read_text())
    shutil.copy2(req, out / "request.used.json")

def first_present(d, keys):
    for k in keys:
        if isinstance(d, dict) and k in d:
            return d[k]
    return None

seed = first_present(request, ["random_seed", "seed"])
if seed is None:
    seed = first_present(request.get("diffusion_unet_inference", {}) if isinstance(request, dict) else {}, ["random_seed", "seed"])
if seed is None:
    seed = 0

cfg = json.loads(cfg_path.read_text())
inf = cfg.setdefault("diffusion_unet_inference", {})
inf["dim"] = [256, 256, 256]
inf["spacing"] = [1.0, 1.0, 1.0]
inf["modality"] = 9
inf["num_inference_steps"] = 30
inf["random_seed"] = int(seed)
inf["num_output_samples"] = 1
for k in ("num_samples", "n_samples", "num_images", "number_of_images", "batch_size"):
    if k in inf:
        inf[k] = 1
cfg_path.write_text(json.dumps(cfg, indent=4) + "\n")

env = json.loads(env_path.read_text())
def set_output_dir(obj):
    found = False
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "output_dir":
                obj[k] = "generated"
                found = True
            else:
                found = set_output_dir(v) or found
    elif isinstance(obj, list):
        for v in obj:
            found = set_output_dir(v) or found
    return found
if not set_output_dir(env):
    env["output_dir"] = "generated"
env_path.write_text(json.dumps(env, indent=4) + "\n")
PY
```

Repeat 2: score 4/5, passed=no, steps=unresolved, exit=1

```bash
OUT="runs/with_vs_without_nv/nv_generate_mr_codex_opus/gpt55/without/repeat_2" REQ="runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json" UP="${NV_GENERATE_ROOT:?Set NV_GENERATE_ROOT to the NV-Generate-CTMR checkout}" && mkdir -p "$OUT/configs" && cp "$REQ" "$OUT/request.json" && cp "$UP/configs/config_network_rflow.json" "$OUT/configs/config_network_rflow.json" && cp "$UP/configs/environment_maisi_diff_model_rflow-mr-brain.json" "$OUT/configs/environment_maisi_diff_model_rflow-mr-brain.json" && cp "$UP/configs/config_maisi_diff_model_rflow-mr-brain.json" "$OUT/configs/config_maisi_diff_model_rflow-mr-brain.json" && PYTHONPATH="$UP${PYTHONPATH:+:$PYTHONPATH}" python -m scripts.download_model_data --version rflow-mr-brain --root_dir "$OUT" --model_only && OUT="$OUT" python -c 'import json, os; out=os.environ["OUT"]; cfg_path=f"{out}/configs/config_maisi_diff_model_rflow-mr-brain.json"; env_path=f"{out}/configs/environment_maisi_diff_model_rflow-mr-brain.json"; cfg=json.load(open(cfg_path)); block=cfg.setdefault("diffusion_unet_inference",{}); block.update({"dim":[256,256,256],"spacing":[1.0,1.0,1.0],"modality":9,"num_output_samples":1,"num_inference_steps":30,"random_seed":2}); json.dump(cfg, open(cfg_path,"w"), indent=4); env=json.load(open(env_path)); def fix(x): return os.path.join(out,"models",x[9:]) if isinstance(x,str) and x.startswith("./models/") else (os.path.join(out,"models",x[7:]) if isinstance(x,str) and x.startswith("models/") else (os.path.join(out,"models") if isinstance(x,str) and x in ("./models","models") else x)); def walk(o):     (o.update({k:(out if k=="output_dir" else walk(v)) for k,v in list(o.items())}) if isinstance(o,dict) else None);     return fix(o) if not isinstance(o,(dict,list)) else ([walk(v) for v in o] if isinstance(o,list) else o); walk(env); env["output_dir"]=out; json.dump(env, open(env_path,"w"), indent=4)' && PYTHONPATH="$UP${PYTHONPATH:+:$PYTHONPATH}" python -m scripts.diff_model_infer -t "$OUT/configs/config_network_rflow.json" -e "$OUT/configs/environment_maisi_diff_model_rflow-mr-brain.json" -c "$OUT/configs/config_maisi_diff_model_rflow-mr-brain.json"
```

Repeat 3: score 4/5, passed=no, steps=unresolved, exit=1

```bash
OUT="runs/with_vs_without_nv/nv_generate_mr_codex_opus/gpt55/without/repeat_3" REQ="runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json" VARIANT="rflow-mr-brain" NETWORK="rflow" bash -lc 'set -euo pipefail; : "${NV_GENERATE_ROOT:?NV_GENERATE_ROOT must point to the NV-Generate-CTMR checkout}"; REPO_ROOT="$(pwd)"; RUN_ROOT="$REPO_ROOT/$OUT/runtime"; mkdir -p "$RUN_ROOT/configs" "$REPO_ROOT/$OUT"; cp "$NV_GENERATE_ROOT/configs/config_network_${NETWORK}.json" "$RUN_ROOT/configs/"; cp "$NV_GENERATE_ROOT/configs/environment_maisi_diff_model_${VARIANT}.json" "$RUN_ROOT/configs/"; cp "$NV_GENERATE_ROOT/configs/config_maisi_diff_model_${VARIANT}.json" "$RUN_ROOT/configs/"; python -c '"'"'import json, pathlib, sys; req_p, env_p, cfg_p, out_dir = map(pathlib.Path, sys.argv[1:5]); req=json.loads(req_p.read_text()) if req_p.exists() else {}; env=json.loads(env_p.read_text()); cfg=json.loads(cfg_p.read_text()); env["output_dir"]=str(out_dir.resolve()); block=cfg.setdefault("diffusion_unet_inference", {}); block["dim"]=[256,256,256]; block["spacing"]=[1.0,1.0,1.0]; block["modality"]=9; block["num_output_samples"]=1; block["random_seed"]=int(req.get("random_seed", req.get("seed", 3))); block["num_inference_steps"]=30; env_p.write_text(json.dumps(env, indent=4) + "\n"); cfg_p.write_text(json.dumps(cfg, indent=4) + "\n")'"'"' "$REQ" "$RUN_ROOT/configs/environment_maisi_diff_model_${VARIANT}.json" "$RUN_ROOT/configs/config_maisi_diff_model_${VARIANT}.json" "$REPO_ROOT/$OUT"; cd "$RUN_ROOT"; PYTHONPATH="$NV_GENERATE_ROOT${PYTHONPATH:+:$PYTHONPATH}" python -m scripts.download_model_data --version "$VARIANT" --root_dir ./ --model_only && PYTHONPATH="$NV_GENERATE_ROOT${PYTHONPATH:+:$PYTHONPATH}" python -m scripts.diff_model_infer -t "./configs/config_network_${NETWORK}.json" -e "./configs/environment_maisi_diff_model_${VARIANT}.json" -c "./configs/config_maisi_diff_model_${VARIANT}.json"'
```

### Opus 4.7, with arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-mr/scripts/run_mr.py runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json --output-dir runs/with_vs_without_nv/nv_generate_mr_codex_opus/opus/with/repeat_1 --modality mri_t1 --random-seed 0 --yes
```

Repeat 2: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-mr/scripts/run_mr.py runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json --output-dir runs/with_vs_without_nv/nv_generate_mr_codex_opus/opus/with/repeat_2 --modality mri_t1 --random-seed 0
```

Repeat 3: score 5/5, passed=yes, steps=0, exit=0

```bash
export NV_GENERATE_ROOT="${NV_GENERATE_ROOT:-.workbench_data/upstreams/NV-Generate-CTMR}" && python -m pip install -r "$NV_GENERATE_ROOT/requirements.txt" && python skills/nv-generate-mr/scripts/run_mr.py runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json --output-dir runs/with_vs_without_nv/nv_generate_mr_codex_opus/opus/with/repeat_3 --modality mri_t1 --random-seed 0 --yes
```

### Opus 4.7, without arm

Extracted first-attempt commands are shown below by repeat. The main baseline uses no repair prompting, so failures are recorded as data.

Repeat 1: score 3/5, passed=no, steps=unresolved, exit=None

```bash
mkdir -p runs/with_vs_without/nv_generate_mr_codex_opus/opus/without/repeat_1 && cd "$NV_GENERATE_ROOT" && python -m scripts.download_model_data --version rflow-mr-brain --root_dir "./" --model_only && REPO_ROOT="$(git -C "$OLDPWD" rev-parse --show-toplevel 2>/dev/null || echo "$OLDPWD")" && OUT_DIR="${REPO_ROOT}/runs/with_vs_without/nv_generate_mr_codex_opus/opus/without/repeat_1" && REQ="${REPO_ROOT}/runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json" && STAGE="${OUT_DIR}/_staged_configs" && mkdir -p "${STAGE}" && cp ./configs/config_network_rflow.json "${STAGE}/config_network_rflow.json" && cp ./configs/environment_maisi_diff_model_rflow-mr-brain.json "${STAGE}/environment_maisi_diff_model_rflow-mr-brain.json" && cp ./configs/config_maisi_diff_model_rflow-mr-brain.json "${STAGE}/config_maisi_diff_model_rflow-mr-brain.json" && python -c "
import json, os
stage=os.environ['STAGE']; out=os.environ['OUT_DIR']; req=os.environ['REQ']
with open(req) as f: r=json.load(f)
env_p=os.path.join(stage,'environment_maisi_diff_model_rflow-mr-brain.json')
cfg_p=os.path.join(stage,'config_maisi_diff_model_rflow-mr-brain.json')
with open(env_p) as f: env=json.load(f)
env['output_dir']=out
with open(env_p,'w') as f: json.dump(env,f,indent=2)
with open(cfg_p) as f: cfg=json.load(f)
inf=cfg['diffusion_unet_inference']
inf['dim']=r.get('dim',[256,256,256])
inf['spacing']=r.get('spacing',[1.0,1.0,1.0])
inf['modality']=r.get('modality',9)
if 'random_seed' in r: inf['random_seed']=r['random_seed']
if 'num_inference_steps' in r: inf['num_inference_steps']=r['num_inference_steps']
if 'cfg_guidance_scale' in r: inf['cfg_guidance_scale']=r['cfg_guidance_scale']
inf['num_output_samples']=1
with open(cfg_p,'w') as f: json.dump(cfg,f,indent=2)
" && export STAGE OUT_DIR REQ && python -m scripts.diff_model_infer -t "${STAGE}/config_network_rflow.json" -e "${STAGE}/environment_maisi_diff_model_rflow-mr-brain.json" -c "${STAGE}/config_maisi_diff_model_rflow-mr-brain.json"
```

Repeat 2: score 2/5, passed=no, steps=unresolved, exit=None

```bash
mkdir -p runs/with_vs_without/nv_generate_mr_codex_opus/opus/without/repeat_2 && cd "$NV_GENERATE_ROOT" && python -m scripts.download_model_data --version rflow-mr-brain --root_dir "./" --model_only && STAGE_DIR="$OLDPWD/runs/with_vs_without/nv_generate_mr_codex_opus/opus/without/repeat_2" && cp configs/config_maisi_diff_model_rflow-mr-brain.json "$STAGE_DIR/config_maisi_diff_model_rflow-mr-brain.json" && cp configs/environment_maisi_diff_model_rflow-mr-brain.json "$STAGE_DIR/environment_maisi_diff_model_rflow-mr-brain.json" && python -c "import json,sys; p=sys.argv[1]; d=json.load(open(p)); d['diffusion_unet_inference']['dim']=[256,256,256]; d['diffusion_unet_inference']['spacing']=[1.0,1.0,1.0]; d['diffusion_unet_inference']['modality']=9; d['diffusion_unet_inference']['num_output_samples']=1; json.dump(d,open(p,'w'),indent=4)" "$STAGE_DIR/config_maisi_diff_model_rflow-mr-brain.json" && python -c "import json,sys; p=sys.argv[1]; o=sys.argv[2]; d=json.load(open(p)); d['output_dir']=o; json.dump(d,open(p,'w'),indent=4)" "$STAGE_DIR/environment_maisi_diff_model_rflow-mr-brain.json" "$STAGE_DIR" && python -m scripts.diff_model_infer -t ./configs/config_network_rflow.json -e "$STAGE_DIR/environment_maisi_diff_model_rflow-mr-brain.json" -c "$STAGE_DIR/config_maisi_diff_model_rflow-mr-brain.json"
```

Repeat 3: score 4/5, passed=no, steps=unresolved, exit=1

```bash
mkdir -p runs/with_vs_without_nv/nv_generate_mr_codex_opus/opus/without/repeat_3 && cd "$NV_GENERATE_ROOT" && python -m scripts.download_model_data --version rflow-mr --root_dir "./" --model_only && REQ="$OLDPWD/runs/with_vs_without_nv/_inputs/nv_generate_mr/request.json" && OUT_DIR="$OLDPWD/runs/with_vs_without_nv/nv_generate_mr_codex_opus/opus/without/repeat_3" && STAGE="$OUT_DIR/_staged_configs" && mkdir -p "$STAGE" && cp ./configs/config_maisi_diff_model_rflow-mr.json "$STAGE/config_maisi_diff_model_rflow-mr.json" && cp ./configs/environment_maisi_diff_model_rflow-mr.json "$STAGE/environment_maisi_diff_model_rflow-mr.json" && python -c "
import json, sys
req = json.load(open('$REQ'))
cfg_p = '$STAGE/config_maisi_diff_model_rflow-mr.json'
env_p = '$STAGE/environment_maisi_diff_model_rflow-mr.json'
cfg = json.load(open(cfg_p))
env = json.load(open(env_p))
inf = cfg['diffusion_unet_inference']
inf['modality'] = 9
inf['num_output_samples'] = 1
for k in ('dim','spacing','random_seed','num_inference_steps','cfg_guidance_scale'):
    if k in req: inf[k] = req[k]
cfg['diffusion_unet_inference'] = inf
env['output_dir'] = '$OUT_DIR'
json.dump(cfg, open(cfg_p,'w'), indent=2)
json.dump(env, open(env_p,'w'), indent=2)
print('FOV:', [inf['dim'][i]*inf['spacing'][i] for i in range(3)])
" && python -m scripts.diff_model_infer -t ./configs/config_network_rflow.json -e "$STAGE/environment_maisi_diff_model_rflow-mr.json" -c "$STAGE/config_maisi_diff_model_rflow-mr.json"
```

## Source Artifacts

| Source | Path |
|---|---|
| Study JSON and comparison | `runs/with_vs_without_nv/studies/nv_generate_mr_codex_opus/` |
| Generated outputs | `runs/with_vs_without_nv/nv_generate_mr_codex_opus/` |
| Fair path-prompt artifact | `tools/nat_audit/data/eval_nv_model_studies_nv_generate_mr_prompts.json` |
| Runner | `tools/with_vs_without/run_nv_model_studies.py` |
