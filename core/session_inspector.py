"""Read-only session inspection routines."""

from __future__ import annotations

import asyncio
import json
import socket
import urllib.error
import urllib.request
from typing import Any

from connections.ssh_manager import ssh_manager
from core.asset_protocols import (
    API_PROTOCOLS,
    SQL_PROTOCOLS,
    SNMP_PROTOCOLS,
    get_asset_definition,
    normalize_protocol,
)


LINUX_INSPECTION_COMMANDS = [
    {
        "name": "identity",
        "title": "系统身份",
        "command": "uname -srm && whoami && hostname",
        "timeout": 10,
    },
    {
        "name": "uptime",
        "title": "运行时间与负载",
        "command": "uptime",
        "timeout": 10,
    },
    {
        "name": "memory",
        "title": "内存概览",
        "command": "free -m",
        "timeout": 10,
    },
    {
        "name": "disk",
        "title": "磁盘概览",
        "command": "df -hP | head -20",
        "timeout": 10,
    },
    {
        "name": "top_processes",
        "title": "资源占用最高进程",
        "command": "ps -eo pid,ppid,comm,%cpu,%mem --sort=-%cpu | head -10",
        "timeout": 10,
    },
]

NETWORK_CLI_INSPECTION_COMMANDS = [
    {
        "name": "version",
        "title": "设备版本与运行时间",
        "command": "display version",
        "timeout": 15,
    },
    {
        "name": "cpu",
        "title": "CPU 状态",
        "command": "display cpu-usage",
        "timeout": 10,
    },
    {
        "name": "memory",
        "title": "内存状态",
        "command": "display memory",
        "timeout": 10,
    },
    {
        "name": "interfaces",
        "title": "接口摘要",
        "command": "display interface brief",
        "timeout": 15,
    },
]


def _profile_for(asset_type: str, protocol: str) -> str | None:
    definition = get_asset_definition(asset_type)
    if definition:
        return definition.get("inspection_profile")
    if protocol == "ssh" and asset_type in {"ssh", "linux", "kvm"}:
        return "linux"
    if protocol == "winrm":
        return "winrm"
    return None


