# Workflow Run Record

- run id: 40b29967a7d7
- skill: medagent.verifiers.totalsegmentator_quality_v1 v0.1.0
- started: 2026-05-26T03:58:42.716818+00:00
- finished: 2026-05-26T03:58:43.277957+00:00
- elapsed: 0.561s
- exit code: 0

## Skill
- dir: verifiers/totalsegmentator_quality_v1
- entrypoint: scripts/grade.py

## Fixture
- path: runs/totalsegmentator_quality_source_pass
- sha256: a1b426d9180c6871003f52bae46c87b07907984880e35c4537cae7af0f050a1b
- size: 31231 bytes

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
        "reason": "loaded <repo>/runs/totalsegmentator_quality_source_pass/predicted_seg.nii.gz",
        "status": "pass"
      },
      {
        "name": "any_class_present",
        "reason": "label_ids_present=[1, 2, 3, 5]",
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
        "reason": "liver=1500.0 mL > spleen=200.0 mL",
        "status": "pass"
      },
      {
        "name": "bilateral_symmetry",
        "reason": "worst relative_diff=0.000 <= 0.5",
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
              2,
              3
            ],
            "names": [
              "kidney_right",
              "kidney_left"
            ],
            "ok": true,
            "relative_diff": 0.0,
            "volumes_ml": [
              150.0,
              150.0
            ]

```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.
