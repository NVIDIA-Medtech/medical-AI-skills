# Curation Skills — With-vs-Without Skill Experiment

Generated: 2026-07-07 13:58 (local).
Protocol: single-shot / no-repair (max_correction_steps=0). Repeats per backend/arm: 3.

This report evaluates the MR-RATE report-curation skills on a three-step pipeline: **(1) select** 10 radiology reports, **(2) confirm no PII**, and **(3) assign a disease label** per report. Each step runs in two arms that differ only in whether the skill is available:

- **With skill** — the agent runs the published skill wrapper (`report-anonymization` for PII, `report-pathology-classification` for labels), which supplies a fixed contract, vocabulary, and audit output.
- **Without skill** — the same backend is given only a generic natural request and must produce the result itself, with no skill vocabulary, schema, or entrypoint.

Grading is deterministic against ground truth: corpus membership (step 1), a known PII injection answer key (step 2), and the gold `mrrate_labels.csv` label vectors (step 3). `passed` measures task completion (the arm produced a contract-valid artifact), reported separately from accuracy — exactly as the reference protocol separates "did the agent take the right action" from model quality.

This is an engineering reproducibility protocol. It is not a clinical, diagnostic, or regulatory claim.

## How to read this run

> The with-skill arm runs the skills' deterministic `mock` mode (a tool call); the without-skill arm uses the named LLM backend(s) unaided. This contrasts the shipped skill tool against an unaided model.

## Evaluation dataset

- Reports: **10**, seeded sample (seed `42`) from `/home/marc/code/medical-data-curator/data/MR-RATE/reports/reports`, restricted to study_uids with gold labels.
- Injected PII: **3** of 10 reports carry a known doctor-name + date + accession line (the step-2 answer key); the rest are verified PII-free.
- Pathology vocabulary: **10 labels** (`Cerebral infarction, Gliosis, Arachnoid cyst, Cerebral atrophy, Ventriculomegaly, Empty sella syndrome, Pituitary adenoma, Mastoiditis, Intracranial meningioma, Encephalomalacia`), a subset shared by the skill and the gold label file.
- Files: `runs/curation_eval/headline_tool/dataset/evaluation_dataset.csv`, ground truth `runs/curation_eval/headline_tool/dataset/ground_truth.json`.
- Final populated dataset (with-skill: PII status + disease labels per report): `runs/curation_eval/headline_tool/evaluation_dataset_labeled.csv`.

### Sample of the evaluation dataset (10 rows)

The actual sampled reports, showing the with-skill PII verdict and assigned disease labels against the ground-truth answer keys (`—` = no positive label).

| # | study_uid | PII injected (truth) | PII verdict (with-skill) | Disease labels — skill | Disease labels — gold |
|--:|---|:--:|:--:|---|---|
| 1 | `VMSF4T57DJ` | yes | PII found | Cerebral infarction | Cerebral infarction |
| 2 | `WZNWW3EBDJ` | yes | PII found | — | — |
| 3 | `JEVZTL5EQ5` | no | confirmed no PII | Cerebral infarction; Gliosis | Gliosis; Ventriculomegaly |
| 4 | `M6D46R3WVW` | no | confirmed no PII | — | Gliosis |
| 5 | `3M3H5JAFIG` | no | confirmed no PII | Gliosis | Gliosis |
| 6 | `6O4MXJ6WC6` | no | confirmed no PII | Gliosis | Gliosis; Ventriculomegaly |
| 7 | `ARR6HFVXON` | no | confirmed no PII | Gliosis; Cerebral atrophy | Gliosis; Cerebral atrophy; Ventriculomegaly |
| 8 | `NABOKOC3QS` | no | confirmed no PII | Gliosis | Gliosis; Cerebral atrophy; Ventriculomegaly |
| 9 | `7M7PT2KNYM` | yes | PII found | Cerebral infarction | — |
| 10 | `BESIMDPG6W` | no | confirmed no PII | — | — |

## Current aggregate result

Success rates are reported per step (the primary metric) and as a strict full-pipeline composite (all three steps pass).

### Per-step success rate (all backends, all repeats)

| Step | With skill | Without skill |
|---|---:|---:|
| 1 select | 6/6 (100%) | 6/6 (100%) |
| 2 confirm-no-PII | 6/6 (100%) | 3/6 (50%) |
| 3 disease-label | 6/6 (100%) | 0/6 (0%) |

### Per-step paired with-vs-without (exact sign test)

| Step | Pairs | Skill wins | Without wins | Ties | Sign-test p |
|---|---:|---:|---:|---:|---:|
| 1 select | 6 | 0 | 0 | 6 | 1.0 |
| 2 PII | 6 | 3 | 0 | 3 | 0.125 |
| 3 label | 6 | 6 | 0 | 0 | 0.015625 |

### Full-pipeline composite (all 3 steps pass)

- With-skill: **6/6** full pipelines.
- Without-skill: **0/6** full pipelines.
- Paired composite: skill won **6**, without-skill won **0**, ties **0** (exact one-sided sign test p = 0.015625).

### Per-backend, per-step pass counts

| Backend | Arm | Pipeline | Step 1 select | Step 2 PII | Step 3 label |
|---|---|---:|---:|---:|---:|
| mock | with | 3/3 | 3/3 | 3/3 | 3/3 |
| mock | without | 0/3 | 3/3 | 3/3 | 0/3 |
| ollama-medgemma | with | 3/3 | 3/3 | 3/3 | 3/3 |
| ollama-medgemma | without | 0/3 | 3/3 | 0/3 | 0/3 |

