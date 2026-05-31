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

import json

from tools.with_vs_without import write_nv_model_invariants as invariants


def _walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def test_snapshot_hashing_is_order_stable() -> None:
    left = {"b": [2, 1], "a": {"z": "x"}}
    right = {"a": {"z": "x"}, "b": [2, 1]}

    assert invariants._sha256_json(left) == invariants._sha256_json(right)


def test_checked_in_snapshot_contains_only_invariant_surface() -> None:
    snapshot = json.loads(invariants.SNAPSHOT_PATH.read_text())
    assert snapshot["schema_version"] == invariants.SCHEMA_VERSION
    assert snapshot["experiment_id"] == invariants.EXPERIMENT_ID
    assert snapshot["record_policy"]["raw_records_location"] == "runs/with_vs_without_nv/"
    assert len(snapshot["fingerprints"]["material"]) == 64

    volatile_keys = {
        "absolute_path",
        "command",
        "commands",
        "environment",
        "environment_lock",
        "generated_at",
        "local_path",
        "provider_response",
        "response",
        "responses",
        "stderr",
        "stderr_tail",
        "stdout",
        "stdout_tail",
        "timestamp",
        "token_usage",
        "usage",
    }
    assert volatile_keys.isdisjoint(set(_walk_keys(snapshot)))
