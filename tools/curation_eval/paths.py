# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Filesystem locations used by the curation evaluation harness.

Everything is resolved relative to this file so the harness works regardless of
the caller's CWD, with environment-variable overrides for non-standard layouts.
"""

from __future__ import annotations

import os
from pathlib import Path

# tools/curation_eval/paths.py -> parents[2] == the medical-AI-skills catalog root.
SKILLS_ROOT = Path(__file__).resolve().parents[2]
# medical-AI-skills -> data_curation_skills_claude_v1 -> code -> <repo root>.
REPO_ROOT = SKILLS_ROOT.parents[2]


def _env_path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).expanduser().resolve() if value else default


# --- Source data (real MR-RATE corpus; read-only) --------------------------
DATA_REPORTS_DIR = _env_path(
    "CEVAL_REPORTS_DIR",
    REPO_ROOT / "data" / "MR-RATE" / "reports" / "reports",
)
LABELS_CSV = _env_path(
    "CEVAL_LABELS_CSV",
    REPO_ROOT / "data" / "MR-RATE" / "reports" / "pathology_lables" / "mrrate_labels.csv",
)

# --- Skills invoked by the with-skill arm ----------------------------------
ANON_SCRIPT = SKILLS_ROOT / "skills" / "report-anonymization" / "scripts" / "run_anonymization.py"
PATHOLOGY_SCRIPT = (
    SKILLS_ROOT
    / "skills"
    / "report-pathology-classification"
    / "scripts"
    / "run_report_pathology_classification.py"
)
PATHOLOGIES_JSON = (
    SKILLS_ROOT / "skills" / "report-pathology-classification" / "data" / "pathologies.json"
)

# --- Anonymization QC-loop step (step 2): skill vs upstream script ----------
# The loop needs openai+pandas (and a hosted/GLiNER QC backend); the system
# python lacks them, so both live arms run under this env by default.
ANON_VLLM_PYTHON = _env_path(
    "CEVAL_QCLOOP_PYTHON", Path("/home/marc/miniconda3/envs/anon-vllm/bin/python")
)
# WITH-skill entrypoint (its --mode live subprocesses the upstream below).
QC_LOOP_SKILL_SCRIPT = (
    SKILLS_ROOT / "skills" / "report-anonymization-qc-loop" / "scripts"
    / "run_anonymization_qc_loop.py"
)
QC_LOOP_FIXTURE = (
    SKILLS_ROOT / "skills" / "report-anonymization-qc-loop" / "fixtures"
    / "sample_anonymized_with_leaks.csv"
)
# WITHOUT-skill entrypoint: the raw upstream convergence loop (teammate's tree).
UPSTREAM_QC_LOOP = _env_path(
    "CEVAL_UPSTREAM_QC_LOOP",
    REPO_ROOT / "code" / "data_curration_skills" / "src" / "reports_preprocessing"
    / "01_anonymization" / "anonymize_qc_loop.py",
)
# reports_preprocessing dir the skill's live mode uses to locate the SAME upstream.
MR_RATE_REPORTS_ROOT = _env_path(
    "CEVAL_MR_RATE_ROOT",
    REPO_ROOT / "code" / "data_curration_skills" / "src" / "reports_preprocessing",
)

# --- Output locations (runs/ is gitignored) --------------------------------
RUNS_DIR = _env_path("CEVAL_RUNS_DIR", SKILLS_ROOT / "runs" / "curation_eval")
DOCS_DIR = SKILLS_ROOT / "docs"
DEFAULT_REPORT_MD = DOCS_DIR / "curation-with-vs-without-experiment.md"


def report_text_columns() -> list[str]:
    """Report-text columns to concatenate when a full-report view is needed."""
    return ["report"]
