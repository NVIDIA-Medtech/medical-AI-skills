# Workflow Run Record

- run id: 937b8b2f03b2
- skill: medagent.verifiers.ct_segmentation_quality_v1 v0.1.0
- started: 2026-05-26T04:44:18.760367+00:00
- finished: 2026-05-26T04:44:28.358030+00:00
- elapsed: 9.598s
- exit code: 0

## Skill
- dir: verifiers/ct_segmentation_quality_v1
- entrypoint: scripts/grade.py

## Fixture
- path: runs/nv_segment_ctmr_trusted_pass_current/skill_run
- sha256: 46663175fe5e344f7cf50e8226642894cf2deda28191b9b5de9f30501d4afe73
- size: 504749 bytes

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
        "reason": "loaded runs/nv_segment_ctmr_trusted_pass_current/skill_run/segment_ctmr_outputs/spleen_03/spleen_03_trans.nii.gz",
        "status": "pass"
      },
      {
        "name": "any_class_present",
        "reason": "label_ids_present=[1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17, 19, 28, 29, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 48, 49, 58, 59, 60, 61, 62, 68, 69, 70, 71, 72, 73, 74, 80, 81, 82, 83, 84, 85, 86, 94, 95, 96, 97, 100, 101, 104, 105, 106, 107, 114, 115, 116, 119, 121, 122, 125, 127]",
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
        "reason": "liver=1197.6959 mL > spleen=161.5827 mL",
        "status": "pass"
      },
      {
        "name": "bilateral_symmetry",
        "reason": "worst relative_diff=0.018 <= 0.5",
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

```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.
