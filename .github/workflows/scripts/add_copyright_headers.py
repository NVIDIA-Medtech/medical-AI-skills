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
"""Insert the NVIDIA SPDX/Apache-2.0 copyright header into source files.

Companion to ``check_copyright.py``: that script *checks* (and can bump the year
of) an existing header but never inserts a missing one. This script inserts the
standard header, as ``#`` comment lines, into any covered file that lacks it,
placed after a leading shebang and/or coding declaration. It is idempotent
(skips files that already carry an ``SPDX-FileCopyrightText`` line) and is wired
into ``make copyright``.

  python3 .github/workflows/scripts/add_copyright_headers.py . \\
      --exclude-config .github/workflows/scripts/copyright_excludes.txt
"""

from __future__ import annotations

import argparse
import os
import re

HEADER_TEXT = [
    "SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.",
    "SPDX-License-Identifier: Apache-2.0",
    "",
    'Licensed under the Apache License, Version 2.0 (the "License");',
    "you may not use this file except in compliance with the License.",
    "You may obtain a copy of the License at",
    "",
    "http://www.apache.org/licenses/LICENSE-2.0",
    "",
    "Unless required by applicable law or agreed to in writing, software",
    'distributed under the License is distributed on an "AS IS" BASIS,',
    "WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.",
    "See the License for the specific language governing permissions and",
    "limitations under the License.",
]

# Same set of source extensions check_copyright.py validates.
FILES_TO_CHECK = [
    re.compile(r"[.](cmake|cpp|cu|cuh|h|hpp|sh|pxd|py|pyx|yaml|yml)$"),
    re.compile(r"CMakeLists[.]txt$"),
    re.compile(r"Dockerfile$"),
    re.compile(r"[.]dockerfile$"),
]
SHEBANG_RE = re.compile(r"^#!")
CODING_RE = re.compile(r"^#.*coding[:=]")


def comment_block() -> list[str]:
    return [(("# " + line).rstrip() + "\n") for line in HEADER_TEXT]


def has_header(text: str) -> bool:
    return "SPDX-FileCopyrightText" in text


def is_covered(path: str) -> bool:
    return any(rx.search(path) for rx in FILES_TO_CHECK)


def load_excludes(config: str | None) -> list[re.Pattern]:
    patterns: list[re.Pattern] = []
    if config and os.path.exists(config):
        with open(config, encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(re.compile(line))
    return patterns


def insert_header(path: str) -> bool:
    with open(path, encoding="utf-8") as fp:
        text = fp.read()
    if not text.strip() or has_header(text):
        return False
    lines = text.splitlines(keepends=True)
    idx = 0
    if lines and SHEBANG_RE.match(lines[0]):
        idx = 1
    if idx < len(lines) and CODING_RE.match(lines[idx]):
        idx += 1
    out = lines[:idx] + comment_block()
    rest = lines[idx:]
    if rest and rest[0].strip() != "":
        out.append("\n")
    out += rest
    with open(path, "w", encoding="utf-8") as fp:
        fp.write("".join(out))
    return True


def iter_files(roots: list[str]):
    for root in roots:
        if os.path.isfile(root):
            yield root
            continue
        for dirpath, dirs, names in os.walk(root):
            if ".git" in dirs:
                dirs.remove(".git")
            for name in names:
                yield os.path.join(dirpath, name)


def main() -> int:
    ap = argparse.ArgumentParser(description="Insert NVIDIA SPDX copyright headers.")
    ap.add_argument("paths", nargs="*", default=["."])
    ap.add_argument("--exclude-config")
    ap.add_argument(
        "--check",
        action="store_true",
        help="Only report files missing a header; do not modify anything.",
    )
    args = ap.parse_args()
    excludes = load_excludes(args.exclude_config)

    changed: list[str] = []
    missing: list[str] = []
    for path in iter_files(args.paths or ["."]):
        if not is_covered(path):
            continue
        rel = os.path.relpath(path)
        if any(rx.search(rel) or rx.search(path) for rx in excludes):
            continue
        if not os.path.exists(path) or os.stat(path).st_size == 0:
            continue
        with open(path, encoding="utf-8", errors="ignore") as fp:
            if has_header(fp.read()):
                continue
        if args.check:
            missing.append(rel)
        elif insert_header(path):
            changed.append(rel)

    if args.check:
        if missing:
            print(f"{len(missing)} file(s) missing a copyright header:")
            for rel in sorted(missing):
                print(f"  {rel}")
            return 1
        print("All covered files carry a copyright header.")
        return 0

    print(f"Inserted copyright header into {len(changed)} file(s).")
    for rel in sorted(changed):
        print(f"  + {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
