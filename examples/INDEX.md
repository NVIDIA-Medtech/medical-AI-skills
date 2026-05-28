# Examples index

Lightweight map for agents and reviewers. Full policy: [`README.md`](README.md).
Pack file names: [`docs/replay.md`](../docs/replay.md).

**Do not read every file.** Start here, then open one anchor pack.

## `evidence_packs/` — canonical anchors

| Pack | Skill | Verdict | Teaches |
|---|---|---|---|
| `find_skills_trusted_pass/` | find_skills + find_skills_quality_v1 | pass | Trusted selector run with manifest consistency verifier |
| `dicom_metadata_pass/` | dicom_metadata_extract | pass | Baseline DICOM metadata + gates |
| `dicom_metadata_trusted_warn/` | dicom_metadata_extract + dicom_metadata_quality_v1 | warn | Trusted run with PHI-tag advisory warning |
| `dicom_invalid_input_fail/` | dicom_metadata_extract | fail | Invalid input / preflight |
| `dicom_series_preflight_trusted_pass/` | dicom_series_preflight + dicom_preflight_quality_v1 | pass | Trusted run with verifier pack and trust summary |
| `dicom_series_to_volume_pass/` | dicom_series_to_volume | pass | Series → NIfTI |
| `dicom_series_to_volume_trusted_pass/` | dicom_series_to_volume + dicom_volume_quality_v1 | pass | Trusted conversion with NIfTI artifact verifier |
| `nv_segment_ct_pass/` | nv_segment_ct | pass | Segmentation happy path |
| `nv_segment_ct_trusted_pass/` | nv_segment_ct + ct_segmentation_quality_v1 | pass | Trusted CT segmentation with anatomy plausibility verifier |
| `nv_segment_ctmr_trusted_pass/` | nv_segment_ctmr + ct_segmentation_quality_v1 | pass | Trusted NV-Segment-CTMR CT-body CUDA run with MONAI bundle entrypoint, model inventory, CT anatomy plausibility, and generated label map referenced but not bundled |
| `nv_segment_ct_finetune_trusted_smoke_pass/` | nv_segment_ct_finetune + ct_segmentation_finetune_quality_v1 | pass | Trusted MONAI bundle smoke finetune run with checkpoint-load, finite-loss, no-OOM, and trajectory verifier; plumbing evidence only |
| `nv_segment_ct_integrity_fail/` | nv_segment_ct | fail | Integrity scan |
| `nv_segment_ct_silent_failure_fail/` | nv_segment_ct | fail | Silent failure gate |
| `nv_generate_ct_rflow_trusted_inventory_pass/` | nv_generate_ct_rflow + ct_synthesis_quality_v1 | pass | Trusted CUDA rflow-ct synthesis inventory run with image/label bytes, hashes, geometry, HU plausibility, label-set sanity, and generated NIfTI volumes referenced but not bundled |
| `nv_generate_mr_trusted_inventory_pass/` | nv_generate_mr + mr_synthesis_quality_v1 | pass | Trusted CUDA rflow-mr synthesis inventory run with image bytes, hashes, requested geometry, finite nonconstant nonnegative voxels, and generated NIfTI volumes referenced but not bundled |
| `nv_generate_mr_brain_trusted_inventory_pass/` | nv_generate_mr_brain + mr_synthesis_quality_v1 | pass | Trusted CUDA rflow-mr-brain synthesis inventory run with image bytes, hashes, requested geometry, finite nonconstant nonnegative voxels, and generated NIfTI volumes referenced but not bundled |
| `nv_reason_cxr_trusted_mock_pass/` | nv_reason_cxr + nv_reason_cxr_quality_v1 | pass | Trusted mock CXR reasoning path with image/hash, runtime identity, and forbidden-phrase verifier |
| `radiology_note_summarizer_trusted_mock_pass/` | radiology_note_summarizer + radiology_note_summary_quality_v1 | pass | Trusted mock LLM path with fact echo, prompt identity, and forbidden-phrase verifier |
| `holohub_flow_benchmark_trusted_stub_pass/` | holohub_flow_benchmark + holohub_flow_benchmark_quality_v1 | pass | Trusted stub benchmark path with logger/GPU artifact hashes, scheduler coverage, latency samples, and contract assertions; not real app performance evidence |
| `benchmark_decathlon_spleen_clean/` | nv_segment_ct | pass | Benchmark loop clean |
| `benchmark_decathlon_with_corruption/` | nv_segment_ct | fail | Benchmark corruption |
| `holohub_imaging_ai_segmentator_pass/` | holohub_imaging_ai_segmentator | pass | HoloHub CT seg |
| `holohub_imaging_ai_segmentator_trusted_inventory_pass/` | holohub_imaging_ai_segmentator + holohub_imaging_segmentation_quality_v1 | pass | Trusted HoloHub imaging inventory run with DICOM SEG/NIfTI counts, hashes, positive segmentation signal, and verifier summary; large artifacts are referenced, not bundled |
| `holohub_endoscopy_tool_tracking_pass/` | holohub_endoscopy_tool_tracking | pass | Endoscopy app |
| `holohub_endoscopy_tool_tracking_trusted_detection_pass/` | holohub_endoscopy_tool_tracking + endoscopy_tool_detection_quality_v1 | pass | Trusted HoloHub endoscopy run with GXF recording hashes, log-parsed detection sidecar, frame coverage, bbox sanity, tool classes, and large artifacts referenced but not bundled |
| `totalsegmentator_trusted_pass/` | totalsegmentator + totalsegmentator_quality_v1 | pass | Trusted TotalSegmentator CUDA run with multilabel inventory, geometry, organ-volume plausibility, and generated NIfTI referenced but not bundled |
| `ct_segmentation_finetune_quality_v1_pass/` | ct_segmentation_finetune_quality_v1 | pass | Verifier-only anchor for finetune checkpoint, trajectory, dataset-audit, and label-coverage checks |
| `endoscopy_tool_detection_quality_v1_pass/` | endoscopy_tool_detection_quality_v1 | pass | Verifier-only anchor for decoded endoscopy detection sidecar, recording inventory, tool-count, coverage, and bbox sanity checks |
| `totalsegmentator_quality_v1_pass/` | totalsegmentator_quality_v1 | pass | Verifier-only anchor for TotalSegmentator anatomy plausibility on a synthetic mask; generated NIfTI referenced but not bundled |
| `totalsegmentator_hu_consistency_v1_pass/` | totalsegmentator_hu_consistency_v1 | pass | Verifier-only anchor for TotalSegmentator HU consistency on synthetic CT/mask inputs; generated NIfTI referenced but not bundled |
| `totalsegmentator_skeleton_topology_v1_pass/` | totalsegmentator_skeleton_topology_v1 | pass | Verifier-only anchor for TotalSegmentator skeleton topology on a synthetic mask; generated NIfTI referenced but not bundled |

