# Medical AI Skills Specs

The repo centers on specs, not a runtime framework. A skill or verifier
publishes `skill_manifest.yaml`; the eval_engine turns one run into an evidence
pack; optional verifiers consume packs for second-pass findings.

## Objects

| Object | Location | Role |
|---|---|---|
| Skill manifest | `skills/*/skill_manifest.yaml` | wrapper spec |
| Verifier manifest | `verifiers/*/skill_manifest.yaml` | audit spec |
| Output schema | `validators/output_schema.json` | JSON structure |
| Benchmark manifest | `benchmarks/*.benchmark.yaml` | dataset-loop protocol |
| Eval engine gates | `eval_engine/` | generic checks |
| Evidence pack | `runs/*`, `examples/evidence_packs/*`, or `examples/studies/*` | run audit record |

## Pattern

- Put JSON shape in schema.
- Put direct output facts in manifest sanity gates.
- Put runtime, cost, env, identity, and factual echo in eval_engine gates.
- Put repeatability expectations in `validation.reproducibility`; runnable
  fixtures use `mode: repeat`, external-runtime gaps use `mode: preflight`
  with a reason.
- Put second-pass domain checks in verifiers.
- Put known missing checks in `limitations`.

## Compatibility

The MVP spec is additive. Add fields and gates freely when documented.
Renaming or removing eval_engine-read manifest fields or evidence-pack filenames
needs a migration plan.

Current manifest grammar: `spec/skill_manifest.schema.json`.
Current benchmark grammar: `spec/benchmark_dataset.schema.json`.
Current evidence-pack contract: `spec/evidence_pack.schema.json` (directory
descriptor) plus per-file schemas under `spec/evidence_pack/`. Pack format
version is `1.0.0`; the source of truth is
`eval_engine.common.PACK_FORMAT_VERSION`. Validate a pack with
`make validate-pack PACK=<dir>`.

### `gate_operators.schema.json`

Defines the sanity-check operator shape. The same operators are inlined under
`$defs/sanity_check` in `skill_manifest.schema.json`. The eval_engine enforces
operators via `eval_engine/gates.py`, not by loading this file. Treat
`gate_operators.schema.json` as a **documentation extract** until a future schema
refactor `$ref`s it from `sanity_check` (avoids two diverging grammars).
