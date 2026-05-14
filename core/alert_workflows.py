"""Persistent alert workflow records for AI-assisted incident handling."""

from __future__ import annotations

import json
import asyncio
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from core import memory as memory_module


ROOT_DIR = Path(__file__).resolve().parent.parent
ALERT_WORKFLOW_STORE_PATH = ROOT_DIR / "alert_workflows.json"
_LOCK = threading.RLock()
_STORE_CACHE: tuple[str, float, int, list[dict[str, Any]]] | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_store() -> list[dict[str, Any]]:
    global _STORE_CACHE
    if not ALERT_WORKFLOW_STORE_PATH.exists():
        _STORE_CACHE = None
        return []
    try:
        stat = ALERT_WORKFLOW_STORE_PATH.stat()
        if _STORE_CACHE and _STORE_CACHE[0] == str(ALERT_WORKFLOW_STORE_PATH) and _STORE_CACHE[1] == stat.st_mtime and _STORE_CACHE[2] == stat.st_size:
            return [dict(item) for item in _STORE_CACHE[3]]
    except OSError:
        return []
    try:
        data = json.loads(ALERT_WORKFLOW_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    items = [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []
    try:
        stat = ALERT_WORKFLOW_STORE_PATH.stat()
        _STORE_CACHE = (str(ALERT_WORKFLOW_STORE_PATH), stat.st_mtime, stat.st_size, [dict(item) for item in items])
    except OSError:
        _STORE_CACHE = None
    return items


def _write_store(items: list[dict[str, Any]]) -> None:
    global _STORE_CACHE
    ALERT_WORKFLOW_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ALERT_WORKFLOW_STORE_PATH.write_text(json.dumps(items[:5000], ensure_ascii=False, indent=2), encoding="utf-8")
    _STORE_CACHE = None


def _host_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    if ":" in text and text.count(":") == 1:
        host, port = text.rsplit(":", 1)
        if port.isdigit():
            return host
    return text


def _resolve_memory_db(memory_db: Any | None = None) -> Any:
    return memory_db if memory_db is not None else memory_module.memory_db


def _session_view(session_id: str, info: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "host": info.get("host") or "",
        "remark": info.get("remark") or "",
        "asset_type": info.get("asset_type") or "",
        "protocol": info.get("protocol") or "",
        "allow_modifications": bool(info.get("allow_modifications")),
        "active_skills": info.get("active_skills") or [],
        "tags": info.get("tags") or [],
    }


def find_alert_asset_sessions(alert_event: dict[str, Any], active_sessions: Mapping[str, dict] | None) -> list[dict[str, Any]]:
    target_host = _host_key(alert_event.get("host"))
    if not target_host:
        return []
    matches: list[dict[str, Any]] = []
    for session_id, session_data in list((active_sessions or {}).items()):
        info = session_data.get("info", {}) if isinstance(session_data, dict) else {}
        if _host_key(info.get("host")) == target_host:
            matches.append(_session_view(session_id, info))
    return matches


def find_alert_asset_candidates(alert_event: dict[str, Any], memory_db: Any | None = None) -> list[dict[str, Any]]:
    target_host = _host_key(alert_event.get("host"))
    if not target_host:
        return []
    store = _resolve_memory_db(memory_db)
    candidates: list[dict[str, Any]] = []
    try:
        assets = store.get_all_assets()
    except Exception:
        return []
    for asset in assets:
        if _host_key(asset.get("host")) != target_host:
            continue
        candidates.append(
            {
                "asset_id": asset.get("id"),
                "host": asset.get("host") or "",
                "remark": asset.get("remark") or "",
                "asset_type": asset.get("asset_type") or "",
                "protocol": asset.get("protocol") or "",
                "tags": asset.get("tags") or [],
                "can_create_session": bool(asset.get("username")),
            }
        )
    return candidates


def _monitoring_queries(alert_event: dict[str, Any]) -> list[dict[str, Any]]:
    host = str(alert_event.get("host") or "").strip()
    alert_name = str(alert_event.get("alert_name") or "").strip()
    alert_class = str(alert_event.get("alert_class") or "").strip().lower()
    queries: list[dict[str, Any]] = []
    if host:
        queries.append({"name": "主机 up 状态", "query": f'up{{instance=~"{host}(:.*)?"}}'})
    if alert_class == "capacity" or any(word in alert_name.lower() for word in ("disk", "filesystem", "inode", "磁盘", "空间")):
        queries.append(
            {
                "name": "磁盘剩余率",
                "query": f'100 * node_filesystem_avail_bytes{{instance=~"{host}(:.*)?",fstype!~"tmpfs|overlay"}} / node_filesystem_size_bytes',
            }
        )
        queries.append(
            {
                "name": "inode 剩余率",
                "query": f'100 * node_filesystem_files_free{{instance=~"{host}(:.*)?"}} / node_filesystem_files{{instance=~"{host}(:.*)?"}}',
            }
        )
    if alert_class == "performance":
        queries.append({"name": "CPU 使用率", "query": f'100 - avg by(instance)(irate(node_cpu_seconds_total{{instance=~"{host}(:.*)?",mode="idle"}}[5m])) * 100'})
        queries.append({"name": "内存可用率", "query": f'100 * node_memory_MemAvailable_bytes{{instance=~"{host}(:.*)?"}} / node_memory_MemTotal_bytes'})
    return queries


def _workflow_steps(
    alert_event: dict[str, Any],
    linked_sessions: list[dict[str, Any]],
    asset_candidates: list[dict[str, Any]],
    injected_count: int = 0,
) -> list[dict[str, Any]]:
    decision = alert_event.get("automation_decision") if isinstance(alert_event.get("automation_decision"), dict) else {}
    remediation_mode = str(decision.get("remediation_mode") or "disabled")
    source_family = str(alert_event.get("source_family") or alert_event.get("source_type") or alert_event.get("source") or "generic")
    monitoring_queries = _monitoring_queries(alert_event)
    return [
        {"id": "receive", "title": "接收告警", "status": "done", "summary": f"{source_family} / {alert_event.get('alert_name') or '-'}"},
        {
            "id": "policy",
            "title": "命中自动化策略",
            "status": "done",
            "summary": decision.get("rule_name") or decision.get("rule_id") or "默认策略",
            "details": {"run_ai": bool(decision.get("run_ai")), "notify": bool(decision.get("notify"))},
        },
        {
            "id": "monitoring_context",
            "title": "查询监控平台上下文",
            "status": "ready" if monitoring_queries else "skipped",
            "summary": "已生成 Prometheus/监控平台查询建议" if monitoring_queries else "当前告警缺少可推导的监控查询",
            "details": {"queries": monitoring_queries},
        },
        {
            "id": "asset_session",
            "title": "联动资产会话",
            "status": "done" if linked_sessions else ("ready" if asset_candidates else "waiting"),
            "summary": (
                f"已匹配 {len(linked_sessions)} 个在线资产会话"
                if linked_sessions
                else (f"找到 {len(asset_candidates)} 个资产候选，等待创建会话" if asset_candidates else "未找到在线会话或资产候选")
            ),
            "details": {"linked_sessions": linked_sessions, "asset_candidates": asset_candidates},
        },
        {
            "id": "readonly_check",
            "title": "只读现场检查",
            "status": "running" if injected_count else ("ready" if linked_sessions else "waiting"),
            "summary": "AI 已注入资产会话执行只读排查" if injected_count else "等待 AI 或人工触发只读检查",
        },
        {
            "id": "remediation",
            "title": "修复策略",
            "status": "disabled" if remediation_mode == "disabled" else "ready",
            "summary": {
                "disabled": "仅分析和建议，不自动修复",
                "suggest": "只生成修复建议，不执行",
                "approval": "生成修复动作，人工审批后执行",
                "auto_low_risk": "仅允许白名单低风险动作自动执行",
            }.get(remediation_mode, "仅分析和建议，不自动修复"),
            "details": {
                "mode": remediation_mode,
                "allowed_actions": decision.get("allowed_remediation_actions") or [],
            },
        },
    ]


def ensure_alert_workflow(
    alert_event: dict[str, Any],
    *,
    active_sessions: Mapping[str, dict] | None = None,
    memory_db: Any | None = None,
    injected_count: int = 0,
) -> dict[str, Any]:
    alert_id = str(alert_event.get("id") or "")
    if not alert_id:
        raise ValueError("alert id is required")
    now = _now()
    linked_sessions = find_alert_asset_sessions(alert_event, active_sessions)
    asset_candidates = find_alert_asset_candidates(alert_event, memory_db)
    with _LOCK:
        items = _read_store()
        existing = next((item for item in items if item.get("alert_id") == alert_id), None)
        workflow = existing or {
            "id": f"workflow_{alert_id}",
            "alert_id": alert_id,
            "created_at": now,
            "messages": [],
        }
        workflow.update(
            {
                "updated_at": now,
                "status": "running" if injected_count else "ready",
                "alert_name": alert_event.get("alert_name") or "",
                "host": alert_event.get("host") or "",
                "source_family": alert_event.get("source_family") or alert_event.get("source_type") or "",
                "linked_sessions": linked_sessions,
                "asset_candidates": asset_candidates,
                "steps": _workflow_steps(alert_event, linked_sessions, asset_candidates, injected_count),
            }
        )
        if not workflow.get("messages"):
            workflow["messages"] = [
                {
                    "role": "system",
                    "time": now,
                    "content": "告警工作流已创建，可在这里人工补充信息或接管分析。",
                }
            ]
        if existing is None:
            items.insert(0, workflow)
        _write_store(items)
        return workflow


def get_alert_workflow(alert_id: str) -> dict[str, Any] | None:
    with _LOCK:
        for item in _read_store():
            if item.get("alert_id") == alert_id or item.get("id") == alert_id:
                return item
    return None


def append_alert_workflow_message(alert_id: str, role: str, content: str) -> dict[str, Any] | None:
    content = str(content or "").strip()
    if not content:
        raise ValueError("message content is required")
    with _LOCK:
        items = _read_store()
        for item in items:
            if item.get("alert_id") != alert_id and item.get("id") != alert_id:
                continue
            item.setdefault("messages", []).append({"role": role or "user", "time": _now(), "content": content})
            item["updated_at"] = _now()
            _write_store(items)
            return item
    return None


def build_alert_workflow_readonly_prompt(alert_event: dict[str, Any], workflow: dict[str, Any] | None = None) -> str:
    queries: list[dict[str, Any]] = []
    if workflow:
        for step in workflow.get("steps") or []:
            if step.get("id") == "monitoring_context":
                details = step.get("details") if isinstance(step.get("details"), dict) else {}
                queries = [item for item in details.get("queries") or [] if isinstance(item, dict)]
                break
    query_lines = []
    for item in queries[:5]:
        query_lines.append(f"- {item.get('name') or 'PromQL'}: `{item.get('query') or '-'}`")
    query_text = "\n".join(query_lines) if query_lines else "- 暂无可推导的监控查询，请根据告警字段判断是否需要查询监控平台。"
    decision = alert_event.get("automation_decision") if isinstance(alert_event.get("automation_decision"), dict) else {}
    remediation_mode = decision.get("remediation_mode") or "disabled"
    return (
        "【告警工作流 / 手动触发只读分析】\n"
        f"告警ID：{alert_event.get('id') or '-'}\n"
        f"告警名称：{alert_event.get('alert_name') or '-'}\n"
        f"故障节点：{alert_event.get('host') or '-'}\n"
        f"来源分类：{alert_event.get('source_family') or alert_event.get('source_type') or '-'} / "
        f"{alert_event.get('alert_class') or '-'} / {alert_event.get('priority') or '-'}\n"
        f"级别：{alert_event.get('severity') or '-'}\n"
        f"描述：{alert_event.get('description') or '-'}\n"
        f"自动修复模式：{remediation_mode}\n\n"
        "请只读排查，不要执行修复命令，不要自行发送通知。优先检查：\n"
        "1. 当前资产的磁盘、inode、CPU、内存、服务状态和近期异常日志。\n"
        "2. 如果当前会话是监控平台，请按下面查询建议核对指标和同组告警。\n"
        "3. 输出根因判断、影响面、证据、建议动作；如需要修复，只生成建议或审批动作。\n\n"
        "监控查询建议：\n"
        f"{query_text}"
    )


async def trigger_alert_workflow_readonly_analysis(
    alert_event: dict[str, Any],
    *,
    active_sessions: dict[str, dict],
    session_locks: dict[str, asyncio.Lock],
    memory_db: Any | None = None,
    dispatcher: Any | None = None,
    heartbeat_runner: Any | None = None,
    task_factory: Any = asyncio.create_task,
) -> dict[str, Any]:
    from core import dispatcher as dispatcher_module
    from core import heartbeat as heartbeat_module
    from core.alert_webhook_service import run_alert_analysis_task

    store = _resolve_memory_db(memory_db)
    workflow = ensure_alert_workflow(alert_event, active_sessions=active_sessions, memory_db=memory_db, injected_count=0)
    linked_sessions = find_alert_asset_sessions(alert_event, active_sessions)
    if not linked_sessions:
        append_alert_workflow_message(alert_event["id"], "system", "未找到在线资产会话，无法触发只读分析。")
        workflow = ensure_alert_workflow(alert_event, active_sessions=active_sessions, memory_db=memory_db, injected_count=0)
        return {"workflow": workflow, "injected_count": 0, "message": "未找到在线资产会话"}

    prompt = build_alert_workflow_readonly_prompt(alert_event, workflow)
    resolved_dispatcher = dispatcher if dispatcher is not None else dispatcher_module.dispatcher
    resolved_heartbeat = heartbeat_runner if heartbeat_runner is not None else heartbeat_module.run_single_heartbeat
    injected_count = 0
    queued_count = 0
    for item in linked_sessions:
        session_id = item["session_id"]
        session_data = active_sessions.get(session_id)
        if not session_data:
            continue
        info = session_data.get("info", {})
        lock = session_locks.setdefault(session_id, asyncio.Lock())
        async with lock:
            if info.get("heartbeat_in_progress"):
                store.append_message(session_id, {"role": "user", "content": prompt})
                queued_count += 1
            else:
                info["heartbeat_in_progress"] = True
                task_factory(
                    run_alert_analysis_task(
                        session_id=session_id,
                        info=info,
                        store=store,
                        dispatcher=resolved_dispatcher,
                        heartbeat_runner=resolved_heartbeat,
                        trigger_msg=prompt,
                        alert_events=[alert_event],
                        notify_after_analysis=False,
                    )
                )
                injected_count += 1

    total = injected_count + queued_count
    append_alert_workflow_message(
        alert_event["id"],
        "system",
        f"已手动触发只读分析：启动 {injected_count} 个会话，排队 {queued_count} 个会话。",
    )
    workflow = ensure_alert_workflow(alert_event, active_sessions=active_sessions, memory_db=memory_db, injected_count=total)
    return {"workflow": workflow, "injected_count": total, "message": "只读分析已触发"}
