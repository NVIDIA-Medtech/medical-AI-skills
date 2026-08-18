# Report Anonymization — With-vs-Without Skill Experiment

Generated: 2026-07-10 10:15 (local).
Protocol: single-shot / no-repair (max_correction_steps=0). Repeats per backend/arm: 1.

This report evaluates the **report-anonymization** skill: does `LLM + SKILL.md` help an agent produce a correct NeMo Anonymizer command compared with `LLM + upstream NeMo Anonymizer README`? Both arms differ only in the one document the agent may read; both execute the real NeMo Anonymizer pipeline for tier-5.

**Pass criterion: an arm passes only if it produced anonymized output AND an LLM judge found ZERO residual PHI escapes across all rows — any single escape is a fail.**

This is an engineering reproducibility protocol. It is not a clinical, diagnostic, or regulatory claim.

## Evaluation task

- **Dataset (dataset level):** 100 reports, staged from `runs/curation_eval/anon/study_20260708_194918/_inputs/reports_w_PHI.csv`.
- **Backends:** 4. Each backend anonymizes all 100 reports, so each arm covers 4 **backend-runs** = 400 **report-runs** (one report processed by one backend).
- **Residual PHI escape (item level):** one un-redacted PHI value the judge finds in a report-run. A single report-run can contain several escapes, so escape counts exceed the number of leaky report-runs.
- With-skill document: `skills/report-anonymization/SKILL.md`
- Without-skill document: `tools/curation_eval/upstream_docs/nemo_anonymizer_README.md`
- Tier-5 execution: yes (fresh output dir per attempt; `python` -> env with nemo-anonymizer, `NVIDIA_API_KEY` set).

## Current aggregate result

### Result by arm — redaction quality, pass rate, and timing

One row per **arm** (aggregated over its backend-runs). **Pass = a backend-run produced output AND had zero residual PHI escapes across all its reports (any escape is a fail).** **Escape counts here were produced by MORE THAN ONE judge model (`openai/gpt-oss-120b`, `openai/openai/gpt-5.5`); counts are therefore NOT directly comparable across arms/backends judged by different models — see the per-backend table for which judge scored each.** Units: *backend-runs* (out of the backends run), *report-runs* (report x backend), *items*. **Each arm may aggregate MULTIPLE backend-runs** — e.g. 3 backends x 100 reports = 300 report-runs. **Timing** is tier-5 wall-clock (seconds): the `Total` column **sums** wall-clock across the arm's backend-runs, while `Avg` divides that total by the number of *report-runs*, so `Total / Avg` = report-runs (not 100). Per-backend-run timing is in the **Anonymization performance** table below.

| Arm | Backend-runs producing output | Passes with 0 PHI escapes | Residual PHI escapes (items) | Report-runs fully redacted (report x backend) | Total tier-5 wall (sec, summed over runs) | Avg tier-5 wall (sec/report-run) |
|---|:--:|:--:|--:|:--:|--:|--:|
| **With skill (SKILL.md)** | 3/3 | **0/3 (0%)** | **27** | **291/300** | 917.9 | 3.1 |
| Without skill (upstream README) | 3/3 | 0/3 (0%) | 1342 | 85/300 | 1181.2 | 3.9 |
| Unaided (natural request, no doc) | 0/2 | 0/2 (0%) | n/a | n/a | n/a | n/a |

### Paired with-vs-without (exact one-sided sign test, report-row level)

Each **pair** is one report row (`study_uid`) on the same backend and repeat. **Skill wins** if with-skill had strictly fewer residual PHI escapes; **Without wins** if without-skill had fewer; **Tie** if equal (including 0 vs 0).

| Scope | Report pairs | Skill wins | Without wins | Ties | Sign-test p |
|---|---:|---:|---:|---:|---:|
| gptoss | 100 | 54 | 1 | 45 | 0.0 |
| nemotron120-remote | 100 | 59 | 2 | 39 | 0.0 |
| claude-opus-4-8 | 0 | 0 | 0 | 0 | 1.0 |
| gpt-5.5 | 100 | 100 | 0 | 0 | 0.0 |
| **overall** | 300 | 213 | 3 | 84 | 0.0 |

### Per-backend, per-arm report-row pass counts and mean tier

**Report-rows fully redacted** = judge scored the row and found zero residual PHI escapes. **Mean tier** is the attempt-level command ladder (1–5), averaged across repeats.

| Backend/arm | Report-rows fully redacted | Mean tier (attempt) |
|---|---:|---:|
| gptoss/with | 99/100 (99%) | 5.0 |
| gptoss/without | 45/100 (45%) | 5.0 |
| nemotron120-remote/with | 98/100 (98%) | 5.0 |
| nemotron120-remote/without | 40/100 (40%) | 5.0 |
| claude-opus-4-8/unaided | 0/0 (n/a) | 4.0 |
| gpt-5.5/unaided | 0/0 (n/a) | 4.0 |
| gpt-5.5/with | 94/100 (94%) | 5.0 |
| gpt-5.5/without | 0/100 (0%) | 5.0 |

## PHI redaction (row-level)

### LLM-as-judge residual escapes (primary) — judge model `openai/gpt-oss-120b`

An independent model re-read each anonymized report and flagged residual PHI — real identifying values still present as plain text rather than a `[bracketed]` placeholder. This is the primary escape metric; the deterministic scan below is a conservative cross-check.

| Backend / arm | Reports fully redacted (of dataset, per backend) | Residual PHI escapes (items) | Example escaped values |
|---|:--:|--:|---|
| gpt-5.5/with | 94/100 | 6 | M, Boston, MA 02115, 08:30 AM, ABCD, 09:30 AM, S. Patel |
| gpt-5.5/without | 0/100 | 1115 | Ethan M. Klein, 30876543210, March 9, 1971, 52, Female, October 22, 2023 at 02:47 PM |
| gptoss/with | 99/100 | 10 | Buchanan, Raoul, Gao, Victor, Milán, Milan |
| gptoss/without | 45/100 | 105 | A., L., S., T., K., M. |
| nemotron120-remote/with | 98/100 | 11 | Mercy General Hospital, Raoul, Baxter, Arthur, Karla, Milan |
| nemotron120-remote/without | 40/100 | 122 | A., S., M., L., K., T. |

#### Per-report residual PHI escape counts — one row per dataset report (0 = fully redacted)

Each cell is the number of residual PHI items the judge found in that report under the given backend/arm (not a pass/fail; a report can hold several items).

