"""Session asset profile generation and formatting."""

from __future__ import annotations

import asyncio
import datetime
import json
import re
from typing import Any

from connections.ssh_manager import ssh_manager
from core.asset_protocols import get_asset_definition, normalize_protocol
from core.memory import memory_db
from core.redaction import redact_json_text, redact_text


PROFILE_VERSION = 1


def session_asset_context(session_id: str) -> dict[str, Any]:
    session = ssh_manager.active_sessions.get(session_id)
    info = dict(session.get("info", {})) if session else {}
    asset_type = str(info.get("asset_type") or "").lower()
    protocol = normalize_protocol(
        asset_type,
        info.get("protocol"),
        info.get("extra_args", {}),
        info.get("host"),
        info.get("port"),
        info.get("remark"),
    )
    host = str(info.get("host") or "")
    port = info.get("port")
    asset_key = f"{asset_type or 'asset'}:{protocol or 'unknown'}:{host}:{port or ''}"
    return {
        "session_id": session_id,
        "asset_key": asset_key,
        "host": host,
        "port": port,
        "remark": info.get("remark") or "",
        "asset_type": asset_type,
        "protocol": protocol,
        "username": info.get("username") or "",
        "target_scope": info.get("target_scope") or "asset",
        "scope_value": info.get("scope_value"),
        "tags": info.get("tags") or [],
    }


def _asset_label(asset_type: str, protocol: str) -> str:
    definition = get_asset_definition(asset_type)
    if definition and definition.get("label"):
        return str(definition["label"])
    if asset_type:
        return asset_type.upper() if len(asset_type) <= 4 else asset_type.replace("_", " ").title()
    return protocol.upper() if protocol else "未知资产"


def _role_for(asset_type: str, protocol: str) -> tuple[str, str]:
    database = {"oracle", "mysql", "postgresql", "mssql", "sqlserver", "mariadb", "db2", "clickhouse"}
    cache = {"redis", "memcached", "mongodb", "elasticsearch"}
    network = {"switch", "router", "firewall", "load_balancer", "f5", "network_device"}
    storage = {"s3", "minio", "oss", "cos", "obs", "storage", "nas", "san", "ceph"}
    virtualization = {"vmware", "proxmox", "openstack", "zstack", "kvm", "hyperv"}
    os_hosts = {"linux", "ssh", "redhat", "centos", "ubuntu", "debian", "windows"}

    if protocol in database or asset_type in database:
        return "数据库服务", "database"
    if protocol in cache or asset_type in cache:
        return "数据/缓存服务", "datastore"
    if asset_type in network or protocol in {"snmp", "network_cli"}:
        return "网络与安全设备", "network"
    if asset_type in storage:
        return "存储服务", "storage"
    if asset_type in virtualization:
        return "虚拟化/云平台", "virtualization"
    if protocol == "winrm" or asset_type == "windows":
        return "Windows 主机", "windows"
    if protocol == "ssh" or asset_type in os_hosts:
        return "Linux/Unix 主机", "linux"
    if protocol in {"http", "https", "http_api", "rest"}:
        return "HTTP/API 服务", "api"
    return "运维资产", "general"


def _history_excerpt(session_id: str, limit: int = 7000) -> str:
    messages = memory_db.get_messages(session_id, for_ui=True)
    lines: list[str] = []
    for msg in messages[-18:]:
        if msg.get("role") not in {"user", "assistant"}:
            continue
        content = str(msg.get("content") or "")
        if not content.strip():
            continue
        role = "用户" if msg.get("role") == "user" else "AI"
        lines.append(f"[{role}] {content[:1200]}")
    text = "\n".join(lines)
    return redact_text(text)[-limit:]


def _inspection_excerpt(inspection: dict[str, Any] | None, limit: int = 9000) -> str:
    if not inspection:
        return ""
    safe = redact_json_text(json.dumps(inspection, ensure_ascii=False, default=str))
    return safe[:limit]


def _extract_json_object(text: str) -> dict[str, Any] | None:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?", "", candidate, flags=re.I).strip()
        candidate = re.sub(r"```$", "", candidate).strip()
    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(candidate[start : end + 1])
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None
    return None


