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

# Run skill_completeness_v1 against every skill/verifier plus its
# owned negative fixture, then run the manifest-declared reproducibility
# audit. Outputs go to runs/skill_audit/<target>/ and
# runs/reproducibility_audit/<target>/, plus summary JSON files.

set -euo pipefail
cd "$(dirname "$0")/.."

VERIFIER_DIR=verifiers/skill_completeness_v1
OUT_ROOT=runs/skill_audit
rm -rf "$OUT_ROOT"
mkdir -p "$OUT_ROOT"

audit_one() {
  local target="$1"
  local label="$2"
  local out="$OUT_ROOT/$label"
  python3 eval_engine/run.py "$VERIFIER_DIR" --fixture "$target" --out "$out" >/dev/null 2>&1 || true
  python3 -c "
import json
v = json.load(open('$out/output.json'))
row = {
    'target': '$label',
    'target_path': '$target',
    'overall': v['overall'],
    'lifecycle': v.get('capability_lifecycle', {}).get('status', 'unknown'),
    'tier1_passed': v['tier1_structural']['checks_passed'],
    'tier1_total':  v['tier1_structural']['checks_total'],
    'tier2_passed': v['tier2_spec_honesty']['checks_passed'],
    'tier2_total':  v['tier2_spec_honesty']['checks_total'],
    'blocking':     v['blocking_issues_count'],
    'advisory':     v['advisory_issues_count'],
}
print(json.dumps(row))
"
}

# Collect rows for every real skill, every verifier, plus the negative fixture.
{
  for d in skills/*/; do
    [ -f "$d/skill_manifest.yaml" ] || continue
    name="$(basename "$d")"
    audit_one "$d" "$name"
  done
  for d in verifiers/*/; do
    [ -f "$d/skill_manifest.yaml" ] || continue
    name="verifiers_$(basename "$d")"
    audit_one "$d" "$name"
  done
  audit_one verifiers/skill_completeness_v1/fixtures/negative_sloppy_skill negative_sloppy_skill
} > "$OUT_ROOT/_rows.jsonl"

python3 -m eval_engine.skill_audit_summary "$OUT_ROOT"
python3 -m eval_engine.reproducibility
