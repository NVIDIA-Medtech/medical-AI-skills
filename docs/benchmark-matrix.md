# Benchmark Matrix

Medical AI Skills is a **catalogue of skill wrappers** by default, but a catalogue alone cannot tell a user "which skill should I run for this task". The benchmark matrix is the comparison surface that closes that gap. It produces a versioned, per-task-class, per-axis measurement of every skill that participates, with no single rank score and no aggregate across benchmarks.

> Benchmark matrix, not leaderboard. Each task class ships a curated, versioned reference fixture battery; skills are measured on it per-axis (accuracy, latency, memory, license, side-effects). Pareto trade-offs are displayed.

— Design framing committed 2026-05-17. The matrix renders the per-axis numbers; the user picks the trade-off that matches their situation. The renderer deliberately does **not** collapse the axes into a single number.

## Pieces

| Surface | Location | Role |
|---|---|---|
| Benchmark manifest | `benchmarks/<id>.benchmark.yaml` | Declares the curated fixture battery, ground-truth mapping, axes, and sanity checks. |
| Benchmark schema (input) | `spec/benchmark_dataset.schema.json` | Validates the manifest. |
| Benchmark result schema (output) | `spec/benchmark_result.schema.json` | Validates the per-run `output.json` inside a benchmark evidence pack. |
| Runner | `eval_engine/run_benchmark.py` (`make run-benchmark`) | Runs one skill against one benchmark; emits a `pack_kind=benchmark_run` pack. |
| Renderer | `eval_engine/render_baselines.py` (`make bench-matrix`) | Globs benchmark packs, groups by benchmark, prints one markdown table per benchmark. |
| Skill opt-in | `skill_manifest.yaml -> benchmarks:` (optional list) | Names the benchmark IDs the skill claims to support. Advisory; runner does not enforce. |

## Adding a new task class

1. Decide the curated cases. They must be small (≤ ~10), licensed appropriately, and stored under a path that `.gitignore`s the heavy data (the Medical AI Skills convention is `.workbench_data/datasets/<dataset>/`).
2. Author `benchmarks/<task_class>_<dataset>.benchmark.yaml`. Required: `format: benchmark_dataset`, `dataset`, `cases`. Optional: `axes`, `sanity_checks`, `prediction`, `ground_truth`. See `benchmarks/ct_segmentation_spleen_msd09.benchmark.yaml` for a complete example with label-vocabulary remapping (VISTA3D class 3 → MSD class 1).
3. Declare the axes block. Each axis: `name`, `field` (dotted path into the aggregate output), `direction` (`higher_better`|`lower_better`), `unit`. The renderer sorts rows by the first `higher_better` axis descending.
4. Verify with `python3 -m eval_engine.lint_repo` (the schema validates automatically when the runner loads the manifest).

## Adding a skill to an existing benchmark

1. In the skill's `skill_manifest.yaml`, add the benchmark id under top-level `benchmarks: [<id>, …]`. This is advisory metadata only; it does not affect run-time gates.
2. Verify the skill emits the prediction path the benchmark's `prediction.path` expects (default: `output.path`).
3. Run `make run-benchmark SKILL=<name> BENCHMARK=benchmarks/<id>.benchmark.yaml BENCHMARK_OUT=runs/baselines/<skill>_<id>`.
4. Re-run `make bench-matrix` to see the skill appear in the table.

## Rendering

```bash
# All benchmarks; print to stdout
make bench-matrix

# One benchmark; print to stdout
make bench-matrix BENCHMARK=ct_segmentation_spleen_msd09

# Write to a file
make bench-matrix BENCHMARK_OUT=runs/matrix.md
```

The renderer reads `runs/`, `examples/evidence_packs/`, and `examples/studies/` for benchmark packs (identified by `manifest.json -> pack_kind == "benchmark_run"`), groups by benchmark dataset, and prints one table per benchmark.

## Relation to the evidence pack

A benchmark run **is** an evidence pack — same provenance, same integrity gates, same replay script. The only difference is the runner's per-case loop and the additional `dataset_run.jsonl` artefact. A benchmark pack written by `run_benchmark.py` carries `pack_kind: "benchmark_run"`, distinct from `skill_run` and `llm_skill_run`. The renderer treats every such pack as a candidate baseline row.

## What this does **not** do

- It does not collapse axes into a single rank. A "best skill" cannot be named without a use-case profile (compute budget, licence tolerance, accuracy floor, latency cap). The renderer surfaces the trade-offs; the user decides.
- It does not enforce statistical reporting. There is no CI computation, no multi-seed, no subgroup analysis today.
- It does not download datasets. Manifests reference local paths (under `.workbench_data/`); each contributor is responsible for staging the cases under the licence they hold.

## Engineering caveats

- Hausdorff distance requires `scipy`; the runner falls back to a naive computation that is correct on tiny synthetic masks but will refuse on large medical volumes (≥ 25M voxel pairs).
- VISTA3D and MSD09 use different label vocabularies for the same organ. The `gt_labels:` override on each benchmark case targets the GT mask only and is the right knob for this kind of mismatch.
- The matrix renderer treats missing axis values (`null`) as the worst rank for sorting purposes. Skills with no real number on the lead axis sink to the bottom rather than disappearing.
