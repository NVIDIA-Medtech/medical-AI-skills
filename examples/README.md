# Examples

Committed examples show evidence-pack shape and gate behavior. They are
engineering records, not clinical or regulatory artifacts.

Agent navigation: start with [`INDEX.md`](INDEX.md) for anchor packs before
opening study trees.

## Layout

```text
examples/
  evidence_packs/     # canonical single-run pass/fail packs
  studies/            # narrative multi-pack demos
  drift/              # drift comparison examples
  fixtures/           # tiny shared example inputs
  workflows/          # workflow YAML examples
```

## Reading examples

Start with `workflow_run_record.md`, then inspect:

- `validation_summary.json` for gate status
- `output.json` for parsed skill output
- `manifest.json` for command, fixture, and file inventory
- `runtime_profile.json`, `cost_profile.json`, and `environment.lock` for
  reproducibility context

The canonical file list is in [`docs/replay.md`](../docs/replay.md).

## Baselines

`*_pass/` and `*_clean/` packs are drift anchors for the same spec. They
are not cross-skill comparisons and should not be read as performance ordering.

Important anchors:

- `find_skills_trusted_pass/`
- `dicom_metadata_pass/`
- `dicom_metadata_trusted_warn/`
- `dicom_series_preflight_trusted_pass/`
- `dicom_series_to_volume_pass/`
- `dicom_series_to_volume_trusted_pass/`
- `nv_segment_ct_pass/`
- `nv_segment_ct_trusted_pass/`
- `nv_segment_ctmr_trusted_pass/`
- `nv_segment_ct_finetune_trusted_smoke_pass/`
- `nv_generate_ct_rflow_trusted_inventory_pass/`
- `nv_generate_mr_trusted_inventory_pass/`
- `nv_generate_mr_brain_trusted_inventory_pass/`
- `nv_reason_cxr_trusted_mock_pass/`
- `radiology_note_summarizer_trusted_mock_pass/`
- `holohub_flow_benchmark_trusted_stub_pass/`
- `benchmark_decathlon_spleen_clean/`
- `holohub_imaging_ai_segmentator_pass/`
- `holohub_imaging_ai_segmentator_trusted_inventory_pass/`
- `holohub_endoscopy_tool_tracking_pass/` (wrapper execution anchor; the
  committed pack does not include decoded detections and is not a paired
  verifier pass)
- `holohub_endoscopy_tool_tracking_trusted_detection_pass/`
- `totalsegmentator_trusted_pass/`
- `ct_segmentation_finetune_quality_v1_pass/`
- `endoscopy_tool_detection_quality_v1_pass/`
- `totalsegmentator_quality_v1_pass/`
- `totalsegmentator_hu_consistency_v1_pass/`
- `totalsegmentator_skeleton_topology_v1_pass/`

Negative packs intentionally fail specific gates, such as invalid DICOM input,
silent segmentation failure, integrity failure, benchmark corruption, or
spec-completeness failures.

Study packs under `examples/studies/` are useful reading, but they are not the
canonical list. Current studies include `multi_llm_observatory/`,
`optimizer_loop_iteration_1/`, `subtle_defect/`,
`skill_completeness_audit_*`, and
the current `with_vs_without_skill/*_codex_opus/` and
`with_vs_without_skill/*_nemotron_correction/` result sets summarized in
[`docs/with-vs-without-skill-experiment.md`](../docs/with-vs-without-skill-experiment.md).

Regenerate or compare examples with `make run-skill`, `make run-benchmark`,
and `make diff`.

`evidence_packs/find_skills_trusted_pass/` is the GPU-free selector trust
anchor. It pairs `find_skills` with `find_skills_quality_v1` to confirm rank
ordering, manifest path/id consistency, no-fit semantics, and selector-scope
disclosure for the repository fixture query.

`evidence_packs/radiology_note_summarizer_trusted_mock_pass/` is the
deterministic mock LLM trust anchor. It pairs `radiology_note_summarizer` with
`radiology_note_summary_quality_v1` to confirm source-pack success, factual
echo, model/prompt identity, and forbidden-phrase guardrails without sending
data to the hosted LLM API.

`evidence_packs/nv_reason_cxr_trusted_mock_pass/` is the deterministic mock
CXR reasoning trust anchor. It pairs `nv_reason_cxr` with
`nv_reason_cxr_quality_v1` to confirm generated synthetic image handling,
image hash binding, runtime identity, response non-emptiness, scope disclosure,
and forbidden-phrase guardrails without downloading model weights.

`evidence_packs/nv_generate_ct_rflow_trusted_inventory_pass/` is the CT
synthesis trusted inventory anchor. It pairs `nv_generate_ct_rflow` with
`ct_synthesis_quality_v1` to confirm a real CUDA rflow-ct run, generated
image/label artifact bytes and hashes, geometry consistency, CT-HU range
floors, label-set sanity, model inventory, and GPU provenance without
committing the generated NIfTI volumes.

