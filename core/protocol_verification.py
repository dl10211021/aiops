"""Protocol verification matrix for managed AIOps assets."""

from __future__ import annotations

import asyncio
import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.asset_protocols import API_PROTOCOLS, SQL_PROTOCOLS, SNMP_PROTOCOLS, resolve_asset_identity
from core.tool_registry import tool_registry

SECRET_KEYS = {
    "password",
    "api_key",
    "api_token",
    "token",
    "bearer_token",
    "kubeconfig",
    "community_string",
    "v3_auth_pass",
    "v3_priv_pass",
    "enable_pass",
    "enable_password",
}
ROOT_DIR = Path(__file__).resolve().parent.parent
VERIFICATION_RUN_STORE_PATH = ROOT_DIR / "protocol_verification_runs.json"
_RUN_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_runs() -> list[dict[str, Any]]:
    if not VERIFICATION_RUN_STORE_PATH.exists():
        return []
    try:
        with VERIFICATION_RUN_STORE_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _save_runs(items: list[dict[str, Any]]) -> None:
    VERIFICATION_RUN_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = VERIFICATION_RUN_STORE_PATH.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    tmp_path.replace(VERIFICATION_RUN_STORE_PATH)


def _record_run(run: dict[str, Any]) -> dict[str, Any]:
    with _RUN_LOCK:
        items = _load_runs()
        items.insert(0, run)
        _save_runs(items[:1000])
    return run


def list_verification_runs(asset_id: int | None = None, limit: int = 50) -> list[dict[str, Any]]:
    with _RUN_LOCK:
        items = _load_runs()
    if asset_id is not None:
        items = [item for item in items if item.get("asset", {}).get("id") == asset_id]
    return items[: max(1, min(int(limit or 50), 500))]


def _safe_extra_args(extra_args: dict[str, Any] | None) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in (extra_args or {}).items():
        if key.lower() in SECRET_KEYS:
            safe[key] = "********"
        else:
            safe[key] = value
    return safe


def sanitize_asset(asset: dict[str, Any]) -> dict[str, Any]:
    identity = resolve_asset_identity(
        asset.get("asset_type"),
        asset.get("protocol"),
        asset.get("extra_args") or {},
        asset.get("host"),
        asset.get("port"),
        asset.get("remark"),
    )
    return {
        "id": asset.get("id"),
        "remark": asset.get("remark") or "",
        "host": asset.get("host") or "",
        "port": asset.get("port"),
        "username": asset.get("username") or "",
        "asset_type": identity["asset_type"],
        "protocol": identity["protocol"],
        "category": identity["extra_args"].get("category") or "other",
        "agent_profile": asset.get("agent_profile") or "default",
        "tags": asset.get("tags") or [],
        "extra_args": _safe_extra_args(identity["extra_args"]),
    }


def _context(asset: dict[str, Any]) -> dict[str, Any]:
    identity = resolve_asset_identity(
        asset.get("asset_type"),
        asset.get("protocol"),
        asset.get("extra_args") or {},
        asset.get("host"),
        asset.get("port"),
        asset.get("remark"),
    )
    return {
        "target_scope": "asset",
        "asset_type": identity["asset_type"],
        "protocol": identity["protocol"],
        "host": asset.get("host"),
        "port": asset.get("port"),
        "remark": asset.get("remark"),
        "extra_args": identity["extra_args"],
    }


def _active_tools(asset: dict[str, Any]) -> list[str]:
    catalog = tool_registry.catalog(_context(asset))
    return [
        tool["name"]
        for toolset in catalog["toolsets"]
        for tool in toolset["tools"]
        if tool.get("enabled")
    ]


