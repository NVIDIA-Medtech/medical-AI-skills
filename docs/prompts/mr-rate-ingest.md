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

**Ops (status language, live gates, MRI fixtures, skill gaps):**
[`docs/mr-rate-ingest-ops.md`](../mr-rate-ingest-ops.md).
Agents must split `mri.status` / `reports.status` / `join.status`. On a real
tranche, pass `--mode live` only. Do not run `--mode mock` and do not fall
back to mock when the LLM or a stage fails.

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
- --mode: live            # real data. Needs MR_RATE_ROOT, MR_RATE_REPORTS_ROOT,
                          # GPU, and an already-running OpenAI-compatible LLM.
                          # Do not pass mock. Do not switch to mock on failure.
- --device: <DEVICE>       # live only
- --mr-rate-root: <MR_RATE_ROOT>   # live only
- Local report LLM (defaults — override only if needed):
  - model: nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4
  - base_url: http://127.0.0.1:8080
  - set in study.json "llm" block, or --model / --base-url, or
    CURATION_LLM_MODEL / CURATION_LLM_BASE_URL

## Required behavior
1. **Prove** the LLM first (`curl -sS --max-time 5 <base_url>/v1/models`
   must return HTTP 200 and `data[].id` == `llm.model`). Connection refused →
   `reports.status=not_run`, `blocker=llm_unreachable`. Stop. Do not run
   `--mode mock` and do not write a custom LLM proxy. Run MRI `--preflight`
   on one study. Read `docs/mr-rate-ingest-ops.md`. On a real error, fix the
   skill or MR-RATE code generally; do not paper over it with mock output.
2. Run:
   python skills/nv-curate-study/scripts/run_curate_study.py <STUDY_JSON> \
     --mode <MODE> --out <OUT_DIR> [--device <DEVICE>] [--mr-rate-root <MR_RATE_ROOT>] \
     [--model nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4] \
     [--base-url http://127.0.0.1:8080]
3. Prefer live preflight first when mode=live:
   ... --preflight
4. Keep publish.skip_upload true until I explicitly approve QC.
5. Report tracks separately using the ops template:
   `mri.status`, `reports.status`, `join.status`, `blocker`, `publish.skip_upload`.
   Example: `MRI: 1/1 live_ok. Reports: not_run. join.status=rejected.
   blocker=llm_unreachable (GET http://127.0.0.1:8080/v1/models failed).`
   Do not run mock to fill the report track. Do not say only “complete in mock; live blocked”.
   Exit 0 with `n_matched=0` is not success.
6. If I later need a full tranche, switch to nv-curate-batch (it calls this skill).

## Hard rules
- Engineering curation only — no clinical or regulatory claims.
- Do not write new `.py` tools; use `skills/*/scripts/` and
  `nv-curate-mri/fixtures/generate_fixtures.py`.
- Do not invent LLM servers. Do not QC voxels. Do not log secrets/PHI.
- Do not commit PHI, credentials, or large volumes.
- On failure, prefer rerunning the failing stage / this one study — not the whole batch.
- PACS `SeriesDescription` must be space-only (colons break dcm2niix vs MR-RATE
  filename prediction). AccessionNumber must be non-empty and match mapping xlsx.
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
- --mode: live           # real data only. Do not pass mock. Do not fall back to mock.
- --smoke: <N>            # e.g. 5
- --device / --mr-rate-root for live mode as needed
- Local report LLM defaults (batch.json "llm" or CLI):
  - model: nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4
  - base_url: http://127.0.0.1:8080

## Required behavior
1. Ensure each studies[] entry is a study.json that nv-curate-study accepts.
   Build MRI fixtures from `skills/nv-curate-mri/fixtures/generate_fixtures.py --step orchestrator`
   (same four files/columns). Align SeriesDescription (spaces only) and AccessionNumber.
2. **Prove** the LLM (`curl <base_url>/v1/models`) and MRI `--preflight`
   before the smoke cohort. See `docs/mr-rate-ingest-ops.md`. If the LLM is
   down, stop with `reports.status=not_run` and `blocker=llm_unreachable`.
   Do not start `--mode mock`. Fix a confirmed skill or MR-RATE bug in the
   catalog, not with a one-study workaround.
3. Run:
   python skills/nv-curate-batch/scripts/run_curate_batch.py <BATCH_JSON> \
     --mode <MODE> --smoke <N> --out <OUT_DIR> \
     [--model nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4] \
     [--base-url http://127.0.0.1:8080] [...]
4. If smoke rejects and fail_closed is true, stop and fix before full batch.
5. Deliver matched vs rejected lists **and** per-track status
   (`mri.status` / `reports.status` / `join.status` / `blocker`). A live MRI
   with reports not run, or live reports failed, is `join.status=rejected`,
   not “batch complete”. Do not fill that gap with `--mode mock`.
   Include per-study summary paths under <OUT_DIR>/studies/<study_uid>/,
   llm.model/base_url, and publish.blocked.
6. Do not upload while skip_upload is true or rejects remain (fail_closed).
   If MRI succeeded and reports failed, rerun reports/`nv-curate-study` for
   that uid only — do not re-deface the tranche.

## Hard rules
- Composition only: batch → nv-curate-study → (live) nv-curate-mri + nv-curate.
  Do not write sidecars or restore deleted wrappers; PR skill gaps instead.
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

- [`docs/mr-rate-ingest-ops.md`](../mr-rate-ingest-ops.md) — live gates, fixtures, status language
- [`docs/using-skills.md`](../using-skills.md)
- [`docs/agent-tasks.md`](../agent-tasks.md)
