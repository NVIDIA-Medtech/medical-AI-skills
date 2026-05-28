# Workflow Run Record

- run id: adebf9f20968
- skill: medagent.dicom_series_preflight v0.1.0
- started: 2026-05-26T01:25:16.147378+00:00
- finished: 2026-05-26T01:25:16.474511+00:00
- elapsed: 0.327s
- exit code: 0

## Skill
- dir: skills/dicom-series-preflight
- entrypoint: scripts/preflight_series.py

## Fixture
- path: skills/dicom-series-preflight/fixtures/clean_no_phi
- sha256: 006b265e0d0d32f7662993aa4de92fec910b4e169b1f83ddea55b08424509132
- size: 293760 bytes

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
  "skill": "dicom_series_preflight",
  "input_dir": "skills/dicom-series-preflight/fixtures/clean_no_phi",
  "inventory": {
    "n_files_seen": 32,
    "n_readable": 32,
    "n_corrupt": 0,
    "corrupt_samples": []
  },
  "series": {
    "n_series": 1,
    "series_instance_uids": [
      "1.2.826.0.1.3680043.8.498.60253016275516659825732719618688914179"
    ],
    "single_series": true,
    "modalities": [
      "CT"
    ]
  },
  "orientation": {
    "n_distinct_iop": 1,
    "primary_iop": [
      1.0,
      0.0,
      0.0,
      0.0,
      1.0,
      0.0
    ],
    "axcodes": [
      "L",
      "P",
      "S"
    ],
    "expected_axcodes": [
      "L",
      "P",
      "S"
    ],
    "axcodes_match": true
  },
  "consistency": {
    "n_distinct_pixel_spacing": 1,
    "n_distinct_shapes": 1,
    "missing_iop_count": 0,
    "missing_spacing_count": 0
  },
  "phi": {
    "phi_present": false,
    "phi_tags_found": [],
    "phi_scope_disclaimer": "Standard DICOM PS3.15 basic-profile tags only. Private tags (odd group) NOT checked. Burnt-in pixel text NOT detected. Use a proper de-identifier for clinical or regulatory work."
  },
  "transfer_syntax": {
    "compressed_instance_count": 0
  },
  "study": {
    "StudyInstanceUID": "1.2.826.0.1.3680043.8.498.73556401863553488911509614038755359055",
    "StudyDate": "20260509",
    "StudyDescription": "Synthetic CT fixture for orientation gate demo"
  },
  "series_metadata": {
    "SeriesInstanceUID": "1.2.826.0.1.3680043.8.498.602
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.