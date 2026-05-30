"""Canonical engine status vocabulary.

The string values are wire format: they land in `validation_summary.json`,
`workflow_summary.json`, audit-shell printers, and test assertions. Do not
change their values — only centralize references so the patterns stop
being open-coded across modules.

Pack-vocab statuses (atomic):
- PASSED, SKIPPED, FLAGGED, WARN, GAP, FIXTURE_UNRESOLVED, PREFLIGHT_FAILED

Failed statuses are compound — `"failed"`, `"failed (execution)"`,
`"failed (schema)"`, etc. — so callers should use `is_failed()` instead of
equality on raw strings.

Verifier-vocab outputs (`"pass"` / `"fail"` / `"warn"`) are translated to
pack vocab by `run_trusted._VERIFIER_OUTPUT_NORMALIZATION`; this module
does not duplicate that table.
"""
from __future__ import annotations

PASSED = "passed"
SKIPPED = "skipped"
FLAGGED = "flagged"
WARN = "warn"
GAP = "gap"
FIXTURE_UNRESOLVED = "fixture_unresolved"
PREFLIGHT_FAILED = "preflight_failed"

FAILED = "failed"
_FAILED_PREFIX = "failed"


def is_failed(status: str | None) -> bool:
    """True for `"failed"` and any `"failed (<reason>)"` variant."""
    if not status:
        return False
    return status == _FAILED_PREFIX or status.startswith(_FAILED_PREFIX + " ")


def is_passed(status: str | None) -> bool:
    """True for `"passed"` and any `"passed (<note>)"` variant."""
    if not status:
        return False
    return status == PASSED or status.startswith(PASSED + " ")
