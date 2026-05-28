# Workflow Run Record

- run id: 473233f467de
- skill: medagent.verifiers.skill_completeness_v1 v0.1.0
- started: 2026-05-10T07:29:19.100330+00:00
- finished: 2026-05-10T07:29:19.211719+00:00
- elapsed: 0.111s
- exit code: 0

## Skill
- dir: verifiers/skill_completeness_v1
- entrypoint: scripts/grade.py

## Fixture
- path: skills/radiology-note-summarizer
- sha256: 71b73a823b625bf4cc9a0a7d7af590cca6f73c374dff86212e41decb6a7da49c
- size: 46445 bytes

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
  "target_skill": "skills/radiology-note-summarizer",
  "tier1_structural": {
    "tier_id": "tier1_structural",
    "checks_passed": 19,
    "checks_total": 20,
    "verdict": "fail",
    "blocking_issues": [
      {
        "check": "frontmatter_name_format",
        "pass": false,
        "msg": "name 'radiology_note_summarizer' must match ^[a-z0-9-]+$ (lowercase letters, digits, hyphens only \u2014 Anthropic best-practices)",
        "severity": "block"
      }
    ],
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
  "overall": "fail",
  "blocking_issues_count": 1,
  "advisory_issues_count": 0
}
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.