def _fallback_profile(
    session_id: str,
    context: dict[str, Any],
    inspection: dict[str, Any] | None,
    source: str,
) -> dict[str, Any]:
    asset_type = str(context.get("asset_type") or "")
    protocol = str(context.get("protocol") or "")
    label = _asset_label(asset_type, protocol)
    role_label, role_category = _role_for(asset_type, protocol)
    checks = inspection.get("checks", []) if isinstance(inspection, dict) else []
    failed = [c for c in checks if isinstance(c, dict) and c.get("status") not in {"success", "ok"}]
    evidence = [
        {"label": "资产类型", "value": label, "source": "连接信息"},
        {"label": "连接协议", "value": protocol.upper() if protocol else "未知", "source": "连接信息"},
    ]
    for check in checks[:4]:
        if isinstance(check, dict):
            output = str(check.get("output") or "").strip().replace("\r", "")
            evidence.append(
                {
                    "label": str(check.get("title") or check.get("name") or "巡检项"),
                    "value": output[:180] or str(check.get("status") or ""),
                    "source": "只读巡检",
                }
            )

    focus_areas = [
        {"title": "基础连通性", "reason": "确认账号、协议端口和资产身份是否稳定。", "priority": "P1"},
        {"title": "资源与服务状态", "reason": "根据 CPU、内存、磁盘、服务和错误日志判断运行风险。", "priority": "P1"},
    ]
    if role_category == "database":
        focus_areas.insert(0, {"title": "数据库实例状态", "reason": "优先检查监听、连接数、表空间、日志和备份状态。", "priority": "P0"})
    elif role_category == "linux":
        focus_areas.insert(0, {"title": "系统服务与安全日志", "reason": "优先确认 failed units、认证失败、磁盘挂载和关键进程。", "priority": "P0"})
    elif role_category == "network":
        focus_areas.insert(0, {"title": "接口与邻居稳定性", "reason": "优先检查接口错误、STP/ARP、路由和防火墙策略。", "priority": "P0"})

    risk_level = "high" if len(failed) >= 3 else ("watch" if failed else "normal")
    return _normalize_profile(
        {
            "version": PROFILE_VERSION,
            "session_id": session_id,
            "asset_key": context.get("asset_key"),
            "host": context.get("host"),
            "port": context.get("port"),
            "remark": context.get("remark"),
            "asset_type": asset_type,
            "protocol": protocol,
            "role_label": role_label,
            "role_category": role_category,
            "purpose": f"基于当前连接信息判断，该资产主要属于{role_label}，需要结合后续巡检持续校准用途。",
            "confidence": 58 if source == "fallback" else 70,
            "risk_level": risk_level,
            "evidence": evidence[:8],
            "focus_areas": focus_areas[:6],
            "services": [],
            "tags": context.get("tags") or [],
            "source": source,
            "source_summary": inspection.get("summary") if isinstance(inspection, dict) else "",
            "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        context,
    )


def _normalize_profile(profile: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    role_label, role_category = _role_for(str(context.get("asset_type") or ""), str(context.get("protocol") or ""))
    normalized = {
        "version": PROFILE_VERSION,
        "session_id": context.get("session_id"),
        "asset_key": context.get("asset_key"),
        "host": context.get("host"),
        "port": context.get("port"),
        "remark": context.get("remark") or "",
        "asset_type": context.get("asset_type") or profile.get("asset_type") or "",
        "protocol": context.get("protocol") or profile.get("protocol") or "",
        "role_label": str(profile.get("role_label") or role_label)[:80],
        "role_category": str(profile.get("role_category") or role_category)[:60],
        "purpose": str(profile.get("purpose") or "")[:700],
        "confidence": int(profile.get("confidence") or 50),
        "risk_level": str(profile.get("risk_level") or "watch"),
        "evidence": profile.get("evidence") if isinstance(profile.get("evidence"), list) else [],
        "focus_areas": profile.get("focus_areas") if isinstance(profile.get("focus_areas"), list) else [],
        "services": profile.get("services") if isinstance(profile.get("services"), list) else [],
        "tags": profile.get("tags") if isinstance(profile.get("tags"), list) else context.get("tags") or [],
        "source": str(profile.get("source") or "ai"),
        "source_summary": str(profile.get("source_summary") or "")[:700],
        "updated_at": str(profile.get("updated_at") or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    }
    normalized["confidence"] = max(0, min(100, normalized["confidence"]))
    if normalized["risk_level"] not in {"normal", "watch", "high"}:
        normalized["risk_level"] = "watch"
    normalized["evidence"] = [
        {
            "label": str(item.get("label") or "证据")[:60],
            "value": str(item.get("value") or "")[:300],
            "source": str(item.get("source") or "")[:60],
        }
        for item in normalized["evidence"][:8]
        if isinstance(item, dict)
    ]
    normalized["focus_areas"] = [
        {
            "title": str(item.get("title") or "排查项")[:80],
            "reason": str(item.get("reason") or "")[:260],
            "priority": str(item.get("priority") or "P1")[:10],
        }
        for item in normalized["focus_areas"][:8]
        if isinstance(item, dict)
    ]
    normalized["services"] = [str(item)[:80] for item in normalized["services"][:12]]
    normalized["tags"] = [str(item)[:40] for item in normalized["tags"][:12]]
    return normalized


async def _generate_ai_profile(
    session_id: str,
    context: dict[str, Any],
    inspection: dict[str, Any] | None,
    model_name: str | None,
) -> dict[str, Any] | None:
    from core.llm_execution import execute_chat_stream
    from core.llm_factory import get_default_model_id

    selected_model = model_name or get_default_model_id()
    prompt = f"""
你是企业 AIOps 平台的资产画像分析器。请根据资产连接信息、只读巡检结果和最近会话内容，判断这是什么资产、可能承担什么业务角色、后续排查应该重点关注什么。

只输出 JSON 对象，不要 Markdown，不要解释。字段：
role_label, role_category, purpose, confidence, risk_level, evidence, focus_areas, services, tags, source_summary。

要求：
- role_label 用中文短语，例如“Oracle 数据库服务”“Linux 应用服务器”“Windows 主机”“网络交换设备”。
- role_category 用英文小写分类，例如 database/linux/windows/network/storage/virtualization/api/general。
- confidence 是 0-100 整数。
- risk_level 只能是 normal/watch/high。
- evidence 最多 6 条，每条含 label,value,source。
- focus_areas 最多 6 条，每条含 title,reason,priority，priority 用 P0/P1/P2。
- 不要输出密码、Token、密钥、完整敏感连接串。

资产连接信息：
{redact_json_text(json.dumps(context, ensure_ascii=False, default=str))}

只读巡检结果：
{_inspection_excerpt(inspection)}

最近会话：
{_history_excerpt(session_id)}
""".strip()
    messages = [
        {"role": "system", "content": "你只输出严格 JSON。"},
        {"role": "user", "content": prompt},
    ]
    content_parts: list[str] = []
    async for event in execute_chat_stream(selected_model, messages, "off", None):
        if event.get("type") == "content":
            content_parts.append(str(event.get("content") or ""))
    parsed = _extract_json_object("".join(content_parts))
    if not parsed:
        return None
    parsed["source"] = "ai"
    return _normalize_profile(parsed, context)


async def generate_session_profile(
    session_id: str,
    model_name: str | None = None,
    include_inspection: bool = True,
) -> dict[str, Any]:
    if session_id not in ssh_manager.active_sessions:
        existing = memory_db.get_asset_profile(session_id)
        if existing:
            return existing
        raise ValueError("会话不存在或已断开")

    context = session_asset_context(session_id)
    inspection: dict[str, Any] | None = None
    if include_inspection:
        try:
            from core.session_inspector import inspect_session

            inspection = await inspect_session(session_id)
        except Exception as e:
            inspection = {"status": "warning", "summary": f"只读巡检未完成: {e}", "checks": []}

    try:
        profile = await _generate_ai_profile(session_id, context, inspection, model_name)
    except Exception:
        profile = None
    if not profile:
        profile = _fallback_profile(session_id, context, inspection, "fallback")
    return await asyncio.to_thread(
        memory_db.save_asset_profile,
        session_id,
        str(profile.get("asset_key") or context.get("asset_key") or ""),
        str(profile.get("host") or context.get("host") or ""),
        str(profile.get("asset_type") or context.get("asset_type") or ""),
        str(profile.get("protocol") or context.get("protocol") or ""),
        profile,
    )


def get_session_profile(session_id: str) -> dict[str, Any] | None:
    return memory_db.get_asset_profile(session_id)


def profile_to_markdown(profile: dict[str, Any]) -> str:
    lines = [
        f"## 资产画像：{profile.get('remark') or profile.get('host') or profile.get('session_id')}",
        "",
        f"- 资产角色：{profile.get('role_label') or '-'}",
        f"- 用途判断：{profile.get('purpose') or '-'}",
        f"- 风险等级：{profile.get('risk_level') or '-'}",
        f"- 置信度：{profile.get('confidence', 0)}%",
        f"- 更新时间：{profile.get('updated_at') or '-'}",
        "",
        "### 关键证据",
    ]
    for item in profile.get("evidence") or []:
        lines.append(f"- {item.get('label')}: {item.get('value')} ({item.get('source') or '未知来源'})")
    lines.append("")
    lines.append("### 后续排查重点")
    for item in profile.get("focus_areas") or []:
        lines.append(f"- [{item.get('priority') or 'P1'}] {item.get('title')}: {item.get('reason')}")
    return "\n".join(lines)
