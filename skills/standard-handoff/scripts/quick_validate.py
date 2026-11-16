#!/usr/bin/env python3
"""Validate SKILL.md frontmatter before packaging or syncing.

Only checks the cross-agent minimum: name + description, hyphen-case name,
no angle brackets in description, name equals directory name.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from _common import read_text

NAME_RE = re.compile(r"^[a-z0-9-]+$")


def validate_skill(skill_dir):
    # resolve() makes `quick_validate.py .` work from inside the skill folder;
    # Path('.').name is '' and would otherwise fail the directory-name check.
    directory = Path(skill_dir).resolve()
    skill_md = directory / "SKILL.md"
    if not skill_md.is_file():
        return False, "SKILL.md not found: {}".format(skill_md)

    text = read_text(skill_md)
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return False, "No YAML frontmatter found"
    frontmatter = match.group(1)

    name_match = re.search(r"^name:\s*(.+?)\s*$", frontmatter, re.MULTILINE)
    desc_match = re.search(r"^description:\s*(.+?)\s*$", frontmatter, re.MULTILINE)
    if not name_match:
        return False, "Missing 'name' in frontmatter"
    if not desc_match:
        return False, "Missing 'description' in frontmatter"

    name = name_match.group(1).strip().strip("\"'")
    if not NAME_RE.match(name):
        return False, "Name '{}' must be lowercase hyphen-case".format(name)
    if name.startswith("-") or name.endswith("-") or "--" in name:
        return False, "Name has leading/trailing/doubled hyphen"
    if len(name) > 64:
        return False, "Name longer than 64 characters"
    if name != directory.name:
        return False, "Name '{}' does not match directory '{}'".format(name, directory.name)

    description = desc_match.group(1)
    if "<" in description or ">" in description:
        return False, "Description cannot contain angle brackets (< or >)"
    return True, "Skill is valid!"


def main():
    if len(sys.argv) < 2:
        print("Usage: quick_validate.py <skill-folder>")
        return 2
    ok, message = validate_skill(sys.argv[1])
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
