from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Callable, Mapping, MutableMapping
from typing import Any, Awaitable

from core import dispatcher as dispatcher_module
from core import heartbeat as heartbeat_module
from core import memory as memory_module
from core.alert_events import create_alert_events
from core.notification_config import build_notification_channel_statuses


logger = logging.getLogger(__name__)


NO_ACTIVE_ALERT_MESSAGE = "告警已接收，但目前无人值守，已记录日志。"
RECORD_ONLY_ALERT_MESSAGE = "告警已接收，按降噪策略仅记录，不自动启动 AI。"
ACTIVE_ALERT_MESSAGE_TEMPLATE = "告警已成功推送到 {count} 个值班中的 AI 大脑中，并已唤醒 AI 进行排查！"


def _resolve_memory_db(memory_db: Any | None = None) -> Any:
    return memory_db if memory_db is not None else memory_module.memory_db


def _resolve_dispatcher(dispatcher: Any | None = None) -> Any:
    return dispatcher if dispatcher is not None else dispatcher_module.dispatcher


def _resolve_heartbeat_runner(heartbeat_runner: Callable[..., Awaitable[Any]] | None = None) -> Callable[..., Awaitable[Any]]:
    return heartbeat_runner if heartbeat_runner is not None else heartbeat_module.run_single_heartbeat


def _resolve_notification_sender(notification_sender: Callable[[str, str, str], dict] | None = None) -> Callable[[str, str, str], dict]:
    if notification_sender is not None:
        return notification_sender
    from core.notifier import send_notification

    return send_notification


def affected_alert_sessions(active_sessions: Mapping[str, dict], host: str) -> list[str]:
    affected: list[str] = []
    for session_id, session_data in list(active_sessions.items()):
        info = session_data.get("info", {})
        if info.get("host") == host or host == "all" or info.get("host") == "localhost":
            affected.append(session_id)
    return affected


def _should_run_ai(alert_event: dict[str, Any]) -> bool:
    decision = alert_event.get("automation_decision")
    if isinstance(decision, dict):
        return bool(decision.get("run_ai"))
    return True


def _should_notify(alert_event: dict[str, Any]) -> bool:
    decision = alert_event.get("automation_decision")
    if isinstance(decision, dict):
        return bool(decision.get("notify"))
    return False


def _automation_summary(alert_events: list[dict[str, Any]], ai_alerts: list[dict[str, Any]]) -> dict[str, Any]:
    by_action: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for alert_event in alert_events:
        action = str(alert_event.get("noise_action") or "unknown")
        source = str(alert_event.get("source_family") or alert_event.get("source_type") or "unknown")
        by_action[action] = by_action.get(action, 0) + 1
        by_source[source] = by_source.get(source, 0) + 1
    return {
        "ai_triggered": bool(ai_alerts),
        "ai_alert_count": len(ai_alerts),
        "recorded_count": len(alert_events),
        "by_noise_action": by_action,
        "by_source_family": by_source,
    }


def build_alert_injection_message(alert_event: dict[str, Any]) -> str:
    severity = alert_event["severity"]
    alert_name = alert_event["alert_name"]
    host = alert_event["host"]
    description = alert_event["description"]
    source_family = alert_event.get("source_family") or alert_event.get("source_type") or "unknown"
    alert_class = alert_event.get("alert_class") or "unknown"
    priority = alert_event.get("priority") or "p2"
    noise_action = alert_event.get("noise_action") or "analyze"
    decision = alert_event.get("automation_decision") if isinstance(alert_event.get("automation_decision"), dict) else {}
    reason = decision.get("reason") or "命中自动分析策略。"
    return (
        f"🔔 【监控告警接入】外部系统触发了级别为 [{str(severity).upper()}] 的告警。\n"
        f"**告警名称**：{alert_name}\n"
        f"**故障节点**：{host}\n"
        f"**来源分类**：{source_family} / {alert_class} / {priority}\n"
        f"**降噪动作**：{noise_action}（{reason}）\n"
        f"**详细信息**：\n{description}\n\n"
        "作为监控专家，请主动分析此告警。如果你是负责整个环境的指挥官（例如你的连接是 localhost），"
        "请使用 `list_active_sessions` 查找合适的子节点并使用 `dispatch_sub_agents` 派发调查任务；"
        "如果你是具体服务器的节点 Agent，请立刻调用技能/工具去探查根因。"
        "完成后只需要在当前会话输出根因、影响面、处置建议；后端会按告警策略统一发送通知，请不要自行调用 `send_notification`。"
    )


