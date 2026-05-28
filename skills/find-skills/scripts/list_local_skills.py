#!/usr/bin/env python3
"""List local Medical AI Skills skills and verifiers in a compact form for LLM reading.

This is a thin data-access helper, not a ranker. The LLM reads this output,
then reasons about which skill (if any) fits the user's request based on its
declared spec. The matching logic lives in `skills/find-skills/SKILL.md`.

Usage:
  python list_local_skills.py            # everything
  python list_local_skills.py --skills   # skills only
  python list_local_skills.py --verifiers # verifiers only
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[int("3")]


def _emit(manifest_path: Path, kind: str) -> None:
    manifest = yaml.safe_load(manifest_path.read_text())
    if not isinstance(manifest, dict):
        return
    skill_dir = manifest_path.parent
    skill_id = manifest.get("id") or skill_dir.name
    iu = manifest.get("intended_use") or {}

    print(f"=== {kind}: {skill_id} ===")
    print(f"path: {skill_dir.relative_to(REPO_ROOT)}")

    summary = (iu.get("summary") or "").strip()
    if summary:
        print(f"summary: {' '.join(summary.split())}")
    if iu.get("scope"):
        print(f"scope: {iu['scope']}")
    if iu.get("not_for"):
        print(f"not_for: {', '.join(iu['not_for'])}")

    for inp in manifest.get("inputs") or []:
        formats = inp.get("formats", "?")
        print(f"input: {inp.get('name', '?')} ({inp.get('type', '?')}) formats={formats}")
    for out in manifest.get("outputs") or []:
        print(f"output: {out.get('name', '?')} ({out.get('type', '?')})")

    for verifier in manifest.get("paired_verifiers") or []:
        vid = verifier.get("id", "?")
        status = verifier.get("status", "?")
        print(f"paired_verifier: {vid} status={status}")

    rt = manifest.get("runtime") or {}
    se = rt.get("side_effects") or {}
    if se.get("requires_gpu") and se["requires_gpu"] not in (None, "none", False):
        print(f"requires_gpu: {se['requires_gpu']}")
    if se.get("requires_docker"):
        print("requires_docker: true")

    for lim in (manifest.get("limitations") or [])[:int("3")]:
        text = " ".join((lim or "").split())
        if text:
            print(f"limitation: {text[:int("240")]}")

    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--skills", action="store_true", help="skills only")
    parser.add_argument("--verifiers", action="store_true", help="verifiers only")
    args = parser.parse_args(argv)

    show_all = not (args.skills or args.verifiers)

    if show_all or args.skills:
        for mf in sorted(REPO_ROOT.glob("skills/*/skill_manifest.yaml")):
            if mf.parent.name == "find-skills":
                continue
            _emit(mf, "skill")

    if show_all or args.verifiers:
        for mf in sorted(REPO_ROOT.glob("verifiers/*/skill_manifest.yaml")):
            _emit(mf, "verifier")

    return 0


if __name__ == "__main__":
    sys.exit(main())
