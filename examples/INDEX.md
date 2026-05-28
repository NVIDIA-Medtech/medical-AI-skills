# Examples index

Lightweight map for agents and reviewers. Full policy: [`README.md`](README.md).
Pack file names: [`docs/replay.md`](../docs/replay.md).

**Do not read every file.** Start here, then open one anchor pack.

## `evidence_packs/` -- canonical anchors

| Pack | Skill | Verdict | Teaches |
|---|---|---|---|
| `dicom_metadata_pass/` | dicom_metadata_extract | pass | Baseline DICOM metadata + gates |
| `dicom_metadata_trusted_warn/` | dicom_metadata_extract + dicom_metadata_quality_v1 | warn | Trusted run with PHI-tag advisory warning |
| `dicom_invalid_input_fail/` | dicom_metadata_extract | fail | Invalid input / preflight |
| `dicom_series_preflight_trusted_pass/` | dicom_series_preflight + dicom_preflight_quality_v1 | pass | Trusted DICOM preflight run with verifier pack and trust summary |
| `dicom_series_to_volume_pass/` | dicom_series_to_volume | pass | DICOM series to NIfTI |
| `dicom_series_to_volume_trusted_pass/` | dicom_series_to_volume + dicom_volume_quality_v1 | pass | Trusted conversion with NIfTI artifact verifier |
| `nv_segment_ct_pass/` | nv_segment_ct | pass | Segmentation happy path |
| `nv_segment_ct_trusted_pass/` | nv_segment_ct + ct_segmentation_quality_v1 | pass | Trusted CT segmentation with anatomy plausibility verifier |
| `nv_segment_ctmr_trusted_pass/` | nv_segment_ctmr + ct_segmentation_quality_v1 | pass | Trusted NV-Segment-CTMR CT-body CUDA run with generated label map referenced but not bundled |
| `nv_segment_ct_finetune_trusted_smoke_pass/` | nv_segment_ct_finetune + ct_segmentation_finetune_quality_v1 | pass | Trusted MONAI bundle smoke finetune run with checkpoint-load, finite-loss, no-OOM, and trajectory verifier |
| `nv_segment_ct_integrity_fail/` | nv_segment_ct | fail | Integrity scan |
| `nv_segment_ct_silent_failure_fail/` | nv_segment_ct | fail | Silent failure gate |
| `nv_generate_ct_rflow_pass/` | nv_generate_ct_rflow | pass | CT synthesis wrapper happy path |
| `nv_generate_ct_rflow_trusted_inventory_pass/` | nv_generate_ct_rflow + ct_synthesis_quality_v1 | pass | Trusted CUDA rflow-ct synthesis inventory run with geometry, HU, label-set, and hash evidence |
| `nv_generate_mr_trusted_inventory_pass/` | nv_generate_mr + mr_synthesis_quality_v1 | pass | Trusted CUDA rflow-mr synthesis inventory run with image bytes, hashes, and numeric sanity |
| `nv_generate_mr_brain_trusted_inventory_pass/` | nv_generate_mr_brain + mr_synthesis_quality_v1 | pass | Trusted CUDA rflow-mr-brain synthesis inventory run with image bytes, hashes, and numeric sanity |
| `nv_reason_cxr_trusted_mock_pass/` | nv_reason_cxr + nv_reason_cxr_quality_v1 | pass | Trusted mock CXR reasoning path with image/hash, runtime identity, and forbidden-phrase verifier |
| `benchmark_decathlon_spleen_clean/` | nv_segment_ct | pass | Benchmark loop clean |
| `benchmark_decathlon_with_corruption/` | nv_segment_ct | fail | Benchmark corruption |
| `benchmark_ct_segmentation_spleen_msd09_pass/` | nv_segment_ct | pass | CT segmentation benchmark evidence |
| `ct_segmentation_finetune_quality_v1_pass/` | ct_segmentation_finetune_quality_v1 | pass | Verifier-only anchor for finetune checkpoint, trajectory, dataset-audit, and label-coverage checks |

## `studies/` -- narrative

| Study | Topic |
|---|---|
| `with_vs_without_skill/*_codex_opus/` | Current Codex/GPT-5.5 and Opus direct with-vs-without study artifacts |
| `with_vs_without_skill/*_nemotron_correction/` | Current Nemotron no-repair baseline artifacts; suffix is historical |

## `workflows/`

| Workflow | Steps | Teaches |
|---|---|---|
| `dicom_preflight_gate.yaml` | trusted preflight | GPU-free pass/warn/fail preflight |
| `ct_dicom_to_segmentation_evidence.yaml` | convert -> trusted segment | DICOM to NIfTI to segment plus `ct_segmentation_quality_v1` trust summary |
| `orientation_safe_segmentation.yaml` | same as flagship | Orientation gate halts before VISTA3D |

## `drift/`

| Directory | Lesson |
|---|---|
| `baseline/` | Anchor pack for drift comparison |
| `environment_drift/` | Dependency / env change |
| `repeated_no_drift/` | Repeat run stability |

## Reading order

1. `python tools/render_review_packet.py <pack>`
2. `workflow_run_record.md`
3. `validation_summary.json`
4. `output.json` if present
5. `manifest.json`
6. `replay.sh` for optional rerun

## Commands

```bash
make review-packet PACK=examples/evidence_packs/dicom_series_preflight_trusted_pass
make review-packet PACK=examples/evidence_packs/nv_segment_ct_trusted_pass
python tools/render_review_packet.py examples/evidence_packs/dicom_metadata_trusted_warn
python tools/render_review_packet.py examples/evidence_packs/dicom_series_to_volume_trusted_pass
python tools/render_review_packet.py examples/evidence_packs/nv_generate_ct_rflow_trusted_inventory_pass
python tools/render_review_packet.py examples/evidence_packs/nv_reason_cxr_trusted_mock_pass
make diff RUN_A=examples/evidence_packs/dicom_metadata_pass RUN_B=runs/my_demo
cd examples/evidence_packs/dicom_metadata_pass && ./replay.sh
```
