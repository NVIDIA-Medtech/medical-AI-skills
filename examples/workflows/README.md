# Workflow examples

Workflows are **curated multi-skill recipes** for the trust/evidence path. They
are not publishable skills. Day-to-day use still starts with each skill's
[`SKILL.md`](../../skills/).

Run any workflow:

```bash
make run-workflow \
  WORKFLOW=examples/workflows/<file>.yaml \
  WORKFLOW_INPUT=<path-to-input> \
  WORKFLOW_OUT=runs/<run_id>
```

Output includes per-step evidence packs, `workflow_summary.json`, and
`workflow_run_record.md`. Steps halt on failure.

## Workflow 1: CT DICOM to segmentation evidence

**File:** [`ct_dicom_to_segmentation_evidence.yaml`](ct_dicom_to_segmentation_evidence.yaml)

**Path:**

```text
DICOM series
  -> dicom_series_to_volume (metadata + geometry preflight, DICOM-to-NIfTI)
  -> nv_segment_ct (trusted)
  -> ct_segmentation_quality_v1
  -> workflow / trust summary
```

| Step | Skill | Trusted verifier | Handoff |
|------|--------|------------------|---------|
| `convert` | `dicom_series_to_volume` | — | `${input}` DICOM directory → `output.path` NIfTI |
| `segment` | `nv_segment_ct` | `ct_segmentation_quality_v1` | `${convert.output.path}` |

**Run:**

```bash
make run-workflow-ct-seg \
  WORKFLOW_INPUT=/path/to/dicom_series \
  WORKFLOW_OUT=runs/ct_dicom_seg_evidence
```

Or:

```bash
make run-workflow \
  WORKFLOW=examples/workflows/ct_dicom_to_segmentation_evidence.yaml \
  WORKFLOW_INPUT=skills/dicom-series-to-volume/fixtures/clean_axial \
  WORKFLOW_OUT=runs/ct_dicom_seg_evidence
```

**What it proves:** orientation/spacing/geometry gates on conversion;
segmentation sanity checks; paired anatomy plausibility (and optional Dice when
ground truth is recorded). Halts before segmentation when convert fails (e.g.
LR-flipped orientation fixture `flipped_lr`).

**Not the primary skill path.** To run one tool on your data without evidence
packs, follow `skills/dicom-series-to-volume/SKILL.md` and
`skills/nv-segment-ct/SKILL.md` in sequence.

## A1: DICOM preflight gate

**File:** [`dicom_preflight_gate.yaml`](dicom_preflight_gate.yaml)

GPU-free pass/warn/fail preflight. See [`examples/README.md`](../README.md).

## Other examples

- [`orientation_safe_segmentation.yaml`](orientation_safe_segmentation.yaml) — same steps as Workflow 1 (alias workflow id)
