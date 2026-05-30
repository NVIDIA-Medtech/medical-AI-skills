# Workflow Run Record

- run id: 23653247fb09
- skill: medagent.verifiers.dicom_volume_quality_v1 v0.1.0
- started: 2026-05-26T01:25:16.905867+00:00
- finished: 2026-05-26T01:25:17.231828+00:00
- elapsed: 0.326s
- exit code: 0

## Skill
- dir: verifiers/dicom_volume_quality_v1
- entrypoint: scripts/grade.py

## Fixture
- path: examples/evidence_packs/dicom_series_to_volume_trusted_pass/skill_run
- sha256: 6da956bac64e68cb9d178dc29ac03d91d4d43e4f0989d31e76a7493c2cfddfdc
- size: 34637 bytes

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
  "verifier": {
    "id": "medagent.verifiers.dicom_volume_quality_v1",
    "version": "0.1.0"
  },
  "target": {
    "evidence_pack": "examples/evidence_packs/dicom_series_to_volume_trusted_pass/skill_run",
    "skill_id": "medagent.dicom_series_to_volume",
    "source_overall_status": "passed",
    "output_artifact": "examples/evidence_packs/dicom_series_to_volume_trusted_pass/skill_run/volume.nii.gz"
  },
  "volume_quality": {
    "n_fail": 0,
    "n_warn": 0,
    "verdict": "pass",
    "acceptable": true,
    "shape": [
      64,
      64,
      32
    ],
    "spacing": [
      1.0,
      1.0,
      2.0
    ],
    "axcodes": [
      "L",
      "P",
      "S"
    ],
    "hu_range": [
      -1000.0,
      60.0
    ]
  },
  "checks": [
    {
      "name": "target_skill_matches",
      "status": "pass",
      "reason": "skill_id='medagent.dicom_series_to_volume'"
    },
    {
      "name": "source_pack_passed",
      "status": "pass",
      "reason": "source pack overall='passed'"
    },
    {
      "name": "modality_ct",
      "status": "pass",
      "reason": "modality='CT'"
    },
    {
      "name": "single_series",
      "status": "pass",
      "reason": "single_series=True"
    },
    {
      "name": "no_inconsistent_shape",
      "status": "pass",
      "reason": "inconsistent_shape=False"
    },
    {
      "name": "output_artifact_declared",
      "status": "pass",
      "reason": "output.path='examples/evidence_packs/dicom_series_to_volume_trusted_pass/skill_run/v
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.