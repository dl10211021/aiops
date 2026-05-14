#!/usr/bin/env python
"""Fail when production tool execution bypasses runtime policy wrappers."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SCAN_ROOTS = ("core", "api", "connections")
ALLOWED_EXECUTION_FILES = {
    "core/agent_headless_loop.py",
    "core/agent_tool_loop.py",
    "core/legacy_command_service.py",
}
SKIPPED_FILES = {
    "core/dispatcher.py",
}
ROUTE_EXECUTION_PATTERN = re.compile(r"\broute_and_execute\s*\(")
POLICY_WRAPPER = "execute_with_runtime_policy"
WRAPPER_LOOKBACK_LINES = 8


def _normalize(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def runtime_policy_coverage_issues_for_text(rel_path: str, text: str) -> list[str]:
    if not ROUTE_EXECUTION_PATTERN.search(text):
        return []
    if rel_path not in ALLOWED_EXECUTION_FILES:
        return [f"{rel_path}: route_and_execute call is not on the reviewed execution allowlist"]

    issues: list[str] = []
    lines = text.splitlines()
    for line_number, line in enumerate(lines, start=1):
        if not ROUTE_EXECUTION_PATTERN.search(line):
            continue
        start = max(0, line_number - WRAPPER_LOOKBACK_LINES - 1)
        context = "\n".join(lines[start:line_number])
        if POLICY_WRAPPER not in context:
            issues.append(
                f"{rel_path}:{line_number}: route_and_execute call is not wrapped by {POLICY_WRAPPER}"
            )
    return issues


def find_runtime_policy_coverage_issues() -> list[str]:
    issues: list[str] = []

    for root in SCAN_ROOTS:
        for path in (ROOT / root).rglob("*.py"):
            rel_path = _normalize(path)
            if rel_path in SKIPPED_FILES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            issues.extend(runtime_policy_coverage_issues_for_text(rel_path, text))

    return issues


def main() -> int:
    issues = find_runtime_policy_coverage_issues()
    if issues:
        print("runtime policy coverage validation failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("runtime policy coverage validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
