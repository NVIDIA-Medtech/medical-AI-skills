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
python3 verifiers/dicom_preflight_quality_v1/scripts/grade.py examples/evidence_packs/dicom_series_preflight_trusted_pass/skill_run
