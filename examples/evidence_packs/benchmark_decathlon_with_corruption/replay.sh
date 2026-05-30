#!/usr/bin/env bash
# Auto-generated benchmark replay. Best-effort; case data must still exist locally.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
while [ ! -e "$REPO_ROOT/Makefile" ] && [ "$REPO_ROOT" != "/" ]; do
  REPO_ROOT="$(dirname "$REPO_ROOT")"
done
[ -e "$REPO_ROOT/Makefile" ] || { echo "could not find repo root"; exit 1; }
cd "$REPO_ROOT"
python3 eval_engine/run_benchmark.py skills/nv-segment-ct --benchmark .workbench_data/datasets/decathlon_spleen_with_corruption.benchmark.yaml --out runs/benchmark_with_corruption_independent --jobs 1