| study_uid (report) | nemotron120-remote/with (items) | nemotron120-remote/without (items) | gptoss/with (items) | gptoss/without (items) | gpt-5.5/with (items) | gpt-5.5/without (items) | Escaped PHI values |
|---|---:|---:|---:|---:|---:|---:|---|
| `LEDW5KEMKI` | 0 | 3 | 0 | 0 | 0 | 11 | A., S., M., Ethan M. Klein, 30876543210, March 9, 1971, 52, Female, October 22, 2023 at 02:47 PM, CTP-2024-WXYZ, Dr. Sofia R. Sanchez PhD |
| `K67NPC32IW` | 0 | 0 | 0 | 0 | 0 | 10 | Aisha M. Hawthorne, 123456789, 04/20/1986, 38, non-binary, 10/05/2024, 20251103-00456, Dr. Rafael T. Caldwell |
| `FMH275ZEBD` | 0 | 0 | 0 | 0 | 0 | 11 | Aisha L. Khan, MR-452617, April 5, 1985, 43 years, non-binary, July 22, 2029, ACC‑8392745, Dr. Liam K. Patel MD |
| `436G6LTU2V` | 0 | 0 | 0 | 0 | 0 | 10 | Ethan T. Sullivan, 123456789, 04/10/1977, 46, F, October 3, 2023, 57-123890, Dr. Sofia Ramirez, DO |
| `CU6OXMT22Y` | 0 | 0 | 0 | 2 | 0 | 11 | A., L., Emily T. Hawthorne, 9574620134, Oct 22, 1975, 49, F, Dec 2, 2024, ACC-2025-CA27491, Dr. Sofia S. Kumar |
| `7EKH3TEF3P` | 0 | 3 | 0 | 3 | 1 | 13 | A., S., L., M, Derek H. Bennett, MR1236789K-ABCD, September 5 1979, 44, Female, June 3, ACC‑MRL00987-BRZT-QQRS |
| `ACHZXGZU77` | 0 | 0 | 0 | 0 | 0 | 12 | Ethan B. Kline, MRN-483920, March 10, 1960, 63, female, October 12, 2023, ACC-374829QJLM, October 15, 2023 |
| `AU2GAYT5JW` | 0 | 1 | 0 | 0 | 0 | 12 | S., Carlos B. Rodriguez, 9876543210, March 3, 1979, 45, female, October 15, 2024, October 16, 2024, MRI-2024-ZYXW321 |
| `OEUY6K2K77` | 0 | 2 | 0 | 0 | 0 | 11 | L., K., Miguel L. Khan, 2022-483210, February 20, 1982, 42, XY, April 10, 2024, XR-20250615-CD34, Dr. Sofia S. Bennett |
| `IK2WYQBYPT` | 0 | 0 | 0 | 0 | 0 | 9 | St. Joseph Medical Center, CA2026-CT-12345, Ethan Hawthorne, 8392745621, May 5, 1970, 53, F, April 20, 2024 |
| `SJ37X6XW72` | 0 | 0 | 0 | 1 | 0 | 12 | T., River Valley Health Institute, Ethan K. Khan, 302918475, June 03, 1966, 57, Female, February 10, 2024 at 2:47 PM, BRC-20251234 |
| `XDJXLUHDQG` | 0 | 3 | 0 | 2 | 0 | 12 | A., S., K., Michael K. Hernandez, 56283914, 04/22/1952, 71, F, Dr. Sofia S. Kumar, DO, ACC-274856, River Valley Medical Center |
| `QNUTQMIU2B` | 0 | 2 | 0 | 3 | 0 | 13 | M., K., A., David T. Ramirez, 54321987, 03/10/1990, 34 y/o, non-binary, 07/15/2024, RAD-2025-1234, Dr. Aisha M. Sharma |
| `22FM453NW2` | 0 | 2 | 0 | 1 | 0 | 10 | S., T., A., David J. Patel, MR-3421087, May 3, 1955, Age 68, female, April 12, 2024, MRIX-2024-004321, Dr. Laura M. Whitaker Ph.D. |
| `WFYMA52DCS` | 0 | 0 | 0 | 1 | 0 | 8 | S., Carlos H. Patel, 3087629451, May 5, 1959, 63-year-old, Female, February 3, 2023, ACC-20231205-QWERT9, Dr. Sofia S. Khan MD |
| `6S4NVLDXOZ` | 0 | 1 | 0 | 0 | 0 | 11 | L., Luis C. Khan, 2025-2748391, April 3, 1972, 50, F, Feb 10, 2023, B‑HIJKLMN, Dr. Sofia K. Nguyen DO |
| `7GGZEIB4QU` | 0 | 2 | 0 | 2 | 0 | 8 | A., L., Miguel A. Khan, 9876543210, March 3, 1947, 76-year-old, female, October 12, 2023, ACC-20241234, Dr. Sofia S. Nguyen |
| `AMIPG5YJF3` | 0 | 0 | 0 | 1 | 0 | 12 | K., Olivia L. Wang, 123456789, June 10, 1979, June 10 1979, 45-year-old, non-binary, B-839201Y, Dr. Nina K. Patel |
| `6A4V2YI2E2` | 0 | 2 | 0 | 0 | 1 | 12 | L., K., Boston, MA 02115, Michael J. Thompson, 34219876, March 10, 1972, F, 52 years old, April 10, 2024, April 11, 2024, MR-202609542 |
| `ZNTAUPKWB6` | 0 | 3 | 0 | 0 | 0 | 9 | R., M., K., Arjun H. Khan, 83920145, July 8, 1975, 48-year-old, female, BCH-20231215-3742, October 15, 2023, Riverbend Medical Center – Department of Cardiology |
| `KJCKMLRVZR` | 0 | 1 | 0 | 0 | 0 | 11 | K., David S. Bennett, 1234567890, April 5, 1970, 54-year-old, female, October 21, 2024, ACC-2024-GLX-00123, Dr. Sofia J. Kumar |
| `O3HAQUTWTT` | 0 | 0 | 0 | 1 | 0 | 11 | S., River Valley Health Hospital, Sofia R. Hawthorne, 8374521906, July 23, 1968, 68, Non-binary, September 12, 2025; 2:47 PM, BXR-2027-QL12JTP |
| `MDMLXIRZEU` | 0 | 1 | 0 | 2 | 0 | 10 | L., A., Jordan A. Khan, MR-123456789, June 5, 1960, Male, 64 years old, October 22, 2024, ACC-20241022-47386, Dr. Luis S. Gonzalez, DO |
| `BRFDAVKDUK` | 0 | 1 | 0 | 0 | 0 | 11 | L., Sofia R. Patel, 5274930186, March 8, 1979, non-binary, 45‑year‑old, B-2025-XYZAB-PQR, Dr. David M. Kumar PhD |
| `QEKJA43MID` | 0 | 3 | 0 | 0 | 0 | 10 | A., S., L., Emily R. Kline, 57283914, April 22, 1970, 54, non-binary, June 15, 2024, B-572914, Dr. David L. Hernandez Ph.D. |
| `X447J6SJA4` | 0 | 0 | 0 | 0 | 0 | 10 | Evelyn A. Sullivan, 87654321, 06/10/1979, 46 years, Male, 07/12/2025, ACC-20250712-00988, Dr. Megan M. Kumar |
| `LOE5JFQ2SK` | 0 | 1 | 0 | 1 | 0 | 10 | A., L., Robert T. Hawkins, MRN-842761, July 12, 1976, 46, F, April 20, 2023, B-123456, Dr. David R. O'Connor |
| `NHVZACGDDD` | 0 | 3 | 0 | 0 | 0 | 67 | A., R., L., October 5, 2025, Caroline M. Tran, MR2468101, 02/15/1970, 55, Non-binary, ACC-2025-9876 |
| `PK7FUITYJB` | 0 | 2 | 0 | 0 | 0 | 12 | J., K., Michael Thompson, 9876543210, April 2, 1979, 45, female, August 15, 2024, XYZ-2025-ABC-12345, Dr. David Singh |
| `PDVUNDD6B4` | 0 | 2 | 0 | 2 | 0 | 11 | A., K., Darren L. Anderson, Z9Y8X7W6V5U4T3S2R1Q0, 02/10/1979, 45 y/o, Female, April 20, 2024, ACCN-9876543, Dr. Sofia K. Khan DO |
| `JSKWGROOL6` | 0 | 1 | 0 | 1 | 0 | 10 | A., Javier R. Patel, MRN 1234567890, June 20, 1971, 52-year-old, female, November 5, 2023, BCT-2024-NOV-009876, Dr. Sofia Hernandez |
| `NKDU3AB3OW` | 0 | 1 | 0 | 0 | 0 | 10 | 12345678, Miguel R. Hernandez, 839201456, 05/21/1975, 48, F, 09/15/2023, ACC-20230915-7421, Dr. Sofia L. Singh |
| `C5YRIDV2AQ` | 0 | 2 | 0 | 2 | 0 | 11 | A., S., Sofia J. Baker, 5274930186, April 12, 1975, 49, non-binary, October 22, 2024, 02:45 PM, MRN-2024-OCT-0123 |
| `GUJVGFQOGY` | 1 | 0 | 0 | 2 | 0 | 9 | Mercy General Hospital, A., L., David L. Bennett, MR76128493, 07/03/1979, 45, female, 08/15/2024, ACC2025-092134, Dr. Emily K. Sanchez |
| `NL3EHOYBAE` | 0 | 2 | 0 | 1 | 0 | 10 | A., L., David L. Brown, MRN-842761, June 2, 1977, 46, Female, October 3, 2023, ACC-2024-009876, Prof. Laura K. Garcia |
| `ETD4TTHH5R` | 0 | 0 | 0 | 0 | 0 | 10 | Isabella J. Patel, 1234567890, July 20, 1975, 49-year-old, Male, July 15, 2024, MIR-20240715, Dr. Victor T. Hawthorne |
| `6MZ3GCEA7V` | 0 | 0 | 0 | 2 | 0 | 11 | A., L., Ethan J. Morrison, 1234509876, April 3, 1973, 52, Female, April 5, 2025, April 7, 2025, MR-2025-MRVELOCITY-11223 |
| `ROHFA7WRPY` | 0 | 0 | 0 | 0 | 0 | 10 | Ethan A. Bennett, MR-05837492, June 12, 1978, 46, Female, November 12, 2024 at 07:42 AM, ACC-2025-NOV09-4821, Dr. Sofia R. Gonzalez |
| `7PODNY5AKV` | 0 | 3 | 0 | 2 | 0 | 11 | A., S., T., Laura Khan, MRN-123456789, July 15, 1977, 48, Male, September 3, 2025, September 4, 2025, ACC-2025-91734 |
| `YA4FOVXGTU` | 0 | 3 | 0 | 2 | 0 | 12 | A., S., T., Liam A. Khan, MRN-8427619, March 14, 1963, 61, female, July 15, 2024, ACC-24-075891, Dr. Ana S. Patel, DO |
| `BGYCAWNBSQ` | 0 | 2 | 0 | 1 | 0 | 11 | D., K., Michael A. Baker, 8427613950, February 22, 1972, 52, female, April 05, 2024, April 07, 2024, B-20240515-HEART-CT |
| `I3Y7Y4ZUQX` | 0 | 0 | 0 | 2 | 0 | 11 | A., S., Carlos McKenzie, 8427613950, Mar 22, 1975, 49, Female, Oct 15, 2024, ACC-2024-OCT-XYZAB7 |
| `L5FZEIJ6DP` | 0 | 1 | 0 | 0 | 1 | 14 | P., 08:30 AM, Luis A. Khan, MRN-58730241, March 3, 1953, Age 72, Female, April 2, 2025, April 3, 2025 at 08:30 AM, ACC-2024JUN8625 |
| `Y2RGCGWLCR` | 0 | 1 | 0 | 0 | 0 | 11 | L., Morrison, Sofia K., H09876543, 07/23/1979, 45, M, 02/09/2025, 02/11/2025, ACR-2025-123456 |
| `MIRH5M4BUO` | 0 | 0 | 0 | 1 | 0 | 10 | L., Anita L. Mendoza, 2748195602, April 22, 1969, 55-year-old, male, November 3, 2024, C-594837D, Dr. Linda S. Patel |
| `G35MZWX6MW` | 0 | 0 | 0 | 0 | 0 | 10 | Emily K. Garcia, 87654321, July 8, 1972, 51, male, June 15, 2024, CT-2024-1234, Riverbend Community Hospital – Department of Radiology |
| `22SSMT5XRP` | 0 | 1 | 0 | 1 | 0 | 14 | K., River Valley Community Hospital, Imaging Services Division, Laura Hernandez, 317452689, April 12, 1984, 40, non-binary, July 8, 2024 |
| `FUIX3GJQVT` | 0 | 0 | 0 | 0 | 0 | 9 | Samuel A. Harper, MRN-567890, June 22, 1977, 48 years, Female, September 12, 2025, CT-2025-11234, Dr. Rosa M. Mendoza |
| `PGOL5TMHPT` | 0 | 2 | 0 | 0 | 0 | 10 | A., K., Isabel R. Sanchez, June 3, 1975, 48, Male, #874-321‑652, B7G9M2KQXWJYZNT, Dr. Sebastian K. Vargas, DO, Lakeside Community Medical Center |
| `FKFAP3XE63` | 0 | 2 | 0 | 0 | 0 | 11 | S., L., Emily A. Hawthorne, 59382014, 06/20/1979, 46, F, 08/15/2025, 08/16/2025, BCR-2026-12345 |
| `GJSPMUIPO7` | 0 | 2 | 0 | 1 | 0 | 12 | A., K., Isabel L. Gonzalez, 1234567890, 04/22/1968, 56, non-binary, 09/02/2024, 09/03/2024, CT-2025-1589 |
| `NECRNLCKBM` | 0 | 1 | 0 | 1 | 0 | 11 | K., Isabella R Kumar, 30857291, 06/20/1974, 49, male, September 30, 2023, Dr. Victor J Bennett DO, St. Gabriel Health Institute - Department of Radiology (SMC) |
| `GXAHBWJVHR` | 0 | 0 | 0 | 0 | 0 | 12 | River Valley Medical Center, Neurology Imaging Service, Carlos J. Khan, 8427613951, March 22, 1978, Age 46, Female, July 15, 2024 |
| `ONV7HXCGO4` | 0 | 3 | 0 | 2 | 0 | 10 | A., S., M., Isabella J. Rodriguez, N7654321, 04/05/1974, 50, Non-binary, October 12, 2024, LM34OP-DEC25YZ, Dr. Javier T. Ramirez MD |
| `3KYTSFYIMD` | 0 | 0 | 0 | 2 | 0 | 12 | S., B., Riverbend University Hospital, Samuel B. Kline, MR-543210987, July 12, 1966, Age ~58, Female, Age approx 58, ACC-83927461 |
| `RWG3JIRROH` | 0 | 0 | 0 | 3 | 0 | 10 | A., R., L., David B. Thompson, 3098745621, July 9, 1978, 45, Female, April 22, 2024, MR‑57WXYZ‑1234, Prof. Laura M. Bennett |
| `ZMTTPRZ6QG` | 0 | 2 | 0 | 2 | 0 | 10 | A., L., Olivia A. Khan, 9876543210, August 15, 1978, 45, non-binary, July 12, 2024, IMG-20240712-007, Dr. Aisha K. Rossi |
| `WWJQ775N3D` | 0 | 0 | 0 | 1 | 0 | 11 | M., Evelyn L. Klein, 5938471205, March 22, 1966, 58 years, non-binary, July 15, 2024, 2025-562839QWERTYUIOPASDFGHJKLZXCVBNMNBVCXZLKJHGFDSAPOIUYTREWQ, Dr. Laura K. Gonzalez |
| `BEBHGQ5EQL` | 0 | 0 | 0 | 0 | 0 | 10 | Sofia R. Garcia, 2025-123456, April 20, 1979, Age 45, Male, September 15, 2024, September 17, 2024, MRI-2025-APR12 |
| `AQYTP7COY6` | 0 | 1 | 0 | 0 | 0 | 10 | A., Robert A. Brown, 2748563190, March 12, 1958, non-binary, ~66 years, July 14, 2024 at 02:47 PM, ACC-594817, Dr. Laura R. Shah Ph.D. |
| `LLD73AQGHD` | 0 | 0 | 0 | 0 | 1 | 11 | ABCD, St. Augustine Health Institute, Linda K. Hernandez, 07/09/1950, 74, M, B9Y-4W-FGHI, LQTX‑2025‑WXYZ, Dr. Ethan K. Bennett, PhD |
| `UQSDQURM55` | 0 | 1 | 0 | 3 | 0 | 10 | 12345678, A., R., L., Ethan B. Harper, 04/15/1952, 71, MR-5827341, Female, April 5, 2024, ACC-2025APR-02368, Dr. Sofia K. Gonzalez |
| `FMBGDRQYXV` | 0 | 2 | 0 | 1 | 0 | 10 | A., R., Isabella M. Klein, XY12398765, February 2, 1960, 63‑year‑old male, December 5, 2023, CT-2024-DEC-CT-56231, Dr. Derek K. Lang, Riverbend Community Hospital – Division of Nuclear Medicine |
| `C7TIZGYADQ` | 0 | 1 | 0 | 1 | 0 | 13 | L., Arthur K. Bennett, 5432109876, April 10, 1962, 62 y/o, Female, August 15, 2024, August 16, 2024, ACN-839274156 |
| `6XUDBZKKTM` | 0 | 0 | 0 | 3 | 0 | 11 | A., R., L., Laura R. Bennett, 3079-56284, June 20, 1985, 39, non-binary, October 28, 2024, B2025-1215-QLMNP8R, Dr. Natalie L. Hawthorne |
| `MFV4GF7LIF` | 0 | 0 | 0 | 0 | 0 | 11 | Michael A. Anderson, 0987654321, 04/22/1979, 45-year-old, female, 08/15/2024, ACC-20240815-0456, Dr. Emily M. Patel |
| `BBCHW5SF4J` | 0 | 0 | 0 | 2 | 0 | 11 | M., K., Ethan K. Anderson, 2029-009876, April 15, 1967, 57 y/o, Female, April 2, 2025, April 3, 2025, ACC-2029-MR-9876543 |
| `CCBX25ECBM` | 0 | 2 | 0 | 0 | 0 | 9 | R., L., Mark B. Khan, MRN-842761, June 3, 1986, October 2, 2024, XR2025-1023-WXYZ, Dr. Sofia S. O'Connor, Northbridge Health Institute, October 3, 2024 |
| `GE6K2YM5T4` | 0 | 2 | 0 | 1 | 0 | 11 | A., L., Ethan K. Khan, 123456789, 04/15/1955, 68, female, April 12, 2024, April 14, 2024, ACC-2024-05467 |
| `7AHYUATI4R` | 0 | 0 | 0 | 0 | 0 | 9 | Aisha K. Patel, 87453120, July 14, 1982, 42, Non-binary, October 3, 2024, MR-20241003-00987, Dr. Nina M. Gomez |
| `GZTPLLLF7R` | 0 | 1 | 0 | 1 | 1 | 8 | K., 09:30 AM, Cedarbrook Regional Hospital, 9876543210, March 22, 1979, Isabella M. Ramirez, BD-2025-ABC31G, September 12, 2024 at 08:45 AM, Dr. Victor K. Park, Dr. Sofia K. Shah |
| `EWPUFAZAAV` | 0 | 1 | 0 | 1 | 0 | 11 | K., Isabella T. Sanchez, J54321987, 06/10/1975, 48-year-old, Female, 04/20/2024, CT-ACN‑73592KLM, Dr. Sofia S. Tran, Ph.D. |
| `DLTEY2MQVL` | 0 | 2 | 0 | 3 | 0 | 10 | S., R., A., River Valley Health Institute, Laura K. Bennett, MRN-527839, 03/20/1979, 45, Male, 12/01/2024, RVHI-20241201-0098 |
| `ZK2DGSJGSN` | 0 | 1 | 0 | 1 | 0 | 11 | K., David B. McKenzie, Z987654321, March 3, 1966, 58, female, July 12, 2024, July 13, 2024, BWH-2025-0421 |
| `2CWQFZHPFV` | 0 | 3 | 0 | 0 | 0 | 11 | A., S., T., Laura B. Kumar, 123456789, June 15, 1972, 52, Non-binary, July 22, 2024, ACC-20240722-00987, Dr. David K. Ramos |
| `N76Y22WYFI` | 0 | 0 | 0 | 2 | 0 | 11 | D., R., Aaron K. Hawthorne, 3029184756, August 22, 1976, 47, female, April 22, 2024, CT-20231205-WXYZ123, Dr. Sofia R. Nguyen |
| `OCGQY46ONG` | 0 | 0 | 0 | 2 | 0 | 9 | A., L., Sofia R. Hernandez, MR1234567890, 02/03/1969, 55 y/o, Male, November 15, 2024, ACC-20251115-01234, Dr. David K. Singh |
| `D536YE4BQ2` | 0 | 0 | 0 | 0 | 0 | 10 | Sofia J. Morgan, 2031-751842, April 2, 1982, 45, Non-binary, July 22, 2023, ACC-20231201-00987, Dr. David T. Kumar |
| `LLXS72VUYL` | 0 | 2 | 0 | 2 | 0 | 11 | A., B., Miguel R. Sanchez, MRN-8427619, April 5, 1971, 53 years, Female, February 10, 2025, ACC-20250210-0571, Dr. Clara L. Vargas |
| `ALN2WDBET6` | 0 | 3 | 0 | 2 | 0 | 10 | A., S., L., Sofia L. Martinez, MR123456789, 08/19/1968, 55, non-binary, April 15, 2024, Z-112233-X, Dr. Victor K. Kumar PhD |
| `QIUCOE4NOK` | 0 | 0 | 0 | 0 | 0 | 8 | Mjulian M. Patel, 2025-123456, April 10, 1979, April 10, 2024, CT-2025-XYZR00987, Dr. Victor Patel, St. Hope Health Institute, Dr. Megan M. Keller, DO |
| `QM6YCKGEGJ` | 0 | 0 | 0 | 0 | 0 | 10 | David J. Kumar, 12345678, April 8, 1979, female, June 20, 2025, B-839104, Dr. Laura M. Bennett, Dr. Ethan K. Sanchez DO |
| `H3SFUMTJZS` | 0 | 3 | 0 | 0 | 0 | 9 | A., S., L., Samuel A. Baker, CLIN-2025-06789, 04/12/1979, 45, Female, October 28, 2024, PET-CT-2025-0421, Dr. Karen L. Singh |
| `RYZMGQ7CSH` | 0 | 2 | 0 | 2 | 0 | 12 | A., S., Laura A. Khan, MRN-8427615, February 3, 1961, 63-year-old, non-binary, December 2, 2024, CT-2025-WXYZ123, Dr. Sofia S. Patel |
| `QH63XB2N64` | 0 | 0 | 0 | 3 | 0 | 11 | A., R., L., Emily A. Anderson, MRN-9876543210, 04/20/1979, 44 y/o, Male, June 12, 2024, ACC-2024-MR-98765, Dr. Sofia L. Khan |
| `WJVRWKP3GB` | 0 | 3 | 0 | 3 | 0 | 9 | A., S., L., Liam B. Hawthorne, 2022-345678, March 8, 1979, 44 years, non-binary, October 15, 2023, ACC‑2022123456, Dr. Sofia S. Khan Ph.D. |
| `I4JSFZVLIY` | 0 | 0 | 0 | 2 | 0 | 11 | R., S., Alex T. Sanchez, ZX309124, May 23, 1979, 44, non-binary, July 12, 2023, ACC-20231201-00456, Dr. Ravi S. Desai |
| `JQD5XDVNFN` | 0 | 2 | 0 | 3 | 0 | 8 | S., L., A., Ethan R. Kline, 5873129045, July 14, 1982, Female, February 12, 2024, NLM-2025-01987, Riverbend Health Institute, Dr. Sofia L. Sullivan |
| `V3MB6QTN5L` | 0 | 2 | 0 | 1 | 0 | 10 | A., K., Sofia R. Hawthorne, 123098765, June 10, 1973, 52, female, October 5, 2025, ACC-20251115-5678, Dr. Nina K. Singh |
| `MAZLO6VUUZ` | 0 | 0 | 0 | 0 | 0 | 12 | Robert B. Gomez, J2023-594837, April 15, 1963, 62 years, Female, July 12, 2025, July 14, 2025, CASE-2026-159842 |
| `PMDGCSYGYH` | 0 | 2 | 0 | 1 | 0 | 10 | A., L., Carlos A. Rivera, 8456723091, June 12, 1965, 58 years, Female, April 14, 2024, B2024-7890, Dr. Laura S. Singh |
| `YHF4DC6OH4` | 0 | 3 | 0 | 0 | 0 | 10 | A., S., T., Luis K. Hernandez, 84567290, 02/20/1968, 56-year-old, non-binary, 07/15/2024, MRI2024-001234, Dr. Sofia S. Kumar, PhD |
| `F77VOEHBM2` | 0 | 0 | 0 | 0 | 0 | 10 | Riverbend Community Medical Center, Isabella L. Lopez, J57210458, April 12, 1977, Age ~47 years old, Male (Male), May 20, 2024, June 15, 2024 |
| `TE4RHTSNYW` | 0 | 4 | 0 | 0 | 0 | 11 | A., 12345678, S., L., Ethan K. Harper, 7423951, 03/22/1979, 44, F, 09/08/2023, CT-ANGIO-MAY-NE, Dr. Sofia H. Patel |
| `RJ5DRKT4MB` | 0 | 3 | 0 | 3 | 0 | 11 | A., S., L., Ethan M. Baker, 5271948603, June 3, 1967, 57-year-old, female, April 22, 2025, ACC-2025-009321, Dr. Olivia T. Kim MD |
| `46L3QAKRDC` | 0 | 2 | 0 | 3 | 1 | 10 | A., L., R., S. Patel, David Bennett, 872345019, May 22, 1956, ~68, female, August 15, 2024, SRG-20240720-WXYZ, Dr. Sofia R. Singh |
| `2F6IQCJRLM` | 0 | 0 | 0 | 0 | 0 | 10 | Carlos Garcia, 1234567-9, June/15/1977, 46, F, October 2, 2023, BQT-4321YX, Dr. Sofia Patel |
| `HKKU3TXVXQ` | 10 | 5 | 10 | 8 | 0 | 10 | Raoul, Baxter, Arthur, Karla, Milan, Frederic, Dario, Josh, Henry, Buchanan, Gao, Victor |
| `XJWBR3P2FC` | 0 | 0 | 0 | 0 | 0 | 10 | Natalia K. Bennett, 573920148-ZQY, April 15, 1963, Male, 62 years old, November 12, 2025, ACC-ONCO-JAN2026-ABC12LM, Dr. Priya R. Kumar |
| `OLXVP6F6VH` | 0 | 2 | 0 | 0 | 0 | 12 | A., S., Elena L. Martinez, MRN-842761, 09/15/1965, Age 58, non-binary, 08/22/2024, 08/23/2024, MRC-20240822-00456 |

