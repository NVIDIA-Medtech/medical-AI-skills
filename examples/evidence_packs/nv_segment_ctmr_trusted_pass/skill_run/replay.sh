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
python3 skills/nv-segment-ctmr/scripts/run_ctmr.py skills/nv-segment-ct/fixtures/spleen_03.nii.gz --output-dir runs/nv_segment_ctmr_trusted_pass_current/skill_run/segment_ctmr_outputs --modality CT_BODY
