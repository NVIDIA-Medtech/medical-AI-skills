# Medical Anonymization — With-vs-Without Skill Experiment

Generated: 2026-07-11 13:40 (local).
Protocol: scripted pipeline comparison (not agent command generation). NeMo inner anonymizer: local GLiNER + `medgemma:27b`. Judge: local `medgemma:27b`.

This report evaluates the **medical-anonymization** skill on the radiology-reports lane: `anonymize_medical_data.py` + `SKILL.md` vs upstream NeMo README baseline (`without_skill_baseline.py`). Both arms execute the real NeMo pipeline on the same staged CSV; they differ in policy (strict entity labels, redact template) and output contract.

**Pass criterion: an arm passes only if it produced anonymized output AND an LLM judge found ZERO residual PHI escapes across all rows — any single escape is a fail.**

This is an engineering reproducibility protocol. It is not a clinical, diagnostic, or regulatory claim.

## Evaluation task

- **Dataset:** 20 radiology reports from `skills/medical-anonymization/fixtures/batch00_reports_w_PHI.csv`. Reports: **20**.
- **Backend:** 1 (`local-phi`: local GLiNER @ 172.20.0.1:8001, Ollama medgemma:27b).
- **With-skill entrypoint:** `skills/medical-anonymization/scripts/anonymize_medical_data.py`
- **Without-skill entrypoint:** `skills/medical-anonymization/scripts/without_skill_baseline.py`
- **Judge reachable:** yes (`medgemma:27b`)

## Current aggregate result

### Result by arm — redaction quality, pass rate, and timing

One row per **arm**. **Pass = produced output AND zero residual PHI escapes across all reports (any escape is a fail).** Judge: `medgemma:27b`.

| Arm | Backend-runs producing output | Passes with 0 PHI escapes | Residual PHI escapes (items) | Report-runs fully redacted (report x backend) | Total exec (s) | Avg s/report |
|---|:--:|:--:|--:|:--:|--:|--:|
| **With skill (SKILL.md)** | 1/1 | **0/1 (0%)** | **1** | **19/20** | 327.9 | 16.4 |
| Without skill (upstream README) | 1/1 | 0/1 (0%) | 10 | 13/20 | 453.0 | 22.6 |

### Headline — PHI redaction result by arm

| Arm | Backend-runs producing output | Residual PHI escapes (items) | Report-runs fully redacted (report x backend) | Backend-runs with 0 escapes |
|---|:--:|--:|:--:|:--:|
| **With skill (SKILL.md)** | 1/1 | **1** | **19/20** | **0/1** |
| Without skill (upstream README) | 1/1 | 10 | 13/20 | 0/1 |

### Overall result (dataset level) — pass = produced output with zero PHI escapes

| Arm | Passes with 0 PHI escapes |
|---|---:|
| With skill (SKILL.md) | 0/1 (0%) |
| Without skill (upstream README) | 0/1 (0%) |

### Paired with-vs-without (exact one-sided sign test, report-row level)

Each **pair** is one report row (`study_uid`). **Skill wins** if with-skill had strictly fewer residual PHI escapes; **Without wins** if without-skill had fewer; **Tie** if equal.

| Scope | Report pairs | Skill wins | Without wins | Ties | Sign-test p |
|---|---:|---:|---:|---:|---:|
| local-phi | 20 | 7 | 1 | 12 | 0.035156 |
| **overall** | 20 | 7 | 1 | 12 | 0.035156 |

### Per-backend, per-arm report-row pass counts

| Backend/arm | Report-rows fully redacted | Mean exec s |
|---|---:|---:|
| local-phi/with | 19/20 | 327.9 |
| local-phi/without | 13/20 | 453.0 |

## PHI redaction (row-level)

### LLM-as-judge residual escapes (primary) — judge model `medgemma:27b`

An independent model re-read each anonymized report and flagged residual PHI — real identifying values still present as plain text rather than a `[bracketed]` placeholder.