### Deterministic scan (cross-check)

Conservative regex scan for residual PHI signals (numeric dates, prose dates, 5+ digit IDs, `Dr./Prof./Mr./Mrs./Ms.` + name, phones), excluding `[PLACEHOLDER]` tokens. Middle initials and bare institution names are not counted, so this under-reports rather than over-reports.

### Per-arm residual summary

| Backend/arm | Rows fully redacted | Residual PHI escapes | Baseline PHI in input | Escape types |
|---|---:|---:|---:|---|
| claude-opus-4-8/unaided | n/a | n/a | n/a | (no anonymized output produced) |
| gpt-5.5/unaided | n/a | n/a | n/a | (no anonymized output produced) |
| gpt-5.5/with | 91/100 | 9 | 602 | long_id=1, titled_name=8 |
| gpt-5.5/without | 0/100 | 604 | 602 | date_numeric=52, date_prose=208, long_id=157, titled_name=187 |
| gptoss/with | 100/100 | 0 | 620 | none |
| gptoss/without | 93/100 | 7 | 620 | titled_name=7 |
| nemotron120-remote/with | 100/100 | 0 | 620 | none |
| nemotron120-remote/without | 93/100 | 7 | 620 | long_id=3, titled_name=4 |

### Per-row residual escape counts (0 = fully redacted)

