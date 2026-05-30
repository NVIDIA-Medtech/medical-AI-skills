"""Assertion grading for paired skill validation scenarios."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MISSING = object()


@dataclass(frozen=True)
class AssertionResult:
    id: str
    kind: str
    passed: bool
    detail: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "pass": self.passed,
            "detail": self.detail,
        }


def _json_path(payload: dict | None, path: str) -> Any:
    if payload is None:
        return MISSING
    cur: Any = payload
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return MISSING
        cur = cur[part]
    return cur


def _display(value: Any) -> str:
    if value is MISSING:
        return "<missing>"
    return repr(value)


def _truthy(value: Any) -> bool:
    if value is MISSING:
        return False
    return bool(value)


def _contains(target: Any, expected: Any) -> bool:
    if target is MISSING:
        return False
    if isinstance(target, list):
        return expected in target or str(expected) in {str(item) for item in target}
    if isinstance(target, str):
        return str(expected).lower() in target.lower()
    return target == expected


def grade_assertion(assertion: dict, *, response_text: str, parsed_json: dict | None) -> AssertionResult:
    aid = assertion["id"]
    kind = assertion["kind"]
    params = assertion["params"]

    if kind == "json_path_value":
        path = params["path"]
        expected = params["expected"]
        actual = _json_path(parsed_json, path)
        if expected == "__truthy__":
            passed = _truthy(actual)
            detail = f"{path} was {_display(actual)}; expected truthy"
        else:
            passed = actual == expected
            detail = f"{path} was {_display(actual)}; expected {_display(expected)}"
        return AssertionResult(aid, kind, passed, detail)

    if kind == "json_path_contains":
        path = params["path"]
        expected = params["expected"]
        actual = _json_path(parsed_json, path)
        passed = _contains(actual, expected)
        return AssertionResult(
            aid,
            kind,
            passed,
            f"{path} was {_display(actual)}; expected to contain {_display(expected)}",
        )

    if kind == "text_contains":
        substring = params["substring"]
        passed = substring.lower() in response_text.lower()
        return AssertionResult(
            aid,
            kind,
            passed,
            f"response {'contains' if passed else 'does not contain'} {_display(substring)}",
        )

    if kind == "text_not_contains":
        substring = params["substring"]
        passed = substring.lower() not in response_text.lower()
        return AssertionResult(
            aid,
            kind,
            passed,
            f"response {'does not contain' if passed else 'contains'} {_display(substring)}",
        )

    return AssertionResult(aid, kind, False, f"unsupported assertion kind: {kind}")


def grade_assertions(assertions: list[dict], *, response_text: str, parsed_json: dict | None) -> list[dict]:
    return [
        grade_assertion(assertion, response_text=response_text, parsed_json=parsed_json).to_dict()
        for assertion in assertions
    ]
