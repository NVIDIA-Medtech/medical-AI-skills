# Architecture

This file defines the repo shape. Product framing lives in
[`README.md`](README.md). Field-level ownership lives in
[`docs/spec-model.md`](docs/spec-model.md).

## Core paths

```text
skill + user input             -> useful local result
skill + manifest + fixture     -> evidence pack
evidence pack + verifier       -> verifier evidence pack
```

- **Skill**: publishable wrapper under `skills/` that calls one upstream tool
  through its documented entry point. Users run it with their own data via
  `SKILL.md` and `scripts/`.
- **Manifest**: `skill_manifest.yaml`, the machine contract for inputs, outputs,
  runtime, side effects, gates, and paired verifiers. Supports integration and
  trust; not the user's first object when adopting a skill.
- **Fixture**: small synthetic/public sample or a manifest pointing to data
  that is not committed. Used for examples, CI, and evidence — not required for
  every user invocation.
- **Benchmark manifest**: YAML under `benchmarks/` naming a dataset protocol
  and local-only case paths (no committed volumes).
- **Evidence pack**: one run's audit record under `runs/` or curated under
  `examples/`. Command, hashes, output, gate status, runtime/cost, environment,
  integrity scan, replay command. Not the skill itself.
- **Verifier**: skill-shaped auditor under `verifiers/` that audits a skill
  directory or an evidence pack. Same runnable contract as skills; specialized
  trust role, not a default publishable medtech capability.

## Validation layers

The eval_engine writes each gate result to `validation_summary.json`.

1. **Preflight**: fixture exists and basic format checks pass.
2. **Schema**: `output.json` matches the declared JSON schema.
3. **Sanity**: manifest-declared dotted-path checks over output values.
4. **Runtime envelope**: wall/runtime bounds from the manifest.
5. **Cost envelope**: optional wall, CPU, RSS, GPU, and token bounds.
6. **Env-pin**: installed dependency versions match declared PEP 440 ranges.
7. **Integrity scan**: static scan for off-spec or promotional content.
8. **Replay metadata**: `replay.sh`, runtime profile, and environment lock.
9. **LLM dispatch**: optional outer record for LLM-mediated runs.
10. **Drift comparison**: evidence-pack diff across environment, gates, and
    output payload.

Not yet solved: full artifact schemas, container-internal env capture,
side-effect enforcement, and adapters for agent frameworks.

## Trust surface

Readable deterministic files:

| File | Role |
|---|---|
| [`eval_engine/preflight.py`](eval_engine/preflight.py) | input boundary checks |
| [`eval_engine/gates.py`](eval_engine/gates.py) | schema-adjacent gates: sanity, runtime, cost, env, factual echo, model identity |
| [`eval_engine/integrity.py`](eval_engine/integrity.py) | static integrity scan |
| [`eval_engine/manifest.py`](eval_engine/manifest.py) | manifest loading, schema validation, spec discovery |
| [`verifiers/skill_completeness_v1/scripts/grade.py`](verifiers/skill_completeness_v1/scripts/grade.py) | structural and manifest verifier |
| [`verifiers/ct_segmentation_quality_v1/scripts/grade.py`](verifiers/ct_segmentation_quality_v1/scripts/grade.py) | domain verifier for CT-segmentation anatomy plausibility and optional Dice |
| [`verifiers/skill_completeness_v1/fixtures/negative_sloppy_skill/`](verifiers/skill_completeness_v1/fixtures/negative_sloppy_skill/) | known-bad calibration fixture |

`make verify` smoke-tests the harness against a canonical pack. `make verify-skills`,
and `make verify-negative-fixtures` are broader local trust checks.

## Entry points

CLI scripts under `eval_engine/` (orchestration only — not import targets):

- `eval_engine/run.py`: one skill or verifier, one fixture, one evidence pack.
- `eval_engine/run_llm_skill.py`: LLM dispatch plus nested `run.py` pack.
- `eval_engine/run_workflow.py`: simple multi-step workflow runner.
- `eval_engine/run_benchmark.py`: dataset loop and aggregate metrics.
- `eval_engine/diff_runs.py`: same-spec drift report.
- `eval_engine/compare_skills.py`: declared-spec comparison without ordering.
- `eval_engine/list_skills.py`: skill index generator (`SKILL_INDEX.md`).
- `eval_engine/lint_repo.py`: repo policy lint.

Shared harness logic lives in `common.py`, `manifest.py`, `gates.py`,
`preflight.py`, `integrity.py`, `evidence.py`, `skill_runtime.py`, and
`cost_capture.py`. Other eval_engine modules must import from those core
modules, not from `run.py`.

There is no stable package API or committed public CLI yet.

### Optional agent backends

[`tools/nat_audit/`](tools/nat_audit/) uses NeMo Agent Toolkit to profile agent
token cost and realistic tool-selection overhead. It is an optional maintainer
adapter, not skill runtime infrastructure. `run_llm_skill.py` remains the
minimal dependency-light LLM dispatch smoke test. Promote NAT integration into
eval_engine only when there is a framework-neutral agent-run record or adapter
interface worth stabilizing.

## Layering rules

- Skills and verifiers do not import from `eval_engine/`; the eval_engine invokes them
  by subprocess.
- Verifier-only shared helpers live under `verifiers/_shared/`, not
  `eval_engine/`.
- Generic gates live in `eval_engine/`.
- Tool-specific facts live in wrapper output and manifest gates.
- Second-pass domain checks live in `verifiers/`.
- Shared validators graduate only after two specs need the same logic.
- `tools/` utilities must not become implicit runtime dependencies of skills unless
  promoted and documented.

## Repository management

Top-level directories are part of the public shape:

| Directory | Committed? | Purpose |
|---|---|---|
| `skills/` | yes | publishable wrapper specs and small fixtures |
| `verifiers/` | yes | skill-shaped second-pass audit specs |
| `eval_engine/` | yes | generic runners, gates, lint, diff, index |
| `spec/` | yes | schemas and short spec prose |
| `examples/` | yes, curated | reference evidence packs, studies, tiny fixtures |
| `benchmarks/` | yes | shared benchmark manifests only |
| `tools/` | yes | maintainer utilities, profilers, adapter experiments |
| `runs/` | no | all local generated evidence packs and artifacts |

There is no top-level `outputs/`. Wrapper scratch output, model output, and
probe evidence all go under `runs/`. `make clean-runs` may delete that tree.

**`tools/` promotion rule:** move logic into `eval_engine/`, `spec/`, or `docs/`
only when it is generic, tested, documented, and not tied to a one-off
experiment. Skills must not depend on `tools/` at runtime unless explicitly
documented in the skill manifest and `SKILL.md`.

New top-level directories need an Architecture update that explains the stable
reader, writer, and promotion rule. Do not add a directory for one temporary
experiment; put it under `runs/`, `tools/`, or local `discussions/`.

## Consumers

Humans read `workflow_run_record.md` first in an evidence pack. CI and agents read
`validation_summary.json`, `manifest.json`, `output.json`,
`runtime_profile.json`, `cost_profile.json`, `integrity_check.json`,
`environment.lock`, `agent_run_trace.jsonl`, and `replay.sh`. Benchmark packs
add `dataset_run.jsonl`; LLM-mediated packs add `llm_interaction.json` and a
nested `skill_run/`.

For day-to-day skill use, humans and agents read `skills/<name>/SKILL.md` first.
