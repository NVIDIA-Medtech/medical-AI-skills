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
# NV_INFER_TOKEN (was set at run time); set it yourself before running replay.sh
export NV_INFER_TOKEN="${NV_INFER_TOKEN:?NV_INFER_TOKEN is required for replay}"
# NVIDIA_API_KEY (was NOT set at run time); set it yourself before running replay.sh
export NVIDIA_API_KEY="${NVIDIA_API_KEY:?NVIDIA_API_KEY is required for replay}"
# MOCK_LLM was not set at run time
python3 skills/radiology-note-summarizer/scripts/summarize.py skills/radiology-note-summarizer/fixtures/case_001_input.json
