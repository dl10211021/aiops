from __future__ import annotations

import datetime as dt
import asyncio
import json
import logging
import os
import sqlite3
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from core.tool_trace_policy import (
    policy_summary,
    trace_evidence_id,
    trace_sql_action_summary,
    trace_tool_policy,
)


DEFAULT_RETENTION_INTERVAL_SECONDS = 24 * 60 * 60
RETENTION_RUN_HISTORY_LIMIT = 50


@dataclass(frozen=True)
class SessionRetentionPolicy:
    enabled: bool = True
    raw_result_days: int = 30
    compressed_history_days: int = 180
    audit_metadata_days: int = 365
    max_result_chars: int = 2000
    preview_chars: int = 1200


def session_retention_policy_from_env(env: Mapping[str, str] | None = None) -> SessionRetentionPolicy:
    env = env or os.environ
    return SessionRetentionPolicy(
        enabled=_bool_env(env, "OPSCORE_SESSION_RETENTION_ENABLED", True),
        raw_result_days=_int_env(env, "OPSCORE_RETENTION_RAW_RESULT_DAYS", 30),
        compressed_history_days=_int_env(env, "OPSCORE_RETENTION_COMPRESSED_HISTORY_DAYS", 180),
        audit_metadata_days=_int_env(env, "OPSCORE_RETENTION_AUDIT_METADATA_DAYS", 365),
        max_result_chars=_int_env(env, "OPSCORE_RETENTION_MAX_RESULT_CHARS", 2000),
        preview_chars=_int_env(env, "OPSCORE_RETENTION_PREVIEW_CHARS", 1200),
    )


def session_retention_interval_seconds(env: Mapping[str, str] | None = None) -> int:
    env = env or os.environ
    return max(300, _int_env(env, "OPSCORE_SESSION_RETENTION_INTERVAL_SECONDS", DEFAULT_RETENTION_INTERVAL_SECONDS))