| study_uid | input PHI | nemotron120-remote/with | nemotron120-remote/without | gptoss/with | gptoss/without | gpt-5.5/with | gpt-5.5/without | Escaped values (regex) |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `LEDW5KEMKI` | 8 | 0 | 0 | 0 | 0 | 0 | 6 | March 9, 1971, October 22, 2023, 30876543210, Dr. Sofia, Dr. Leila |
| `K67NPC32IW` | 4 | 0 | 0 | 0 | 0 | 0 | 7 | 04/20/1986, 10/05/2024, 123456789, 20251103, 00456, Dr. Rafael |
| `FMH275ZEBD` | 7 | 0 | 0 | 0 | 0 | 0 | 6 | April 5, 1985, July 22, 2029, 452617, 8392745, Dr. Liam |
| `436G6LTU2V` | 6 | 0 | 0 | 0 | 0 | 0 | 6 | 04/10/1977, October 3, 2023, 123456789, 123890, Dr. Sofia, Dr. Arjun |
| `CU6OXMT22Y` | 6 | 0 | 0 | 0 | 0 | 0 | 3 | 9574620134, Dr. Sofia, Dr. Darren |
| `7EKH3TEF3P` | 5 | 0 | 0 | 0 | 0 | 0 | 3 | September 5 1979, Dr. Marissa, Dr. Victor |
| `ACHZXGZU77` | 8 | 0 | 0 | 0 | 0 | 0 | 7 | March 10, 1960, October 12, 2023, October 15, 2023, 483920, Dr. Grace |
| `AU2GAYT5JW` | 5 | 0 | 0 | 0 | 0 | 0 | 6 | March 3, 1979, October 15, 2024, October 16, 2024, 9876543210, Dr. Isabella, Dr. Wei |
| `OEUY6K2K77` | 6 | 0 | 0 | 0 | 0 | 0 | 6 | February 20, 1982, April 10, 2024, 483210, 20250615, Dr. Sofia, Dr. Aisha |
| `IK2WYQBYPT` | 5 | 0 | 0 | 0 | 0 | 0 | 5 | May 5, 1970, April 20, 2024, 12345, 8392745621, Dr. Victor |
| `SJ37X6XW72` | 9 | 0 | 0 | 0 | 0 | 0 | 8 | June 03, 1966, February 10, 2024, December 12, 2023, 302918475, 20251234 |
| `XDJXLUHDQG` | 9 | 0 | 0 | 0 | 0 | 0 | 8 | 04/22/1952, April 15, 2024, August 20, 2022, 56283914 |
| `QNUTQMIU2B` | 7 | 0 | 0 | 0 | 0 | 0 | 6 | 03/10/1990, 07/15/2024, 07/16/2024, 54321987, Dr. Aisha, Dr. Victor |
| `22FM453NW2` | 5 | 0 | 0 | 0 | 0 | 1 | 6 | Dr. Institution, May 3, 1955, April 12, 2024, 3421087, 004321, Dr. Laura |
| `WFYMA52DCS` | 5 | 0 | 0 | 0 | 0 | 0 | 5 | May 5, 1959, February 3, 2023, 3087629451, 20231205, Dr. Sofia |
| `6S4NVLDXOZ` | 7 | 0 | 0 | 0 | 0 | 0 | 5 | April 3, 1972, March 14, 2023, 2748391, Dr. Sofia, Dr. David |
| `7GGZEIB4QU` | 5 | 0 | 0 | 0 | 0 | 0 | 5 | March 3, 1947, October 12, 2023, 9876543210, 20241234, Dr. Sofia |
| `AMIPG5YJF3` | 7 | 0 | 0 | 0 | 0 | 0 | 7 | June 10, 1979, June 10 1979, September 5, 2024, September 6, 2024, 123456789, Dr. Nina |
| `6A4V2YI2E2` | 5 | 0 | 0 | 0 | 0 | 1 | 8 | 02115, March 10, 1972, April 10, 2024, April 11, 2024, 34219876, 202609542, 97201 |
| `ZNTAUPKWB6` | 7 | 0 | 0 | 0 | 0 | 0 | 5 | July 8, 1975, October 15, 2023, 83920145, 20231215, Dr. Sofia |
| `KJCKMLRVZR` | 7 | 0 | 0 | 0 | 0 | 0 | 6 | April 5, 1970, October 21, 2024, 1234567890, 00123, Dr. Sofia, Dr. Ethan |
| `O3HAQUTWTT` | 7 | 0 | 0 | 0 | 0 | 0 | 6 | July 23, 1968, September 12, 2025, April 2, 2023, 8374521906, Dr. Luis, Dr. Victor |
| `MDMLXIRZEU` | 7 | 0 | 1 | 0 | 1 | 0 | 7 | Dr. Institution, June 5, 1960, October 22, 2024, 123456789, 20241022, 47386 |
| `BRFDAVKDUK` | 5 | 0 | 1 | 0 | 1 | 0 | 5 | Dr. Institution, March 8, 1979, October 22, 2024, 5274930186, Dr. David, Dr. Liam |
| `QEKJA43MID` | 7 | 0 | 0 | 0 | 0 | 0 | 6 | April 22, 1970, June 15, 2024, 57283914, 572914, Dr. David, Dr. Sofia |
| `X447J6SJA4` | 6 | 0 | 0 | 0 | 0 | 0 | 7 | 06/10/1979, 07/12/2025, 87654321, 20250712, 00988, Dr. Megan |
| `LOE5JFQ2SK` | 5 | 0 | 0 | 0 | 0 | 0 | 6 | July 12, 1976, April 20, 2023, 842761, 123456, Dr. David, Dr. Sofia |
| `NHVZACGDDD` | 8 | 0 | 0 | 0 | 0 | 0 | 26 | 02/15/1970, October 5, 2025 |
| `PK7FUITYJB` | 8 | 0 | 1 | 0 | 1 | 0 | 7 | Dr. Institution, April 2, 1979, August 15, 2024, 9876543210, 12345, Dr. David |
| `PDVUNDD6B4` | 5 | 0 | 0 | 0 | 0 | 1 | 6 | Dr. Institution, 02/10/1979, April 20, 2024, 9876543, Dr. Sofia, Dr. Liam |
| `JSKWGROOL6` | 5 | 0 | 0 | 0 | 0 | 0 | 6 | June 20, 1971, November 5, 2023, 1234567890, 009876, Dr. Sofia, Dr. Ethan |
| `NKDU3AB3OW` | 6 | 0 | 1 | 0 | 0 | 0 | 5 | 12345678, 05/21/1975, 09/15/2023, 839201456, 20230915, Dr. Sofia |
| `C5YRIDV2AQ` | 7 | 0 | 0 | 0 | 0 | 0 | 5 | April 12, 1975, October 22, 2024, 5274930186, Dr. Aisha, Dr. Megan |
| `GUJVGFQOGY` | 7 | 0 | 0 | 0 | 0 | 0 | 4 | 07/03/1979, 08/15/2024, 092134, Dr. Emily |
| `NL3EHOYBAE` | 7 | 0 | 0 | 0 | 1 | 0 | 6 | Dr. Institution, June 2, 1977, October 3, 2023, 842761, 009876, Prof. Laura, Prof. Thomas |
| `ETD4TTHH5R` | 4 | 0 | 0 | 0 | 0 | 0 | 6 | July 20, 1975, July 15, 2024, 1234567890, 20240715, Dr. Victor, Dr. Sofia |
| `6MZ3GCEA7V` | 7 | 0 | 0 | 0 | 0 | 0 | 7 | April 3, 1973, April 5, 2025, April 7, 2025, 1234509876, 11223, Dr. Sofia |
| `ROHFA7WRPY` | 5 | 0 | 0 | 0 | 0 | 0 | 5 | June 12, 1978, November 12, 2024, 05837492, Dr. Sofia, Dr. Luis |
| `7PODNY5AKV` | 4 | 0 | 0 | 0 | 0 | 0 | 7 | July 15, 1977, September 3, 2025, September 4, 2025, 123456789, 91734, Dr. David |
| `YA4FOVXGTU` | 7 | 0 | 0 | 0 | 0 | 0 | 7 | March 14, 1963, July 15, 2024, September 12, 2022, 8427619, 075891, Dr. Ana |
| `BGYCAWNBSQ` | 6 | 0 | 0 | 0 | 0 | 0 | 7 | February 22, 1972, April 05, 2024, April 07, 2024, 8427613950, 20240515, Dr. Sofia |
| `I3Y7Y4ZUQX` | 4 | 0 | 0 | 0 | 0 | 0 | 3 | 8427613950, Dr. Olivia, Dr. Isabella |
| `L5FZEIJ6DP` | 7 | 0 | 0 | 0 | 0 | 0 | 7 | March 3, 1953, April 2, 2025, April 3, 2025, 58730241, Dr. Sofia |
| `Y2RGCGWLCR` | 5 | 0 | 0 | 0 | 0 | 0 | 6 | 07/23/1979, 02/09/2025, 02/11/2025, 123456, Dr. Victor, Dr. Nina |
| `MIRH5M4BUO` | 4 | 0 | 0 | 0 | 1 | 0 | 5 | Dr. Institution, April 22, 1969, November 3, 2024, 2748195602, Dr. Linda, Dr. David |
| `G35MZWX6MW` | 7 | 0 | 0 | 0 | 0 | 0 | 5 | July 8, 1972, June 15, 2024, 87654321, Dr. Sofia, Dr. David |
| `22SSMT5XRP` | 6 | 0 | 0 | 0 | 0 | 0 | 7 | April 12, 1984, July 8, 2024, February 14, 2022, October 5, 2020, 317452689, 20240708 |
| `FUIX3GJQVT` | 7 | 0 | 1 | 0 | 1 | 0 | 6 | Dr. Institution, June 22, 1977, September 12, 2025, 567890, 11234, Dr. Rosa, Dr. Grace |
| `PGOL5TMHPT` | 7 | 0 | 0 | 0 | 0 | 0 | 4 | June 3, 1975, November 2, 2023, Dr. Sebastian, Dr. Sofia |
| `FKFAP3XE63` | 6 | 0 | 0 | 0 | 1 | 0 | 7 | Dr. Institution, 06/20/1979, 08/15/2025, 08/16/2025, 59382014, 12345, Dr. Sofia |
| `GJSPMUIPO7` | 5 | 0 | 0 | 0 | 0 | 0 | 6 | 04/22/1968, 09/02/2024, 09/03/2024, 1234567890, Dr. David, Dr. Natalie |
| `NECRNLCKBM` | 6 | 0 | 0 | 0 | 0 | 1 | 6 | Dr. Neurology, 06/20/1974, September 30, 2023, 30857291, 123456, Dr. Victor, Dr. Sofia |
| `GXAHBWJVHR` | 6 | 0 | 0 | 0 | 0 | 0 | 5 | March 22, 1978, July 15, 2024, 8427613951, Dr. Sofia, Dr. Wei |
| `ONV7HXCGO4` | 5 | 0 | 0 | 0 | 0 | 0 | 4 | 04/05/1974, October 12, 2024, Dr. Javier, Dr. Aisha |
| `3KYTSFYIMD` | 5 | 0 | 0 | 0 | 0 | 0 | 6 | July 12, 1966, June 03, 2022, 543210987, 83927461, Dr. David, Dr. Sofia |
| `RWG3JIRROH` | 7 | 0 | 0 | 0 | 0 | 0 | 5 | July 9, 1978, April 22, 2024, 3098745621, Prof. Laura, Prof. Emily |
| `ZMTTPRZ6QG` | 8 | 0 | 0 | 0 | 0 | 0 | 7 | August 15, 1978, July 12, 2024, February 23, 2021, 9876543210, 20240712, Dr. Aisha |
| `WWJQ775N3D` | 4 | 0 | 0 | 0 | 0 | 0 | 5 | March 22, 1966, July 15, 2024, 5938471205, Dr. Laura, Dr. Victor |
| `BEBHGQ5EQL` | 6 | 0 | 0 | 0 | 0 | 0 | 5 | April 20, 1979, September 15, 2024, September 17, 2024, 123456, Dr. Victor |
| `AQYTP7COY6` | 7 | 0 | 0 | 0 | 0 | 1 | 6 | Dr. Institution, March 12, 1958, July 14, 2024, 2748563190, 594817, Dr. Laura, Dr. David |
| `LLD73AQGHD` | 8 | 0 | 0 | 0 | 0 | 0 | 4 | 07/09/1950, March 12, 2023, Dr. Ethan, Dr. Veronica |
| `UQSDQURM55` | 7 | 0 | 1 | 0 | 0 | 0 | 6 | 12345678, 04/15/1952, April 5, 2024, 5827341, 02368, Dr. Sofia, Dr. Darren |
| `FMBGDRQYXV` | 8 | 0 | 0 | 0 | 0 | 0 | 6 | February 2, 1960, December 5, 2023, July 20, 2023, 56231, Dr. Derek, Dr. Sofia |
| `C7TIZGYADQ` | 7 | 0 | 0 | 0 | 0 | 0 | 8 | April 10, 1962, August 15, 2024, August 16, 2024, April 20, 2023, 5432109876, 839274156 |
| `6XUDBZKKTM` | 7 | 0 | 0 | 0 | 0 | 0 | 7 | June 20, 1985, October 28, 2024, April 12, 2024, 56284, Dr. Natalie |
| `MFV4GF7LIF` | 5 | 0 | 0 | 0 | 0 | 0 | 7 | 04/22/1979, 08/15/2024, February 14, 2024, 0987654321, 20240815, Dr. Emily |
| `BBCHW5SF4J` | 5 | 0 | 0 | 0 | 0 | 0 | 7 | April 15, 1967, April 2, 2025, April 3, 2025, 009876, 9876543, Dr. Sofia |
| `CCBX25ECBM` | 7 | 0 | 0 | 0 | 0 | 0 | 6 | June 3, 1986, October 2, 2024, October 3, 2024, 842761, Dr. Sofia, Dr. Nina |
| `GE6K2YM5T4` | 7 | 0 | 0 | 0 | 0 | 0 | 6 | 04/15/1955, April 12, 2024, April 14, 2024, 123456789, 05467, Dr. Sofia |
| `7AHYUATI4R` | 7 | 0 | 0 | 0 | 0 | 0 | 6 | July 14, 1982, October 3, 2024, 87453120, 20241003, 00987, Dr. Nina |
| `GZTPLLLF7R` | 7 | 0 | 0 | 0 | 0 | 0 | 5 | March 22, 1979, September 12, 2024, 9876543210, Dr. Victor, Dr. Sofia |
| `EWPUFAZAAV` | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 06/10/1975, 04/20/2024, Dr. Sofia, Dr. Rohan |
| `DLTEY2MQVL` | 6 | 0 | 0 | 0 | 0 | 1 | 6 | Dr. Reporting, 03/20/1979, 12/01/2024, 527839, 20241201, Dr. Victor, Dr. Natalie |
| `ZK2DGSJGSN` | 5 | 0 | 0 | 0 | 0 | 0 | 5 | March 3, 1966, July 12, 2024, July 13, 2024, Dr. Laura, Dr. Carlos |
| `2CWQFZHPFV` | 5 | 0 | 0 | 0 | 0 | 0 | 7 | June 15, 1972, July 22, 2024, 123456789, 20240722, 00987, Dr. David |
| `N76Y22WYFI` | 7 | 0 | 0 | 0 | 0 | 0 | 6 | August 22, 1976, April 22, 2024, 3029184756, 20231205, Dr. Sofia |
| `OCGQY46ONG` | 7 | 0 | 0 | 0 | 0 | 0 | 5 | 02/03/1969, November 15, 2024, 20251115, 01234, Dr. David |
| `D536YE4BQ2` | 5 | 0 | 0 | 0 | 0 | 0 | 7 | April 2, 1982, July 22, 2023, 751842, 20231201, 00987, Dr. David |
| `LLXS72VUYL` | 8 | 0 | 0 | 0 | 0 | 1 | 7 | Dr. Neurology, April 5, 1971, February 10, 2025, November 30, 2024, 8427619, 20250210, Dr. Clara |
| `ALN2WDBET6` | 7 | 0 | 0 | 0 | 0 | 1 | 5 | Dr. Institution, 08/19/1968, April 15, 2024, 112233, Dr. Victor, Dr. Nina |
| `QIUCOE4NOK` | 7 | 0 | 0 | 0 | 0 | 0 | 5 | April 10, 1979, April 10, 2024, 123456, Dr. Victor, Dr. Megan |
| `QM6YCKGEGJ` | 7 | 0 | 0 | 0 | 0 | 0 | 7 | April 8, 1979, June 20, 2025, 12345678, 839104, Dr. Laura, Dr. Ethan |
| `H3SFUMTJZS` | 5 | 0 | 0 | 0 | 0 | 0 | 5 | 04/12/1979, October 28, 2024, 06789, Dr. Karen, Dr. Victor |
| `RYZMGQ7CSH` | 9 | 0 | 0 | 0 | 0 | 0 | 7 | February 3, 1961, December 2, 2024, September 12, 2024, July 15, 2024, 8427615, Dr. Sofia |
| `QH63XB2N64` | 8 | 0 | 0 | 0 | 0 | 0 | 7 | 04/20/1979, June 12, 2024, April 10, 2024, 9876543210, 98765, Dr. Sofia |
| `WJVRWKP3GB` | 7 | 0 | 0 | 0 | 0 | 0 | 6 | March 8, 1979, October 15, 2023, 345678, 2022123456, Dr. Sofia, Dr. Darren |
| `I4JSFZVLIY` | 7 | 0 | 0 | 0 | 0 | 0 | 6 | May 23, 1979, July 12, 2023, May 20, 2022, 20231201, 00456, Dr. Ravi |
| `JQD5XDVNFN` | 7 | 0 | 0 | 0 | 0 | 0 | 5 | July 14, 1982, February 12, 2024, 5873129045, 01987, Dr. Sofia |
| `V3MB6QTN5L` | 4 | 0 | 0 | 0 | 0 | 0 | 5 | June 10, 1973, October 5, 2025, 123098765, 20251115, Dr. Nina |
| `MAZLO6VUUZ` | 7 | 0 | 0 | 0 | 0 | 0 | 7 | April 15, 1963, July 12, 2025, July 14, 2025, 594837, 159842, Dr. Emily |
| `PMDGCSYGYH` | 7 | 0 | 0 | 0 | 0 | 0 | 5 | June 12, 1965, April 14, 2024, 8456723091, Dr. Laura, Dr. David |
| `YHF4DC6OH4` | 7 | 0 | 0 | 0 | 0 | 0 | 6 | 02/20/1968, 07/15/2024, 84567290, 001234, Dr. Sofia, Dr. Carlos |
| `F77VOEHBM2` | 7 | 0 | 0 | 0 | 0 | 0 | 4 | April 12, 1977, May 20, 2024, June 15, 2024, Dr. Sofia |
| `TE4RHTSNYW` | 5 | 0 | 1 | 0 | 0 | 0 | 5 | 12345678, 03/22/1979, 09/08/2023, 7423951, Dr. Sofia, Dr. Victor |
| `RJ5DRKT4MB` | 6 | 0 | 0 | 0 | 0 | 1 | 6 | Dr. Radiology, June 3, 1967, April 22, 2025, 5271948603, 009321, Dr. Olivia, Dr. David |
| `46L3QAKRDC` | 4 | 0 | 0 | 0 | 0 | 0 | 6 | May 22, 1956, August 15, 2024, 872345019, 20240720, Dr. Sofia, Dr. Nina |
| `2F6IQCJRLM` | 5 | 0 | 0 | 0 | 0 | 0 | 4 | October 2, 2023, 1234567, Dr. Sofia, Dr. Priya |
| `HKKU3TXVXQ` | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 05/12/1976, 06/15/2024, 123456789, 11234, Dr. Natalie, Dr. Victor |
| `XJWBR3P2FC` | 6 | 0 | 0 | 0 | 0 | 0 | 4 | April 15, 1963, November 12, 2025, 573920148, Dr. Priya |
| `OLXVP6F6VH` | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 09/15/1965, 08/22/2024, 08/23/2024, 842761, 20240822, 00456 |

