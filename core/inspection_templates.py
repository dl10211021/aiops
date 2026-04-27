"""CRUD storage and validation for read-only inspection templates."""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_STORE_PATH = ROOT_DIR / "inspection_templates.json"

_LOCK = threading.RLock()

ALLOWED_TOOLS = {
    "linux_execute_command",
    "container_execute_command",
    "middleware_execute_command",
    "storage_execute_command",
    "network_cli_execute_command",
    "winrm_execute_command",
    "db_execute_query",
    "redis_execute_command",
    "mongodb_find",
    "http_api_request",
    "k8s_api_request",
    "monitoring_api_query",
    "virtualization_api_request",
    "storage_api_request",
    "snmp_get",
}

BUILTIN_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "builtin-k8s-core-readonly",
        "name": "Kubernetes 核心只读巡检",
        "asset_type": "k8s",
        "protocol": "k8s",
        "enabled": True,
        "builtin": True,
        "readonly": True,
        "steps": [
            {
                "name": "nodes",
                "title": "节点列表",
                "tool": "k8s_api_request",
                "method": "GET",
                "path": "/api/v1/nodes",
                "timeout": 20,
            },
            {
                "name": "pods",
                "title": "Pod 列表",
                "tool": "k8s_api_request",
                "method": "GET",
                "path": "/api/v1/pods",
                "timeout": 20,
            },
            {
                "name": "deployments",
                "title": "Deployment 列表",
                "tool": "k8s_api_request",
                "method": "GET",
                "path": "/apis/apps/v1/deployments",
                "timeout": 20,
            },
            {
                "name": "events",
                "title": "事件列表",
                "tool": "k8s_api_request",
                "method": "GET",
                "path": "/api/v1/events",
                "timeout": 20,
            },
        ],
    },
    {
        "id": "builtin-prometheus-core-readonly",
        "name": "Prometheus 核心只读巡检",
        "asset_type": "prometheus",
        "protocol": "http_api",
        "enabled": True,
        "builtin": True,
        "readonly": True,
        "steps": [
            {
                "name": "build_info",
                "title": "版本信息",
                "tool": "monitoring_api_query",
                "method": "GET",
                "path": "/api/v1/status/buildinfo",
                "timeout": 15,
            },
            {
                "name": "targets",
                "title": "采集目标状态",
                "tool": "monitoring_api_query",
                "method": "GET",
                "path": "/api/v1/targets",
                "timeout": 20,
            },
            {
                "name": "up",
                "title": "Up 指标",
                "tool": "monitoring_api_query",
                "method": "GET",
                "path": "/api/v1/query?query=up",
                "timeout": 20,
            },
            {
                "name": "alerts",
                "title": "当前告警",
                "tool": "monitoring_api_query",
                "method": "GET",
                "path": "/api/v1/query?query=ALERTS",
                "timeout": 20,
            },
            {
                "name": "cpu_usage",
                "title": "CPU 使用率",
                "tool": "monitoring_api_query",
                "method": "GET",
                "path": "/api/v1/query?query=100%20-%20(avg%20by(instance)%20(rate(node_cpu_seconds_total%7Bmode%3D%22idle%22%7D%5B5m%5D))%20*%20100)",
                "timeout": 20,
            },
            {
                "name": "memory_usage",
                "title": "内存使用率",
                "tool": "monitoring_api_query",
                "method": "GET",
                "path": "/api/v1/query?query=(1%20-%20(node_memory_MemAvailable_bytes%20/%20node_memory_MemTotal_bytes))%20*%20100",
                "timeout": 20,
            },
            {
                "name": "disk_usage",
                "title": "磁盘使用率",
                "tool": "monitoring_api_query",
                "method": "GET",
                "path": "/api/v1/query?query=100%20-%20(node_filesystem_avail_bytes%7Bfstype!~%22tmpfs%7Coverlay%22%7D%20*%20100%20/%20node_filesystem_size_bytes%7Bfstype!~%22tmpfs%7Coverlay%22%7D)",
                "timeout": 20,
            },
        ],
    },
    {
        "id": "builtin-windows-core-readonly",
        "name": "Windows 核心只读巡检",
        "asset_type": "windows",
        "protocol": "winrm",
        "enabled": True,
        "builtin": True,
        "readonly": True,
        "steps": [
            {
                "name": "os",
                "title": "系统版本与启动时间",
                "tool": "winrm_execute_command",
                "command": "Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,LastBootUpTime,InstallDate | ConvertTo-Json -Compress",
                "timeout": 20,
            },
            {
                "name": "hardware",
                "title": "硬件资源",
                "tool": "winrm_execute_command",
                "command": "Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model,TotalPhysicalMemory,NumberOfLogicalProcessors | ConvertTo-Json -Compress",
                "timeout": 20,
            },
            {
                "name": "disk",
                "title": "磁盘空间",
                "tool": "winrm_execute_command",
                "command": "Get-CimInstance Win32_LogicalDisk -Filter \"DriveType=3\" | Select-Object DeviceID,Size,FreeSpace | ConvertTo-Json -Compress",
                "timeout": 20,
            },
            {
                "name": "services",
                "title": "异常服务",
                "tool": "winrm_execute_command",
                "command": "Get-Service | Where-Object {$_.Status -ne 'Running'} | Select-Object -First 30 Name,Status,DisplayName | ConvertTo-Json -Compress",
                "timeout": 20,
            },
            {
                "name": "events",
                "title": "近 24 小时系统错误事件",
                "tool": "winrm_execute_command",
                "command": "Get-WinEvent -FilterHashtable @{LogName='System'; Level=1,2; StartTime=(Get-Date).AddDays(-1)} -MaxEvents 20 | Select-Object TimeCreated,Id,ProviderName,LevelDisplayName,Message | ConvertTo-Json -Compress",
                "timeout": 30,
            },
            {
                "name": "hotfixes",
                "title": "最近补丁",
                "tool": "winrm_execute_command",
                "command": "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 10 HotFixID,InstalledOn,Description | ConvertTo-Json -Compress",
                "timeout": 30,
            },
        ],
    },
    {
        "id": "builtin-mysql-core-readonly",
        "name": "MySQL 协议核心只读巡检",
        "asset_type": "*",
        "protocol": "mysql",
        "enabled": True,
        "builtin": True,
        "readonly": True,
        "steps": [
            {
                "name": "version",
                "title": "数据库版本",
                "tool": "db_execute_query",
                "sql": "SELECT VERSION() AS version",
                "timeout": 20,
            },
            {
                "name": "connections",
                "title": "当前连接数",
                "tool": "db_execute_query",
                "sql": "SHOW GLOBAL STATUS LIKE 'Threads_connected'",
                "timeout": 20,
            },
            {
                "name": "slow_queries",
                "title": "慢查询计数",
                "tool": "db_execute_query",
                "sql": "SHOW GLOBAL STATUS LIKE 'Slow_queries'",
                "timeout": 20,
            },
            {
                "name": "innodb_status",
                "title": "InnoDB 状态",
                "tool": "db_execute_query",
                "sql": "SHOW ENGINE INNODB STATUS",
                "timeout": 30,
            },
            {
                "name": "schema_size",
                "title": "库空间 TopN",
                "tool": "db_execute_query",
                "sql": "SELECT table_schema, ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS size_mb FROM information_schema.tables GROUP BY table_schema ORDER BY size_mb DESC LIMIT 20",
                "timeout": 30,
            },
        ],
    },
    {
        "id": "builtin-postgresql-core-readonly",
        "name": "PostgreSQL 协议核心只读巡检",
        "asset_type": "*",
        "protocol": "postgresql",
        "enabled": True,
        "builtin": True,
        "readonly": True,
        "steps": [
            {
                "name": "version",
                "title": "数据库版本",
                "tool": "db_execute_query",
                "sql": "SELECT version() AS version",
                "timeout": 20,
            },
            {
                "name": "connections",
                "title": "连接概览",
                "tool": "db_execute_query",
                "sql": "SELECT state, count(*) AS sessions FROM pg_stat_activity GROUP BY state ORDER BY sessions DESC",
                "timeout": 20,
            },
            {
                "name": "database_stats",
                "title": "数据库统计",
                "tool": "db_execute_query",
                "sql": "SELECT datname, numbackends, xact_commit, xact_rollback, deadlocks FROM pg_stat_database ORDER BY deadlocks DESC LIMIT 20",
                "timeout": 20,
            },
            {
                "name": "active_queries",
                "title": "活跃查询",
                "tool": "db_execute_query",
                "sql": "SELECT pid, state, wait_event_type, wait_event, query FROM pg_stat_activity WHERE state <> 'idle' LIMIT 20",
                "timeout": 20,
            },
            {
                "name": "database_size",
                "title": "库空间 TopN",
                "tool": "db_execute_query",
                "sql": "SELECT datname, pg_size_pretty(pg_database_size(datname)) AS size FROM pg_database ORDER BY pg_database_size(datname) DESC LIMIT 20",
                "timeout": 30,
            },
        ],
    },
    {
        "id": "builtin-oracle-core-readonly",
        "name": "Oracle 核心只读巡检",
        "asset_type": "*",
        "protocol": "oracle",
        "enabled": True,
        "builtin": True,
        "readonly": True,
        "steps": [
            {
                "name": "version",
                "title": "数据库版本",
                "tool": "db_execute_query",
                "sql": "SELECT banner FROM v$version",
                "timeout": 20,
            },
            {
                "name": "connections",
                "title": "会话数",
                "tool": "db_execute_query",
                "sql": "SELECT COUNT(*) AS sessions FROM v$session",
                "timeout": 20,
            },
            {
                "name": "tablespace_usage",
                "title": "表空间使用率",
                "tool": "db_execute_query",
                "sql": "SELECT tablespace_name, ROUND(used_percent, 2) AS used_percent FROM dba_tablespace_usage_metrics ORDER BY used_percent DESC",
                "timeout": 30,
            },
            {
                "name": "wait_events",
                "title": "等待事件 TopN",
                "tool": "db_execute_query",
                "sql": "SELECT event, total_waits, time_waited FROM v$system_event ORDER BY time_waited DESC",
                "timeout": 30,
            },
        ],
    },
    {
        "id": "builtin-mssql-core-readonly",
        "name": "SQL Server 核心只读巡检",
        "asset_type": "*",
        "protocol": "mssql",
        "enabled": True,
        "builtin": True,
        "readonly": True,
        "steps": [
            {
                "name": "version",
                "title": "数据库版本",
                "tool": "db_execute_query",
                "sql": "SELECT @@VERSION AS version",
                "timeout": 20,
            },
            {
                "name": "connections",
                "title": "会话数",
                "tool": "db_execute_query",
                "sql": "SELECT COUNT(*) AS sessions FROM sys.dm_exec_sessions",
                "timeout": 20,
            },
            {
                "name": "wait_stats",
                "title": "等待统计 TopN",
                "tool": "db_execute_query",
                "sql": "SELECT TOP 20 wait_type, wait_time_ms FROM sys.dm_os_wait_stats ORDER BY wait_time_ms DESC",
                "timeout": 30,
            },
            {
                "name": "database_files",
                "title": "数据库文件空间 TopN",
                "tool": "db_execute_query",
                "sql": "SELECT TOP 20 DB_NAME(database_id) AS database_name, name, size * 8 / 1024 AS size_mb FROM sys.master_files ORDER BY size DESC",
                "timeout": 30,
            },
        ],
    },
    {
        "id": "builtin-network-cli-core-readonly",
        "name": "网络设备 SSH CLI 核心只读巡检",
        "asset_type": "network_cli",
        "asset_types": ["switch", "firewall", "vpn"],
        "protocol": "ssh",
        "enabled": True,
        "builtin": True,
        "readonly": True,
        "steps": [
            {
                "name": "version",
                "title": "设备版本与运行时间",
                "tool": "network_cli_execute_command",
                "command": "display version",
                "timeout": 20,
            },
            {
                "name": "cpu",
                "title": "CPU 状态",
                "tool": "network_cli_execute_command",
                "command": "display cpu-usage",
                "timeout": 15,
            },
            {
                "name": "memory",
                "title": "内存状态",
                "tool": "network_cli_execute_command",
                "command": "display memory",
                "timeout": 15,
            },
            {
                "name": "interfaces",
                "title": "接口摘要",
                "tool": "network_cli_execute_command",
                "command": "display interface brief",
                "timeout": 20,
            },
            {
                "name": "interface_errors",
                "title": "接口错误包",
                "tool": "network_cli_execute_command",
                "command": "display interface | include CRC|error|discard",
                "timeout": 30,
            },
            {
                "name": "neighbors",
                "title": "LLDP 邻居",
                "tool": "network_cli_execute_command",
                "command": "display lldp neighbor brief",
                "timeout": 20,
            },
        ],
    },
    {
        "id": "builtin-snmp-core-readonly",
        "name": "SNMP 核心只读巡检",
        "asset_type": "*",
        "protocol": "snmp",
        "enabled": True,
        "builtin": True,
        "readonly": True,
        "steps": [
            {
                "name": "system_description",
                "title": "系统描述",
                "tool": "snmp_get",
                "oid": "1.3.6.1.2.1.1.1.0",
                "timeout": 15,
            },
            {
                "name": "system_uptime",
                "title": "系统运行时间",
                "tool": "snmp_get",
                "oid": "1.3.6.1.2.1.1.3.0",
                "timeout": 15,
            },
            {
                "name": "interface_count",
                "title": "接口数量",
                "tool": "snmp_get",
                "oid": "1.3.6.1.2.1.2.1.0",
                "timeout": 15,
            },
            {
                "name": "system_name",
                "title": "系统名称",
                "tool": "snmp_get",
                "oid": "1.3.6.1.2.1.1.5.0",
                "timeout": 15,
            },
        ],
    },
    {
        "id": "builtin-vmware-core-readonly",
        "name": "VMware 核心只读巡检",
        "asset_type": "vmware",
        "protocol": "http_api",
        "enabled": True,
        "builtin": True,
        "readonly": True,
        "steps": [
            {
                "name": "version",
                "title": "vCenter 版本",
                "tool": "virtualization_api_request",
                "method": "GET",
                "path": "/api/appliance/system/version",
                "timeout": 20,
            },
            {
                "name": "hosts",
                "title": "主机列表",
                "tool": "virtualization_api_request",
                "method": "GET",
                "path": "/api/vcenter/host",
                "timeout": 30,
            },
            {
                "name": "vms",
                "title": "虚拟机列表",
                "tool": "virtualization_api_request",
                "method": "GET",
                "path": "/api/vcenter/vm",
                "timeout": 30,
            },
            {
                "name": "datastores",
                "title": "数据存储",
                "tool": "virtualization_api_request",
                "method": "GET",
                "path": "/api/vcenter/datastore",
                "timeout": 30,
            },
        ],
    },
    {
        "id": "builtin-proxmox-core-readonly",
        "name": "Proxmox VE 核心只读巡检",
        "asset_type": "proxmox",
        "protocol": "http_api",
        "enabled": True,
        "builtin": True,
        "readonly": True,
        "steps": [
            {
                "name": "version",
                "title": "Proxmox 版本",
                "tool": "virtualization_api_request",
                "method": "GET",
                "path": "/api2/json/version",
                "timeout": 20,
            },
            {
                "name": "nodes",
                "title": "节点列表",
                "tool": "virtualization_api_request",
                "method": "GET",
                "path": "/api2/json/nodes",
                "timeout": 30,
            },
            {
                "name": "resources",
                "title": "集群资源",
                "tool": "virtualization_api_request",
                "method": "GET",
                "path": "/api2/json/cluster/resources",
                "timeout": 30,
            },
            {
                "name": "storage",
                "title": "存储列表",
                "tool": "virtualization_api_request",
                "method": "GET",
                "path": "/api2/json/storage",
                "timeout": 30,
            },
        ],
    },
    {
        "id": "builtin-kvm-core-readonly",
        "name": "KVM/Libvirt 核心只读巡检",
        "asset_type": "kvm",
        "protocol": "ssh",
        "enabled": True,
        "builtin": True,
        "readonly": True,
        "steps": [
            {
                "name": "nodeinfo",
                "title": "宿主机虚拟化信息",
                "tool": "linux_execute_command",
                "command": "virsh nodeinfo",
                "timeout": 20,
            },
            {
                "name": "vms",
                "title": "虚拟机列表",
                "tool": "linux_execute_command",
                "command": "virsh list --all",
                "timeout": 20,
            },
            {
                "name": "storage_pools",
                "title": "存储池",
                "tool": "linux_execute_command",
                "command": "virsh pool-list --all",
                "timeout": 20,
            },
            {
                "name": "networks",
                "title": "虚拟网络",
                "tool": "linux_execute_command",
                "command": "virsh net-list --all",
                "timeout": 20,
            },
            {
                "name": "disk",
                "title": "宿主机磁盘",
                "tool": "linux_execute_command",
                "command": "df -hP",
                "timeout": 20,
            },
        ],
    },
    {
        "id": "builtin-redfish-core-readonly",
        "name": "Redfish 硬件核心只读巡检",
        "asset_type": "redfish",
        "protocol": "redfish",
        "enabled": True,
        "builtin": True,
        "readonly": True,
        "steps": [
            {
                "name": "service_root",
                "title": "Redfish Service Root",
                "tool": "http_api_request",
                "method": "GET",
                "path": "/redfish/v1/",
                "timeout": 20,
            },
            {
                "name": "systems",
                "title": "服务器系统",
                "tool": "http_api_request",
                "method": "GET",
                "path": "/redfish/v1/Systems",
                "timeout": 30,
            },
            {
                "name": "chassis",
                "title": "机箱硬件",
                "tool": "http_api_request",
                "method": "GET",
                "path": "/redfish/v1/Chassis",
                "timeout": 30,
            },
            {
                "name": "managers",
                "title": "带外管理器",
                "tool": "http_api_request",
                "method": "GET",
                "path": "/redfish/v1/Managers",
                "timeout": 30,
            },
        ],
    },
]

