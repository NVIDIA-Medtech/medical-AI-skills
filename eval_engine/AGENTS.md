# eval_engine/ - Agent Guide

Support harness for trust and evidence — not the primary user path for skills.
MVP evidence-pack scaffolding, not a public CLI. It reads manifests, invokes
skills/verifiers by subprocess, applies gates, and writes packs. Users normally
run `skills/<name>/scripts/` directly; use `eval_engine/run.py` when you need a
pack.

## CLI entrypoints (orchestration only)

These Typer scripts wire flows together. **Do not import from them** except
when spawning subprocesses (for example `run_workflow.py` calling `run.py`).

| File | Role |
|---|---|
| `run.py` | one spec + fixture → evidence pack |
| `run_llm_skill.py` | LLM dispatch smoke test → nested `skill_run/` pack |
| `run_benchmark.py` | benchmark dataset loop → benchmark pack |
| `run_workflow.py` | multi-step workflow → workflow pack; `trusted: true` on a step calls `run_trusted` |
| `diff_runs.py` | same-spec drift report |
| `compare_skills.py` | declared-shape comparison (no performance ordering) |
| `list_skills.py` | generates `SKILL_INDEX.md` |
| `lint_repo.py` | structural and policy lint |

## Core modules (shared library)

Import shared behavior from these modules, not from `run.py`:

| Module | Role |
|---|---|
| `common.py` | hashes, timestamps, env lock, replay helpers, `REPO_ROOT`, `FENCE` |
| `manifest.py` | `load_manifest`, spec discovery, schema validation |
| `skill_runtime.py` | resolve entrypoint, load skill for subprocess |
| `preflight.py` | input and environment boundary checks |
| `gates.py` | sanity, env pin, factual echo, model identity, path resolution |
| `gate_registry.py` | gate category taxonomy |
| `cost_capture.py` | wall/CPU/RSS/GPU capture and cost envelope |
| `integrity.py` | static integrity scan |
| `evidence.py` | evidence-pack writers |

## Rules

- Do not import from `skills/` or `verifiers/`.
- **Do not import from `run.py`** in other eval_engine modules (use core modules).
- Keep skill-specific behavior declarative in `skill_manifest.yaml`.
- Every gate needs a status in `validation_summary.json`.
- Evidence-pack filenames are spec anchors; do not rename them.
- Additive files are fine when documented in `docs/replay.md`.

## Agent backends (NAT)

NeMo Agent Toolkit workflows under `tools/nat_audit/` are optional **agent-backend
profilers**, not core eval_engine infrastructure. `run_llm_skill.py` is the
dependency-light LLM dispatch contract test. NAT may later call `run.py` or emit
comparable nested evidence; promote only after a framework-neutral adapter exists.

## Extend

Add gates as manifest-declared options or baseline safety checks. Keep Typer
style for CLI surfaces. Regenerate the index with `make list-skills` after
changing spec discovery.