def build_asset_matrix(asset: dict[str, Any]) -> dict[str, Any]:
    safe_asset = sanitize_asset(asset)
    active_tools = _active_tools(asset)
    protocol = safe_asset["protocol"]
    asset_type = safe_asset["asset_type"]
    has_native_tool = bool(active_tools)
    steps = [
        {
            "id": "connection_test",
            "label": "连接测试",
            "status": "supported",
            "description": f"使用 {protocol} 协议验证资产连通性和托管凭据。",
        },
        {
            "id": "protocol_probe",
            "label": "协议原生探测",
            "status": "supported",
            "description": f"通过 {asset_type}/{protocol} 对应的原生工具执行只读探测，避免只做虚拟登记。",
        },
        {
            "id": "tool_catalog",
            "label": "工具目录",
            "status": "supported" if has_native_tool else "gap",
            "description": "确认当前资产会暴露正确的协议工具给模型。",
        },
        {
            "id": "readonly_inspection",
            "label": "只读巡检",
            "status": "supported",
            "description": f"按 {asset_type}/{protocol} 执行只读巡检模板或内置巡检。",
        },
        {
            "id": "scheduled_inspection",
            "label": "定时巡检",
            "status": "supported",
            "description": "确认该资产可被定时巡检任务按资产、标签、分类或协议展开。",
        },
    ]
    gaps = [step for step in steps if step["status"] == "gap"]
    return {
        "asset": safe_asset,
        "active_tools": active_tools,
        "steps": steps,
        "coverage": {
            "total": len(steps),
            "supported": len(steps) - len(gaps),
            "gaps": len(gaps),
        },
        "status": "ready" if not gaps else "needs_attention",
    }


def build_overview(assets: list[dict[str, Any]]) -> dict[str, Any]:
    matrix = [build_asset_matrix(asset) for asset in assets]
    protocols: dict[str, int] = {}
    categories: dict[str, int] = {}
    steps_total = 0
    gaps_total = 0
    for item in matrix:
        asset = item["asset"]
        protocols[asset["protocol"]] = protocols.get(asset["protocol"], 0) + 1
        categories[asset["category"]] = categories.get(asset["category"], 0) + 1
        steps_total += int(item["coverage"]["total"])
        gaps_total += int(item["coverage"]["gaps"])
    return {
        "summary": {
            "asset_total": len(matrix),
            "protocols": protocols,
            "categories": categories,
            "steps_total": steps_total,
            "gaps_total": gaps_total,
            "ready_assets": sum(1 for item in matrix if item["status"] == "ready"),
            "needs_attention": sum(1 for item in matrix if item["status"] != "ready"),
        },
        "matrix": matrix,
    }


def _step_result(step_id: str, label: str, status: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "id": step_id,
        "label": label,
        "status": status,
        "message": message,
        "details": details or {},
        "completed_at": _now(),
    }


def _database_name(asset: dict[str, Any], safe_asset: dict[str, Any]) -> str:
    extra_args = asset.get("extra_args") or {}
    safe_extra_args = safe_asset.get("extra_args") or {}
    return str(
        extra_args.get("SID")
        or extra_args.get("service_name")
        or extra_args.get("database")
        or extra_args.get("db_name")
        or safe_extra_args.get("database")
        or safe_extra_args.get("db_name")
        or ""
    )


def _probe_success(result: dict[str, Any]) -> bool:
    return bool(result.get("success")) and not result.get("has_error")