## `studies/` — narrative (non-canonical list)

| Study | Topic |
|---|---|
| `multi_llm_observatory/` | LLM model comparison on radiology summarizer |
| `subtle_defect/` | Strict vs permissive LLM gate behavior |
| `optimizer_loop_iteration_1/` | Iterative gate tuning narrative |
| `skill_completeness_audit_pre_fix/` | Completeness verifier before fix |
| `skill_completeness_audit_post_fix/` | Completeness verifier after fix |
| `with_vs_without_skill/*_codex_opus/` | Current Codex/GPT-5.5 and Opus direct with-vs-without study artifacts |
| `with_vs_without_skill/*_nemotron_correction/` | Current Nemotron no-repair baseline artifacts; suffix is historical |

## `workflows/`

| Workflow | Steps | Teaches |
|---|---|---|
| `dicom_preflight_gate.yaml` | trusted preflight | **A1 onboarding:** GPU-free pass/warn/fail preflight |
| `ct_dicom_to_segmentation_evidence.yaml` | convert → trusted segment | Workflow 1: DICOM→NIfTI→segment+`ct_segmentation_quality_v1`→trust summary |
| `holohub_imaging_evidence.yaml` | HoloHub CT seg app | **Workflow 2 MVP:** artifact inventory + container fingerprints (GPU) |
| `holohub_endoscopy_evidence.yaml` | HoloHub endoscopy + verifier | Workflow 2 variant; verifier gap (S4) until detections emitted |
| `orientation_safe_segmentation.yaml` | same as flagship (alias id) | Orientation gate halts before VISTA3D |
| `abdomen_ct_summary.yaml` | convert → segment → LLM summarize | Multi-step + composed fixture |