async def _inspect_with_template(
    session_id: str,
    info: dict[str, Any],
    asset_type: str,
    protocol: str,
    template: dict[str, Any],
) -> dict[str, Any]:
    checks = []
    extra_args = info.get("extra_args") or {}

    for step in template.get("steps", []):
        tool = step.get("tool")
        result: dict[str, Any]
        command = step.get("command") or step.get("sql") or step.get("path") or step.get("oid") or ""

        if tool in {
            "linux_execute_command",
            "container_execute_command",
            "middleware_execute_command",
            "storage_execute_command",
        }:
            result = await asyncio.to_thread(
                ssh_manager.execute_command,
                session_id,
                step.get("command"),
                step.get("timeout") or 15,
            )
        elif tool == "network_cli_execute_command":
            result = await asyncio.to_thread(
                ssh_manager.execute_network_cli_command,
                session_id,
                step.get("command"),
                step.get("timeout") or 15,
            )
        elif tool == "winrm_execute_command":
            from connections.winrm_manager import winrm_executor

            result = await asyncio.to_thread(
                winrm_executor.execute_command,
                host=info.get("host"),
                port=info.get("port"),
                username=info.get("username"),
                password=info.get("password"),
                command=step.get("command"),
                extra_args=extra_args,
            )
        elif tool == "db_execute_query":
            from connections.db_manager import db_executor

            database = (
                extra_args.get("SID")
                or extra_args.get("service_name")
                or extra_args.get("database")
                or extra_args.get("db_name")
                or ""
            )
            result_str = await asyncio.to_thread(
                db_executor.execute_query,
                protocol,
                info.get("host"),
                info.get("port"),
                info.get("username"),
                info.get("password"),
                database,
                step.get("sql") or step.get("command"),
                extra_args,
            )
            result = {"success": True, "output": result_str, "exit_status": 0}
        elif tool == "redis_execute_command":
            from connections.datastore_manager import redis_executor

            result = await asyncio.to_thread(
                redis_executor.execute_command,
                host=info.get("host"),
                port=info.get("port"),
                username=info.get("username") or "",
                password=info.get("password"),
                command=step.get("command"),
                extra_args=extra_args,
            )
        elif tool == "mongodb_find":
            from connections.datastore_manager import mongo_executor

            args = step.get("args") or {}
            result = await asyncio.to_thread(
                mongo_executor.find,
                host=info.get("host"),
                port=info.get("port"),
                username=info.get("username") or "",
                password=info.get("password"),
                database=args.get("database") or extra_args.get("database") or "admin",
                collection=args.get("collection") or "system.version",
                filter_doc=args.get("filter") or {},
                projection=args.get("projection"),
                limit=args.get("limit") or 10,
                extra_args=extra_args,
            )
        elif tool in {
            "http_api_request",
            "k8s_api_request",
            "monitoring_api_query",
            "virtualization_api_request",
            "storage_api_request",
        }:
            from connections.http_api_manager import http_api_executor

            result = await asyncio.to_thread(
                http_api_executor.request,
                asset_type=asset_type,
                host=info.get("host"),
                port=info.get("port"),
                username=info.get("username") or "",
                password=info.get("password"),
                extra_args=extra_args,
                method=step.get("method") or "GET",
                path=step.get("path") or "/",
                headers=(step.get("args") or {}).get("headers") or {},
                body=(step.get("args") or {}).get("body"),
            )
        elif tool == "snmp_get":
            from connections.snmp_manager import snmp_executor

            snmp_extra_args = dict(extra_args)
            if snmp_extra_args.get("v3_auth_user") and not snmp_extra_args.get("v3_username"):
                snmp_extra_args["v3_username"] = snmp_extra_args.get("v3_auth_user")
            elif info.get("username") and not any(
                snmp_extra_args.get(key)
                for key in ("v3_username", "v3_auth_user", "security_name", "username", "user")
            ):
                snmp_extra_args.setdefault("v3_username", info.get("username"))
            result = await asyncio.to_thread(
                snmp_executor.get,
                host=info.get("host"),
                port=info.get("port") or 161,
                oid=step.get("oid") or "1.3.6.1.2.1.1.1.0",
                extra_args=snmp_extra_args,
            )
        else:
            result = {"success": False, "error": f"不支持的巡检工具: {tool}"}

        success = bool(result.get("success")) and not result.get("has_error")
        output = result.get("output") or result.get("error") or json.dumps(result, ensure_ascii=False, default=str)
        checks.append(
            {
                "name": step.get("name"),
                "title": step.get("title") or step.get("name"),
                "status": "success" if success else "error",
                "command": command,
                "output": output,
                "exit_status": result.get("exit_status") if "exit_status" in result else (0 if success else None),
            }
        )

    failed = [check for check in checks if check["status"] != "success"]
    return {
        "status": "success" if not failed else "warning",
        "supported": True,
        "asset_type": asset_type,
        "protocol": protocol,
        "profile": "template",
        "template_id": template.get("id"),
        "summary": f"按模板 {template.get('name') or template.get('id')} 完成 {len(checks)} 项只读巡检，异常 {len(failed)} 项。",
        "checks": checks,
    }


def _http_probe_url(info: dict[str, Any], asset_type: str) -> str:
    from connections.http_api_manager import build_base_url

    extra_args = info.get("extra_args") or {}
    default_path = {
        "prometheus": "/api/v1/status/buildinfo",
        "zabbix": "/api_jsonrpc.php",
        "vmware": "/",
        "f5": "/",
        "redfish": "/redfish/v1/",
        "manageengine": "/",
        "elasticsearch": "/",
    }.get(asset_type, "/")
    path = str(extra_args.get("health_path") or default_path)
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{build_base_url(info.get('host'), info.get('port'), extra_args)}{path}"


