# Skill vs README Current Results Analysis

Last refreshed: May 26, 2026.

This report tracks the current audited state of the NV model
with-vs-without study. The last completed direct-API aggregate covered seven
skills. The registry now includes two additional finetuning scenarios whose
prompt artifacts are complete, but whose direct API repeat artifacts are still
pending.

This is an engineering reproducibility analysis. It is not a clinical,
diagnostic, regulatory, or model-quality claim.

## Current Status

Primary status comes from
[`docs/with-vs-without-skill-experiment.md`](with-vs-without-skill-experiment.md)
and `python tools/with_vs_without/audit_nv_model_studies.py --format markdown`.

| Check | Current value |
|---|---:|
| Prompt artifacts complete | 9/9 |
| Study artifacts complete | 6/9 |
| Complete paired outcomes | 6/9 |
| Outcomes supporting SKILL.md paired advantage | 6/9 |
| Strict audit issues | 70 |
| Pending direct-study skills | 3 |

The strict proof gate is intentionally not cited while prompt-only scenarios
and stale direct-repeat artifacts remain:

```bash
make audit-with-vs-without
make plan-with-vs-without
```

## Current Interpretation

The completed direct-API evidence supports SKILL.md paired advantage for the
skills whose study artifacts are still current:

| Skill | Status |
|---|---|
| `nv_generate_ct_rflow` | Prompt artifact complete; direct repeats need refresh in the current local audit |
| `nv_generate_mr` | Complete; supports SKILL.md paired advantage |
| `nv_generate_mr_brain` | Complete; supports SKILL.md paired advantage |
| `nv_generate_mr_brain_finetune` | Prompt artifact complete; direct API repeats pending |
| `nv_generate_vae_finetune` | Prompt artifact complete; direct API repeats pending |
| `nv_reason_cxr` | Complete; supports SKILL.md paired advantage |
| `nv_segment_ct` | Complete; supports SKILL.md paired advantage |
| `nv_segment_ct_finetune` | Complete; supports SKILL.md paired advantage |
| `nv_segment_ctmr` | Complete; supports SKILL.md paired advantage |

Across the historical completed direct-API study, the with-skill arm passed 62/63
repeats, while the README-only arm passed 0/63 repeats. In matched
backend-repeat pairs, SKILL.md won 62 times, README-only won once, and no pairs
tied because both arms failed. The one-sided paired sign test over decisive
pairs gives `p = 6.939e-18`.

## Scope

Supported by the last completed seven-skill aggregate, pending refresh of the
current nine-scenario registry:

> Across the seven covered NV model skills and the current direct-API protocol,
> SKILL.md is a stronger LLM operating contract than the selected upstream
> README/model-guide baseline.

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
