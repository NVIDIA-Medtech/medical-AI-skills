# Spec Model

The canonical machine-readable spec index is [`../spec/README.md`](../spec/README.md).
This page is only the placement guide for deciding where a check belongs.

## Surfaces

| Surface | Location | Role |
|---|---|---|
| Spec files | `spec/` | machine-readable and narrative spec grammar |
| Skill manifest | `skills/<name>/skill_manifest.yaml` | Published wrapper spec |
| Verifier manifest | `verifiers/<name>/skill_manifest.yaml` | Published audit spec |
| Human guide | `SKILL.md` | How to invoke and what not to claim |
| Wrapper code | `scripts/` | Calls upstream tool and emits JSON facts |
| Output schema | `validators/output_schema.json` | Structural output spec |
| Eval engine gates | `eval_engine/` | Generic validation and evidence-pack writing |
| Benchmark manifest | `benchmarks/` | dataset-loop protocol without committed data |
| Evidence pack | `runs/`, `examples/evidence_packs/`, or `examples/studies/` | Audit record of one run |
| Contract summary | `tools/render_contract_summary.py` output, usually under `runs/` | Generated read-only view over a skill/verifier contract before execution; not a source of truth |
| Review packet | `tools/render_review_packet.py` output, usually under `runs/` | Generated human review view over existing pack files; not a source of truth |
| Trace inventory | `tools/inventory_trace_shapes.py` output, usually under `runs/` | Generated compatibility report for current `agent_run_trace.jsonl` records before schema work |
| Capability lifecycle | `verifiers/skill_completeness_v1` output | Derived status (`draft` -> `runnable` -> `gated` -> `verified` -> `published`) for review; not a manifest field |

## Enforcement map

| Manifest field | Enforced by |
|---|---|
| top-level grammar | `spec/skill_manifest.schema.json`, `eval_engine/lint_repo.py` |
| `runtime.entrypoint` | `eval_engine/skill_runtime.py`, `eval_engine/run.py` |
| `runtime.args` | `eval_engine/skill_runtime.py:render_runtime_args` |
| `inputs[]` | `eval_engine/preflight.py` |
| `outputs[].schema` | `eval_engine/run.py` and `jsonschema` |
| `validation.sanity_checks` | `eval_engine/gates.py` |
| `validation.expected_runtime_seconds` | `eval_engine/run.py` |
| `validation.expected_cost` | `eval_engine/cost_capture.py`, `eval_engine/gates.py` |
| `validation.env_pin` | `eval_engine/gates.py` |
| `validation.factual_echo` | `eval_engine/gates.py` |
| `runtime.llm` | `eval_engine/gates.py` |
| `validation.runtime_integrity` | `eval_engine/gates.py` |
| `validation.reproducibility` | `eval_engine/reproducibility.py`, `make verify-skills` |
| `runtime.side_effects` | declared and audited; full measurement is tech debt |
| `runtime.side_effects.environment` | declared policy for caller environment mutation; audited in reviews |
| `paired_verifiers[]` | `verifiers/skill_completeness_v1` |
| `cost` (advisory) | documented only; measured via `tools/nat_audit/` |
| `transport` | packaging hint only; not enforced by eval_engine |

## Placement rule

Use the narrowest layer that can verify the claim honestly.

| Claim | Put it in |
|---|---|
| Output shape | JSON schema |
| Direct output fact | manifest sanity gate |
| Cheap artifact fact the wrapper already knows | wrapper output plus manifest gate |
| Runtime/cost/env drift | eval_engine gate |
| Cross-artifact or domain-quality assessment | verifier |
| Known missing check | `limitations` |
| Pre-run contract compression | contract summary generated from `SKILL.md` and `skill_manifest.yaml` |
| Human review compression | review packet generated from an evidence pack |
| Trace-schema discovery | trace inventory generated from existing evidence packs |
| Publication readiness summary | derived lifecycle in `skill_completeness_v1` output |

## Capability lifecycle

Lifecycle status is derived, not stored. `skill_completeness_v1` reports:

```text
draft -> runnable -> gated -> verified -> published
```

- `runnable`: structural requirements pass.
- `gated`: runnable plus blocking manifest/gate/reproducibility checks pass.
- `verified` for user-facing capabilities: gated plus implemented paired
  verifiers resolve and curated trusted-run evidence shows verifier coverage
  passed or warned without gaps.
- `verified` for verifiers: gated plus a curated verifier evidence pack for the
  verifier's own manifest id passes validation. Verifiers are independent
  auditors and do not need their own `paired_verifiers[]`.
- `published` for user-facing capabilities: verified plus behavior evals, a
  benchmark note, and curated example evidence exist.
- `published` for verifiers: verified plus curated example evidence exists.

The lifecycle is a review shortcut, not an additional manifest grammar or a
replacement for evidence packs. If a user-facing capability says `gated`,
reviewers should look first for paired-verifier gaps. If a verifier says
`gated`, reviewers should look first for missing curated passing verifier
evidence. If either says `verified`, inspect the referenced evidence before
treating it as publication-ready.

## Dependency drift policy

Use `upstream_refs` for source provenance: the external package version
constraint, hosted model id, model-repo revision, or git commit that defines
the skill's upstream behavior. Every publishable skill under `skills/` must
have at least one entry.

Use `validation.env_pin` for direct upstream dependencies whose versions affect
the skill's behavioral contract: model bundles, inference frameworks, and
medical file-format libraries. Do not use it as a full lockfile or pin every
transitive dependency. LLM model identity belongs in `runtime.llm` and the
model-identity / factual-echo gates, not package pins.

