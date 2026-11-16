#!/usr/bin/env python3
"""Mirror the standard-handoff payload into agent skill roots.

Modes:
  (default) / --check    read-only comparison, never writes
  --apply                atomic directory swap from a staging copy
  --uninstall            remove targets whose hashes match MANIFEST exactly
  --apply --check        dry-run apply
  --uninstall --check    dry-run uninstall (safe preview)

DSH is never written unless --dsh-preset is supplied explicitly.
No settings.json, source tree, or dist/ is ever touched.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD = ROOT / "skills" / "standard-handoff"
sys.path.insert(0, str(PAYLOAD / "scripts"))

import _common  # noqa: E402

TARGETS = (
    ("WorkBuddy", "~/.workbuddy/skills/standard-handoff"),
    ("Claude Code", "~/.claude/skills/standard-handoff"),
    ("Codex", "~/.codex/skills/standard-handoff"),
    ("agents (generic)", "~/.agents/skills/standard-handoff"),
)


def expected_state():
    manifest = PAYLOAD / _common.MANIFEST_NAME
    if not manifest.is_file():
        raise SystemExit("ERROR: MANIFEST.sha256 missing in payload; rebuild it first")
    state = _common.read_manifest(manifest)
    state[_common.MANIFEST_NAME] = _common.sha256_file(manifest)
    return state


def diff(target, expected):
    missing, mismatched, extra = [], [], []
    if not target.is_dir():
        return missing, mismatched, extra, True
    for relative, digest in sorted(expected.items()):
        candidate = target / relative
        if not candidate.is_file():
            missing.append(relative)
        elif _common.sha256_file(candidate) != digest:
            mismatched.append(relative)
    for item in sorted(target.rglob("*")):
        if item.is_file():
            relative = item.relative_to(target).as_posix()
            if relative not in expected:
                extra.append(relative)
    return missing, mismatched, extra, False


def describe(label, target, missing, mismatched, extra, absent):
    print("[{}] {}".format(label, target))
    if absent:
        print("  MISSING: target directory does not exist")
        return False
    if not (missing or mismatched or extra):
        print("  OK: all files match MANIFEST")
        return True
    for relative in missing:
        print("  MISSING FILE: " + relative)
    for relative in mismatched:
        print("  HASH MISMATCH: " + relative)
    for relative in extra:
        print("  EXTRA FILE (not in MANIFEST): " + relative)
    return False


def check_target(label, target, expected):
    missing, mismatched, extra, absent = diff(target, expected)
    return describe(label, target, missing, mismatched, extra, absent)


def apply_target(label, target, expected, force=False, dry_run=False):
    print("[{}] {}".format(label, target))
    extra = []
    if target.is_dir():
        _, _, extra, _ = diff(target, expected)
    if extra and not force:
        print("  SKIP: {} file(s) not in MANIFEST would be removed.".format(len(extra)))
        for relative in extra:
            print("    " + relative)
        print("  Re-run with --force to allow full replacement.")
        return False
    if dry_run:
        print("  WOULD APPLY: {} payload file(s), atomic swap".format(len(expected)))
        return True

    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".standard-handoff.stage-", dir=str(parent)))
    backup = parent / (".standard-handoff.old-" + str(os.getpid()))
    try:
        for absolute, relative in _common.iter_payload_files(PAYLOAD):
            destination = stage / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(absolute), str(destination))
        shutil.copy2(str(PAYLOAD / _common.MANIFEST_NAME),
                     str(stage / _common.MANIFEST_NAME))

        if backup.exists():
            shutil.rmtree(str(backup), ignore_errors=True)
        had_original = target.exists()
        if had_original:
            os.replace(str(target), str(backup))
        try:
            os.replace(str(stage), str(target))
        except OSError:
            if had_original:
                os.replace(str(backup), str(target))
            raise
        if had_original:
            shutil.rmtree(str(backup), ignore_errors=True)
        print("  APPLIED: {} file(s)".format(len(expected)))
        return True
    except OSError as exc:
        print("  ERROR: {}".format(exc))
        return False
    finally:
        if stage.exists():
            shutil.rmtree(str(stage), ignore_errors=True)


def uninstall_target(label, target, expected, dry_run=False):
    print("[{}] {}".format(label, target))
    if not target.is_dir():
        print("  SKIP: target does not exist")
        return True
    missing, mismatched, extra, _ = diff(target, expected)
    if missing or mismatched or extra:
        print("  REFUSE: target does not match MANIFEST exactly "
              "(missing={}, mismatched={}, extra={})".format(
                  len(missing), len(mismatched), len(extra)))
        print("  Remove it manually if you really want to.")
        return False
    if dry_run:
        print("  WOULD REMOVE: {} file(s), all hashes match".format(len(expected)))
        return True
    shutil.rmtree(str(target))
    print("  REMOVED")
    return True


def main():
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true",
                        help="read-only comparison; also turns --apply/--uninstall into a dry run")
    parser.add_argument("--apply", action="store_true", help="mirror payload into agent roots")
    parser.add_argument("--uninstall", action="store_true", help="remove exact-match mirrors")
    parser.add_argument("--force", action="store_true",
                        help="allow replacing targets that contain extra files")
    parser.add_argument("--dsh-preset", metavar="PATH",
                        help="explicitly target a DSH preset skills directory")
    args = parser.parse_args()

    if args.apply and args.uninstall:
        parser.error("--apply and --uninstall are mutually exclusive")

    mode = "check"
    if args.apply:
        mode = "apply"
    elif args.uninstall:
        mode = "uninstall"
    dry_run = bool(args.check)

    expected = expected_state()
    targets = [(label, Path(_common.expand_path(raw, ROOT))) for label, raw in TARGETS]
    if args.dsh_preset:
        base = Path(_common.expand_path(args.dsh_preset, ROOT))
        targets.append(("DSH preset", base / "standard-handoff"))

    print("standard-handoff sync | mode={}{} | payload files={}".format(
        mode, " (dry run)" if dry_run and mode != "check" else "", len(expected)))
    print("-" * 68)

    results = []
    for label, target in targets:
        if mode == "check":
            results.append(check_target(label, target, expected))
        elif mode == "apply":
            results.append(apply_target(label, target, expected, args.force, dry_run))
        else:
            results.append(uninstall_target(label, target, expected, dry_run))

    if not args.dsh_preset:
        print("[DSH] skipped - pass --dsh-preset <preset/skills> to target explicitly")
    print("-" * 68)
    if mode == "check":
        print("RESULT: {}/{} targets in sync".format(sum(results), len(results)))
    else:
        print("RESULT: {}/{} targets succeeded".format(sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
