#!/usr/bin/env python3
"""Generate synthetic DICOM fixtures for dicom_series_preflight.

  clean_no_phi/  — canonical pass (LPS CT, no populated PHI tags)
  clean_axial/   — warn demo (same geometry, PHI tags populated)
  flipped_lr/    — fail demo (LR-flipped IOP)

Reuses the same volume geometry as dicom_series_to_volume fixtures.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
sys.path.insert(0, str(REPO / "skills" / "dicom-series-to-volume" / "fixtures"))

from generate_fixtures import write_series  # noqa: E402

if __name__ == "__main__":
    write_series(ROOT / "clean_axial", iop=[1, 0, 0, 0, 1, 0], series_label="clean_phi")
    write_series(ROOT / "flipped_lr", iop=[-1, 0, 0, 0, 1, 0], series_label="flipped_lr")
    write_series(ROOT / "clean_no_phi", iop=[1, 0, 0, 0, 1, 0], series_label="clean_no_phi")
    # Strip PHI tags from pass fixture
    import pydicom

    for p in (ROOT / "clean_no_phi").glob("*.dcm"):
        ds = pydicom.dcmread(str(p))
        for tag in (
            "PatientName",
            "PatientID",
            "PatientBirthDate",
            "PatientSex",
            "InstitutionName",
        ):
            if hasattr(ds, tag):
                delattr(ds, tag)
        ds.save_as(str(p), enforce_file_format=True)
    print("wrote clean_no_phi, clean_axial, flipped_lr under", ROOT)