| Backend / arm | Reports fully redacted | Residual PHI escapes (items) | Example escaped values |
|---|:--:|--:|---|
| local-phi/with | 19/20 | 1 | [DOCTOR] |
| local-phi/without | 13/20 | 10 | [REDACTED_DATE_OF_BIRTH], K., MRI20250924-0158, L., L. , 20240920-00123 |

#### Per-report residual PHI escape counts — one row per dataset report (0 = fully redacted)

Each cell is the number of residual PHI items the judge found in that report.

| study_uid (report) | local-phi/with (items) | local-phi/without (items) | Escaped PHI values |
|---|---:|---:|---|
| `LEDW5KEMKI` | 0 | 0 | — |
| `K67NPC32IW` | 1 | 0 | [DOCTOR] |
| `FMH275ZEBD` | 0 | 0 | — |
| `436G6LTU2V` | 0 | 2 | [REDACTED_DATE_OF_BIRTH] |
| `CU6OXMT22Y` | 0 | 1 | K. |
| `7EKH3TEF3P` | 0 | 1 | MRI20250924-0158 |
| `ACHZXGZU77` | 0 | 1 | K. |
| `AU2GAYT5JW` | 0 | 0 | — |
| `OEUY6K2K77` | 0 | 0 | — |
| `IK2WYQBYPT` | 0 | 0 | — |
| `SJ37X6XW72` | 0 | 0 | — |
| `XDJXLUHDQG` | 0 | 0 | — |
| `QNUTQMIU2B` | 0 | 0 | — |
| `22FM453NW2` | 0 | 2 | L., L.  |
| `WFYMA52DCS` | 0 | 1 | K. |
| `6S4NVLDXOZ` | 0 | 0 | — |
| `7GGZEIB4QU` | 0 | 0 | — |
| `AMIPG5YJF3` | 0 | 0 | — |
| `6A4V2YI2E2` | 0 | 0 | — |
| `ZNTAUPKWB6` | 0 | 2 | 20240920-00123, R. |

### Deterministic scan (cross-check)

Conservative regex scan for residual PHI signals (dates, long IDs, titled names, phones), excluding `[PLACEHOLDER]` tokens.

| Backend/arm | Rows fully redacted | Residual PHI escapes | Baseline PHI in input |
|---|---:|---:|---:|
| local-phi/with | 20/20 | 0 | 133 |
| local-phi/without | 18/20 | 5 | 133 |

## Structured + DICOM capability (medical-anonymization only)

The rad-reports experiment above isolates **text redaction quality**. The medical-anonymization skill additionally provides deterministic structured-field policy and DICOM metadata JSONL — gaps the without-skill baseline cannot cover.

| Lane | With skill (s) | Without skill (s) | Expected without gap |
|------|---------------:|------------------:|----------------------|
| dicom-metadata | 3.15 | 1.27 | no_structured_policy_applied |
| ehr | 54.74 | 33.81 | structured_id_not_hashed |
| reports | 34.8 | 42.51 | — |

## Timing

- With-skill pipeline: **327.9s** (16.4s/report)
- Without-skill pipeline: **453.0s** (22.6s/report)
- Judge calls: 40 (29484 tokens)

## Findings

- **Redaction quality (reports lane):** with-skill left **1** residual PHI items and fully redacted **19/20** report-runs; without-skill left **10** items and fully redacted **13/20** report-runs (~10x fewer items with the skill).
- **Paired sign test:** 7 skill-wins, 1 without-wins, 12 ties (p = 0.035156).
- **Capability gap:** without-skill has no DICOM policy, no structured MRN hashing, no nested/KV JSONL or audit trail (see structured + DICOM section).
- `Pass` = produced output AND zero LLM-judged residual PHI escapes (any escape is a fail).

## Reproduce

```bash
/home/marc/.conda/envs/reports-openai/bin/python skills/medical-anonymization/scripts/generate_with_vs_without_judge_report.py \
  --output-md docs/anonymization-with-vs-without-medical-local.md
```
