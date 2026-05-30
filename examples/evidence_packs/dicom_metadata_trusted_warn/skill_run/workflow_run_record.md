# Workflow Run Record

- run id: 5930862315f5
- skill: medagent.dicom_metadata_extract v0.1.0
- started: 2026-05-26T01:25:47.338482+00:00
- finished: 2026-05-26T01:25:47.669698+00:00
- elapsed: 0.331s
- exit code: 0

## Skill
- dir: skills/dicom-metadata-extract
- entrypoint: scripts/extract_metadata.py

## Fixture
- path: skills/dicom-metadata-extract/fixtures/sample_ct.dcm
- sha256: 8f6ac2e354fc5a7e0086d76578dd9896f01be922136051f387b6b28ad084ba7e
- size: 9190 bytes

## Validation
- overall: passed
- schema: passed
- sanity: passed
- runtime: within_envelope
- cost: passed
- env_pin: passed
- integrity: clean

## Output (excerpt)
```json
{
  "path": "skills/dicom-metadata-extract/fixtures/sample_ct.dcm",
  "transfer_syntax": {
    "uid": "1.2.840.10008.1.2.1",
    "name": "Explicit VR Little Endian"
  },
  "modality": "CT",
  "study": {
    "StudyInstanceUID": "1.2.826.0.1.3680043.8.498.70205069167432896821744418685172690618",
    "StudyDate": "20260518",
    "StudyTime": "102957",
    "StudyDescription": "Synthetic test study (no clinical content)",
    "AccessionNumber": null
  },
  "series": {
    "SeriesInstanceUID": "1.2.826.0.1.3680043.8.498.31550974118702976965686593096238327316",
    "SeriesNumber": "1",
    "SeriesDescription": "Synthetic CT for skill testing",
    "Modality": "CT",
    "BodyPartExamined": "ABDOMEN"
  },
  "image": {
    "SOPInstanceUID": "1.2.826.0.1.3680043.8.498.87363990806676731690652303827211061652",
    "InstanceNumber": "1",
    "Rows": 64,
    "Columns": 64,
    "BitsAllocated": 16,
    "PixelRepresentation": 0,
    "PhotometricInterpretation": "MONOCHROME2",
    "NumberOfFrames": null
  },
  "phi_present": true,
  "phi_tags_found": [
    "PatientName",
    "PatientID",
    "PatientBirthDate",
    "PatientSex",
    "InstitutionName",
    "ReferringPhysicianName"
  ],
  "phi_scope_disclaimer": "Standard DICOM PS3.15 basic-profile tags only. Private tags (odd group) NOT checked. Burnt-in pixel text NOT detected. Use a proper de-identifier for clinical or regulatory work."
}
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.