## Reproducibility policy

Every skill and verifier declares `validation.reproducibility`. Use
`mode: repeat` when the committed fixture can run locally through
`eval_engine/run.py`; the audit writes two evidence packs, compares gate
statuses and semantic output, and hashes emitted artifact paths. Use
`mode: preflight` only when an external runtime, model weights, GPU, container,
or deliberately test-synthesized binary fixture prevents honest repository-local
execution. Preflight mode must include a reason so reviewers can distinguish a
known boundary check from an end-to-end repeat.

If the declared fixture is an intentionally gitignored binary artifact, add a
repo-local `fixture_builder` script under `validation.reproducibility`. The
reproducibility audit runs that script before checking the fixture path; the
completeness verifier requires the builder to stay inside the skill or verifier
directory.

Verifiers are not trusted by name. They need manifests, schemas, positive and
negative fixtures, tests, and their own evidence packs.

## Segmentation output schema

**Canonical file:** `spec/segmentation_output.schema.json` (JSON Schema draft-07, `$id` version `v1.0.0`).

### Envelope rationale

The shared segmentation schema captures the stable envelope used by
`nv_segment_ct`-style segmentation wrappers: `invocation`, `output`, and
`runtime` are required objects, while skill-specific detail stays in each
skill-local validator.

### Required and optional fields

| Field | Status |
|---|---|
| `invocation` | required object |
| `output` | required object |
| `runtime` | required object |
| `skill`, `model`, `model_repo`, `license`, `input`, `intended_use_disclaimer`, `logs` | optional skill-specific fields |

The shared schema requires only the common envelope. Optional fields are
declared with `additionalProperties: true` so each skill can carry its full
payload without conflict.

### Migration strategy

The `eval_engine` (`eval_engine/run.py`, `_schema_status`) resolves a skill's output schema by reading the file at `skill_dir/validators/output_schema.json` and passing it directly to `jsonschema.validate()` without registering a custom `RefResolver`. Out-of-tree `$ref` paths therefore do not resolve at validation time. A `$ref` or `allOf` pointing to `spec/segmentation_output.schema.json` from a skill-local validator would silently be ignored or raise a `RefResolutionError`.

Because of this constraint, the migration uses the **inline-copy with comment** strategy: each skill-local validator retains its existing required-field list (which is a strict superset of the intersection), and a `$comment` field is added pointing to `spec/segmentation_output.schema.json` as the canonical reference. Both skills' existing required fields already satisfy the shared schema's requirements, so no functional schema change is needed — only the comment anchors the two local validators to the shared spec.

| Skill | Validator path | Strategy |
|---|---|---|
| `nv_segment_ct` | `skills/nv-segment-ct/validators/output_schema.json` | `$comment` added; required block unchanged (superset of envelope) |

The paired verifier `ct_segmentation_quality_v1` references the same envelope
when it accesses `output_payload.get("output")` and
`output_payload.get("invocation")`.

### Future upgrade path

If the `eval_engine` is extended to register a file-system `RefResolver` (e.g. via `jsonschema.RefResolver.from_schema` with a `handlers` mapping for `file://` URIs), the `$comment` blocks can be replaced with:

```json
"allOf": [{"$ref": "../../spec/segmentation_output.schema.json"}]
```

At that point the inline-copy convention becomes redundant and can be removed. The canonical spec file is already in place to support this upgrade without any further schema authoring.

## Benchmark result schema

**Canonical file:** `spec/benchmark_result.schema.json` (JSON Schema 2020-12, `$id` version `v1.0.0`).

The benchmark **input** manifest is already governed by `spec/benchmark_dataset.schema.json`; the benchmark **output** (the aggregate `output.json` written by `eval_engine/run_benchmark.py` inside a `pack_kind: benchmark_run` pack) was previously schema-less. As of 2026-05-17 the output shape is canonicalised here so that the cross-skill matrix renderer (`eval_engine/render_baselines.py`) and downstream comparison tooling can rely on a stable contract.

| Required top-level key | Source |
|---|---|
| `skill` | Identity of the skill that produced the run (`id`, `version`, `entrypoint`). |
| `benchmark` | Identity of the benchmark the skill ran (`manifest_path`, `source`, `dataset`, `license`, `case_count_*`). |
| `output` | Aggregate metrics: `case_count`, `pass_count`, `fail_count`, `coverage_pct`, plus `dice`, `iou`, `hd` summary blocks. |

Each metric summary (`dice`, `iou`, `hd`) is a fixed `{count, mean, median, p10, min, max}` block, all numeric fields nullable to handle the "no cases produced this metric" path that `run_benchmark.py` already supports.

### Relation to the cross-skill matrix

`eval_engine/render_baselines.py` reads the `axes:` declaration of each `benchmark.yaml` and uses dotted field paths into this schema (e.g. `output.dice.mean`) to pull scalars per skill. The schema therefore frames the contract between the benchmark **input** (`axes` block) and the rendered comparison table; if a benchmark introduces a new axis (e.g. `output.calibration.ece`) it must extend the result schema correspondingly.

### Why this is not a pack-format bump

The benchmark result schema is a sibling spec to `spec/evidence_pack.schema.json`. The pack-level contract (`pack_format_version` in `eval_engine.common`) is unchanged — only the aggregate `output.json` shape inside benchmark packs is now formally specified. Existing benchmark packs validate against the new schema because `run_benchmark.py` was already emitting the same shape; only the absence of a written schema was the gap.