### Paired with-vs-without (per backend)

| Backend | Pairs | Skill wins | Without wins | Ties | Sign-test p |
|---|---:|---:|---:|---:|---:|
| mock | 3 | 3 | 0 | 0 | 0.125 |
| ollama-medgemma | 3 | 3 | 0 | 0 | 0.125 |
| **overall** | 6 | 6 | 0 | 0 | 0.015625 |

## Token profiling

Provider-reported usage per backend/arm. The **with-skill** arm calls the skill wrapper as a tool; its internal usage is not surfaced as provider tokens (0 shown), while the **without-skill** arm's tokens are the model calls it makes to improvise the task.

| Backend | Arm | Repeats | Passes | LLM calls | Prompt tok | Completion tok | Total tok | Mean total/repeat | Mean exec s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mock | with | 3 | 3 | 0 | 0 | 0 | 0 | 0.0 | 0.024 |
| mock | without | 3 | 0 | 60 | 12369 | 174 | 12543* | 4181.0 | 0.001 |
| ollama-medgemma | with | 3 | 3 | 0 | 0 | 0 | 0 | 0.0 | 0.022 |
| ollama-medgemma | without | 3 | 0 | 60 | 20040 | 1355 | 21395 | 7131.7 | 5.944 |

`*` = estimated (mock backend approximates tokens by whitespace; real backends report exact usage).

## Quality layer (vs ground truth)

Task completion (`passed`, above) is separate from accuracy. This layer reports agreement with the answer keys.

| Backend | Arm | Step 2 PII accuracy | Step 3 label micro-F1 | Step 3 exact-match |
|---|---|---:|---:|---:|
| mock | with | 1.0000 | 0.6364 | 0.4000 |
| mock | without | 1.0000 | n/a (free-text) | n/a |
| ollama-medgemma | with | 1.0000 | 0.6364 | 0.4000 |
| ollama-medgemma | without | 0.7667 | n/a (free-text) | n/a |

## Findings

- **Step 3 (disease labelling) is the decisive, clean gap.** With the skill's fixed vocabulary and complete-0/1-vector contract, the label step passed **6/6**; without it, **0/6**. Unaided, the model returns free-text disease names that never satisfy the fixed-vocabulary contract, so coverage fails even when the content is plausible (paired sign-test p = 0.015625).
- **Step 2 (PII confirmation).** With-skill passed **6/6**, without-skill **3/6**. Mean PII accuracy: with 1.0000, without 0.8834. A yes/no verdict is within reach of a generic prompt, but model-driven arms tend to over-flag (false positives on already-de-identified text), whereas the deterministic anonymization skill confirms clean reports exactly. The strict step gate (all verdicts correct) therefore fails the model arms even though recall on injected PII is high.
- **Step 1 (selection)** is a shared, deterministic seeded fixture graded for validity; it is table-stakes, not a with/without differentiator.
- **Composite masking.** Because the full-pipeline gate requires all three steps, a shared step-2 weakness can flatten the composite even when step 3 shows a strong skill advantage. Read the per-step rates as the primary signal.

## Five-tier grade (per step)

**select**

| Tier | Check |
|---|---|
| 1 | Produced a selection artifact. |
| 2 | Selected exactly the requested number of reports. |
| 3 | Every selected study_uid exists in the source corpus. |
| 4 | Every selected report has non-empty text. |
| 5 | Selected uids are unique and carry ground-truth labels. |

**pii**

| Tier | Check |
|---|---|
| 1 | Produced a PII review output. |
| 2 | At least one verdict is machine-parseable. |
| 3 | A parseable verdict for every report (coverage). |
| 4 | All verdicts are valid booleans (contract complete). |
| 5 | All verdicts match the injection answer key. |

**label**

| Tier | Check |
|---|---|
| 1 | Produced a labelling output. |
| 2 | Output is parseable structured data. |
| 3 | Labels use the fixed pathology vocabulary (0/1 per label). |
| 4 | A complete label vector for every report (coverage). |
| 5 | All label values valid and gradeable against gold. |

## Backend reachability (probed at run time)

| Backend | Kind | Model | Reachable | Note |
|---|---|---|:--:|---|
| mock | mock | `synthetic-mock-deterministic` | yes | 0.0s ping |
| ollama-medgemma | openai | `medgemma:27b` | yes | 0.722s ping |

## Reproduce

From the `medical-AI-skills` catalog root:

```bash
# Build the dataset (deterministic; no LLM needed)
python -m tools.curation_eval.run_curation_eval dataset --n 10 --seed 42 --inject-pii 3 --out runs/curation_eval/dataset

# Offline methodology proof (mock skill mock backend)
python -m tools.curation_eval.run_curation_eval run --backends mock --repeats 3 --mode mock

# Live, multi-backend (same model with-wrapper vs without); needs the
# servers reachable and a GPU for the skills' live mode
python -m tools.curation_eval.run_curation_eval run \
  --backends ollama-nemotron ollama-qwen --repeats 3 --mode live --cuda-visible-devices 1
```

Artifacts for this run: `runs/curation_eval/headline_tool` (per-arm outputs + `study_results.json`).
