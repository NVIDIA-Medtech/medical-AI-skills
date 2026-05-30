#!/usr/bin/env python3
"""Mechanical doc + structure lints for Medical AI Skills.

Codex-style "doc gardening" — a small set of rules that keep this repo
agent-legible. Run as `python3 -m eval_engine.lint_repo` or `make lint`.

Each rule emits one or more findings. The script exits 1 if any finding
is severity=error. Warnings are listed but do not fail the run.

Rules implemented:

  E1  AGENTS.md (root + per-subsystem) must exist and be <= MAX_AGENTS_LINES.
  E2  ARCHITECTURE.md must exist and be <= MAX_ARCHITECTURE_LINES.
  E3  Every spec directory must contain SKILL.md and skill_manifest.yaml.
  E4  Skill and verifier scripts must not `import eval_engine` or `from eval_engine`.
  E5  Skill manifests must declare runtime.entrypoint and that file must exist.
  E6  Skill manifests must validate against spec/skill_manifest.schema.json.
  E7  Implemented paired_verifiers must resolve to committed verifier manifests.
  E8  Top-level outputs/ must not exist; generated artifacts belong under runs/.
  E9  Top-level fixtures/ must not exist; benchmark manifests belong under benchmarks/.
  E10 Tracked medical/media artifacts must not enter the public tree.
  E11 Public files must not contain local user-home absolute paths.
  E12 Skill manifests must not declare validation keys unknown to gate_registry.
  E13 Large public files must not enter the public tree.
  E14 Skill manifests must declare at least one upstream_refs entry with a
      version constraint, exact version, model/repo revision, or git commit.
  E15 Exact runtime package pins must satisfy matching validation.env_pin
      constraints.
  E16 Generated record surfaces must stay under ignored local output paths.
  W1  Manifests with `outputs:[]` should declare at least one schema for json outputs.
  W2  README.md should reference every skill subdirectory at least once.
  W3  Skill scripts should not patch upstream implementation files at runtime.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from eval_engine.gate_registry import unknown_validation_keys  # noqa: E402
from eval_engine.manifest import (  # noqa: E402
    iter_spec_dirs,
    load_manifest,
    paired_verifier_resolution_errors,
    resolve_entrypoint,
    validate_manifest_schema,
)

MAX_AGENTS_LINES = 120
MAX_ARCHITECTURE_LINES = 150
MAX_TEXT_SCAN_BYTES = 2 * 1024 * 1024
MAX_PUBLIC_FILE_BYTES = 50 * 1024 * 1024

IMPORT_HARNESS_RE = re.compile(
    r"^\s*(?:from\s+eval_engine|import\s+eval_engine)\b", re.M
)
LOCAL_HOME_PATH_RE = re.compile("/" + r"(?:home|Users)/[A-Za-z0-9._-]+")
RUNTIME_UPSTREAM_PATCH_RE = re.compile(
    r"\b(?:"
    r"runtime[_ -]?patch(?:es|ing)?|"
    r"apply[_ -]?runtime[_ -]?patch(?:es)?|"
    r"monkeypatch|"
    r"sitecustomize|"
    r"patch(?:es|ed|ing)?\s+(?:the\s+)?upstream|"
    r"rewrite(?:s|n|ing)?\s+(?:the\s+)?upstream"
    r")\b",
    re.I,
)
BLOCKED_ARTIFACT_SUFFIXES = (
    ".dcm",
    ".nii",
    ".nii.gz",
    ".mp4",
    ".gxf_entities",
    ".gxf_index",
)
TRACKED_STUB_ALLOWLIST = {
    "verifiers/ct_segmentation_quality_v1/fixtures/pass_pack/predicted_seg.nii.gz",
    "verifiers/ct_segmentation_quality_v1/fixtures/fragmented_pack/predicted_seg.nii.gz",
    "verifiers/ct_segmentation_quality_v1/fixtures/gt_pass_pack/predicted_seg.nii.gz",
    "verifiers/ct_segmentation_quality_v1/fixtures/gt_pass_pack/reference_seg.nii.gz",
}
GENERATED_RECORD_RE = re.compile(
    r"^(?:"
    r"runs/|"
    r"docs/with-vs-without-nv-[^/]+\.md$|"
    r"examples/studies/with_vs_without_skill/|"
    r"examples/studies/.*/(?:with_skill_artifacts|without_skill_artifacts)/"
    r")"
)


def _line_count(path: Path) -> int:
    try:
        return len(path.read_text().splitlines())
    except Exception:
        return -1


def _all_agents_md() -> list[Path]:
    return sorted(
        [
            p
            for p in REPO_ROOT.rglob("AGENTS.md")
            if "/.git/" not in str(p) and "/discussions/" not in str(p)
        ]
    )


def _all_spec_dirs() -> list[Path]:
    return iter_spec_dirs()


def _git_public_files() -> list[str]:
    """Committed plus untracked non-ignored files, as repo-relative POSIX paths."""
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-co", "--exclude-standard"],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except Exception:
        return []
    return sorted({line.strip() for line in proc.stdout.splitlines() if line.strip()})


def _is_generated_record_path(rel_path: str) -> bool:
    return bool(GENERATED_RECORD_RE.search(rel_path))


def _has_blocked_artifact_suffix(path: str) -> bool:
    return any(path.endswith(suffix) for suffix in BLOCKED_ARTIFACT_SUFFIXES)


def _has_tracked_upstream_ref(manifest: dict) -> bool:
    refs = manifest.get("upstream_refs")
    if not isinstance(refs, list) or not refs:
        return False
    version_keys = ("git_commit", "revision", "version", "version_constraint")
    return all(
        isinstance(ref, dict) and any(ref.get(key) for key in version_keys)
        for ref in refs
    )


def _pkg_name_from_spec(spec: str) -> str | None:
    match = re.match(r"^\s*([A-Za-z0-9_.-]+)", str(spec))
    if not match:
        return None
    name = match.group(1)
    if name.startswith(("<", ">", "=", "!", "~")):
        return None
    return name.lower().replace("_", "-")


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


def _mentions_runtime_upstream_patch(src: str) -> bool:
    return bool(RUNTIME_UPSTREAM_PATCH_RE.search(src))


def lint() -> tuple[list[dict], list[dict]]:
    errors: list[dict] = []
    warnings: list[dict] = []
    public_files = _git_public_files()
    spec_dirs = _all_spec_dirs()

    # E1
    for p in _all_agents_md():
        n = _line_count(p)
        if n < 0:
            errors.append(
                {
                    "rule": "E1",
                    "path": str(p.relative_to(REPO_ROOT)),
                    "msg": "AGENTS.md unreadable",
                }
            )
            continue
        if n > MAX_AGENTS_LINES:
            errors.append(
                {
                    "rule": "E1",
                    "path": str(p.relative_to(REPO_ROOT)),
                    "msg": f"AGENTS.md is {n} lines, max is {MAX_AGENTS_LINES}. "
                    "Split content into ARCHITECTURE.md or per-subsystem AGENTS.md.",
                }
            )

    # E2
    arch = REPO_ROOT / "ARCHITECTURE.md"
    if not arch.exists():
        errors.append({"rule": "E2", "path": "ARCHITECTURE.md", "msg": "missing"})
    else:
        n = _line_count(arch)
        if n > MAX_ARCHITECTURE_LINES:
            errors.append(
                {
                    "rule": "E2",
                    "path": "ARCHITECTURE.md",
                    "msg": f"ARCHITECTURE.md is {n} lines, max is {MAX_ARCHITECTURE_LINES}.",
                }
            )

    # E8
    if (REPO_ROOT / "outputs").exists():
        errors.append(
            {
                "rule": "E8",
                "path": "outputs/",
                "msg": "top-level outputs/ is obsolete; write generated artifacts under runs/",
            }
        )

    # E9
    if (REPO_ROOT / "fixtures").exists():
        errors.append(
            {
                "rule": "E9",
                "path": "fixtures/",
                "msg": "top-level fixtures/ is obsolete; benchmark manifests belong under benchmarks/",
            }
        )

    # E10 + E11 + E13 + E16 (single pass over the public file list)
    for rel_path in public_files:
        path = REPO_ROOT / rel_path
        if _is_generated_record_path(rel_path):
            errors.append(
                {
                    "rule": "E16",
                    "path": rel_path,
                    "msg": (
                        "generated records must stay under ignored local output "
                        "paths; commit only compact summaries or curated packs"
                    ),
                }
            )
        if (
            rel_path not in TRACKED_STUB_ALLOWLIST
            and _has_blocked_artifact_suffix(rel_path)
            and path.exists()
        ):
            errors.append(
                {
                    "rule": "E10",
                    "path": rel_path,
                    "msg": "medical/media artifacts must stay local; commit a manifest, schema, or tiny text stub instead",
                }
            )
        if not path.is_file():
            continue
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        if rel_path not in TRACKED_STUB_ALLOWLIST and size > MAX_PUBLIC_FILE_BYTES:
            errors.append(
                {
                    "rule": "E13",
                    "path": rel_path,
                    "msg": (
                        f"public file is {size / (1024 * 1024):.1f} MiB; "
                        "large generated artifacts must stay under ignored runs/ "
                        "or another ignored local work directory"
                    ),
                }
            )
        if size > MAX_TEXT_SCAN_BYTES:
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        if LOCAL_HOME_PATH_RE.search(text):
            errors.append(
                {
                    "rule": "E11",
                    "path": rel_path,
                    "msg": "local user-home absolute path found; use repo-relative paths or env/config placeholders",
                }
            )

    # E3 + E4 + E5
    for spec_dir in spec_dirs:
        rel = str(spec_dir.relative_to(REPO_ROOT))
        skill_md = spec_dir / "SKILL.md"
        manifest_path = spec_dir / "skill_manifest.yaml"
        if not skill_md.exists():
            errors.append({"rule": "E3", "path": rel, "msg": "missing SKILL.md"})
        if not manifest_path.exists():
            errors.append(
                {"rule": "E3", "path": rel, "msg": "missing skill_manifest.yaml"}
            )
            continue

        try:
            manifest = load_manifest(manifest_path)
        except ValueError as e:
            errors.append({"rule": "E6", "path": rel, "msg": str(e)})
            continue

        # E5
        try:
            entry_path = resolve_entrypoint(spec_dir, manifest)
        except ValueError as e:
            errors.append({"rule": "E5", "path": rel, "msg": str(e)})
        else:
            if not entry_path.exists():
                entry = (manifest.get("runtime", {}) or {}).get("entrypoint")
                errors.append(
                    {
                        "rule": "E5",
                        "path": rel,
                        "msg": f"runtime.entrypoint {entry!r} does not exist",
                    }
                )

        # E6
        for msg in validate_manifest_schema(manifest):
            errors.append({"rule": "E6", "path": rel, "msg": msg})

        # E7
        for msg in paired_verifier_resolution_errors(manifest):
            errors.append({"rule": "E7", "path": rel, "msg": msg})

        # E12 — only applies to skill dirs (verifiers don't carry validation gates).
        if spec_dir.is_relative_to(REPO_ROOT / "skills"):
            unknown = unknown_validation_keys(manifest)
            if unknown:
                errors.append(
                    {
                        "rule": "E12",
                        "path": rel,
                        "msg": (
                            f"skill {spec_dir.name!r} declares unknown validation key(s): "
                            f"{', '.join(unknown)}. Either register them in "
                            "gate_registry.VALIDATION_GATE_KEYS or remove from manifest."
                        ),
                    }
                )
            if not _has_tracked_upstream_ref(manifest):
                errors.append(
                    {
                        "rule": "E14",
                        "path": rel,
                        "msg": (
                            "skill manifest must declare upstream_refs with "
                            "git_commit, revision, version, or version_constraint"
                        ),
                    }
                )
            conflicts = _env_pin_exact_pin_conflicts(manifest)
            if conflicts:
                errors.append(
                    {
                        "rule": "E15",
                        "path": rel,
                        "msg": "; ".join(conflicts),
                    }
                )

        # W1
        outputs = manifest.get("outputs", []) or []
        json_outputs = [
            o for o in outputs if isinstance(o, dict) and o.get("type") == "json"
        ]
        if json_outputs and not any(o.get("schema") for o in json_outputs):
            warnings.append(
                {
                    "rule": "W1",
                    "path": rel,
                    "msg": "manifest declares json output but no `schema` field",
                }
            )

        # E4 — specs must be portable subprocess targets; eval_engine drives them.
        scripts_dir = spec_dir / "scripts"
        if scripts_dir.is_dir():
            for py in scripts_dir.rglob("*.py"):
                try:
                    src = py.read_text()
                except Exception:
                    continue
                if IMPORT_HARNESS_RE.search(src):
                    errors.append(
                        {
                            "rule": "E4",
                            "path": str(py.relative_to(REPO_ROOT)),
                            "msg": "spec imports from `eval_engine` (skills and verifiers must be driven by, not import, the eval_engine)",
                        }
                    )
                if spec_dir.is_relative_to(
                    REPO_ROOT / "skills"
                ) and _mentions_runtime_upstream_patch(src):
                    warnings.append(
                        {
                            "rule": "W3",
                            "path": str(py.relative_to(REPO_ROOT)),
                            "msg": (
                                "script mentions runtime upstream patching; "
                                "normal skill runs should follow the upstream "
                                "README/requirements path and use config staging "
                                "plus reference baselines instead of modifying "
                                "upstream implementation files"
                            ),
                        }
                    )

    # W2
    readme = REPO_ROOT / "README.md"
    if readme.exists():
        text = readme.read_text()
        for spec_dir in spec_dirs:
            if spec_dir.name not in text:
                warnings.append(
                    {
                        "rule": "W2",
                        "path": str(spec_dir.relative_to(REPO_ROOT)),
                        "msg": "spec not referenced from README.md",
                    }
                )

    return errors, warnings


def _print(items: Iterable[dict], header: str) -> None:
    items = list(items)
    print(f"{header}: {len(items)}")
    for f in items:
        print(f"  [{f['rule']}] {f['path']}: {f['msg']}")


def main() -> int:
    errors, warnings = lint()
    _print(warnings, "warnings")
    _print(errors, "errors")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
