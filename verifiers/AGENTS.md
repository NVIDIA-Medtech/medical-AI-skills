# verifiers/ - Agent Guide

Verifiers are skill-shaped **auditors** for the trust layer. They audit a skill
directory or evidence-pack directory and run through the same eval_engine
contract as publishable skills, but they are not medtech capabilities end users
select for their own clinical-engineering data.

## Layout

```text
verifiers/<name>/
  SKILL.md
  skill_manifest.yaml
  scripts/
  validators/
  fixtures/
  tests/
```

## Rules

- Do not import from `eval_engine/`.
- Put verifier-only shared grader helpers under `verifiers/_shared/`.
- Include positive and negative fixtures for meaningful failure modes.
- Assert metrics and failure reasons in tests.
- Keep output deterministic unless marked advisory or skipped.
- Do not make clinical, diagnostic, or regulatory claims.

Target skills refer to verifiers with `paired_verifiers[]`.
