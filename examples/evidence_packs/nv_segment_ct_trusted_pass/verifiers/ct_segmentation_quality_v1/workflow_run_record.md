# Workflow Run Record

- run id: 1f36db3ad0b9
- skill: medagent.verifiers.ct_segmentation_quality_v1 v0.1.0
- started: 2026-05-26T01:48:11.428534+00:00
- finished: 2026-05-26T01:48:12.497677+00:00
- elapsed: 1.069s
- exit code: 0

## Skill
- dir: verifiers/ct_segmentation_quality_v1
- entrypoint: scripts/grade.py

## Fixture
- path: examples/evidence_packs/nv_segment_ct_trusted_pass/skill_run
- sha256: 78da76edcd7f22bc626667a5ee638778b528e07fe521096dcdbdc988e1fcdd97
- size: 26525 bytes

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
  "anatomy_plausibility": {
    "checks": [
      {
        "name": "label_map_present",
        "reason": "loaded skills/nv-segment-ct/fixtures/spleen_03_vista3d_out/spleen_03/spleen_03_seg.nii.gz",
        "status": "pass"
      },
      {
        "name": "any_class_present",
        "reason": "label_ids_present=[1, 3, 5, 14]",
        "status": "pass"
      },
      {
        "failing": [],
        "name": "all_classes_within_volume_bounds",
        "reason": "all per-class volumes within population bounds",
        "status": "pass"
      },
      {
        "failing": [],
        "name": "no_fragmented_classes",
        "reason": "no class exceeds CC cap or fails largest-CC fraction",
        "status": "pass"
      },
      {
        "name": "liver_gt_spleen",
        "reason": "liver=1245.3886 mL > spleen=163.9564 mL",
        "status": "pass"
      },
      {
        "name": "bilateral_symmetry",
        "reason": "worst relative_diff=0.030 <= 0.5",
        "status": "pass"
      }
    ],
    "classes_failing_volume_bounds": [],
    "classes_overfragmented": [],
    "cross_class": {
      "bilateral_symmetry": {
        "pairs": [
          {
            "label_ids": [
              5,
              14
            ],
            "names": [
              "label_id_5",
              "label_id_14"
            ],
            "ok": true,
            "relative_diff": 0.0302,
            "volumes_ml": [
              139.4724,
              135.3163
            ]
          }

```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.