# Skill vs README Current Results Analysis

Last refreshed: May 29, 2026.

This report tracks the current audited state of the NV model
with-vs-without study. The registry covers nine skills, and the current saved
artifacts pass the strict audit for all nine skills.

This is an engineering reproducibility analysis. It is not a clinical,
diagnostic, regulatory, or model-quality claim.

## Current Status

Primary status comes from
[`docs/with-vs-without-skill-experiment.md`](with-vs-without-skill-experiment.md)
and `python tools/with_vs_without/audit_nv_model_studies.py --strict --require-skill-advantage --format markdown`.

| Check | Current value |
|---|---:|
| Prompt artifacts complete | 9/9 |
| Study artifacts complete | 9/9 |
| Complete paired outcomes | 9/9 |
| Outcomes supporting SKILL.md paired advantage | 9/9 |
| Strict audit issues | 0 |
| Pending direct-study refresh skills | 0 |

The full strict proof gate is clean:

```bash
make audit-with-vs-without
make prove-with-vs-without
```

## Current Interpretation

The current direct-API evidence supports SKILL.md paired advantage for all
nine covered NV model skills. The Codex/Opus study is fully passing for the
with-skill arm, and the Nemotron baseline also supports the skill-advantage
gate for every skill despite a small number of with-skill command-format
failures.

| Skill | Status |
|---|---|
| `nv_generate_ct_rflow` | Complete; supports SKILL.md paired advantage |
| `nv_generate_mr` | Complete; supports SKILL.md paired advantage |
| `nv_generate_mr_brain` | Complete; supports SKILL.md paired advantage |
| `nv_generate_mr_brain_finetune` | Complete; supports SKILL.md paired advantage |
| `nv_generate_vae_finetune` | Complete; supports SKILL.md paired advantage |
| `nv_reason_cxr` | Complete; supports SKILL.md paired advantage |
| `nv_segment_ct` | Complete; supports SKILL.md paired advantage |
| `nv_segment_ct_finetune` | Complete; supports SKILL.md paired advantage |
| `nv_segment_ctmr` | Complete; supports SKILL.md paired advantage |

Across all nine skills and three LLM backends, the with-skill arm passed
78/81 repeats, while the README-only arm passed 0/81 repeats. In matched
backend-repeat pairs, SKILL.md won 78 times, README-only won 1 time, and 2
pairs tied because both arms failed. The one-sided paired sign test over the
79 decisive pairs gives `p = 1.323e-22`.

The stronger Codex/Opus backends show a fully clean with-skill pass rate:
54/54 with-skill repeats passed and 0/54 README-only repeats passed. Nemotron
is more fragile around strict command formatting, but still shows aggregate
skill advantage: 24/27 with-skill repeats passed and 0/27 README-only repeats
passed.

## Scope

Supported by the current refreshed artifacts:

> For all nine covered NV model skills, SKILL.md is a stronger LLM operating
> contract than the selected upstream README/model-guide baseline under the
> current direct-API protocol.

Still not claimed:

> SKILL.md beats every possible improved README or benchmark-specific upstream
> adapter.

That stronger documentation-quality question requires a separate
`README+adapter` arm.

## Future README+Adapter Arm

The stronger README-quality question still requires a third arm:

| Arm | Purpose |
|---|---|
| `README` | Raw upstream README/model-guide baseline. Keep this unchanged. |
| `README+adapter` | Upstream docs plus neutral benchmark context such as staged input path, output directory, fresh venv assumption, no upstream mutation, no unsafe cleanup, and expected artifact type. |
| `SKILL.md` | Current purpose-built skill contract. |

Keep pass/fail as the primary outcome, use three repeats per backend/arm, and
do not let the adapter call hidden skill wrappers or read `skills/<name>/`.
