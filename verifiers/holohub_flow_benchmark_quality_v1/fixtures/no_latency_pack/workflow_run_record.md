# Workflow Run Record

- run id: 86050f51a72e
- skill: medagent.holohub_flow_benchmark v0.1.0
- started: 2026-05-26T02:25:19.328671+00:00
- finished: 2026-05-26T02:25:20.575801+00:00
- elapsed: 1.247s
- exit code: 0

## Skill
- dir: skills/holohub-flow-benchmark
- entrypoint: scripts/run_flow_benchmark.py

## Fixture
- path: skills/holohub-flow-benchmark/fixtures/default
- sha256: bc7f91db9e56d8aa22a5eef3bf883bed1c76f2836c4f278d572fda62814006a8
- size: 271 bytes

## Validation
- overall: passed
- schema: passed
- sanity: passed
- runtime: within_envelope
- cost: passed
- env_pin: skipped
- integrity: clean

## Output (excerpt)
```json
{
  "skill": "holohub_flow_benchmark",
  "input": {
    "fixture": "<repo>/skills/holohub-flow-benchmark/fixtures/default"
  },
  "environment": {
    "python_executable": "python3",
    "cuda_visible_devices": null,
    "nvidia_visible_devices": null,
    "display": null,
    "display_configured": false
  },
  "plan": {
    "app": "endoscopy_tool_tracking",
    "language": "python",
    "schedulers": [
      "greedy"
    ],
    "runs": 1,
    "instances": 1,
    "messages": 100,
    "worker_threads": 1,
    "monitor_gpu": true,
    "run_mode": "local",
    "skip_begin_messages": 10,
    "discard_last_messages": 10,
    "build_requested": false,
    "no_docker_build": false,
    "clean_output": true,
    "mode": "verify",
    "smoke_mode": false,
    "rationale": [
      "run HoloHub benchmarking inside the HoloHub container by default",
      "delegate instrumentation to HoloHub holoscan_flow_benchmarking",
      "parse host-visible data-flow tracking logs into evidence-pack latency metrics"
    ]
  },
  "invocation": {
    "holohub_root": "<stub_holohub_root>",
    "holohub_commit": "73efd0b8653b4ccc6f62af44932e3dfd8dadfff6",
    "benchmark_script": "<stub_holohub_root>/benchmarks/holoscan_flow_benchmarking/benchmark.py",
    "output_dir": "<repo>/verifiers/holohub_flow_benchmark_quality_v1/fixtures/no_latency_pack/artifacts/flow_benchmark_output",
    "con
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.