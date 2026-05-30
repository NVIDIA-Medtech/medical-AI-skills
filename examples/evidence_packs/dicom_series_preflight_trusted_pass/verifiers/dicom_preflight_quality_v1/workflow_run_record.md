# Workflow Run Record

- run id: cd101ad5b2f4
- skill: medagent.verifiers.dicom_preflight_quality_v1 v0.1.0
- started: 2026-05-26T01:25:16.828339+00:00
- finished: 2026-05-26T01:25:16.947678+00:00
- elapsed: 0.119s
- exit code: 0

## Skill
- dir: verifiers/dicom_preflight_quality_v1
- entrypoint: scripts/grade.py

## Fixture
- path: examples/evidence_packs/dicom_series_preflight_trusted_pass/skill_run
- sha256: b3527c966d57d6fccfeb1f53880abe90a8bcde7ce7f2fc0f9a7d5de985a5cf2f
- size: 27704 bytes

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
  "verifier": {
    "id": "medagent.verifiers.dicom_preflight_quality_v1",
    "version": "0.1.0"
  },
  "target": {
    "evidence_pack": "examples/evidence_packs/dicom_series_preflight_trusted_pass/skill_run",
    "skill_id": "medagent.dicom_series_preflight",
    "source_overall_status": "passed",
    "skill_preflight_verdict": "pass"
  },
  "preflight_gate": {
    "findings": [],
    "n_fail": 0,
    "n_warn": 0,
    "verdict": "pass",
    "acceptable": true
  },
  "checks": [
    {
      "name": "skill_pack_readable",
      "status": "pass",
      "reason": "output.json present and skill id matches"
    },
    {
      "name": "source_skill_passed",
      "status": "pass",
      "reason": "source pack overall='passed'"
    },
    {
      "name": "no_fail_findings",
      "status": "pass",
      "reason": "fail findings: []"
    },
    {
      "name": "orientation_ok",
      "status": "pass",
      "reason": "axcodes=['L', 'P', 'S']"
    },
    {
      "name": "single_series",
      "status": "pass",
      "reason": "n_series=1"
    },
    {
      "name": "no_corrupt_instances",
      "status": "pass",
      "reason": "n_corrupt=0"
    }
  ],
  "overall": "pass"
}
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.