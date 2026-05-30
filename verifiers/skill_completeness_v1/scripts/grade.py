#!/usr/bin/env python3
"""skill_completeness_v1 -- deterministic audit plus optional LLM review.

Grades a target skill directory against the structural and spec-
honesty requirements documented in CONTRIBUTING.md / AGENTS.md AND the
Anthropic Agent Skills authoring best-practices at
https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices.

Tier 1 (blocking, deterministic)
  - SKILL.md exists with valid Anthropic frontmatter (name + description)
  - frontmatter `name` is ≤ 64 chars, lowercase letters/digits/hyphens
    only, no XML tags, no reserved words ("anthropic", "claude")
  - frontmatter `description` is ≤ 1024 chars, non-empty, no XML tags
  - skill_manifest.yaml exists and parses
  - Manifest carries required top-level fields (id, version, license,
    intended_use, inputs, outputs, runtime)
  - runtime.entrypoint refers to an existing file under the skill dir
  - Each outputs[].schema (when declared) refers to an existing file

Tier 2 (mixed: side_effects + at-least-one-gate are blocking; the rest
are advisory)
  - runtime.side_effects block declared (blocking)
  - At least one validation gate declared (blocking)
  - At least one reproducibility anchor declared (blocking)
  - Exact runtime package pins satisfy matching validation.env_pin constraints
    (blocking)
  - Implemented paired_verifiers entries resolve to a committed verifier
    for user-facing skills that declare them (blocking)
  - At least one fixture under fixtures/ (advisory)
  - Pip imports in scripts ⊆ declared pip_packages (advisory)
  - sanity_checks aren't all trivial (advisory)
  - frontmatter `name` is in vague-name blocklist (advisory)
  - frontmatter `description` written in third person (advisory)
  - SKILL.md body length ≤ 500 lines (advisory)
  - SKILL.md contains Medical AI Skills agent-usability sections (advisory)
  - SKILL.md lists the Available Scripts table header (advisory)
  - SKILL.md Available Scripts entries resolve to committed files (advisory)
  - SKILL.md Available Scripts includes runtime.entrypoint (advisory)
  - SKILL.md Available Scripts argument cells use concrete sketches rather
    than vague cross-references (advisory)
  - SKILL.md Available Scripts entrypoint row includes literal runtime.args
    flags/values such as --output-dir or modality names (advisory)
  - SKILL.md mentions the manifest runtime.entrypoint (advisory)
  - SKILL.md mentions run_script or a concrete Python invocation using the
    runtime.entrypoint (advisory)
  - SKILL.md mentions literal runtime.args tokens such as required flags
    or mode names (advisory)
  - SKILL.md mentions every runtime.env_required variable (advisory)
  - SKILL.md mentions runtime.env_optional and runtime.env_conditional
    variables (advisory)
  - SKILL.md mentions declared side-effect paths, network endpoints, Docker,
    and GPU requirements (advisory)
  - Markdown links in SKILL.md use forward slashes only (advisory)
  - Markdown links resolve to files on disk (advisory)
  - References from SKILL.md are at most one level deep — i.e. linked
    files do not themselves link to further files via the same
    relative-link pattern (advisory)

Tier 3 (LLM-assisted documentation review) is opt-in with LLM_VERIFIER=1 and
uses NVIDIA AI Inference Hub. Tier 4 (test quality) remains deferred and
emits verdict=skipped.
"""
from __future__ import annotations

import ast
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml


VERIFIER_VERSION = "0.4.0"
REQUIRED_MANIFEST_TOP_FIELDS = ("id", "version", "license", "intended_use",
                                "inputs", "outputs", "runtime")
REQUIRED_RUNTIME_FIELDS = ("entrypoint",)

# Anthropic Agent Skills best-practices — frontmatter constraints.
NAME_MAX_LEN = 64
NAME_REGEX = re.compile(r"^[a-z0-9-]+$")
NAME_RESERVED_WORDS = ("anthropic", "claude")
DESCRIPTION_MAX_LEN = 1024

# Vague names Anthropic explicitly says to avoid.
VAGUE_NAME_BLOCKLIST = frozenset({
    "helper", "utils", "tools", "documents", "data", "files",
})

SKILL_MD_BODY_MAX_LINES = 500
REQUIRED_SKILL_MD_SECTIONS = (
    "Purpose",
    "Instructions",
    "Available Scripts",
    "Prerequisites",
    "Limitations",
    "Troubleshooting",
)
AVAILABLE_SCRIPTS_HEADER = "| Script | Purpose | Arguments |"
VAGUE_AVAILABLE_ARGUMENT_PHRASES = (
    "see usage",
    "runtime.args",
    "skill_manifest",
    "manifest args",
)
THIRD_PERSON_RED_FLAGS = (
    "I can ", "I will ", "I'll ", "I help",
    "You can ", "You will ", "You'll ",
    "We can ", "We will ", "We'll ",
)
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
SKILL_DIR = Path(__file__).resolve().parent.parent
VERIFIERS_ROOT = SKILL_DIR.parent
REPO_ROOT = VERIFIERS_ROOT.parent
BEST_PRACTICES_RUBRIC = SKILL_DIR / "reference" / "agent_skill_best_practices.md"
LIFECYCLE_ORDER = ("draft", "runnable", "gated", "verified", "published")

# Optional Tier 3 LLM review. This stays opt-in so CI and local structural
# audits remain reproducible without network access.
LLM_VERIFIER_ENABLE_VALUES = {"1", "true", "yes", "on", "required"}
LLM_VERIFIER_ENDPOINT_DEFAULT = "https://inference-api.nvidia.com/v1"
LLM_VERIFIER_MODEL_DEFAULT = "azure/openai/gpt-5.5"
LLM_VERIFIER_TIMEOUT_SECONDS = 60
LLM_VERIFIER_MAX_TOKENS = 4096

# Imports that are part of the standard library and need no declaration.
STDLIB_MODULES = frozenset({
    "__future__", "abc", "argparse", "ast", "base64", "binascii", "collections",
    "contextlib", "copy", "csv", "dataclasses", "datetime", "enum",
    "fnmatch", "functools", "glob", "hashlib", "io", "importlib", "inspect",
    "itertools", "json", "logging", "math", "os", "pathlib", "platform",
    "queue", "random", "re", "shlex", "shutil", "signal", "string",
    "statistics", "struct", "subprocess", "sys", "tempfile", "textwrap",
    "threading", "time", "traceback", "types", "typing", "urllib", "uuid", "venv",
    "warnings", "xml", "zipfile", "zlib",
})

# import-name -> pip distribution name (for the few non-trivial mappings).
IMPORT_TO_PIP = {
    "yaml": "pyyaml",
    "PIL": "pillow",
    "skimage": "scikit-image",
    "sklearn": "scikit-learn",
    "cv2": "opencv-python",
    "ignite": "pytorch-ignite",
    "torch_tensorrt": "torch-tensorrt",
}


def _norm_pkg(spec: str) -> str:
    """Strip a pip spec down to the bare package name (lowercased, deduped)."""
    s = spec.strip().lower()
    for sep in (">=", "<=", "==", "!=", "~=", ">", "<", ";", "[", " "):
        if sep in s:
            s = s.split(sep, 1)[0]
    return s.strip()


def _local_module_names(skill_dir: Path) -> set[str]:
    """Names of .py files anywhere under the skill directory or its bundle/.
    These are treated as local imports (e.g. `hugging_face_pipeline` from a
    HuggingFace repo cached under bundle/) and exempted from the pip-imports
    declaration check."""
    locals_: set[str] = set()
    # the Medical AI Skills convention is to keep skill-owned entrypoints under a
    # top-level scripts/ directory; some thin wrappers also import upstream
    # modules named scripts.* after changing cwd into the cached checkout.
    locals_.add("scripts")
    for py in skill_dir.rglob("*.py"):
        # Don't claim our own scripts/ as third-party-package candidates.
        locals_.add(py.stem)
    shared_dir = skill_dir.parent / "_shared"
    if shared_dir.is_dir():
        locals_.add(shared_dir.name)
        for py in shared_dir.rglob("*.py"):
            locals_.add(py.stem)
    if skill_dir.parent == VERIFIERS_ROOT:
        locals_.add("verifiers")
    return locals_