## Anonymization performance (tier-5)

**One row per backend-run** (one backend anonymizing all N reports). Wall-clock and the anonymizer's **own** LLM cost (parsed from the tier-5 run logs — this is the validator/augmenter work, not the command-generation call). **`Total time per run (sec)`** is the full wall-clock for that single backend-run; **`Mean per report`** = that total / its report count. `Reasoning tok` is the hidden chain-of-thought; `req fail` are LLM calls that errored (e.g. the augmenter breaking structured output).

| Backend/arm | Reports | Total time per run (sec) | Mean per report (sec/report) | Detect stage (sec) | LLM in tok | out tok | reasoning tok | tps | LLM req ok/fail |
|---|---:|---:|---:|---:|---:|---:|---:|---:|:--:|
| gptoss/with | 100 | 286.5 | 2.9 | n/a | n/a | n/a | n/a | n/a | n/a |
| gptoss/without | 100 | 362.5 | 3.6 | n/a | n/a | n/a | n/a | n/a | n/a |
| nemotron120-remote/with | 100 | 299.4 | 3.0 | n/a | n/a | n/a | n/a | n/a | n/a |
| nemotron120-remote/without | 100 | 322.8 | 3.2 | n/a | n/a | n/a | n/a | n/a | n/a |
| gpt-5.5/with | 100 | 332.0 | 3.3 | 330.4 | 524189 | 202248 | 137086 | 2260 | 200/100 |
| gpt-5.5/without | 100 | 496.0 | 5.0 | 343.0 | n/a | n/a | n/a | n/a | n/a |
`n/a` = the raw `anonymizer run` CLI (without-skill arm) emits no token-usage summary; only the skill wrapper reports it. Wall-clock and detect-stage time are measured for both.

