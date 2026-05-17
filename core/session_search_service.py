from __future__ import annotations

import json
from typing import Any

from core.memory import sanitize_ltm_summary


def search_session_records(args: dict[str, Any], memory_db: Any | None = None) -> dict[str, Any]:
    """Search OpsCore session messages with a bounded read-only scan."""
    query = str(args.get("query") or args.get("q") or args.get("text") or "").strip()
    if not query:
        return {"status": "ERROR", "error": "session_search requires query."}

    try:
        limit = max(1, min(int(args.get("limit") or args.get("max_results") or args.get("max_sessions") or 5), 20))
    except (TypeError, ValueError):
        limit = 5
    try:
        scan_limit = max(limit, min(int(args.get("scan_limit") or 1000), 5000))
    except (TypeError, ValueError):
        scan_limit = 1000

    session_id = str(args.get("session_id") or "").strip()
    include_run_trace = bool(args.get("include_run_trace", True))

    db = memory_db or _default_memory_db()
    rows = _fetch_candidate_rows(db, session_id=session_id, limit=scan_limit)
    results = _match_rows(rows, query=query, include_run_trace=include_run_trace, limit=limit)
    return {
        "status": "SUCCESS",
        "query": query,
        "result_count": len(results),
        "results": results,
        "hint": "这是只读会话搜索结果；采用前必须结合当前资产实时工具结果验证。",
    }


def _default_memory_db() -> Any:
    from core.memory import memory_db

    return memory_db


def _fetch_candidate_rows(memory_db: Any, *, session_id: str, limit: int) -> list[dict[str, Any]]:
    connect = getattr(memory_db, "_connect", None)
    lock = getattr(memory_db, "_db_lock", None)
    if not callable(connect):
        return _fetch_via_get_messages(memory_db, session_id=session_id, limit=limit)

    rows: list[dict[str, Any]] = []
    with lock if lock is not None else _null_lock():
        with connect() as conn:
            cursor = conn.cursor()
            if session_id:
                cursor.execute(
                    """
                    SELECT id, session_id, message_json, timestamp
                    FROM memory
                    WHERE session_id = ? AND is_compressed = 0
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (session_id, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, session_id, message_json, timestamp
                    FROM memory
                    WHERE is_compressed = 0
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
            for row in cursor.fetchall():
                rows.append({"id": row[0], "session_id": row[1], "message_json": row[2], "created_at": row[3]})
    return rows


def _fetch_via_get_messages(memory_db: Any, *, session_id: str, limit: int) -> list[dict[str, Any]]:
    if not session_id or not hasattr(memory_db, "get_messages"):
        return []
    rows = []
    for msg in memory_db.get_messages(session_id, for_ui=True, limit=limit):
        rows.append({"id": msg.get("_memory_id") or msg.get("id"), "session_id": session_id, "message": msg, "created_at": msg.get("created_at")})
    return rows


class _null_lock:
    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


def _match_rows(rows: list[dict[str, Any]], *, query: str, include_run_trace: bool, limit: int) -> list[dict[str, Any]]:
    query_lower = query.lower()
    results: list[dict[str, Any]] = []
    for row in rows:
        msg = row.get("message") or _loads(row.get("message_json"))
        if not isinstance(msg, dict):
            continue
        if msg.get("memory_type") == "aiops_run_trace" and not include_run_trace:
            continue
        searchable = json.dumps(msg, ensure_ascii=False, default=str).lower()
        if query_lower not in searchable:
            continue
        results.append(_result_from_message(row, msg, query=query))
        if len(results) >= limit:
            break
    return results


def _loads(raw: Any) -> dict[str, Any] | None:
    try:
        parsed = json.loads(str(raw or "{}"))
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def _result_from_message(row: dict[str, Any], msg: dict[str, Any], *, query: str) -> dict[str, Any]:
    traces = msg.get("exec_trace") or msg.get("execTrace") or []
    if not isinstance(traces, list):
        traces = []
    memory_type = str(msg.get("memory_type") or "").strip()
    match_type = "run_trace" if memory_type == "aiops_run_trace" else ("tool_evidence" if traces else "conversation")
    return {
        "session_id": row.get("session_id") or msg.get("session_id") or "",
        "message_id": row.get("id") or msg.get("_memory_id") or msg.get("id"),
        "created_at": row.get("created_at") or msg.get("created_at") or msg.get("timestamp"),
        "role": msg.get("role") or "",
        "match_type": match_type,
        "memory_type": memory_type,
        "preview": _preview(msg, query=query),
        "run_id": msg.get("run_id") or (msg.get("run_event_payload") or {}).get("run_id") if isinstance(msg.get("run_event_payload"), dict) else msg.get("run_id"),
        "evidence_refs": _evidence_refs(traces),
    }


def _preview(msg: dict[str, Any], *, query: str) -> str:
    text = str(msg.get("content") or msg.get("summary") or "").strip()
    if not text:
        text = json.dumps(msg, ensure_ascii=False, default=str)
    lower = text.lower()
    pos = lower.find(query.lower())
    if pos >= 0:
        start = max(0, pos - 80)
        end = min(len(text), pos + len(query) + 160)
        text = text[start:end]
        if start > 0:
            text = "..." + text
        if end < len(lower):
            text = text + "..."
    return sanitize_ltm_summary(text, max_chars=260)


def _evidence_refs(traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for trace in traces:
        if not isinstance(trace, dict):
            continue
        evidence = trace.get("evidence") if isinstance(trace.get("evidence"), dict) else {}
        result_meta = trace.get("resultMeta") if isinstance(trace.get("resultMeta"), dict) else {}
        evidence_id = evidence.get("evidence_id") or result_meta.get("evidence_id")
        tool = trace.get("tool") or trace.get("name")
        if evidence_id or tool:
            refs.append({"id": evidence_id or "", "tool": tool or "", "status": trace.get("status") or ""})
        if len(refs) >= 5:
            break
    return refs