`evidence_packs/nv_generate_mr_trusted_inventory_pass/` and
`evidence_packs/nv_generate_mr_brain_trusted_inventory_pass/` are the MR
synthesis trusted inventory anchors. They pair the image-only MR wrappers with
`mr_synthesis_quality_v1` to confirm real CUDA rflow-mr/rflow-mr-brain runs,
generated image bytes and hashes, requested geometry, finite nonconstant
nonnegative voxel values, model inventory, and GPU provenance without
committing generated NIfTI volumes.

`evidence_packs/holohub_flow_benchmark_trusted_stub_pass/` is the deterministic
stub HoloHub benchmark trust anchor. It pairs `holohub_flow_benchmark` with
`holohub_flow_benchmark_quality_v1` to confirm logger and GPU artifact hashes,
scheduler coverage, latency sample parsing, benchmark-log completion, contract
assertions, and review-packet visibility. It is not real HoloHub app
performance evidence; use a full HoloHub run for performance claims.

`evidence_packs/holohub_imaging_ai_segmentator_trusted_inventory_pass/` is the
HoloHub imaging inventory trust anchor. It pairs
`holohub_imaging_ai_segmentator` with
`holohub_imaging_segmentation_quality_v1` to confirm the app run, DICOM SEG and
NIfTI inventory, non-zero segmentation signal, container provenance, and
verifier summary without committing the large generated DICOM SEG/NIfTI
artifacts.

`evidence_packs/holohub_endoscopy_tool_tracking_trusted_detection_pass/` is the
HoloHub endoscopy detection trust anchor. It pairs
`holohub_endoscopy_tool_tracking` with
`endoscopy_tool_detection_quality_v1` on the documented `default` sample path
to confirm the HoloHub container run, GXF recording artifact hashes, decoded
`tool_detections.jsonl` export, frame coverage, tool-count, bbox sanity, and
observed tool classes. The generated GXF pair, detection sidecar, Docker layers,
and model artifacts are referenced by path, hash, and verifier facts but are not
committed.

`evidence_packs/nv_segment_ct_finetune_trusted_smoke_pass/` is the
NV-Segment-CT continual-finetune smoke trust anchor. It pairs
`nv_segment_ct_finetune` with `ct_segmentation_finetune_quality_v1` on the
four-case `spleen_micro` fixture to confirm the MONAI bundle launches, writes a
checkpoint, has finite training loss, avoids OOM, records a validation
trajectory, and passes checkpoint-load inspection. It is plumbing evidence only
and does not replace the Task06 Lung Tumor sanity run or convergence-quality
evidence. The generated 872 MB checkpoint is referenced by path, size, and
verifier facts but is not committed.

`evidence_packs/totalsegmentator_trusted_pass/` is the TotalSegmentator
user-facing trust anchor. It pairs `totalsegmentator` with
`totalsegmentator_quality_v1` on the shared spleen CT fixture to confirm the
official Python API ran with `ml=True`, emitted a multilabel mask, preserved
input geometry, produced task-valid labels, and passed organ-volume,
fragmentation, liver>spleen, and bilateral-kidney plausibility checks. The
generated NIfTI is referenced by path and verifier facts but is not committed.

`evidence_packs/nv_segment_ctmr_trusted_pass/` is the NV-Segment-CTMR CT-body
trust anchor. It pairs `nv_segment_ctmr` with `ct_segmentation_quality_v1` on
the shared spleen CT fixture to confirm the upstream MONAI bundle entrypoint
ran on CUDA, loaded the pinned model inventory, preserved input geometry,
emitted task-valid CT-body labels, and passed organ-volume, fragmentation,
liver>spleen, and bilateral-kidney plausibility checks. The generated label-map
NIfTI is referenced by path and verifier facts but is not committed. The CT
verifier support is intentionally limited to CT_BODY; MRI_BODY and MRI_BRAIN
need modality-specific verifier anchors.

Verifier-only anchors close trust-layer lifecycle gaps without claiming that
the corresponding heavy upstream skill has a trusted run. The
`ct_segmentation_finetune_quality_v1_pass/` pack audits a committed synthetic
finetune fixture. The `endoscopy_tool_detection_quality_v1_pass/` pack audits
the verifier's tiny committed positive fixture with a decoded
`tool_detections.jsonl` sidecar; it does not make the HoloHub wrapper itself a
trusted detection run. The three `totalsegmentator_*_v1_pass/` packs audit
synthetic verifier inputs generated under `runs/`; the generated NIfTI files
are referenced by path, byte count, and SHA-256 hash but are not committed.

## Flagship workflow A1: DICOM preflight gate (start here)

GPU-free trusted preflight for a DICOM folder:

```bash
make run-workflow \
  WORKFLOW=examples/workflows/dicom_preflight_gate.yaml \
  WORKFLOW_INPUT=skills/dicom-series-preflight/fixtures/clean_no_phi \
  WORKFLOW_OUT=runs/dicom_preflight_gate
```

| Fixture | Expected workflow `overall` |
|---|---|
| `fixtures/clean_no_phi` | `passed` |
| `fixtures/clean_axial` | `warn` (PHI tags populated) |
| `fixtures/flipped_lr` | `failed` (orientation gate) |

