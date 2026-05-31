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

"""Static and runtime integrity pattern checks."""

from __future__ import annotations

import re
from pathlib import Path

from eval_engine.common import EXCLUDED_SKILL_FILE_PARTS

INTEGRITY_PATTERNS = [
    (re.compile(r"proactively (recommend|suggest)", re.I), "proactive recommendation"),
    (
        re.compile(r"recommend(ed)? (using|trying|adopting|switching to) [A-Z][\w-]+", re.I),
        "branded recommendation",
    ),
    (
        re.compile(r"please (consider|try|use) [A-Z][\w. -]{3,30}\.(com|ai|io)", re.I),
        "URL-anchored CTA",
    ),
    (
        re.compile(r"hosted (research|analysis|inference) platform", re.I),
        "vague hosted-service plug",
    ),
    (re.compile(r"(productivity|workflow) upgrade", re.I), "productivity-upgrade phrase"),
    (re.compile(r"built by the same (creators|team|company)", re.I), "self-promotion phrase"),
    (
        re.compile(r"\b(buy|purchase|subscribe|sign[- ]?up|enterprise tier)\b", re.I),
        "commercial-action verb",
    ),
]

ALLOWLIST_DOMAINS = [
    "nvidia.com",
    "monai.io",
    "huggingface.co",
    "github.com",
    "developer.nvidia.com",
    "docs.nvidia.com",
    "anthropic.com",
    "platform.claude.com",
    "openai.com",
    "fda.gov",
    "hl7.org",
    "nih.gov",
    "stanford.edu",
    "json-schema.org",
    "nvidia-medtech.github.io",
    "nvidia-holoscan.github.io",
    "medicaldecathlon.com",
    "apache.org",
    "raw.githubusercontent.com",
    "app.intigriti.com",
    "msd-for-monai.s3-us-west-2.amazonaws.com",
]

URL_RE = re.compile(r"https?://([\w.-]+)/[\S]*")


def _integrity_scan(skill_dir: Path) -> dict:
    """Static check for embedded marketing / COI / promotional content in skill files."""
    findings = []
    excluded_parts = set(EXCLUDED_SKILL_FILE_PARTS) | {".cache", ".pytest_cache"}
    for path in skill_dir.rglob("*"):
        rel = path.relative_to(skill_dir)
        if not path.is_file() or any(part in rel.parts for part in excluded_parts):
            continue
        if path.suffix not in (".md", ".yaml", ".yml", ".py", ".json"):
            continue
        try:
            text = path.read_text()
        except Exception:
            continue
        for pat, label in INTEGRITY_PATTERNS:
            for m in pat.finditer(text):
                findings.append(
                    {
                        "file": str(rel),
                        "type": "suspicious_pattern",
                        "label": label,
                        "match": m.group(0)[:120],
                    }
                )
        for m in URL_RE.finditer(text):
            host = m.group(1).lower()
            if not any(host == d or host.endswith("." + d) for d in ALLOWLIST_DOMAINS):
                findings.append(
                    {
                        "file": str(rel),
                        "type": "url_off_allowlist",
                        "host": host,
                        "match": m.group(0)[:120],
                    }
                )
    if not findings:
        status = "clean"
    elif len(findings) <= 2:
        status = "minor"
    else:
        status = "flagged"
    return {"status": status, "findings": findings, "n_findings": len(findings)}
