---
name: holohub-flow-benchmark-quality-v1
description: Used to verify holohub-flow-benchmark evidence packs for logger artifact hashes, scheduler coverage, latency samples, benchmark-log completion, contract assertions, and non-clinical scope disclosure.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - medtech
    - holohub
    - benchmark
    - verifier
---

# HoloHub Flow Benchmark Quality Verifier

## Purpose
- Used for deterministic second-pass review of a `holohub-flow-benchmark` evidence pack.
- Checks source-pack success, benchmark exit status, logger artifact hashes, scheduler coverage, latency sample counts, benchmark-log completion, GPU-utilization artifact consistency when requested, contract assertions, and non-clinical scope disclosure.
- Manifest I/O: inputs are `holohub_flow_benchmark_evidence_pack`; outputs are `holohub_flow_benchmark_quality_report`.

## Instructions
- Use this verifier only on an evidence pack directory produced by `skills/holohub-flow-benchmark`.
- Run it through `eval_engine/run.py` when producing verifier evidence.
- The verifier entrypoint is `scripts/grade.py`; do not replace it with prompt-only review.
- Treat a pass as engineering-performance evidence only, not as clinical, surgical, model-quality, or regulatory validation.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/grade.py` | Primary verifier entrypoint declared by `skill_manifest.yaml`. | `EVIDENCE_PACK_DIR` |

## Prerequisites
- Runtime requirements: Python standard library only.
- The input directory must contain `manifest.json`, `validation_summary.json`, and `output.json` from a `holohub-flow-benchmark` evidence pack.
- Host-visible logger artifacts referenced by `output.json` must be available for artifact/hash checks.

## Limitations
- Does not validate model correctness, surgical tool detections, segmentation quality, or clinical utility.
- Latency-budget results are tied to the source contract and host calibration.
- Does not re-run HoloHub or inspect container-internal state.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| `target_skill_matches` fails | The fixture is not a `holohub-flow-benchmark` evidence pack. | Re-run the verifier against the source skill pack directory. |
| `logger_artifacts_hash_match` fails | Logger artifacts are missing, moved, empty, or hash-mismatched. | Regenerate the benchmark pack with host-visible logger output. |
| `scheduler_coverage_complete` fails | Requested scheduler logs are missing or empty. | Check `HOLOHUB_BENCHMARK_SCHEDULERS` and benchmark output. |
| `contract_assertions_passed` fails | Source pack contract checks found missing paths, missing operators, or budget failures. | Inspect the source pack's `contract` block and app-specific contract YAML. |

## Example

```bash
python eval_engine/run.py verifiers/holohub_flow_benchmark_quality_v1 \
  --fixture runs/holohub_flow_benchmark_demo \
  --out runs/holohub_flow_benchmark_quality

python verifiers/holohub_flow_benchmark_quality_v1/scripts/grade.py \
  runs/holohub_flow_benchmark_demo
```
