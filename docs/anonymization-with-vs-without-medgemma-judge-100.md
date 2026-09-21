# Report Anonymization — With-vs-Without Skill Experiment

Generated: 2026-07-09 10:25 (local).
Protocol: single-shot / no-repair (max_correction_steps=0). Repeats per backend/arm: 1.

**Canonical location:** the current version of this document is maintained on **GitLab master** — `medgar/medical-AI-skills` at `gitlab-master.nvidia.com` (branch `main`), path `docs/anonymization-with-vs-without-medgemma-judge-100.md` (+ `.html`).

This report evaluates the **report-anonymization** skill: does `LLM + SKILL.md` help an agent produce a correct NeMo Anonymizer command compared with `LLM + upstream NeMo Anonymizer README`? Both arms differ only in the one document the agent may read; both execute the real NeMo Anonymizer pipeline for tier-5.

**Pass criterion: an arm passes only if it produced anonymized output AND an LLM judge found ZERO residual PHI escapes across all rows — any single escape is a fail.**

This is an engineering reproducibility protocol. It is not a clinical, diagnostic, or regulatory claim.

## Test summary — tests, outcome, performance, failure modes

### What was tested
- **Question:** does `LLM + SKILL.md` help an agent produce a correct NeMo Anonymizer command vs. `LLM + upstream NeMo README`, measured by residual PHI after real execution?
- **Data:** 100 synthetic-PHI radiology reports, whole-job-at-once (one anonymizer invocation per arm over all 100).
- **Roles this run (all PHI stays local):**
  - **Backend / command-generator:** `nemotron120-remote` (`nvidia/nemotron-3-super-120b-a12b`, build.nvidia.com) — reads only the doc, never sees report data.
  - **Inner anonymizer** (GLiNER detect + LLM validate/augment, Redact strategy): **local `medgemma:27b`**.
  - **Judge / reviewer:** **local `medgemma:27b`**.
- **Preceding validation:** a direct 5-row medgemma anonymizer run — 0 residual PHI, independent leak-check passed — before the full experiment.

### Outcome
- Both arms executed cleanly: **tier 5, exit 0, 100/100 reports transformed**.
- **With-skill:** **90/99** report-rows fully redacted, **20** residual PHI items (judge).
- **Without-skill:** **64/99** report-rows fully redacted, **61** residual PHI items.
- **~3× fewer residual PHI items with the skill**; deterministic regex cross-check agrees (with **10** vs without **27** items).
- **Paired row-level sign test:** 34 skill-wins, 6 without-wins, 59 ties, **p = 4e-6** — the skill significantly reduces residual PHI.
- Strict attempt-level pass (zero escapes across *all* 100) = **0/1 both arms**: neither cleared a perfect zero-escape bar at 100-report scale, so the row-level counts above are the primary signal.

