"""Generate a synthetic CT DICOM fixture for skill testing.

Has populated standard PHI tags with obviously-synthetic values so the
PHI-presence flag can be tested. Run once: produces sample_ct.dcm.
"""
from datetime import datetime
from pathlib import Path

import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileDataset


def generate(out_path: Path) -> None:
    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = pydicom.uid.CTImageStorage
    file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
    file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian

    ds = FileDataset(str(out_path), {}, file_meta=file_meta, preamble=b"\0" * 128)

    # Standard PHI tags — synthetic values, obviously fake
    ds.PatientName = "ANON^TEST^SYNTHETIC"
    ds.PatientID = "TEST_ID_001"
    ds.PatientBirthDate = "20000101"
    ds.PatientSex = "O"
    ds.InstitutionName = "TEST_INSTITUTION_DO_NOT_USE"
    ds.ReferringPhysicianName = "TEST^Physician"

    now = datetime.now()
    ds.StudyDate = now.strftime("%Y%m%d")
    ds.StudyTime = now.strftime("%H%M%S")
    ds.StudyInstanceUID = pydicom.uid.generate_uid()
    ds.StudyDescription = "Synthetic test study (no clinical content)"
    ds.SeriesInstanceUID = pydicom.uid.generate_uid()
    ds.SeriesNumber = 1
    ds.SeriesDescription = "Synthetic CT for skill testing"
    ds.Modality = "CT"
    ds.BodyPartExamined = "ABDOMEN"
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
    ds.InstanceNumber = 1

    ds.Rows = 64
    ds.Columns = 64
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"

    rng = np.random.default_rng(42)
    pixel_array = rng.integers(0, 4096, size=(64, 64), dtype=np.uint16)
    ds.PixelData = pixel_array.tobytes()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        ds.save_as(str(out_path), enforce_file_format=True)
    except TypeError:
        ds.save_as(str(out_path), write_like_original=False)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "sample_ct.dcm"
    generate(out)
