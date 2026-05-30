# Benchmarks

Benchmark manifests describe dataset-loop protocols for `eval_engine/run_benchmark.py`.
They may name local case and ground-truth paths, but the image data and labels
must stay outside git.

Committed files in this directory should be small `*.benchmark.yaml` manifests
that validate against [`../spec/benchmark_dataset.schema.json`](../spec/benchmark_dataset.schema.json).
