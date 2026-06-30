# Benchmark — nv-curate

Engineering behavior benchmark for the nv-curate orchestrator. Integration/quality
signal, not a clinical or regulatory claim.

## Task

Drive the MR-RATE report-curation pipeline (de-identify -> translate -> structure ->
label) from a `datasources.json` plan into an AI-ready dataset, and hand off to a
training or analysis task. Three actions map to the three end-user prompts (plan,
curate, finetune).

## Modes

| Mode | Stages run as | GPU | Determinism | Use |
|---|---|---|---|---|
| `mock` (default) | each stage skill's stdlib mock | none | deterministic | CI gates, fixtures, offline verification |
| `live` | each stage skill's upstream vLLM path | CUDA | model-dependent | real curation |

## With-skill vs without-skill

- **Without the skill**, an agent asked to "curate this data and fine-tune" must
  hand-wire four scripts, guess the column hand-offs, invent a datasources schema,
  and has no per-stage evidence or a defined finetune hand-off.
- **With the skill**, one entrypoint maps the three prompts to actions, pins the
  stage column hand-offs, runs each stage as an independently-gated skill, assembles
  a `study_uid`-joined datalist, and reports a concrete finetune hand-off (or an
  honest not-ready reason when no image volumes are present).

## Results

### Mock curate (synthetic datasources fixture, 3 studies)

_Populated from `runs/nv_curate_pack` (`python -m eval_engine.run`)._

| Metric | Value |
|---|---|
| pipeline_status | complete |
| stages completed | 4 (anonymize, translate, structure, classify) |
| n_studies / ai_ready.n_records | 3 |
| ai_ready.has_labels | true |
| ai_ready.has_images | false (text-only fixture) |
| task.ready (analysis) | true |
| eval_engine overall | passed |

### Finetune hand-off (prompt 3)

- With the text-only fixture, `--action finetune` reports `finetune_handoff.ready =
  false` with reason "datalist has no image volumes" and emits the analysis dataset.
  This is the correct behavior — the diffusion finetune consumes images joined by
  `study_uid`; the report track supplies labels/metadata and cohort selection.

### Live run (real MR-RATE Turkish reports)

_Populated from a `--mode live` run on a real-data slice (recorded in gitignored
`runs/`): per-stage real metrics (PHI leak, translation QC, structure QC, label
coverage), model id, GPU, and wall time._

## Gaps

- Mock stages are deterministic stand-ins, not the LLM-quality transforms.
- Image-track join is name/`study_uid`-convention based; real PACS-derived volumes
  may need an explicit study_uid->path map.
