#!/usr/bin/env bash
# Auto-generated replay. Best-effort; may not reproduce across
# pydicom/torch/Python version changes (compare environment.lock).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
while [ ! -e "$REPO_ROOT/Makefile" ] && [ "$REPO_ROOT" != "/" ]; do
  REPO_ROOT="$(dirname "$REPO_ROOT")"
done
[ -e "$REPO_ROOT/Makefile" ] || { echo "could not find repo root (looked for Makefile)"; exit 1; }
cd "$REPO_ROOT"
python3 skills/dicom-series-to-volume/scripts/series_to_volume.py skills/dicom-series-to-volume/fixtures/clean_axial --output examples/evidence_packs/dicom_series_to_volume_trusted_pass/skill_run/volume.nii.gz
