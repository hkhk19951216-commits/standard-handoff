#!/usr/bin/env python3
"""Full self-test for the standard-handoff source tree.

Pure standard library, Python 3.9+. Run from anywhere:

    python tools/selftest.py

Checks: frontmatter gate, four packet fixtures, template-boilerplate gate,
banned platform APIs (AST-based, so string constants do not false-positive),
UTF-8 + LF hygiene, MANIFEST integrity, the four-level Python fallback, and
the shipped install verifier (including tamper detection).
"""
from __future__ import annotations

import ast
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD = ROOT / "skills" / "standard-handoff"
sys.path.insert(0, str(PAYLOAD / "scripts"))

import _common  # noqa: E402
import handoff_validate as validator  # noqa: E402
import quick_validate  # noqa: E402
import verify_install  # noqa: E402

BANNED_MODULES = {"fcntl", "pwd", "grp", "termios"}
BANNED_OS_ATTRS = {"getuid", "geteuid", "setuid", "getgid", "getegid", "chown"}

FIXTURES = ROOT / "evals" / "fixtures"
RESULTS = []


def record(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print("{} {}{}".format("PASS" if ok else "FAIL", name,
                           (" - " + detail) if detail else ""))


def load(name):
    return _common.read_text(FIXTURES / name)


def test_frontmatter():
    ok, message = quick_validate.validate_skill(PAYLOAD)
    record("frontmatter gate", ok, message)
    text = _common.read_text(PAYLOAD / "SKILL.md")
    block = text.split("---", 2)[1]
    keys = [line.split(":", 1)[0].strip() for line in block.splitlines()
            if ":" in line and not line.startswith((" ", "\t", "#"))]
    record("frontmatter is exactly name+description",
           sorted(keys) == ["description", "name"], ", ".join(sorted(keys)))


def test_fixtures():
    expectations = {
        "ok.md": ("clean packet", lambda e, w: len(e) == 0),
        "placeholder.md": ("placeholders rejected",
                           lambda e, w: any("unresolved placeholder" in x for x in e)),
        "dangerous.md": ("destructive first action rejected",
                         lambda e, w: any("destructive command" in x for x in e)),
        "chinese-false-positive.md": (
            "Chinese prose does not trigger danger errors",
            lambda e, w: len(e) == 0 and not any(
                "destructive" in x.lower() or "dangerous" in x.lower() for x in e)),
    }
    for name, (label, predicate) in expectations.items():
        errors, warnings = validator.validate(load(name))
        ok = predicate(errors, warnings)
        record(label, ok, "{} error(s), {} warning(s){}".format(
            len(errors), len(warnings), (" | " + "; ".join(errors)) if errors else ""))

    errors, _ = validator.validate(_common.read_text(PAYLOAD / "assets" / "handoff.template.md"))
    record("unfilled template is rejected",
           any("template boilerplate" in x for x in errors),
           "{} error(s)".format(len(errors)))


def test_banned_apis():
    offenders = []
    folders = [ROOT / "tools", PAYLOAD / "scripts"]
    for folder in folders:
        for path in sorted(folder.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split(".")[0] in BANNED_MODULES:
                            offenders.append("{}:{} import {}".format(
                                path.name, node.lineno, alias.name))
                elif isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.split(".")[0] in BANNED_MODULES:
                        offenders.append("{}:{} from {}".format(
                            path.name, node.lineno, node.module))
                elif (isinstance(node, ast.Attribute)
                      and isinstance(node.value, ast.Name)
                      and node.value.id == "os"
                      and node.attr in BANNED_OS_ATTRS):
                    offenders.append("{}:{} os.{}".format(path.name, node.lineno, node.attr))
    record("no banned platform APIs (AST)", not offenders, "; ".join(offenders))


def test_encoding_and_lf():
    bad_cr = []
    bad_utf8 = []
    for absolute, relative in _common.iter_payload_files(PAYLOAD):
        raw = absolute.read_bytes()
        if b"\r" in raw:
            bad_cr.append(relative)
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            bad_utf8.append(relative)
    manifest = PAYLOAD / _common.MANIFEST_NAME
    if manifest.exists():
        if b"\r" in manifest.read_bytes():
            bad_cr.append(_common.MANIFEST_NAME)
    record("payload is UTF-8", not bad_utf8, ", ".join(bad_utf8))
    record("payload is LF-only", not bad_cr, ", ".join(bad_cr))
    record("no CRLF anywhere in tree", not _common.find_crlf(ROOT),
           ", ".join(_common.find_crlf(ROOT)))


def test_manifest():
    manifest = PAYLOAD / _common.MANIFEST_NAME
    if not manifest.is_file():
        record("MANIFEST exists", False, "run build_manifest first")
        return
    record("MANIFEST exists", True, "")
    expected = _common.read_manifest(manifest)
    actual = {rel: _common.sha256_file(absolute)
              for absolute, rel in _common.iter_payload_files(PAYLOAD)}
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    changed = sorted(k for k in set(expected) & set(actual) if expected[k] != actual[k])
    ok = not (missing or extra or changed)
    detail = "{} files".format(len(actual))
    if missing:
        detail += "; missing=" + ",".join(missing)
    if extra:
        detail += "; extra=" + ",".join(extra)
    if changed:
        detail += "; changed=" + ",".join(changed)
    record("MANIFEST matches payload", ok, detail)


def test_python_fallback():
    found = _common.detect_python()
    record("detect_python finds an interpreter", found is not None,
           " ".join(found) if found else "none")

    explicit = _common.detect_python(explicit=sys.executable)
    record("L1 explicit --python wins",
           bool(explicit) and explicit[0] == sys.executable)

    previous = os.environ.get("PYTHON_BIN")
    os.environ["PYTHON_BIN"] = sys.executable
    try:
        from_env = _common.detect_python()
        record("L1 PYTHON_BIN honoured",
               bool(from_env) and from_env[0] == sys.executable)
    finally:
        if previous is None:
            os.environ.pop("PYTHON_BIN", None)
        else:
            os.environ["PYTHON_BIN"] = previous

    original_run = _common.subprocess.run

    def always_fail(*args, **kwargs):
        raise OSError("simulated interpreter probe failure")

    _common.subprocess.run = always_fail
    try:
        record("all four levels failing returns None (no guessing)",
               _common.detect_python() is None)
    finally:
        _common.subprocess.run = original_run

    sample = FIXTURES / ".selftest-crlf.tmp"
    with open(str(sample), "wb") as handle:
        handle.write(b"line one\r\nline two\r\n")
    try:
        record("read_text normalises CRLF",
               "\r" not in _common.read_text(sample))
    finally:
        sample.unlink(missing_ok=True)


def test_install_verifier():
    problems, count = verify_install.check(PAYLOAD)
    record("INSTALL verifier passes on source payload", not problems,
           "{} files{}".format(count, ("; " + "; ".join(problems)) if problems else ""))

    with tempfile.TemporaryDirectory(prefix="standard-handoff-selftest-") as tmp:
        copy = Path(tmp) / "standard-handoff"
        shutil.copytree(str(PAYLOAD), str(copy), ignore=shutil.ignore_patterns(
            "__pycache__", "*.pyc", ".DS_Store", "Thumbs.db"))
        problems, count = verify_install.check(copy)
        record("INSTALL verifier passes on a fresh unpacked copy", not problems,
               "{} files{}".format(count, ("; " + "; ".join(problems)) if problems else ""))

        with open(str(copy / "README.md"), "a", encoding="utf-8", newline="\n") as handle:
            handle.write("\nselftest tamper marker\n")
        problems, _ = verify_install.check(copy)
        record("INSTALL verifier detects a tampered file",
               any("hash mismatch" in x for x in problems),
               "; ".join(problems) if problems else "no problem reported")


def main():
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("standard-handoff selftest | root={}".format(ROOT))
    print("python={}".format(sys.version.split()[0]))
    print("-" * 68)
    test_frontmatter()
    test_fixtures()
    test_banned_apis()
    test_encoding_and_lf()
    test_manifest()
    test_python_fallback()
    test_install_verifier()
    print("-" * 68)
    failed = [name for name, ok, _ in RESULTS if not ok]
    print("RESULT: {} passed, {} failed".format(len(RESULTS) - len(failed), len(failed)))
    for name in failed:
        print("  FAILED: " + name)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
