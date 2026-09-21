# Report Anonymization — With-vs-Without Skill Experiment

Generated: 2026-07-08 20:31 (local).
Protocol: single-shot / no-repair (max_correction_steps=0). Repeats per backend/arm: 1.

This report evaluates the **report-anonymization** skill: does `LLM + SKILL.md` help an agent produce a correct NeMo Anonymizer command compared with `LLM + upstream NeMo Anonymizer README`? Both arms differ only in the one document the agent may read; both execute the real NeMo Anonymizer pipeline for tier-5.

**Pass criterion: an arm passes only if it produced anonymized output AND an LLM judge found ZERO residual PHI escapes across all rows — any single escape is a fail.**

This is an engineering reproducibility protocol. It is not a clinical, diagnostic, or regulatory claim.

## Evaluation task

- **Dataset (dataset level):** 100 reports, staged from `runs/curation_eval/anon/study_20260708_194918/_inputs/reports_w_PHI.csv`.
- **Backends:** 2. Each backend anonymizes all 100 reports, so each arm covers 2 **backend-runs** = 200 **report-runs** (one report processed by one backend).
- **Residual PHI escape (item level):** one un-redacted PHI value the judge finds in a report-run. A single report-run can contain several escapes, so escape counts exceed the number of leaky report-runs.
- With-skill document: `skills/report-anonymization/SKILL.md`
- Without-skill document: `tools/curation_eval/upstream_docs/nemo_anonymizer_README.md`
- Tier-5 execution: yes (fresh output dir per attempt; `python` -> env with nemo-anonymizer, `NVIDIA_API_KEY` set).

## Current aggregate result

### Headline — PHI redaction result by arm

**Pass = a backend-run produced output AND had zero residual PHI escapes across all its reports (any escape is a fail).** Residual escapes (individual PHI items) are counted by an LLM judge (`openai/gpt-oss-120b`) re-reading each anonymized report. Each column names its unit: *backend-runs* (out of the backends run) vs *report-runs* (report x backend) vs *items*.

| Arm | Backend-runs producing output | Residual PHI escapes (items) | Report-runs fully redacted (report x backend) | Backend-runs with 0 escapes |
|---|:--:|--:|:--:|:--:|
| **With skill (SKILL.md)** | 2/2 | **21** | **197/200** | **0/2** |
| Without skill (upstream README) | 2/2 | 227 | 85/200 | 0/2 |

### Overall result (dataset level) — pass = produced output with zero PHI escapes

Each row is one **backend-run** (one backend anonymizing the full staged dataset). A pass requires tier-5 output and zero residual PHI escapes across all reports in that run.

| Arm | Passes with 0 PHI escapes |
|---|---:|
| With skill (SKILL.md) | 0/2 (0%) |
| Without skill (upstream README) | 0/2 (0%) |

### Paired with-vs-without (exact one-sided sign test, report-row level)

Each **pair** is one report row (`study_uid`) on the same backend and repeat. **Skill wins** if with-skill had strictly fewer residual PHI escapes; **Without wins** if without-skill had fewer; **Tie** if equal (including 0 vs 0).

| Scope | Report pairs | Skill wins | Without wins | Ties | Sign-test p |
|---|---:|---:|---:|---:|---:|
| gptoss | 100 | 54 | 1 | 45 | 0.0 |
| nemotron120-remote | 100 | 59 | 2 | 39 | 0.0 |
| **overall** | 200 | 113 | 3 | 84 | 0.0 |

### Per-backend, per-arm report-row pass counts and mean tier

**Report-rows fully redacted** = judge scored the row and found zero residual PHI escapes. **Mean tier** is the attempt-level command ladder (1–5), averaged across repeats.

| Backend/arm | Report-rows fully redacted | Mean tier (attempt) |
|---|---:|---:|
| gptoss/with | 99/100 (99%) | 5.0 |
| gptoss/without | 45/100 (45%) | 5.0 |
| nemotron120-remote/with | 98/100 (98%) | 5.0 |
| nemotron120-remote/without | 40/100 (40%) | 5.0 |

