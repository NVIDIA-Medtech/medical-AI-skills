# skills/ - Agent Guide

Each directory under `skills/` is a **publishable** wrapper users run with their
own data via `SKILL.md` and `scripts/`. The eval_engine can also run the same
spec against a fixture to produce an evidence pack.

## Layout

```text
skills/<name>/
  SKILL.md
  skill_manifest.yaml
  scripts/
  validators/
  fixtures/
  tests/
```

`SKILL.md` and `skill_manifest.yaml` are required. Use the other directories
when the spec needs them.

## Rules

- Wrap the upstream tool through its documented entry point.
- Declare `upstream_refs` in the manifest for every upstream package, hosted
  model, model repo, or git repo that materially affects behavior.
- Do not patch or rewrite upstream implementation files during normal skill
  runs. Prefer the upstream README/requirements path, stage documented configs
  explicitly, and use reference baselines to catch checkpoint, config, data
  split, or dependency drift.
- Do not import from `eval_engine/`.
- Emit JSON on stdout.
- Reference a JSON schema from the manifest when output is gated.
- Keep fixtures small, synthetic/public, and free of patient identifiers.
- Declare limitations instead of inventing unsupported validation.
- Use `paired_verifiers[]` when a domain invariant needs a second pass.
- Make no clinical, diagnostic, or regulatory claims.

## SKILL.md style

SKILL.md authoring (frontmatter first, naming, descriptions, progressive
disclosure, evals/benchmark expectations, anti-patterns) follows
[`../docs/skill-authoring-best-practices.md`](../docs/skill-authoring-best-practices.md).
That doc is Medical AI Skills application of Anthropic's
[Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
plus NVIDIA's external skills publishing guide — read it before adding or
significantly editing a SKILL.md.

`dicom_metadata_extract/` is the smallest example to copy.