async def _inspect_http_api(info: dict[str, Any], asset_type: str, protocol: str) -> dict[str, Any]:
    from connections.http_api_manager import build_base_url
    from urllib.parse import urlparse

    parsed = urlparse(build_base_url(info.get("host"), info.get("port"), info.get("extra_args") or {}))
    host = parsed.hostname or info.get("host")
    port = parsed.port or int(info.get("port") or 443)
    checks = []

    try:
        with socket.create_connection((host, port), timeout=5):
            pass
        checks.append(
            {
                "name": "tcp",
                "title": "TCP 连通性",
                "status": "success",
                "output": f"{host}:{port} 可达",
                "exit_status": 0,
            }
        )
    except Exception as e:
        checks.append(
            {
                "name": "tcp",
                "title": "TCP 连通性",
                "status": "error",
                "output": str(e),
                "exit_status": None,
            }
        )
        return {
            "status": "error",
            "supported": True,
            "asset_type": asset_type,
            "protocol": protocol,
            "profile": "http_api",
            "summary": "TCP 连通性失败，未继续执行 HTTP 探测。",
            "checks": checks,
        }

    url = _http_probe_url(info, asset_type)
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = resp.read(4096).decode("utf-8", errors="replace")
            status_code = resp.getcode()
    except urllib.error.HTTPError as e:
        status_code = e.code
        body = e.read(1024).decode("utf-8", errors="replace")
    except Exception as e:
        checks.append(
            {
                "name": "http_probe",
                "title": "HTTP/API 探测",
                "status": "warning",
                "output": f"{url} 探测失败: {e}",
                "exit_status": None,
            }
        )
    else:
        checks.append(
            {
                "name": "http_probe",
                "title": "HTTP/API 探测",
                "status": "success" if status_code < 500 else "warning",
                "output": f"{url} HTTP {status_code}\n{body[:1000]}",
                "exit_status": status_code,
            }
        )

    failed = [check for check in checks if check["status"] == "error"]
    return {
        "status": "success" if not failed else "warning",
        "supported": True,
        "asset_type": asset_type,
        "protocol": protocol,
        "profile": "http_api",
        "summary": f"完成 {len(checks)} 项 HTTP/API 只读巡检，错误 {len(failed)} 项。",
        "checks": checks,
    }


async def _inspect_sql(info: dict[str, Any], asset_type: str, protocol: str) -> dict[str, Any]:
    from connections.db_manager import db_executor

    extra_args = info.get("extra_args") or {}
    database = (
        extra_args.get("SID")
        or extra_args.get("service_name")
        or extra_args.get("database")
        or extra_args.get("db_name")
        or ""
    )
    sql = "SELECT 1 FROM DUAL" if protocol == "oracle" else "SELECT 1"
    result_str = await asyncio.to_thread(
        db_executor.execute_query,
        protocol,
        info.get("host"),
        info.get("port"),
        info.get("username"),
        info.get("password"),
        database,
        sql,
        extra_args,
    )
    try:
        result = json.loads(result_str)
    except Exception:
        result = {"success": False, "error": result_str}

    success = bool(result.get("success"))
    return {
        "status": "success" if success else "error",
        "supported": True,
        "asset_type": asset_type,
        "protocol": protocol,
        "profile": "sql",
        "summary": "数据库只读巡检完成。" if success else "数据库只读巡检失败。",
        "checks": [
            {
                "name": "sql_ping",
                "title": "数据库只读 SQL 探测",
                "status": "success" if success else "error",
                "command": sql,
                "output": result_str,
                "exit_status": 0 if success else None,
            }
        ],
    }


async def _inspect_redis(info: dict[str, Any], asset_type: str, protocol: str) -> dict[str, Any]:
    from connections.datastore_manager import redis_executor

    result = await asyncio.to_thread(
        redis_executor.execute_command,
        host=info.get("host"),
        port=info.get("port"),
        username=info.get("username") or "",
        password=info.get("password"),
        command="PING",
        extra_args=info.get("extra_args") or {},
    )
    success = bool(result.get("success"))
    return {
        "status": "success" if success else "error",
        "supported": True,
        "asset_type": asset_type,
        "protocol": protocol,
        "profile": "redis",
        "summary": "Redis 只读巡检完成。" if success else "Redis 只读巡检失败。",
        "checks": [
            {
                "name": "redis_ping",
                "title": "Redis PING 探测",
                "status": "success" if success else "error",
                "command": "PING",
                "output": json.dumps(result, ensure_ascii=False, default=str),
                "exit_status": 0 if success else None,
            }
        ],
    }


