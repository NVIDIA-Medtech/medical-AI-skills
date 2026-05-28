# Workflow Run Record

- run id: 84a41bfa1dbe
- skill: medagent.verifiers.find_skills_quality_v1 v0.1.0
- started: 2026-05-26T01:25:16.637751+00:00
- finished: 2026-05-26T01:25:16.751695+00:00
- elapsed: 0.114s
- exit code: 0

## Skill
- dir: verifiers/find_skills_quality_v1
- entrypoint: scripts/grade.py

## Fixture
- path: examples/evidence_packs/find_skills_trusted_pass/skill_run
- sha256: 611c42d594b9d4792f52cda4f823986619f4abbd3f7d72321878310c05a67643
- size: 40701 bytes

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
    "id": "medagent.verifiers.find_skills_quality_v1",
    "version": "0.1.0"
  },
  "target": {
    "evidence_pack": "examples/evidence_packs/find_skills_trusted_pass/skill_run",
    "skill_id": "medagent.find_skills",
    "source_overall_status": "passed"
  },
  "selector_quality": {
    "n_fail": 0,
    "n_warn": 0,
    "verdict": "pass",
    "acceptable": true,
    "query": "segment a CT NIfTI volume",
    "catalog_count": 28,
    "recommendation_count": 3,
    "top_id": "medagent.nv_segment_ct"
  },
  "checks": [
    {
      "name": "target_skill_matches",
      "status": "pass",
      "reason": "skill_id='medagent.find_skills'"
    },
    {
      "name": "source_pack_passed",
      "status": "pass",
      "reason": "source pack overall='passed'"
    },
    {
      "name": "query_present",
      "status": "pass",
      "reason": "query='segment a CT NIfTI volume'"
    },
    {
      "name": "catalog_count_positive",
      "status": "pass",
      "reason": "catalog.count=28, recommendations=3"
    },
    {
      "name": "recommendations_nonempty",
      "status": "pass",
      "reason": "recommendations=3"
    },
    {
      "name": "top_recommendation_is_first",
      "status": "pass",
      "reason": "top='medagent.nv_segment_ct', first='medagent.nv_segment_ct'"
    },
    {
      "name": "scores_sorted_desc",
      "status": "pass",
      "reason": "scores=[12, 12, 11]"
    },
    {
      "name": "no_fit_matches_top_score",
      "status": "pass",

```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.
