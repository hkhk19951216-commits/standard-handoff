#!/usr/bin/env python3
"""Build distributable standard-handoff artifacts with a completeness gate.

Produces:
  dist/standard-handoff/                    pure skill directory (for DSH presets)
  dist/standard-handoff-<version>.zip       top-level folder preserved
  dist/standard-handoff-<version>.zip.sha256

Every build runs quick_validate, a required-file completeness gate, UTF-8 /
LF hygiene, MANIFEST verification, then unpacks its own zip and re-verifies
the MANIFEST. A failed self-verification deletes the zip artifacts.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD = ROOT / "skills" / "standard-handoff"
DIST = ROOT / "dist"
sys.path.insert(0, str(PAYLOAD / "scripts"))

import _common  # noqa: E402
import quick_validate  # noqa: E402

REQUIRED = (
    "SKILL.md",
    "README.md",
    "INSTALL.md",
    "LICENSE",
    "NOTICE.md",
    _common.MANIFEST_NAME,
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

HYGIENE_NAMES = {"__pycache__", ".DS_Store", "Thumbs.db", ".git"}


def fail(message):
    raise SystemExit("GATE FAILED: " + message)


def run_gates():
    ok, message = quick_validate.validate_skill(PAYLOAD)
    print("frontmatter gate: {}".format(message))
    if not ok:
        fail(message)

    missing = [name for name in REQUIRED if not (PAYLOAD / name).is_file()]
    print("completeness gate: {}/{} required files present".format(
        len(REQUIRED) - len(missing), len(REQUIRED)))
    if missing:
        fail("missing required payload files: " + ", ".join(missing))

    bad_utf8, bad_cr, dirty = [], [], []
    for absolute, relative in _common.iter_payload_files(PAYLOAD):
        raw = absolute.read_bytes()
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            bad_utf8.append(relative)
        if b"\r" in raw:
            bad_cr.append(relative)
    manifest_file = PAYLOAD / _common.MANIFEST_NAME
    if b"\r" in manifest_file.read_bytes():
        bad_cr.append(_common.MANIFEST_NAME)
    for item in PAYLOAD.rglob("*"):
        if item.name in HYGIENE_NAMES or item.suffix in (".pyc", ".tmp"):
            dirty.append(item.relative_to(PAYLOAD).as_posix())
    print("hygiene gate: utf8_bad={} crlf_bad={} dirty={}".format(
        len(bad_utf8), len(bad_cr), len(dirty)))
    if bad_utf8:
        fail("non-UTF8 files: " + ", ".join(bad_utf8))
    if bad_cr:
        fail("CRLF files: " + ", ".join(bad_cr))
    if dirty:
        fail("forbidden files in payload: " + ", ".join(dirty))

    expected = _common.read_manifest(manifest_file)
    actual = {rel: _common.sha256_file(absolute)
              for absolute, rel in _common.iter_payload_files(PAYLOAD)}
    if expected != actual:
        changed = sorted(set(expected) ^ set(actual)) + sorted(
            k for k in set(expected) & set(actual) if expected[k] != actual[k])
        fail("MANIFEST is stale; rebuild it. Affected: " + ", ".join(changed))
    print("manifest gate: {} files verified".format(len(actual)))
    return expected


def build_plain_directory():
    target = DIST / "standard-handoff"
    if target.exists():
        shutil.rmtree(str(target))
    target.mkdir(parents=True)
    for absolute, relative in _common.iter_payload_files(PAYLOAD):
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(absolute), str(destination))
    shutil.copy2(str(PAYLOAD / _common.MANIFEST_NAME),
                 str(target / _common.MANIFEST_NAME))
    print("built: dist/standard-handoff/ ({} files)".format(len(REQUIRED)))
    return target


def build_zip(version):
    DIST.mkdir(parents=True, exist_ok=True)
    zip_path = DIST / ("standard-handoff-{}.zip".format(version))
    sum_path = DIST / ("standard-handoff-{}.zip.sha256".format(version))
    entries = sorted(_common.iter_payload_files(PAYLOAD), key=lambda pair: pair[1])
    entries.append((PAYLOAD / _common.MANIFEST_NAME, _common.MANIFEST_NAME))
    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as archive:
        for absolute, relative in entries:
            archive.write(str(absolute), arcname="standard-handoff/" + relative)
    digest = _common.sha256_file(zip_path)
    _common.write_text_lf(sum_path, "{}  {}\n".format(digest, zip_path.name))
    print("built: {} ({} entries, {} bytes)".format(
        zip_path.name, len(entries), zip_path.stat().st_size))
    print("built: {} -> {}".format(sum_path.name, digest))
    return zip_path, sum_path


def self_verify(zip_path, sum_path, expected):
    with tempfile.TemporaryDirectory(prefix="standard-handoff-verify-") as tmp:
        with zipfile.ZipFile(str(zip_path)) as archive:
            archive.extractall(tmp)
        extracted = Path(tmp) / "standard-handoff"
        manifest = extracted / _common.MANIFEST_NAME
        if not manifest.is_file():
            return "extracted package has no MANIFEST.sha256"
        if _common.sha256_file(manifest) != _common.sha256_file(PAYLOAD / _common.MANIFEST_NAME):
            return "extracted MANIFEST differs from source"
        for relative, digest in sorted(expected.items()):
            candidate = extracted / relative
            if not candidate.is_file():
                return "extracted file missing: " + relative
            if _common.sha256_file(candidate) != digest:
                return "extracted hash mismatch: " + relative
        listed = _common.read_text(sum_path).strip()
        if not listed.startswith(_common.sha256_file(zip_path)):
            return "zip checksum file does not match the zip"
    return None


def main():
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="1.0.0", help="version string for the zip filename")
    args = parser.parse_args()

    print("standard-handoff package | version={}".format(args.version))
    print("-" * 68)
    expected = run_gates()
    build_plain_directory()
    zip_path, sum_path = build_zip(args.version)
    problem = self_verify(zip_path, sum_path, expected)
    print("-" * 68)
    if problem:
        zip_path.unlink(missing_ok=True)
        sum_path.unlink(missing_ok=True)
        print("SELF-VERIFY FAILED: {}".format(problem))
        print("zip artifacts deleted; dist/standard-handoff/ retained for inspection")
        return 1
    print("SELF-VERIFY PASSED: extracted package matches MANIFEST exactly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