Canonical trusted-run anchor:
`evidence_packs/dicom_series_preflight_trusted_pass/` contains the same
GPU-free clean-no-PHI path as a committed trusted run: `skill_run/`,
`verifiers/dicom_preflight_quality_v1/`, and `trust_summary.json`.

The smaller single-file DICOM metadata anchor
`evidence_packs/dicom_metadata_trusted_warn/` demonstrates trusted-run warning
semantics: the skill gates pass, `dicom_metadata_quality_v1` accepts the pack,
and the trust summary records standard PHI tag presence as a warning rather
than treating it as de-identification proof.

The DICOM-to-volume trusted anchor
`evidence_packs/dicom_series_to_volume_trusted_pass/` contains the conversion
pack, the emitted `volume.nii.gz`, `verifiers/dicom_volume_quality_v1/`, and a
trust summary that checks the NIfTI artifact against reported geometry and voxel
range evidence.

## Flagship workflow 1: CT DICOM to segmentation evidence

**Path:**

```text
DICOM series
  -> dicom_series_to_volume (metadata + geometry preflight, DICOM-to-NIfTI)
  -> nv_segment_ct (trusted)
  -> ct_segmentation_quality_v1
  -> workflow / trust summary
```

Workflow 1 chains `dicom_series_to_volume` with a **trusted** `nv_segment_ct`
step that runs `ct_segmentation_quality_v1` on the segmentation pack. Full spec:
[`workflows/README.md`](workflows/README.md).

Canonical direct CT segmentation trusted anchor:
`evidence_packs/nv_segment_ct_trusted_pass/` contains the VISTA3D wrapper
pack, the `ct_segmentation_quality_v1` verifier pack, and a trust summary with
anatomy plausibility, label-set containment, and artifact-hash evidence for the
local spleen fixture.

```bash
# Positive path (clean axial synthetic CT series)
make run-workflow \
  WORKFLOW=examples/workflows/ct_dicom_to_segmentation_evidence.yaml \
  WORKFLOW_INPUT=skills/dicom-series-to-volume/fixtures/clean_axial \
  WORKFLOW_OUT=runs/ct_dicom_seg_evidence

# Negative path (LR-flipped IOP — halts at convert, segment never runs)
make run-workflow \
  WORKFLOW=examples/workflows/ct_dicom_to_segmentation_evidence.yaml \
  WORKFLOW_INPUT=skills/dicom-series-to-volume/fixtures/flipped_lr \
  WORKFLOW_OUT=runs/ct_dicom_seg_flipped_fail
```

## Flagship workflow 2: HoloHub imaging evidence (MVP)

**Path:**

```text
HoloHub fixture/source
  -> holohub_imaging_ai_segmentator (trusted)
  -> holohub_imaging_segmentation_quality_v1
  -> holohub_flow_benchmark (smoke)
  -> workflow summary (+ stream linkage)
```

Requires `HOLOHUB_ROOT`, GPU, Docker, and a local DICOM series (rebake with
`skills/holohub-imaging-ai-segmentator/fixtures/build_dicom_from_nifti.py`). Full
spec: [`workflows/README.md`](workflows/README.md).

Canonical inventory-level trusted anchor:
`evidence_packs/holohub_imaging_ai_segmentator_trusted_inventory_pass/`
contains a current-format skill pack, verifier pack, provenance, and trust
summary. It references the generated DICOM SEG/NIfTI artifact hashes and sizes
but does not bundle those large medical artifacts.

```bash
export HOLOHUB_ROOT=/path/to/holohub
make run-workflow-holohub-imaging \
  WORKFLOW_INPUT=.workbench_data/holohub_input/spleen_10 \
  WORKFLOW_HOLOHUB_IMAGING_OUT=runs/holohub_imaging_evidence
```

Endoscopy variant (trusted + flow benchmark; detection export via log/sidecar):
`holohub_endoscopy_evidence.yaml`.

For a compact flow-benchmark trust reference without running the full HoloHub
app, inspect `evidence_packs/holohub_flow_benchmark_trusted_stub_pass/`.
It exercises the benchmark wrapper and verifier against a deterministic stub
and deliberately does not claim real latency performance.

Inspect `WORKFLOW_OUT/workflow_summary.json` for per-step status and
`trust` linkage; the segment step writes `segment/trust_summary.json` and
`segment/skill_run/` when the convert step passes.

On the committed `clean_axial` synthetic series, segmentation often passes
skill gates while `ct_segmentation_quality_v1` fails anatomy-plausibility
bounds (tiny phantom volumes). That is expected engineering behavior, not a
workflow bug — the workflow still produces conversion, segmentation, and
verifier evidence packs in one run.

## Contribution policy

External contributions are welcome when the example is curated evidence, not
a dumped local run. Acceptable additions:

- a small pass pack for a new or changed spec
- a negative pack that proves a gate fails correctly
- a drift example with a clear lesson
- a compact study that connects several evidence packs

Generated work starts in `runs/`. Promote only the small, sanitized subset that
should become a shared reading or regression artifact. Never commit patient
data, large medical volumes, model weights, raw recordings, secrets, or bulky
provider logs.

Verifier anti-patterns and negative fixtures live with the owning verifier
under `verifiers/<name>/fixtures/`.
