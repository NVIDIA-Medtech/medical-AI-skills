# Workflow Run Record

- run id: 74b58ee061d1
- skill: medagent.verifiers.totalsegmentator_quality_v1 v0.1.0
- started: 2026-05-26T04:32:39.119994+00:00
- finished: 2026-05-26T04:32:48.147405+00:00
- elapsed: 9.027s
- exit code: 0

## Skill
- dir: verifiers/totalsegmentator_quality_v1
- entrypoint: scripts/grade.py

## Fixture
- path: runs/totalsegmentator_trusted_pass_current/skill_run
- sha256: 58bea2e1a5bd42f84927d0406ed66d61747596aae70e842d51908aeb5f9bcfdd
- size: 249400 bytes

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
        "reason": "loaded <repo>/runs/totalsegmentator_trusted_pass_current/skill_run/totalsegmentator_outputs/spleen_03_totalseg.nii.gz",
        "status": "pass"
      },
      {
        "name": "any_class_present",
        "reason": "label_ids_present=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 18, 19, 20, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 51, 52, 63, 64, 65, 66, 67, 68, 77, 78, 79, 82, 83, 86, 87, 88, 89, 97, 98, 99, 100, 101, 102, 103, 109, 110, 111, 112, 113, 114, 115, 116, 117]",
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
        "reason": "liver=1254.0059 mL > spleen=159.2689 mL",
        "status": "pass"
      },
      {
        "name": "bilateral_symmetry",
        "reason": "worst relative_diff=0.026 <= 0.5",
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

```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.