def build_alert_batch_injection_message(alert_events: list[dict[str, Any]]) -> str:
    if len(alert_events) == 1:
        return build_alert_injection_message(alert_events[0])
    lines = [
        "🔔 【监控告警接入】外部系统批量触发告警，请优先判断是否为同一故障面。",
        "",
    ]
    for index, alert_event in enumerate(alert_events[:10], start=1):
        source_family = alert_event.get("source_family") or alert_event.get("source_type") or "unknown"
        alert_class = alert_event.get("alert_class") or "unknown"
        priority = alert_event.get("priority") or "p2"
        lines.append(
            f"{index}. [{str(alert_event['severity']).upper()}] "
            f"{source_family}/{alert_class}/{priority} "
            f"{alert_event['alert_name']} / {alert_event['host']} - {alert_event['description']}"
        )
    if len(alert_events) > 10:
        lines.append(f"... 另有 {len(alert_events) - 10} 条告警未展开。")
    lines.append("")
    lines.append("请结合当前会话资产、活跃会话和监控平台线索，给出处置优先级、影响面和下一步只读排查动作。")
    lines.append("后端会按告警策略统一发送通知，请不要自行调用 `send_notification`。")
    return "\n".join(lines)


def build_alert_analysis_notification(alert_events: list[dict[str, Any]], session_id: str, report: Any) -> tuple[str, str]:
    primary = alert_events[0]
    title = f"告警分析完成：{primary.get('alert_name') or '系统告警'}"
    lines = [
        f"- 会话: `{session_id}`",
        f"- 来源: `{primary.get('source_family') or primary.get('source_type') or '-'}`",
        f"- 主机: `{primary.get('host') or '-'}`",
        f"- 优先级: `{primary.get('priority') or '-'}`",
        f"- 告警数: `{len(alert_events)}`",
        "",
        "## AI 分析结果",
        str(report or "AI 已完成告警处理，但没有返回可发送的摘要。"),
    ]
    return title, "\n".join(lines)


def resolve_alert_notification_channels(
    alert_events: list[dict[str, Any]],
    *,
    env: Mapping[str, str] | None = None,
) -> list[str]:
    if not alert_events:
        return []
    plan = alert_events[0].get("notification_plan")
    targets = set(plan.get("targets") or []) if isinstance(plan, dict) else {"wechat", "dingtalk", "email"}
    if not targets:
        return []
    statuses = build_notification_channel_statuses(os.environ if env is None else env)
    return [
        str(item["channel"])
        for item in statuses
        if item.get("ready") and item.get("channel") in targets
    ]