## Token profiling

Provider-reported usage for the command-generation call (the agent overhead to pick the command). The NeMo Anonymizer pipeline's own internal token use during tier-5 execution is captured separately in **Anonymization performance** above.

| Backend | Arm | Repeats | Passes with 0 PHI escapes | LLM calls | Prompt tok | Completion tok | Reasoning tok | Total tok | Mean cmd-gen exec (sec) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| gptoss | with | 1 | 0 | 1 | 1992 | 395 | 0 | 2387 | 286.497 |
| gptoss | without | 1 | 0 | 1 | 1656 | 449 | 0 | 2105 | 362.456 |
| nemotron120-remote | with | 1 | 0 | 1 | 2081 | 472 | 0 | 2553 | 299.405 |
| nemotron120-remote | without | 1 | 0 | 1 | 1707 | 612 | 0 | 2319 | 322.763 |
| claude-opus-4-8 | unaided | 1 | 0 | 1 | 404 | 962 | 0 | 1366 | 17.047 |
| gpt-5.5 | unaided | 1 | 0 | 1 | 255 | 2847 | 1024 | 3102 | 2400.002 |
| gpt-5.5 | with | 1 | 0 | 1 | 1930 | 650 | 512 | 2580 | 332.002 |
| gpt-5.5 | without | 1 | 0 | 1 | 1594 | 761 | 512 | 2355 | 496.026 |

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

