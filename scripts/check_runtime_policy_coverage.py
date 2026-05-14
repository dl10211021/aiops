#!/usr/bin/env python
"""Fail when production tool execution bypasses runtime policy wrappers."""

from __future__ import annotations

import ast
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
POLICY_WRAPPER = "execute_with_runtime_policy"


def _normalize(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def runtime_policy_coverage_issues_for_text(rel_path: str, text: str) -> list[str]:
    issues: list[str] = []
    tree = _parse_source(rel_path, text)
    if isinstance(tree, str):
        return [tree]

    issues.extend(approval_policy_coverage_issues_for_tree(rel_path, tree))

    route_calls = _route_and_execute_calls(tree)
    if not route_calls:
        return issues
    if rel_path not in ALLOWED_EXECUTION_FILES:
        issues.append(f"{rel_path}: route_and_execute call is not on the reviewed execution allowlist")
        return issues

    parents = _parent_map(tree)
    for call in route_calls:
        if not _has_policy_wrapper_ancestor(call, parents):
            issues.append(
                f"{rel_path}:{call.lineno}: route_and_execute call is not wrapped by {POLICY_WRAPPER}"
            )
    return issues


def approval_policy_coverage_issues_for_text(rel_path: str, text: str) -> list[str]:
    if rel_path == "core/dispatcher.py":
        return []
    tree = _parse_source(rel_path, text)
    if isinstance(tree, str):
        return [tree]
    return approval_policy_coverage_issues_for_tree(rel_path, tree)


def approval_policy_coverage_issues_for_tree(rel_path: str, tree: ast.AST) -> list[str]:
    if rel_path == "core/dispatcher.py":
        return []

    issues: list[str] = []
    aliases = _safety_policy_aliases(tree)

    if _imports_safety_policy_approval(tree):
        issues.append(
            f"{rel_path}: import dispatcher.check_approval_needed instead of core.safety_policy.check_approval_needed"
        )
    if _calls_safety_policy_approval(tree, aliases):
        issues.append(
            f"{rel_path}: call dispatcher.check_approval_needed instead of core.safety_policy.check_approval_needed"
        )
    return issues


def _parse_source(rel_path: str, text: str) -> ast.AST | str:
    try:
        return ast.parse(text)
    except SyntaxError as exc:
        return f"{rel_path}: unable to parse Python source for runtime policy coverage: {exc.msg}"


def _parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    return {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}


def _route_and_execute_calls(tree: ast.AST) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _call_name(node.func).endswith("route_and_execute")
    ]


def _has_policy_wrapper_ancestor(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
    current = parents.get(node)
    while current is not None:
        if isinstance(current, ast.Call) and _call_name(current.func).endswith(POLICY_WRAPPER):
            return True
        current = parents.get(current)
    return False


def _imports_safety_policy_approval(tree: ast.AST) -> bool:
    return any(
        isinstance(node, ast.ImportFrom)
        and node.module == "core.safety_policy"
        and any(alias.name == "check_approval_needed" for alias in node.names)
        for node in ast.walk(tree)
    )


def _safety_policy_aliases(tree: ast.AST) -> set[str]:
    aliases: set[str] = {"core.safety_policy", "safety_policy"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "core.safety_policy":
                    aliases.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module == "core":
            for alias in node.names:
                if alias.name == "safety_policy":
                    aliases.add(alias.asname or alias.name)
    return aliases


def _calls_safety_policy_approval(tree: ast.AST, aliases: set[str]) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node.func)
        if name == "core.safety_policy.check_approval_needed":
            return True
        if name.endswith(".check_approval_needed") and name.rsplit(".", 1)[0] in aliases:
            return True
    return False


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


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
