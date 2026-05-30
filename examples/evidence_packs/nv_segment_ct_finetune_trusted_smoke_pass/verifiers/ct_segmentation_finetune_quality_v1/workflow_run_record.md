# Workflow Run Record

- run id: 96da7fb4290e
- skill: medagent.verifiers.ct_segmentation_finetune_quality_v1 v0.1.0
- started: 2026-05-26T04:18:27.212241+00:00
- finished: 2026-05-26T04:18:28.415074+00:00
- elapsed: 1.203s
- exit code: 0

## Skill
- dir: verifiers/ct_segmentation_finetune_quality_v1
- entrypoint: scripts/grade.py

## Fixture
- path: runs/nv_segment_ct_finetune_trusted_smoke_pass/skill_run
- sha256: e657adcb371d9c81b9ad67f3f39dcf8ff4e360dbea9402b0e094265235ab0463
- size: 872029992 bytes

## Validation
- overall: passed
- schema: passed
- sanity: passed
- runtime: within_envelope
- cost: skipped
- env_pin: skipped
- integrity: clean

## Output (excerpt)
```json
{
  "artifact_inventory": {
    "checkpoint_loadable": true,
    "checkpoint_param_count": 217965054,
    "checkpoint_path": "<repo>/runs/nv_segment_ct_finetune_trusted_smoke_pass/skill_run/artifacts/checkpoints/model_finetune.pt",
    "checkpoint_resolved": true,
    "checkpoint_size_bytes": 871971832,
    "torch_available": true
  },
  "dataset_audit_review": {
    "anatomy": null,
    "anatomy_volume_all_in_range": null,
    "failed_checks": [],
    "hu_range_negative_present": null,
    "image_looks_like_ct": null,
    "orientation_consistent": null,
    "shape_consistent": null,
    "verdict": "pass"
  },
  "label_coverage": {
    "missing_user_labels": [],
    "user_labels_declared": [
      1
    ],
    "user_labels_seen_in_sample": [],
    "verdict": "skipped"
  },
  "overall": "pass",
  "target": {
    "checkpoint_path": "<repo>/runs/nv_segment_ct_finetune_trusted_smoke_pass/skill_run/artifacts/checkpoints/model_finetune.pt",
    "evidence_pack": "<repo>/runs/nv_segment_ct_finetune_trusted_smoke_pass/skill_run",
    "sanity": false,
    "skill_id": "medagent.nv_segment_ct_finetune",
    "smoke": true,
    "source_overall_status": "passed"
  },
  "training_trajectory": {
    "baseline_val_dice": 0.0,
    "best_val_dice": 0.0002,
    "epochs_declared": 2,
    "epochs_recorded": 3,
    "failed_checks": [],
    "improvement_over_baseline": 0.0002,
    "oom": false,
    "regres
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.