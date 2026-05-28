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

## Workflow 2: HoloHub imaging evidence (MVP)

**File:** [`holohub_imaging_evidence.yaml`](holohub_imaging_evidence.yaml)

**Path:**

```text
HoloHub fixture/source (DICOM CT series)
  -> holohub_imaging_ai_segmentator
  -> artifact inventory + container/HoloHub fingerprints (output.json)
  -> workflow summary
```

No paired verifier on this skill yet. Requires **GPU, Docker, `HOLOHUB_ROOT`**, and a
runnable DICOM directory (not committed — bake locally):

```bash
python3 skills/holohub-imaging-ai-segmentator/fixtures/build_dicom_from_nifti.py \
  .workbench_data/datasets/Task09_Spleen/imagesTr/spleen_10.nii.gz \
  .workbench_data/holohub_input/spleen_10

export HOLOHUB_ROOT=/path/to/holohub
make run-workflow-holohub-imaging \
  WORKFLOW_INPUT=.workbench_data/holohub_input/spleen_10 \
  WORKFLOW_HOLOHUB_IMAGING_OUT=runs/holohub_imaging_evidence
```

Inspect `holohub_app/skill_run/` for the trusted skill pack and verifier output;
`workflow_summary.json` includes `trust` and `stream` (flow-benchmark schedulers).
Reference pack:
[`holohub_imaging_ai_segmentator_pass`](../evidence_packs/holohub_imaging_ai_segmentator_pass/).

### Workflow 2 variant: endoscopy (trusted, known gap)

**File:** [`holohub_endoscopy_evidence.yaml`](holohub_endoscopy_evidence.yaml)

Runs trusted `holohub_endoscopy_tool_tracking` (detection export via log/sidecar)
+ `holohub_flow_benchmark` (endoscopy contract, smoke). Use `WORKFLOW_INPUT=default`
when HoloHub has provisioned sample data. The committed stub fixture is only a
boundary-check input; it is not a detection-quality pass case.

```bash
make run-workflow-holohub-endoscopy \
  HOLOHUB_ROOT=/path/to/holohub \
  WORKFLOW_INPUT=default
```

### Workflow 2 roadmap

| Phase | Status | Deliverable |
|-------|--------|-------------|
| 2a MVP | Done | Imaging + endoscopy workflow YAML, Makefile targets |
| 2b Flow benchmark | Done | Second step `holohub_flow_benchmark` + per-step `env` in workflow YAML |
| 2c Container provenance | Partial | `provenance.json` enriched from skill `invocation` (image id, commit, log tails) |
| 2d Detection export | Partial | `tool_detections.jsonl` from log parse or recording sidecar; full GXF decode still open |
| 2e Imaging verifier | Done | `holohub_imaging_segmentation_quality_v1`; imaging workflow uses `trusted: true` |
| 2f Stream linkage | Done | `workflow_summary.stream` — latency by scheduler, artifacts, contract/domain rollup |

## Other examples

- [`orientation_safe_segmentation.yaml`](orientation_safe_segmentation.yaml) — same steps as Workflow 1 (alias workflow id)
- [`abdomen_ct_summary.yaml`](abdomen_ct_summary.yaml) — convert → segment → LLM summarize (`fixture_template`)
