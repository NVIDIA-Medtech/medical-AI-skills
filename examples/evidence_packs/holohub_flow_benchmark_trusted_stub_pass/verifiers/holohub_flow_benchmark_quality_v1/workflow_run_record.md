# Workflow Run Record

- run id: 83773464252d
- skill: medagent.verifiers.holohub_flow_benchmark_quality_v1 v0.1.0
- started: 2026-05-26T03:01:44.357761+00:00
- finished: 2026-05-26T03:01:44.474247+00:00
- elapsed: 0.116s
- exit code: 0

## Skill
- dir: verifiers/holohub_flow_benchmark_quality_v1
- entrypoint: scripts/grade.py

## Fixture
- path: examples/evidence_packs/holohub_flow_benchmark_trusted_stub_pass/skill_run
- sha256: b0d4b38038a2ee691204f4ab9673eccbe46e274e8bb7887021fe2738e0c23ef3
- size: 84934 bytes

## Validation
- overall: passed
- schema: passed
- sanity: passed
- runtime: within_envelope
- cost: skipped
- env_pin: skipped
- integrity: clean

## Output (excerpt)
```json
{
  "checks": [
    {
      "name": "target_skill_matches",
      "reason": "skill_id='medagent.holohub_flow_benchmark'",
      "status": "pass"
    },
    {
      "name": "source_pack_passed",
      "reason": "source pack overall='passed'",
      "status": "pass"
    },
    {
      "name": "output_skill_matches",
      "reason": "output.skill='holohub_flow_benchmark'",
      "status": "pass"
    },
    {
      "name": "benchmark_exit_code_zero",
      "reason": "benchmark_exit_code=0",
      "status": "pass"
    },
    {
      "name": "holohub_commit_present",
      "reason": "holohub_commit='4aab4365c361feb60ee607cb91fd5ba6d8cfebb9'",
      "status": "pass"
    },
    {
      "artifacts": [
        {
          "actual_bytes": 37300,
          "actual_sha256": "8f753769ad4347feae94eb352af985c37dbba949008db417ac9a3f1cf61f7862",
          "bytes_match": true,
          "declared_bytes": 37300,
          "declared_path": "logger_greedy_1_1.log",
          "declared_sha256": "8f753769ad4347feae94eb352af985c37dbba949008db417ac9a3f1cf61f7862",
          "exists": true,
          "resolved_path": "examples/evidence_packs/holohub_flow_benchmark_trusted_stub_pass/skill_run/artifacts/flow_benchmark_output/logger_greedy_1_1.log",
          "sha256_match": true
        }
      ],
      "name": "logger_artifacts_hash_match",
      "reason": "logger_files=1",
      "status": "pass"
    },
    {
      "name": "latency_samples_present",
      "reason": "paths=2, total_samples=160, min_path_
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.