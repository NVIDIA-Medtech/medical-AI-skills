# Workflow Run Record

- run id: c33412537b18
- skill: medagent.verifiers.ct_segmentation_finetune_quality_v1 v0.1.0
- started: 2026-05-26T03:58:42.715302+00:00
- finished: 2026-05-26T03:58:43.915915+00:00
- elapsed: 1.201s
- exit code: 0

## Skill
- dir: verifiers/ct_segmentation_finetune_quality_v1
- entrypoint: scripts/grade.py

## Fixture
- path: verifiers/ct_segmentation_finetune_quality_v1/fixtures/pass_pack
- sha256: bd6607307c38171718a9e6b324c6ccb63d1bc59dc6d0cac04f4ef81be3e547b8
- size: 2568309 bytes

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
    "checkpoint_param_count": 640800,
    "checkpoint_path": "checkpoint.pt",
    "checkpoint_resolved": true,
    "checkpoint_size_bytes": 2565117,
    "torch_available": true
  },
  "dataset_audit_review": {
    "anatomy": "spleen",
    "anatomy_volume_all_in_range": true,
    "failed_checks": [],
    "hu_range_negative_present": true,
    "image_looks_like_ct": true,
    "orientation_consistent": true,
    "shape_consistent": true,
    "verdict": "pass"
  },
  "label_coverage": {
    "missing_user_labels": [],
    "user_labels_declared": [
      1
    ],
    "user_labels_seen_in_sample": [
      1
    ],
    "verdict": "pass"
  },
  "overall": "pass",
  "target": {
    "checkpoint_path": "checkpoint.pt",
    "evidence_pack": "<repo>/verifiers/ct_segmentation_finetune_quality_v1/fixtures/pass_pack",
    "sanity": false,
    "skill_id": "nv_segment_ct_finetune",
    "smoke": false,
    "source_overall_status": "passed"
  },
  "training_trajectory": {
    "baseline_val_dice": 0.45,
    "best_val_dice": 0.72,
    "epochs_declared": 3,
    "epochs_recorded": 3,
    "failed_checks": [],
    "improvement_over_baseline": 0.27,
    "oom": false,
    "regressed": false,
    "sanity_recovery_demonstrated": null,
    "train_loss_finite": true,
    "verdict": "pass"
  },
  "verifier": {
    "id": "medagent.verifiers.ct_segmentation_finetune_quality_v1",
    "version": "0.1.0"
  }
}
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.