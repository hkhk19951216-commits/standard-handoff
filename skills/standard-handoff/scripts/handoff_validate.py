#!/usr/bin/env python3
"""Read-only validator for handoff packets.

Checks structure and safety gates ONLY. It does NOT verify factual truth,
confidence upgrades, semantic continuity, origin, signature, approval,
or current authorization. PASS does not mean the next step is safe to run.

When this script is unavailable, write the Markdown directly and never
fabricate hashes, scans, signatures, or verification results.

Chinese dangerous-word regexes from earlier implementations were removed on
purpose: they flagged ordinary phrases such as "create a task list document".
Instead of scanning Chinese prose, we verify that the approval-boundary
section actually declares all eight restricted verb categories.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

from _common import read_text

HEADINGS = (
    "当前目标",
    "已完成的工作",
    "重要决策",
    "待完成事项",
    "约束与风险",
    "当前代码状态",
    "下一步",
)

RED_VERBS = ("发送", "发布", "付款", "删除", "安装", "执行", "披露", "外部写入")
RECONFIRM = "当前会话重新确认"

PLACEHOLDER_PATTERNS = (
    re.compile(r"<[^>\n]+>"),
    re.compile(r"\b(?:TODO|FIXME|XXX)\b", re.IGNORECASE),
    re.compile(r"待填写|【待补】"),
)

# Boilerplate that only exists in assets/handoff.template.md. A packet that
# still contains any of these was exported without being filled in. This closes
# the "empty template passes validation" hole while deliberately NOT banning
# extra headings (the template itself has a removable usage-notes section).
TEMPLATE_MARKERS = (
    "生成时删除本节",
    "YYYY-MM-DD",
    "一句话目标，加可观测的完成标准",
    "（若与上一节重复",
)

DANGEROUS_COMMANDS = (
    re.compile(r"\brm\s+-[rRfF]", re.IGNORECASE),
    re.compile(r"\bRemove-Item\b", re.IGNORECASE),
    re.compile(r"\bgit\s+(?:push|rebase|reset\s+--hard)\b", re.IGNORECASE),
    re.compile(r"\bgit\s+clean\s+-[fFdDxX]", re.IGNORECASE),
    re.compile(r"\b(?:DROP\s+(?:TABLE|DATABASE)|ALTER\s+TABLE)\b", re.IGNORECASE),
    re.compile(r"\b(?:npm|pnpm|yarn)\s+(?:install|add)\s+(?:-g|--global)\b", re.IGNORECASE),
)

SECRET_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN .*PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}"),
    re.compile(r"(?i)\bpassword\s*[:=]\s*[^\s（(]{4,}"),
    re.compile(r"(?m)^[A-Z][A-Z0-9_]{2,}=[^\s（(]{8,}$"),
)

CONFIDENCE_RE = re.compile(r"\[(?:CONFIRMED|REPORTED|INFERRED|UNKNOWN)\]")


def section_body(text, heading):
    match = re.search(
        r"^## " + re.escape(heading) + r"\s*$\n(.*?)(?=^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else ""


def first_action(body):
    match = re.search(r"^\s*1\.\s+(.+?)\s*$", body, re.MULTILINE)
    return match.group(1).strip() if match else ""


def content_units(text):
    latin = len(re.findall(r"[A-Za-z0-9_]+(?:[-'][A-Za-z0-9_]+)*", text))
    cjk = len(re.findall(r"[\u3400-\u9fff]", text))
    return latin + cjk


def validate(text):
    errors = []
    warnings = []

    for heading in HEADINGS:
        count = len(re.findall(r"^## " + re.escape(heading) + r"\s*$", text, re.MULTILINE))
        if count != 1:
            errors.append("section must appear exactly once: ## {}".format(heading))
        elif not section_body(text, heading):
            errors.append("empty section: ## {}".format(heading))

    for pattern in PLACEHOLDER_PATTERNS:
        hit = pattern.search(text)
        if hit:
            errors.append("unresolved placeholder: {!r}".format(hit.group(0)))

    for marker in TEMPLATE_MARKERS:
        if marker in text:
            errors.append("unfilled template boilerplate: {!r}".format(marker))
            break

    next_body = section_body(text, "下一步")
    action = first_action(next_body)
    if not action:
        errors.append("Next actions must start with a numbered item 1")
    else:
        for pattern in DANGEROUS_COMMANDS:
            if pattern.search(action):
                errors.append("first action contains a destructive command: {}".format(pattern.pattern))
                break

    for pattern in SECRET_PATTERNS:
        hit = pattern.search(text)
        if hit:
            errors.append("possible secret material present: {!r}".format(hit.group(0)[:24]))
            break

    constraints = section_body(text, "约束与风险")
    missing = [verb for verb in RED_VERBS if verb not in constraints]
    if missing:
        errors.append("approval boundary missing verb categories: {}".format(", ".join(missing)))
    if RECONFIRM not in constraints:
        errors.append("approval boundary must state current-session reconfirmation")

    partial = re.search(r'^coverage:\s*"?PARTIAL"?', text, re.MULTILINE)
    if partial and "已知遗漏" not in section_body(text, "待完成事项"):
        errors.append("PARTIAL coverage requires a known-omissions entry")

    units = content_units(text)
    if units > 2500:
        warnings.append("packet is long ({} estimated units; target <= 2500)".format(units))
    elif units < 180:
        warnings.append("packet is unusually short ({} estimated units)".format(units))

    generated = re.search(r'^generated:\s*"?(\d{4}-\d{2}-\d{2})"?', text, re.MULTILINE)
    if generated:
        try:
            made = date.fromisoformat(generated.group(1))
            age = (date.today() - made).days
            if age > 30:
                warnings.append("STALE: revalidate branch, tests and external state")
            elif age > 7:
                warnings.append("AGING: revalidate drift-prone state")
        except ValueError:
            warnings.append("generated date is not a valid ISO date")
    else:
        warnings.append("no generated date found")

    if not CONFIDENCE_RE.search(section_body(text, "当前目标")):
        warnings.append("current goal has no confidence label")

    return errors, warnings


def main():
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path, help="UTF-8 Markdown handoff packet")
    args = parser.parse_args()

    try:
        text = read_text(args.packet)
    except (OSError, UnicodeError) as exc:
        print("ERROR: cannot read UTF-8 packet: {}".format(exc))
        return 2

    errors, warnings = validate(text)
    for item in errors:
        print("ERROR: " + item)
    for item in warnings:
        print("WARNING: " + item)
    if errors:
        print("FAIL: {} error(s), {} warning(s)".format(len(errors), len(warnings)))
        return 1
    print("PASS: 0 errors, {} warning(s)".format(len(warnings)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
