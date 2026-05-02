from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Mapping, MutableMapping
from typing import Any, Awaitable

from core.alert_events import create_alert_event


logger = logging.getLogger(__name__)


NO_ACTIVE_ALERT_MESSAGE = "告警已接收，但目前无人值守，已记录日志。"
ACTIVE_ALERT_MESSAGE_TEMPLATE = "告警已成功推送到 {count} 个值班中的 AI 大脑中，并已唤醒 AI 进行排查！"


def affected_alert_sessions(active_sessions: Mapping[str, dict], host: str) -> list[str]:
    affected: list[str] = []
    for session_id, session_data in list(active_sessions.items()):
        info = session_data.get("info", {})
        if info.get("host") == host or host == "all" or info.get("host") == "localhost":
            affected.append(session_id)
    return affected


def build_alert_injection_message(alert_event: dict[str, Any]) -> str:
    severity = alert_event["severity"]
    alert_name = alert_event["alert_name"]
    host = alert_event["host"]
    description = alert_event["description"]
    return (
        f"🔔 【监控告警接入】外部系统触发了级别为 [{str(severity).upper()}] 的告警。\n"
        f"**告警名称**：{alert_name}\n"
        f"**故障节点**：{host}\n"
        f"**详细信息**：\n{description}\n\n"
        "作为监控专家，请主动分析此告警。如果你是负责整个环境的指挥官（例如你的连接是 localhost），"
        "请使用 `list_active_sessions` 查找合适的子节点并使用 `dispatch_sub_agents` 派发调查任务；"
        "如果你是具体服务器的节点 Agent，请立刻调用技能/工具去探查根因！"
    )


async def read_alert_webhook_payload(json_reader: Callable[[], Awaitable[Any]]) -> Any:
    try:
        return await json_reader()
    except (ValueError, TypeError):
        return {}


async def handle_alert_webhook(
    payload: dict[str, Any],
    active_sessions: MutableMapping[str, dict],
    session_locks: MutableMapping[str, asyncio.Lock],
    memory_db,
    dispatcher,
    heartbeat_runner: Callable[..., Awaitable[Any]],
    *,
    task_factory: Callable[[Awaitable[Any]], Any] = asyncio.create_task,
) -> dict[str, Any]:
    alert_event = create_alert_event(payload)
    host = alert_event["host"]
    alert_name = alert_event["alert_name"]
    severity = alert_event["severity"]

    logger.info(
        "Webhook alert received: host=%s alert=%s severity=%s keys=%s",
        host,
        alert_name,
        payload.get("severity") or payload.get("priority") or payload.get("status") or "",
        sorted(list(payload.keys()))[:20],
    )
    logger.info("Parsed Alert -> Host: %s, Name: %s, Severity: %s", host, alert_name, severity)

    affected_sessions = affected_alert_sessions(active_sessions, host)
    if not affected_sessions:
        logger.warning("Alert received but no active AI session is connected to %s or localhost.", host)
        return {
            "message": NO_ACTIVE_ALERT_MESSAGE,
            "data": {"alert": alert_event, "injected_count": 0},
        }

    injection_message = build_alert_injection_message(alert_event)
    injected_count = 0
    for session_id in affected_sessions:
        info = active_sessions[session_id].get("info", {})
        lock = session_locks.setdefault(session_id, asyncio.Lock())
        async with lock:
            if info.get("heartbeat_in_progress"):
                memory_db.append_message(session_id, {"role": "user", "content": injection_message})
                logger.info("Session %s is busy, appended alert to context only.", session_id)
            else:
                info["heartbeat_in_progress"] = True
                logger.info("Actively triggering background AI task for session %s due to alert.", session_id)
                task_factory(
                    heartbeat_runner(
                        session_id,
                        info,
                        memory_db,
                        dispatcher,
                        trigger_msg=injection_message,
                    )
                )
        injected_count += 1

    return {
        "message": ACTIVE_ALERT_MESSAGE_TEMPLATE.format(count=injected_count),
        "data": {"alert": alert_event, "injected_count": injected_count},
    }