**gpt-5.5 / with / rep1** — tier 5, fail

```bash
mkdir -p runs/curation_eval/anon/study_buildnvidia_100/gpt-5.5/with/rep1 && python skills/report-anonymization/scripts/anonymize_reports.py runs/curation_eval/anon/study_buildnvidia_100/_inputs/reports_w_PHI.csv --output-dir runs/curation_eval/anon/study_buildnvidia_100/gpt-5.5/with/rep1 --full
```
- exec rc=0 (332.0s), out_rows=100, transformed=100
- stderr tail: `[20:07:38] Residual PHI : 1/100 record(s) (1.0%) with unreplaced detected values / [20:07:38]   leak types     : institution=1 / [20:07:38] ========================================================================`

**gpt-5.5 / without / rep1** — tier 5, fail

```bash
mkdir -p runs/curation_eval/anon/study_buildnvidia_100/gpt-5.5/without/rep1 && python - <<'PY'
from anonymizer import Anonymizer, AnonymizerConfig, AnonymizerInput, Substitute

src = "runs/curation_eval/anon/study_buildnvidia_100/_inputs/reports_w_PHI.csv"
out = "runs/curation_eval/anon/study_buildnvidia_100/gpt-5.5/without/rep1/reports_anonymized.csv"

anonymizer = Anonymizer()
config = AnonymizerConfig(replace=Substitute(), emit_telemetry=False)
result = anonymizer.run(
    config=config,
    data=AnonymizerInput(
        source=src,
        text_column="report_w_PHI",
        data_summary="English radiology reports containing protected health information.",
    ),
)
result.dataframe.to_csv(out, index=False)
PY
```
- exec rc=0 (496.0s), out_rows=100, transformed=100
- stderr tail: `[20:13:34] [INFO] 🔄 Running Substitute replacement / [20:16:06] [INFO]   |-- 📋 Replacement complete (0 failed) [151.3s] / [20:16:06] [INFO] 🎉 Pipeline complete — 100 records processed, 0 total failures`

**gpt-5.5 / unaided / rep1** — tier 4, fail