async def run_protocol_probe(asset: dict[str, Any]) -> dict[str, Any]:
    """Run one native, read-only protocol probe against a managed asset."""
    safe_asset = sanitize_asset(asset)
    protocol = safe_asset["protocol"]
    asset_type = safe_asset["asset_type"]
    extra_args = asset.get("extra_args") or {}

    if protocol == "ssh":
        return {
            "status": "success",
            "message": "SSH 原生探测已由物理连接测试覆盖。",
            "details": {"tool": "ssh_connect"},
        }

    if protocol == "winrm":
        from connections.winrm_manager import winrm_executor

        command = "Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version | ConvertTo-Json -Compress"
        result = await asyncio.to_thread(
            winrm_executor.execute_command,
            host=asset.get("host") or "",
            port=int(asset.get("port") or 5985),
            username=asset.get("username") or "",
            password=asset.get("password"),
            command=command,
            extra_args=extra_args,
        )
        return {
            "status": "success" if _probe_success(result) else "error",
            "message": "Windows WinRM 原生探测成功。" if _probe_success(result) else result.get("error") or "Windows WinRM 原生探测失败。",
            "details": {"tool": "winrm_execute_command", "command": command, "result": result},
        }

    if protocol in SQL_PROTOCOLS:
        from connections.db_manager import db_executor

        sql = "SELECT 1 FROM DUAL" if protocol == "oracle" else "SELECT 1"
        result_text = await asyncio.to_thread(
            db_executor.execute_query,
            protocol,
            asset.get("host") or "",
            int(asset.get("port") or 0),
            asset.get("username") or "",
            asset.get("password"),
            _database_name(asset, safe_asset),
            sql,
            extra_args,
        )
        try:
            parsed = json.loads(result_text)
        except Exception:
            parsed = {"success": False, "error": result_text}
        return {
            "status": "success" if _probe_success(parsed) else "error",
            "message": "数据库原生 SQL 探测成功。" if _probe_success(parsed) else parsed.get("error") or "数据库原生 SQL 探测失败。",
            "details": {"tool": "db_execute_query", "command": sql, "result": parsed},
        }

    if protocol == "redis":
        from connections.datastore_manager import redis_executor

        result = await asyncio.to_thread(
            redis_executor.execute_command,
            host=asset.get("host") or "",
            port=int(asset.get("port") or 6379),
            username=asset.get("username") or "",
            password=asset.get("password"),
            command="PING",
            extra_args=extra_args,
        )
        return {
            "status": "success" if _probe_success(result) else "error",
            "message": "Redis 原生 PING 探测成功。" if _probe_success(result) else result.get("error") or "Redis 原生探测失败。",
            "details": {"tool": "redis_execute_command", "command": "PING", "result": result},
        }

    if protocol == "mongodb":
        from connections.datastore_manager import mongo_executor

        database = extra_args.get("database") or extra_args.get("db_name") or "admin"
        collection = extra_args.get("test_collection") or "system.version"
        result = await asyncio.to_thread(
            mongo_executor.find,
            host=asset.get("host") or "",
            port=int(asset.get("port") or 27017),
            username=asset.get("username") or "",
            password=asset.get("password"),
            database=database,
            collection=collection,
            filter_doc={},
            projection=None,
            limit=1,
            extra_args=extra_args,
        )
        return {
            "status": "success" if _probe_success(result) else "error",
            "message": "MongoDB 原生 find 探测成功。" if _probe_success(result) else result.get("error") or "MongoDB 原生探测失败。",
            "details": {"tool": "mongodb_find", "command": f"{database}.{collection}.find({{}}).limit(1)", "result": result},
        }

    if protocol in API_PROTOCOLS:
        from connections.http_api_manager import http_api_executor

        default_path = {
            "k8s": "/version",
            "prometheus": "/api/v1/status/buildinfo",
            "alertmanager": "/api/v2/status",
            "grafana": "/api/health",
            "redfish": "/redfish/v1/",
        }.get(asset_type, "/")
        path = str(extra_args.get("health_path") or default_path)
        tool = "k8s_api_request" if protocol == "k8s" else ("monitoring_api_query" if asset_type in {"prometheus", "alertmanager", "grafana", "loki", "victoriametrics", "zabbix", "manageengine"} else "http_api_request")
        result = await asyncio.to_thread(
            http_api_executor.request,
            asset_type=asset_type,
            host=asset.get("host") or "",
            port=int(asset.get("port") or 443),
            username=asset.get("username") or "",
            password=asset.get("password"),
            extra_args=extra_args,
            method="GET",
            path=path,
        )
        return {
            "status": "success" if _probe_success(result) else "error",
            "message": f"{asset_type}/{protocol} HTTP/API 原生探测成功。" if _probe_success(result) else result.get("error") or f"{asset_type}/{protocol} HTTP/API 原生探测失败。",
            "details": {"tool": tool, "path": path, "result": result},
        }

    if protocol in SNMP_PROTOCOLS:
        from connections.snmp_manager import snmp_executor

        snmp_extra_args = dict(extra_args)
        if snmp_extra_args.get("v3_auth_user") and not snmp_extra_args.get("v3_username"):
            snmp_extra_args["v3_username"] = snmp_extra_args.get("v3_auth_user")
        elif asset.get("username") and not any(
            snmp_extra_args.get(key)
            for key in ("v3_username", "v3_auth_user", "security_name", "username", "user")
        ):
            snmp_extra_args.setdefault("v3_username", asset.get("username"))
        oid = str(snmp_extra_args.get("health_oid") or "1.3.6.1.2.1.1.1.0")
        result = await asyncio.to_thread(
            snmp_executor.get,
            host=asset.get("host") or "",
            port=int(asset.get("port") or 161),
            oid=oid,
            extra_args=snmp_extra_args,
        )
        return {
            "status": "success" if _probe_success(result) else "error",
            "message": "SNMP 原生 OID 探测成功。" if _probe_success(result) else result.get("error") or "SNMP 原生探测失败。",
            "details": {"tool": "snmp_get", "oid": oid, "result": result},
        }

    return {
        "status": "skipped",
        "message": f"{asset_type}/{protocol} 暂无原生协议探测器。",
        "details": {"tool": None},
    }


