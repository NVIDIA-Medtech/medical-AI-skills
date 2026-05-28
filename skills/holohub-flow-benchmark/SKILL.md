---
name: holohub-flow-benchmark
description: Used for benchmarking HoloHub app data-flow latency with optional contracts. Not for model correctness or clinical quality claims.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - medtech
    - holohub
    - benchmark
---

# HoloHub Flow Benchmark

## Purpose
- Used for benchmarking HoloHub app data-flow latency with optional contracts. Not for model correctness or clinical quality claims.
- Use the wrapper exactly as documented; do not replace the upstream entrypoint with a handwritten implementation.
- Manifest I/O: inputs are `benchmark_fixture`; outputs are `benchmark_logs` and `result_json`.

## Instructions
- Read `skill_manifest.yaml` before changing arguments, side effects, or validation gates.
- Run `scripts/run_flow_benchmark.py` through the documented command below; keep outputs under a caller-provided run directory.
- If a host agent exposes `run_script`, use `run_script("scripts/run_flow_benchmark.py", args=[...])`; otherwise run the Bash/Python command shown below.
- Check the emitted JSON and paired verifier guidance before treating the run as evidence.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/run_flow_benchmark.py` | Primary entrypoint declared by skill_manifest.yaml. | `[FIXTURE_LABEL]` plus `HOLOHUB_ROOT` and `HOLOHUB_BENCHMARK_*` env vars |

## Prerequisites
- Required environment variables: `HOLOHUB_ROOT`, `HOLOHUB_BENCHMARK_APP`.
- Runtime requirements: GPU/CUDA when declared by the manifest; Docker/NVIDIA Container Toolkit when container mode is used; Python packages listed in `runtime.side_effects.pip_packages`.
- Side effects: container mode may write Docker layers under `/var/lib/docker/` and pull images from `https://nvcr.io`; source or sample fetches use `https://github.com`.
- Run commands from the repository root unless an existing section below says otherwise.

## Limitations
- This wraps HoloHub's performance instrumentation only. It does not measure model correctness, tool-count quality, segmentation quality, or bounding-box validity.
- Contract assertions check file presence, optional sha256 pins, operator-path presence, scheduler coverage, and declared latency budgets. They do not prove clinical or domain quality.
- The default mode executes inside the HoloHub benchmarking container created with `./holohub run-container --extra-scripts benchmarking`. Bare-metal runs require HOLOHUB_BENCHMARK_RUN_MODE=local and host installation of benchmark and application dependencies.
- TensorRT-backed applications should be warmed once before collecting latency numbers so engine generation is not mixed into steady-state performance.
- Not for clinical deployment, clinical interpretation, intra-operative guidance, autonomous diagnosis.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| Missing dependency or import error | Runtime package drift from `skill_manifest.yaml`. | Install the packages declared in the manifest or use the documented setup command. |
| Empty or schema-invalid output | Wrong input path, unsupported modality, or upstream failure. | Re-run with a known fixture and inspect the wrapper JSON plus stderr. |
| Validation gate failure | Output violated a declared engineering invariant. | Keep the failed evidence pack and use the gate message to repair inputs or wrapper code. |

Wraps HoloHub's official `benchmarks/holoscan_flow_benchmarking` toolchain
for **any** HoloHub application. The default path is container-first: the
host launches the HoloHub benchmarking container, and the benchmark build
plus `benchmark.py` run inside that container against `/workspace/holohub`.

Two modes:

| Mode | Trigger | What you get |
|---|---|---|
| **Measure** | no contract supplied | Per-scheduler, per-flow latency metrics (min/avg/median/max/p95/p99, tail and flatness). No pass/fail assertion — pure measurement. Works for any HoloHub app. |
| **Verify** | `HOLOHUB_BENCHMARK_CONTRACT=<path/to/contract.yaml>` | Above, plus contract-driven assertions: required data files present, expected operator sequence observed, latency budgets met, scheduler coverage complete, etc. Pass/fail per assertion. |

The skill does not reimplement any HoloHub app, postprocessor, or Holoscan
data-flow tracker. It delegates instrumentation to HoloHub and adds the
contract layer on top.

## Preconditions

