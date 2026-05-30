# Evidence Pack Spec

An evidence pack is the audit record of one eval_engine run. It is not a clinical
artifact and not a replacement for upstream logs.

Stable filenames are documented in [`docs/replay.md`](../docs/replay.md) and
protected by root agent instructions. Do not rename them casually.

Core files:

- `manifest.json`
- `output.json`
- `validation_summary.json`
- `runtime_profile.json`
- `cost_profile.json`
- `integrity_check.json`
- `environment.lock`
- `agent_run_trace.jsonl`
- `replay.sh`
- `workflow_run_record.md`

Benchmark packs add `dataset_run.jsonl`. LLM-mediated packs add
`llm_interaction.json` and usually a nested `skill_run/`.
Trusted-run directories add a top-level `trust_summary.json` that links the
nested skill and verifier packs. Trust summary format `1.1.0` is additive over
`1.0.0`: it keeps `verifiers[]`, `gaps[]`, and `overall`, then adds
`evidence_packs[]` hashes, `implemented_verifiers[]`,
`planned_verifier_gaps[]`, `env_skipped_verifier_gaps[]`, and
`warning_findings[]`.

`agent_run_trace.jsonl` is line-oriented: each line is one JSON object. New
records carry canonical `event_type` and `timestamp` fields while still keeping
legacy aliases such as `kind`, `ts`, `args`, and `elapsed_s` for older review
tools. Current skill, preflight, and LLM-dispatch tool-call start records also
include public `command` and `cwd` fields so reviewers can bind a trace event to
the sanitized command that ran. `validate-pack --allow-legacy` normalizes
historical alias-only trace records before validating them.

## Machine contract

The pack-level contract lives in [`evidence_pack.schema.json`](evidence_pack.schema.json)
(directory descriptor) and per-file JSON Schemas under
[`evidence_pack/`](evidence_pack/). Every pack written by current `eval_engine`
runners carries `pack_format_version` in `manifest.json` (also stamped with
`pack_kind` for skill_run / benchmark_run / llm_skill_run). Verifiers and
downstream readers consume `pack_format_version` to decide which fields they
trust.

Validate a pack against the contract:

```bash
make validate-pack PACK=runs/my_pack
make validate-pack PACK=examples/evidence_packs/older_pack VALIDATE_PACK_ARGS='--allow-legacy'
```

The current pack format is `1.0.0`. Pre-1.0 packs without `pack_format_version`
exist in `examples/` for historical reference and validate only under
`--allow-legacy`. See [`versioning_policy.md`](versioning_policy.md) for what
warrants a version bump.