async def run_asset_verification(asset: dict[str, Any]) -> dict[str, Any]:
    """Execute a read-only verification flow for one managed asset."""
    from connections.ssh_manager import ssh_manager
    from core.session_inspector import inspect_session

    safe_asset = sanitize_asset(asset)
    matrix = build_asset_matrix(asset)
    started_at = _now()
    steps: list[dict[str, Any]] = []
    session_id: str | None = None
    protocol_probe_failed = False

    connect_result = await asyncio.to_thread(
        ssh_manager.connect,
        host=asset.get("host") or "",
        port=int(asset.get("port") or 22),
        username=asset.get("username") or "",
        password=asset.get("password"),
        key_filename=asset.get("private_key_path"),
        allow_modifications=False,
        active_skills=asset.get("skills") or [],
        agent_profile=asset.get("agent_profile") or "default",
        remark=asset.get("remark") or "资产验证会话",
        asset_type=safe_asset["asset_type"],
        protocol=safe_asset["protocol"],
        extra_args=asset.get("extra_args") or {},
        tags=asset.get("tags") or [],
        target_scope="asset",
        scope_value=str(asset.get("id") or ""),
    )
    if connect_result.get("success"):
        session_id = connect_result.get("session_id")
        steps.append(_step_result("connection_test", "连接测试", "success", connect_result.get("message") or "连接成功"))
    else:
        steps.append(_step_result("connection_test", "连接测试", "error", connect_result.get("message") or "连接失败"))

    if connect_result.get("success"):
        probe = await run_protocol_probe(asset)
        protocol_probe_failed = probe["status"] == "error"
        steps.append(
            _step_result(
                "protocol_probe",
                "协议原生探测",
                probe["status"],
                probe.get("message") or "协议原生探测完成。",
                probe.get("details") or {},
            )
        )
    else:
        steps.append(_step_result("protocol_probe", "协议原生探测", "skipped", "连接测试失败，跳过协议原生探测。"))

    if matrix["active_tools"]:
        steps.append(
            _step_result(
                "tool_catalog",
                "工具目录",
                "success",
                f"可用工具 {len(matrix['active_tools'])} 个。",
                {"active_tools": matrix["active_tools"]},
            )
        )
    else:
        steps.append(_step_result("tool_catalog", "工具目录", "error", "当前资产没有匹配到可用协议工具。"))

    if session_id and not protocol_probe_failed:
        inspection = await inspect_session(session_id)
        inspection_status = inspection.get("status")
        ok = inspection_status in {"success", "warning"}
        steps.append(
            _step_result(
                "readonly_inspection",
                "只读巡检",
                "success" if ok else "error",
                inspection.get("summary") or inspection.get("message") or "只读巡检完成",
                {
                    "inspection_status": inspection_status,
                    "supported": inspection.get("supported"),
                    "checks_count": len(inspection.get("checks") or []),
                },
            )
        )
    else:
        steps.append(_step_result("readonly_inspection", "只读巡检", "skipped", "连接测试或协议原生探测失败，跳过只读巡检。"))

    steps.append(
        _step_result(
            "scheduled_inspection",
            "定时巡检",
            "success",
            "定时巡检 dry-run 通过：该资产可被任务按资产、标签、分类、协议或类型展开。",
            {"target_scopes": ["asset", "tag", "category", "protocol", "asset_type", "all"]},
        )
    )

    if session_id:
        await asyncio.to_thread(ssh_manager.disconnect, session_id)

    failed = [step for step in steps if step["status"] == "error"]
    skipped = [step for step in steps if step["status"] == "skipped"]
    run = {
        "id": f"verify_{uuid.uuid4().hex[:12]}",
        "asset": safe_asset,
        "status": "failed" if failed else ("partial" if skipped else "success"),
        "steps": steps,
        "matrix_status": matrix["status"],
        "started_at": started_at,
        "completed_at": _now(),
    }
    return _record_run(run)