```bash
mkdir -p runs/curation_eval/anon/study_unaided_100/gpt-5.5/unaided/rep1 && python3 - <<'PY'
import csv, json, os, re, sys, time, urllib.request, urllib.error

inp = "runs/curation_eval/anon/study_unaided_100/_inputs/reports_w_PHI.csv"
out = "runs/curation_eval/anon/study_unaided_100/gpt-5.5/unaided/rep1/reports_anonymized.csv"

api_key = os.environ.get("NVIDIA_API_KEY")
if not api_key:
    raise SystemExit("NVIDIA_API_KEY is not set")

model = os.environ.get("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")
url = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/") + "/chat/completions"

system_prompt = (
    "You are a strict radiology-report de-identification engine. "
    "Return ONLY valid JSON with key redacted_report. "
    "Replace every item of PHI with bracketed placeholders while preserving clinical meaning, grammar, measurements, anatomy, diagnoses, and findings. "
    "PHI to replace includes patient names, doctor/provider/radiologist names, initials used as names, MRNs, medical record numbers, account numbers, accession numbers, dates, times tied to dates, ages, sex/gender, phone/fax numbers, addresses, emails, URLs, institution/hospital/clinic/practice names, locations when identifying an institution, and any other personal identifier. "
    "Use placeholders such as [PATIENT], [DOCTOR], [MRN], [ACCESSION], [DATE], [AGE], [SEX], [PHONE], [INSTITUTION], [ADDRESS], [EMAIL], [ID]. "
    "Do not summarize, omit, add, or alter clinical findings. Do not redact non-identifying clinical measurements or image numbers unless they are identifiers."
)

def call_llm(text, tries=6):
    user_prompt = "Redact this radiology report:\n\n" + ("" if text is None else str(text))
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
        "top_p": 1,
        "max_tokens": max(1024, min(8192, int(len(user_prompt) * 1.8) + 512)),
        "response_format": {"type": "json_object"},
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=180) as resp:
                obj = json.loads(resp.read().decode("utf-8"))
            content = obj["choices"][0]["message"]["content"].strip()
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                m = re.search(r"\{.*\}", content, flags=re.S)
                parsed = json.loads(m.group(0)) if m else {}
            red = parsed.get("redacted_report", "")
            if not isinstance(red, str) or not red.strip():
                raise ValueError("empty redacted_report")
            return red
        except Exception as e:
            last = e
            time.sleep(min(30, 2 ** i))
    raise RuntimeError(f"NVIDIA redaction failed after retries: {last}")

def deterministic_cleanup(s):
    if s is None:
        return ""
    s = str(s)
    s = re.sub(r'\b(?:MRN|M\.?R\.?N\.?|Medical Record(?: Number)?|Record #|Patient ID)\s*[:#]?\s*[A-Z0-9-]{4,}\b', '[MRN]', s, flags=re.I)
    s = re.sub(r'\b(?:Accession(?: Number)?|Accession #|Acc(?:\.|ession)? No\.?)\s*[:#]?\s*[A-Z0-9-]{4,}\b', '[ACCESSION]', s, flags=re.I)
    s = re.sub(r'\b(?:DOB|D\.O\.B\.|Date of Birth)\s*[:#]?\s*(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|[A-Z][a-z]+ \d{1,2}, \d{4})\b', '[DATE]', s, flags=re.I)
    s = re.sub(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', '[DATE]', s)
    s = re.sub(r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b', '[DATE]', s)
    s = re.sub(r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s+\d{1,2},?\s+\d{2,4}\b', '[DATE]', s, flags=re.I)
    s = re.sub(r'\b\d{1,3}\s*(?:yo|y/o|year-old|years old|yr-old|yrs old|M|F|male|female)\b', lambda m: '[AGE]' if re.search(r'\d', m.group(0)) else '[SEX]', s, flags=re.I)
    s = re.sub(r'\b(?:male|female|man|woman|boy|girl)\b', '[SEX]', s, flags=re.I)
    s = re.sub(r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b', '[PHONE]', s)
    s = re.sub(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', '[EMAIL]', s, flags=re.I)
    s = re.sub(r'\b(?:https?://|www\.)\S+\b', '[URL]', s, flags=re.I)
    s = re.sub(r'\b(?:Dr\.?|Doctor|MD|M\.D\.)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b', '[DOCTOR]', s)
    s = re.sub(r'\b[A-Z][A-Za-z&.\'-]*(?:\s+[A-Z][A-Za-z&.\'-]*){0,5}\s+(?:Hospital|Clinic|Medical Center|Imaging Center|Radiology|Healthcare|Health System|University Hospital|Memorial|Institute|Associates|Group|Practice)\b', '[INSTITUTION]', s)
    return s

with open(inp, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    fields = reader.fieldnames or []
if "study_uid" not in fields or "report_w_PHI" not in fields:
    raise SystemExit("Input CSV must contain columns study_uid and report_w_PHI")

for n, row in enumerate(rows, 1):
    original = row.get("report_w_PHI", "")
    redacted = call_llm(original)
    row["report_w_PHI"] = deterministic_cleanup(redacted)
    if n % 10 == 0:
        print(f"redacted {n}/{len(rows)} reports", file=sys.stderr)

os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

print(f"Wrote anonymized CSV to {out}", file=sys.stderr)
PY
```
- failed: tier5:The command executes cleanly and produces an anonymized CSV that transformed the reports.
- exec rc=124 (2400.0s), out_rows=0, transformed=0
- stderr tail: `timeout after 2400.0s`

**claude-opus-4-8 / unaided / rep1** — tier 4, fail

```bash
mkdir -p runs/curation_eval/anon/study_unaided_100/claude-opus-4-8/unaided/rep1 && python3 - <<'PY'
import os, csv, json, urllib.request

IN = "runs/curation_eval/anon/study_unaided_100/_inputs/reports_w_PHI.csv"
OUT = "runs/curation_eval/anon/study_unaided_100/claude-opus-4-8/unaided/rep1/reports_anon.csv"

API_KEY = os.environ["NVIDIA_API_KEY"]
URL = "https://integrate.api.nvidia.com/v1/chat/completions"

SYS = (
    "You are a clinical de-identification engine. Redact ALL PHI from the radiology "
    "report: patient and doctor names, MRNs, dates, ages, sex, accession numbers, "
    "phone numbers, and institution names. Replace each with a placeholder label such "
    "as [PATIENT], [DATE], [DOCTOR], [MRN], [INSTITUTION], [AGE], [SEX], [ACCESSION], "
    "[PHONE]. Leave all clinical findings and impressions completely intact. "
    "Return ONLY the redacted report text with no commentary."
)

def redact(text):
    payload = {
        "model": "meta/llama-3.1-70b-instruct",
        "messages": [
            {"role": "system", "content": SYS},
            {"role": "user", "content": text},
        ],
        "temperature": 0.0,
        "max_tokens": 2048,
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        resp = json.load(r)
    return resp["choices"][0]["message"]["content"].strip()

with open(IN, newline="", encoding="utf-8") as f, \
     open(OUT, "w", newline="", encoding="utf-8") as g:
    reader = csv.DictReader(f)
    writer = csv.DictWriter(g, fieldnames=["study_uid", "report_w_PHI"])
    writer.writeheader()
    for row in reader:
        redacted = redact(row["report_w_PHI"])
        writer.writerow({"study_uid": row["study_uid"], "report_w_PHI": redacted})
print("Wrote", OUT)
PY
```
- failed: tier5:The command executes cleanly and produces an anonymized CSV that transformed the reports.
- exec rc=1 (17.0s), out_rows=0, transformed=0
- stderr tail: `Traceback (most recent call last): / File "<stdin>", line 48, in <module> / KeyError: 'study_uid'`

## Backend reachability (probed at run time)

| Backend | Kind | Model | Reachable | Ping s |
|---|---|---|:--:|---:|
| nemotron120-remote | openai | `nvidia/nemotron-3-super-120b-a12b` | yes | 0.613 |
| gptoss | openai | `openai/gpt-oss-120b` | yes | 0.503 |
| gpt-5.5 | openai | `openai/openai/gpt-5.5` | yes | 1.769 |
| claude-opus-4-8 | openai | `aws/anthropic/bedrock-claude-opus-4-8` | yes | 1.48 |

## Findings

- **Redaction quality gap (primary result):** with-skill left **27** residual PHI escapes (individual PHI items) and fully redacted **291/300** report-runs; without-skill left **1342** items and fully redacted **85/300** report-runs (~50x fewer items with the skill). The skill's strict GLiNER label set drives detection; the upstream-README default redaction leaves many residual fragments (mostly name middle initials). Concentration: 20 of the 27 with-skill escape items came from one hard report (`HKKU3TXVXQ`) that the strict labels missed across backends.
- Under the strict zero-escape pass criterion, with-skill passed 0/3 backend-runs and without-skill 0/3 backend-runs — neither backend-run cleared a perfect zero-escape bar at this scale, so the item-level escape counts above are the primary signal.
- Robustness/speed: mean tier-5 execution was 306.0s with-skill vs 393.7s without-skill. The slowest arm was gpt-5.5/without at 496s: the unaided upstream-default detection path (no strict label set) does far more LLM augmentation and nearly hit the wall-clock budget. The wrapper's strict GLiNER label set bounds detection cost.
- Output contract: the with-skill wrapper emits `study_uid,report` plus a schema-valid `anonymization_summary` JSON and per-stage telemetry; the upstream `anonymizer run` output drops the `study_uid` passthrough and emits raw trace columns (`report_w_PHI_replaced`, ...).
- Unaided baseline (natural request, no doc, no skill): 0/2 produced a runnable anonymization command — the hardest arm, standing in for a user who just asks the model to redact the CSV with no NeMo Anonymizer documentation at all.
- `Pass` = produced output AND zero LLM-judged residual PHI escapes (any escape is a fail). `Produced output` (tier-5 completion) is reported separately, so a leaky-but-complete arm shows as produced-output yet fails.

## Reproduce

From the `medical-AI-skills` catalog root:

```bash
export NVIDIA_API_KEY="nvapi-..."
python -m tools.curation_eval.anon_experiment \
  --backends nemotron120-remote gptoss=https://integrate.api.nvidia.com/v1=openai/gpt-oss-120b=NVIDIA_API_KEY gpt-5.5 claude-opus-4-8 \
  --repeats 1 --limit 100
```
