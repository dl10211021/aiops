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
SAFETY_APPROVAL_QUALIFIED_PATTERN = re.compile(r"\bcore\.safety_policy\.check_approval_needed\s*\(")
POLICY_WRAPPER = "execute_with_runtime_policy"
WRAPPER_LOOKBACK_LINES = 8


def _normalize(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def runtime_policy_coverage_issues_for_text(rel_path: str, text: str) -> list[str]:
    issues: list[str] = []
    issues.extend(approval_policy_coverage_issues_for_text(rel_path, text))
    if not ROUTE_EXECUTION_PATTERN.search(text):
        return issues
    if rel_path not in ALLOWED_EXECUTION_FILES:
        issues.append(f"{rel_path}: route_and_execute call is not on the reviewed execution allowlist")
        return issues

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


def approval_policy_coverage_issues_for_text(rel_path: str, text: str) -> list[str]:
    if rel_path == "core/dispatcher.py":
        return []
    issues: list[str] = []
    if _imports_safety_policy_approval(text):
        issues.append(
            f"{rel_path}: import dispatcher.check_approval_needed instead of core.safety_policy.check_approval_needed"
        )
    if SAFETY_APPROVAL_QUALIFIED_PATTERN.search(text):
        issues.append(
            f"{rel_path}: call dispatcher.check_approval_needed instead of core.safety_policy.check_approval_needed"
        )
    return issues


def _imports_safety_policy_approval(text: str) -> bool:
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line.startswith("from core.safety_policy import"):
            index += 1
            continue
        import_text = line
        while import_text.count("(") > import_text.count(")") and index + 1 < len(lines):
            index += 1
            import_text += "\n" + lines[index].strip()
        if re.search(r"\bcheck_approval_needed\b", import_text):
            return True
        index += 1
    return False


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
