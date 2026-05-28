# Workflow Run Record

- run id: a7807420ae19
- skill: medagent.verifiers.skill_completeness_v1 v0.1.0
- started: 2026-05-10T07:30:18.278421+00:00
- finished: 2026-05-10T07:30:18.390399+00:00
- elapsed: 0.112s
- exit code: 0

## Skill
- dir: verifiers/skill_completeness_v1
- entrypoint: scripts/grade.py

## Fixture
- path: skills/dicom-series-to-volume
- sha256: adfb7757cab61b246b977fa41799c0e86570c644d8b1fbbeb28a53283bddc9ad
- size: 662485 bytes

## Validation
- overall: passed
- schema: passed
- sanity: passed
- runtime: within_envelope
- cost: skipped
- integrity: minor

## Output (excerpt)
```json
{
  "skill": "skill_completeness_v1",
  "verifier_version": "0.2.0",
  "target_skill": "skills/dicom-series-to-volume",
  "tier1_structural": {
    "tier_id": "tier1_structural",
    "checks_passed": 20,
    "checks_total": 20,
    "verdict": "pass",
    "blocking_issues": [],
    "advisory_issues": []
  },
  "tier2_spec_honesty": {
    "tier_id": "tier2_spec_honesty",
    "checks_passed": 11,
    "checks_total": 11,
    "verdict": "pass",
    "blocking_issues": [],
    "advisory_issues": []
  },
  "tier3_documentation": {
    "tier_id": "tier3_documentation",
    "verdict": "skipped",
    "reason": "v0.2 \u2014 requires LLM rubric grading of SKILL.md vs manifest consistency, intended-use clarity, presence of not_for section"
  },
  "tier4_tests": {
    "tier_id": "tier4_tests",
    "verdict": "skipped",
    "reason": "v0.2 \u2014 requires test execution + coverage assessment"
  },
  "overall": "pass",
  "blocking_issues_count": 0,
  "advisory_issues_count": 0
}
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.