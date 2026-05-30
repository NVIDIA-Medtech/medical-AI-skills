# Agent task contract

Machine-oriented map: **for this task, read these files and run these commands**.
Humans observe evidence packs and policy docs; agents implement and maintain the
catalog and harness.

**Status:** MVP scaffolding. Prefer `make` targets over ad-hoc `python eval_engine/…`
unless you are debugging the harness itself.

## First orientation (any task)

| Step | Read / run |
|---|---|
| 1 | [`AGENTS.md`](../AGENTS.md) — purpose, boundaries, do-not list |
| 2 | [`ARCHITECTURE.md`](../ARCHITECTURE.md) — objects and layering |
| 3 | [`SKILL_INDEX.md`](../SKILL_INDEX.md) or `make list-skills` |
| 4 | This file for the matching task row below |

Core flow (canonical diagram — do not duplicate elsewhere):

```text
skill + user input             -> useful local result
skill + manifest + fixture     -> evidence pack
evidence pack + verifier       -> verifier evidence pack
```

## Task matrix

| Task | Read first | Then | Preferred command |
|---|---|---|---|
| **Discover a skill** | `SKILL_INDEX.md` | `skills/<name>/SKILL.md`, `skill_manifest.yaml` | `make list-skills` |
| **Inspect a contract** | `python tools/render_contract_summary.py skills/<name>` | `SKILL.md`, `skill_manifest.yaml` | `python tools/render_contract_summary.py skills/<name>` |
| **Run a skill (user data)** | `skills/<name>/SKILL.md` | `runtime.side_effects`, `limitations` | Script in `SKILL.md` (not eval_engine) |
| **Generate evidence pack** | `docs/trust-and-evidence.md` | Target manifest `validation.*` | `make run-skill SKILL=<name> FIXTURE=<path> OUT=runs/<id>` |
| **Inspect a pack** | `docs/trust-and-evidence.md` | `workflow_run_record.md`, `validation_summary.json`, `output.json`, `trust_summary.json` if present | `make review-packet PACK=<pack>` |
| **Compare runs** | `docs/replay.md` | Both pack dirs | `make diff RUN_A=… RUN_B=…` |
| **Add a skill** | `docs/authoring-skills.md`, `skills/dicom-metadata-extract/` | `docs/skill-scope.md` | `make verify-skills` after authoring |
| **Add a verifier** | `CONTRIBUTING.md` § Verifier | `verifiers/skill_completeness_v1/` | `make run-skill` with verifier path |
| **Audit one skill** | `verifiers/skill_completeness_v1/SKILL.md` | Target `skills/<name>/` | `make audit-skill SKILL=<name>` |
| **Release readiness** | `docs/release-readiness.md` | `runs/skill_audit/_summary.json`, candidate evidence packs | `make status-agent-skills` then `make review-packet PACK=<pack>` |
| **Add with-vs-without comparison** | `docs/with-vs-without-authoring.md` | `tools/with_vs_without/run_nv_model_studies.py`, target `SKILL.md`, upstream README/model card | `python tools/with_vs_without/run_nv_model_studies.py --skills <name> --mode prompts --prompt-style path` |
| **Change a gate / harness** | `eval_engine/AGENTS.md`, `docs/spec-model.md` | `spec/skill_manifest.schema.json` | `make lint` then `make verify-skills` and `make verify` |
| **Change manifest schema** | `spec/README.md` | `docs/spec-model.md` | `make lint` |
| **Promote an example pack** | `examples/README.md` | `examples/INDEX.md` | `make diff` against prior anchor |
| **Repo hygiene** | Lint output | `make lint` | `make lint` |

## Where to put changes

| Change | Location |
|---|---|
| User-facing wrapper | `skills/<name>/` |
| Second-pass audit | `verifiers/<name>/` |
| Generic gate or pack writer | `eval_engine/` |
| Schema / spec prose | `spec/` (+ `docs/spec-model.md`) |
| Curated proof | `examples/` |
| Maintainer experiment | `tools/` |
| Generated output | `runs/` (gitignored) |

**Never:** import `eval_engine/` from `skills/` or `verifiers/`.

## Verification ladder (after edits)

```bash
make lint                    # policy + manifest schema
make test                    # pytest (eval_engine + skills + verifiers)
make verify-skills           # structural audit + reproducibility audit
make verify                  # harness smoke + canonical pack diff
```

Optional when touching gates:

```bash
make verify-negative-fixtures
```

## Safety defaults

- Refuse clinical decision support, patient-facing advice, or regulatory claims.
- Do not commit patient data, large volumes, weights, or secrets.
- When unsure, choose the reversible option and document any gap under
  the relevant manifest's `limitations`.
