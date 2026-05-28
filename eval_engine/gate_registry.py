"""Shared registry for manifest-declared validation gates."""
from __future__ import annotations

SANITY_OPERATORS = frozenset({
    "eq",
    "ne",
    "gt",
    "gte",
    "lt",
    "lte",
    "matches",
    "length_eq",
    "length_gte",
    "length_lte",
    "contains",
    "contains_any_of",
    "exists",
})

VALIDATION_GATE_KEYS = frozenset({
    "expected_runtime_seconds",
    "sanity_checks",
    "expected_cost",
    "env_pin",
    "factual_echo",
    "runtime_integrity",
    "integrity",
    "reproducibility",
    "benchmark_sanity_checks",
    "benchmark",
})


def gate_categories(manifest: dict) -> list[str]:
    """Return human-readable gate categories declared by a manifest."""
    cats: list[str] = []
    if any(out.get("schema") for out in manifest.get("outputs") or []):
        cats.append("schema")

    validation = manifest.get("validation") or {}
    sanity_checks = validation.get("sanity_checks") or []
    if sanity_checks:
        cats.append(f"sanity×{len(sanity_checks)}")
    if validation.get("expected_runtime_seconds"):
        cats.append("runtime")
    if validation.get("expected_cost"):
        cats.append("cost")
    if validation.get("env_pin"):
        cats.append(f"env_pin×{len(validation['env_pin'])}")
    if validation.get("factual_echo"):
        cats.append(f"factual_echo×{len(validation['factual_echo'])}")
    if validation.get("runtime_integrity"):
        cats.append("runtime_integrity")
    if validation.get("integrity"):
        cats.append("integrity")
    if validation.get("reproducibility"):
        mode = validation["reproducibility"].get("mode", "declared")
        cats.append(f"reproducibility:{mode}")
    if manifest.get("paired_verifiers"):
        cats.append(f"paired_verifiers×{len(manifest['paired_verifiers'])}")
    if manifest.get("llm") or (manifest.get("runtime") or {}).get("llm"):
        cats.append("llm")
    return cats


def unknown_validation_keys(manifest: dict) -> list[str]:
    """Return validation keys the current eval_engine does not know how to classify."""
    validation = manifest.get("validation") or {}
    if not isinstance(validation, dict):
        return []
    return sorted(k for k in validation if k not in VALIDATION_GATE_KEYS)