## PHI redaction (row-level)

### LLM-as-judge residual escapes (primary) — judge model `openai/gpt-oss-120b`

An independent model re-read each anonymized report and flagged residual PHI — real identifying values still present as plain text rather than a `[bracketed]` placeholder. This is the primary escape metric; the deterministic scan below is a conservative cross-check.

| Backend / arm | Reports fully redacted (of dataset, per backend) | Residual PHI escapes (items) | Example escaped values |
|---|:--:|--:|---|
| gptoss/with | 99/100 | 10 | Buchanan, Raoul, Gao, Victor, Milán, Milan |
| gptoss/without | 45/100 | 105 | A., L., S., T., K., M. |
| nemotron120-remote/with | 98/100 | 11 | Mercy General Hospital, Raoul, Baxter, Arthur, Karla, Milan |
| nemotron120-remote/without | 40/100 | 122 | A., S., M., L., K., T. |

#### Per-report residual PHI escape counts — one row per dataset report (0 = fully redacted)

Each cell is the number of residual PHI items the judge found in that report under the given backend/arm (not a pass/fail; a report can hold several items).

| study_uid (report) | nemotron120-remote/with (items) | nemotron120-remote/without (items) | gptoss/with (items) | gptoss/without (items) | Escaped PHI values |
|---|---:|---:|---:|---:|---|
| `LEDW5KEMKI` | 0 | 3 | 0 | 0 | A., S., M. |
| `K67NPC32IW` | 0 | 0 | 0 | 0 | — |
| `FMH275ZEBD` | 0 | 0 | 0 | 0 | — |
| `436G6LTU2V` | 0 | 0 | 0 | 0 | — |
| `CU6OXMT22Y` | 0 | 0 | 0 | 2 | A., L. |
| `7EKH3TEF3P` | 0 | 3 | 0 | 3 | A., S., L. |
| `ACHZXGZU77` | 0 | 0 | 0 | 0 | — |
| `AU2GAYT5JW` | 0 | 1 | 0 | 0 | S. |
| `OEUY6K2K77` | 0 | 2 | 0 | 0 | L., K. |
| `IK2WYQBYPT` | 0 | 0 | 0 | 0 | — |
| `SJ37X6XW72` | 0 | 0 | 0 | 1 | T. |
| `XDJXLUHDQG` | 0 | 3 | 0 | 2 | A., S., K. |
| `QNUTQMIU2B` | 0 | 2 | 0 | 3 | M., K., A. |
| `22FM453NW2` | 0 | 2 | 0 | 1 | S., T., A. |
| `WFYMA52DCS` | 0 | 0 | 0 | 1 | S. |
| `6S4NVLDXOZ` | 0 | 1 | 0 | 0 | L. |
| `7GGZEIB4QU` | 0 | 2 | 0 | 2 | A., L. |
| `AMIPG5YJF3` | 0 | 0 | 0 | 1 | K. |
| `6A4V2YI2E2` | 0 | 2 | 0 | 0 | L., K. |
| `ZNTAUPKWB6` | 0 | 3 | 0 | 0 | R., M., K. |
| `KJCKMLRVZR` | 0 | 1 | 0 | 0 | K. |
| `O3HAQUTWTT` | 0 | 0 | 0 | 1 | S. |
| `MDMLXIRZEU` | 0 | 1 | 0 | 2 | L., A. |
| `BRFDAVKDUK` | 0 | 1 | 0 | 0 | L. |
| `QEKJA43MID` | 0 | 3 | 0 | 0 | A., S., L. |
| `X447J6SJA4` | 0 | 0 | 0 | 0 | — |
| `LOE5JFQ2SK` | 0 | 1 | 0 | 1 | A., L. |
| `NHVZACGDDD` | 0 | 3 | 0 | 0 | A., R., L. |
| `PK7FUITYJB` | 0 | 2 | 0 | 0 | J., K. |
| `PDVUNDD6B4` | 0 | 2 | 0 | 2 | A., K. |
| `JSKWGROOL6` | 0 | 1 | 0 | 1 | A. |
| `NKDU3AB3OW` | 0 | 1 | 0 | 0 | 12345678 |
| `C5YRIDV2AQ` | 0 | 2 | 0 | 2 | A., S. |
| `GUJVGFQOGY` | 1 | 0 | 0 | 2 | Mercy General Hospital, A., L. |
| `NL3EHOYBAE` | 0 | 2 | 0 | 1 | A., L. |
| `ETD4TTHH5R` | 0 | 0 | 0 | 0 | — |
| `6MZ3GCEA7V` | 0 | 0 | 0 | 2 | A., L. |
| `ROHFA7WRPY` | 0 | 0 | 0 | 0 | — |
| `7PODNY5AKV` | 0 | 3 | 0 | 2 | A., S., T. |
| `YA4FOVXGTU` | 0 | 3 | 0 | 2 | A., S., T. |
| `BGYCAWNBSQ` | 0 | 2 | 0 | 1 | D., K. |
| `I3Y7Y4ZUQX` | 0 | 0 | 0 | 2 | A., S. |
| `L5FZEIJ6DP` | 0 | 1 | 0 | 0 | P. |
| `Y2RGCGWLCR` | 0 | 1 | 0 | 0 | L. |
| `MIRH5M4BUO` | 0 | 0 | 0 | 1 | L. |
| `G35MZWX6MW` | 0 | 0 | 0 | 0 | — |
| `22SSMT5XRP` | 0 | 1 | 0 | 1 | K. |
| `FUIX3GJQVT` | 0 | 0 | 0 | 0 | — |
| `PGOL5TMHPT` | 0 | 2 | 0 | 0 | A., K. |
| `FKFAP3XE63` | 0 | 2 | 0 | 0 | S., L. |
| `GJSPMUIPO7` | 0 | 2 | 0 | 1 | A., K. |
| `NECRNLCKBM` | 0 | 1 | 0 | 1 | K. |
| `GXAHBWJVHR` | 0 | 0 | 0 | 0 | — |
| `ONV7HXCGO4` | 0 | 3 | 0 | 2 | A., S., M. |
| `3KYTSFYIMD` | 0 | 0 | 0 | 2 | S., B. |
| `RWG3JIRROH` | 0 | 0 | 0 | 3 | A., R., L. |
| `ZMTTPRZ6QG` | 0 | 2 | 0 | 2 | A., L. |
| `WWJQ775N3D` | 0 | 0 | 0 | 1 | M. |
| `BEBHGQ5EQL` | 0 | 0 | 0 | 0 | — |
| `AQYTP7COY6` | 0 | 1 | 0 | 0 | A. |
| `LLD73AQGHD` | 0 | 0 | 0 | 0 | — |
| `UQSDQURM55` | 0 | 1 | 0 | 3 | 12345678, A., R., L. |
| `FMBGDRQYXV` | 0 | 2 | 0 | 1 | A., R. |
| `C7TIZGYADQ` | 0 | 1 | 0 | 1 | L. |
| `6XUDBZKKTM` | 0 | 0 | 0 | 3 | A., R., L. |
| `MFV4GF7LIF` | 0 | 0 | 0 | 0 | — |
| `BBCHW5SF4J` | 0 | 0 | 0 | 2 | M., K. |
| `CCBX25ECBM` | 0 | 2 | 0 | 0 | R., L. |
| `GE6K2YM5T4` | 0 | 2 | 0 | 1 | A., L. |
| `7AHYUATI4R` | 0 | 0 | 0 | 0 | — |
| `GZTPLLLF7R` | 0 | 1 | 0 | 1 | K. |
| `EWPUFAZAAV` | 0 | 1 | 0 | 1 | K. |
| `DLTEY2MQVL` | 0 | 2 | 0 | 3 | S., R., A. |
| `ZK2DGSJGSN` | 0 | 1 | 0 | 1 | K. |
| `2CWQFZHPFV` | 0 | 3 | 0 | 0 | A., S., T. |
| `N76Y22WYFI` | 0 | 0 | 0 | 2 | D., R. |
| `OCGQY46ONG` | 0 | 0 | 0 | 2 | A., L. |
| `D536YE4BQ2` | 0 | 0 | 0 | 0 | — |
| `LLXS72VUYL` | 0 | 2 | 0 | 2 | A., B. |
| `ALN2WDBET6` | 0 | 3 | 0 | 2 | A., S., L. |
| `QIUCOE4NOK` | 0 | 0 | 0 | 0 | — |
| `QM6YCKGEGJ` | 0 | 0 | 0 | 0 | — |
| `H3SFUMTJZS` | 0 | 3 | 0 | 0 | A., S., L. |
| `RYZMGQ7CSH` | 0 | 2 | 0 | 2 | A., S. |
| `QH63XB2N64` | 0 | 0 | 0 | 3 | A., R., L. |
| `WJVRWKP3GB` | 0 | 3 | 0 | 3 | A., S., L. |
| `I4JSFZVLIY` | 0 | 0 | 0 | 2 | R., S. |
| `JQD5XDVNFN` | 0 | 2 | 0 | 3 | S., L., A. |
| `V3MB6QTN5L` | 0 | 2 | 0 | 1 | A., K. |
| `MAZLO6VUUZ` | 0 | 0 | 0 | 0 | — |
| `PMDGCSYGYH` | 0 | 2 | 0 | 1 | A., L. |
| `YHF4DC6OH4` | 0 | 3 | 0 | 0 | A., S., T. |
| `F77VOEHBM2` | 0 | 0 | 0 | 0 | — |
| `TE4RHTSNYW` | 0 | 4 | 0 | 0 | A., 12345678, S., L. |
| `RJ5DRKT4MB` | 0 | 3 | 0 | 3 | A., S., L. |
| `46L3QAKRDC` | 0 | 2 | 0 | 3 | A., L., R. |
| `2F6IQCJRLM` | 0 | 0 | 0 | 0 | — |
| `HKKU3TXVXQ` | 10 | 5 | 10 | 8 | Raoul, Baxter, Arthur, Karla, Milan, Frederic, Dario, Josh, Henry, Buchanan, Gao, Victor |
| `XJWBR3P2FC` | 0 | 0 | 0 | 0 | — |
| `OLXVP6F6VH` | 0 | 2 | 0 | 0 | A., S. |

