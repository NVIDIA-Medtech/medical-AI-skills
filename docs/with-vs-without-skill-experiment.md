# With-vs-Without Skill Experiment Docs

Last refreshed: May 27, 2026.
Audit status: current local audit is incomplete after adding the two finetuning
prompt-only scenarios; direct repeat artifacts are pending for those new
scenarios.

Each covered user-facing model skill has two comparison documents from the corrected with-vs-without protocol:

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

The saved direct-API runs used an embedded-doc minimal prompt only because those chat backends had no file-reading tools. The study JSONs preserve those exact direct-API messages; the `tools/nat_audit/data` artifacts are the fair A2-style path prompts for future NAT/tool-agent comparisons.

The direct-API backend protocol is service-default by design: each LLM request sends only `model` and `messages`. It omits sampling fields, token caps, backend-specific reasoning controls, and extra request body fields. Retry attempts and socket timeouts are client transport settings, not model behavior settings.

## Last Completed Aggregate Result

The aggregate below is the last completed direct-API result set for the
original seven scenarios. The newly added `nv_generate_mr_brain_finetune` and
`nv_generate_vae_finetune` scenarios currently have complete prompt artifacts
and no direct API repeat artifacts yet.

- Codex/Opus with-skill repeats: 42/42 passed.
- Codex/Opus README-only repeats: 0/42 passed.
- Nemotron with-skill repeats: 21/21 passed.
- Nemotron README-only repeats: 0/21 passed.
- Codex/Opus outcome-support gates: 7/7 skill reports support SKILL.md paired advantage.
- Nemotron outcome-support gates: 7/7 skill reports support SKILL.md paired advantage.

Every with-skill repeat exits successfully and passes the deterministic grader.

Artifact completeness alone does not establish the skill-advantage claim. Treat the aggregate as supporting that claim only when every expected per-skill/backend outcome-support gate reports a SKILL.md paired advantage.

## Token Profiling

The table below aggregates provider-reported usage across all seven skills for each backend/arm. It is useful for separating workflow success from prompting cost: README-only arms often spent more output tokens explaining or improvising commands while still failing the artifact contract.

| Backend | Arm | Repeats | Passes | Attempts | Prompt tokens | Completion tokens | Reasoning tokens | Total tokens | Mean total/repeat | Executed | Mean exec s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GPT-5.5 / Codex | with | 21 | 21 | 21 | 48,432 | 9,854 | 7,043 | 58,286 | 2,775.5 | 21 | 48.8 |
| GPT-5.5 / Codex | without | 21 | 0 | 21 | 65,172 | 108,211 | 86,134 | 173,383 | 8,256.3 | 5 | 0.0 |
| Nemotron | with | 21 | 21 | 21 | 51,063 | 35,026 | 0 | 86,089 | 4,099.5 | 21 | 56.5 |
| Nemotron | without | 21 | 0 | 21 | 69,408 | 133,520 | 0 | 202,928 | 9,663.2 | 7 | 0.0 |
| Opus 4.7 | with | 21 | 21 | 21 | 83,070 | 4,355 | 0 | 87,425 | 4,163.1 | 21 | 52.9 |
| Opus 4.7 | without | 21 | 0 | 21 | 101,544 | 16,292 | 0 | 117,836 | 5,611.2 | 17 | 0.2 |

Reasoning tokens are included in completion tokens where reported. Mean execution seconds excludes repeats that never reached command execution, but those repeats still contributed prompt and completion tokens.

## Nemotron Diagnostic Layer

Nemotron is reported with the same main no-repair outcome gate as the other backends. The additional layer below isolates backend protocol behavior: strict fenced-block compliance, deterministic recoverability of malformed command text, and repeated failure buckets.

| Arm | Repeats | Passed strict | Strict command | Recoverable malformed command | Unrecoverable formatting | Guard-ready after tolerant extraction | Static guard blocked | Format categories | Guard reasons |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| with | 21 | 21 | 21 | 0 | 0 | 0 | 0 | strict 21 | none |
| without | 21 | 0 | 16 | 5 | 0 | 3 | 2 | strict 16; raw_shell 5 | command does not reference the neutral staged input path (2) |

Protocol-compliance failure buckets, counted per repeat and not mutually exclusive:

| Bucket | Count |
|---|---:|
| No strict command extracted | 5 |
| Wrong or missing runnable surface | 6 |
| Missing staged input path | 14 |
| Missing model/modality/control marker | 8 |
| Missing output directory | 5 |
| Unsafe/static guard block | 9 |
| Nonzero execution exit | 6 |
| Artifact contract failure after execution | 1 |

