# Getting started: ingesting an MR-RATE data tranche

This guide walks you through adding studies to MR-RATE using the two end-to-end
curation skills in this repository. They compose the MRI and report pipelines,
join the two tracks on `study_uid`, and keep publishing blocked until you
approve QC.

These skills **wrap** the existing MR-RATE
[data-preprocessing](https://github.com/forithmus/MR-RATE/tree/main/data-preprocessing)
code. They do not replace it.

## Which skill do I use?

| Goal | Skill | Where it lives |
|---|---|---|
| One MRI + its report | `nv-curate-study` | [`skills/nv-curate-study/`](skills/nv-curate-study/) |
| A batch / tranche | `nv-curate-batch` | [`skills/nv-curate-batch/`](skills/nv-curate-batch/) |

**How they compose:** `nv-curate-batch` calls `nv-curate-study` once per study
(smoke cohort first). Each study run drives MRI, then reports, joins the two,
and emits matched / rejected results — with publish blocked while
`skip_upload` is true.

If you are new to this, work through the sections in order. If you have run an
ingest before, jump to [Recommended operating sequence](#8-recommended-operating-sequence)
and use the rest as reference.

---

## 1. Get the testing branch

The skills live on the `draft/report-anonymization-skill-testing` branch:
<https://github.com/medatasci/medical-AI-skills/tree/draft/report-anonymization-skill-testing>

```bash
git clone https://github.com/medatasci/medical-AI-skills.git
cd medical-AI-skills
git checkout draft/report-anonymization-skill-testing
```

You will also need your local MR-RATE
[data-preprocessing](https://github.com/forithmus/MR-RATE/tree/main/data-preprocessing)
checkout for `--mode live`.

Copy-paste prompts for driving this with an agent:
[`docs/prompts/mr-rate-ingest.md`](docs/prompts/mr-rate-ingest.md).

---

## 2. Curate one study (`nv-curate-study`)

Start with a single study before you touch a tranche.

Read first:

- Skill: [`skills/nv-curate-study/SKILL.md`](skills/nv-curate-study/SKILL.md)
- Config schema: [`schemas/study.schema.json`](skills/nv-curate-study/schemas/study.schema.json)
- Fixture template: [`fixtures/study.json`](skills/nv-curate-study/fixtures/study.json)

Fill in a `study.json` for the one MRI + report: paths, `study_uid`, the report
`datasources.json`, and `publish.skip_upload: true`.

Then run it. Start in mock mode to check your wiring, and only then go live:

```bash
# Wiring / CI (no GPU; MRI stubbed)
python skills/nv-curate-study/scripts/run_curate_study.py \
  skills/nv-curate-study/fixtures/study.json \
  --mode mock --out runs/nv_curate_study_demo

# Live (real MR-RATE + GPU + report stack)
export MR_RATE_ROOT=/path/to/MR-RATE/data-preprocessing
export MR_RATE_REPORTS_ROOT="$MR_RATE_ROOT/src/mr_rate_preprocessing/reports_preprocessing"
python skills/nv-curate-study/scripts/run_curate_study.py /path/to/study.json \
  --mode live --device 0 --out runs/nv_curate_study_live

# Optional: MRI env check only
python skills/nv-curate-study/scripts/run_curate_study.py /path/to/study.json \
  --mode live --preflight --out runs/nv_curate_study_preflight
```

**What success looks like:** `join.status=matched`, `publish.blocked=true` while
upload is skipped, and stage outputs under `<out>/mri` and `<out>/reports`.

---

## 3. Curate a tranche (`nv-curate-batch`)

Read first:

- Skill: [`skills/nv-curate-batch/SKILL.md`](skills/nv-curate-batch/SKILL.md)
- Config schema: [`schemas/batch.schema.json`](skills/nv-curate-batch/schemas/batch.schema.json)
- Fixture template: [`fixtures/batch.json`](skills/nv-curate-batch/fixtures/batch.json)

Build a `batch.json` whose `studies[]` entries are paths to (or inline)
`study.json` files that `nv-curate-study` accepts. Set a smoke size (e.g. 5)
before running the full batch.

```bash
python skills/nv-curate-batch/scripts/run_curate_batch.py \
  /path/to/batch.json \
  --mode live --smoke 5 --device 0 \
  --out runs/nv_curate_batch_live
```

**What success looks like:** the smoke cohort comes back clean, then the full
batch runs; matched vs reject lists appear in the summary; per-study detail
lands under `<out>/studies/<study_uid>/`; publish is still blocked until you
approve.

When a single study is rejected, fix that one study with `nv-curate-study`
rather than reprocessing the whole tranche.

---

## 4. One-time environment setup (live mode)

### Reports

- Python env with the report pipeline dependencies / vLLM
- `export MR_RATE_REPORTS_ROOT=/path/to/MR-RATE/data-preprocessing/src/mr_rate_preprocessing/reports_preprocessing`
- GPU as needed; set `CUDA_VISIBLE_DEVICES`

### MRI

- The usual MRI conda env ([`environment.yml`](https://github.com/forithmus/MR-RATE/blob/main/data-preprocessing/environment.yml))
- [`dcm2niix`](https://github.com/rordenlab/dcm2niix) on `PATH`; CUDA GPU for HD-BET / Quickshear
- `export MR_RATE_ROOT=/path/to/MR-RATE/data-preprocessing`

Always smoke a small cohort before the full tranche, and keep
`skip_upload: true` until QC passes.

Machine-readable ops for agents live in
[`docs/mr-rate-ingest-ops.md`](docs/mr-rate-ingest-ops.md). Humans should use
the same status fields described below, so that a "green" mock run is never
mistaken for a live matched pair.

---

## 4b. Live gates, fixtures, and how to report status

### Do not start a live batch until all three gates pass

1. **The LLM is already serving.** `curl -sS --max-time 5 http://127.0.0.1:8080/v1/models`
   returns HTTP 200 and a `data[].id` equal to `llm.model`. Connection refused
   means `blocker=llm_unreachable` — do not invent a proxy or server, and do not
   run `--mode live` for reports.
2. **MRI preflight passes.** `nv-curate-mri … --preflight` (checks `dcm2niix` on
   PATH, CUDA, and `$MR_RATE_ROOT`).
3. **Report stage scripts exist.** `nv-curate` invokes
   `report-anonymization/scripts/run_anonymization.py`. Confirm that entrypoint
   resolves before a live run. If a stage entrypoint is missing, do not write a
   replacement wrapper — open a PR (see [section 9](#9-bugs-and-improvements)).
   This was a known gap when the skills first shipped, because the skill only
   provided `anonymize_reports.py`; on the current
   `draft/report-anonymization-skill-testing` branch both
   `skills/report-anonymization/scripts/run_anonymization.py` and
   `anonymize_reports.py` are present.

### Per-study `mri_fixtures`

Generate them with the official generator, then fill in the real rows:

```bash
python skills/nv-curate-mri/fixtures/generate_fixtures.py \
  --step orchestrator --out /path/to/study/mri_fixtures
```

Keep these four files and column names:

| File | Required columns |
|---|---|
| `dicom_folder_paths.csv` | `FolderPath` |
| `pacs_metadata.csv` | `REQUIRED_PACS_COLUMNS` |
| `patient_mapping.xlsx` | `Accession`, `Anon Patient ID` |
| `study_date_mapping.xlsx` | `Accession`, `Anonymized Study Date` |

Two content rules that cause most fixture failures:

- DICOM `AccessionNumber` must be non-empty and must match the mapping
  `Accession` (dcm2niix skips empty accessions).
- PACS `SeriesDescription`: spaces only. A colon produces
  `Missing NIfTI file: 3_t1_axial:_Processed_….nii.gz`, because dcm2niix strips
  punctuation that MR-RATE's filename predictor keeps.

And a few things not to do:

- Do not write new `.py` tools.
- Do not QC/validate voxels — the MRI skill does that.
- Do not pip-install while a GPU run is in progress.
- Do not reuse `--out` if the logs say the output CSV already exists; use a new
  directory.

### Status language (required for humans and agents)

Report MRI and reports as **separate tracks**. A process exit code of 0 is not a
match. Here is a correctly reported incomplete run:

```text
MRI: 20/20 live_ok (nv-curate-mri).
Reports: 20/20 mock_ok (nv-curate --mode mock).
join.status=rejected.
blocker=llm_unreachable (GET http://127.0.0.1:8080/v1/models failed).
publish.skip_upload=true.
Do not treat this as a live matched pair.
```

Avoid both of these failure modes:

- "20 / 20 complete in mock; live blocked" — hides that MRI was live.
- "not matched as a live pair (no LLM on :8080)" — a one-liner with no counts,
  no commands, and no indication of which track failed.

A live defaced NIfTI plus failed reports is still `join.status=rejected`. Fix
the report blocker and rerun that `study_uid` with `nv-curate-study` — do not
re-deface the whole batch.

---

## 5. What runs underneath (for debugging and stage reruns)

In live mode, each study composes two tracks:

| Track | Orchestrator | What it runs |
|---|---|---|
| Reports | [`nv-curate`](skills/nv-curate/SKILL.md) | anonymize → translate + QC → structure + QC → pathology labels |
| MRI volumes | [`nv-curate-mri`](skills/nv-curate-mri/SKILL.md) | dcm2niix → PACS filter → series classify → modality filter → HD-BET/Quickshear → zip → metadata |

If you need to rerun a single failed stage, these are the per-step skills:

| Reports stage skills | MRI stage skills |
|---|---|
| [`report-anonymization`](skills/report-anonymization/SKILL.md) | [`mri-dcm2niix`](skills/mri-dcm2niix/SKILL.md) |
| [`report-translation`](skills/report-translation/SKILL.md) | [`mri-pacs-metadata-filter`](skills/mri-pacs-metadata-filter/SKILL.md) |
| [`report-structuring`](skills/report-structuring/SKILL.md) | [`mri-series-classification`](skills/mri-series-classification/SKILL.md) |
| [`report-pathology-classification`](skills/report-pathology-classification/SKILL.md) | [`mri-modality-filter`](skills/mri-modality-filter/SKILL.md) |
| [`medical-anonymization`](skills/medical-anonymization/SKILL.md) | [`mri-brain-seg-deface`](skills/mri-brain-seg-deface/SKILL.md) |
| [`dicom-metadata-extract`](skills/dicom-metadata-extract/SKILL.md) | [`mri-zip-upload`](skills/mri-zip-upload/SKILL.md) |
| | [`mri-metadata-prepare`](skills/mri-metadata-prepare/SKILL.md) |

---

## 6. Lay out raw inputs like an MR-RATE batch

Mirror the existing batch layout (e.g. `batchNN`) under
[data-preprocessing](https://github.com/forithmus/MR-RATE/tree/main/data-preprocessing):

```text
data/raw/batchNN/
  batchNN_dicom_folder_paths.csv
  batchNN_pacs_metadata.csv
  batchNN_accession_to_anon_patient.xlsx
  batchNN_accession_to_anon_study_date.xlsx
```

Copy [`run/configs/mri_batch00.yaml`](https://github.com/forithmus/MR-RATE/blob/main/data-preprocessing/run/configs/mri_batch00.yaml)
to `mri_batchNN.yaml`. Replace the template `your-org/mr-rate-dataset` with the
native-space target <https://huggingface.co/datasets/Forithmus/MR-RATE> only when
you are ready to publish. Keep `skip_upload: true` until QC passes.

Point each study's report `datasources.json` at your report CSV(s). For the
schema and examples, see
[`datasources.json` example](skills/nv-curate/fixtures/datasources.json) and
[`datasources.schema.json`](skills/nv-curate/schemas/datasources.schema.json).

---

## 7. After QC: publish / merge into MR-RATE

1. Confirm matched studies only; keep rejects on a reject list.
2. Human spot-check anonymization, defacing, and report structure.
3. On explicit approval, enable upload and publish to
   <https://huggingface.co/datasets/Forithmus/MR-RATE> (or the correct
   space-specific repo).
4. Merge and verify with the utilities under
   [`data-preprocessing/scripts/hf`](https://github.com/forithmus/MR-RATE/tree/main/data-preprocessing/scripts/hf)
   — for example [`merge_downloaded_repos.py`](https://github.com/forithmus/MR-RATE/blob/main/data-preprocessing/scripts/hf/merge_downloaded_repos.py)
   and [`download.py`](https://github.com/forithmus/MR-RATE/blob/main/data-preprocessing/scripts/hf/download.py).
5. Document `batchNN` in the
   [dataset guide](https://github.com/forithmus/MR-RATE/blob/main/data-preprocessing/docs/dataset_guide.md).

---

## 8. Recommended operating sequence

1. Stage raw DICOM paths, PACS CSV, mappings, and the report CSV for `batchNN`.
2. Write the per-study `study.json` files plus one `batch.json`.
3. Run a mock smoke on fixtures to validate wiring. This does **not** prove
   defacing or a live LLM.
4. Clear the live gates from [section 4b](#4b-live-gates-fixtures-and-how-to-report-status):
   `curl …/v1/models`, MRI `--preflight`, and confirm the report entrypoints.
   Then run `nv-curate-batch --smoke N`, fix any single failing `study_uid` with
   `nv-curate-study`, and run the full batch with `skip_upload: true`. Report
   `mri.status`, `reports.status`, and `join.status` separately.
5. Run the join / completeness audit plus human QC.
6. Enable upload and merge into the published MR-RATE database.

---

## 9. Bugs and improvements

While we are in testing, open PRs for verified bugs and skill / code
improvements against <https://github.com/medatasci/medical-AI-skills>, base
branch `draft/report-anonymization-skill-testing`
(skills live under
<https://github.com/medatasci/medical-AI-skills/tree/draft/report-anonymization-skill-testing/skills>).

For real preprocessing bugs inside MR-RATE, open a PR against
<https://github.com/forithmus/MR-RATE>.

**Do not attach PHI.**

---

## 10. Links to open first

- [`nv-curate-study`](skills/nv-curate-study/) — one MRI + report
- [`nv-curate-batch`](skills/nv-curate-batch/) — tranche (calls the study skill)
- [Ingest prompts](docs/prompts/mr-rate-ingest.md)
- [`nv-curate`](skills/nv-curate/SKILL.md) / [`nv-curate-mri`](skills/nv-curate-mri/SKILL.md) — the underlying tracks
- [MR-RATE data-preprocessing README](https://github.com/forithmus/MR-RATE/blob/main/data-preprocessing/README.md)
- [MR-RATE dataset guide](https://github.com/forithmus/MR-RATE/blob/main/data-preprocessing/docs/dataset_guide.md)

Full URLs, for contexts that strip formatting:

```text
https://github.com/medatasci/medical-AI-skills/tree/draft/report-anonymization-skill-testing/skills/nv-curate-study
https://github.com/medatasci/medical-AI-skills/tree/draft/report-anonymization-skill-testing/skills/nv-curate-batch
https://github.com/medatasci/medical-AI-skills/blob/draft/report-anonymization-skill-testing/docs/prompts/mr-rate-ingest.md
https://github.com/medatasci/medical-AI-skills/tree/draft/report-anonymization-skill-testing
https://huggingface.co/datasets/Forithmus/MR-RATE
https://github.com/forithmus/MR-RATE/blob/main/data-preprocessing/README.md
```
