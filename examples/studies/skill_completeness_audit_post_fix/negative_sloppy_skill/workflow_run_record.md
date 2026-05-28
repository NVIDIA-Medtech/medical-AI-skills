# Workflow Run Record

- run id: 1b69f0910f12
- skill: medagent.verifiers.skill_completeness_v1 v0.1.0
- started: 2026-05-10T07:30:20.999278+00:00
- finished: 2026-05-10T07:30:21.110952+00:00
- elapsed: 0.112s
- exit code: 0

## Skill
- dir: verifiers/skill_completeness_v1
- entrypoint: scripts/grade.py

## Fixture
- path: verifiers/skill_completeness_v1/fixtures/negative_sloppy_skill
- sha256: 986c3ddbe3ccddfc31856cc226b30771495454a228829386266144ec113c23a3
- size: 1322 bytes

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
  "target_skill": "verifiers/skill_completeness_v1/fixtures/negative_sloppy_skill",
  "tier1_structural": {
    "tier_id": "tier1_structural",
    "checks_passed": 17,
    "checks_total": 20,
    "verdict": "fail",
    "blocking_issues": [
      {
        "check": "frontmatter_name_format",
        "pass": false,
        "msg": "name 'sloppy_skill' must match ^[a-z0-9-]+$ (lowercase letters, digits, hyphens only \u2014 Anthropic best-practices)",
        "severity": "block"
      },
      {
        "check": "manifest_field:intended_use",
        "pass": false,
        "msg": "manifest missing required field 'intended_use'",
        "severity": "block"
      },
      {
        "check": "entrypoint_file_exists",
        "pass": false,
        "msg": "runtime.entrypoint refers to 'scripts/missing_entrypoint.py' which does not exist on disk",
        "severity": "block"
      }
    ],
    "advisory_issues": []
  },
  "tier2_spec_honesty": {
    "tier_id": "tier2_spec_honesty",
    "checks_passed": 7,
    "checks_total": 10,
    "verdict": "fail",
    "blocking_issues": [
      {
        "check": "runtime_side_effects_declared",
        "pass": false,
        "msg": "runtime.side_effects block missing \u2014 declare it (CONTRIBUTING.md \u00a7Side effects)",
        "severity": "block"
      }
    ],
    "advisory_issues": [
      {
        "check": "at_least_one_fixture",
        "pass": false,

```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.