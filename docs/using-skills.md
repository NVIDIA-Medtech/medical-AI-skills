# Using skills

How-to guide for running a committed medtech skill with **your** data and
environment. For trust artifacts (evidence packs, replay), see
[`trust-and-evidence.md`](trust-and-evidence.md).

## Discover

1. Browse [`SKILL_INDEX.md`](../SKILL_INDEX.md) (`make list-skills` to regenerate).
2. Open the chosen skill's `SKILL.md` under `skills/<name>/`.

The index lists **publishable skills** first. Verifiers are listed separately.

## Run (primary path)

You do **not** need the eval engine for normal use.

1. Read `skills/<name>/SKILL.md` for prerequisites (GPU, packages, upstream repos).
2. Run the documented `scripts/` entrypoint with your input paths and output
   directory.

Example:

```bash
python skills/dicom-metadata-extract/scripts/extract_metadata.py \
  /path/to/study.dcm \
  --output /path/to/out_dir
```

Each skill documents its own flags. Follow the upstream tool's recommended
invocation; Medical AI Skills wrapper should not reimplement inference.

## Optional: flagship workflow 1 (multi-skill evidence)

When you need **Workflow 1** (convert CT DICOM series → NIfTI → trusted
segmentation + verifier) in one command with a workflow-level summary:

```text
DICOM series
  -> dicom_series_to_volume (metadata + geometry preflight, DICOM-to-NIfTI)
  -> nv_segment_ct (trusted)
  -> ct_segmentation_quality_v1
  -> workflow / trust summary
```

```bash
make run-workflow-ct-seg \
  WORKFLOW_INPUT=/path/to/dicom_series \
  WORKFLOW_OUT=runs/ct_dicom_seg_evidence
```

Inspect `WORKFLOW_OUT/workflow_run_record.md` and `workflow_summary.json`.
This orchestrates skills from [`examples/workflows/ct_dicom_to_segmentation_evidence.yaml`](../examples/workflows/ct_dicom_to_segmentation_evidence.yaml).
It does **not** replace reading each skill's `SKILL.md` for day-to-day use.

## Optional: evidence pack

When you need an audit record (CI, review, publication), use the harness:

```bash
make run-skill SKILL=dicom_metadata_extract \
  FIXTURE=skills/dicom-metadata-extract/fixtures/sample_ct.dcm \
  OUT=runs/my_demo
```

Output lands in `runs/` (gitignored). Committed reference packs live under
[`examples/`](../examples/README.md).

## Compare or replay evidence

```bash
make diff RUN_A=examples/evidence_packs/dicom_metadata_pass \
  RUN_B=runs/my_demo
```

Replay a committed pack from its directory:

```bash
cd examples/evidence_packs/dicom_metadata_pass && ./replay.sh
```

See [`replay.md`](replay.md) for pack file names.

## Safety

- Do not use patient-identifiable data in public issues or PRs.
- Skills are engineering verification wrappers, not clinical tools.
- Read each skill's `limitations` and `intended_use.not_for` in the manifest.
