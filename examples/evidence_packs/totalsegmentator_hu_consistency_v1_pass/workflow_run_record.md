# Workflow Run Record

- run id: 95e8964e1cb5
- skill: medagent.verifiers.totalsegmentator_hu_consistency_v1 v0.1.0
- started: 2026-05-26T03:58:42.824611+00:00
- finished: 2026-05-26T03:58:43.170609+00:00
- elapsed: 0.346s
- exit code: 0

## Skill
- dir: verifiers/totalsegmentator_hu_consistency_v1
- entrypoint: scripts/grade.py

## Fixture
- path: runs/totalsegmentator_hu_consistency_source_pass
- sha256: bfc88c15df1dfa23dbd0cb141eb4f55c19953e404c9ee80e4ba0318d93e96265
- size: 19723 bytes

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
  "hu_consistency": {
    "checked_count": 6,
    "checks": [
      {
        "name": "any_class_checked",
        "reason": "6 class(es) had HU bounds defined out of 6 present",
        "status": "pass"
      },
      {
        "failing": [],
        "name": "pass_fraction_meets_floor",
        "reason": "6/6 classes within HU range (fraction=1.000 >= 0.7)",
        "status": "pass"
      }
    ],
    "classes_out_of_range": [],
    "min_pass_fraction": 0.7,
    "pass_fraction": 1.0,
    "passing_count": 6,
    "per_class": [
      {
        "check_status": "checked",
        "hu_max_expected": 180.0,
        "hu_min_expected": 30.0,
        "in_range": true,
        "label_id": 1,
        "mean_hu": 45.0,
        "median_hu": 45.0,
        "name": "spleen",
        "p10_hu": 45.0,
        "p90_hu": 45.0,
        "std_hu": 0.0,
        "voxel_count": 9000
      },
      {
        "check_status": "checked",
        "hu_max_expected": 300.0,
        "hu_min_expected": 20.0,
        "in_range": true,
        "label_id": 2,
        "mean_hu": 35.0,
        "median_hu": 35.0,
        "name": "kidney_right",
        "p10_hu": 35.0,
        "p90_hu": 35.0,
        "std_hu": 0.0,
        "voxel_count": 5625
      },
      {
        "check_status": "checked",
        "hu_max_expected": 300.0,
        "hu_min_expected": 20.0,
        "in_range": true,
        "label_id": 3,
        "mean_hu": 35.0,
        "median_hu": 35.0,
        "name": "kidney_left",
        "p10_hu": 35.0,

```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.