Clone HoloHub and set `HOLOHUB_ROOT`. Container mode (default) also needs
Docker, NVIDIA Container Toolkit, an NVIDIA GPU, and `DISPLAY` set for the
Holoviz render path (or run headless via `holoviz.headless: true` in the
app's YAML). Set `HOLOHUB_BENCHMARK_APP` to the HoloHub application name
under `applications/`.

```bash
git clone https://github.com/nvidia-holoscan/holohub.git $HOME/holohub
export HOLOHUB_ROOT=$HOME/holohub
export HOLOHUB_BENCHMARK_APP=<app_name>   # e.g. multiai_ultrasound
```

## What actually runs

This skill benchmarks a HoloHub **benchmark build**, not an app's normal
production launch path. When `HOLOHUB_BENCHMARK_BUILD=true` (the default), the
wrapper runs `./holohub build <app> --local --benchmark --language <language>`;
then it invokes HoloHub's
`benchmarks/holoscan_flow_benchmarking/benchmark.py` for the requested app,
schedulers, runs, instances, and message count. In container mode, both steps
run inside the HoloHub benchmarking container started with
`./holohub run-container <app> --extra-scripts benchmarking`.

So yes: the benchmarked execution uses HoloHub's profiling/data-flow-tracking
logic instead of the customer's ordinary run command. It should be interpreted
as instrumentation-enabled performance evidence. It does **not** edit,
overwrite, or replace the customer's source code, and it does not substitute a
fake application implementation. If an app needs custom runtime arguments or a
specific launch command, pass it through `HOLOHUB_BENCHMARK_RUN_COMMAND`, which
is forwarded to `benchmark.py --run-command`.

Engineering performance benchmarking and verification only. Not for
clinical interpretation, intra-operative guidance, regulatory submission,
or detection-quality claims. Quality verifiers live alongside this skill
under `verifiers/` and consume its evidence pack.

## Quick Start

### Measure mode (any app)

```bash
HOLOHUB_ROOT=/path/to/holohub \
HOLOHUB_BENCHMARK_APP=multiai_ultrasound \
HOLOHUB_BENCHMARK_LANGUAGE=python \
HOLOHUB_BENCHMARK_SCHEDULERS=greedy \
HOLOHUB_BENCHMARK_MESSAGES=200 \
DISPLAY=${DISPLAY:-:1} \
python3 -m eval_engine.run skills/holohub-flow-benchmark \
  --fixture skills/holohub-flow-benchmark/fixtures/default \
  --out runs/multiai_ultrasound_flow
```

No contract supplied → skill emits raw latency metrics for every
flow path it observes, across the requested schedulers. `domain` block
in the output is `{"present": false}`.

### Verify mode (contract-driven)

```bash
HOLOHUB_ROOT=/path/to/holohub \
HOLOHUB_BENCHMARK_APP=endoscopy_tool_tracking \
HOLOHUB_BENCHMARK_CONTRACT=skills/holohub-flow-benchmark/contracts/endoscopy_tool_tracking.yaml \
HOLOHUB_BENCHMARK_LANGUAGE=python \
HOLOHUB_BENCHMARK_SCHEDULERS=greedy,multithread \
DISPLAY=${DISPLAY:-:1} \
python3 -m eval_engine.run skills/holohub-flow-benchmark \
  --fixture skills/holohub-flow-benchmark/fixtures/default \
  --out runs/endoscopy_flow_verify
```

Contract supplied → measure + assert. The evidence pack carries a
`contract` block with one boolean per declared assertion, and the
manifest sanity gate refuses the pack if any required assertion fails.

## Contract format

A contract is a YAML file that pins what a "well-behaved" run of one
HoloHub application looks like. It is intentionally small. See
`contracts/_template.yaml` for the schema and `contracts/endoscopy_tool_tracking.yaml`
for a worked example.

```yaml
# contracts/<app>.yaml
contract_version: 1
app: endoscopy_tool_tracking

# Files the app needs at runtime. Pinned relative to HOLOHUB_ROOT.
# Pinning sha256 is optional; when set, the skill verifies it.
required_data_files:
  - {path: data/endoscopy/tool_loc_convlstm.onnx, sha256: null}
  - {path: data/endoscopy/surgical_video.gxf_entities, sha256: null}
  - {path: data/endoscopy/surgical_video.gxf_index, sha256: null}

# Path to the app entry point, relative to HOLOHUB_ROOT. The skill
# asserts the file exists.
source_file: applications/endoscopy_tool_tracking/python/endoscopy_tool_tracking.py

# The model file whose sha256 is fingerprinted in the evidence pack.
# Optional; if unset the skill skips model fingerprinting.
model_file: data/endoscopy/tool_loc_convlstm.onnx

# Operator-sequence assertions on the parsed data-flow paths.
# "primary_sequence" must appear as a contiguous subsequence in at least
# one observed flow path per scheduler. "direct_paths" must match exactly.
flow_assertions:
  primary_sequence:
    - Endoscopy App.replayer
    - Endoscopy App.format_converter
    - Endoscopy App.lstm_inferer
    - Endoscopy App.tool_tracking_postprocessor
    - Endoscopy App.holoviz
  direct_paths:
    - [Endoscopy App.replayer, Endoscopy App.holoviz]

# Latency budgets. Each is asserted against the primary path metrics
# of every requested scheduler. Omit a budget to skip its check.
latency_budgets:
  p50_ms_max: null
  p95_ms_max: 33.0     # 30 fps surgical viewer hard ceiling
  p99_ms_max: 50.0
  tail_95_100_ms_max: null
  flatness_10_90_ms_max: null
  min_sample_count: 80 # after skip_begin / discard_last trim

# Sample-count sanity. The skill checks that each path has at least
# `min_sample_count` samples after trimming.

# Optional notes shown in the evidence pack for human readers.
notes: |
  30 fps p95 budget assumes Holoviz render path; raise if running headless.
```

The skill exposes assertion results as flat booleans under
`contract.assertions.*` so the manifest sanity-check section can gate on
them with `eq: true`.

## Why a contract instead of code

The endoscopy-specific skill bakes ~6 constants into Python. Adding a
new HoloHub app means a new skill, a new Python file, and duplicated
plumbing. With a contract layer:

- New app = one YAML file under `contracts/`
- The benchmark script, log parser, metric computation, and evidence
  pack stay identical across apps
- Cross-app contract diffs are reviewable in version control

The endoscopy skill is preserved as a documented reference; new apps
should land here.

## Important Knobs (env)

Same surface as the endoscopy skill, with the addition of contract control:

| Env var | Default | Notes |
|---|---|---|
| `HOLOHUB_ROOT` | required | Path to HoloHub checkout |
| `HOLOHUB_BENCHMARK_APP` | required | HoloHub app name under `applications/` |
| `HOLOHUB_BENCHMARK_CONTRACT` | unset | Path to contract YAML; unset = measure mode |
| `HOLOHUB_BENCHMARK_RUN_MODE` | `container` | `container` (default) or `local` |
| `HOLOHUB_BENCHMARK_LANGUAGE` | `python` | `python` or `cpp` |
| `HOLOHUB_BENCHMARK_SCHEDULERS` | `greedy` | csv of greedy,multithread,eventbased |
| `HOLOHUB_BENCHMARK_RUNS` | `1` | runs per scheduler |
| `HOLOHUB_BENCHMARK_INSTANCES` | `1` | parallel app instances |
| `HOLOHUB_BENCHMARK_MESSAGES` | `100` | messages per run |
| `HOLOHUB_BENCHMARK_WORKER_THREADS` | `1` | scheduler worker threads |
| `HOLOHUB_BENCHMARK_MONITOR_GPU` | `false` | enable `gpu_utilization_*.csv` |
| `HOLOHUB_BENCHMARK_BUILD` | `true` | run `./holohub build --benchmark` first |
| `HOLOHUB_BENCHMARK_CONTAINER_ARGS` | unset | extra args passed to `run-container` |
| `HOLOHUB_BENCHMARK_BUILD_ARGS` | unset | extra args passed to the benchmark build |
| `HOLOHUB_BENCHMARK_NO_DOCKER_BUILD` | `false` | pass `--no-docker-build` to `run-container` |
| `HOLOHUB_BENCHMARK_RUN_COMMAND` | unset | override `benchmark.py --run-command` |
| `HOLOHUB_BENCHMARK_CLEAN_OUTPUT` | `true` | remove stale benchmark output before a run |
| `HOLOHUB_BENCHMARK_SKIP_BEGIN_MESSAGES` | `10` | trim warm-up samples |
| `HOLOHUB_BENCHMARK_DISCARD_LAST_MESSAGES` | `10` | trim teardown samples |
| `HOLOHUB_BENCHMARK_SMOKE` | `false` | run a short contract-lint smoke path |
| `HOLOHUB_BENCHMARK_GPU` | `all` | forwarded as `CUDA_VISIBLE_DEVICES` |
| `HOLOHUB_BENCHMARK_OUTPUT_DIR` | `$HOLOHUB_ROOT/build/<app>/flow_benchmark_output` | |
| `HOLOHUB_BENCHMARK_TIMEOUT_SECONDS` | `3600` | per subprocess |
| `DISPLAY` | inherited | required for default Holoviz render path |
| `NVIDIA_VISIBLE_DEVICES` | inherited | container-visible GPU selection when set |

## What This Proves

**Measure mode** proves HoloHub's benchmark instrumentation ran inside
the expected container model, data-flow tracking logs were emitted, and
latency samples were parsed for at least one end-to-end path per
requested scheduler. It fingerprints the HoloHub commit, container
image when available, outer container command, inner benchmark
commands, and output artifacts.

**Verify mode** additionally proves that the configured contract holds
for this app on this hardware: required data files exist (and optionally
match pinned sha256), expected operator sequences are present in the
parsed flow, the requested scheduler set is fully covered, and every
declared latency budget is met on the primary path.

It does not prove model-output quality (detection / segmentation
accuracy). Pair with the corresponding `verifiers/<app>_quality_v*`
skill when decoded model outputs exist.

## Adding a contract for a new app

1. Run the skill once in **measure mode** against the target app to
   discover the actual operator names and data-file layout.
2. Copy `contracts/_template.yaml` to `contracts/<app>.yaml`.
3. Fill in `required_data_files`, `source_file`, `flow_assertions` from
   what step 1 revealed.
4. Pick latency budgets from the app's real-time requirement (e.g.
   30 fps surgical viewer → p95_ms_max = 33; 60 fps AR overlay → 16;
   1 kHz robot loop → 1).
5. Re-run in **verify mode**; iterate until all assertions pass on a
   green baseline.
6. Commit the contract — it is the per-app spec from then on.

---

¹ The contract pattern follows the same "verify pipeline before
claiming correctness" discipline as `nv_segment_ct_finetune`'s baseline
+ regression gate.
