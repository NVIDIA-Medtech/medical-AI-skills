# tools/ - Agent Guide

Maintainer utilities only. Do not treat `tools/` as the product surface.

## Rules

- Each tool ships `README.md` with exact reproduce commands.
- No patient data, secrets, API keys, or large generated artifacts in git.
- Generated output goes under `runs/` (gitignored) unless promoted to `examples/`
  as curated evidence with review.
- **Do not** import from `tools/` in `skills/` or `verifiers/` unless the skill
  manifest and `SKILL.md` explicitly document the dependency.
- NeMo Agent Toolkit and similar heavy deps stay in tool-local venvs under
  `tools/<name>/`, not repo-root v0 dependencies.

## Graduation

Move generic, tested logic to `eval_engine/`, `spec/`, or `docs/` only when it
is no longer an experiment. Update `ARCHITECTURE.md` when adding a new top-level
tool directory.

## Extend

Add `tools/<name>/` with `README.md`. Link from this file's layout table when
the tool is stable enough for other maintainers to run.