### Deterministic scan (cross-check)

Conservative regex scan for residual PHI signals (numeric dates, prose dates, 5+ digit IDs, `Dr./Prof./Mr./Mrs./Ms.` + name, phones), excluding `[PLACEHOLDER]` tokens. Middle initials and bare institution names are not counted, so this under-reports rather than over-reports.

### Per-arm residual summary

| Backend/arm | Rows fully redacted | Residual PHI escapes | Baseline PHI in input | Escape types |
|---|---:|---:|---:|---|
| gptoss/with | 100/100 | 0 | 620 | none |
| gptoss/without | 93/100 | 7 | 620 | titled_name=7 |
| nemotron120-remote/with | 100/100 | 0 | 620 | none |
| nemotron120-remote/without | 93/100 | 7 | 620 | long_id=3, titled_name=4 |

### Per-row residual escape counts (0 = fully redacted)

| study_uid | input PHI | nemotron120-remote/with | nemotron120-remote/without | gptoss/with | gptoss/without | Escaped values (regex) |
|---|---:|---:|---:|---:|---:|---|
| `LEDW5KEMKI` | 8 | 0 | 0 | 0 | 0 | — |
| `K67NPC32IW` | 4 | 0 | 0 | 0 | 0 | — |
| `FMH275ZEBD` | 7 | 0 | 0 | 0 | 0 | — |
| `436G6LTU2V` | 6 | 0 | 0 | 0 | 0 | — |
| `CU6OXMT22Y` | 6 | 0 | 0 | 0 | 0 | — |
| `7EKH3TEF3P` | 5 | 0 | 0 | 0 | 0 | — |
| `ACHZXGZU77` | 8 | 0 | 0 | 0 | 0 | — |
| `AU2GAYT5JW` | 5 | 0 | 0 | 0 | 0 | — |
| `OEUY6K2K77` | 6 | 0 | 0 | 0 | 0 | — |
| `IK2WYQBYPT` | 5 | 0 | 0 | 0 | 0 | — |
| `SJ37X6XW72` | 9 | 0 | 0 | 0 | 0 | — |
| `XDJXLUHDQG` | 9 | 0 | 0 | 0 | 0 | — |
| `QNUTQMIU2B` | 7 | 0 | 0 | 0 | 0 | — |
| `22FM453NW2` | 5 | 0 | 0 | 0 | 0 | — |
| `WFYMA52DCS` | 5 | 0 | 0 | 0 | 0 | — |
| `6S4NVLDXOZ` | 7 | 0 | 0 | 0 | 0 | — |
| `7GGZEIB4QU` | 5 | 0 | 0 | 0 | 0 | — |
| `AMIPG5YJF3` | 7 | 0 | 0 | 0 | 0 | — |
| `6A4V2YI2E2` | 5 | 0 | 0 | 0 | 0 | — |
| `ZNTAUPKWB6` | 7 | 0 | 0 | 0 | 0 | — |
| `KJCKMLRVZR` | 7 | 0 | 0 | 0 | 0 | — |
| `O3HAQUTWTT` | 7 | 0 | 0 | 0 | 0 | — |
| `MDMLXIRZEU` | 7 | 0 | 1 | 0 | 1 | Dr. Institution |
| `BRFDAVKDUK` | 5 | 0 | 1 | 0 | 1 | Dr. Institution |
| `QEKJA43MID` | 7 | 0 | 0 | 0 | 0 | — |
| `X447J6SJA4` | 6 | 0 | 0 | 0 | 0 | — |
| `LOE5JFQ2SK` | 5 | 0 | 0 | 0 | 0 | — |
| `NHVZACGDDD` | 8 | 0 | 0 | 0 | 0 | — |
| `PK7FUITYJB` | 8 | 0 | 1 | 0 | 1 | Dr. Institution |
| `PDVUNDD6B4` | 5 | 0 | 0 | 0 | 0 | — |
| `JSKWGROOL6` | 5 | 0 | 0 | 0 | 0 | — |
| `NKDU3AB3OW` | 6 | 0 | 1 | 0 | 0 | 12345678 |
| `C5YRIDV2AQ` | 7 | 0 | 0 | 0 | 0 | — |
| `GUJVGFQOGY` | 7 | 0 | 0 | 0 | 0 | — |
| `NL3EHOYBAE` | 7 | 0 | 0 | 0 | 1 | Dr. Institution |
| `ETD4TTHH5R` | 4 | 0 | 0 | 0 | 0 | — |
| `6MZ3GCEA7V` | 7 | 0 | 0 | 0 | 0 | — |
| `ROHFA7WRPY` | 5 | 0 | 0 | 0 | 0 | — |
| `7PODNY5AKV` | 4 | 0 | 0 | 0 | 0 | — |
| `YA4FOVXGTU` | 7 | 0 | 0 | 0 | 0 | — |
| `BGYCAWNBSQ` | 6 | 0 | 0 | 0 | 0 | — |
| `I3Y7Y4ZUQX` | 4 | 0 | 0 | 0 | 0 | — |
| `L5FZEIJ6DP` | 7 | 0 | 0 | 0 | 0 | — |
| `Y2RGCGWLCR` | 5 | 0 | 0 | 0 | 0 | — |
| `MIRH5M4BUO` | 4 | 0 | 0 | 0 | 1 | Dr. Institution |
| `G35MZWX6MW` | 7 | 0 | 0 | 0 | 0 | — |
| `22SSMT5XRP` | 6 | 0 | 0 | 0 | 0 | — |
| `FUIX3GJQVT` | 7 | 0 | 1 | 0 | 1 | Dr. Institution |
| `PGOL5TMHPT` | 7 | 0 | 0 | 0 | 0 | — |
| `FKFAP3XE63` | 6 | 0 | 0 | 0 | 1 | Dr. Institution |
| `GJSPMUIPO7` | 5 | 0 | 0 | 0 | 0 | — |
| `NECRNLCKBM` | 6 | 0 | 0 | 0 | 0 | — |
| `GXAHBWJVHR` | 6 | 0 | 0 | 0 | 0 | — |
| `ONV7HXCGO4` | 5 | 0 | 0 | 0 | 0 | — |
| `3KYTSFYIMD` | 5 | 0 | 0 | 0 | 0 | — |
| `RWG3JIRROH` | 7 | 0 | 0 | 0 | 0 | — |
| `ZMTTPRZ6QG` | 8 | 0 | 0 | 0 | 0 | — |
| `WWJQ775N3D` | 4 | 0 | 0 | 0 | 0 | — |
| `BEBHGQ5EQL` | 6 | 0 | 0 | 0 | 0 | — |
| `AQYTP7COY6` | 7 | 0 | 0 | 0 | 0 | — |
| `LLD73AQGHD` | 8 | 0 | 0 | 0 | 0 | — |
| `UQSDQURM55` | 7 | 0 | 1 | 0 | 0 | 12345678 |
| `FMBGDRQYXV` | 8 | 0 | 0 | 0 | 0 | — |
| `C7TIZGYADQ` | 7 | 0 | 0 | 0 | 0 | — |
| `6XUDBZKKTM` | 7 | 0 | 0 | 0 | 0 | — |
| `MFV4GF7LIF` | 5 | 0 | 0 | 0 | 0 | — |
| `BBCHW5SF4J` | 5 | 0 | 0 | 0 | 0 | — |
| `CCBX25ECBM` | 7 | 0 | 0 | 0 | 0 | — |
| `GE6K2YM5T4` | 7 | 0 | 0 | 0 | 0 | — |
| `7AHYUATI4R` | 7 | 0 | 0 | 0 | 0 | — |
| `GZTPLLLF7R` | 7 | 0 | 0 | 0 | 0 | — |
| `EWPUFAZAAV` | 4 | 0 | 0 | 0 | 0 | — |
| `DLTEY2MQVL` | 6 | 0 | 0 | 0 | 0 | — |
| `ZK2DGSJGSN` | 5 | 0 | 0 | 0 | 0 | — |
| `2CWQFZHPFV` | 5 | 0 | 0 | 0 | 0 | — |
| `N76Y22WYFI` | 7 | 0 | 0 | 0 | 0 | — |
| `OCGQY46ONG` | 7 | 0 | 0 | 0 | 0 | — |
| `D536YE4BQ2` | 5 | 0 | 0 | 0 | 0 | — |
| `LLXS72VUYL` | 8 | 0 | 0 | 0 | 0 | — |
| `ALN2WDBET6` | 7 | 0 | 0 | 0 | 0 | — |
| `QIUCOE4NOK` | 7 | 0 | 0 | 0 | 0 | — |
| `QM6YCKGEGJ` | 7 | 0 | 0 | 0 | 0 | — |
| `H3SFUMTJZS` | 5 | 0 | 0 | 0 | 0 | — |
| `RYZMGQ7CSH` | 9 | 0 | 0 | 0 | 0 | — |
| `QH63XB2N64` | 8 | 0 | 0 | 0 | 0 | — |
| `WJVRWKP3GB` | 7 | 0 | 0 | 0 | 0 | — |
| `I4JSFZVLIY` | 7 | 0 | 0 | 0 | 0 | — |
| `JQD5XDVNFN` | 7 | 0 | 0 | 0 | 0 | — |
| `V3MB6QTN5L` | 4 | 0 | 0 | 0 | 0 | — |
| `MAZLO6VUUZ` | 7 | 0 | 0 | 0 | 0 | — |
| `PMDGCSYGYH` | 7 | 0 | 0 | 0 | 0 | — |
| `YHF4DC6OH4` | 7 | 0 | 0 | 0 | 0 | — |
| `F77VOEHBM2` | 7 | 0 | 0 | 0 | 0 | — |
| `TE4RHTSNYW` | 5 | 0 | 1 | 0 | 0 | 12345678 |
| `RJ5DRKT4MB` | 6 | 0 | 0 | 0 | 0 | — |
| `46L3QAKRDC` | 4 | 0 | 0 | 0 | 0 | — |
| `2F6IQCJRLM` | 5 | 0 | 0 | 0 | 0 | — |
| `HKKU3TXVXQ` | 0 | 0 | 0 | 0 | 0 | — |
| `XJWBR3P2FC` | 6 | 0 | 0 | 0 | 0 | — |
| `OLXVP6F6VH` | 8 | 0 | 0 | 0 | 0 | — |

