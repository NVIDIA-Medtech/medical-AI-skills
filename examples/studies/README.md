# Studies

Studies are curated multi-pack examples. They are useful for reading a workflow
or failure mode across several evidence packs, but they are not the canonical
single-run examples used by quickstart docs.

Current committed studies:

- `multi_llm_observatory/`
- `optimizer_loop_iteration_1/`
- `skill_completeness_audit_pre_fix/`
- `skill_completeness_audit_post_fix/`
- `subtle_defect/`

Generated with-vs-without LLM study records are not committed to git. They
default to `runs/with_vs_without_nv/studies/`, which is gitignored.

Commit durable result summaries under `docs/` and regenerate local study
records when a strict audit or rerun plan needs the raw per-repeat JSON.