def _scan_imports(scripts_dir: Path, skill_dir: Path) -> set[str]:
    """Best-effort: top-level imported module names from every .py under scripts/.
    Filters out names that resolve to a local .py file under the skill dir."""
    found: set[str] = set()
    local_names = _local_module_names(skill_dir)
    if not scripts_dir.is_dir():
        return found
    for py in scripts_dir.rglob("*.py"):
        try:
            text = py.read_text()
            tree = ast.parse(text, filename=str(py))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name.split(".")[0].strip()
                    if mod and mod not in local_names:
                        found.add(mod)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    continue
                mod = (node.module or "").split(".")[0].strip()
                if mod and mod not in local_names:
                    found.add(mod)
    return found


def _external_asset_module_names(manifest: dict) -> set[str]:
    """Module names declared as files supplied by runtime.external_assets."""
    modules: set[str] = set()
    runtime = manifest.get("runtime") or {}
    for asset in runtime.get("external_assets") or []:
        if not isinstance(asset, dict):
            continue
        for item in asset.get("contains") or []:
            name = str(item).strip()
            if name.endswith(".py"):
                modules.add(Path(name).stem)
    return modules


def _parse_frontmatter(skill_md_text: str) -> tuple[bool, str | None, dict | None, str]:
    """Returns (ok, error_msg, parsed_dict, body_text). body_text is whatever
    follows the closing '---' (used for body-length and link checks). When
    the frontmatter is malformed body_text is the entire input."""
    if not skill_md_text.startswith("---\n"):
        return False, "no leading '---' (Anthropic-style frontmatter required)", None, skill_md_text
    end = skill_md_text.find("\n---\n", 4)
    if end == -1:
        return False, "frontmatter not terminated by a second '---'", None, skill_md_text
    fm = skill_md_text[4:end]
    body = skill_md_text[end + len("\n---\n"):]
    try:
        data = yaml.safe_load(fm)
    except Exception as e:
        return False, f"frontmatter is not valid YAML: {e}", None, body
    if not isinstance(data, dict):
        return False, "frontmatter is not a YAML mapping", None, body
    return True, None, data, body


def _frontmatter_ok(skill_md_text: str) -> tuple[bool, str | None]:
    ok, err, data, _body = _parse_frontmatter(skill_md_text)
    if not ok:
        return False, err
    assert data is not None
    if not data.get("name"):
        return False, "frontmatter missing required field 'name'"
    if not data.get("description"):
        return False, "frontmatter missing required field 'description'"
    return True, None


def _check_pass(name: str) -> dict:
    return {"check": name, "pass": True}


def _check_fail(name: str, msg: str, severity: str = "block") -> dict:
    return {"check": name, "pass": False, "msg": msg, "severity": severity}


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[truncated for LLM verifier]..."


def _available_script_rows(body: str) -> list[dict[str, str]]:
    """Extract rows from the Available Scripts table."""
    rows: list[dict[str, str]] = []
    in_section = False
    for raw in body.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            if in_section:
                break
            in_section = line == "## Available Scripts"
            continue
        if not in_section:
            continue
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        match = re.fullmatch(r"`([^`]+)`", cells[0])
        if match:
            rows.append({
                "path": match.group(1).strip(),
                "purpose": cells[1],
                "arguments": " | ".join(cells[2:]).strip(),
            })
    return rows


def _vague_available_script_arguments(rows: list[dict[str, str]]) -> list[str]:
    vague: list[str] = []
    for row in rows:
        arguments = row.get("arguments", "")
        arguments_l = arguments.lower()
        if not arguments.strip():
            vague.append(row["path"])
            continue
        if any(phrase in arguments_l for phrase in VAGUE_AVAILABLE_ARGUMENT_PHRASES):
            vague.append(row["path"])
    return vague