## Token profiling

Provider-reported usage for the command-generation call (the agent overhead to pick the command). The NeMo Anonymizer pipeline's own internal token use during tier-5 execution is not surfaced as provider usage.

| Backend | Arm | Repeats | Passes with 0 PHI escapes | LLM calls | Prompt tok | Completion tok | Reasoning tok | Total tok | Mean exec s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| gptoss | with | 1 | 0 | 1 | 1992 | 395 | 0 | 2387 | 286.497 |
| gptoss | without | 1 | 0 | 1 | 1656 | 449 | 0 | 2105 | 362.456 |
| nemotron120-remote | with | 1 | 0 | 1 | 2081 | 472 | 0 | 2553 | 299.405 |
| nemotron120-remote | without | 1 | 0 | 1 | 1707 | 612 | 0 | 2319 | 322.763 |

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
python skills/report-anonymization/scripts/anonymize_reports.py runs/curation_eval/anon/study_20260708_194918/_inputs/reports_w_PHI.csv --output-dir runs/curation_eval/anon/study_20260708_194918/nemotron120-remote/with/rep1 --full
```
- exec rc=0 (299.4s), out_rows=100, transformed=100
- stderr tail: `[19:54:22] Residual PHI : 1/100 record(s) (1.0%) with unreplaced detected values / [19:54:22]   leak types     : doctor=1 / [19:54:22] ========================================================================`

**nemotron120-remote / without / rep1** — tier 5, fail

```bash
mkdir -p runs/curation_eval/anon/study_20260708_194918/nemotron120-remote/without/rep1 && anonymizer run --source runs/curation_eval/anon/study_20260708_194918/_inputs/reports_w_PHI.csv --text-column report_w_PHI --replace redact --output runs/curation_eval/anon/study_20260708_194918/nemotron120-remote/without/rep1/anonymized_reports.csv --no-emit-telemetry
```
- exec rc=0 (322.8s), out_rows=100, transformed=100
- stderr tail: `[19:59:52] [INFO]   |-- 📊 Replacement progress: 100/100 (100%) — 0 failed, 2199.2 rec/s, eta 0.0s / [19:59:52] [INFO]   |-- 📋 Replacement complete (0 failed) [0.0s] / [19:59:52] [INFO] 🎉 Pipeline complete — 100 records processed, 0 total failures`

**gptoss / with / rep1** — tier 5, fail

```bash
python skills/report-anonymization/scripts/anonymize_reports.py \
  runs/curation_eval/anon/study_20260708_194918/_inputs/reports_w_PHI.csv \
  --output-dir runs/curation_eval/anon/study_20260708_194918/gptoss/with/rep1 \
  --full