def send_alert_analysis_notifications(
    alert_events: list[dict[str, Any]],
    session_id: str,
    report: Any,
    *,
    notification_sender: Callable[[str, str, str], dict] | None = None,
    env: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    channels = resolve_alert_notification_channels(alert_events, env=env)
    if not channels:
        return [{"channel": "none", "status": "SKIPPED", "message": "没有已启用且配置完整的告警通知通道。"}]
    title, content = build_alert_analysis_notification(alert_events, session_id, report)
    sender = _resolve_notification_sender(notification_sender)
    results: list[dict[str, Any]] = []
    for channel in channels:
        result = sender(channel, title, content)
        if isinstance(result, dict):
            results.append({"channel": channel, **result})
        else:
            results.append({"channel": channel, "status": "UNKNOWN", "message": str(result)})
    return results


async def run_alert_analysis_task(
    *,
    session_id: str,
    info: dict[str, Any],
    store: Any,
    dispatcher: Any,
    heartbeat_runner: Callable[..., Awaitable[Any]],
    trigger_msg: str,
    alert_events: list[dict[str, Any]],
    notify_after_analysis: bool,
    notification_sender: Callable[[str, str, str], dict] | None = None,
) -> Any:
    report = await heartbeat_runner(
        session_id,
        info,
        store,
        dispatcher,
        trigger_msg=trigger_msg,
    )
    if notify_after_analysis:
        results = send_alert_analysis_notifications(
            alert_events,
            session_id,
            report,
            notification_sender=notification_sender,
        )
        logger.info(
            "Alert analysis notification completed for session %s: %s",
            session_id,
            results,
        )
    return report


async def read_alert_webhook_payload(json_reader: Callable[[], Awaitable[Any]]) -> Any:
    try:
        return await json_reader()
    except (ValueError, TypeError):
        return {}


async def handle_alert_webhook(
    payload: dict[str, Any],
    active_sessions: MutableMapping[str, dict],
    session_locks: MutableMapping[str, asyncio.Lock],
    dispatcher: Any | None = None,
    heartbeat_runner: Callable[..., Awaitable[Any]] | None = None,
    *,
    memory_db: Any | None = None,
    task_factory: Callable[[Awaitable[Any]], Any] = asyncio.create_task,
    notification_sender: Callable[[str, str, str], dict] | None = None,
) -> dict[str, Any]:
    alert_events = create_alert_events(payload)
    if not alert_events:
        return {
            "message": NO_ACTIVE_ALERT_MESSAGE,
            "data": {"alert": None, "alerts": [], "injected_count": 0, "automation": _automation_summary([], [])},
        }
    primary_alert = alert_events[0]
    ai_alerts = [alert_event for alert_event in alert_events if _should_run_ai(alert_event)]
    automation = _automation_summary(alert_events, ai_alerts)
    host = primary_alert["host"]
    alert_name = primary_alert["alert_name"]
    severity = primary_alert["severity"]

    logger.info(
        "Webhook alert received: host=%s alert=%s severity=%s count=%s keys=%s",
        host,
        alert_name,
        payload.get("severity") or payload.get("priority") or payload.get("status") or "",
        len(alert_events),
        sorted(list(payload.keys()))[:20],
    )
    logger.info("Parsed Alert -> Host: %s, Name: %s, Severity: %s", host, alert_name, severity)

    if not ai_alerts:
        return {
            "message": RECORD_ONLY_ALERT_MESSAGE,
            "data": {
                "alert": primary_alert,
                "alerts": alert_events,
                "injected_count": 0,
                "automation": automation,
            },
        }

    affected_sessions = sorted({
        session_id
        for alert_event in ai_alerts
        for session_id in affected_alert_sessions(active_sessions, alert_event["host"])
    })
    if not affected_sessions:
        logger.warning("Alert received but no active AI session is connected to affected hosts or localhost.")
        return {
            "message": NO_ACTIVE_ALERT_MESSAGE,
            "data": {"alert": primary_alert, "alerts": alert_events, "injected_count": 0, "automation": automation},
        }

    injection_message = build_alert_batch_injection_message(ai_alerts)
    injected_count = 0
    notification_scheduled = False
    needs_notification = any(_should_notify(alert_event) for alert_event in ai_alerts)
    store = _resolve_memory_db(memory_db)
    resolved_dispatcher = _resolve_dispatcher(dispatcher)
    resolved_heartbeat_runner = _resolve_heartbeat_runner(heartbeat_runner)
    for session_id in affected_sessions:
        info = active_sessions[session_id].get("info", {})
        lock = session_locks.setdefault(session_id, asyncio.Lock())
        async with lock:
            if info.get("heartbeat_in_progress"):
                store.append_message(session_id, {"role": "user", "content": injection_message})
                logger.info("Session %s is busy, appended alert to context only.", session_id)
            else:
                info["heartbeat_in_progress"] = True
                logger.info("Actively triggering background AI task for session %s due to alert.", session_id)
                should_notify_this_task = needs_notification and not notification_scheduled
                notification_scheduled = notification_scheduled or should_notify_this_task
                task_factory(
                    run_alert_analysis_task(
                        session_id=session_id,
                        info=info,
                        store=store,
                        dispatcher=resolved_dispatcher,
                        heartbeat_runner=resolved_heartbeat_runner,
                        trigger_msg=injection_message,
                        alert_events=ai_alerts,
                        notify_after_analysis=should_notify_this_task,
                        notification_sender=notification_sender,
                    )
                )
        injected_count += 1

    return {
        "message": ACTIVE_ALERT_MESSAGE_TEMPLATE.format(count=injected_count),
        "data": {
            "alert": primary_alert,
            "alerts": alert_events,
            "injected_count": injected_count,
            "automation": {**automation, "notification_scheduled": notification_scheduled},
        },
    }
