# Workflow Run Record

- run id: c7cae34b7de2
- skill: medagent.verifiers.dicom_metadata_quality_v1 v0.1.0
- started: 2026-05-26T01:25:48.008530+00:00
- finished: 2026-05-26T01:25:48.122956+00:00
- elapsed: 0.114s
- exit code: 0

## Skill
- dir: verifiers/dicom_metadata_quality_v1
- entrypoint: scripts/grade.py

## Fixture
- path: examples/evidence_packs/dicom_metadata_trusted_warn/skill_run
- sha256: 8ad1b27f71dfd615d292b0ab8285d5962b25cbd81cfa5671d5b89cd59db88a51
- size: 24038 bytes

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
    "id": "medagent.verifiers.dicom_metadata_quality_v1",
    "version": "0.1.0"
  },
  "target": {
    "evidence_pack": "examples/evidence_packs/dicom_metadata_trusted_warn/skill_run",
    "skill_id": "medagent.dicom_metadata_extract",
    "source_overall_status": "passed"
  },
  "metadata_quality": {
    "n_fail": 0,
    "n_warn": 1,
    "verdict": "warn",
    "acceptable": true
  },
  "checks": [
    {
      "name": "target_skill_matches",
      "status": "pass",
      "reason": "skill_id='medagent.dicom_metadata_extract'"
    },
    {
      "name": "source_pack_passed",
      "status": "pass",
      "reason": "source pack overall='passed'"
    },
    {
      "name": "modality_present",
      "status": "pass",
      "reason": "modality='CT'"
    },
    {
      "name": "transfer_syntax_present",
      "status": "pass",
      "reason": "transfer_syntax={'uid': '1.2.840.10008.1.2.1', 'name': 'Explicit VR Little Endian'}"
    },
    {
      "name": "study_uid_present",
      "status": "pass",
      "reason": "StudyInstanceUID='1.2.826.0.1.3680043.8.498.70205069167432896821744418685172690618'"
    },
    {
      "name": "image_dimensions_positive",
      "status": "pass",
      "reason": "Rows=64, Columns=64"
    },
    {
      "name": "phi_flag_is_boolean",
      "status": "pass",
      "reason": "phi_present=True"
    },
    {
      "name": "phi_tags_list_shape",
      "status": "pass",
      "reason": "phi_tags_found must be a list of tag-name strings"
    
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.