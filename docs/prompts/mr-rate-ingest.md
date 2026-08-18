# MR-RATE ingest prompts (copy-paste for agents)

Paste one of the prompts below into an agent session that has this
`medical-AI-skills` checkout (and, for live mode, a local MR-RATE
`data-preprocessing` checkout). Fill every `<PLACEHOLDER>` before sending.

| Goal | Skill | Doc |
|---|---|---|
| One MRI + its report | **`nv-curate-study`** | [`skills/nv-curate-study/SKILL.md`](../../skills/nv-curate-study/SKILL.md) |
| Batch / tranche | **`nv-curate-batch`** (calls `nv-curate-study` per study) | [`skills/nv-curate-batch/SKILL.md`](../../skills/nv-curate-batch/SKILL.md) |

Underlying stage orchestrators (used by the study skill in live mode):

| Track | Skill |
|---|---|
| MRI volumes | [`nv-curate-mri`](../../skills/nv-curate-mri/SKILL.md) |
| Reports | [`nv-curate`](../../skills/nv-curate/SKILL.md) |

**Scope:** research data-curation engineering only. Not clinical care, not
regulatory de-identification, not patient-facing use.

---

## Prompt A — single study → `nv-curate-study`

```text
Use the nv-curate-study skill to curate ONE MRI study and its associated
radiology report for MR-RATE.

Read skills/nv-curate-study/SKILL.md and schemas/study.schema.json first.
Do not invent paths, PHI mappings, or upload credentials. Stop if inputs
are missing.

## Fill these
- study.json path (or create one from the template fixtures/study.json): <STUDY_JSON>
- --out: <OUT_DIR>
- --mode: mock | live     # live needs MR_RATE_ROOT, MR_RATE_REPORTS_ROOT, GPU
- --device: <DEVICE>       # live only
- --mr-rate-root: <MR_RATE_ROOT>   # live only

## Required behavior
1. Run:
   python skills/nv-curate-study/scripts/run_curate_study.py <STUDY_JSON> \
     --mode <MODE> --out <OUT_DIR> [--device <DEVICE>] [--mr-rate-root <MR_RATE_ROOT>]
2. Prefer live preflight first when mode=live:
   ... --preflight
3. Keep publish.skip_upload true until I explicitly approve QC.
4. Report join.status (matched/rejected), MRI/report out dirs, and blockers.
5. If I later need a full tranche, switch to nv-curate-batch (it calls this skill).

## Hard rules
- Engineering curation only — no clinical or regulatory claims.
- Do not commit PHI, credentials, or large volumes.
- On failure, prefer rerunning the failing stage / this one study — not the whole batch.
- If you confirm a bug, skill gap, or code improvement, open a pull request to the
  testing upstream
  https://github.com/medatasci/medical-AI-skills
  (base branch `draft/report-anonymization-skill-testing`; skills live under
  https://github.com/medatasci/medical-AI-skills/tree/draft/report-anonymization-skill-testing/skills).
  For real preprocessing bugs in MR-RATE `data-preprocessing`, PR
  https://github.com/forithmus/MR-RATE instead.
  Do not leave verified fixes only as local patches. Never attach PHI to the PR.
```
---

## Prompt B — tranche → `nv-curate-batch` (uses skill A)

```text
Use the nv-curate-batch skill to curate a TRANCHE of MRI studies and associated
reports for MR-RATE. This skill must invoke nv-curate-study once per study
(smoke cohort first). Do not reimplement MRI or report stages yourself.

Read skills/nv-curate-batch/SKILL.md and schemas/batch.schema.json first.
Also skim skills/nv-curate-study/SKILL.md so you know the per-study contract.

## Fill these
- batch.json path (template: skills/nv-curate-batch/fixtures/batch.json): <BATCH_JSON>
- --out: <OUT_DIR>
- --mode: mock | live
- --smoke: <N>            # e.g. 5
- --device / --mr-rate-root for live mode as needed

## Required behavior
1. Ensure each studies[] entry is a study.json that nv-curate-study accepts.
2. Run:
   python skills/nv-curate-batch/scripts/run_curate_batch.py <BATCH_JSON> \
     --mode <MODE> --smoke <N> --out <OUT_DIR> [...]
3. If smoke rejects and fail_closed is true, stop and fix before full batch.
4. Deliver matched vs rejected lists, per-study summary paths under
   <OUT_DIR>/studies/<study_uid>/, and publish.blocked status.
5. Do not upload while skip_upload is true or rejects remain (fail_closed).

## Hard rules
- Composition only: batch → nv-curate-study → (live) nv-curate-mri + nv-curate.
- Engineering curation only — no clinical or regulatory claims.
- Prefer fixing one rejected study via nv-curate-study over reprocessing all.
- If you confirm a bug, skill gap, or code improvement, open a pull request to the
  testing upstream
  https://github.com/medatasci/medical-AI-skills
  (base branch `draft/report-anonymization-skill-testing`; skills live under
  https://github.com/medatasci/medical-AI-skills/tree/draft/report-anonymization-skill-testing/skills).
  For real preprocessing bugs in MR-RATE `data-preprocessing`, PR
  https://github.com/forithmus/MR-RATE instead.
  Do not leave verified fixes only as local patches. Never attach PHI to the PR.
```
---

## Related docs

- [`docs/using-skills.md`](../using-skills.md)
- [`docs/agent-tasks.md`](../agent-tasks.md)
