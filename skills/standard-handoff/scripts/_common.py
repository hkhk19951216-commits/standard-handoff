#!/usr/bin/env python3
"""Shared helpers for standard-handoff tooling.

Pure standard library, Python 3.9+, LF-only, no platform-specific APIs.
Deliberately avoids fcntl / os.getuid / pwd / grp / termios: those are the
exact imports that break CLI tools on Windows.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

FORBIDDEN_IMPORTS = (
    "import fcntl",
    "os.getuid",
    "import pwd",
    "import grp",
    "import termios",
)

MANIFEST_NAME = "MANIFEST.sha256"
EXCLUDE_NAMES = {MANIFEST_NAME, ".DS_Store", "Thumbs.db"}
EXCLUDE_DIRS = {"__pycache__", ".git", "dist", "evals"}
EXCLUDE_SUFFIXES = {".pyc", ".tmp"}


def expand_path(raw, root=None):
    """Expand ~ and %VAR%/$VAR, then anchor relative paths under root."""
    value = os.path.expanduser(str(raw))
    value = os.path.expandvars(value)
    if not os.path.isabs(value) and root is not None:
        value = os.path.join(str(root), value)
    return os.path.normpath(value)


def detect_python(explicit=None):
    """Four-level fallback. Returns [binary, ...prefix args] or None.

    L1 explicit --python / PYTHON_BIN, L2 sys.executable,
    L3 PATH python3 -> python -> py -3, L4 explicit failure (never guess).
    """
    candidates = []
    if explicit:
        candidates.append([explicit])
    env_bin = os.environ.get("PYTHON_BIN")
    if env_bin:
        candidates.append([env_bin])
    if sys.executable:
        candidates.append([sys.executable])
    for name in ("python3", "python"):
        found = shutil.which(name)
        if found:
            candidates.append([found])
    py_launcher = shutil.which("py")
    if py_launcher:
        candidates.append([py_launcher, "-3"])

    for prefix in candidates:
        try:
            probe = subprocess.run(
                prefix + ["-c", "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)"],
                capture_output=True,
            )
            if probe.returncode == 0:
                return prefix
        except (OSError, ValueError):
            continue
    return None


def read_text(path):
    """UTF-8 read with CRLF/CR normalisation (avoids false regex negatives)."""
    raw = Path(path).read_text(encoding="utf-8", errors="replace")
    return raw.replace("\r\n", "\n").replace("\r", "\n")


def write_text_lf(path, text):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(str(target), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(str(path), "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_payload_files(root):
    """Return [(absolute Path, posix relative path)] in stable order."""
    base = Path(root)
    found = []
    for item in sorted(base.rglob("*")):
        if not item.is_file():
            continue
        rel = item.relative_to(base)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if item.name in EXCLUDE_NAMES or item.suffix in EXCLUDE_SUFFIXES:
            continue
        if item.name.endswith(".tmp"):
            continue
        found.append((item, rel.as_posix()))
    return found


def build_manifest(root):
    lines = []
    for absolute, relative in iter_payload_files(root):
        lines.append("{}  {}".format(sha256_file(absolute), relative))
    return "\n".join(lines) + "\n"


def read_manifest(path):
    mapping = {}
    for line in read_text(path).splitlines():
        line = line.strip()
        if not line:
            continue
        digest, _, relative = line.partition("  ")
        mapping[relative.strip()] = digest.strip()
    return mapping


def find_crlf(root):
    """Report CR bytes in TEXT files only.

    A zip or other binary artifact can legitimately contain 0x0D bytes; those
    are not line endings and must not fail the LF hygiene check.
    """
    offenders = []
    for item in sorted(Path(root).rglob("*")):
        if not item.is_file() or item.name == MANIFEST_NAME + ".tmp":
            continue
        raw = item.read_bytes()
        if b"\r" not in raw:
            continue
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        offenders.append(str(item))
    return offenders