async def _inspect_mongodb(info: dict[str, Any], asset_type: str, protocol: str) -> dict[str, Any]:
    from connections.datastore_manager import mongo_executor

    extra_args = info.get("extra_args") or {}
    database = extra_args.get("database") or extra_args.get("db_name") or "admin"
    result = await asyncio.to_thread(
        mongo_executor.find,
        host=info.get("host"),
        port=info.get("port"),
        username=info.get("username") or "",
        password=info.get("password"),
        database=database,
        collection=str(extra_args.get("test_collection") or "system.version"),
        filter_doc={},
        limit=1,
        extra_args=extra_args,
    )
    success = bool(result.get("success"))
    return {
        "status": "success" if success else "error",
        "supported": True,
        "asset_type": asset_type,
        "protocol": protocol,
        "profile": "mongodb",
        "summary": "MongoDB 只读巡检完成。" if success else "MongoDB 只读巡检失败。",
        "checks": [
            {
                "name": "mongodb_find",
                "title": "MongoDB 只读 find 探测",
                "status": "success" if success else "error",
                "command": f"{database}.{extra_args.get('test_collection') or 'system.version'}.find({{}}).limit(1)",
                "output": json.dumps(result, ensure_ascii=False, default=str),
                "exit_status": 0 if success else None,
            }
        ],
    }


async def _inspect_snmp(info: dict[str, Any], asset_type: str, protocol: str) -> dict[str, Any]:
    from connections.snmp_manager import snmp_executor

    extra_args = dict(info.get("extra_args") or {})
    if extra_args.get("v3_auth_user") and not extra_args.get("v3_username"):
        extra_args["v3_username"] = extra_args.get("v3_auth_user")
    elif info.get("username") and not any(
        extra_args.get(key)
        for key in ("v3_username", "v3_auth_user", "security_name", "username", "user")
    ):
        extra_args.setdefault("v3_username", info.get("username"))
    oid = str(extra_args.get("health_oid") or "1.3.6.1.2.1.1.1.0")
    result = await asyncio.to_thread(
        snmp_executor.get,
        host=info.get("host"),
        port=info.get("port") or 161,
        oid=oid,
        extra_args=extra_args,
    )
    success = bool(result.get("success"))
    return {
        "status": "success" if success else "error",
        "supported": True,
        "asset_type": asset_type,
        "protocol": protocol,
        "profile": "snmp",
        "summary": "SNMP 只读巡检完成。" if success else "SNMP 只读巡检失败。",
        "checks": [
            {
                "name": "snmp_get",
                "title": "SNMP System Description",
                "status": "success" if success else "error",
                "command": oid,
                "output": json.dumps(result, ensure_ascii=False, default=str),
                "exit_status": 0 if success else None,
            }
        ],
    }


async def _inspect_network_cli(session_id: str, asset_type: str, protocol: str) -> dict[str, Any]:
    checks = []
    for spec in NETWORK_CLI_INSPECTION_COMMANDS:
        result = await asyncio.to_thread(
            ssh_manager.execute_network_cli_command,
            session_id,
            spec["command"],
            spec["timeout"],
        )
        success = bool(result.get("success")) and not result.get("has_error")
        checks.append(
            {
                "name": spec["name"],
                "title": spec["title"],
                "status": "success" if success else "error",
                "command": spec["command"],
                "output": result.get("output") or result.get("error") or "",
                "exit_status": result.get("exit_status"),
            }
        )

    failed = [check for check in checks if check["status"] != "success"]
    return {
        "status": "success" if not failed else "warning",
        "supported": True,
        "asset_type": asset_type,
        "protocol": protocol,
        "profile": "network_cli",
        "summary": f"完成 {len(checks)} 项网络设备 SSH CLI 只读巡检，异常 {len(failed)} 项。",
        "checks": checks,
    }


WINRM_INSPECTION_COMMANDS = [
    {
        "name": "os",
        "title": "Windows 系统信息",
        "command": "Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,LastBootUpTime | ConvertTo-Json -Compress",
    },
    {
        "name": "cpu_memory",
        "title": "CPU 与内存",
        "command": "Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize,FreePhysicalMemory; Get-CimInstance Win32_Processor | Select-Object Name,LoadPercentage",
    },
    {
        "name": "disk",
        "title": "磁盘概览",
        "command": "Get-CimInstance Win32_LogicalDisk -Filter \"DriveType=3\" | Select-Object DeviceID,Size,FreeSpace | ConvertTo-Json -Compress",
    },
]


