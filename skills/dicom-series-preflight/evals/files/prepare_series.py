# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Materialize three small synthetic DICOM series for the shared evaluation input."""

import sys
from pathlib import Path

from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid


def main(root: Path) -> None:
    for name, x_axis, subject in (
        ("series-a", -1, ""),
        ("series-b", 1, ""),
        ("series-c", 1, "TEST^SUBJECT"),
    ):
        folder = root / name
        folder.mkdir(parents=True, exist_ok=True)
        study, series = generate_uid(), generate_uid()
        for index in range(4):
            meta = FileMetaDataset()
            meta.TransferSyntaxUID = ExplicitVRLittleEndian
            meta.MediaStorageSOPClassUID = CTImageStorage
            meta.MediaStorageSOPInstanceUID = generate_uid()
            path = folder / f"slice_{index}.dcm"
            ds = FileDataset(str(path), {}, file_meta=meta, preamble=bytes(128))
            ds.SOPClassUID, ds.SOPInstanceUID = CTImageStorage, meta.MediaStorageSOPInstanceUID
            ds.StudyInstanceUID, ds.SeriesInstanceUID = study, series
            ds.PatientName = subject
            ds.Modality = "CT"
            ds.InstanceNumber = index + 1
            ds.ImageOrientationPatient = [x_axis, 0, 0, 0, 1, 0]
            ds.ImagePositionPatient = [0, 0, 2 * index * x_axis]
            ds.PixelSpacing, ds.SliceThickness = [1, 1], 2
            ds.Rows = ds.Columns = 8
            ds.SamplesPerPixel = 1
            ds.PhotometricInterpretation = "MONOCHROME2"
            ds.BitsAllocated = ds.BitsStored = 16
            ds.HighBit, ds.PixelRepresentation = 15, 1
            ds.PixelData = bytes(8 * 8 * 2)
            ds.save_as(path, enforce_file_format=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
