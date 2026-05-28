# Workflow Run Record

- run id: b29343e9ba7c
- skill: medagent.verifiers.radiology_note_summary_quality_v1 v0.1.0
- started: 2026-05-26T01:59:46.190792+00:00
- finished: 2026-05-26T01:59:46.305526+00:00
- elapsed: 0.115s
- exit code: 0

## Skill
- dir: verifiers/radiology_note_summary_quality_v1
- entrypoint: scripts/grade.py

## Fixture
- path: examples/evidence_packs/radiology_note_summarizer_trusted_mock_pass/skill_run
- sha256: f9db9c2eed015df2fbe2e89b0c92e53bd3ad082ba2a34a1dc7af6fd6cd6e2c28
- size: 25435 bytes

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
      "reason": "skill_id='radiology_note_summarizer'",
      "status": "pass"
    },
    {
      "name": "source_pack_passed",
      "reason": "source pack overall='passed'",
      "status": "pass"
    },
    {
      "name": "fixture_loaded",
      "reason": "fixture=skills/radiology-note-summarizer/fixtures/case_001_input.json",
      "status": "pass"
    },
    {
      "name": "study_uid_echoed",
      "reason": "output='SYNTH-STUDY-001', fixture='SYNTH-STUDY-001'",
      "status": "pass"
    },
    {
      "name": "modality_echoed_in_prose",
      "reason": "modality='CT'",
      "status": "pass"
    },
    {
      "name": "body_part_echoed_in_prose",
      "reason": "body_part='ABDOMEN'",
      "status": "pass"
    },
    {
      "name": "findings_nonempty",
      "reason": "findings=4",
      "status": "pass"
    },
    {
      "name": "impressions_nonempty",
      "reason": "impressions must be a non-empty string",
      "status": "pass"
    },
    {
      "name": "flags_for_followup_list",
      "reason": "flags_for_followup must be present as a list",
      "status": "pass"
    },
    {
      "name": "model_identity_matches",
      "reason": "runtime.model='nvidia/openai/gpt-oss-20b'",
      "status": "pass"
    },
    {
      "name": "endpoint_matches",
      "reason": "runtime.endpoint='https://inference-api.nvidia.com/v1'",
      "status": "pass"
    },
    {
      "name": "temperature_matches",
      "re
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.