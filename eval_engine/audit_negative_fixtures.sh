#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

# Run every manifest-declared `negative_fixtures` entry and verify the
# named gate failed (and the run did NOT pass overall). Without this, a
# negative fixture that silently starts passing is indistinguishable
# from a pass-fixture that broke — both look like "exit 0".
#
# Skill/verifier manifests opt into this by adding a top-level
# `negative_fixtures:` list with `path`, `expected_overall`, and
# `expected_failed_gate` per entry. See
# skills/dicom-series-to-volume/skill_manifest.yaml.

set -euo pipefail
cd "$(dirname "$0")/.."

OUT_ROOT=runs/negative_fixture_proofs
rm -rf "$OUT_ROOT"
mkdir -p "$OUT_ROOT"

failures=0
total=0

echo
printf "%-40s %-30s %-22s %-12s %s\n" "skill / fixture" "expected_failed_gate" "actual_status" "overall" "verdict"
printf "%-40s %-30s %-22s %-12s %s\n" "----" "----" "----" "----" "----"

TMP_NEG="$(mktemp)"
trap 'rm -f "$TMP_NEG"' EXIT

for skill_manifest in skills/*/skill_manifest.yaml verifiers/*/skill_manifest.yaml; do
  [ -f "$skill_manifest" ] || continue
  skill_dir=$(dirname "$skill_manifest")
  skill_name=$(basename "$skill_dir")
  python3 - "$skill_manifest" "$TMP_NEG" <<'PY'
import sys, yaml
m = yaml.safe_load(open(sys.argv[1])) or {}
out = open(sys.argv[2], "w")
for entry in (m.get("negative_fixtures") or []):
    path = entry.get("path", "")
    eo = entry.get("expected_overall", "failed")
    eg = entry.get("expected_failed_gate", "")
    out.write(f"{path}\t{eo}\t{eg}\n")
out.close()
PY
  while IFS=$'\t' read -r rel_path exp_overall exp_gate; do
    [ -z "$rel_path" ] && continue
    fixture="$skill_dir/$rel_path"
    label="$skill_name/$(basename "$rel_path")"
    out="$OUT_ROOT/$skill_name-$(basename "$rel_path")"
    python3 eval_engine/run.py "$skill_dir" --fixture "$fixture" --out "$out" >/dev/null 2>&1 || true
    # Map a logical gate name to the validation_summary key, then read both
    # the gate status and overall_status in a single python invocation.
    gate_field="${exp_gate}_status"
    read -r actual_gate overall <<<"$(python3 - "$out/validation_summary.json" "$gate_field" <<'PY'
import json, sys
path, key = sys.argv[1], sys.argv[2]
try:
    d = json.load(open(path))
except (FileNotFoundError, json.JSONDecodeError):
    d = {}
print(d.get(key, 'MISSING'), d.get('overall_status', 'MISSING'))
PY
)"
    total=$((total+1))
    # The gate must be failed (or flagged for runtime_integrity), and
    # overall must NOT be passed.
    bad_gate_ok=0
    case "$actual_gate" in
      failed|flagged) bad_gate_ok=1 ;;
    esac
    if [ "$bad_gate_ok" = "1" ] && [ "$overall" != "passed" ] && [ "$overall" != "MISSING" ]; then
      verdict="OK"
    else
      verdict="FAIL"
      failures=$((failures+1))
    fi
    printf "%-40s %-30s %-22s %-12s %s\n" "$label" "$exp_gate" "$actual_gate" "$overall" "$verdict"
  done <"$TMP_NEG"
done

echo
if [ "$total" = "0" ]; then
  echo "no negative_fixtures declared in any skill manifest"
  exit 0
fi
if [ "$failures" -gt 0 ]; then
  echo "=== negative-fixture proof: $failures / $total FAILED ==="
  exit 1
fi
echo "=== negative-fixture proof: all $total fixtures fired the expected gate ==="