async def _inspect_winrm(info: dict[str, Any], asset_type: str, protocol: str) -> dict[str, Any]:
    from connections.winrm_manager import winrm_executor

    checks = []
    for spec in WINRM_INSPECTION_COMMANDS:
        result = await asyncio.to_thread(
            winrm_executor.execute_command,
            host=info.get("host"),
            port=info.get("port"),
            username=info.get("username"),
            password=info.get("password"),
            command=spec["command"],
            extra_args=info.get("extra_args") or {},
        )
        success = bool(result.get("success"))
        checks.append(
            {
                "name": spec["name"],
                "title": spec["title"],
                "status": "success" if success else "error",
                "command": spec["command"],
                "output": result.get("output") or result.get("error") or "",
                "exit_status": result.get("exit_status"),
            }
        )

    failed = [check for check in checks if check["status"] != "success"]
    return {
        "status": "success" if not failed else "warning",
        "supported": True,
        "asset_type": asset_type,
        "protocol": protocol,
        "profile": "winrm",
        "summary": f"完成 {len(checks)} 项 Windows WinRM 只读巡检，异常 {len(failed)} 项。",
        "checks": checks,
    }


async def inspect_session(session_id: str) -> dict[str, Any]:
    session = ssh_manager.active_sessions.get(session_id)
    if not session:
        return {
            "status": "error",
            "supported": False,
            "message": "会话不存在或已断开",
            "checks": [],
        }

    info = session.get("info", {})
    asset_type = str(info.get("asset_type") or "").lower()
    protocol = normalize_protocol(
        asset_type,
        info.get("protocol"),
        info.get("extra_args", {}),
        info.get("host"),
        info.get("port"),
        info.get("remark"),
    )
    profile = _profile_for(asset_type, protocol)

    try:
        from core.inspection_templates import find_matching_template

        template = find_matching_template(asset_type, protocol)
    except Exception:
        template = None
    if template:
        return await _inspect_with_template(session_id, info, asset_type, protocol, template)

    if protocol == "ssh" and profile == "linux":
        checks = []
        for spec in LINUX_INSPECTION_COMMANDS:
            result = await asyncio.to_thread(
                ssh_manager.execute_command,
                session_id,
                spec["command"],
                spec["timeout"],
            )
            success = bool(result.get("success")) and not result.get("has_error")
            checks.append(
                {
                    "name": spec["name"],
                    "title": spec["title"],
                    "status": "success" if success else "error",
                    "command": spec["command"],
                    "output": result.get("output") or result.get("error") or "",
                    "exit_status": result.get("exit_status"),
                }
            )

        failed = [check for check in checks if check["status"] != "success"]
        return {
            "status": "success" if not failed else "warning",
            "supported": True,
            "asset_type": asset_type,
            "protocol": protocol,
            "profile": profile,
            "summary": f"完成 {len(checks)} 项只读巡检，异常 {len(failed)} 项。",
            "checks": checks,
        }

    if protocol == "ssh" and profile == "network_cli":
        return await _inspect_network_cli(session_id, asset_type, protocol)

    if protocol == "winrm":
        return await _inspect_winrm(info, asset_type, protocol)

    if protocol in SQL_PROTOCOLS:
        return await _inspect_sql(info, asset_type, protocol)

    if protocol == "redis":
        return await _inspect_redis(info, asset_type, protocol)

    if protocol == "mongodb":
        return await _inspect_mongodb(info, asset_type, protocol)

    if protocol in API_PROTOCOLS:
        return await _inspect_http_api(info, asset_type, protocol)

    if protocol in SNMP_PROTOCOLS:
        return await _inspect_snmp(info, asset_type, protocol)

    return {
        "status": "unsupported",
        "supported": False,
        "asset_type": asset_type,
        "protocol": protocol,
        "profile": profile,
        "message": f"{asset_type or 'unknown'}/{protocol} 暂未接入深度巡检；当前已支持 Linux/KVM SSH、网络设备 SSH CLI、Windows WinRM、SQL、Redis、MongoDB、SNMP 与 HTTP/API 只读巡检。",
        "checks": [],
    }