## Overall Findings

The current evidence strongly favors `LLM + SKILL.md` over `LLM + upstream README/guide` for these engineering tasks. Across all seven NV model skills and three LLM backends, the with-skill arm passed 63/63 repeats, while the README-only arm passed 0/63 repeats. In matched backend-repeat pairs, SKILL.md won 63 times, README-only won 0 times, and 0 pairs tied because both arms failed. The exact one-sided paired sign test over decisive pairs gives `p = 1.084e-19`.

The effect is clearest for the stronger coding backends: GPT-5.5/Codex and Opus both passed every with-skill repeat after the SKILL.md updates, for a combined 42/42 with-skill pass rate versus 0/42 for README-only. Nemotron is more fragile, especially around command formatting and extraction, but still shows an aggregate skill advantage: 21/21 with-skill passes versus 0/21 README-only passes.

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

Rows with pass statistics are historical completed runs. Rows marked pending
have prompt artifacts only and should not be cited as outcome evidence.

| Skill | Codex/Opus comparison | Nemotron baseline study | Current evidence |
|---|---|---|---|
| `nv_generate_ct_rflow` | [`with-vs-without-nv-generate-ct-rflow-codex-opus.md`](with-vs-without-nv-generate-ct-rflow-codex-opus.md) | [`with-vs-without-nv-generate-ct-rflow-nemotron-correction.md`](with-vs-without-nv-generate-ct-rflow-nemotron-correction.md) | Codex/Opus with 6/6 pass (avg 5.0/5) vs README 0/6 (avg 3.3/5); paired SKILL.md paired advantage (6/6 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.01562); gate Supports SKILL.md advantage. Nemotron with 3/3 pass (avg 5.0/5, steps mean 0.0; unresolved 0; values [0, 0, 0]) vs README 0/3 pass (avg 1.7/5, steps all unresolved; values [unresolved, unresolved, unresolved]); paired SKILL.md paired advantage (3/3 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.125); gate Supports SKILL.md advantage. |
| `nv_generate_mr` | [`with-vs-without-nv-generate-mr-codex-opus.md`](with-vs-without-nv-generate-mr-codex-opus.md) | [`with-vs-without-nv-generate-mr-nemotron-correction.md`](with-vs-without-nv-generate-mr-nemotron-correction.md) | Codex/Opus with 6/6 pass (avg 5.0/5) vs README 0/6 (avg 4.0/5); paired SKILL.md paired advantage (6/6 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.01562); gate Supports SKILL.md advantage. Nemotron with 3/3 pass (avg 5.0/5, steps mean 0.0; unresolved 0; values [0, 0, 0]) vs README 0/3 pass (avg 3.3/5, steps all unresolved; values [unresolved, unresolved, unresolved]); paired SKILL.md paired advantage (3/3 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.125); gate Supports SKILL.md advantage. |
| `nv_generate_mr_brain` | [`with-vs-without-nv-generate-mr-brain-codex-opus.md`](with-vs-without-nv-generate-mr-brain-codex-opus.md) | [`with-vs-without-nv-generate-mr-brain-nemotron-correction.md`](with-vs-without-nv-generate-mr-brain-nemotron-correction.md) | Codex/Opus with 6/6 pass (avg 5.0/5) vs README 0/6 (avg 3.7/5); paired SKILL.md paired advantage (6/6 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.01562); gate Supports SKILL.md advantage. Nemotron with 3/3 pass (avg 5.0/5, steps mean 0.0; unresolved 0; values [0, 0, 0]) vs README 0/3 pass (avg 2.0/5, steps all unresolved; values [unresolved, unresolved, unresolved]); paired SKILL.md paired advantage (3/3 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.125); gate Supports SKILL.md advantage. |
| `nv_generate_mr_brain_finetune` | pending direct API repeats | pending direct API repeats | Prompt artifact complete at `tools/nat_audit/data/eval_nv_model_studies_nv_generate_mr_brain_finetune_prompts.json`; outcome evidence pending. |
| `nv_generate_vae_finetune` | pending direct API repeats | pending direct API repeats | Prompt artifact complete at `tools/nat_audit/data/eval_nv_model_studies_nv_generate_vae_finetune_prompts.json`; outcome evidence pending. |
| `nv_reason_cxr` | [`with-vs-without-nv-reason-cxr-codex-opus.md`](with-vs-without-nv-reason-cxr-codex-opus.md) | [`with-vs-without-nv-reason-cxr-nemotron-correction.md`](with-vs-without-nv-reason-cxr-nemotron-correction.md) | Codex/Opus with 6/6 pass (avg 5.0/5) vs README 0/6 (avg 4.0/5); paired SKILL.md paired advantage (6/6 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.01562); gate Supports SKILL.md advantage. Nemotron with 3/3 pass (avg 5.0/5, steps mean 0.0; unresolved 0; values [0, 0, 0]) vs README 0/3 pass (avg 4.0/5, steps all unresolved; values [unresolved, unresolved, unresolved]); paired SKILL.md paired advantage (3/3 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.125); gate Supports SKILL.md advantage. |
| `nv_segment_ct` | [`with-vs-without-nv-segment-ct-codex-opus.md`](with-vs-without-nv-segment-ct-codex-opus.md) | [`with-vs-without-nv-segment-ct-nemotron-correction.md`](with-vs-without-nv-segment-ct-nemotron-correction.md) | Codex/Opus with 6/6 pass (avg 5.0/5) vs README 0/6 (avg 3.5/5); paired SKILL.md paired advantage (6/6 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.01562); gate Supports SKILL.md advantage. Nemotron with 3/3 pass (avg 5.0/5, steps mean 0.0; unresolved 0; values [0, 0, 0]) vs README 0/3 pass (avg 2.3/5, steps all unresolved; values [unresolved, unresolved, unresolved]); paired SKILL.md paired advantage (3/3 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.125); gate Supports SKILL.md advantage. |
| `nv_segment_ct_finetune` | [`with-vs-without-nv-segment-ct-finetune-codex-opus.md`](with-vs-without-nv-segment-ct-finetune-codex-opus.md) | [`with-vs-without-nv-segment-ct-finetune-nemotron-correction.md`](with-vs-without-nv-segment-ct-finetune-nemotron-correction.md) | Codex/Opus with 6/6 pass (avg 5.0/5) vs README 0/6 (avg 3.8/5); paired SKILL.md paired advantage (6/6 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.01562); gate Supports SKILL.md advantage. Nemotron with 3/3 pass (avg 5.0/5, steps mean 0.0; unresolved 0; values [0, 0, 0]) vs README 0/3 pass (avg 2.7/5, steps all unresolved; values [unresolved, unresolved, unresolved]); paired SKILL.md paired advantage (3/3 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.125); gate Supports SKILL.md advantage. |
| `nv_segment_ctmr` | [`with-vs-without-nv-segment-ctmr-codex-opus.md`](with-vs-without-nv-segment-ctmr-codex-opus.md) | [`with-vs-without-nv-segment-ctmr-nemotron-correction.md`](with-vs-without-nv-segment-ctmr-nemotron-correction.md) | Codex/Opus with 6/6 pass (avg 5.0/5) vs README 0/6 (avg 3.8/5); paired SKILL.md paired advantage (6/6 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.01562); gate Supports SKILL.md advantage. Nemotron with 3/3 pass (avg 5.0/5, steps mean 0.0; unresolved 0; values [0, 0, 0]) vs README 0/3 pass (avg 1.0/5, steps all unresolved; values [unresolved, unresolved, unresolved]); paired SKILL.md paired advantage (3/3 SKILL.md wins, 0 README-only wins, 0 ties, sign-test p=0.125); gate Supports SKILL.md advantage. |

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

Study JSONs live under `examples/studies/with_vs_without_skill/`. Large generated NIfTI volumes, checkpoints, and command outputs live under `runs/with_vs_without_nv/` and remain gitignored.

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
| `nv_reason_cxr` | `tools/nat_audit/data/eval_nv_model_studies_nv_reason_cxr_prompts.json` |
| `nv_segment_ct` | `tools/nat_audit/data/eval_nv_model_studies_nv_segment_ct_prompts.json` |
| `nv_segment_ct_finetune` | `tools/nat_audit/data/eval_nv_model_studies_nv_segment_ct_finetune_prompts.json` |
| `nv_segment_ctmr` | `tools/nat_audit/data/eval_nv_model_studies_nv_segment_ctmr_prompts.json` |

Regenerate prompt artifacts without making external API calls:

```bash
python tools/with_vs_without/run_nv_model_studies.py --mode prompts --prompt-style path
```
