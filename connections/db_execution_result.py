"""Shared database execution result helpers."""

from __future__ import annotations

from typing import Any


def statement_type(sql: str) -> str:
    root = str(sql or "").strip().split(None, 1)[0].lower()
    return root or "unknown"


def should_commit_after_statement(sql: str) -> bool:
    root = statement_type(sql)
    return bool(root) and root not in {
        "select",
        "show",
        "describe",
        "desc",
        "explain",
        "with",
        "commit",
        "rollback",
    }


def commit_if_needed(conn: Any, sql: str) -> None:
    if not should_commit_after_statement(sql):
        return
    commit = getattr(conn, "commit", None)
    if callable(commit):
        commit()


def query_success(sql: str, rows: list[Any], data: list[Any] | None = None) -> dict:
    return {
        "success": True,
        "has_result_set": True,
        "statement_type": statement_type(sql),
        "committed": False,
        "count": len(rows),
        "data": data if data is not None else rows,
    }


def statement_success(conn: Any, cursor: Any, sql: str) -> dict:
    should_commit = should_commit_after_statement(sql)
    if should_commit:
        commit_if_needed(conn, sql)
    affected_rows = getattr(cursor, "rowcount", -1)
    root = statement_type(sql)
    return {
        "success": True,
        "has_result_set": False,
        "statement_type": root,
        "committed": should_commit,
        "affected_rows": affected_rows,
        "message": f"{root.upper()} 已执行" + ("并提交" if should_commit else ""),
        "data": [],
    }
