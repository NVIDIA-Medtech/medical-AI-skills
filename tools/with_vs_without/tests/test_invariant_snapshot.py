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
    assert (
        snapshot["record_policy"]["raw_records_location"] == "runs/with_vs_without_nv/"
    )
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
