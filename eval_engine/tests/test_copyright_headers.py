# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "scripts"
YEAR = date.today().year
NOTICE = (
    f"SPDX-FileCopyrightText: Copyright (c) {YEAR} NVIDIA CORPORATION & AFFILIATES. "
    "All rights reserved."
)


def check(directory, *args):
    return subprocess.run(
        [sys.executable, SCRIPTS / "check_copyright.py", *args, directory],
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    ("filename", "wrapper"),
    [
        ("sample.py", '"""{}"""'),
        ("ci.yml", "# {}"),
        ("Makefile", "# {}"),
        ("app.js", "// {}"),
        ("style.css", "/* {} */"),
    ],
)
def test_compliance_status_for_nvidia_notice(tmp_path, filename, wrapper):
    path = tmp_path / filename
    path.write_text(wrapper.format(NOTICE) + "\n")
    assert check(tmp_path).returncode == 0
    for invalid in (
        NOTICE.replace(" NVIDIA", ", NVIDIA"),
        NOTICE.replace("AFFILIATES", "Affiliates"),
    ):
        path.write_text("\n" + wrapper.format(invalid) + "\n")
        for args in ((), ("--ignore-year-mismatch",)):
            result = check(tmp_path, *args)
            assert result.returncode == 1
            assert f"{filename}:2" in result.stdout
            assert NOTICE in result.stdout


def test_update_year_only_changes_nvidia_years(tmp_path):
    path = tmp_path / "sample.py"
    old = NOTICE.replace(str(YEAR), str(YEAR - 1))
    updated = NOTICE.replace(str(YEAR), f"{YEAR - 1}-{YEAR}")
    other = f"# Copyright (c) {YEAR - 2}, Other Author."
    content = f'{other}\r\n# {old}\r\nexample = "{old}"\r\n'.encode()
    path.write_bytes(content)
    assert check(tmp_path).returncode == 1
    assert check(tmp_path, "--update-current-year").returncode == 0
    assert path.read_bytes() == content.replace(f"# {old}".encode(), f"# {updated}".encode())
    assert check(tmp_path).returncode == 0


def test_third_party_notice_and_generated_header(tmp_path):
    path = tmp_path / "sample.py"
    path.write_text(f"# Copyright (c) {YEAR}, Other Author.\n")
    assert check(tmp_path).returncode == 0
    path.write_text(f'example = "{NOTICE}"\n')
    assert check(tmp_path).returncode == 1
    path.write_text("print(42)\n")
    subprocess.run([sys.executable, SCRIPTS / "add_copyright_headers.py", path], check=True)
    assert check(tmp_path).returncode == 0
