#!/usr/bin/env python3
"""Build a DICOM CT series fixture for `holohub_imaging_ai_segmentator`
from a Decathlon-shaped NIfTI volume.

Reverse of `skills/dicom-series-to-volume/scripts/series_to_volume.py`:
takes a NIfTI CT volume in HU and emits one CT-image-storage .dcm per
axial slice, with consistent series/study UIDs and per-slice
ImagePositionPatient / SOPInstanceUID. The HoloHub
`imaging_ai_segmentator` app's DICOM operators ingest this directly.

Why this exists: HoloHub's auto-fixture is a single-slice CT
(CT_DICOM_SINGLE/7106) that triggers an empty segmentation. The
TotalSegmentator model needs a real multi-slice abdominal CT to
produce a non-empty mask. We have Decathlon Task09 Spleen NIfTI
volumes locally; this script converts one into a DICOM series so
HoloHub's pipeline (DICOM loader → MONAI inference → DICOM SEG
writer) has the input shape it expects.

The output directory is gitignored; rerun this script after a clone
to produce the fixture locally.

Usage:
    python3 build_dicom_from_nifti.py \\
      <input.nii.gz> <output_dir> [--patient-id ID]

Default for a fresh setup:
    python3 skills/holohub-imaging-ai-segmentator/fixtures/build_dicom_from_nifti.py \\
      .workbench_data/datasets/Task09_Spleen/imagesTr/spleen_10.nii.gz \\
      .workbench_data/holohub_input/spleen_10
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid


def nifti_to_dicom_series(nifti_path: Path, out_dir: Path, patient_id: str = "DECATH-SPLEEN-10") -> int:
    """Write one CT DICOM file per axial slice. Returns slice count.

    Assumes the input NIfTI is in canonical RAS space; we convert to
    DICOM's LPS convention by negating the first two affine rows.
    """
    img = nib.load(str(nifti_path))
    arr = np.asarray(img.get_fdata())
    if arr.ndim != 3:
        raise ValueError(f"expected 3D NIfTI; got shape {arr.shape}")

    # NIfTI's affine is RAS+; DICOM's is LPS. Flip x,y.
    affine_ras = img.affine
    lps_to_ras = np.diag([float("-1.0"), float("-1.0"), float("1.0"), float("1.0")])
    affine_lps = lps_to_ras @ affine_ras

    spacing_x = float(np.linalg.norm(affine_lps[:3, 0]))
    spacing_y = float(np.linalg.norm(affine_lps[:3, 1]))
    spacing_z = float(np.linalg.norm(affine_lps[:3, 2]))
    row_dir = affine_lps[:3, 0] / spacing_x if spacing_x > 0 else np.array([1.0, 0.0, 0.0])
    col_dir = affine_lps[:3, 1] / spacing_y if spacing_y > 0 else np.array([0.0, 1.0, 0.0])
    slice_dir = affine_lps[:3, 2] / spacing_z if spacing_z > 0 else np.array([0.0, 0.0, 1.0])
    origin = affine_lps[:3, 3]

    rows, cols, n_slices = arr.shape

    out_dir = out_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    # Wipe any stale .dcm so a re-run is clean.
    for old in out_dir.glob("*.dcm"):
        old.unlink()

    study_uid = generate_uid()
    series_uid = generate_uid()
    frame_of_reference_uid = generate_uid()

    # Map HU values (typically -1000 to ~3000) into a 16-bit signed range
    # using RescaleSlope=1, RescaleIntercept=-1024 (DICOM-standard for CT).
    # Stored value = HU - intercept; clamp to int16.
    intercept = -1024.0
    slope = 1.0

    for k in range(n_slices):
        slice_hu = arr[:, :, k]
        stored = np.rint((slice_hu - intercept) / slope)
        stored = np.clip(stored, -32768, 32767).astype(np.int16)

        # ImagePositionPatient is the world-space coordinate of the
        # top-left voxel of this slice.
        position = (origin + k * spacing_z * slice_dir).tolist()

        file_meta = Dataset()
        file_meta.MediaStorageSOPClassUID = CTImageStorage
        file_meta.MediaStorageSOPInstanceUID = generate_uid()
        file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
        file_meta.ImplementationClassUID = generate_uid()

        ds = FileDataset("", {}, file_meta=file_meta, preamble=b"\0" * 128)
        ds.is_little_endian = True
        ds.is_implicit_VR = False

        ds.PatientName = "DECATH^SPLEEN^10"
        ds.PatientID = patient_id
        ds.PatientBirthDate = "19000101"
        ds.PatientSex = "O"

        ds.StudyInstanceUID = study_uid
        ds.StudyDate = "20260510"
        ds.StudyTime = "120000"
        # StudyID is required by highdicom's DICOM SEG writer (raises
        # AttributeError if absent). The official spec says StudyID is
        # type 2 (must be present, may be empty); pydicom does not
        # auto-populate it from a synthesised series.
        ds.StudyID = "1"
        ds.StudyDescription = "Decathlon Task09 Spleen CT (HoloHub fixture)"
        ds.AccessionNumber = "DECATH-S10"

        ds.SeriesInstanceUID = series_uid
        ds.SeriesNumber = "1"
        ds.SeriesDescription = "Axial CT abdomen"
        ds.Modality = "CT"
        ds.BodyPartExamined = "ABDOMEN"
        # ImageType is load-bearing: HoloHub's SeriesSelectorOperator
        # filters by ImageType matching ['ORIGINAL', 'PRIMARY']. Without
        # it the series is silently rejected and the app falls through
        # to the auto-fetched HoloHub test fixture (CT_DICOM_SINGLE/7106
        # — single-slice "Routine Brain"), giving misleading empty-seg
        # output downstream.
        ds.ImageType = ["ORIGINAL", "PRIMARY"]
        ds.FrameOfReferenceUID = frame_of_reference_uid

        ds.SOPClassUID = CTImageStorage
        ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
        ds.InstanceNumber = str(k + 1)

        ds.Rows = rows
        ds.Columns = cols
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.BitsAllocated = 16
        ds.BitsStored = 16
        ds.HighBit = 15
        ds.PixelRepresentation = 1  # signed

        # DICOM VR DS (decimal string) caps at 16 chars; round to keep us
        # within budget without losing useful precision.
        def _ds(v: float) -> str:
            return f"{v:.6g}"

        ds.PixelSpacing = [_ds(spacing_y), _ds(spacing_x)]
        ds.SliceThickness = _ds(spacing_z)
        ds.SpacingBetweenSlices = _ds(spacing_z)
        ds.ImageOrientationPatient = [_ds(v) for v in (*row_dir, *col_dir)]
        ds.ImagePositionPatient = [_ds(v) for v in position]
        ds.RescaleSlope = _ds(slope)
        ds.RescaleIntercept = _ds(intercept)
        ds.RescaleType = "HU"
        # Reasonable display window for abdomen CT.
        ds.WindowCenter = "40"
        ds.WindowWidth = "400"

        ds.PixelData = stored.tobytes()

        out_path = out_dir / f"slice_{k:04d}.dcm"
        ds.save_as(str(out_path), enforce_file_format=True)

    return n_slices


def main() -> int:
    p = argparse.ArgumentParser(description="Build a DICOM CT series from a NIfTI volume.")
    p.add_argument("nifti", type=Path)
    p.add_argument("out_dir", type=Path)
    p.add_argument("--patient-id", default="DECATH-SPLEEN-10")
    args = p.parse_args()

    if not args.nifti.exists():
        sys.stderr.write(f"input not found: {args.nifti}\n")
        return 2
    n = nifti_to_dicom_series(args.nifti, args.out_dir, args.patient_id)
    print(f"wrote {n} DICOM slices to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
