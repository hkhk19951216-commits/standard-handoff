#!/usr/bin/env python3
"""Read-only integrity check for an unpacked standard-handoff distribution.

Works on any machine with Python 3.9+ and no third-party packages.

    python3 scripts/verify_install.py
    py -3   scripts/verify_install.py
    py -3   scripts/verify_install.py --target "~/.claude/skills/standard-handoff"

Compares every file against MANIFEST.sha256, checks frontmatter and LF
hygiene. Never writes and never repairs. A PASS means the bytes match this
distribution; it says nothing about whether a handoff document is truthful.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from _common import (  # noqa: E402
    MANIFEST_NAME,
    expand_path,
    find_crlf,
    iter_payload_files,
    read_manifest,
    sha256_file,
)
from quick_validate import validate_skill  # noqa: E402

CRITICAL = (
    "SKILL.md",
    "INSTALL.md",
    "README.md",
    "LICENSE",
    "NOTICE.md",
    "agents/openai.yaml",
    "assets/handoff.template.md",
    "references/rigor.md",
    "references/quality.md",
    "references/packaging.md",
    "references/receiving.md",
    "scripts/_common.py",
    "scripts/handoff_validate.py",
    "scripts/quick_validate.py",
    "scripts/verify_install.py",
)


def check(root):
    manifest = root / MANIFEST_NAME
    if not manifest.is_file():
        return ["MANIFEST.sha256 missing: {}".format(manifest)], 0

    expected = read_manifest(manifest)
    actual = {rel for _, rel in iter_payload_files(root)}
    problems = []

    for relative in sorted(set(expected) - actual):
        problems.append("missing: " + relative)
    for relative in sorted(actual - set(expected)):
        problems.append("extra (not in MANIFEST): " + relative)
    for relative in sorted(set(expected) & actual):
        if sha256_file(root / relative) != expected[relative]:
            problems.append("hash mismatch: " + relative)

    for relative in CRITICAL:
        if not (root / relative).is_file():
            problems.append("critical file missing: " + relative)

    ok, message = validate_skill(root)
    if not ok:
        problems.append("frontmatter: " + message)

    for offender in find_crlf(root):
        problems.append("CRLF in text file: " + offender)

    return problems, len(expected)


def main():
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", metavar="PATH",
                        help="verify an installed copy instead of this unpacked folder")
    args = parser.parse_args()

    root = Path(expand_path(args.target)) if args.target else ROOT
    label = "installed copy" if args.target else "unpacked distribution"
    print("standard-handoff verify | {} | {}".format(label, root))
    print("-" * 68)
    if not root.is_dir():
        print("FAIL: directory does not exist")
        return 2

    problems, count = check(root)
    for item in problems:
        print("  " + item)
    print("-" * 68)
    if problems:
        print("FAIL: {} problem(s); {} file(s) listed in MANIFEST".format(len(problems), count))
        print("Re-extract the zip or re-copy the whole folder. Do not hand-edit files.")
        return 1
    print("PASS: {} file(s) match MANIFEST; frontmatter and LF are clean".format(count))
    print("Next: open a new agent session and say one of the trigger phrases in INSTALL.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
