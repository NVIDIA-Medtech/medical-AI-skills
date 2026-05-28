# Workflow Run Record

- run id: d46f7e84a7c3
- skill: medagent.holohub_flow_benchmark v0.1.0
- started: 2026-05-26T02:58:23.605449+00:00
- finished: 2026-05-26T02:58:24.979057+00:00
- elapsed: 1.374s
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
    "python_executable": "<python>",
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
    "holohub_root": "/tmp/holohub-flow-trusted-3ruh67gp/holohub",
    "holohub_commit": "4aab4365c361feb60ee607cb91fd5ba6d8cfebb9",
    "benchmark_script": "/tmp/holohub-flow-trusted-3ruh67gp/holohub/benchmarks/holoscan_flow_benchmarking/benchmark.py",
    "output_dir": "<repo>/examples/evidence_packs/holohub_flow_benchmark_trusted_stub_pass/skill_run/artifact
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.