# pydicom 3.x Notes

Authoritative source: <https://pydicom.github.io/>.

## Save API

pydicom 3.x uses `enforce_file_format=True`; pydicom 2.x used
`write_like_original=False`.

```python
try:
    ds.save_as(path, enforce_file_format=True)
except TypeError:
    ds.save_as(path, write_like_original=False)
```

## Metadata reads

Use `pydicom.dcmread(path, stop_before_pixels=True)` for preflight and
metadata extraction. It avoids pixel allocation and survives many pixel-data
problems.

Important fields: `SeriesInstanceUID`, `Modality`, `ImageType`,
`ImageOrientationPatient`, `ImagePositionPatient`, `PixelSpacing`,
`RescaleSlope`, and `RescaleIntercept`.

## DICOM SEG drift

DICOM SEG writers commonly regenerate SOPInstanceUID, date, and time fields.
Suppress those jittery payload paths in drift reports and gate semantic facts
instead.
