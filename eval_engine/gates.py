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

"""Manifest-declared validation gate evaluators."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from eval_engine.integrity import INTEGRITY_PATTERNS


def _runtime_reported_packages(output_payload: dict | None) -> dict[str, str]:
    """Return package versions self-reported by the skill runtime, if present."""
    if not isinstance(output_payload, dict):
        return {}
    env = output_payload.get("environment")
    if not isinstance(env, dict):
        return {}
    packages = env.get("packages")
    if not isinstance(packages, dict):
        return {}
    return {
        str(name).lower().replace("_", "-"): str(version)
        for name, version in packages.items()
        if version is not None
    }


def _evaluate_env_pin(env_pin: dict | None, output_payload: dict | None = None) -> dict:
    """Evaluate manifest-declared `validation.env_pin` against runtime versions.

    Skills that re-exec into a managed venv can report
    ``output.environment.packages``. Prefer that self-reported runtime over the
    eval_engine host process; fall back to importlib.metadata for simpler skills.
    """
    if not env_pin:
        return {"status": "skipped", "results": [], "reason": "no env_pin declared"}

    try:
        from importlib.metadata import PackageNotFoundError
        from importlib.metadata import version as _pkg_version

        from packaging.specifiers import InvalidSpecifier, SpecifierSet
        from packaging.version import InvalidVersion, Version
    except ImportError as e:
        return {
            "status": "skipped",
            "results": [],
            "reason": f"packaging library unavailable: {e}",
        }

    runtime_packages = _runtime_reported_packages(output_payload)
    results: list[dict] = []
    for pkg, spec in env_pin.items():
        entry: dict = {"package": pkg, "constraint": spec}
        pkg_key = str(pkg).lower().replace("_", "-")
        if pkg_key in runtime_packages:
            installed = runtime_packages[pkg_key]
            entry["source"] = "output.environment.packages"
        else:
            try:
                installed = _pkg_version(pkg)
            except PackageNotFoundError:
                entry.update({"installed": None, "ok": False, "reason": "not installed"})
                results.append(entry)
                continue
            entry["source"] = "eval_engine_host"
        entry["installed"] = installed
        try:
            specset = SpecifierSet(str(spec))
            ok = Version(installed) in specset
            entry["ok"] = ok
            entry["reason"] = (
                "satisfies constraint" if ok else f"{installed} does not satisfy {spec}"
            )
        except (InvalidVersion, InvalidSpecifier) as e:
            entry.update({"ok": False, "reason": f"version-check error: {e}"})
        results.append(entry)

    status = "passed" if results and all(r["ok"] for r in results) else "failed"
    return {"status": status, "results": results}


def _resolve_path(payload: dict, path: str):
    """Walk a dotted path through nested dicts. Returns None if any step missing."""
    val = payload
    for p in path.split("."):
        if isinstance(val, dict):
            val = val.get(p)
        else:
            return None
        if val is None:
            return None
    return val


def _evaluate_sanity_checks(payload: dict, checks: list) -> list:
    """Evaluate manifest-declared sanity checks against an output payload."""
    results = []
    for c in checks or []:
        path = c.get("path")
        val = _resolve_path(payload, path) if path else None
        ok = False
        reason = None
        if "eq" in c:
            ok = val == c["eq"]
            reason = f"{val!r} == {c['eq']!r}" if ok else f"{val!r} != {c['eq']!r}"
        elif "ne" in c:
            ok = val != c["ne"]
            reason = f"{val!r} != {c['ne']!r}" if ok else f"{val!r} == {c['ne']!r}"
        elif "gt" in c:
            ok = val is not None and isinstance(val, (int, float)) and val > c["gt"]
            reason = f"{val} > {c['gt']}" if ok else f"NOT {val} > {c['gt']}"
        elif "gte" in c:
            ok = val is not None and isinstance(val, (int, float)) and val >= c["gte"]
            reason = f"{val} >= {c['gte']}" if ok else f"NOT {val} >= {c['gte']}"
        elif "lt" in c:
            ok = val is not None and isinstance(val, (int, float)) and val < c["lt"]
            reason = f"{val} < {c['lt']}" if ok else f"NOT {val} < {c['lt']}"
        elif "lte" in c:
            ok = val is not None and isinstance(val, (int, float)) and val <= c["lte"]
            reason = f"{val} <= {c['lte']}" if ok else f"NOT {val} <= {c['lte']}"
        elif "matches" in c:
            try:
                pat = re.compile(c["matches"])
                ok = isinstance(val, str) and bool(pat.search(val))
                reason = (
                    f"matched {c['matches']!r}"
                    if ok
                    else f"NOT matched {c['matches']!r} on {val!r}"
                )
            except re.error as e:
                ok = False
                reason = f"invalid regex {c['matches']!r}: {e}"
        elif "length_eq" in c:
            try:
                ok = len(val) == c["length_eq"]
                reason = (
                    f"len={len(val)} == {c['length_eq']}"
                    if ok
                    else f"len={len(val)} != {c['length_eq']}"
                )
            except TypeError:
                ok = False
                reason = f"value not lengthable: {type(val).__name__}"
        elif "length_gte" in c:
            try:
                ok = len(val) >= c["length_gte"]
                reason = (
                    f"len={len(val)} >= {c['length_gte']}"
                    if ok
                    else f"len={len(val)} < {c['length_gte']}"
                )
            except TypeError:
                ok = False
                reason = f"value not lengthable: {type(val).__name__}"
        elif "length_lte" in c:
            try:
                ok = len(val) <= c["length_lte"]
                reason = (
                    f"len={len(val)} <= {c['length_lte']}"
                    if ok
                    else f"len={len(val)} > {c['length_lte']}"
                )
            except TypeError:
                ok = False
                reason = f"value not lengthable: {type(val).__name__}"
        elif "contains" in c:
            target = c["contains"]
            if isinstance(val, str):
                ok = isinstance(target, str) and target in val
                reason = "substring match" if ok else f"{target!r} not in string"
            elif isinstance(val, (list, tuple)):
                ok = target in val
                reason = "member match" if ok else f"{target!r} not in list"
            else:
                ok = False
                reason = f"value type {type(val).__name__} not searchable"
        elif "contains_any_of" in c:
            targets = c["contains_any_of"] or []
            if isinstance(val, str):
                hit = next((t for t in targets if isinstance(t, str) and t in val), None)
                ok = hit is not None
                reason = f"matched {hit!r}" if ok else f"none of {targets!r} in string"
            elif isinstance(val, (list, tuple)):
                hit = next((t for t in targets if t in val), None)
                ok = hit is not None
                reason = f"matched {hit!r}" if ok else f"none of {targets!r} in list"
            else:
                ok = False
                reason = f"value type {type(val).__name__} not searchable"
        elif "exists" in c:
            should_exist = bool(c["exists"])
            present = val is not None
            ok = present == should_exist
            reason = ("present" if present else "absent") + (
                " (expected)" if ok else " (unexpected)"
            )
        results.append({"check": c, "actual": val, "ok": ok, "reason": reason})
    return results


def _missing_output_sanity_results(checks: list) -> list:
    return [
        {
            "check": c,
            "actual": None,
            "ok": False,
            "reason": "sanity_checks declared but output JSON was not available",
        }
        for c in checks or []
    ]


def _sanity_status(results: list) -> str:
    return (
        "passed"
        if results and all(r["ok"] for r in results)
        else ("failed" if any(not r["ok"] for r in results) else "skipped")
    )


def _flatten_strings(val) -> list[str]:
    """Recursively yield all string leaves from val (str/list/dict/scalars)."""
    out: list[str] = []
    if isinstance(val, str):
        out.append(val)
    elif isinstance(val, list):
        for x in val:
            out.extend(_flatten_strings(x))
    elif isinstance(val, dict):
        for x in val.values():
            out.extend(_flatten_strings(x))
    return out


def _evaluate_factual_echo(
    input_payload: dict, output_payload: dict, decls: list
) -> tuple[str, list]:
    """Verify values drawn from an input fixture appear in declared output paths."""
    results = []
    if not decls:
        return "skipped", results
    for d in decls:
        input_path = d.get("input_path")
        mode = d.get("mode", "exact")
        ci = bool(d.get("case_insensitive", False))
        out_paths = d.get("output_paths") or ([d["output_path"]] if d.get("output_path") else [])
        in_val = _resolve_path(input_payload, input_path) if input_path else None
        ok = False
        reason = None
        if in_val is None:
            reason = f"input_path {input_path!r} not found in fixture"
        elif not out_paths:
            reason = "no output_path(s) declared"
        elif mode == "exact":
            actuals = [_resolve_path(output_payload, p) for p in out_paths]
            if ci and isinstance(in_val, str):
                ok = any(isinstance(a, str) and a.lower() == in_val.lower() for a in actuals)
            else:
                ok = any(a == in_val for a in actuals)
            reason = (
                f"input={in_val!r} in {out_paths!r}"
                if ok
                else f"input={in_val!r} not equal to any of {actuals!r}"
            )
        elif mode == "any_contains":
            target = str(in_val)
            blobs = []
            for p in out_paths:
                blobs.extend(_flatten_strings(_resolve_path(output_payload, p)))
            if ci:
                ok = any(target.lower() in b.lower() for b in blobs)
            else:
                ok = any(target in b for b in blobs)
            reason = (
                f"{target!r} found in {out_paths!r}"
                if ok
                else f"{target!r} not found in any of {out_paths!r}"
            )
        else:
            reason = f"unknown mode {mode!r}"
        results.append(
            {
                "input_path": input_path,
                "mode": mode,
                "output_paths": out_paths,
                "input_value": in_val,
                "case_insensitive": ci,
                "ok": ok,
                "reason": reason,
            }
        )
    status = "passed" if all(r["ok"] for r in results) else "failed"
    return status, results


def _evaluate_model_identity(manifest: dict, output_payload: dict) -> tuple[str, list]:
    """If manifest.runtime.llm is declared, verify self-reported runtime identity."""
    llm_decl = (manifest.get("runtime", {}) or {}).get("llm")
    if not llm_decl:
        return "skipped", []
    results = []
    runtime_blob = (output_payload or {}).get("runtime") or {}
    for field in ("model", "endpoint", "temperature"):
        declared = llm_decl.get(field)
        if declared is None:
            continue
        actual = runtime_blob.get(field)
        ok = actual == declared
        results.append(
            {
                "field": field,
                "declared": declared,
                "actual": actual,
                "ok": ok,
                "reason": f"{actual!r} == {declared!r}" if ok else f"{actual!r} != {declared!r}",
            }
        )
    if not results:
        return "skipped", results
    status = "passed" if all(r["ok"] for r in results) else "failed"
    return status, results


def _evaluate_runtime_integrity(
    output_payload: dict, decl: dict, skill_dir: Path
) -> tuple[str, list]:
    """Reapply the integrity-scan pattern bank to manifest-declared output paths."""
    if not decl:
        return "skipped", []
    paths = decl.get("paths") or []
    extra_patterns = []
    pf = decl.get("patterns_file")
    if pf:
        try:
            extra_raw = yaml.safe_load((skill_dir / pf).read_text()) or []
            for item in extra_raw:
                pat = re.compile(item["pattern"], re.I)
                extra_patterns.append((pat, item.get("label", item["pattern"])))
        except Exception as e:
            return "failed", [{"error": f"could not load patterns_file {pf!r}: {e}"}]
    bank = list(INTEGRITY_PATTERNS) + extra_patterns
    findings: list[dict] = []
    for p in paths:
        for blob in _flatten_strings(_resolve_path(output_payload, p)):
            for pat, label in bank:
                for m in pat.finditer(blob):
                    findings.append(
                        {
                            "path": p,
                            "label": label,
                            "match": m.group(0)[:160],
                        }
                    )
    status = "clean" if not findings else "flagged"
    return status, findings
