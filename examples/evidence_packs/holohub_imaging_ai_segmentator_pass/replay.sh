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
export HOLOHUB_ROOT=.workbench_data/holohub
export HOLOHUB_RUN_MODE=container
# HOLOSCAN_OUTPUT_PATH was not set at run time
# HOLOSCAN_MODEL_PATH was not set at run time
# HOLOHUB_TIMEOUT_SECONDS was not set at run time
python3 skills/holohub-imaging-ai-segmentator/scripts/run_holohub_app.py .workbench_data/holohub_input/spleen_10
