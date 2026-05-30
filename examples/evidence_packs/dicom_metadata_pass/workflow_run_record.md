# Workflow Run Record

- run id: 8162bcc6d926
- skill: medagent.dicom_metadata_extract v0.1.0
- started: 2026-05-10T10:46:16.284271+00:00
- finished: 2026-05-10T10:46:16.501662+00:00
- elapsed: 0.217s
- exit code: 0

## Skill
- dir: skills/dicom-metadata-extract
- entrypoint: scripts/extract_metadata.py

## Fixture
- path: skills/dicom-metadata-extract/fixtures/sample_ct.dcm
- sha256: 4143f3313661cabac059776d00a589168f0268ec5528930b7e67af61c7b2d70a
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
    "StudyInstanceUID": "1.2.826.0.1.3680043.8.498.51234902331161357359349253745613059633",
    "StudyDate": "20260504",
    "StudyTime": "104835",
    "StudyDescription": "Synthetic test study (no clinical content)",
    "AccessionNumber": null
  },
  "series": {
    "SeriesInstanceUID": "1.2.826.0.1.3680043.8.498.71663850202801832057861355710084335307",
    "SeriesNumber": "1",
    "SeriesDescription": "Synthetic CT for skill testing",
    "Modality": "CT",
    "BodyPartExamined": "ABDOMEN"
  },
  "image": {
    "SOPInstanceUID": "1.2.826.0.1.3680043.8.498.32927786328344331435640089278996222262",
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