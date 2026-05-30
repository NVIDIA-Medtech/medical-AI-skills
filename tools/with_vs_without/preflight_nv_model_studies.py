#!/usr/bin/env python3
"""Preflight NV with-vs-without direct-study reruns without API calls."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.with_vs_without import audit_nv_model_studies as audit  # noqa: E402
from tools.with_vs_without import run_nv_model_studies as studies  # noqa: E402

API_KEY_NAMES = {
    "NVIDIA_API_KEY": ("NVIDIA_API_KEY", "NVIDIA_BUILD_KEY"),
    "NV_INFER_TOKEN": ("NV_INFER_TOKEN",),
}


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        home = Path.home()
        try:
            return "<HOME>/" + str(path.relative_to(home))
        except ValueError:
            return str(path)


def _check(status: str, scope: str, name: str, detail: str) -> dict[str, str]:
    return {"status": status, "scope": scope, "check": name, "detail": detail}


def _env_name_present(names: tuple[str, ...], *, environ: dict[str, str] | None = None, bashrc: Path | None = None) -> str | None:
    env = environ if environ is not None else os.environ
    for name in names:
        if env.get(name, "").strip():
            return name

    rc = bashrc if bashrc is not None else Path.home() / ".bashrc"
    if not rc.is_file():
        return None
    for line in rc.read_text(errors="replace").splitlines():
        stripped = line.strip()
        if not stripped.startswith("export "):
            continue
        for name in names:
            prefix = f"export {name}="
            if not stripped.startswith(prefix):
                continue
            value = stripped.split("=", 1)[1].split("#", 1)[0].strip().strip("'\"")
            if value:
                return name
    return None


def _backends_for_mode(mode: str) -> list[studies.Backend]:
    if mode == "prompts":
        return []
    if mode == "codex-opus":
        return [studies.BACKENDS["gpt55"], studies.BACKENDS["opus"]]
    if mode == "nemotron":
        return [studies.BACKENDS["nemotron"]]
    return [studies.BACKENDS["gpt55"], studies.BACKENDS["opus"], studies.BACKENDS["nemotron"]]


def _issue_code_counts(issues: list[dict[str, str]], *, limit: int = 5) -> str:
    counts = Counter(issue.get("code", "unknown") for issue in issues)
    if not counts:
        return "none"
    return ", ".join(f"{code} x{count}" for code, count in counts.most_common(limit))


def _path_like(value: str) -> bool:
    return "/" in value or value.startswith(".") or value.startswith("~")


def _check_file(path: Path, *, scope: str, name: str) -> dict[str, str]:
    if not path.is_file():
        return _check("error", scope, name, f"missing file: {_rel(path)}")
    if path.stat().st_size <= 0:
        return _check("error", scope, name, f"empty file: {_rel(path)}")
    return _check("pass", scope, name, _rel(path))


def _check_fixture(path: Path, *, scope: str) -> dict[str, str]:
    if path.is_file():
        return _check("pass", scope, "fixture", _rel(path))
    if path.is_dir():
        has_files = any(child.is_file() for child in path.rglob("*"))
        if has_files:
            return _check("pass", scope, "fixture", _rel(path))
        return _check("error", scope, "fixture", f"fixture directory has no files: {_rel(path)}")
    return _check("error", scope, "fixture", f"missing fixture: {_rel(path)}")


def _expected_skill_doc(skill: str) -> str:
    return f"skills/{skill.replace('_', '-')}/SKILL.md"


def _check_scenario_doc_contract(skill: str, scenario: studies.Scenario) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    user_goal = scenario.user_goal
    missing_placeholders = [
        placeholder
        for placeholder in ("{input_path}", "{out_dir}")
        if placeholder not in user_goal
    ]
    if missing_placeholders:
        checks.append(
            _check(
                "error",
                skill,
                "user_goal_placeholders",
                (
                    "scenario.user_goal must include neutral staged input and "
                    f"output placeholders; missing {', '.join(missing_placeholders)}"
                ),
            )
        )
    else:
        checks.append(_check("pass", skill, "user_goal_placeholders", "{input_path}, {out_dir}"))

    expected_with_doc = _expected_skill_doc(skill)
    if scenario.with_doc == (expected_with_doc,):
        checks.append(_check("pass", skill, "with_doc_location", expected_with_doc))
    else:
        checks.append(
            _check(
                "error",
                skill,
                "with_doc_location",
                (
                    "with-skill arm must expose exactly the skill wrapper "
                    f"{expected_with_doc!r}, got {list(scenario.with_doc)!r}"
                ),
            )
        )
    if len(scenario.without_doc) == 1 and scenario.without_doc[0].startswith(
        "tools/with_vs_without/upstream_docs/"
    ):
        checks.append(_check("pass", skill, "without_doc_location", scenario.without_doc[0]))
    else:
        checks.append(
            _check(
                "error",
                skill,
                "without_doc_location",
                (
                    "README baseline must expose exactly one repo-local upstream "
                    f"snapshot under tools/with_vs_without/upstream_docs/, got {list(scenario.without_doc)!r}"
                ),
            )
        )
    return checks


def preflight(
    *,
    skills: list[str] | None = None,
    mode: str = "all",
    repeats: int = studies.DIRECT_REPEATS,
    prompt_root: Path = studies.PROMPT_ARTIFACT_ROOT,
    bashrc: Path | None = None,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    selected = skills or sorted(studies.SCENARIOS)
    checks: list[dict[str, str]] = []

    python_bin = Path(os.environ.get("A2_AGENT_PYTHON") or sys.executable)
    if python_bin.exists():
        checks.append(_check("pass", "host", "python", _rel(python_bin)))
    else:
        checks.append(_check("error", "host", "python", f"missing Python executable: {_rel(python_bin)}"))
    bash = shutil.which("bash")
    checks.append(
        _check("pass", "host", "bash", bash or "bash")
        if bash
        else _check("error", "host", "bash", "bash is required for guarded command execution")
    )

    seen_env_groups: set[tuple[str, ...]] = set()
    for backend in _backends_for_mode(mode):
        names = API_KEY_NAMES.get(backend.env_var, (backend.env_var,))
        if names in seen_env_groups:
            continue
        seen_env_groups.add(names)
        found = _env_name_present(names, environ=environ, bashrc=bashrc)
        if found:
            checks.append(
                _check(
                    "pass",
                    "credentials",
                    "/".join(names),
                    f"configured via {found}; value not printed",
                )
            )
        else:
            checks.append(
                _check(
                    "error",
                    "credentials",
                    "/".join(names),
                    f"set one of {', '.join(names)} before running direct API studies",
                )
            )

    for skill in selected:
        scenario = studies.SCENARIOS[skill]
        checks.extend(_check_scenario_doc_contract(skill, scenario))
        checks.append(_check_fixture(REPO_ROOT / scenario.fixture, scope=skill))
        for doc in scenario.with_doc:
            checks.append(_check_file(REPO_ROOT / doc, scope=skill, name="with_doc"))
        for doc in scenario.without_doc:
            checks.append(_check_file(REPO_ROOT / doc, scope=skill, name="without_doc"))

        prompt = audit.audit_prompt_artifact(skill, prompt_root=prompt_root, repeats=repeats)
        if prompt["status"] == "complete":
            checks.append(_check("pass", skill, "prompt_artifact", prompt["path"]))
        else:
            checks.append(
                _check(
                    "error",
                    skill,
                    "prompt_artifact",
                    (
                        f"{prompt['path']} has {len(prompt['issues'])} issue(s): "
                        f"{_issue_code_counts(prompt['issues'])}"
                    ),
                )
            )

        for key, value in (scenario.env or {}).items():
            if not _path_like(value):
                continue
            path = Path(value).expanduser()
            if path.exists():
                checks.append(_check("pass", skill, f"runtime_env:{key}", _rel(path)))
            else:
                checks.append(
                    _check(
                        "error",
                        skill,
                        f"runtime_env:{key}",
                        f"missing path-like runtime cache: {_rel(path)}",
                    )
                )

    errors = sum(1 for item in checks if item["status"] == "error")
    warnings = sum(1 for item in checks if item["status"] == "warning")
    return {
        "status": "pass" if errors == 0 else "fail",
        "mode": mode,
        "expected_repeats": repeats,
        "summary": {
            "skills": len(selected),
            "checks": len(checks),
            "errors": errors,
            "warnings": warnings,
        },
        "checks": checks,
    }


def _format_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# NV model study preflight: {report['status']}",
        "",
        f"Mode: `{report['mode']}`",
        f"Expected repeats per backend/arm: {report['expected_repeats']}",
        (
            f"Checks: {report['summary']['checks']}; "
            f"errors: {report['summary']['errors']}; "
            f"warnings: {report['summary']['warnings']}"
        ),
        "",
        "| Status | Scope | Check | Detail |",
        "|---|---|---|---|",
    ]
    for item in report["checks"]:
        lines.append(
            f"| {item['status']} | {item['scope']} | {item['check']} | {item['detail']} |"
        )
    if report["status"] != "pass":
        lines.extend(
            [
                "",
                "Fix preflight errors before launching direct study reruns with "
                f"`{studies.EXTERNAL_LLM_DATA_TRANSFER_FLAG}`.",
            ]
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills", nargs="*", default=None, choices=sorted(studies.SCENARIOS))
    parser.add_argument("--mode", choices=["codex-opus", "nemotron", "all", "prompts"], default="all")
    parser.add_argument("--repeats", type=int, default=studies.DIRECT_REPEATS)
    parser.add_argument("--prompt-root", type=Path, default=studies.PROMPT_ARTIFACT_ROOT)
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    args = parser.parse_args(argv)
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")

    report = preflight(
        skills=args.skills,
        mode=args.mode,
        repeats=args.repeats,
        prompt_root=args.prompt_root,
    )
    if args.format == "json":
        sys.stdout.write(json.dumps(report, indent=2) + "\n")
    else:
        sys.stdout.write(_format_markdown(report))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
