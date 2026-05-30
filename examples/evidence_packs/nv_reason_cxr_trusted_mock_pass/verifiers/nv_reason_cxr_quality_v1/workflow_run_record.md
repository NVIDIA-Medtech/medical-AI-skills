# Workflow Run Record

- run id: 141a1068ce38
- skill: medagent.verifiers.nv_reason_cxr_quality_v1 v0.1.0
- started: 2026-05-26T02:12:40.738756+00:00
- finished: 2026-05-26T02:12:40.853170+00:00
- elapsed: 0.114s
- exit code: 0

## Skill
- dir: verifiers/nv_reason_cxr_quality_v1
- entrypoint: scripts/grade.py

## Fixture
- path: examples/evidence_packs/nv_reason_cxr_trusted_mock_pass/skill_run
- sha256: a9b2ed64a8694c55fad4f8d285ffc286ab6a0a70b2eb26f856af7b18e7e16201
- size: 27409 bytes

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
      "reason": "skill_id='medagent.nv_reason_cxr'",
      "status": "pass"
    },
    {
      "name": "source_pack_passed",
      "reason": "source pack overall='passed'",
      "status": "pass"
    },
    {
      "name": "output_skill_matches",
      "reason": "output.skill='nv_reason_cxr'",
      "status": "pass"
    },
    {
      "name": "fixture_loaded",
      "reason": "fixture=skills/nv-reason-cxr/fixtures/synthetic_cxr_input.json",
      "status": "pass"
    },
    {
      "name": "case_id_matches_fixture",
      "reason": "input='synthetic-cxr-smoke', fixture='synthetic-cxr-smoke'",
      "status": "pass"
    },
    {
      "name": "prompt_matches_fixture",
      "reason": "input='Find abnormalities and support devices.', fixture='Find abnormalities and support devices.'",
      "status": "pass"
    },
    {
      "name": "image_metadata_shape",
      "reason": "format='png', source='generated_fixture', size=96x96",
      "status": "pass"
    },
    {
      "name": "image_file_readable",
      "reason": "image=examples/evidence_packs/nv_reason_cxr_trusted_mock_pass/skill_run/artifacts/input_synthetic_chest_xray.png",
      "status": "pass"
    },
    {
      "name": "image_sha256_matches",
      "reason": "reported='767c7ad1c4e799c0b177015970ef7dafa7feedcfad11e03c992146cffb6569cf', actual='767c7ad1c4e799c0b177015970ef7dafa7feedcfad11e03c992146cffb6569cf'",
      "status": "pass"
    },
    {
      "name": "
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.