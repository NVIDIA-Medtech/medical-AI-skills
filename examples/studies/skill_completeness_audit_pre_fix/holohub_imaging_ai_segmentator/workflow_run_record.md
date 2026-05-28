# Workflow Run Record

- run id: dddd0f942783
- skill: medagent.verifiers.skill_completeness_v1 v0.1.0
- started: 2026-05-10T07:29:17.864447+00:00
- finished: 2026-05-10T07:29:17.975086+00:00
- elapsed: 0.111s
- exit code: 0

## Skill
- dir: verifiers/skill_completeness_v1
- entrypoint: scripts/grade.py

## Fixture
- path: skills/holohub-imaging-ai-segmentator
- sha256: 091072c0e225edd2eb2dc751a1c889f95b81f6ff49478185eaeb29a03cfc3608
- size: 24366 bytes

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
  "target_skill": "skills/holohub-imaging-ai-segmentator",
  "tier1_structural": {
    "tier_id": "tier1_structural",
    "checks_passed": 19,
    "checks_total": 20,
    "verdict": "fail",
    "blocking_issues": [
      {
        "check": "frontmatter_name_format",
        "pass": false,
        "msg": "name 'holohub_imaging_ai_segmentator' must match ^[a-z0-9-]+$ (lowercase letters, digits, hyphens only \u2014 Anthropic best-practices)",
        "severity": "block"
      }
    ],
    "advisory_issues": []
  },
  "tier2_spec_honesty": {
    "tier_id": "tier2_spec_honesty",
    "checks_passed": 10,
    "checks_total": 11,
    "verdict": "pass",
    "blocking_issues": [],
    "advisory_issues": [
      {
        "check": "at_least_one_fixture",
        "pass": false,
        "msg": "no fixtures under fixtures/ \u2014 add at least one synthetic or public sample",
        "severity": "advisory"
      }
    ]
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
  "overall": "fail",
  "blocking_issues_count": 1,
  "advisory_issues_
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.