def _path_stays_under(parent: Path, child: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _runtime_literal_args(runtime: dict) -> list[str]:
    args = runtime.get("args") or []
    if not isinstance(args, list):
        return []
    literals: list[str] = []
    for item in args:
        if not isinstance(item, str):
            continue
        if item.startswith("${") and item.endswith("}"):
            continue
        if "${" in item:
            continue
        literals.append(item)
    return literals


def _env_names_from_value(value: object) -> list[str]:
    names: list[str] = []
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if isinstance(value, list):
        for item in value:
            names.extend(_env_names_from_value(item))
    elif isinstance(value, dict):
        for item in value.values():
            names.extend(_env_names_from_value(item))
    return names


def _dedupe_names(names: list[str]) -> list[str]:
    return list(dict.fromkeys(name for name in names if name))


def _runtime_side_effect_env(runtime: dict, key: str) -> list[str]:
    side_effects = runtime.get("side_effects") or {}
    if not isinstance(side_effects, dict):
        return []
    return _env_names_from_value(side_effects.get(key))


def _runtime_env_required(runtime: dict) -> list[str]:
    return _dedupe_names(
        _env_names_from_value(runtime.get("env_required"))
        + _runtime_side_effect_env(runtime, "env_required")
    )


def _runtime_env_optional(runtime: dict) -> list[str]:
    return _dedupe_names(
        _env_names_from_value(runtime.get("env_optional"))
        + _runtime_side_effect_env(runtime, "env_optional")
    )


def _runtime_env_conditional(runtime: dict) -> list[str]:
    return _dedupe_names(_env_names_from_value(runtime.get("env_conditional")))


def _side_effect_value_tokens(values: object) -> list[str]:
    tokens: list[str] = []
    if isinstance(values, str):
        return [values] if values.strip() else []
    if isinstance(values, list):
        for item in values:
            if isinstance(item, str):
                tokens.extend(_side_effect_value_tokens(item))
            elif isinstance(item, dict):
                path = item.get("path") or item.get("endpoint")
                if isinstance(path, str) and path.strip():
                    tokens.append(path.strip())
    return _dedupe_names(tokens)


def _side_effect_doc_candidates(key: str, token: str) -> list[str]:
    candidates = [token]
    if key == "network_endpoints" and "://" in token:
        candidates.append(token.split("://", 1)[1].rstrip("/"))
    if token.startswith("~/"):
        candidates.append(token[2:])
    if token.startswith("$"):
        candidates.append(token[1:].split("/", 1)[0])
    if token.startswith("<caller-provided"):
        candidates.extend(["--output-dir", "--out", "output directory"])
    if "${" in token:
        candidates.extend(["--output", "--output-dir", "output"])
    return _dedupe_names(candidates)


def _entrypoint_available_script_row(
    rows: list[dict[str, str]],
    entrypoint: str | None,
) -> dict[str, str] | None:
    if not entrypoint:
        return None
    for row in rows:
        if row.get("path") == entrypoint:
            return row
    return None


def _manifest_io_doc_candidates(item: dict) -> list[str]:
    candidates: list[str] = []
    name = item.get("name")
    if isinstance(name, str) and name.strip():
        clean = name.strip()
        candidates.extend([clean, clean.replace("_", " "), clean.replace("_", "-")])
        for suffix, replacement in (
            ("_json", " json"),
            ("_dir", " directory"),
            ("_path", " path"),
        ):
            if clean.endswith(suffix):
                candidates.append(clean[: -len(suffix)].replace("_", " ") + replacement)
    return _dedupe_names(candidates)


def _manifest_io_mentions_missing(manifest: dict, body: str) -> list[str]:
    body_l = body.lower()
    missing: list[str] = []
    for section in ("inputs", "outputs"):
        items = manifest.get(section) or []
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            candidates = _manifest_io_doc_candidates(item)
            if not candidates:
                continue
            if not any(candidate.lower() in body_l for candidate in candidates):
                name = item.get("name") or "<unnamed>"
                missing.append(f"{section}:{name}")
    return missing


def _paired_verifier_checks(manifest: dict) -> list[dict]:
    """Validate top-level paired_verifiers declarations when present."""
    paired = manifest.get("paired_verifiers") or []
    if not paired:
        return []
    checks: list[dict] = []
    if not isinstance(paired, list):
        return [_check_fail("paired_verifiers_shape", "paired_verifiers must be a list")]

    for idx, item in enumerate(paired):
        if not isinstance(item, dict):
            checks.append(_check_fail(
                "paired_verifier_entry_shape",
                f"paired_verifiers[{idx}] must be a mapping",
            ))
            continue
        verifier_id = str(item.get("id") or "")
        status = str(item.get("status") or "")
        if not verifier_id:
            checks.append(_check_fail(
                "paired_verifier_id_present",
                f"paired_verifiers[{idx}] is missing id",
            ))
            continue
        if status not in {"planned", "implemented"}:
            checks.append(_check_fail(
                "paired_verifier_status_valid",
                f"paired_verifiers[{idx}] status must be planned or implemented, got {status!r}",
            ))
            continue
        if status == "planned":
            checks.append(_check_fail(
                "paired_verifier_implemented_exists",
                f"{verifier_id} is declared planned; implemented verifier is still missing",
                severity="advisory",
            ))
            continue

        short_name = verifier_id.rsplit(".", 1)[-1].rsplit("/", 1)[-1]
        candidate = VERIFIERS_ROOT / short_name
        if (candidate / "skill_manifest.yaml").exists():
            checks.append(_check_pass("paired_verifier_implemented_exists"))
        else:
            checks.append(_check_fail(
                "paired_verifier_implemented_exists",
                f"{verifier_id} is marked implemented but {candidate}/skill_manifest.yaml does not exist",
            ))
    return checks


def _pkg_name_from_spec(spec: str) -> str | None:
    match = re.match(r"^\s*([A-Za-z0-9_.-]+)", str(spec))
    if not match:
        return None
    name = match.group(1)
    if name.startswith(("<", ">", "=", "!", "~")):
        return None
    return name.lower().replace("_", "-")


def _has_version_constraint(spec: str) -> bool:
    return bool(re.search(r"(==|!=|>=|<=|~=|>|<)", str(spec)))


def _has_reproducibility_anchor(manifest: dict) -> bool:
    refs = manifest.get("upstream_refs") or []
    if isinstance(refs, list) and any(
        isinstance(ref, dict)
        and any(ref.get(k) for k in ("git_commit", "revision", "version", "version_constraint"))
        for ref in refs
    ):
        return True
    runtime = manifest.get("runtime") or {}
    side_effects = runtime.get("side_effects") or {}
    if isinstance(side_effects, dict) and any(
        _has_version_constraint(str(pkg))
        for pkg in side_effects.get("pip_packages") or []
    ):
        return True
    dependencies = runtime.get("dependencies") or {}
    if isinstance(dependencies, dict) and any(
        _has_version_constraint(str(spec)) for spec in dependencies.values()
    ):
        return True
    llm_decl = runtime.get("llm") or manifest.get("llm")
    return bool(isinstance(llm_decl, dict) and llm_decl.get("model"))


def _reproducibility_check_errors(manifest: dict, skill_dir: Path) -> list[str]:
    validation = manifest.get("validation") or {}
    repro = validation.get("reproducibility")
    if not isinstance(repro, dict):
        return ["validation.reproducibility block missing"]
    mode = repro.get("mode")
    if mode not in ("repeat", "preflight"):
        return ["validation.reproducibility.mode must be repeat or preflight"]
    fixture = repro.get("fixture")
    if not isinstance(fixture, str) or not fixture.strip():
        return ["validation.reproducibility.fixture missing"]
    fixture_path = Path(fixture)
    if not fixture_path.is_absolute():
        fixture_path = skill_dir / fixture_path
    if not fixture_path.exists():
        builder = repro.get("fixture_builder")
        if not isinstance(builder, str) or not builder.strip():
            return [f"validation.reproducibility.fixture does not exist: {fixture}"]
        builder_path = Path(builder)
        if builder_path.is_absolute():
            return ["validation.reproducibility.fixture_builder must be relative to the skill dir"]
        builder_path = (skill_dir / builder_path).resolve()
        try:
            builder_path.relative_to(skill_dir.resolve())
        except ValueError:
            return ["validation.reproducibility.fixture_builder must stay under the skill dir"]
        if not builder_path.is_file():
            return [f"validation.reproducibility.fixture_builder does not exist: {builder}"]
    runs = repro.get("runs", 2)
    if not isinstance(runs, int) or runs < 2:
        return ["validation.reproducibility.runs must be an integer >= 2"]
    if mode == "preflight" and not str(repro.get("reason") or "").strip():
        return ["validation.reproducibility.reason is required for preflight mode"]
    return []


def _exact_runtime_package_pins(manifest: dict) -> dict[str, str]:
    pins: dict[str, str] = {}
    runtime = manifest.get("runtime") or {}
    dependencies = runtime.get("dependencies") or {}
    if isinstance(dependencies, dict):
        for name, constraint in dependencies.items():
            constraint_s = str(constraint).strip()
            if constraint_s.startswith("=="):
                pins[str(name).lower().replace("_", "-")] = constraint_s[2:].strip()
    side_effects = runtime.get("side_effects") or {}
    if isinstance(side_effects, dict):
        for spec in side_effects.get("pip_packages") or []:
            spec_s = str(spec).strip()
            if "==" not in spec_s:
                continue
            name = _pkg_name_from_spec(spec_s)
            if not name:
                continue
            pins[name] = spec_s.split("==", 1)[1].split(";", 1)[0].strip()
    return pins


def _version_tuple(version: str) -> tuple[int, ...]:
    parts = re.split(r"[.+-]", str(version), maxsplit=1)[0].split(".")
    nums: list[int] = []
    for part in parts:
        match = re.match(r"^(\d+)", part)
        nums.append(int(match.group(1)) if match else 0)
    return tuple(nums)


def _cmp_version(left: str, right: str) -> int:
    a = list(_version_tuple(left))
    b = list(_version_tuple(right))
    width = max(len(a), len(b))
    a.extend([0] * (width - len(a)))
    b.extend([0] * (width - len(b)))
    return (a > b) - (a < b)


def _version_satisfies_spec(version: str, spec: str) -> bool:
    spec = str(spec).strip()
    if spec in {"", "*"}:
        return True
    for clause in [part.strip() for part in spec.split(",") if part.strip()]:
        match = re.match(r"^(==|!=|>=|<=|>|<)\s*([A-Za-z0-9_.+-]+)$", clause)
        if not match:
            continue
        op, target = match.groups()
        cmp = _cmp_version(version, target)
        if op == "==" and cmp != 0:
            return False
        if op == "!=" and cmp == 0:
            return False
        if op == ">=" and cmp < 0:
            return False
        if op == "<=" and cmp > 0:
            return False
        if op == ">" and cmp <= 0:
            return False
        if op == "<" and cmp >= 0:
            return False
    return True


def _env_pin_exact_pin_conflicts(manifest: dict) -> list[str]:
    validation = manifest.get("validation") or {}
    env_pin = validation.get("env_pin") or {}
    if not isinstance(env_pin, dict):
        return []
    pins = _exact_runtime_package_pins(manifest)
    conflicts: list[str] = []
    for name, pinned_version in pins.items():
        constraint = env_pin.get(name)
        if constraint is None:
            constraint = env_pin.get(name.replace("-", "_"))
        if constraint is None:
            continue
        if not _version_satisfies_spec(pinned_version, str(constraint)):
            conflicts.append(
                f"{name} exact runtime pin {pinned_version!r} does not satisfy "
                f"validation.env_pin constraint {constraint!r}"
            )
    return conflicts


def _read_text_excerpt(path: Path, max_chars: int) -> str:
    try:
        return _truncate(path.read_text(), max_chars)
    except Exception as e:
        return f"[could not read {path.name}: {e}]"


def _target_file_listing(skill_dir: Path) -> list[str]:
    skip_dirs = {"bundle", "bundles", "__pycache__", ".cache", ".git"}
    files: list[str] = []
    for p in sorted(skill_dir.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(skill_dir)
        if any(part in skip_dirs for part in rel.parts):
            continue
        files.append(str(rel))
    return files


def _target_context_for_llm(skill_dir: Path) -> dict:
    """Bounded context for the advisory LLM verifier.

    The LLM gets the skill docs and manifest plus small script/test/schema
    excerpts. Large bundles and cached model assets are intentionally skipped.
    """
    excerpts: dict[str, str] = {}
    for rel, limit in (
        ("SKILL.md", 14000),
        ("skill_manifest.yaml", 10000),
    ):
        path = skill_dir / rel
        if path.exists():
            excerpts[rel] = _read_text_excerpt(path, limit)

    for folder, pattern, per_file_limit, max_files in (
        ("scripts", "*.py", 5000, 3),
        ("tests", "*.py", 5000, 3),
        ("validators", "*.json", 4000, 3),
    ):
        base = skill_dir / folder
        if not base.is_dir():
            continue
        for path in sorted(base.rglob(pattern))[:max_files]:
            rel = str(path.relative_to(skill_dir))
            excerpts[rel] = _read_text_excerpt(path, per_file_limit)

    return {
        "files": _target_file_listing(skill_dir)[:120],
        "excerpts": excerpts,
    }


def _chat_completions_url(endpoint: str) -> str:
    base = endpoint.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return base + "/chat/completions"


def _parse_json_from_model(text: str) -> dict:
    s = text.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return json.loads(s)


def _normalise_llm_checks(payload: dict) -> list[dict]:
    checks = payload.get("checks")
    if not isinstance(checks, list):
        checks = []
    normalised: list[dict] = []
    for idx, item in enumerate(checks):
        if not isinstance(item, dict):
            continue
        name = str(item.get("check") or f"llm_check_{idx + 1}")
        ok = bool(item.get("pass"))
        msg = str(item.get("msg") or item.get("reason") or "")
        check = {
            "check": name,
            "pass": ok,
            # Tier 3 is qualitative. Keep all findings advisory so an LLM
            # cannot autonomously reject a skill that passed deterministic gates.
            "severity": "advisory",
        }
        if msg:
            check["msg"] = msg
        evidence = item.get("evidence")
        if evidence:
            check["evidence"] = str(evidence)
        normalised.append(check)

    if not normalised and payload.get("verdict") in {"pass", "fail"}:
        normalised.append({
            "check": "llm_overall_documentation_review",
            "pass": payload.get("verdict") == "pass",
            "severity": "advisory",
            "msg": str(payload.get("summary") or "LLM returned only an overall verdict"),
        })
    return normalised


def grade_tier3_llm(skill_dir: Path) -> dict:
    mode = os.environ.get("LLM_VERIFIER", "").strip().lower()
    if mode not in LLM_VERIFIER_ENABLE_VALUES:
        return {
            "tier_id": "tier3_documentation",
            "verdict": "skipped",
            "reason": "set LLM_VERIFIER=1 and NV_INFER_TOKEN to enable NVIDIA-hosted advisory review",
        }

    api_key = os.environ.get("NV_INFER_TOKEN", "")
    endpoint = os.environ.get("LLM_VERIFIER_ENDPOINT", LLM_VERIFIER_ENDPOINT_DEFAULT)
    model = os.environ.get("LLM_VERIFIER_MODEL", LLM_VERIFIER_MODEL_DEFAULT)
    if not api_key:
        return {
            "tier_id": "tier3_documentation",
            "verdict": "skipped",
            "reason": "LLM_VERIFIER is enabled but NV_INFER_TOKEN is not set",
            "llm": {"endpoint": endpoint, "model": model},
        }

    rubric = _read_text_excerpt(BEST_PRACTICES_RUBRIC, 9000)
    context = _target_context_for_llm(skill_dir)
    system_prompt = (
        "You are an advisory skill-quality verifier for a medical-imaging "
        "medical AI skills. Review only authoring quality, manifest/docs "
        "consistency, and testability. Do not make clinical claims. "
        "Return JSON only."
    )
    response_schema = {
        "verdict": "pass or fail",
        "summary": "one short sentence",
        "checks": [
            {
                "check": "specific_check_name",
                "pass": True,
                "msg": "brief issue or rationale",
                "evidence": "file or quoted phrase if useful",
            }
        ],
    }
    user_prompt = (
        "Review the target skill against the rubric below. Treat findings as "
        "advisory unless the deterministic manifest spec is obviously "
        "contradicted. Prefer concrete, file-grounded findings over style "
        "opinions. Return exactly one JSON object matching this shape:\n"
        + json.dumps(response_schema, indent=2)
        + "\n\nRubric:\n"
        + rubric
        + "\n\nTarget skill context:\n"
        + json.dumps(context, indent=2)
    )

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": LLM_VERIFIER_MAX_TOKENS,
        "seed": 42,
    }
    req = urllib.request.Request(
        _chat_completions_url(endpoint),
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=LLM_VERIFIER_TIMEOUT_SECONDS) as resp:
            raw_response = json.loads(resp.read())
        message = raw_response["choices"][0]["message"]
        content = message.get("content", "")
        if isinstance(content, list):
            content = "\n".join(str(part.get("text", part)) for part in content)
        payload = _parse_json_from_model(str(content))
    except urllib.error.HTTPError as e:
        excerpt = e.read()[:600].decode("utf-8", errors="replace")
        return {
            "tier_id": "tier3_documentation",
            "verdict": "skipped",
            "reason": f"LLM verifier HTTP {e.code} {e.reason}: {excerpt}",
            "llm": {"endpoint": endpoint, "model": model},
        }
    except Exception as e:
        return {
            "tier_id": "tier3_documentation",
            "verdict": "skipped",
            "reason": f"LLM verifier could not produce a parseable review: {e}",
            "llm": {"endpoint": endpoint, "model": model},
        }

    checks = _normalise_llm_checks(payload)
    advisory = [c for c in checks if not c.get("pass")]
    usage = raw_response.get("usage") or {}
    return {
        "tier_id": "tier3_documentation",
        "verdict": "fail" if advisory else "pass",
        "checks_passed": sum(1 for c in checks if c.get("pass")),
        "checks_total": len(checks),
        "blocking_issues": [],
        "advisory_issues": advisory,
        "summary": str(payload.get("summary") or ""),
        "llm": {
            "endpoint": endpoint,
            "model": raw_response.get("model") or model,
            "requested_model": model,
            "request_id": raw_response.get("id"),
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "source": "inference-api.nvidia.com chat/completions",
            "rubric": str(BEST_PRACTICES_RUBRIC.relative_to(SKILL_DIR)),
        },
    }


def grade_tier1(skill_dir: Path) -> list[dict]:
    """All Tier 1 issues are blocking."""
    checks: list[dict] = []

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        checks.append(_check_fail("skill_md_exists", "missing SKILL.md"))
    else:
        text = skill_md.read_text()
        ok, err, fm, _body = _parse_frontmatter(text)
        if ok and fm is not None:
            checks.append(_check_pass("skill_md_frontmatter_valid"))
            # Anthropic-spec format checks on the parsed frontmatter (Tier 1
            # blocking — these are upstream spec requirements).
            name = fm.get("name") or ""
            if not name:
                checks.append(_check_fail("frontmatter_name_present",
                                          "frontmatter missing required field 'name'"))
            else:
                checks.append(_check_pass("frontmatter_name_present"))
                if len(name) <= NAME_MAX_LEN:
                    checks.append(_check_pass("frontmatter_name_length"))
                else:
                    checks.append(_check_fail("frontmatter_name_length",
                                              f"name length {len(name)} exceeds Anthropic limit {NAME_MAX_LEN}"))
                if NAME_REGEX.match(name):
                    checks.append(_check_pass("frontmatter_name_format"))
                else:
                    checks.append(_check_fail("frontmatter_name_format",
                                              f"name {name!r} must match ^[a-z0-9-]+$ (lowercase letters, digits, hyphens only — Anthropic best-practices)"))
                lower = name.lower()
                if any(w in lower for w in NAME_RESERVED_WORDS):
                    checks.append(_check_fail("frontmatter_name_no_reserved",
                                              f"name {name!r} contains a reserved word from {list(NAME_RESERVED_WORDS)}"))
                else:
                    checks.append(_check_pass("frontmatter_name_no_reserved"))
                if "<" in name or ">" in name:
                    checks.append(_check_fail("frontmatter_name_no_xml",
                                              "name contains XML tag characters"))
                else:
                    checks.append(_check_pass("frontmatter_name_no_xml"))

            description = fm.get("description") or ""
            if not description.strip():
                checks.append(_check_fail("frontmatter_description_present",
                                          "frontmatter missing required field 'description'"))
            else:
                checks.append(_check_pass("frontmatter_description_present"))
                if len(description) <= DESCRIPTION_MAX_LEN:
                    checks.append(_check_pass("frontmatter_description_length"))
                else:
                    checks.append(_check_fail("frontmatter_description_length",
                                              f"description length {len(description)} exceeds Anthropic limit {DESCRIPTION_MAX_LEN}"))
                if "<" in description or ">" in description:
                    checks.append(_check_fail("frontmatter_description_no_xml",
                                              "description contains XML tag characters"))
                else:
                    checks.append(_check_pass("frontmatter_description_no_xml"))
        else:
            checks.append(_check_fail("skill_md_frontmatter_valid", err or "unknown frontmatter error"))

    manifest_path = skill_dir / "skill_manifest.yaml"
    if not manifest_path.exists():
        checks.append(_check_fail("skill_manifest_exists", "missing skill_manifest.yaml"))
        return checks

    try:
        manifest = yaml.safe_load(manifest_path.read_text())
    except Exception as e:
        checks.append(_check_fail("skill_manifest_yaml_valid", f"YAML parse error: {e}"))
        return checks
    if not isinstance(manifest, dict):
        checks.append(_check_fail("skill_manifest_yaml_valid", "manifest is not a YAML mapping"))
        return checks
    checks.append(_check_pass("skill_manifest_yaml_valid"))

    for field in REQUIRED_MANIFEST_TOP_FIELDS:
        if manifest.get(field) is not None:
            checks.append(_check_pass(f"manifest_field:{field}"))
        else:
            checks.append(_check_fail(f"manifest_field:{field}", f"manifest missing required field '{field}'"))

    runtime = manifest.get("runtime") or {}
    if isinstance(runtime, dict):
        for field in REQUIRED_RUNTIME_FIELDS:
            if runtime.get(field):
                checks.append(_check_pass(f"runtime_field:{field}"))
            else:
                checks.append(_check_fail(f"runtime_field:{field}", f"runtime.{field} missing"))
        entrypoint = runtime.get("entrypoint")
        if entrypoint:
            ep_path = (skill_dir / entrypoint).resolve()
            if ep_path.exists():
                checks.append(_check_pass("entrypoint_file_exists"))
            else:
                checks.append(_check_fail("entrypoint_file_exists",
                                          f"runtime.entrypoint refers to {entrypoint!r} which does not exist on disk"))
    else:
        checks.append(_check_fail("runtime_block_is_mapping", "runtime is not a YAML mapping"))

    for idx, out in enumerate(manifest.get("outputs") or []):
        if not isinstance(out, dict):
            continue
        schema_rel = out.get("schema")
        if not schema_rel:
            continue
        schema_path = (skill_dir / schema_rel).resolve()
        check_name = f"output_schema_exists:outputs[{idx}].schema"
        if schema_path.exists():
            checks.append(_check_pass(check_name))
        else:
            checks.append(_check_fail(check_name,
                                      f"outputs[{idx}].schema={schema_rel!r} does not exist"))

    return checks


def grade_tier2(skill_dir: Path) -> list[dict]:
    """Mixed severity. side_effects + at-least-one-gate are blocking; the rest advisory."""
    checks: list[dict] = []
    manifest_path = skill_dir / "skill_manifest.yaml"
    if not manifest_path.exists():
        return checks  # Tier 1 already failed; nothing more to grade
    try:
        manifest = yaml.safe_load(manifest_path.read_text()) or {}
    except Exception:
        return checks

    runtime = manifest.get("runtime") or {}
    side_effects = runtime.get("side_effects") if isinstance(runtime, dict) else None
    if side_effects is not None:
        checks.append(_check_pass("runtime_side_effects_declared"))
    else:
        checks.append(_check_fail("runtime_side_effects_declared",
                                  "runtime.side_effects block missing — declare it (CONTRIBUTING.md §Side effects)"))

    validation = manifest.get("validation") or {}
    has_gate = any(validation.get(k) for k in (
        "expected_runtime_seconds", "sanity_checks", "expected_cost",
        "factual_echo", "runtime_integrity", "model_identity",
        "expected_axcodes",
    ))
    if has_gate:
        checks.append(_check_pass("at_least_one_validation_gate"))
    else:
        checks.append(_check_fail("at_least_one_validation_gate",
                                  "no validation gate declared — at least one of expected_runtime_seconds / sanity_checks / expected_cost / factual_echo / runtime_integrity is required"))

    if _has_reproducibility_anchor(manifest):
        checks.append(_check_pass("reproducibility_anchor_declared"))
    else:
        checks.append(_check_fail(
            "reproducibility_anchor_declared",
            "no reproducibility anchor declared — add upstream_refs with a commit/revision/version, "
            "versioned runtime dependencies, or runtime.llm model identity",
        ))

    repro_errors = _reproducibility_check_errors(manifest, skill_dir)
    if repro_errors:
        checks.append(_check_fail(
            "reproducibility_check_declared",
            "; ".join(repro_errors),
        ))
    else:
        checks.append(_check_pass("reproducibility_check_declared"))

    conflicts = _env_pin_exact_pin_conflicts(manifest)
    if conflicts:
        checks.append(_check_fail(
            "env_pin_matches_exact_runtime_pins",
            "; ".join(conflicts),
        ))
    else:
        checks.append(_check_pass("env_pin_matches_exact_runtime_pins"))

    checks.extend(_paired_verifier_checks(manifest))

    fixtures_dir = skill_dir / "fixtures"
    fixture_items = [p for p in fixtures_dir.iterdir() if not p.name.startswith(".")] if fixtures_dir.is_dir() else []
    if fixture_items:
        checks.append(_check_pass("at_least_one_fixture"))
    else:
        checks.append(_check_fail("at_least_one_fixture",
                                  "no fixtures under fixtures/ — add at least one synthetic or public sample",
                                  severity="advisory"))

    if isinstance(side_effects, dict):
        declared_pkgs = {_norm_pkg(s) for s in (side_effects.get("pip_packages") or [])}
        actual_imports = _scan_imports(skill_dir / "scripts", skill_dir)
        external_modules = _external_asset_module_names(manifest)
        third_party = {
            imp for imp in actual_imports
            if imp not in STDLIB_MODULES and imp not in external_modules
        }
        actual_pkgs = {IMPORT_TO_PIP.get(imp, imp.lower()) for imp in third_party}
        # safetensors is a separate package; numpy often comes via monai/torch but
        # callers should still declare it. We do not whitelist transitives.
        missing = actual_pkgs - declared_pkgs
        if missing:
            checks.append(_check_fail("pip_imports_declared_in_side_effects",
                                      f"imports {sorted(missing)} appear in scripts/ but are not in runtime.side_effects.pip_packages",
                                      severity="advisory"))
        else:
            checks.append(_check_pass("pip_imports_declared_in_side_effects"))

    sanity_checks = validation.get("sanity_checks") or []
    if sanity_checks:
        nontrivial = 0
        for sc in sanity_checks:
            if not isinstance(sc, dict):
                continue
            ops = set(sc.keys()) - {"path"}
            if ops - {"exists"}:
                nontrivial += 1
        if nontrivial > 0:
            checks.append(_check_pass("sanity_checks_not_all_trivial"))
        else:
            checks.append(_check_fail("sanity_checks_not_all_trivial",
                                      "every sanity_check uses only 'exists' — consider gt/eq/matches/length_gte for tighter specs",
                                      severity="advisory"))

    # ---- Anthropic Agent Skills authoring best-practices (Tier 2 advisory) ----
    skill_md_path = skill_dir / "SKILL.md"
    if skill_md_path.exists():
        text = skill_md_path.read_text()
        ok, _err, fm, body = _parse_frontmatter(text)
        name = (fm.get("name") if (ok and fm) else "") or ""
        description = (fm.get("description") if (ok and fm) else "") or ""

        # Vague-name blocklist.
        if name:
            if name.lower() in VAGUE_NAME_BLOCKLIST:
                checks.append(_check_fail("frontmatter_name_not_vague",
                                          f"name {name!r} is on Anthropic's vague-name blocklist {sorted(VAGUE_NAME_BLOCKLIST)}",
                                          severity="advisory"))
            else:
                checks.append(_check_pass("frontmatter_name_not_vague"))

        # Description third-person heuristic.
        if description:
            head = description[:60]
            offending = [phrase for phrase in THIRD_PERSON_RED_FLAGS
                         if phrase in head]
            if offending:
                checks.append(_check_fail("frontmatter_description_third_person",
                                          f"description appears to use first/second person near the start (matched {offending[0]!r}); Anthropic requires third person",
                                          severity="advisory"))
            else:
                checks.append(_check_pass("frontmatter_description_third_person"))

        # SKILL.md body line count.
        body_lines = body.count("\n") if body else 0
        if body_lines <= SKILL_MD_BODY_MAX_LINES:
            checks.append(_check_pass("skill_md_body_length"))
        else:
            checks.append(_check_fail("skill_md_body_length",
                                      f"SKILL.md body has {body_lines} lines; Anthropic recommends ≤ {SKILL_MD_BODY_MAX_LINES} (split into reference files)",
                                      severity="advisory"))

        # Medical AI Skills agent-usability structure. These checks are advisory so
        # legacy verifiers can still pass deterministic gates, but user-facing
        # skills should keep them clean.
        missing_sections = [
            section
            for section in REQUIRED_SKILL_MD_SECTIONS
            if f"## {section}" not in body
        ]
        if missing_sections:
            checks.append(_check_fail(
                "skill_md_agent_usability_sections",
                "SKILL.md is missing agent-usability sections: "
                + ", ".join(missing_sections),
                severity="advisory",
            ))
        else:
            checks.append(_check_pass("skill_md_agent_usability_sections"))

        if AVAILABLE_SCRIPTS_HEADER in body:
            checks.append(_check_pass("skill_md_available_scripts_table"))
        else:
            checks.append(_check_fail(
                "skill_md_available_scripts_table",
                "SKILL.md should include an Available Scripts table with "
                "`| Script | Purpose | Arguments |` so agents can find the "
                "runnable surface without trial and error",
                severity="advisory",
            ))

        entrypoint = runtime.get("entrypoint") if isinstance(runtime, dict) else None
        available_script_rows = _available_script_rows(body)
        available_script_paths = [row["path"] for row in available_script_rows]
        if available_script_paths:
            missing_scripts: list[str] = []
            escaping_scripts: list[str] = []
            for rel in available_script_paths:
                script_path = skill_dir / rel
                if not _path_stays_under(skill_dir, script_path):
                    escaping_scripts.append(rel)
                elif not script_path.is_file():
                    missing_scripts.append(rel)
            if missing_scripts or escaping_scripts:
                details = []
                if missing_scripts:
                    details.append(f"missing files: {missing_scripts[:3]}")
                if escaping_scripts:
                    details.append(f"paths outside skill dir: {escaping_scripts[:3]}")
                checks.append(_check_fail(
                    "skill_md_available_scripts_resolve",
                    "; ".join(details),
                    severity="advisory",
                ))
            else:
                checks.append(_check_pass("skill_md_available_scripts_resolve"))
        else:
            checks.append(_check_fail(
                "skill_md_available_scripts_resolve",
                "Available Scripts table should list backtick-wrapped committed script paths",
                severity="advisory",
            ))

        vague_argument_rows = _vague_available_script_arguments(available_script_rows)
        if available_script_rows and not vague_argument_rows:
            checks.append(_check_pass("skill_md_available_scripts_arguments_specific"))
        else:
            if vague_argument_rows:
                msg = (
                    "Available Scripts Arguments cells should show concrete invocation "
                    "sketches instead of pointing elsewhere; vague rows: "
                    f"{vague_argument_rows[:5]}"
                )
            else:
                msg = (
                    "Available Scripts table should provide concrete argument sketches "
                    "for each listed script"
                )
            checks.append(_check_fail(
                "skill_md_available_scripts_arguments_specific",
                msg,
                severity="advisory",
            ))

        if entrypoint:
            entrypoint_text = str(entrypoint)
            entrypoint_name = Path(entrypoint_text).name
            if entrypoint_text in available_script_paths:
                checks.append(_check_pass("skill_md_available_scripts_include_entrypoint"))
            else:
                checks.append(_check_fail(
                    "skill_md_available_scripts_include_entrypoint",
                    f"Available Scripts table does not list runtime.entrypoint {entrypoint_text!r}",
                    severity="advisory",
                ))
            if entrypoint_text in body or entrypoint_name in body:
                checks.append(_check_pass("skill_md_mentions_runtime_entrypoint"))
            else:
                checks.append(_check_fail(
                    "skill_md_mentions_runtime_entrypoint",
                    f"SKILL.md does not mention runtime.entrypoint {entrypoint_text!r}; "
                    "agents need the exact wrapper path",
                    severity="advisory",
                ))

            literal_args = _runtime_literal_args(runtime) if isinstance(runtime, dict) else []
            entrypoint_row = _entrypoint_available_script_row(available_script_rows, entrypoint_text)
            if literal_args and entrypoint_row is not None:
                entrypoint_args = entrypoint_row.get("arguments", "")
                missing_from_row = [arg for arg in literal_args if arg not in entrypoint_args]
                if missing_from_row:
                    checks.append(_check_fail(
                        "skill_md_available_entrypoint_arguments_match_runtime",
                        "Available Scripts row for runtime.entrypoint omits literal "
                        f"runtime.args tokens: {missing_from_row[:5]}",
                        severity="advisory",
                    ))
                else:
                    checks.append(_check_pass("skill_md_available_entrypoint_arguments_match_runtime"))
            elif literal_args:
                checks.append(_check_fail(
                    "skill_md_available_entrypoint_arguments_match_runtime",
                    "Available Scripts table does not expose runtime.entrypoint "
                    "arguments, so agents must infer manifest literal runtime.args",
                    severity="advisory",
                ))
            else:
                checks.append(_check_pass("skill_md_available_entrypoint_arguments_match_runtime"))

        if "run_script(" in body or re.search(r"\bpython(?:3)?\s+[\w./-]+", body):
            checks.append(_check_pass("skill_md_has_concrete_invocation"))
        else:
            checks.append(_check_fail(
                "skill_md_has_concrete_invocation",
                "SKILL.md should include `run_script(...)` or a concrete "
                "`python ...` invocation",
                severity="advisory",
            ))

        if entrypoint:
            entrypoint_text = str(entrypoint)
            entrypoint_name = Path(entrypoint_text).name
            run_script_re = re.compile(
                r"run_script\(\s*['\"]" + re.escape(entrypoint_text) + r"['\"]"
            )
            python_entrypoint_re = re.compile(
                r"\bpython(?:3)?\s+(?:[\w./-]+/)?" + re.escape(entrypoint_name) + r"\b"
            )
            if run_script_re.search(body) or python_entrypoint_re.search(body):
                checks.append(_check_pass("skill_md_invocation_uses_entrypoint"))
            else:
                checks.append(_check_fail(
                    "skill_md_invocation_uses_entrypoint",
                    f"SKILL.md has an invocation hint, but not one that clearly calls {entrypoint_text!r}",
                    severity="advisory",
                ))

        if isinstance(runtime, dict):
            literal_args = _runtime_literal_args(runtime)
            missing_args = [arg for arg in literal_args if arg not in body]
            if missing_args:
                checks.append(_check_fail(
                    "skill_md_mentions_runtime_literal_args",
                    f"SKILL.md omits literal runtime.args tokens: {missing_args[:5]}",
                    severity="advisory",
                ))
            else:
                checks.append(_check_pass("skill_md_mentions_runtime_literal_args"))

            env_required = _runtime_env_required(runtime)
            missing_env = [env for env in env_required if env not in body]
            if missing_env:
                checks.append(_check_fail(
                    "skill_md_mentions_runtime_env_required",
                    f"SKILL.md omits runtime.env_required variables: {missing_env[:5]}",
                    severity="advisory",
                ))
            else:
                checks.append(_check_pass("skill_md_mentions_runtime_env_required"))

            env_optional = _runtime_env_optional(runtime)
            missing_optional_env = [env for env in env_optional if env not in body]
            if missing_optional_env:
                checks.append(_check_fail(
                    "skill_md_mentions_runtime_env_optional",
                    f"SKILL.md omits runtime.env_optional variables: {missing_optional_env[:5]}",
                    severity="advisory",
                ))
            else:
                checks.append(_check_pass("skill_md_mentions_runtime_env_optional"))

            env_conditional = _runtime_env_conditional(runtime)
            missing_conditional_env = [env for env in env_conditional if env not in body]
            if missing_conditional_env:
                checks.append(_check_fail(
                    "skill_md_mentions_runtime_env_conditional",
                    f"SKILL.md omits runtime.env_conditional variables: {missing_conditional_env[:5]}",
                    severity="advisory",
                ))
            else:
                checks.append(_check_pass("skill_md_mentions_runtime_env_conditional"))

            runtime_side_effects = runtime.get("side_effects") or {}
            missing_side_effects: list[str] = []
            if isinstance(runtime_side_effects, dict):
                for key in ("local_writes", "home_writes", "network_endpoints"):
                    for token in _side_effect_value_tokens(runtime_side_effects.get(key)):
                        candidates = _side_effect_doc_candidates(key, token)
                        if not any(candidate and candidate in body for candidate in candidates):
                            missing_side_effects.append(f"{key}:{token}")
                if runtime_side_effects.get("requires_docker") is True:
                    if "Docker" not in body and "docker" not in body:
                        missing_side_effects.append("requires_docker:true")
                requires_gpu = str(runtime_side_effects.get("requires_gpu") or "none").lower()
                if requires_gpu not in {"", "false", "no", "none"}:
                    if not any(marker in body for marker in ("GPU", "gpu", "CUDA", "cuda")):
                        missing_side_effects.append(f"requires_gpu:{requires_gpu}")
            if missing_side_effects:
                checks.append(_check_fail(
                    "skill_md_mentions_runtime_side_effects",
                    "SKILL.md omits declared runtime.side_effects details: "
                    f"{missing_side_effects[:8]}",
                    severity="advisory",
                ))
            else:
                checks.append(_check_pass("skill_md_mentions_runtime_side_effects"))

        missing_io = _manifest_io_mentions_missing(manifest, body)
        if missing_io:
            checks.append(_check_fail(
                "skill_md_mentions_manifest_io",
                "SKILL.md omits manifest-declared input/output hints: "
                f"{missing_io[:8]}",
                severity="advisory",
            ))
        else:
            checks.append(_check_pass("skill_md_mentions_manifest_io"))

        # Forward-slash paths in markdown links + reference existence + ref depth.
        link_targets: list[tuple[str, str]] = []
        for m in MARKDOWN_LINK_RE.finditer(body):
            label, target = m.group(1), m.group(2)
            link_targets.append((label, target))

        # Filter to relative-link targets that look like files in the skill dir
        # (skip http://..., #anchors, mailto:..., etc.).
        def _is_local(target: str) -> bool:
            if not target:
                return False
            if target.startswith(("http://", "https://", "mailto:", "#")):
                return False
            return True

        local_targets = [
            (label, target)
            for (label, target) in link_targets
            if _is_local(target)
        ]

        # Forward-slash check.
        backslash_targets = [t for (_l, t) in local_targets if "\\" in t]
        if backslash_targets:
            checks.append(_check_fail("skill_md_paths_forward_slash",
                                      f"markdown links use Windows-style backslashes: {backslash_targets[:3]}; Anthropic requires forward slashes",
                                      severity="advisory"))
        else:
            checks.append(_check_pass("skill_md_paths_forward_slash"))

        # Reference resolution check.
        broken = []
        for (_l, t) in local_targets:
            target_path = t.split("#", 1)[0]
            if not target_path:
                continue
            resolved = (skill_dir / target_path).resolve()
            if not resolved.exists():
                broken.append(target_path)
        if broken:
            checks.append(_check_fail("skill_md_references_resolve",
                                      f"markdown links to nonexistent paths: {broken[:3]}",
                                      severity="advisory"))
        else:
            checks.append(_check_pass("skill_md_references_resolve"))

        # Reference depth check — files referenced from SKILL.md should not
        # themselves contain relative-path links to further files (one level
        # deep per Anthropic).
        nested_chains: list[str] = []
        for (_l, t) in local_targets:
            target_path = t.split("#", 1)[0]
            resolved = (skill_dir / target_path).resolve()
            if not resolved.is_file() or resolved.suffix.lower() not in (".md", ".markdown"):
                continue
            try:
                inner = resolved.read_text()
            except Exception:
                continue
            for m in MARKDOWN_LINK_RE.finditer(inner):
                inner_target = m.group(2)
                if not _is_local(inner_target):
                    continue
                # Allow self / parent references that don't go deeper.
                inner_path = inner_target.split("#", 1)[0]
                if not inner_path or inner_path.startswith(".."):
                    continue
                nested_chains.append(f"{target_path} -> {inner_path}")
                break
        if nested_chains:
            checks.append(_check_fail("skill_md_references_one_level_deep",
                                      f"reference chain >1 level deep (Anthropic prefers SKILL.md → leaf): {nested_chains[:2]}",
                                      severity="advisory"))
        else:
            checks.append(_check_pass("skill_md_references_one_level_deep"))

    return checks


def _summarise(tier_id: str, checks: list[dict]) -> dict:
    blocking = [c for c in checks if not c.get("pass") and c.get("severity", "block") == "block"]
    advisory = [c for c in checks if not c.get("pass") and c.get("severity") == "advisory"]
    passed = sum(1 for c in checks if c.get("pass"))
    return {
        "tier_id": tier_id,
        "checks_passed": passed,
        "checks_total": len(checks),
        "verdict": "fail" if blocking else ("pass" if checks else "skipped"),
        "blocking_issues": blocking,
        "advisory_issues": advisory,
    }


def _load_manifest(skill_dir: Path) -> dict:
    try:
        manifest = yaml.safe_load((skill_dir / "skill_manifest.yaml").read_text()) or {}
    except Exception:
        return {}
    return manifest if isinstance(manifest, dict) else {}


def _rel_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def _has_blocking_issues(summary: dict) -> bool:
    return bool(summary.get("blocking_issues"))


def _implemented_verifier_dirs(manifest: dict) -> list[Path]:
    dirs: list[Path] = []
    for item in manifest.get("paired_verifiers") or []:
        if not isinstance(item, dict) or item.get("status") != "implemented":
            continue
        verifier_id = str(item.get("id") or "")
        if not verifier_id:
            continue
        short_name = verifier_id.rsplit(".", 1)[-1].rsplit("/", 1)[-1]
        candidate = VERIFIERS_ROOT / short_name
        if (candidate / "skill_manifest.yaml").exists():
            dirs.append(candidate)
    return dirs


def _planned_verifier_ids(manifest: dict) -> list[str]:
    planned: list[str] = []
    for item in manifest.get("paired_verifiers") or []:
        if isinstance(item, dict) and item.get("status") == "planned":
            planned.append(str(item.get("id") or "<missing-id>"))
    return planned


def _is_verifier_target(skill_dir: Path) -> bool:
    try:
        rel = skill_dir.resolve().relative_to(VERIFIERS_ROOT.resolve())
    except ValueError:
        return False
    return bool(rel.parts) and rel.parts[0] != "_shared"


def _curated_evidence_packs(skill_id: str) -> list[str]:
    if not skill_id:
        return []
    roots = (REPO_ROOT / "examples" / "evidence_packs", REPO_ROOT / "examples" / "studies")
    packs: list[str] = []
    for root in roots:
        if not root.is_dir():
            continue
        for manifest_path in sorted(root.rglob("manifest.json")):
            try:
                payload = json.loads(manifest_path.read_text())
            except Exception:
                continue
            if payload.get("skill_id") == skill_id:
                packs.append(_rel_path(manifest_path.parent))
    return packs


def _curated_passing_evidence_packs(skill_id: str) -> list[str]:
    if not skill_id:
        return []
    roots = (REPO_ROOT / "examples" / "evidence_packs", REPO_ROOT / "examples" / "studies")
    packs: list[str] = []
    for root in roots:
        if not root.is_dir():
            continue
        for manifest_path in sorted(root.rglob("manifest.json")):
            try:
                manifest_payload = json.loads(manifest_path.read_text())
            except Exception:
                continue
            if manifest_payload.get("skill_id") != skill_id:
                continue
            validation_path = manifest_path.parent / "validation_summary.json"
            try:
                validation_payload = json.loads(validation_path.read_text())
            except Exception:
                continue
            if validation_payload.get("overall_status") == "passed":
                packs.append(_rel_path(manifest_path.parent))
    return packs


def _curated_trusted_runs(skill_id: str) -> list[str]:
    if not skill_id:
        return []
    roots = (REPO_ROOT / "examples" / "evidence_packs", REPO_ROOT / "examples" / "studies")
    summaries: list[str] = []
    for root in roots:
        if not root.is_dir():
            continue
        for summary_path in sorted(root.rglob("trust_summary.json")):
            try:
                payload = json.loads(summary_path.read_text())
            except Exception:
                continue
            if payload.get("skill_id") != skill_id:
                continue
            if payload.get("overall") not in {"passed", "warn"}:
                continue
            if payload.get("planned_verifier_gaps") or payload.get("env_skipped_verifier_gaps"):
                continue
            summaries.append(_rel_path(summary_path.parent))
    return summaries


def _lifecycle_step(status: str, met: bool, *, evidence: list[str] | None = None,
                    gaps: list[str] | None = None) -> dict:
    return {
        "status": status,
        "met": met,
        "evidence": evidence or [],
        "gaps": gaps or [],
    }


def derive_capability_lifecycle(skill_dir: Path, tier1_summary: dict, tier2_summary: dict) -> dict:
    """Derive the lightweight lifecycle status without adding manifest state."""
    manifest = _load_manifest(skill_dir)
    skill_id = str(manifest.get("id") or "")
    is_verifier = _is_verifier_target(skill_dir)
    has_benchmark_note = (skill_dir / "BENCHMARK.md").is_file()
    has_evals = (skill_dir / "evals" / "evals.json").is_file()
    implemented_verifiers = [_rel_path(path) for path in _implemented_verifier_dirs(manifest)]
    planned_verifiers = _planned_verifier_ids(manifest)
    curated_packs = _curated_evidence_packs(skill_id)
    curated_passing_packs = _curated_passing_evidence_packs(skill_id)
    trusted_runs = _curated_trusted_runs(skill_id)

    runnable_gaps: list[str] = []
    if _has_blocking_issues(tier1_summary):
        runnable_gaps.append("tier1_structural has blocking issues")

    gated_gaps: list[str] = []
    if _has_blocking_issues(tier1_summary) or _has_blocking_issues(tier2_summary):
        gated_gaps.append("tier1_structural or tier2_spec_honesty has blocking issues")

    verified_gaps: list[str] = []
    if gated_gaps:
        verified_gaps.append("gated lifecycle step is not met")
    if is_verifier:
        if not curated_passing_packs:
            verified_gaps.append("no curated verifier evidence pack found with passing validation")
    else:
        if planned_verifiers:
            verified_gaps.append("planned paired verifiers remain: " + ", ".join(planned_verifiers))
        if not implemented_verifiers:
            verified_gaps.append("no implemented paired_verifiers[] entries resolve to committed verifiers")
        if not trusted_runs:
            verified_gaps.append("no curated trusted-run summary found with passing verifier evidence")

    published_gaps: list[str] = []
    if not is_verifier and not has_evals:
        published_gaps.append("missing evals/evals.json")
    if not is_verifier and not has_benchmark_note:
        published_gaps.append("missing BENCHMARK.md")
    if not curated_packs:
        published_gaps.append("no curated example evidence pack found for manifest id")

    runnable_met = not runnable_gaps
    gated_met = runnable_met and not gated_gaps
    verified_met = gated_met and not verified_gaps
    if not verified_met:
        published_gaps.insert(0, "verified lifecycle step is not met")
    published_met = verified_met and not published_gaps

    steps = [
        _lifecycle_step("draft", True, evidence=["base state for any skill-shaped directory"]),
        _lifecycle_step(
            "runnable",
            runnable_met,
            evidence=["tier1_structural has no blocking issues"] if runnable_met else [],
            gaps=runnable_gaps,
        ),
        _lifecycle_step(
            "gated",
            gated_met,
            evidence=[
                "tier1_structural has no blocking issues",
                "tier2_spec_honesty has no blocking issues",
            ] if gated_met else [],
            gaps=gated_gaps,
        ),
        _lifecycle_step(
            "verified",
            verified_met,
            evidence=(
                curated_passing_packs
                if is_verifier
                else implemented_verifiers + trusted_runs
            ),
            gaps=verified_gaps,
        ),
        _lifecycle_step(
            "published",
            published_met,
            evidence=(
                (["evals/evals.json"] if has_evals else [])
                + (["BENCHMARK.md"] if has_benchmark_note else [])
                + curated_packs
            ),
            gaps=published_gaps,
        ),
    ]
    status = "draft"
    for step in steps:
        if step["met"]:
            status = step["status"]
        else:
            break
    return {
        "status": status,
        "order": list(LIFECYCLE_ORDER),
        "source": (
            "derived from skill_completeness_v1 checks; verifier targets use "
            "curated passing verifier evidence instead of paired_verifiers[]"
        ),
        "target_type": "verifier" if is_verifier else "capability",
        "requirements": steps,
    }


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: grade.py <target_skill_dir>"}, indent=2))
        sys.exit(2)
    skill_dir = Path(sys.argv[1]).resolve()
    if not skill_dir.is_dir():
        print(json.dumps({"error": f"not a directory: {skill_dir}"}, indent=2))
        sys.exit(2)

    tier1 = grade_tier1(skill_dir)
    tier2 = grade_tier2(skill_dir)
    tier1_summary = _summarise("tier1_structural", tier1)
    tier2_summary = _summarise("tier2_spec_honesty", tier2)
    tier3_summary = grade_tier3_llm(skill_dir)

    overall_blocking = (len(tier1_summary["blocking_issues"])
                        + len(tier2_summary["blocking_issues"])
                        + len(tier3_summary.get("blocking_issues", [])))
    overall_advisory = (len(tier1_summary["advisory_issues"])
                        + len(tier2_summary["advisory_issues"])
                        + len(tier3_summary.get("advisory_issues", [])))
    overall = "pass" if overall_blocking == 0 else "fail"

    result = {
        "skill": "skill_completeness_v1",
        "verifier_version": VERIFIER_VERSION,
        "target_skill": str(skill_dir),
        "tier1_structural": tier1_summary,
        "tier2_spec_honesty": tier2_summary,
        "tier3_documentation": tier3_summary,
        "tier4_tests": {
            "tier_id": "tier4_tests",
            "verdict": "skipped",
            "reason": "v0.3 -- requires test execution + coverage assessment",
        },
        "capability_lifecycle": derive_capability_lifecycle(
            skill_dir,
            tier1_summary,
            tier2_summary,
        ),
        "overall": overall,
        "blocking_issues_count": overall_blocking,
        "advisory_issues_count": overall_advisory,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