```
- exec rc=0 (286.5s), out_rows=100, transformed=100
- stderr tail: `[20:04:41] Residual PHI : 1/100 record(s) (1.0%) with unreplaced detected values / [20:04:41]   leak types     : doctor=1 / [20:04:41] ========================================================================`

**gptoss / without / rep1** — tier 5, fail

```bash
mkdir -p runs/curation_eval/anon/study_20260708_194918/gptoss/without/rep1 && \
anonymizer run \
  --source runs/curation_eval/anon/study_20260708_194918/_inputs/reports_w_PHI.csv \
  --text-column report_w_PHI \
  --replace redact \
  --output runs/curation_eval/anon/study_20260708_194918/gptoss/without/rep1/anonymized_reports.csv
```
- exec rc=0 (362.5s), out_rows=100, transformed=100
- stderr tail: `[20:10:48] [INFO]   |-- 📊 Replacement progress: 100/100 (100%) — 0 failed, 2045.1 rec/s, eta 0.0s / [20:10:48] [INFO]   |-- 📋 Replacement complete (0 failed) [0.1s] / [20:10:48] [INFO] 🎉 Pipeline complete — 100 records processed, 0 total failures`

## Backend reachability (probed at run time)

| Backend | Kind | Model | Reachable | Ping s |
|---|---|---|:--:|---:|
| nemotron120-remote | openai | `nvidia/nemotron-3-super-120b-a12b` | yes | 0.613 |
| gptoss | openai | `openai/gpt-oss-120b` | yes | 0.503 |

## Findings

- **Redaction quality gap (primary result):** with-skill left **21** residual PHI escapes (individual PHI items) and fully redacted **197/200** report-runs; without-skill left **227** items and fully redacted **85/200** report-runs (~11x fewer items with the skill). The skill's strict GLiNER label set drives detection; the upstream-README default redaction leaves many residual fragments (mostly name middle initials). Concentration: 20 of the 21 with-skill escape items came from one hard report (`HKKU3TXVXQ`) that the strict labels missed across backends.
- Under the strict zero-escape pass criterion, with-skill passed 0/2 backend-runs and without-skill 0/2 backend-runs — neither backend-run cleared a perfect zero-escape bar at this scale, so the item-level escape counts above are the primary signal.
- Robustness/speed: mean tier-5 execution was 293.0s with-skill vs 342.6s without-skill. The slowest arm was gptoss/without at 362s: the unaided upstream-default detection path (no strict label set) does far more LLM augmentation and nearly hit the wall-clock budget. The wrapper's strict GLiNER label set bounds detection cost.
- Output contract: the with-skill wrapper emits `study_uid,report` plus a schema-valid `anonymization_summary` JSON and per-stage telemetry; the upstream `anonymizer run` output drops the `study_uid` passthrough and emits raw trace columns (`report_w_PHI_replaced`, ...).
- `Pass` = produced output AND zero LLM-judged residual PHI escapes (any escape is a fail). `Produced output` (tier-5 completion) is reported separately, so a leaky-but-complete arm shows as produced-output yet fails.

## Reproduce

From the `medical-AI-skills` catalog root:

```bash
export NVIDIA_API_KEY="nvapi-..."
python -m tools.curation_eval.anon_experiment \
  --backends nemotron120-remote gptoss=https://integrate.api.nvidia.com/v1=openai/gpt-oss-120b=NVIDIA_API_KEY \
  --repeats 1 --limit 100
```