## `drift/`

| Directory | Lesson |
|---|---|
| `baseline/` | Anchor pack for drift comparison |
| `environment_drift/` | Dependency / env change |
| `repeated_no_drift/` | Repeat run stability |

## Reading order (any pack)

1. `python tools/render_review_packet.py <pack>`
2. `workflow_run_record.md`
3. `validation_summary.json`
4. `output.json` (if present)
5. `manifest.json`
6. `replay.sh` (optional rerun)

## Commands

```bash
make review-packet PACK=examples/evidence_packs/dicom_series_preflight_trusted_pass
make review-packet PACK=examples/evidence_packs/nv_segment_ct_trusted_pass
make review-packet PACK=examples/evidence_packs/totalsegmentator_trusted_pass
python tools/render_review_packet.py examples/evidence_packs/dicom_metadata_trusted_warn
python tools/render_review_packet.py examples/evidence_packs/find_skills_trusted_pass
python tools/render_review_packet.py examples/evidence_packs/dicom_series_preflight_trusted_pass
python tools/render_review_packet.py examples/evidence_packs/dicom_series_to_volume_trusted_pass
python tools/render_review_packet.py examples/evidence_packs/nv_segment_ct_trusted_pass
python tools/render_review_packet.py examples/evidence_packs/nv_segment_ctmr_trusted_pass
python tools/render_review_packet.py examples/evidence_packs/nv_segment_ct_finetune_trusted_smoke_pass
python tools/render_review_packet.py examples/evidence_packs/nv_generate_ct_rflow_trusted_inventory_pass
python tools/render_review_packet.py examples/evidence_packs/nv_generate_mr_trusted_inventory_pass
python tools/render_review_packet.py examples/evidence_packs/nv_generate_mr_brain_trusted_inventory_pass
python tools/render_review_packet.py examples/evidence_packs/holohub_flow_benchmark_trusted_stub_pass
python tools/render_review_packet.py examples/evidence_packs/holohub_imaging_ai_segmentator_trusted_inventory_pass
python tools/render_review_packet.py examples/evidence_packs/holohub_endoscopy_tool_tracking_trusted_detection_pass
python tools/render_review_packet.py examples/evidence_packs/totalsegmentator_trusted_pass
python tools/render_review_packet.py examples/evidence_packs/ct_segmentation_finetune_quality_v1_pass
python tools/render_review_packet.py examples/evidence_packs/endoscopy_tool_detection_quality_v1_pass
python tools/render_review_packet.py examples/evidence_packs/totalsegmentator_quality_v1_pass
python tools/render_review_packet.py examples/evidence_packs/totalsegmentator_hu_consistency_v1_pass
python tools/render_review_packet.py examples/evidence_packs/totalsegmentator_skeleton_topology_v1_pass
python tools/render_review_packet.py examples/evidence_packs/nv_reason_cxr_trusted_mock_pass
python tools/render_review_packet.py examples/evidence_packs/radiology_note_summarizer_trusted_mock_pass
make diff RUN_A=examples/evidence_packs/dicom_metadata_pass RUN_B=runs/my_demo
cd examples/evidence_packs/dicom_metadata_pass && ./replay.sh
```
