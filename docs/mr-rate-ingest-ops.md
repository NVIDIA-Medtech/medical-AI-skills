# MR-RATE ingest operations (humans and agents)

How to finish a live MRI + report tranche without silent mock success,
custom Python sidecars, or mixed-mode “matched” claims.

Read this **with** [`prompts/mr-rate-ingest.md`](prompts/mr-rate-ingest.md) and
the skill `SKILL.md` you are invoking. Engineering curation only.

## Status language (required)

Report **tracks separately**. Never collapse mock reports + live MRI into
“curation complete.”

| Field | Allowed values | Meaning |
|---|---|---|
| `mri.status` | `live_ok` \| `live_failed` \| `stubbed_mock` \| `not_run` | MRI track only |
| `reports.status` | `live_ok` \| `live_failed` \| `mock_ok` \| `not_run` | Report track only |
| `join.status` | `matched` \| `rejected` | Both live sides present and `study_uid` join succeeded |
| `blocker` | short machine token or `none` | Why join is not `matched` |
| `publish.skip_upload` | `true` \| `false` | Must stay `true` until human QC |

**Say this:**

```text
MRI: 20/20 live_ok (nv-curate-mri). Reports: 20/20 mock_ok (nv-curate --mode mock).
join.status=rejected. blocker=llm_unreachable (GET http://127.0.0.1:8080/v1/models failed).
publish.skip_upload=true. Do not treat this as a live matched pair.
```

**Do not say this:**

- “20 / 20 complete in mock; live blocked” (hides that MRI was live)
- “not matched as a live pair (no LLM on :8080)” as the *only* sentence (omit counts, which track failed, which command)
- “batch succeeded” when `n_matched=0` and `n_rejected=20` (process exit 0 ≠ matched)
- “curated to MR-RATE format” when reports never ran live

Batch JSON `n_matched` / `n_rejected` is the join result of **both** tracks.
A study with live defaced NIfTI and failed reports is still `rejected`.

## Hard rules (agents)

1. **Do not write new `.py` helpers.** Invoke `skills/*/scripts/` and
   `fixtures/generate_fixtures.py`. If a wrapper is missing, stop and open a
   skill-gap PR — do not reconstruct deleted scripts.
2. **Do not invent a local LLM server** (custom proxy, OpenAI shim, dummy
   FastAPI). Live reports require an already-running OpenAI-compatible server
   at `llm.base_url` with the **same model id** as `llm.model`.
3. **Do not QC voxels or “validate images”** unless the user asked. That is
   `nv-curate-mri` / MR-RATE.
4. **Do not pip-install into the live venv while a GPU pipeline is running.**
5. **Do not reuse `--out`** when MR-RATE logs `Output CSV already exists`.
   Pick a new out dir (or delete only with explicit user approval).
6. **Do not put API keys, tokens, or PHI in HTML/Markdown reports.**
7. **Prefer one rejected `study_uid` + `nv-curate-study`** over rerunning the
   tranche.

## Live gate (run before `--mode live`)

All of these must pass. If any fail, **do not** start `nv-curate-batch --mode live`.

```bash
# 1) LLM actually serving the configured model
curl -sS --max-time 5 "$CURATION_LLM_BASE_URL/v1/models"
# Expect HTTP 200 and a data[].id that equals llm.model (default
# nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4). Connection refused = blocker=llm_unreachable.

# 2) MRI preflight (one study is enough)
python skills/nv-curate-mri/scripts/run_mri_pipeline.py \
  --fixtures /path/to/study/mri_fixtures \
  --out /path/to/out_preflight \
  --mr-rate-root "$MR_RATE_ROOT" \
  --preflight

# 3) Report orchestrator entrypoints exist
test -f skills/nv-curate/scripts/nv_curate.py
test -f skills/report-anonymization/scripts/anonymize_reports.py
# Known gap: nv-curate currently looks for scripts/run_anonymization.py.
# If that file is missing, live join will fail at anonymize. Do not write a
# replacement; PR nv-curate to call anonymize_reports.py (see SKILL.md).
```

Env for live MRI: `MR_RATE_ROOT`, `MR_RATE_REPORTS_ROOT`, `dcm2niix` on `PATH`,
CUDA GPU, `CUDA_DEVICE_ORDER=PCI_BUS_ID` recommended.

## Per-study MRI fixtures (nv-curate-mri)

Generate the shape with the official generator, then replace synthetic rows
with real (already de-identified / research) values — **same columns**:

```bash
python skills/nv-curate-mri/fixtures/generate_fixtures.py \
  --step orchestrator --out /path/to/study/mri_fixtures
```

Required files:

| File | Role |
|---|---|
| `dicom_folder_paths.csv` | Column `FolderPath` → DICOM series directory |
| `pacs_metadata.csv` | Required PACS columns (see generator `REQUIRED_PACS_COLUMNS`) |
| `patient_mapping.xlsx` | `Accession`, `Anon Patient ID` |
| `study_date_mapping.xlsx` | `Accession`, `Anonymized Study Date` |

Alignment rules that prevent the most common live MRI rejects:

| Check | Why |
|---|---|
| DICOM `AccessionNumber` is non-empty and equals the study folder / `Accession` in mappings | dcm2niix **skips** empty accession; mapping join fails otherwise |
| `SeriesDescription` uses **spaces only** (no `:`, `/`, or other punctuation dcm2niix strips) | MR-RATE predicts `{SeriesNumber}_{words}.nii.gz`; a colon in PACS CSV yields `3_t1_axial:_foo.nii.gz` while dcm2niix writes `3_t1_axial_foo.nii.gz` → modality filter “Missing NIfTI” |
| `PulseSequenceName` / scanning fields match classifier TIER1 (e.g. `T1TFE` → T1w center) | Otherwise no center modality |
| Do not hand-validate FOV/shape; if the series fails quality gates, read `logs/modality_filtering_*.log` | |

## When MRI is OK but the study is still rejected

`nv-curate-study --mode live` runs MRI **then** reports. Report failure rejects
the study even if `processed/**/img/*.nii.gz` exists.

Then:

1. Leave MRI artifacts in place; do not re-deface unless MRI logs failed.
2. Fix the **report** blocker (LLM, missing entrypoint, CSV columns).
3. Rerun **that study** with `nv-curate-study`, or run `nv-curate` alone on
   `datasources.json` once the LLM is up.
4. State both tracks in the status block above.

## Mock vs live

| Mode | MRI | Reports | Proves |
|---|---|---|---|
| `mock` | stubbed | sibling mock CLIs (or study stub) | wiring only |
| `live` | real MR-RATE + GPU | real stage skills + LLM | ingest |

`--mode live` with reports falling back to mock is **not** live join. If you
ran `nv-curate --mode mock` after a live MRI loop, say so explicitly.

## Skill-gap PRs (do not local-patch and move on)

| Symptom | Likely gap | PR target |
|---|---|---|
| `stage skill entrypoint missing: .../run_anonymization.py` | `nv-curate` STAGES vs `report-anonymization` `anonymize_reports.py` | medical-AI-skills `draft/report-anonymization-skill-testing` |
| Filename colon mismatch | document + optional generator check | medical-AI-skills and/or MR-RATE `get_dcm2niix_filename` |
| Live anonymize launches SLURM/vLLM Qwen regardless of `llm.base_url` | wrapper/upstream contract | medical-AI-skills and/or MR-RATE reports_preprocessing |

Never attach PHI to the PR.
