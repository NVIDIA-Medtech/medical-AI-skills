#!/usr/bin/env python3
"""Deterministic synthetic fixtures for the MR-RATE MRI-preprocessing skills.

Generates small, valid, PHI-free inputs that the REAL upstream MR-RATE step
scripts can process (this is not a mock: the upstream code runs for real on
these inputs). One generator, one flag per pipeline step:

    python mri_fixtures.py --step {dcm2niix,pacs,series,modality,brainseg,zip,metadata,orchestrator} --out DIR

Everything is seeded so repeated runs are byte-stable (except DICOM/NIfTI file
mtimes). No real patient data, no PHI, no network.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Shared constants — kept consistent with the upstream MR-RATE config so the
# real step scripts accept the fixtures (config_metadata_columns.json /
# config_mri_preprocessing.py).
# ---------------------------------------------------------------------------
ACCESSION = "A0001"
STUDY_UID = "1.2.826.0.1.3680043.8.498.10000000000000000000000000000001"
REQUIRED_PACS_COLUMNS = [
    "AccessionNumber", "EchoTrainLength", "FieldStrength_T", "FlipAngle",
    "ImageOrientation(Patient)", "ImageType", "ImageTypeText",
    "MRAcquisitionType", "Manufacturer", "Manufacturer'sModelName",
    "Patient'sAge", "Patient'sSex", "ProtocolName", "PulseSequenceName",
    "ScanOptions", "ScanningSequence", "SequenceName", "SequenceVariant",
    "SeriesDescription", "SeriesInstanceUID", "SeriesNumber",
    "StudyDescription", "StudyInstanceUID", "TE_ms", "TI_ms", "TR_ms",
]
IOP_AXIAL = "1\\0\\0\\0\\1\\0"  # row=[1,0,0] col=[0,1,0] -> normal [0,0,1] -> AXIAL

# Two series per study: a T1w center + a T2w moving modality. Descriptions use
# only spaces so the upstream filename predictor and dcm2niix agree.
SERIES = [
    {
        "SeriesNumber": 6, "SeriesDescription": "T1 MPRAGE",
        "classified_modality": "T1w", "ScanningSequence": "GR\\IR",
        "PulseSequenceName": "T1TFE",  # -> upstream classifier TIER1 = T1w (center)
        "MRAcquisitionType": "3D", "modality_id": "t1w-raw-axi",
    },
    {
        "SeriesNumber": 7, "SeriesDescription": "T2 AX",
        "classified_modality": "T2w", "ScanningSequence": "SE",
        "PulseSequenceName": "T2TSE",  # -> upstream classifier TIER1 = T2w (moving)
        "MRAcquisitionType": "2D", "modality_id": "t2w-raw-axi",
    },
]
NIFTI_SHAPE = (80, 80, 60)          # >= MIN_SHAPE (16) each dim
NIFTI_SPACING = (2.0, 2.0, 2.5)     # FOV = (160,160,150) mm, within [140,350]


def _dcm2niix_filename(desc: str, num: int) -> str:
    """Match upstream modality_filtering.get_dcm2niix_filename."""
    return f"{int(num)}_{'_'.join(str(desc).split())}.nii.gz"


def _axial_affine() -> np.ndarray:
    aff = np.eye(4)
    aff[0, 0] = NIFTI_SPACING[0]
    aff[1, 1] = NIFTI_SPACING[1]
    aff[2, 2] = NIFTI_SPACING[2]
    return aff


def _write_nifti(path: Path, brainlike: bool = False, seed: int = 0) -> None:
    """Write a small valid NIfTI. If brainlike, embed a bright ellipsoid on a
    dark background so a real brain-extraction step has plausible signal."""
    import nibabel as nib

    rng = np.random.default_rng(seed)
    nx, ny, nz = NIFTI_SHAPE
    if brainlike:
        zz, yy, xx = np.meshgrid(
            np.linspace(-1, 1, nz), np.linspace(-1, 1, ny),
            np.linspace(-1, 1, nx), indexing="ij",
        )
        # ellipsoid mask -> transpose back to (x,y,z)
        ell = ((xx / 0.7) ** 2 + (yy / 0.8) ** 2 + (zz / 0.85) ** 2) <= 1.0
        vol = np.zeros((nz, ny, nx), dtype=np.float32)
        vol[ell] = 800.0
        vol += rng.normal(0, 15, size=vol.shape).astype(np.float32)
        vol = np.clip(vol, 0, None).transpose(2, 1, 0)
        data = vol.astype(np.int16)
    else:
        data = rng.integers(0, 500, size=NIFTI_SHAPE, dtype=np.int16)
    path.parent.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(data, _axial_affine()), str(path))


# ---------------------------------------------------------------------------
# Step 1 — dcm2niix: a folder of valid MR DICOM slices + folder-paths CSV
# ---------------------------------------------------------------------------
def gen_dcm2niix(out: Path) -> Path:
    import pydicom
    from pydicom.dataset import Dataset, FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian, MRImageStorage, generate_uid

    import pandas as pd

    dicom_dir = out / "dicom" / ACCESSION
    dicom_dir.mkdir(parents=True, exist_ok=True)
    series_uid = generate_uid()
    # 80x80x60 @ (2,2,2.5) mm -> FOV (160,160,150) mm, shape >= 16: passes the
    # upstream modality-filtering quality gate (MIN_SHAPE 16, FOV 140-350).
    n_slices, rows, cols = 60, 80, 80
    rng = np.random.default_rng(1)
    # brain-like bright ellipsoid on a dark background so HD-BET has real signal
    zz, yy, xx = np.meshgrid(
        np.linspace(-1, 1, n_slices), np.linspace(-1, 1, rows),
        np.linspace(-1, 1, cols), indexing="ij")
    ell = ((xx / 0.7) ** 2 + (yy / 0.8) ** 2 + (zz / 0.85) ** 2) <= 1.0
    vol = np.zeros((n_slices, rows, cols), dtype=np.float32)
    vol[ell] = 900.0
    vol = np.clip(vol + rng.normal(0, 20, vol.shape), 0, 4000).astype(np.uint16)
    for i in range(n_slices):
        fm = FileMetaDataset()
        fm.MediaStorageSOPClassUID = MRImageStorage
        fm.MediaStorageSOPInstanceUID = generate_uid()
        fm.TransferSyntaxUID = ExplicitVRLittleEndian
        fm.ImplementationClassUID = generate_uid()
        ds = Dataset()
        ds.file_meta = fm
        ds.is_little_endian = True
        ds.is_implicit_VR = False
        ds.SOPClassUID = MRImageStorage
        ds.SOPInstanceUID = fm.MediaStorageSOPInstanceUID
        ds.Modality = "MR"
        ds.AccessionNumber = ACCESSION
        ds.PatientID = "SYN-0001"
        ds.PatientName = "SYN-0001"
        ds.PatientAge = "045Y"
        ds.StudyInstanceUID = STUDY_UID
        ds.SeriesInstanceUID = series_uid
        ds.SeriesNumber = 6
        ds.InstanceNumber = i + 1
        ds.SeriesDescription = "T1 MPRAGE"
        ds.MRAcquisitionType = "3D"
        ds.ScanningSequence = "GR"
        ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
        ds.ImagePositionPatient = [0.0, 0.0, float(i) * 2.5]
        ds.PixelSpacing = [2.0, 2.0]
        ds.SliceThickness = 2.5
        ds.Rows = rows
        ds.Columns = cols
        ds.BitsAllocated = 16
        ds.BitsStored = 16
        ds.HighBit = 15
        ds.PixelRepresentation = 0
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.PixelData = vol[i].tobytes()
        ds.save_as(str(dicom_dir / f"slice_{i:03d}.dcm"), write_like_original=False)

    csv = out / "dicom_folder_paths.csv"
    pd.DataFrame({"FolderPath": [str(dicom_dir.resolve())]}).to_csv(csv, index=False)
    return csv


# ---------------------------------------------------------------------------
# Step 2 — pacs_metadata_filtering: raw PACS CSV with a duplicate + a NaN-age row
# ---------------------------------------------------------------------------
def _pacs_row(series: dict, age: str = "045Y") -> dict:
    row = {c: "" for c in REQUIRED_PACS_COLUMNS}
    row.update({
        "AccessionNumber": ACCESSION,
        "EchoTrainLength": 1, "FieldStrength_T": 1.5, "FlipAngle": 90,
        "ImageOrientation(Patient)": IOP_AXIAL, "ImageType": "ORIGINAL\\PRIMARY",
        "ImageTypeText": "ORIGINAL", "MRAcquisitionType": series["MRAcquisitionType"],
        "Manufacturer": "SYNTHETIC", "Manufacturer'sModelName": "TestScanner",
        "Patient'sAge": age, "Patient'sSex": "M", "ProtocolName": "HEAD",
        "PulseSequenceName": series.get("PulseSequenceName", series["SeriesDescription"]),
        "ScanOptions": "",
        "ScanningSequence": series["ScanningSequence"], "SequenceName": "",
        "SequenceVariant": "SK", "SeriesDescription": series["SeriesDescription"],
        "SeriesInstanceUID": f"{STUDY_UID}.{series['SeriesNumber']}",
        "SeriesNumber": series["SeriesNumber"], "StudyDescription": "MRI HEAD",
        "StudyInstanceUID": STUDY_UID, "TE_ms": 10, "TI_ms": 0, "TR_ms": 2000,
    })
    return row


def gen_pacs(out: Path):
    import pandas as pd
    rows = [_pacs_row(s) for s in SERIES]
    rows.append(_pacs_row(SERIES[0]))                      # exact duplicate -> dropped
    bad = _pacs_row({**SERIES[1], "SeriesNumber": 8, "SeriesDescription": "T2 EXTRA"})
    bad["Patient'sAge"] = np.nan                           # NaN critical col -> dropped
    rows.append(bad)
    csv = out / "pacs_metadata.csv"
    pd.DataFrame(rows).to_csv(csv, index=False)
    return csv


# ---------------------------------------------------------------------------
# Step 3 — series_classification: a cleaned metadata CSV (2 valid series)
# ---------------------------------------------------------------------------
def gen_series(out: Path):
    import pandas as pd
    rows = [_pacs_row(s) for s in SERIES]
    csv = out / "cleaned_metadata.csv"
    pd.DataFrame(rows).to_csv(csv, index=False)
    return csv


# ---------------------------------------------------------------------------
# Step 4 — modality_filtering: a classified CSV + raw NIfTI tree
# ---------------------------------------------------------------------------
def _classified_row(series: dict) -> dict:
    row = _pacs_row(series)
    row.update({
        "classified_modality": series["classified_modality"],
        "is_derived": False, "is_localizer": False, "is_subtraction": False,
        "is_contrast_enhanced": False, "sequence_family": "structural",
        "classification_rule": "synthetic", "dwi_sub_type": "",
    })
    return row


def _write_raw_niftis(raw_root: Path):
    raw_root.mkdir(parents=True, exist_ok=True)
    acc_dir = raw_root / ACCESSION
    for i, s in enumerate(SERIES):
        fn = _dcm2niix_filename(s["SeriesDescription"], s["SeriesNumber"])
        _write_nifti(acc_dir / fn, brainlike=(s["classified_modality"] == "T1w"), seed=i)


def gen_modality(out: Path):
    import pandas as pd
    csv = out / "classified.csv"
    pd.DataFrame([_classified_row(s) for s in SERIES]).to_csv(csv, index=False)
    _write_raw_niftis(out / "raw_niftis")
    return csv


# ---------------------------------------------------------------------------
# modalities.json (output of step 4, input to steps 5/6/7)
# ---------------------------------------------------------------------------
def _modalities_json() -> dict:
    def entry(s):
        fn = _dcm2niix_filename(s["SeriesDescription"], s["SeriesNumber"])
        return {
            "series_instance_uid": f"{STUDY_UID}.{s['SeriesNumber']}",
            "img_path": fn,
        }
    center = SERIES[0]
    moving = SERIES[1]
    return {
        ACCESSION: {
            "study_instance_uid": STUDY_UID,
            "center_modality": {center["modality_id"]: entry(center)},
            "moving_modality": {moving["modality_id"]: entry(moving)},
        }
    }


def gen_brainseg(out: Path):
    mj = out / "modalities.json"
    mj.write_text(json.dumps(_modalities_json(), indent=2), encoding="utf-8")
    _write_raw_niftis(out / "raw_niftis")
    return mj


# ---------------------------------------------------------------------------
# Steps 6 & 7 — a completed processed/ tree (img + seg with masks), no GPU
# ---------------------------------------------------------------------------
def _write_processed_tree(proc_root: Path):
    study = proc_root / ACCESSION
    img = study / "img"
    seg = study / "seg"
    for s in SERIES:
        mid = s["modality_id"]
        _write_nifti(img / f"{ACCESSION}_{mid}.nii.gz", brainlike=True, seed=10)
        _write_nifti(seg / f"{ACCESSION}_{mid}_brain-mask.nii.gz", seed=11)
        _write_nifti(seg / f"{ACCESSION}_{mid}_defacing-mask.nii.gz", seed=12)


def gen_zip(out: Path):
    _write_processed_tree(out / "processed")
    mj = out / "modalities.json"
    mj.write_text(json.dumps(_modalities_json(), indent=2), encoding="utf-8")
    return out / "processed"


def gen_metadata(out: Path):
    import pandas as pd
    _write_processed_tree(out / "processed")
    mj = out / "modalities.json"
    mj.write_text(json.dumps(_modalities_json(), indent=2), encoding="utf-8")

    # step-4-style metadata CSV (input to prepare_metadata)
    rows = []
    for s in SERIES:
        r = _classified_row(s)
        r.update({
            "study_id": ACCESSION, "patient_id": "patient_0001",
            "modality_id": s["modality_id"],
            "is_center_modality": s["classified_modality"] == "T1w",
            "acquisition_plane": "AXIAL", "patient_age": 45,
            "ras_array_shape": str(list(NIFTI_SHAPE)),
            "ras_array_spacing_mm": str(list(NIFTI_SPACING)),
            "ras_array_fov_mm": "[160.0, 160.0, 150.0]",
            "raw_nifti_filename": _dcm2niix_filename(s["SeriesDescription"], s["SeriesNumber"]),
        })
        rows.append(r)
    pd.DataFrame(rows).to_csv(out / "modalities_metadata.csv", index=False)

    pd.DataFrame({"Accession": [ACCESSION], "Anon Patient ID": ["patient_0001"]}).to_excel(
        out / "patient_mapping.xlsx", index=False)
    pd.DataFrame({"Accession": [ACCESSION], "Anonymized Study Date": ["2020-01-01"]}).to_excel(
        out / "study_date_mapping.xlsx", index=False)
    return out / "modalities_metadata.csv"


# ---------------------------------------------------------------------------
# Orchestrator — a minimal end-to-end batch config + all raw inputs
# ---------------------------------------------------------------------------
def gen_orchestrator(out: Path):
    # One clean T1 study end to end: DICOM (series 6, T1) + a single-row PACS CSV
    # whose PulseSequenceName makes the real classifier label it T1w (center).
    import pandas as pd
    gen_dcm2niix(out)  # writes dicom/A0001 (series 6 "T1 MPRAGE") + dicom_folder_paths.csv
    pd.DataFrame([_pacs_row(SERIES[0])]).to_csv(out / "pacs_metadata.csv", index=False)
    pd.DataFrame({"Accession": [ACCESSION], "Anon Patient ID": ["patient_0001"]}).to_excel(
        out / "patient_mapping.xlsx", index=False)
    pd.DataFrame({"Accession": [ACCESSION], "Anonymized Study Date": ["2020-01-01"]}).to_excel(
        out / "study_date_mapping.xlsx", index=False)
    return out / "dicom_folder_paths.csv"


GENERATORS = {
    "dcm2niix": gen_dcm2niix, "pacs": gen_pacs, "series": gen_series,
    "modality": gen_modality, "brainseg": gen_brainseg, "zip": gen_zip,
    "metadata": gen_metadata, "orchestrator": gen_orchestrator,
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--step", required=True, choices=sorted(GENERATORS))
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    primary = GENERATORS[args.step](args.out)
    print(json.dumps({"step": args.step, "out": str(args.out.resolve()),
                      "primary": str(Path(primary).resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
