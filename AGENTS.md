# AGENTS.md - Medical AI Skills

This is the map for agents working in this repo. Subdirectory `AGENTS.md`
files override this one.

## Repo purpose

Publishable, agent-callable medtech skills. Manifests, evidence packs,
verifiers, and the eval engine make those skills reproducible and trustworthy.
This is not an agent runtime and not a clinical tool.

**Primary path:** user runs a skill with their own data via `SKILL.md` and
`scripts/`.

**Trust path:** `eval_engine` runs a skill against a fixture and writes an
evidence pack; verifiers audit skills or packs when domain claims need a second
pass.

## Status

MVP scaffolding; `spec/` is draft, not a released package API.

## Agent tasks

[`docs/agent-tasks.md`](docs/agent-tasks.md) (task → read → command).

## Map

- `README.md`: product positioning and user-facing commands.
- `ARCHITECTURE.md`: object model, gate ladder, directory boundaries.
- `CONTRIBUTING.md`: authoring lanes and review rules.
- `docs/using-skills.md`: discover and run skills with local data.
- `docs/prompts/mr-rate-ingest.md`: copy-paste prompts for `nv-curate-study` / `nv-curate-batch`.
- `docs/mr-rate-ingest-ops.md`: live gates, MRI fixtures, required status language.

## MR-RATE ingest

When the user asks to curate real studies, run `--mode live` only. Do not run
`--mode mock`, and do not switch the report track to mock when the LLM or a
stage fails. Mock mode is for CI fixtures, not for a data tranche.

On a real-data error, fix the skill or MR-RATE code in a general way (config
and paths, not one `study_uid`) and record the failure. Leave
`reports.status=not_run` or `live_failed` with `blocker` set. A live MRI plus
mock reports is not a finished ingest.
- `skills/nv-curate-study/`: curate one MRI + report for MR-RATE.
- `skills/nv-curate-batch/`: curate a tranche by calling `nv-curate-study` per study.
- `docs/authoring-skills.md`: add a publishable wrapper skill.
- `docs/skill-scope.md`: what belongs in the public skill catalog.
- `docs/trust-and-evidence.md`: manifests, packs, replay, verifiers.
- `docs/spec-model.md`: where each check belongs.
- `docs/replay.md`: evidence-pack files and replay behavior.
- `docs/skill-authoring-best-practices.md`, `spec/`: SKILL style and schemas.
- `skills/`: publishable wrapper specs (primary product).
- `verifiers/`: skill-shaped auditors (trust layer).
- `eval_engine/`: runners, gates, diff, catalog, lint (support harness).
- `examples/`: curated evidence packs, studies, and tiny fixtures.
- `examples/INDEX.md`, `benchmarks/`, `tools/`, `Makefile`.

`discussions/` is local-only and gitignored. If a brief references a missing
file there, ask the dispatcher instead of inventing content.

## Where to put work

| Change | Location |
|---|---|
| New user-facing wrapped tool | `skills/<name>/` |
| New second-pass audit | `verifiers/<name>/` |
| New generic gate or pack writer | `eval_engine/` |
| New manifest field or schema rule | `spec/` (+ update `docs/spec-model.md`) |
| Usage or authoring docs | `docs/` |
| Curated proof pack or study | `examples/` |
| Shared dataset protocol (no data) | `benchmarks/` |
| Maintainer profiler or experiment | `tools/` |
| Local generated output | `runs/` |

If the contribution helps an end user solve a medtech task with their own data,
it belongs in `skills/`. If it audits a skill or evidence pack, use
`verifiers/`. If it changes how evidence is generated, use `eval_engine/`.

## Commands (copy-paste)

```bash
make list-skills
make run-skill SKILL=dicom_metadata_extract \
  FIXTURE=skills/dicom-metadata-extract/fixtures/sample_ct.dcm \
  OUT=runs/demo
make lint
make test
make verify-skills
make verify
```

`make verify` smoke-tests the harness; not full-repo skill verification.
`make help` lists common targets; `make help-all` lists every target.

## Do not

- Change the product framing to "evidence-pack platform" or "generic evaluator."
- Add NeMo Agent Toolkit, LangChain, or LangGraph as **v0 repo dependencies**
  (optional experiments may live under `tools/` with their own venv).
- Implement a generic skill evaluator.
- Add clinical decision-support, patient-facing chatbot, generic LLM utility,
  leaderboard, or EHR write-path skills.
- Make clinical, diagnostic, or regulatory claims.
- Commit patient data, DICOM/NIfTI volumes, DICOM SEG files, weights, or large
  run artifacts.
- Commit generated provider responses, per-repeat study JSON, detailed reports,
  logs, or runtime environments; use `runs/` or another ignored path.
- Add marketing tone.
- Import `eval_engine/` from `skills/` or `verifiers/`.

## Spec files

Do not rename evidence-pack files without explicit approval:
`validation_summary.json`, `manifest.json`, `runtime_profile.json`,
`agent_run_trace.jsonl`, `integrity_check.json`, `cost_profile.json`,
`environment.lock`, `replay.sh`, `output.json`, `workflow_run_record.md`.

Do not rename eval_engine-read manifest fields without a migration plan:
`runtime.entrypoint`, `runtime.env_required`, `validation.sanity_checks`,
`validation.expected_runtime_seconds`, `validation.expected_cost`,
`outputs[].schema`.

Adding fields, gates, or manifest keys is additive.

## Defaults

Python 3.11+, pydicom 3.x, pytest, Typer, jsonschema, PyYAML, NumPy, NiBabel,
Apache 2.0, plain Python.

When unsure, choose the reversible option; note gaps in the relevant
manifest's `limitations`.
