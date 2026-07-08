# Examples

Committed examples show evidence-pack shape and gate behavior. They are
engineering records, not clinical or regulatory artifacts.

Agent navigation: start with [`INDEX.md`](INDEX.md) for anchor packs before
opening study trees.

## Layout

```text
examples/
  evidence_packs/     # canonical single-run pass/fail packs
  dependency_locks/   # exact tested dependency resolutions; evidence only
  studies/            # compact narrative studies only; generated records stay ignored
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

Committed example `environment.lock` files are compacted to the packages used
by env-pin checks. Regenerate a pack under `runs/` when you need a full local
`pip freeze`.

`dependency_locks/` records exact versions that completed cross-skill checks.
These JSON files are evidence snapshots, not install inputs and not a second
dependency owner; skills continue to use upstream requirements or declared
compatibility ranges.

The canonical file list is in [`docs/replay.md`](../docs/replay.md).

## Baselines

`*_pass/` and `*_clean/` packs are drift anchors for the same spec. They
are not cross-skill comparisons and should not be read as performance ordering.

This branch keeps DICOM utilities and NVIDIA-Medtech `nv-*` skills only.
Important anchors:

- `dicom_metadata_pass/`
- `dicom_metadata_trusted_warn/`
- `dicom_series_preflight_trusted_pass/`
- `dicom_series_to_volume_pass/`
- `dicom_series_to_volume_trusted_pass/`
- `nv_segment_ct_pass/`
- `nv_segment_ct_trusted_pass/`
- `nv_segment_ctmr_trusted_pass/`
- `nv_segment_ct_finetune_trusted_smoke_pass/`
- `nv_generate_ct_rflow_pass/`
- `nv_generate_ct_rflow_trusted_inventory_pass/`
- `nv_generate_mr_trusted_inventory_pass/`
- `nv_generate_mr_brain_trusted_inventory_pass/`
- `nv_reason_cxr_trusted_mock_pass/`
- `benchmark_decathlon_spleen_clean/`
- `benchmark_decathlon_with_corruption/`
- `benchmark_ct_segmentation_spleen_msd09_pass/`
- `ct_segmentation_finetune_quality_v1_pass/`

Negative packs intentionally fail specific gates, such as invalid DICOM input,
silent segmentation failure, integrity failure, benchmark corruption, or
spec-completeness failures.

Study packs under `examples/studies/` are optional narrative records, not the
canonical list. Generated with-vs-without study records now stay under
`runs/with_vs_without_nv/studies/`, with the checked-in summary at
[`docs/with-vs-without-skill-experiment.md`](../docs/with-vs-without-skill-experiment.md).

Regenerate or compare examples with `make run-skill`, `make run-benchmark`,
and `make diff`.

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

`evidence_packs/nv_segment_ct_finetune_trusted_smoke_pass/` is the
NV-Segment-CT continual-finetune smoke trust anchor. It pairs
`nv_segment_ct_finetune` with `ct_segmentation_finetune_quality_v1` on the
four-case `spleen_micro` fixture to confirm the MONAI bundle launches, writes a
checkpoint, has finite training loss, avoids OOM, records a validation
trajectory, and passes checkpoint-load inspection. It is plumbing evidence only
and does not replace the Task06 Lung Tumor sanity run or convergence-quality
evidence. The generated 872 MB checkpoint is referenced by path, size, and
verifier facts but is not committed.

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
finetune fixture.

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
data, large medical volumes, model weights, raw recordings, secrets, bulky
provider logs, raw provider responses, per-repeat study JSON, detailed
generated reports, or runtime environments.

Verifier anti-patterns and negative fixtures live with the owning verifier
under `verifiers/<name>/fixtures/`.