def apply_session_retention(
    conn: sqlite3.Connection,
    *,
    policy: SessionRetentionPolicy | None = None,
    now: dt.datetime | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    policy = policy or session_retention_policy_from_env()
    started_at = now or dt.datetime.now()
    now = started_at
    stats: dict[str, Any] = {
        "policy": asdict(policy),
        "enabled": policy.enabled,
        "dry_run": dry_run,
        "started_at": _format_datetime(started_at),
        "rows_scanned": 0,
        "rows_compacted": 0,
        "rows_deleted": 0,
        "audit_rows_inserted": 0,
        "audit_rows_deleted": 0,
    }
    if not policy.enabled:
        return stats

    _ensure_retention_tables(conn)
    old_audit_ids = _old_audit_row_ids(conn, policy=policy, now=now)
    candidate_cutoff = _candidate_cutoff_timestamp(policy, now)
    rows = conn.execute(
        """
        SELECT id, session_id, message_json, is_compressed, timestamp
        FROM memory
        WHERE timestamp <= ?
        ORDER BY id ASC
        """,
        (candidate_cutoff,),
    ).fetchall()
    stats["rows_scanned"] = len(rows)

    compacted_updates: list[tuple[str, int]] = []
    delete_ids: list[int] = []
    audit_rows: list[tuple[Any, ...]] = []
    for row in rows:
        row_id, session_id, message_json, is_compressed, timestamp = row
        age_days = _age_days(timestamp, now)
        if age_days is None:
            continue
        try:
            message = json.loads(message_json)
        except Exception:
            continue
        if not isinstance(message, dict):
            continue

        if age_days >= policy.raw_result_days:
            compacted = _compact_message_results(message, policy=policy, now=now)
            if compacted:
                compacted_updates.append((json.dumps(message, ensure_ascii=False), row_id))

        if age_days >= policy.compressed_history_days and int(is_compressed or 0) == 1:
            delete_ids.append(row_id)
            audit_rows.append(
                (
                    session_id,
                    row_id,
                    str(message.get("role") or ""),
                    str(timestamp or ""),
                    "delete_compressed_history",
                    _message_audit_summary(message, policy.preview_chars),
                )
            )

    stats["rows_compacted"] = len(compacted_updates)
    stats["rows_deleted"] = len(delete_ids)
    stats["audit_rows_inserted"] = len(audit_rows)
    stats["audit_rows_deleted"] = len(old_audit_ids)
    completed_at = dt.datetime.now()
    stats["completed_at"] = _format_datetime(completed_at)
    stats["duration_ms"] = int((completed_at - started_at).total_seconds() * 1000)
    stats["status"] = "completed"

    if not dry_run:
        conn.executemany(
            "UPDATE memory SET message_json = ? WHERE id = ?",
            compacted_updates,
        )
        if audit_rows:
            conn.executemany(
                """
                INSERT INTO session_retention_audit (
                    session_id, message_id, role, original_timestamp, action, summary
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                audit_rows,
            )
        if delete_ids:
            conn.executemany("DELETE FROM memory WHERE id = ?", [(row_id,) for row_id in delete_ids])
        if old_audit_ids:
            conn.executemany(
                "DELETE FROM session_retention_audit WHERE id = ?",
                [(row_id,) for row_id in old_audit_ids],
            )
        _record_retention_run(conn, stats, status="completed")
        conn.commit()
    return stats


def latest_session_retention_status(
    conn: sqlite3.Connection,
    *,
    interval_seconds: int | None = None,
) -> dict[str, Any]:
    _ensure_retention_tables(conn)
    interval = int(interval_seconds or session_retention_interval_seconds())
    status: dict[str, Any] = {
        "last_run": None,
        "next_run_at": None,
        "interval_seconds": interval,
    }
    row = conn.execute(
        """
        SELECT started_at, completed_at, status, rows_scanned, rows_compacted,
               rows_deleted, audit_rows_deleted, stats_json
        FROM session_retention_runs
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()
    if not row:
        return status

    (
        started_at,
        completed_at,
        run_status,
        rows_scanned,
        rows_compacted,
        rows_deleted,
        audit_rows_deleted,
        stats_json,
    ) = row
    try:
        last_run = json.loads(stats_json or "{}")
    except Exception:
        last_run = {}
    last_run.update(
        {
            "started_at": str(started_at or ""),
            "completed_at": str(completed_at or ""),
            "status": str(run_status or ""),
            "rows_scanned": int(rows_scanned or 0),
            "rows_compacted": int(rows_compacted or 0),
            "rows_deleted": int(rows_deleted or 0),
            "audit_rows_deleted": int(audit_rows_deleted or 0),
            "dry_run": False,
        }
    )
    status["last_run"] = last_run
    completed_dt = _parse_timestamp(completed_at)
    if completed_dt:
        status["next_run_at"] = _format_datetime(completed_dt + dt.timedelta(seconds=interval))
    return status


async def run_session_retention_maintenance(memory_db: Any | None = None) -> dict[str, Any]:
    if memory_db is None:
        from core.memory import memory_db as default_memory_db

        memory_db = default_memory_db
    return await asyncio.to_thread(memory_db.apply_session_retention)


async def session_retention_maintenance_loop(
    *,
    interval_seconds: int | None = None,
    runner: Any = run_session_retention_maintenance,
    sleep: Any = asyncio.sleep,
    logger: logging.Logger | None = None,
    max_runs: int | None = None,
) -> None:
    logger = logger or logging.getLogger(__name__)
    interval = interval_seconds if interval_seconds is not None else session_retention_interval_seconds()
    interval = max(1, int(interval))
    runs = 0
    while max_runs is None or runs < max_runs:
        try:
            result = await runner()
            logger.info(
                "Session retention maintenance completed: scanned=%s compacted=%s deleted=%s audit_deleted=%s",
                result.get("rows_scanned"),
                result.get("rows_compacted"),
                result.get("rows_deleted"),
                result.get("audit_rows_deleted"),
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Session retention maintenance failed.")
        runs += 1
        if max_runs is not None and runs >= max_runs:
            break
        await sleep(interval)


def _bool_env(env: Mapping[str, str], key: str, default: bool) -> bool:
    raw = str(env.get(key, "")).strip().lower()
    if not raw:
        return default
    return raw not in {"0", "false", "no", "off", "disabled"}


def _int_env(env: Mapping[str, str], key: str, default: int) -> int:
    try:
        value = int(str(env.get(key, "")).strip())
    except Exception:
        return default
    return max(0, value)


def _ensure_retention_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS session_retention_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            message_id INTEGER NOT NULL,
            role TEXT,
            original_timestamp DATETIME,
            action TEXT NOT NULL,
            summary TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS session_retention_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at DATETIME NOT NULL,
            completed_at DATETIME NOT NULL,
            status TEXT NOT NULL,
            rows_scanned INTEGER DEFAULT 0,
            rows_compacted INTEGER DEFAULT 0,
            rows_deleted INTEGER DEFAULT 0,
            audit_rows_deleted INTEGER DEFAULT 0,
            stats_json TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_memory_retention_timestamp_compressed ON memory(timestamp, is_compressed)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_session_retention_audit_created_at ON session_retention_audit(created_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_session_retention_runs_completed_at ON session_retention_runs(completed_at)"
    )


def _candidate_cutoff_timestamp(policy: SessionRetentionPolicy, now: dt.datetime) -> str:
    candidate_days = max(0, min(policy.raw_result_days, policy.compressed_history_days))
    return _format_datetime(now - dt.timedelta(days=candidate_days))


def _old_audit_row_ids(
    conn: sqlite3.Connection,
    *,
    policy: SessionRetentionPolicy,
    now: dt.datetime,
) -> list[int]:
    if policy.audit_metadata_days <= 0:
        return []
    cutoff = _format_datetime(now - dt.timedelta(days=policy.audit_metadata_days))
    rows = conn.execute(
        "SELECT id FROM session_retention_audit WHERE created_at <= ? ORDER BY id ASC",
        (cutoff,),
    ).fetchall()
    return [int(row_id) for (row_id,) in rows]


def _record_retention_run(conn: sqlite3.Connection, stats: dict[str, Any], *, status: str) -> None:
    payload = {**stats, "status": status}
    conn.execute(
        """
        INSERT INTO session_retention_runs (
            started_at, completed_at, status, rows_scanned, rows_compacted,
            rows_deleted, audit_rows_deleted, stats_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.get("started_at") or _format_datetime(dt.datetime.now()),
            payload.get("completed_at") or _format_datetime(dt.datetime.now()),
            status,
            int(payload.get("rows_scanned") or 0),
            int(payload.get("rows_compacted") or 0),
            int(payload.get("rows_deleted") or 0),
            int(payload.get("audit_rows_deleted") or 0),
            json.dumps(payload, ensure_ascii=False),
        ),
    )
    conn.execute(
        """
        DELETE FROM session_retention_runs
        WHERE id NOT IN (
            SELECT id FROM session_retention_runs
            ORDER BY id DESC
            LIMIT ?
        )
        """,
        (RETENTION_RUN_HISTORY_LIMIT,),
    )


def _parse_timestamp(value: Any) -> dt.datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return dt.datetime.strptime(text[:19], fmt)
        except ValueError:
            continue
    return None


def _format_datetime(value: dt.datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _age_days(timestamp: Any, now: dt.datetime) -> int | None:
    created = _parse_timestamp(timestamp)
    if not created:
        return None
    return max(0, (now - created).days)


def _compact_message_results(
    message: dict[str, Any],
    *,
    policy: SessionRetentionPolicy,
    now: dt.datetime,
) -> bool:
    changed = False
    if message.get("role") == "tool" and not message.get("retention_compacted"):
        raw = str(message.get("content") or "")
        if raw:
            message["content"] = json.dumps(
                _retention_summary_payload(raw, policy=policy, now=now),
                ensure_ascii=False,
            )
            message["retention_compacted"] = True
            changed = True

    traces = message.get("exec_trace") or message.get("execTrace")
    if isinstance(traces, list):
        for trace in traces:
            if not isinstance(trace, dict) or trace.get("result_retention") == "summary_after_30_days":
                continue
            raw_result = str(trace.get("result") or "")
            if not raw_result:
                continue
            trace["result"] = json.dumps(
                _retention_summary_payload(raw_result, policy=policy, now=now),
                ensure_ascii=False,
            )
            trace["result_retention"] = "summary_after_30_days"
            trace["original_result_chars"] = len(raw_result)
            changed = True
    return changed


def _retention_summary_payload(
    raw: str,
    *,
    policy: SessionRetentionPolicy,
    now: dt.datetime,
) -> dict[str, Any]:
    summary = summarize_tool_result(raw, max_chars=policy.preview_chars)
    return {
        "retention_compacted": True,
        "retention_tier": "result_summary",
        "retention_note": f"完整工具结果已按 {policy.raw_result_days} 天策略摘要化；命令/SQL 保留在执行链路中。",
        "compacted_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "original_chars": len(raw),
        "summary": summary,
    }


def summarize_tool_result(raw: str, *, max_chars: int = 1200) -> str:
    text = str(raw or "")
    try:
        parsed = json.loads(text)
    except Exception:
        return _truncate(text, max_chars)
    if not isinstance(parsed, dict):
        return _truncate(text, max_chars)

    summary: dict[str, Any] = {}
    for key in (
        "success",
        "status",
        "exit_status",
        "statement_type",
        "committed",
        "count",
        "has_result_set",
        "has_error",
        "error_type",
        "error",
        "message",
        "tool_policy",
    ):
        if key in parsed:
            summary[key] = parsed[key]

    for key in ("output", "stdout", "stderr", "result", "data"):
        if key not in parsed:
            continue
        summary[f"{key}_preview"] = _value_preview(parsed[key], max_chars=max_chars)
        break
    return _truncate(json.dumps(summary or parsed, ensure_ascii=False), max_chars)


def _value_preview(value: Any, *, max_chars: int) -> Any:
    if isinstance(value, str):
        return _truncate(value, max_chars)
    if isinstance(value, list):
        return {
            "type": "list",
            "count": len(value),
            "sample": value[:3],
        }
    if isinstance(value, dict):
        return {
            "type": "object",
            "keys": list(value.keys())[:20],
            "sample": _truncate(json.dumps(value, ensure_ascii=False), max_chars),
        }
    return value


def _message_audit_summary(message: dict[str, Any], max_chars: int) -> str:
    content = str(message.get("content") or "")
    traces = message.get("exec_trace") or message.get("execTrace") or []
    tool_names = []
    evidence_ids = []
    policy_bits = []
    sql_actions = []
    if isinstance(traces, list):
        for trace in traces:
            if not isinstance(trace, dict):
                continue
            tool_names.append(str(trace.get("tool") or ""))
            evidence_id = trace_evidence_id(trace)
            if evidence_id:
                evidence_ids.append(evidence_id)
            policy = trace_tool_policy(trace, fallback_to_registry=False)
            if policy:
                policy_bits.append(policy_summary(policy))
            sql_action = trace_sql_action_summary(trace)
            if sql_action:
                sql_actions.append(sql_action)
    parts = [
        f"role={message.get('role') or ''}",
        f"tools={','.join([name for name in tool_names if name]) or '-'}",
        f"evidence={','.join(evidence_ids) or '-'}",
        f"policy={';'.join(policy_bits) or '-'}",
        f"sql_action={';'.join(sql_actions) or '-'}",
        f"content={_truncate(content, max_chars)}",
    ]
    return "\n".join(parts)


def _truncate(value: str, max_chars: int) -> str:
    text = str(value or "")
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n...[retention truncated]"
