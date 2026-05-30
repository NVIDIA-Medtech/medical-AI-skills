# With-vs-Without Skill Experiment Docs

Last refreshed: May 29, 2026.
Audit status: strict audit passed for refreshed artifacts on May 29, 2026.

This checked-in aggregate summarizes the corrected with-vs-without protocol. Detailed per-skill generated reports are reproducible local artifacts under `runs/with_vs_without_nv/reports/` rather than committed records:

1. A **Codex/Opus backend comparison**: same task on GPT-5.5/Codex and Opus-class backends, using the no-repair baseline protocol.
2. A **Nemotron baseline study**: same task on `nvidia/nvidia/nemotron-3-super-v3`, also using `max_correction_steps=0`.

Every backend/skill/arm configuration is repeated three times. Each repeat gets a separate output directory; every execution attempt inside a repeat uses a newly created venv with `PYTHONNOUSERSITE=1` and without inherited `PYTHONPATH`. Dependency and model download caches are shared only as documented test-environment caches under `.workbench_data/with_vs_without_cache` (`PIP_CACHE_DIR=.workbench_data/with_vs_without_cache/pip`, `HF_HOME=.workbench_data/with_vs_without_cache/huggingface`, `HF_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `HUGGINGFACE_HUB_CACHE=.workbench_data/with_vs_without_cache/huggingface/hub`, `TRANSFORMERS_CACHE=.workbench_data/with_vs_without_cache/huggingface/transformers`, `TORCH_HOME=.workbench_data/with_vs_without_cache/torch`, `XDG_CACHE_HOME=.workbench_data/with_vs_without_cache/xdg`, `CONDA_PKGS_DIRS=.workbench_data/with_vs_without_cache/conda_pkgs`, `UV_CACHE_DIR=.workbench_data/with_vs_without_cache/uv`, `CUDA_CACHE_PATH=.workbench_data/with_vs_without_cache/cuda`, `NUMBA_CACHE_DIR=.workbench_data/with_vs_without_cache/numba`).

The main protocol is deliberately **no-repair**:

```text
DIRECT_MAX_CORRECTION_STEPS = 0
```

The experiment measures whether the backend can produce a valid first-shot command from the arm-specific documentation. Generic correction/autofix is not part of the main claim because it changes the question from "does SKILL.md improve task completion?" to "does a repair loop improve failed commands?" Any run with `max_correction_steps > 0` is diagnostic-only and should not be mixed into the aggregate results below. The `nemotron-correction` directory suffix is a historical artifact name; the approved baseline artifacts in that directory still use `max_correction_steps=0`.

This is an engineering reproducibility protocol. It tests whether an agent can read documentation and take the right action. It is not a clinical, diagnostic, regulatory, or model-quality claim.

The corrected experiment is **LLM + SKILL.md vs LLM + upstream README/guide**. The fair NAT/tool-agent prompts give only a natural user request, a neutral staged input path, an output directory, and the path of the arm-specific document to read. They do not embed the documentation and do not give label IDs, config names, entrypoint names, model variants, or backend implementation details outside the documentation arm.

The completed direct-API runs used an embedded-doc minimal prompt only because those chat backends had no file-reading tools. The study JSONs preserve those exact direct-API messages; the `tools/nat_audit/data` artifacts are the fair A2-style path prompts for future NAT/tool-agent comparisons.

The direct-API backend protocol is service-default by design: each LLM request sends only `model` and `messages`. It omits sampling fields, token caps, backend-specific reasoning controls, and extra request body fields. Retry attempts and socket timeouts are client transport settings, not model behavior settings.

## Current Aggregate Result

- Codex/Opus with-skill repeats: 54/54 passed.
- Codex/Opus README-only repeats: 0/54 passed.
- Nemotron with-skill repeats: 24/27 passed.
- Nemotron README-only repeats: 0/27 passed.
- Codex/Opus outcome-support gates: 9/9 skill reports support SKILL.md paired advantage.
- Nemotron outcome-support gates: 9/9 skill reports support SKILL.md paired advantage.

Every Codex/Opus with-skill repeat exits successfully and passes the deterministic grader. Nemotron baseline with-skill repeats are mixed at 24/27; unresolved repeats are listed in the per-skill reports.

Artifact completeness alone does not establish the skill-advantage claim. Treat the aggregate as supporting that claim only when every expected per-skill/backend outcome-support gate reports a SKILL.md paired advantage.

## Token Profiling

The table below aggregates provider-reported usage across all 9 skills for each backend/arm. It is useful for separating workflow success from prompting cost: README-only arms often spent more output tokens explaining or improvising commands while still failing the artifact contract.

| Backend | Arm | Repeats | Passes | Attempts | Prompt tokens | Completion tokens | Reasoning tokens | Total tokens | Mean total/repeat | Executed | Mean exec s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GPT-5.5 / Codex | with | 27 | 27 | 27 | 69,759 | 10,808 | 7,262 | 80,567 | 2,984.0 | 27 | 43.5 |
| GPT-5.5 / Codex | without | 27 | 0 | 27 | 71,478 | 134,131 | 99,786 | 205,609 | 7,615.1 | 13 | 1.0 |
| Nemotron | with | 27 | 24 | 27 | 73,254 | 34,840 | 0 | 108,094 | 4,003.5 | 24 | 54.9 |
| Nemotron | without | 27 | 0 | 27 | 76,077 | 185,021 | 0 | 261,098 | 9,670.3 | 2 | 0.0 |
| Opus 4.7 | with | 27 | 27 | 27 | 119,073 | 6,100 | 0 | 125,173 | 4,636.0 | 27 | 49.1 |
| Opus 4.7 | without | 27 | 0 | 27 | 112,254 | 24,014 | 0 | 136,268 | 5,047.0 | 15 | 0.4 |

Reasoning tokens are included in completion tokens where reported. Mean execution seconds excludes repeats that never reached command execution, but those repeats still contributed prompt and completion tokens.

## Nemotron Diagnostic Layer

Nemotron is reported with the same main no-repair outcome gate as the other backends. The additional layer below isolates backend protocol behavior: strict fenced-block compliance, deterministic recoverability of malformed command text, and repeated failure buckets.

| Arm | Repeats | Passed strict | Strict command | Recoverable malformed command | Unrecoverable formatting | Guard-ready after tolerant extraction | Static guard blocked | Format categories | Guard reasons |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| with | 27 | 24 | 24 | 3 | 0 | 3 | 0 | strict 22; language_prefix 2; raw_shell 3 | none |
| without | 27 | 0 | 12 | 14 | 1 | 2 | 12 | strict 12; raw_shell 13; malformed_fence 1; no_shell 1 | command does not reference the neutral staged input path (10); command does not reference an expected runnable surface (1); without-skill command references forbidden Medical AI Skills skill marker (1) |

Protocol-compliance failure buckets, counted per repeat and not mutually exclusive:

| Bucket | Count |
|---|---:|
| No strict command extracted | 18 |
| Wrong or missing runnable surface | 22 |
| Missing staged input path | 23 |
| Missing model/modality/control marker | 19 |
| Missing output directory | 18 |
| Unsafe/static guard block | 10 |
| Nonzero execution exit | 2 |
| Artifact contract failure after execution | 0 |

## Overall Findings

The current evidence strongly favors `LLM + SKILL.md` over `LLM + upstream README/guide` for these engineering tasks. Across all 9 NV model skills and three LLM backends, the with-skill arm passed 78/81 repeats, while the README-only arm passed 0/81 repeats. In matched backend-repeat pairs, SKILL.md won 78 times, README-only won 1 times, and 2 pairs tied because both arms failed. The exact one-sided paired sign test over decisive pairs gives `p = 1.323e-22`.

The stronger coding backends show a large aggregate gap: GPT-5.5/Codex and Opus produced a combined 54/54 with-skill pass rate versus 0/54 for README-only. Nemotron is more fragile, especially around command formatting and extraction, but still shows an aggregate skill advantage: 24/27 with-skill passes versus 0/27 README-only passes.

The README-only arms were not usually irrelevant; they often found part of the right upstream surface and earned partial scores. The failure was executable completion. Common README-only failure modes were nonzero execution exits, missing or malformed command extraction, unsafe cleanup such as generated `rm` fragments, commands that missed the neutral staged input path, commands that missed the expected output directory, and outputs that did not satisfy the deterministic artifact contract. These map directly to the details SKILL.md files are intended to make explicit: exact entrypoints, fresh-environment dependency steps, model variants, label or modality controls, staged input/output contracts, and verifier-facing artifacts.

The current artifacts support the claim that purpose-built skills are a much better LLM operating contract than the current upstream README/model-guide baseline. They do not, by themselves, prove that skills would beat every possible improved README. A stronger README-quality claim should be tested with a separate `README+adapter` arm that keeps upstream docs as the source of truth but adds neutral benchmark context such as staged input path, output directory, fresh venv assumptions, no upstream mutation, no unsafe cleanup, and expected artifact type. If that adapter starts naming wrapper entrypoints and validation schemas, it is effectively becoming skill-shaped, so it should be reported as a separate condition rather than replacing the raw README baseline.

## Correction Diagnostics

No current provider-default `max_correction_steps=3` Nemotron debug run is included in this report. If that diagnostic is run, keep it in a separate study root so it cannot overwrite or be mixed into the strict `max_correction_steps=0` baseline above.

Recommended correction work is therefore separate from the main study:

- Keep the primary with-vs-without study at `max_correction_steps=0`.
- Treat repair as its own diagnostic experiment.
- Split repair into specific classes: format-only repair, path/output repair, stderr/stdout execution repair, and artifact-contract repair from verifier output.
- Evaluate tolerant command extraction separately, especially for Nemotron.
- Do not make README-only repair competitive by leaking skill-specific wrapper details; that would invalidate the arm.

To add this protocol for a new skill, follow [`with-vs-without-authoring.md`](with-vs-without-authoring.md).

## Document Matrix

| Skill | Detailed reports | Current evidence |
|---|---|---|
| `nv_generate_ct_rflow` | `runs/with_vs_without_nv/reports/with-vs-without-nv-generate-ct-rflow-codex-opus.md`; `runs/with_vs_without_nv/reports/with-vs-without-nv-generate-ct-rflow-nemotron-correction.md` | Codex/Opus with 6/6 pass (avg 5.0/5) vs README 0/6 (avg 3.7/5); paired SKILL.md paired advantage (6/6 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.01562); gate Supports SKILL.md advantage. Nemotron with 3/3 pass (avg 5.0/5, steps mean 0.0; unresolved 0; values [0, 0, 0]) vs README 0/3 pass (avg 2.0/5, steps all unresolved; values [unresolved, unresolved, unresolved]); paired SKILL.md paired advantage (3/3 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.125); gate Supports SKILL.md advantage. |
| `nv_generate_mr` | `runs/with_vs_without_nv/reports/with-vs-without-nv-generate-mr-codex-opus.md`; `runs/with_vs_without_nv/reports/with-vs-without-nv-generate-mr-nemotron-correction.md` | Codex/Opus with 6/6 pass (avg 5.0/5) vs README 0/6 (avg 3.5/5); paired SKILL.md paired advantage (6/6 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.01562); gate Supports SKILL.md advantage. Nemotron with 3/3 pass (avg 5.0/5, steps mean 0.0; unresolved 0; values [0, 0, 0]) vs README 0/3 pass (avg 1.0/5, steps all unresolved; values [unresolved, unresolved, unresolved]); paired SKILL.md paired advantage (3/3 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.125); gate Supports SKILL.md advantage. |
| `nv_generate_mr_brain` | `runs/with_vs_without_nv/reports/with-vs-without-nv-generate-mr-brain-codex-opus.md`; `runs/with_vs_without_nv/reports/with-vs-without-nv-generate-mr-brain-nemotron-correction.md` | Codex/Opus with 6/6 pass (avg 5.0/5) vs README 0/6 (avg 3.8/5); paired SKILL.md paired advantage (6/6 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.01562); gate Supports SKILL.md advantage. Nemotron with 2/3 pass (avg 3.3/5, steps mean 0.0; unresolved 1; values [0, unresolved, 0]) vs README 0/3 pass (avg 1.0/5, steps all unresolved; values [unresolved, unresolved, unresolved]); paired SKILL.md paired advantage (2/3 SKILL.md wins, 1 README-only wins, 0 ties, sign-test p=0.5); gate Supports SKILL.md advantage. |
| `nv_generate_mr_brain_finetune` | `runs/with_vs_without_nv/reports/with-vs-without-nv-generate-mr-brain-finetune-codex-opus.md`; `runs/with_vs_without_nv/reports/with-vs-without-nv-generate-mr-brain-finetune-nemotron-correction.md` | Codex/Opus with 6/6 pass (avg 5.0/5) vs README 0/6 (avg 2.7/5); paired SKILL.md paired advantage (6/6 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.01562); gate Supports SKILL.md advantage. Nemotron with 2/3 pass (avg 3.3/5, steps mean 0.0; unresolved 1; values [0, 0, unresolved]) vs README 0/3 pass (avg 2.0/5, steps all unresolved; values [unresolved, unresolved, unresolved]); paired SKILL.md paired advantage (2/3 SKILL.md wins, 0 README-only wins, 1 ties, sign-test p=0.25); gate Supports SKILL.md advantage. |
| `nv_generate_vae_finetune` | `runs/with_vs_without_nv/reports/with-vs-without-nv-generate-vae-finetune-codex-opus.md`; `runs/with_vs_without_nv/reports/with-vs-without-nv-generate-vae-finetune-nemotron-correction.md` | Codex/Opus with 6/6 pass (avg 5.0/5) vs README 0/6 (avg 3.0/5); paired SKILL.md paired advantage (6/6 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.01562); gate Supports SKILL.md advantage. Nemotron with 3/3 pass (avg 5.0/5, steps mean 0.0; unresolved 0; values [0, 0, 0]) vs README 0/3 pass (avg 2.0/5, steps all unresolved; values [unresolved, unresolved, unresolved]); paired SKILL.md paired advantage (3/3 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.125); gate Supports SKILL.md advantage. |
| `nv_reason_cxr` | `runs/with_vs_without_nv/reports/with-vs-without-nv-reason-cxr-codex-opus.md`; `runs/with_vs_without_nv/reports/with-vs-without-nv-reason-cxr-nemotron-correction.md` | Codex/Opus with 6/6 pass (avg 5.0/5) vs README 0/6 (avg 3.3/5); paired SKILL.md paired advantage (6/6 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.01562); gate Supports SKILL.md advantage. Nemotron with 2/3 pass (avg 3.3/5, steps mean 0.0; unresolved 1; values [0, unresolved, 0]) vs README 0/3 pass (avg 2.7/5, steps all unresolved; values [unresolved, unresolved, unresolved]); paired SKILL.md paired advantage (2/3 SKILL.md wins, 0 README-only wins, 1 ties, sign-test p=0.25); gate Supports SKILL.md advantage. |
| `nv_segment_ct` | `runs/with_vs_without_nv/reports/with-vs-without-nv-segment-ct-codex-opus.md`; `runs/with_vs_without_nv/reports/with-vs-without-nv-segment-ct-nemotron-correction.md` | Codex/Opus with 6/6 pass (avg 5.0/5) vs README 0/6 (avg 3.3/5); paired SKILL.md paired advantage (6/6 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.01562); gate Supports SKILL.md advantage. Nemotron with 3/3 pass (avg 5.0/5, steps mean 0.0; unresolved 0; values [0, 0, 0]) vs README 0/3 pass (avg 0.7/5, steps all unresolved; values [unresolved, unresolved, unresolved]); paired SKILL.md paired advantage (3/3 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.125); gate Supports SKILL.md advantage. |
| `nv_segment_ct_finetune` | `runs/with_vs_without_nv/reports/with-vs-without-nv-segment-ct-finetune-codex-opus.md`; `runs/with_vs_without_nv/reports/with-vs-without-nv-segment-ct-finetune-nemotron-correction.md` | Codex/Opus with 6/6 pass (avg 5.0/5) vs README 0/6 (avg 4.0/5); paired SKILL.md paired advantage (6/6 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.01562); gate Supports SKILL.md advantage. Nemotron with 3/3 pass (avg 5.0/5, steps mean 0.0; unresolved 0; values [0, 0, 0]) vs README 0/3 pass (avg 1.3/5, steps all unresolved; values [unresolved, unresolved, unresolved]); paired SKILL.md paired advantage (3/3 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.125); gate Supports SKILL.md advantage. |
| `nv_segment_ctmr` | `runs/with_vs_without_nv/reports/with-vs-without-nv-segment-ctmr-codex-opus.md`; `runs/with_vs_without_nv/reports/with-vs-without-nv-segment-ctmr-nemotron-correction.md` | Codex/Opus with 6/6 pass (avg 5.0/5) vs README 0/6 (avg 3.8/5); paired SKILL.md paired advantage (6/6 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.01562); gate Supports SKILL.md advantage. Nemotron with 3/3 pass (avg 5.0/5, steps mean 0.0; unresolved 0; values [0, 0, 0]) vs README 0/3 pass (avg 0.0/5, steps all unresolved; values [unresolved, unresolved, unresolved]); paired SKILL.md paired advantage (3/3 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.125); gate Supports SKILL.md advantage. |

## Shared Arm Rules

| Arm | Agent may read | Agent may not read | Final answer target |
|---|---|---|---|
| With skill | `skills/<skill>/SKILL.md` | unrelated skill internals unless linked by `SKILL.md` | One bash command or `&&`-chained command using Medical AI Skills wrapper |
| Without skill | one upstream README, model card, or upstream guide selected for that skill | `skills/<skill>/`, wrapper scripts, validators, manifests, evidence packs | One bash command or `&&`-chained command using upstream directly |

The without-skill arm is not a no-docs baseline. It is a comparison against the upstream documentation a reasonable user would have.

## Shared Five-Tier Grade

| Tier | Check |
|---|---|
| 1 | A runnable entrypoint is present. |
| 2 | The command references the neutral staged user input path under `runs/with_vs_without_nv/_inputs/`. |
| 3 | The command selects the required model variant, modality, label IDs, or anatomy controls. |
| 4 | The command writes to the expected arm-specific output directory. |
| 5 | The command executes outside the sandbox, produces the expected artifact, and passes deterministic output checks. |

## Generated Artifacts

Study JSONs, large generated NIfTI volumes, checkpoints, and command outputs live under `runs/with_vs_without_nv/` and remain gitignored.

NV full run log: `not found`.
NV targeted rerun log: `not found`.

The helper used for the all-skill batch is `tools/with_vs_without/run_nv_model_studies.py`. It executes only guarded commands that reference the expected output directory and the expected skill/upstream runnable surface; unsafe shell fragments and without-skill commands that call hidden Medical AI Skills skill paths or wrapper basenames are blocked and graded as failures.

## Prompt Artifacts

The fair A2-style path prompts for NAT/tool-agent comparisons are saved here:

| Skill | Prompt artifact |
|---|---|
| `nv_generate_ct_rflow` | `tools/nat_audit/data/eval_nv_model_studies_nv_generate_ct_rflow_prompts.json` |
| `nv_generate_mr` | `tools/nat_audit/data/eval_nv_model_studies_nv_generate_mr_prompts.json` |
| `nv_generate_mr_brain` | `tools/nat_audit/data/eval_nv_model_studies_nv_generate_mr_brain_prompts.json` |
| `nv_generate_mr_brain_finetune` | `tools/nat_audit/data/eval_nv_model_studies_nv_generate_mr_brain_finetune_prompts.json` |
| `nv_generate_vae_finetune` | `tools/nat_audit/data/eval_nv_model_studies_nv_generate_vae_finetune_prompts.json` |
| `nv_reason_cxr` | `tools/nat_audit/data/eval_nv_model_studies_nv_reason_cxr_prompts.json` |
| `nv_segment_ct` | `tools/nat_audit/data/eval_nv_model_studies_nv_segment_ct_prompts.json` |
| `nv_segment_ct_finetune` | `tools/nat_audit/data/eval_nv_model_studies_nv_segment_ct_finetune_prompts.json` |
| `nv_segment_ctmr` | `tools/nat_audit/data/eval_nv_model_studies_nv_segment_ctmr_prompts.json` |

Regenerate prompt artifacts without making external API calls:

```bash
python tools/with_vs_without/run_nv_model_studies.py --mode prompts --prompt-style path
```