UNSAFE_PATTERNS = [
    r"\brm\s+",
    r"\bdel\s+",
    r"\bdelete\b",
    r"\bdrop\b",
    r"\btruncate\b",
    r"\binsert\b",
    r"\bupdate\b",
    r"\breplace\b",
    r"\brestart\b",
    r"\bstop\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bkill\b",
    r"\bsystemctl\s+(restart|stop|disable|mask)",
    r"\bdocker\s+(rm|rmi|stop|restart|exec|cp)",
    r"\bkubectl\s+(delete|apply|create|replace|patch|scale)",
]


def _read_store() -> list[dict[str, Any]]:
    if not TEMPLATE_STORE_PATH.exists():
        return []
    try:
        data = json.loads(TEMPLATE_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _write_store(items: list[dict[str, Any]]) -> None:
    TEMPLATE_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TEMPLATE_STORE_PATH.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _clean_id(value: object) -> str:
    raw = str(value or "").strip().lower()
    return re.sub(r"[^a-z0-9_.-]+", "-", raw).strip("-")


def _assert_safe_text(value: object, field_name: str) -> None:
    text = str(value or "").strip().lower()
    if not text:
        return
    for pattern in UNSAFE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            raise ValueError(f"{field_name} 包含非只读或高风险片段: {pattern}")


def normalize_template(template: dict[str, Any]) -> dict[str, Any]:
    template_id = _clean_id(template.get("id") or template.get("name"))
    if not template_id:
        raise ValueError("巡检模板 id 不能为空")

    steps = template.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("巡检模板至少需要一个 step")

    normalized_steps = []
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise ValueError(f"step #{index} 必须是对象")
        tool = str(step.get("tool") or "").strip()
        if tool not in ALLOWED_TOOLS:
            raise ValueError(f"step #{index} 使用了不支持的工具: {tool}")

        method = str(step.get("method") or "GET").upper()
        if method not in {"GET", "HEAD"}:
            raise ValueError("巡检模板只允许 GET/HEAD 类只读 HTTP 方法")

        _assert_safe_text(step.get("command"), "command")
        _assert_safe_text(step.get("sql"), "sql")
        _assert_safe_text(step.get("path"), "path")

        normalized_steps.append(
            {
                "name": _clean_id(step.get("name") or f"step-{index}"),
                "title": str(step.get("title") or step.get("name") or f"Step {index}").strip(),
                "tool": tool,
                "command": str(step.get("command") or "").strip(),
                "sql": str(step.get("sql") or "").strip(),
                "path": str(step.get("path") or "").strip(),
                "oid": str(step.get("oid") or "").strip(),
                "method": method,
                "timeout": int(step.get("timeout") or 15),
                "args": step.get("args") if isinstance(step.get("args"), dict) else {},
            }
        )

    is_builtin = bool(template.get("builtin"))
    source = "builtin" if is_builtin else str(template.get("source") or "custom").strip() or "custom"

    asset_types = template.get("asset_types")
    if isinstance(asset_types, list):
        normalized_asset_types = [
            item
            for item in (str(value or "").strip().lower() for value in asset_types)
            if item
        ]
    else:
        normalized_asset_types = []
    asset_type = str(template.get("asset_type") or "*").strip().lower()
    if not normalized_asset_types:
        normalized_asset_types = [asset_type]

    return {
        "id": template_id,
        "name": str(template.get("name") or template_id).strip(),
        "asset_type": asset_type,
        "asset_types": normalized_asset_types,
        "protocol": str(template.get("protocol") or "*").strip().lower(),
        "enabled": bool(template.get("enabled", True)),
        "builtin": is_builtin,
        "readonly": bool(template.get("readonly", is_builtin)),
        "source": source,
        "steps": normalized_steps,
    }


def _builtin_template_ids() -> set[str]:
    return {_clean_id(item.get("id")) for item in BUILTIN_TEMPLATES}


def _normalize_builtin_templates(include_disabled: bool = True) -> list[dict[str, Any]]:
    templates = [normalize_template({**item, "builtin": True, "readonly": True}) for item in BUILTIN_TEMPLATES]
    if include_disabled:
        return templates
    return [item for item in templates if item.get("enabled")]


def _normalize_custom_templates(include_disabled: bool = True) -> list[dict[str, Any]]:
    templates = [
        {
            **normalize_template(item),
            "builtin": False,
            "readonly": bool(item.get("readonly", True)),
            "source": "custom",
        }
        for item in _read_store()
    ]
    if include_disabled:
        return templates
    return [item for item in templates if item.get("enabled")]


def list_templates(include_disabled: bool = True) -> list[dict[str, Any]]:
    with _LOCK:
        builtins = _normalize_builtin_templates(include_disabled=include_disabled)
        custom = _normalize_custom_templates(include_disabled=include_disabled)
    return [*builtins, *custom]


def save_template(template: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_template(template)
    if normalized["id"] in _builtin_template_ids():
        raise ValueError("内置巡检模板为只读，不能覆盖")
    normalized["builtin"] = False
    normalized["readonly"] = bool(template.get("readonly", True))
    normalized["source"] = "custom"
    with _LOCK:
        items = _read_store()
        next_items = [item for item in items if _clean_id(item.get("id")) != normalized["id"]]
        next_items.append(normalized)
        _write_store(sorted(next_items, key=lambda item: item["id"]))
    return normalized


def delete_template(template_id: str) -> bool:
    clean = _clean_id(template_id)
    if clean in _builtin_template_ids():
        return False
    with _LOCK:
        items = _read_store()
        next_items = [item for item in items if _clean_id(item.get("id")) != clean]
        if len(next_items) == len(items):
            return False
        _write_store(next_items)
    return True


def find_matching_template(asset_type: str, protocol: str) -> dict[str, Any] | None:
    asset_type = str(asset_type or "").lower()
    protocol = str(protocol or "").lower()
    with _LOCK:
        templates = [
            *_normalize_custom_templates(include_disabled=False),
            *_normalize_builtin_templates(include_disabled=False),
        ]
    for template in templates:
        template_asset_types = set(template.get("asset_types") or [template.get("asset_type")])
        type_match = "*" in template_asset_types or asset_type in template_asset_types
        protocol_match = template["protocol"] in {"*", protocol}
        if type_match and protocol_match:
            return template
    return None
