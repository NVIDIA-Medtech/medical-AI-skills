# benchmark_decathlon_spleen_clean

Independent 41-case benchmark run on the clean Medical Decathlon Task09
Spleen distribution. Real `eval_engine/run_benchmark.py` invocation, full
evidence pack (no derivation, no filtering).

- run id: 312affba6284
- skill: medagent.nv_segment_ct v0.2.0
- benchmark manifest: `.workbench_data/datasets/decathlon_spleen.benchmark.yaml`
- started: 2026-05-11T06:44:14.183632+00:00
- finished: 2026-05-11T06:49:34.274754+00:00
- elapsed: 320.091s on RTX 6000 Ada + CUDA 13.0
- cases: 41 / 41 passed
- overall: passed

## Intended use

**Drift-comparison reference** anchored to a specific tuple:

- skill: `medagent.nv_segment_ct` v0.2.0 (VISTA3D 132-class, label vector `[3]`)
- host: NVIDIA RTX 6000 Ada Generation, CUDA 13.0
- python: 3.12.3
- env fingerprint: `7b37b2170f57f5e7`
- dataset: Task09_Spleen `imagesTr/` + `labelsTr/` (CC-BY-SA 4.0)

Diff a future run of the same skill against this pack to detect
regression on representative load (model retrained, CUDA upgraded,
monai version moved, etc.).

**Not** a cross-skill performance comparison. This pack is a drift anchor for
one spec, not a performance-ordering artifact.

## Clean Dice distribution (41 cases)

| stat | Dice | IoU | Hausdorff |
|---|---|---|---|
| mean   | 0.9578 | 0.9192 | 5.70 |
| median | 0.9608 | 0.9246 | 5.00 |
| p10    | 0.9422 | 0.8908 | 3.93 |
| min    | 0.9160 | 0.8450 | 3.24 |
| max    | 0.9723 | 0.9460 | 12.16 |

41 / 41 cases pass. Tight clustering; nothing tail-heavy.

## Relation to `benchmark_decathlon_with_corruption/`

Sibling pack — runs the same skill on the same 41 clean cases plus 3
deliberately-corrupted variants under tighter gates. The 41 clean
rows are bit-identical between the two packs on this anchor
(VISTA3D's inference path happens to be deterministic on this GPU /
CUDA combination); a future hardware or library change may introduce
~1e-4 floating-point jitter, which is expected and not drift.

## Files

- `dataset_run.jsonl` — one line per case with metrics and paths
- `output.json` — aggregate benchmark summary
- `manifest.json` — run id, fixture sha, env fingerprint, command
- `environment.lock` — pip freeze (385 lines)
- `agent_run_trace.jsonl` — start/end events
- `runtime_profile.json` — wall-clock timing
- `integrity_check.json` — skill-content red-team scan
- `validation_summary.json` — preflight + sanity-gate results
- `replay.sh` — auto-generated `eval_engine/run_benchmark.py` invocation

## Caveats

- Metrics are engineering-time checks, not clinical performance claims.
- Replay requires Task09_Spleen locally (`.workbench_data/datasets/Task09_Spleen/`); the dataset is not committed.
