# Workflow Run Record

- run id: 1812ad535ad4
- skill: medagent.dicom_series_to_volume v0.1.0
- started: 2026-05-10T21:17:07.190428+00:00
- finished: 2026-05-10T21:17:07.408547+00:00
- elapsed: 0.218s
- exit code: 0

## Skill
- dir: skills/dicom-series-to-volume
- entrypoint: scripts/series_to_volume.py

## Fixture
- path: skills/dicom-series-to-volume/fixtures/clean_axial
- sha256: 816042f3b11bbbae78b4f294f9457434157ce4d2f452895ae8138660bf14ad39
- size: 296000 bytes

## Validation
- overall: passed
- schema: passed
- sanity: passed
- runtime: within_envelope
- cost: passed
- env_pin: skipped
- integrity: clean

## Output (excerpt)
```json
{
  "skill": "dicom_series_to_volume",
  "n_slices": 32,
  "single_series": true,
  "series_instance_uid": "1.2.826.0.1.3680043.8.498.34592247408981119827086557674534754293",
  "series_instance_uid_count": 1,
  "modality": "CT",
  "modalities": [
    "CT"
  ],
  "dicom_metadata": {
    "Modality": "CT",
    "BodyPartExamined": "ABDOMEN",
    "StudyInstanceUID": "1.2.826.0.1.3680043.8.498.51867841225106029517805824877861521047",
    "SeriesInstanceUID": "1.2.826.0.1.3680043.8.498.34592247408981119827086557674534754293",
    "StudyDescription": "Synthetic CT fixture for orientation gate demo",
    "SeriesDescription": "Synthetic axial CT",
    "StudyDate": "20260509"
  },
  "input_dir": "skills/dicom-series-to-volume/fixtures/clean_axial",
  "output": {
    "path": "skills/dicom-series-to-volume/fixtures/clean_axial.nii.gz",
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
    "affine": [
      [
        -1.0,
        0.0,
        0.0,
        0.0
      ],
      [
        0.0,
        -1.0,
        0.0,
        0.0
      ],
      [
        0.0,
        0.0,
        2.0,
        0.0
      ],
      [
        0.0,
        0.0,
        0.0,
        1.0
      ]
    ],
    "axcodes": [
      "L",
      "P",
      "S"
    ]
  },
  "hu_range": [
    -1000.0,
    60.0
  ],
  "inconsistent_shape": false,
  "runtime": {
    "conversion_seconds": 0.01
  },
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.