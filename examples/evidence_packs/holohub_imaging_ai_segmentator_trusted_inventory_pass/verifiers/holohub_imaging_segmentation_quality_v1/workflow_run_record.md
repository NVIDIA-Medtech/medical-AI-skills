# Workflow Run Record

- run id: 03bf87c72747
- skill: medagent.verifiers.holohub_imaging_segmentation_quality_v1 v0.1.0
- started: 2026-05-26T03:10:58.887265+00:00
- finished: 2026-05-26T03:10:59.003735+00:00
- elapsed: 0.116s
- exit code: 0

## Skill
- dir: verifiers/holohub_imaging_segmentation_quality_v1
- entrypoint: scripts/grade.py

## Fixture
- path: examples/evidence_packs/holohub_imaging_ai_segmentator_trusted_inventory_pass/skill_run
- sha256: 0184f93e72e3dc7147d9d29401d7742dd0e9ea6aed213f11d71e94d07b36089e
- size: 63986 bytes

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
    "dicom_seg_bytes": 20213016,
    "dicom_seg_count": 1,
    "nifti_original_count": 1,
    "nifti_segmentation_count": 1,
    "seg_signals": {
      "empty_segmentation_warning": false,
      "seg_array_shape": [
        55,
        512,
        512
      ],
      "seg_pixel_max_value": 103
    }
  },
  "domain_floor": {
    "checks": [
      {
        "name": "output_json_present",
        "reason": "output.json loaded",
        "status": "pass"
      },
      {
        "actual": "holohub_imaging_ai_segmentator",
        "expected": [
          "holohub_imaging_ai_segmentator",
          "medagent.holohub_imaging_ai_segmentator"
        ],
        "name": "target_skill_is_imaging",
        "reason": "skill_id='holohub_imaging_ai_segmentator'",
        "status": "pass"
      },
      {
        "actual": "passed",
        "expected": "passed",
        "name": "source_pack_passed",
        "reason": "source overall_status='passed'",
        "status": "pass"
      },
      {
        "name": "holohub_exit_clean",
        "reason": "exit_code=0",
        "status": "pass"
      },
      {
        "name": "dicom_seg_present",
        "reason": "dicom_seg.count=1",
        "status": "pass"
      },
      {
        "name": "dicom_seg_nonempty",
        "reason": "dicom_seg.total_bytes=20213016",
        "status": "pass"
      },
      {
        "name": "nifti_original_present",
        "reason": "nifti.original.count=1",
        "status": "pass"
      },
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.