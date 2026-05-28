#!/usr/bin/env bash
# Prove each manifest-declared output-side gate on radiology_note_summarizer
# actually fires when the LLM emits the wrong shape. Without this, MOCK_LLM=1
# is a tautology: the canned response was tuned to make every gate green, so
# "all green" tells you nothing about whether the gates would catch a real
# bad LLM output.
#
# This script runs the skill once per fault-injection mode, then asserts the
# expected gate failed (and only that gate). Outputs land under
# runs/mock_gate_proofs/<mode>/.

set -euo pipefail
cd "$(dirname "$0")/.."

OUT_ROOT=runs/mock_gate_proofs
rm -rf "$OUT_ROOT"
mkdir -p "$OUT_ROOT"

FIXTURE=skills/radiology-note-summarizer/fixtures/case_001_input.json

# Each row: <mode> <expected-failed-gate-key> <expected-status-value>
# The eval_engine writes validation_summary.json with one *_status field per
# gate. We check the named field has the named status, and overall_status
# is not "passed".
declare -a CASES=(
  "pass                     overall_status            passed"
  "fail_factual_echo        factual_echo_status       failed"
  "fail_runtime_integrity   runtime_integrity_status  flagged"
  "fail_sanity              sanity_status             failed"
  "fail_schema              schema_status             failed"
  "fail_model_identity      model_identity_status     failed"
)

failures=0
echo
printf "%-26s %-26s %-10s %-10s %s\n" "mode" "gate" "expected" "actual" "verdict"
printf "%-26s %-26s %-10s %-10s %s\n" "----" "----" "--------" "------" "-------"

for row in "${CASES[@]}"; do
  read -r mode gate expected <<<"$row"
  out="$OUT_ROOT/$mode"
  MOCK_LLM="$mode" python3 eval_engine/run.py skills/radiology-note-summarizer \
    --fixture "$FIXTURE" --out "$out" >/dev/null 2>&1 || true
  read -r actual overall <<<"$(python3 - "$out/validation_summary.json" "$gate" <<'PY'
import json, sys
path, key = sys.argv[1], sys.argv[2]
try:
    d = json.load(open(path))
except (FileNotFoundError, json.JSONDecodeError):
    d = {}
print(d.get(key, 'MISSING'), d.get('overall_status', 'MISSING'))
PY
)"
  if [ "$mode" = "pass" ]; then
    if [ "$overall" = "passed" ]; then verdict="OK"; else verdict="FAIL"; failures=$((failures+1)); fi
  else
    if [ "$actual" = "$expected" ] && [ "$overall" != "passed" ]; then
      verdict="OK"
    else
      verdict="FAIL"
      failures=$((failures+1))
    fi
  fi
  printf "%-26s %-26s %-10s %-10s %s\n" "$mode" "$gate" "$expected" "$actual" "$verdict"
done

echo
if [ "$failures" -gt 0 ]; then
  echo "=== mock-gate proof: $failures FAILURE(S) ==="
  exit 1
fi
echo "=== mock-gate proof: all gates fire as designed ==="