### Performance
- Backend command-gen (remote): ~10 s (with) / ~34 s (without) — clean, correct paths.
- Inner anonymizer (local medgemma): with **1514 s** (~25 min, ~15 s/report); without **2216 s** (~37 min, ~22 s/report — the upstream default does more LLM augmentation without the skill's strict GLiNER label set).
- **Per-row wall-clock (mean, tracked metric):** with = **15.1 s/report**, without = **22.2 s/report**. Whole-job-at-once runs rows in parallel, so this is the derived mean (`pipeline_secs / n_rows`); true per-row timing will be captured via a planned `--chunk-size` option (chunk = 1 → exact per-row).
- Judge (local medgemma): 200 report-rows, ~1 s each (~3–4 min).
- End-to-end ~63 min. Backend command-gen token use is tiny (~2.7k / 3.2k tokens per arm).

### Failure modes encountered (and resolutions)
- **nemotron as the inner validator:** reasoning (~15k tokens/run) overran the JSON schema → the validator dropped every record. Ollama did not honor `think:false` or `chat_template_kwargs.enable_thinking:false`; `/no_think` emptied the output. → inner anonymizer switched to non-reasoning **medgemma** (works: 0-fail).
- **medgemma / local-nemotron as the command-gen backend:** unreliable — medgemma wrote wrong script paths / dropped `.csv`; local nemotron reasoned for minutes and drifted the output path. → command-gen moved to the **remote** nemotron120 (data-free step, correct commands).
- **Disk:** gpt-oss-120b (65 GB) does not fit the ~47 GB free on C:, so it cannot be the local inner model here.
- **Harness output discovery:** only searched the exact per-rep dir; agents sometimes wrote a rep-named sibling CSV → added a symmetric fallback so produced output is found.
- **Local-config plumbing:** forced via a `sitecustomize.py` on `PYTHONPATH` that points any `Anonymizer()` at local providers — reversible, no site-packages mutation.

> Follow-up options are tracked in [`anonymization-experiment-backlog.md`](anonymization-experiment-backlog.md): backend comparison, judge calibration (medgemma vs gpt-oss-120b), whole-job-vs-chunked execution, and nemotron reasoning control.

## Methods and dependencies

### Arms — the only difference is the reference document
Both arms give the backend LLM the **same task** and a **single reference document**, differing only in *which* document — isolating the skill's effect on command generation.

- **With-skill** — `skills/report-anonymization/SKILL.md`, the **report-anonymization** skill. It documents the `anonymize_reports.py` wrapper: strict GLiNER label set, Redact strategy, `study_uid,report` output, and a residual-leak audit.
- **Without-skill** — `tools/curation_eval/upstream_docs/nemo_anonymizer_README.md`, a vendored copy of the **upstream NeMo Anonymizer README** (the raw `anonymizer` CLI / Python API with default config).

### How each arm is prompted (symmetric)
**System prompt (both arms):** *"You are a careful assistant that turns a data-engineering task plus one reference document into exactly one runnable shell command. You output a single fenced bash code block and nothing else executable."*

**User prompt (both arms):** the engineer's task — de-identify the 100-report CSV (columns `study_uid`, `report_w_PHI`) and write the anonymized output — with the one document pasted inline and a guard:
- With-skill: *"The only workflow document available to you is `…/SKILL.md`. Read it below. **Do not inspect any other files under skills/report-anonymization/.**"*
- Without-skill: same wording, but the upstream README, and *"**Do not read or use any files under skills/report-anonymization/.**"*

The backend returns one fenced bash command; the harness guards it (blocks destructive patterns), executes it against the real NeMo Anonymizer, grades it on the five-tier ladder, and the judge then re-reads each output row for residual PHI.

### Models (with sources)
| Role | Model id | Runs where | Source |
|---|---|---|---|
| Backend (command generation) | `nvidia/nemotron-3-super-120b-a12b` | remote — build.nvidia.com | [build.nvidia.com](https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b) · [HF](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16) · [NIM ref](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-super-120b-a12b) |
| Detector | `nvidia/gliner-pii` (GLiNER) | local — `serve_gliner.py`, GPU 2 Ada | [HF: nvidia/gliner-pii](https://huggingface.co/nvidia/gliner-pii) |
| Validator + augmenter (inner) | `medgemma:27b` | local — Ollama `172.20.0.1:11434` | [ollama.com/library/medgemma](https://ollama.com/library/medgemma) |
| Judge / reviewer | `medgemma:27b` | local — Ollama | [ollama.com/library/medgemma](https://ollama.com/library/medgemma) |

**PHI locality:** the remote backend only *writes the command* (it sees `SKILL.md`/the README, never report data); all detection, replacement, and judging run **locally** on medgemma — forced by a `sitecustomize.py` on `PYTHONPATH` that points any `Anonymizer()` at local providers (`providers.local.yaml` / `models.local.yaml`).

### Software, sources & versions (reproducibility)
- **NeMo Anonymizer** — repo: https://github.com/NVIDIA-NeMo/Anonymizer · PyPI: [`nemo-anonymizer`](https://pypi.org/project/nemo-anonymizer/) **`==0.2.1`** (latest tag `v0.2.1`; the package is dynamic-versioned, so `main` is ahead by unreleased commits but carries no newer version number). Reference docs: the repo `README.md` and `docs/concepts/self-hosting-gliner.md`.
- **Self-hosted GLiNER server** — `tools/serve_gliner.py`, taken from the Anonymizer repo (it is **not** shipped in the pip wheel): https://github.com/NVIDIA-NeMo/Anonymizer/blob/main/tools/serve_gliner.py . It downloads `nvidia/gliner-pii` from HuggingFace on first run. Deps: `fastapi`, `uvicorn`, `gliner`, `torch` (CUDA build from https://download.pytorch.org/whl/cu124).
- **Ollama** (local LLM serving) — https://ollama.com ; model `medgemma:27b` (https://ollama.com/library/medgemma).
- **Python** 3.12 (`data_curration` conda env). Orchestrator deps: `nemo-anonymizer==0.2.1`, `pandas`, `pyarrow`, `tiktoken`.
- **This repo** — harness `tools/curation_eval/anon_experiment.py`; skill wrapper `skills/report-anonymization/scripts/anonymize_reports.py`; local model config `providers.local.yaml` / `models.local.yaml`; local-default shim `sitecustomize.py` (added to `PYTHONPATH` so any `Anonymizer()` defaults to local models). Full local-serving setup and this run's exact command are in `local_serving/` and the **Reproduce** section below.

## Rewrite-mode & timing exploration (post-run status)

Beyond the redact baseline reported here, two enhancements were explored after the run:

**Per-row wall-clock timing.** The report tracks the **mean** per report (15.1 s with-skill, 22.2 s without-skill). *True* per-row wall-clock (each report timed individually) is **not yet captured** — whole-job-at-once runs reports in parallel, so it needs a `--chunk-size` option (chunk = 1 → exact per-row), which is designed but not yet built.

**Rewrite mode (`--mode rewrite`).** Added as a CLI toggle (default stays `redact`). Instead of `[TOKEN]` redaction, an LLM rewrites the whole passage and runs a built-in **evaluate → repair loop** (the requested "additional iterations"). Verified working locally on medgemma (the repair loop triggered; output is rewritten prose with PHI removed and clinical findings intact). Two caveats from a 2-row test:
- **Slow:** ~3 min/report (vs ~15 s redact) → a 100-report rewrite run is **~5 hours** on local medgemma.
- **Drop rate:** 1 of 2 rows was dropped at **latent-entity detection** — medgemma produced a `rationale` longer than the schema's `max_length=150`, which `nemo-anonymizer` 0.2.1 strictly rejects. This constraint is **identical on GitHub `main`** (the package is dynamic-versioned; latest tag `v0.2.1`; `main` is ~1 month of commits ahead but carries no new version and does **not** relax this), so a version upgrade will **not** fix it.

## Next steps

1. **True per-row timing** — implement `--chunk-size` (chunk = 1 → exact per-row wall-clock) and re-run the 100-report redact pass to populate a per-row timing metric (completes the per-row ask; report currently has only the mean).
2. **Rewrite-mode drop rate** — latent-entity detection is *optional* in rewrite mode and is also the slow step; disable it (or point that role at a stronger model) and re-test before deciding whether a full 100-report rewrite run is worthwhile.
3. **Judge calibration** — the medgemma judge is stricter than the prior `gpt-oss-120b` judge (direction is robust, absolute counts differ); re-score the same outputs with both judges to calibrate.
4. **Backend comparison ("B")** — run the with/without experiment with `nemotron-3-super:120b` as the command-gen backend and compare against this run.
5. **Chunked execution** — add batch chunking (`with/without-chunked` modes) for resumability, rate-limit resilience, and parallelism vs. the whole-job baseline.

Full detail for each is tracked in [`anonymization-experiment-backlog.md`](anonymization-experiment-backlog.md).

## Evaluation task

- **Dataset (dataset level):** 100 reports, staged from `runs/curation_eval/anon/study_medgemma_judge_100/_inputs/reports_w_PHI.csv`.
- **Backends:** 1. Each backend anonymizes all 100 reports, so each arm covers 1 **backend-runs** = 100 **report-runs** (one report processed by one backend).
- **Residual PHI escape (item level):** one un-redacted PHI value the judge finds in a report-run. A single report-run can contain several escapes, so escape counts exceed the number of leaky report-runs.
- With-skill document: `skills/report-anonymization/SKILL.md`
- Without-skill document: `tools/curation_eval/upstream_docs/nemo_anonymizer_README.md`
- Tier-5 execution: yes (fresh output dir per attempt; `python` -> env with nemo-anonymizer, `NVIDIA_API_KEY` set).

## Current aggregate result

### Headline — PHI redaction result by arm

**Pass = a backend-run produced output AND had zero residual PHI escapes across all its reports (any escape is a fail).** Residual escapes (individual PHI items) are counted by an LLM judge (`medgemma:27b`) re-reading each anonymized report. Each column names its unit: *backend-runs* (out of the backends run) vs *report-runs* (report x backend) vs *items*.

| Arm | Backend-runs producing output | Residual PHI escapes (items) | Report-runs fully redacted (report x backend) | Backend-runs with 0 escapes |
|---|:--:|--:|:--:|:--:|
| **With skill (SKILL.md)** | 1/1 | **20** | **90/99** | **0/1** |
| Without skill (upstream README) | 1/1 | 61 | 64/99 | 0/1 |

### Overall result (dataset level) — pass = produced output with zero PHI escapes

Each row is one **backend-run** (one backend anonymizing the full staged dataset). A pass requires tier-5 output and zero residual PHI escapes across all reports in that run.

| Arm | Passes with 0 PHI escapes |
|---|---:|
| With skill (SKILL.md) | 0/1 (0%) |
| Without skill (upstream README) | 0/1 (0%) |

### Paired with-vs-without (exact one-sided sign test, report-row level)

Each **pair** is one report row (`study_uid`) on the same backend and repeat. **Skill wins** if with-skill had strictly fewer residual PHI escapes; **Without wins** if without-skill had fewer; **Tie** if equal (including 0 vs 0).

| Scope | Report pairs | Skill wins | Without wins | Ties | Sign-test p |
|---|---:|---:|---:|---:|---:|
| nemotron120-remote | 99 | 34 | 6 | 59 | 4e-06 |
| **overall** | 99 | 34 | 6 | 59 | 4e-06 |

### Per-backend, per-arm report-row pass counts and mean tier

**Report-rows fully redacted** = judge scored the row and found zero residual PHI escapes. **Mean tier** is the attempt-level command ladder (1–5), averaged across repeats.

| Backend/arm | Report-rows fully redacted | Mean tier (attempt) |
|---|---:|---:|
| nemotron120-remote/with | 90/99 (91%) | 5.0 |
| nemotron120-remote/without | 64/99 (65%) | 5.0 |

## PHI redaction (row-level)

### LLM-as-judge residual escapes (primary) — judge model `medgemma:27b`

An independent model re-read each anonymized report and flagged residual PHI — real identifying values still present as plain text rather than a `[bracketed]` placeholder. This is the primary escape metric; the deterministic scan below is a conservative cross-check.

| Backend / arm | Reports fully redacted (of dataset, per backend) | Residual PHI escapes (items) | Example escaped values |
|---|:--:|--:|---|
| nemotron120-remote/with | 90/99 | 20 | INSTITUTION, March 15, [DOCTOR], [INSTITUTION], [DOCTOR], MD, Dr. [DOCTOR] |
| nemotron120-remote/without | 64/99 | 61 | K., March 15, November 2, 2024, November 3, 2024, ACC-20230112-MRINC7, 78-year-old |

#### Per-report residual PHI escape counts — one row per dataset report (0 = fully redacted)

Each cell is the number of residual PHI items the judge found in that report under the given backend/arm (not a pass/fail; a report can hold several items).

| study_uid (report) | nemotron120-remote/with (items) | nemotron120-remote/without (items) | Escaped PHI values |
|---|---:|---:|---|
| `LEDW5KEMKI` | 0 | 0 | — |
| `K67NPC32IW` | 1 | 0 | INSTITUTION |
| `FMH275ZEBD` | 0 | 0 | — |
| `436G6LTU2V` | 0 | 1 | K. |
| `CU6OXMT22Y` | 0 | 0 | — |
| `7EKH3TEF3P` | 1 | 2 | March 15, March 15, K. |
| `ACHZXGZU77` | 0 | 0 | — |
| `AU2GAYT5JW` | 0 | 2 | November 2, 2024, November 3, 2024 |
| `OEUY6K2K77` | 0 | 0 | — |
| `IK2WYQBYPT` | 0 | 0 | — |
| `SJ37X6XW72` | 0 | 0 | — |
| `XDJXLUHDQG` | 0 | 0 | — |
| `QNUTQMIU2B` | 0 | 0 | — |
| `22FM453NW2` | 0 | 0 | — |
| `WFYMA52DCS` | 0 | 1 | ACC-20230112-MRINC7 |
| `6S4NVLDXOZ` | 0 | 0 | — |
| `7GGZEIB4QU` | 0 | 2 | 78-year-old, [REDACTED_GENDER] |
| `AMIPG5YJF3` | 0 | 0 | — |
| `6A4V2YI2E2` | 0 | 0 | — |
| `ZNTAUPKWB6` | 0 | 0 | — |
| `KJCKMLRVZR` | 0 | 2 | L., [REDACTED_FIRST_NAME] L. [REDACTED_LAST_NAME] |
| `O3HAQUTWTT` | 0 | 0 | — |
| `MDMLXIRZEU` | 0 | 0 | — |
| `BRFDAVKDUK` | 0 | 1 | R. |
| `QEKJA43MID` | 0 | 1 | K. |
| `X447J6SJA4` | 0 | 0 | — |
| `LOE5JFQ2SK` | 0 | 0 | — |
| `NHVZACGDDD` | 3 | 12 | [DOCTOR], [INSTITUTION], [REDACTED_USER_NAME]̀NCE, [REDACTED_DATE], [REDACTED_OCCUPATION], [REDACTED_FIRST_NAME] [REDACTED_LAST_NAME], [REDACTED_DEGREE], [REDACTED_FIELD_OF_STUDY]. (twice), [REDACTED_ORGANIZATION_NAME], [REDACTED_BLOOD_TYPE] |
| `PK7FUITYJB` | 0 | 1 | L. |
| `PDVUNDD6B4` | 0 | 0 | — |
| `JSKWGROOL6` | 0 | 1 | ACR-2023-OCT-001234 |
| `NKDU3AB3OW` | 0 | 2 | K., [REDACTED_FIRST_NAME] K. [REDACTED_LAST_NAME] |
| `C5YRIDV2AQ` | 0 | 1 | MRN-2024-NOV-0047 |
| `GUJVGFQOGY` | 0 | 1 | 04/18/2024 |
| `NL3EHOYBAE` | 0 | 1 | A. |
| `ETD4TTHH5R` | 1 | 2 | [DOCTOR], MD, [REDACTED_FIRST_NAME] T. [REDACTED_LAST_NAME], [REDACTED_FIRST_NAME] [REDACTED_LAST_NAME] |
| `6MZ3GCEA7V` | 0 | 1 | L. |
| `ROHFA7WRPY` | 0 | 1 | R. |
| `7PODNY5AKV` | 0 | 2 | V., [REDACTED_FIRST_NAME] V. [REDACTED_LAST_NAME] |
| `YA4FOVXGTU` | 0 | 0 | — |
| `BGYCAWNBSQ` | 0 | 0 | — |
| `I3Y7Y4ZUQX` | 0 | 0 | — |
| `L5FZEIJ6DP` | 0 | 0 | — |
| `Y2RGCGWLCR` | 0 | 1 | K. |
| `MIRH5M4BUO` | 0 | 0 | — |
| `G35MZWX6MW` | 0 | 0 | — |
| `22SSMT5XRP` | 0 | 0 | — |
| `FUIX3GJQVT` | 0 | 2 | K, [REDACTED_CERTIFICATE_LICENSE_NUMBER] |
| `PGOL5TMHPT` | 0 | 0 | — |
| `FKFAP3XE63` | 0 | 1 | J. |
| `GJSPMUIPO7` | 0 | 0 | — |
| `NECRNLCKBM` | 0 | 0 | — |
| `GXAHBWJVHR` | 0 | 0 | — |
| `ONV7HXCGO4` | 0 | 1 | AB87CD-SEP24XZ |
| `3KYTSFYIMD` | -1 | -1 | — |
| `RWG3JIRROH` | 0 | 1 | J. |
| `ZMTTPRZ6QG` | 0 | 0 | — |
| `WWJQ775N3D` | 0 | 0 | — |
| `BEBHGQ5EQL` | 0 | 1 | MRI-2024-OCT55 |
| `AQYTP7COY6` | 0 | 0 | — |
| `LLD73AQGHD` | 0 | 0 | — |
| `UQSDQURM55` | 0 | 0 | — |
| `FMBGDRQYXV` | 0 | 0 | — |
| `C7TIZGYADQ` | 0 | 0 | — |
| `6XUDBZKKTM` | 0 | 0 | — |
| `MFV4GF7LIF` | 2 | 0 | [DOCTOR] |
| `BBCHW5SF4J` | 0 | 0 | — |
| `CCBX25ECBM` | 0 | 2 | September 16, 2024, September 17, 2024 |
| `GE6K2YM5T4` | 0 | 0 | — |
| `7AHYUATI4R` | 0 | 0 | — |
| `GZTPLLLF7R` | 0 | 1 | Dr. K. |
| `EWPUFAZAAV` | 0 | 0 | — |
| `DLTEY2MQVL` | 2 | 0 | [INSTITUTION], Dr. [DOCTOR] |
| `ZK2DGSJGSN` | 0 | 2 | June 5, 2024, June 6, 2024 |
| `2CWQFZHPFV` | 0 | 1 | J. |
| `N76Y22WYFI` | 0 | 2 | 20240310, R. |
| `OCGQY46ONG` | 0 | 0 | — |
| `D536YE4BQ2` | 0 | 0 | — |
| `LLXS72VUYL` | 0 | 0 | — |
| `ALN2WDBET6` | 0 | 0 | — |
| `QIUCOE4NOK` | 6 | 0 | [PATIENT], [PATIENT_MRN], [DATE_OF_BIRTH], Dr. [DOCTOR], [DATE], [ACCESSION_NUMBER] |
| `QM6YCKGEGJ` | 0 | 0 | — |
| `H3SFUMTJZS` | 0 | 0 | — |
| `RYZMGQ7CSH` | 0 | 0 | — |
| `QH63XB2N64` | 0 | 0 | — |
| `WJVRWKP3GB` | 0 | 0 | — |
| `I4JSFZVLIY` | 0 | 1 | ACC-20230605-00123 |
| `JQD5XDVNFN` | 0 | 2 | R., ACR-2023-00456 |
| `V3MB6QTN5L` | 0 | 0 | — |
| `MAZLO6VUUZ` | 3 | 2 | uroradiology, [DOCTOR], [INSTITUTION], K., [REDACTED_LAST_NAME] |
| `PMDGCSYGYH` | 0 | 0 | — |
| `YHF4DC6OH4` | 0 | 0 | — |
| `F77VOEHBM2` | 0 | 0 | — |
| `TE4RHTSNYW` | 0 | 2 | OCTOBER, T. |
| `RJ5DRKT4MB` | 0 | 0 | — |
| `46L3QAKRDC` | 1 | 0 | S. Patel |
| `2F6IQCJRLM` | 0 | 0 | — |
| `HKKU3TXVXQ` | 0 | 0 | — |
| `XJWBR3P2FC` | 0 | 0 | — |
| `OLXVP6F6VH` | 0 | 2 | 09/14/2024, 09/15/2024 |

### Deterministic scan (cross-check)

Conservative regex scan for residual PHI signals (numeric dates, prose dates, 5+ digit IDs, `Dr./Prof./Mr./Mrs./Ms.` + name, phones), excluding `[PLACEHOLDER]` tokens. Middle initials and bare institution names are not counted, so this under-reports rather than over-reports.

### Per-arm residual summary

| Backend/arm | Rows fully redacted | Residual PHI escapes | Baseline PHI in input | Escape types |
|---|---:|---:|---:|---|
| nemotron120-remote/with | 90/100 | 10 | 602 | date_prose=1, long_id=1, titled_name=8 |
| nemotron120-remote/without | 80/100 | 27 | 602 | date_numeric=5, date_prose=8, long_id=8, titled_name=6 |

### Per-row residual escape counts (0 = fully redacted)

| study_uid | input PHI | nemotron120-remote/with | nemotron120-remote/without | Escaped values (regex) |
|---|---:|---:|---:|---|
| `LEDW5KEMKI` | 6 | 0 | 0 | — |
| `K67NPC32IW` | 7 | 0 | 0 | — |
| `FMH275ZEBD` | 6 | 0 | 0 | — |
| `436G6LTU2V` | 6 | 0 | 0 | — |
| `CU6OXMT22Y` | 3 | 0 | 0 | — |
| `7EKH3TEF3P` | 3 | 0 | 0 | — |
| `ACHZXGZU77` | 7 | 0 | 0 | — |
| `AU2GAYT5JW` | 6 | 0 | 2 | November 2, 2024, November 3, 2024 |
| `OEUY6K2K77` | 6 | 0 | 0 | — |
| `IK2WYQBYPT` | 5 | 0 | 0 | — |
| `SJ37X6XW72` | 8 | 0 | 0 | — |
| `XDJXLUHDQG` | 8 | 0 | 0 | — |
| `QNUTQMIU2B` | 6 | 0 | 0 | — |
| `22FM453NW2` | 6 | 1 | 1 | Dr. Institution, Dr. Institution |
| `WFYMA52DCS` | 5 | 0 | 1 | 20230112 |
| `6S4NVLDXOZ` | 5 | 0 | 0 | — |
| `7GGZEIB4QU` | 5 | 0 | 0 | — |
| `AMIPG5YJF3` | 7 | 1 | 1 | May 2 1990 |
| `6A4V2YI2E2` | 8 | 1 | 0 | 02115 |
| `ZNTAUPKWB6` | 5 | 0 | 0 | — |
| `KJCKMLRVZR` | 6 | 0 | 0 | — |
| `O3HAQUTWTT` | 6 | 0 | 0 | — |
| `MDMLXIRZEU` | 7 | 0 | 0 | — |
| `BRFDAVKDUK` | 5 | 0 | 1 | Dr. Institution |
| `QEKJA43MID` | 6 | 0 | 1 | 846321 |
| `X447J6SJA4` | 7 | 0 | 0 | — |
| `LOE5JFQ2SK` | 6 | 0 | 0 | — |
| `NHVZACGDDD` | 26 | 0 | 0 | — |
| `PK7FUITYJB` | 7 | 0 | 0 | — |
| `PDVUNDD6B4` | 6 | 1 | 1 | Dr. Institution, Dr. Institution |
| `JSKWGROOL6` | 6 | 0 | 1 | 001234 |
| `NKDU3AB3OW` | 5 | 0 | 0 | — |
| `C5YRIDV2AQ` | 5 | 0 | 0 | — |
| `GUJVGFQOGY` | 4 | 0 | 1 | 04/18/2024 |
| `NL3EHOYBAE` | 6 | 0 | 0 | — |
| `ETD4TTHH5R` | 6 | 0 | 0 | — |
| `6MZ3GCEA7V` | 7 | 0 | 0 | — |
| `ROHFA7WRPY` | 5 | 0 | 0 | — |
| `7PODNY5AKV` | 6 | 0 | 0 | — |
| `YA4FOVXGTU` | 7 | 0 | 0 | — |
| `BGYCAWNBSQ` | 7 | 0 | 0 | — |
| `I3Y7Y4ZUQX` | 3 | 0 | 0 | — |
| `L5FZEIJ6DP` | 7 | 0 | 0 | — |
| `Y2RGCGWLCR` | 6 | 0 | 2 | 01/13/2025, 01/15/2025 |
| `MIRH5M4BUO` | 5 | 0 | 0 | — |
| `G35MZWX6MW` | 5 | 0 | 0 | — |
| `22SSMT5XRP` | 7 | 0 | 0 | — |
| `FUIX3GJQVT` | 6 | 0 | 0 | — |
| `PGOL5TMHPT` | 4 | 0 | 0 | — |
| `FKFAP3XE63` | 7 | 0 | 0 | — |
| `GJSPMUIPO7` | 6 | 0 | 0 | — |
| `NECRNLCKBM` | 6 | 1 | 0 | Dr. Neurology |
| `GXAHBWJVHR` | 5 | 0 | 0 | — |
| `ONV7HXCGO4` | 4 | 0 | 0 | — |
| `3KYTSFYIMD` | 5 | 0 | 0 | — |
| `RWG3JIRROH` | 5 | 0 | 0 | — |
| `ZMTTPRZ6QG` | 7 | 0 | 0 | — |
| `WWJQ775N3D` | 5 | 0 | 0 | — |
| `BEBHGQ5EQL` | 5 | 0 | 0 | — |
| `AQYTP7COY6` | 6 | 1 | 0 | Dr. Institution |
| `LLD73AQGHD` | 4 | 0 | 0 | — |
| `UQSDQURM55` | 6 | 0 | 0 | — |
| `FMBGDRQYXV` | 6 | 0 | 0 | — |
| `C7TIZGYADQ` | 8 | 0 | 1 | Dr. Hospital |
| `6XUDBZKKTM` | 7 | 0 | 0 | — |
| `MFV4GF7LIF` | 7 | 0 | 0 | — |
| `BBCHW5SF4J` | 7 | 0 | 0 | — |
| `CCBX25ECBM` | 6 | 0 | 2 | September 16, 2024, September 17, 2024 |
| `GE6K2YM5T4` | 6 | 0 | 0 | — |
| `7AHYUATI4R` | 6 | 0 | 0 | — |
| `GZTPLLLF7R` | 5 | 0 | 0 | — |
| `EWPUFAZAAV` | 4 | 0 | 0 | — |
| `DLTEY2MQVL` | 6 | 1 | 0 | Dr. Reporting |
| `ZK2DGSJGSN` | 5 | 0 | 2 | June 5, 2024, June 6, 2024 |
| `2CWQFZHPFV` | 7 | 0 | 0 | — |
| `N76Y22WYFI` | 6 | 0 | 1 | 20240310 |
| `OCGQY46ONG` | 5 | 0 | 0 | — |
| `D536YE4BQ2` | 7 | 0 | 0 | — |
| `LLXS72VUYL` | 7 | 1 | 0 | Dr. Neurology |
| `ALN2WDBET6` | 5 | 1 | 1 | Dr. Institution, 876543 |
| `QIUCOE4NOK` | 5 | 0 | 0 | — |
| `QM6YCKGEGJ` | 7 | 0 | 2 | May 15, 2025, Dr. Institution |
| `H3SFUMTJZS` | 5 | 0 | 0 | — |
| `RYZMGQ7CSH` | 7 | 0 | 0 | — |
| `QH63XB2N64` | 7 | 0 | 0 | — |
| `WJVRWKP3GB` | 6 | 0 | 0 | — |
| `I4JSFZVLIY` | 6 | 0 | 2 | 20230605, 00123 |
| `JQD5XDVNFN` | 5 | 0 | 1 | 00456 |
| `V3MB6QTN5L` | 5 | 0 | 1 | Dr. Institution |
| `MAZLO6VUUZ` | 7 | 0 | 0 | — |
| `PMDGCSYGYH` | 5 | 0 | 0 | — |
| `YHF4DC6OH4` | 6 | 0 | 0 | — |
| `F77VOEHBM2` | 4 | 0 | 0 | — |
| `TE4RHTSNYW` | 5 | 0 | 0 | — |
| `RJ5DRKT4MB` | 6 | 1 | 0 | Dr. Radiology |
| `46L3QAKRDC` | 6 | 0 | 0 | — |
| `2F6IQCJRLM` | 4 | 0 | 0 | — |
| `HKKU3TXVXQ` | 6 | 0 | 0 | — |
| `XJWBR3P2FC` | 4 | 0 | 0 | — |
| `OLXVP6F6VH` | 8 | 0 | 2 | 09/14/2024, 09/15/2024 |

## Token profiling

Provider-reported usage for the command-generation call (the agent overhead to pick the command). The NeMo Anonymizer pipeline's own internal token use during tier-5 execution is not surfaced as provider usage.

| Backend | Arm | Repeats | Passes with 0 PHI escapes | LLM calls | Prompt tok | Completion tok | Reasoning tok | Total tok | Mean exec s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| nemotron120-remote | with | 1 | 0 | 1 | 2066 | 602 | 0 | 2668 | 1513.848 |
| nemotron120-remote | without | 1 | 0 | 1 | 1692 | 1511 | 0 | 3203 | 2216.451 |

## Five-tier grade

| Tier | Check |
|---|---|
| 1 | A runnable NeMo Anonymizer entrypoint is present. |
| 2 | The command references the neutral staged input path. |
| 3 | The command targets the correct report text column (report_w_PHI) / wrapper. |
| 4 | The command writes to the expected arm output directory. |
| 5 | The command executes cleanly and produces an anonymized CSV that transformed the reports. |

## Generated commands

**nemotron120-remote / with / rep1** — tier 5, fail

```bash
python skills/report-anonymization/scripts/anonymize_reports.py runs/curation_eval/anon/study_medgemma_judge_100/_inputs/reports_w_PHI.csv --output-dir runs/curation_eval/anon/study_medgemma_judge_100/nemotron120-remote/with/rep1 --full
```
- exec rc=0 (1513.8s), out_rows=100, transformed=100
- stderr tail: `[09:44:18] Residual PHI : 1/100 record(s) (1.0%) with unreplaced detected values / [09:44:18]   leak types     : institution=1 / [09:44:18] ========================================================================`

**nemotron120-remote / without / rep1** — tier 5, fail

```bash
mkdir -p runs/curation_eval/anon/study_medgemma_judge_100/nemotron120-remote/without/rep1 && anonymizer run --source runs/curation_eval/anon/study_medgemma_judge_100/_inputs/reports_w_PHI.csv --text-column report_w_PHI --replace redact --output runs/curation_eval/anon/study_medgemma_judge_100/nemotron120-remote/without/rep1/anonymized_reports.csv
```
- exec rc=0 (2216.5s), out_rows=100, transformed=100
- stderr tail: `[10:21:48] [INFO]   |-- 📊 Replacement progress: 100/100 (100%) — 0 failed, 2285.0 rec/s, eta 0.0s / [10:21:48] [INFO]   |-- 📋 Replacement complete (0 failed) [0.0s] / [10:21:48] [INFO] 🎉 Pipeline complete — 100 records processed, 0 total failures`

## Backend reachability (probed at run time)

| Backend | Kind | Model | Reachable | Ping s |
|---|---|---|:--:|---:|
| nemotron120-remote | openai | `nvidia/nemotron-3-super-120b-a12b` | yes | 0.904 |

## Findings

- **Redaction quality gap (primary result):** with-skill left **20** residual PHI escapes (individual PHI items) and fully redacted **90/99** report-runs; without-skill left **61** items and fully redacted **64/99** report-runs (~3x fewer items with the skill). The skill's strict GLiNER label set drives detection; the upstream-README default redaction leaves many residual fragments (mostly name middle initials).
- Under the strict zero-escape pass criterion, with-skill passed 0/1 backend-runs and without-skill 0/1 backend-runs — neither backend-run cleared a perfect zero-escape bar at this scale, so the item-level escape counts above are the primary signal.
- Robustness/speed: mean tier-5 execution was 1513.8s with-skill vs 2216.5s without-skill. The slowest arm was nemotron120-remote/without at 2216s: the unaided upstream-default detection path (no strict label set) does far more LLM augmentation and nearly hit the wall-clock budget. The wrapper's strict GLiNER label set bounds detection cost.
- Output contract: the with-skill wrapper emits `study_uid,report` plus a schema-valid `anonymization_summary` JSON and per-stage telemetry; the upstream `anonymizer run` output drops the `study_uid` passthrough and emits raw trace columns (`report_w_PHI_replaced`, ...).
- `Pass` = produced output AND zero LLM-judged residual PHI escapes (any escape is a fail). `Produced output` (tier-5 completion) is reported separately, so a leaky-but-complete arm shows as produced-output yet fails.

## Reproduce

From the `medical-AI-skills` catalog root:

```bash
export NVIDIA_API_KEY="nvapi-..."
python -m tools.curation_eval.anon_experiment \
  --backends nemotron120-remote \
  --repeats 1 --limit 100
```
