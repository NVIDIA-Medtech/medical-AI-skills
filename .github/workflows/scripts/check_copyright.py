"""
SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: Apache-2.0

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

# This file is modified from the RAPIDS RAFT project which is under the
# Apache 2.0 license.
# (https://github.com/rapidsai/raft/blob/branch-22.08/ci/checks/copyright.py)

import argparse
import datetime
import itertools
import os
import re
import sys

import gitutils
from add_copyright_headers import NVIDIA_COPYRIGHT

FilesToCheck = [
    re.compile(r"[.](cmake|cpp|css|cu|cuh|h|hpp|js|sh|pxd|py|pyx|ya?ml)$"),
    re.compile(r"(^|/)Makefile$"),
    re.compile(r"CMakeLists[.]txt$"),
    re.compile(r"Dockerfile$"),
    re.compile(r"[.]dockerfile$"),
    re.compile(r"CMakeLists_standalone[.]txt$"),
    re.compile(r"setup[.]cfg$"),
    re.compile(r"[.]flake8[.]cython$"),
    re.compile(r"meta[.]yaml$"),
]
ExemptFiles = []

# Match a notice on its own line, including in a comment or Python docstring.
CopyrightHeader = re.compile(
    r"""^\s*(?:[#/*]+|"{3}|'{3})?\s*"""
    r"(?P<notice>(?:SPDX-FileCopyrightText:\s*(?:Copyright\s*)?|Copyright\s*)"
    r"(?:\(c\)\s*)?(?P<start>\d{4})(?:\s*-\s*(?P<end>\d{4}))?[\s,]+(?P<holder>.+?))"
    r"""\s*(?:\*/|"{3}|'{3})?\s*$""",
    re.IGNORECASE,
)


def check_this_file(f):
    # This check covers things like symlinks which point to files that DNE
    if not (os.path.exists(f)):
        return False
    if gitutils and gitutils.is_file_empty(f):
        return False
    for exempt in ExemptFiles:
        if exempt.search(f):
            return False
    return any(checker.search(f) for checker in FilesToCheck)


def check_copyright(f, update_current_year, ignore_year_mismatch=False):
    """Check NVIDIA notice formatting and the copyright year range."""
    with open(f, encoding="utf-8", newline="") as fp:
        lines = fp.readlines()

    errs = []
    nvidia_headers = []
    first_header = None
    for line_no, line in enumerate(lines, 1):
        match = CopyrightHeader.match(line)
        if not match:
            continue
        if first_header is None:
            first_header = (line_no, match)
        if re.match(r"NVIDIA\b", match["holder"], re.IGNORECASE):
            nvidia_headers.append((line_no, match))
            years = match["start"] + ("-" + match["end"] if match["end"] else "")
            expected = NVIDIA_COPYRIGHT.format(years=years)
            if match["notice"] != expected:
                errs.append((f, line_no, f"Expected NVIDIA copyright notice: {expected}", None))
    if first_header is None:
        return [
            (f, 0, "Copyright header missing or formatted incorrectly (manual fix required)", None)
        ]
    if errs:
        return errs

    this_year = datetime.date.today().year
    updated = False
    for line_no, match in nvidia_headers or [first_header]:
        start = int(match["start"])
        end = int(match["end"] or start)
        if start > end:
            errs.append((f, line_no, "First year after second year in the copyright header", None))
        elif not ignore_year_mismatch and not start <= this_year <= end:
            years = f"{min(start, this_year)}-{max(end, this_year)}"
            if update_current_year:
                after_years = match.end("end") if match["end"] else match.end("start")
                line = lines[line_no - 1]
                lines[line_no - 1] = line[: match.start("start")] + years + line[after_years:]
                print(f"File: {f}. Changing line {line_no}")
                updated = True
            else:
                errs.append(
                    (f, line_no, "Current year not included in the copyright header", years)
                )
    if updated:
        with open(f, "w", encoding="utf-8", newline="") as out_file:
            out_file.writelines(lines)
    return errs


def get_all_files_under_dir(root):
    ret_list = []
    for dirpath, _, filenames in os.walk(root):
        ret_list.extend([os.path.join(dirpath, fn) for fn in filenames])
    return ret_list


def check_copyright_main():
    """
    Checks for copyright headers in all the modified files. In case of local
    repo, this script will just look for uncommitted files and in case of CI
    it compares between branches "$PR_TARGET_BRANCH" and "current-pr-branch"
    """
    ret_val = 0
    global ExemptFiles

    argparser = argparse.ArgumentParser(
        "Checks for a consistent copyright header in git's modified files"
    )
    argparser.add_argument(
        "--update-current-year",
        dest="update_current_year",
        action="store_true",
        required=False,
        help="If set, update the current year if a header is already present and well formatted.",
    )
    argparser.add_argument(
        "--git-modified-only",
        dest="git_modified_only",
        action="store",
        type=str,
        nargs="?",
        default=None,
        const="no-target",
        required=False,
        help="If set, "
        "only files seen as modified by git will be "
        "processed. It will look for local modifications"
        "(unstaged, untracked) if no git reference is provided.",
    )
    argparser.add_argument(
        "--exclude",
        dest="exclude",
        action="append",
        required=False,
        default=[],
        help=("Exclude the paths specified (regexp). Can be specified multiple times."),
    )
    argparser.add_argument(
        "--exclude-config",
        dest="exclude_config",
        type=str,
        required=False,
        default=None,
        help=(
            "Path to a file containing exclude patterns (one per line). "
            "Lines starting with # are treated as comments."
        ),
    )
    argparser.add_argument(
        "--ignore-year-mismatch",
        dest="ignore_year_mismatch",
        action="store_true",
        required=False,
        help="If set, ignore year mismatches in copyright headers (when current year is not within the copyright year range).",
    )

    args, dirs = argparser.parse_known_args()

    # Read excludes from config file if specified
    config_excludes = []
    if args.exclude_config:
        config_path = args.exclude_config
        if not os.path.isabs(config_path):
            # If relative path, try current working directory first
            if os.path.exists(config_path):
                config_path = os.path.abspath(config_path)
            else:
                # If not found in current directory, try relative to script directory
                script_dir = os.path.dirname(os.path.abspath(__file__))
                config_path = os.path.join(script_dir, os.path.basename(config_path))

        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith("#"):
                        config_excludes.append(line)
        else:
            print(f"Warning: Config file not found at {config_path}")

    try:
        # Combine config file excludes with command line excludes
        all_excludes = config_excludes + args.exclude
        ExemptFiles = ExemptFiles + [pathName for pathName in all_excludes]
        ExemptFiles = [re.compile(file) for file in ExemptFiles]
    except re.error as reException:
        print("Regular expression error:")
        print(reException)
        return 1

    all_files = []
    if dirs:
        for d in [os.path.abspath(d) for d in dirs]:
            if not (os.path.isdir(d)):
                raise ValueError(f"{d} is not a directory.")
            all_files += get_all_files_under_dir(d)

    if args.git_modified_only:
        target_branch = None
        if args.git_modified_only != "no-target":
            target_branch = args.git_modified_only
            print(f"Checking copyright headers in modified files between {target_branch} and HEAD")
        modified_files = gitutils.modified_files(target_branch, True)
        all_files = list(set(all_files).intersection(modified_files)) if dirs else modified_files

    files = [f for f in all_files if check_this_file(f)]

    # Print progress information
    print(f"Checking copyright headers in {len(files)} files out of {len(all_files)} total files")
    if len(files) > 0:
        print(f"Example files being checked: {', '.join(files[:3])}")
        if len(files) > 3:
            print(f"... and {len(files) - 3} more files")

    errors = tuple(
        itertools.chain(
            *[
                check_copyright(f, args.update_current_year, args.ignore_year_mismatch)
                for f in files
            ]
        )
    )
    if errors:
        print("Copyright headers incomplete in some of the files!")
        for file_name, line_no, err_msg, _ in errors:
            print(f"  {file_name}:{line_no} Issue: {err_msg}")
        print("")
        n_fixable = sum(1 for e in errors if e[-1] is not None)
        if n_fixable > 0:
            print(
                f"You can run `python3 {' '.join(sys.argv)} --update-current-year` to fix "
                f"{n_fixable} of these errors."
            )
        ret_val = 1
    else:
        print("Copyright check passed")

    return ret_val


if __name__ == "__main__":
    import sys

    sys.exit(check_copyright_main())
