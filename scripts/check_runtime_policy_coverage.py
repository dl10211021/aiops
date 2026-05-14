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


def _normalize(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def find_runtime_policy_coverage_issues() -> list[str]:
    issues: list[str] = []
    call_pattern = re.compile(r"\broute_and_execute\s*\(")

    for root in SCAN_ROOTS:
        for path in (ROOT / root).rglob("*.py"):
            rel_path = _normalize(path)
            if rel_path in SKIPPED_FILES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if not call_pattern.search(text):
                continue
            if rel_path not in ALLOWED_EXECUTION_FILES:
                issues.append(f"{rel_path}: route_and_execute call is not on the reviewed execution allowlist")
                continue
            if "execute_with_runtime_policy" not in text:
                issues.append(f"{rel_path}: route_and_execute call is not wrapped by execute_with_runtime_policy")

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
