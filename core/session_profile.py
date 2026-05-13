"""Session asset profile generation and formatting."""

from __future__ import annotations

import asyncio
import datetime
import json
import re
from typing import Any

from connections.ssh_manager import ssh_manager
from core.asset_protocols import get_asset_definition, normalize_protocol
from core.assistant_model_config import (
    assistant_task_enabled,
    assistant_thinking_mode,
    resolve_assistant_model_id,
)
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
    definition = get_asset_definition(asset_type)
    category = str((definition or {}).get("category") or "").lower()
    database_protocols = {
        "oracle",
        "mysql",
        "postgresql",
        "mssql",
        "sqlserver",
        "db2",
        "dameng",
        "xugu",
        "hive",
        "iotdb",
        "clickhouse",
        "elasticsearch",
        "nebula_graph",
    }
    datastore_protocols = {"redis", "memcached", "mongodb"}
    os_hosts = {"linux", "ssh", "redhat", "centos", "ubuntu", "debian", "windows"}

    if category == "db" and (protocol in datastore_protocols or asset_type in datastore_protocols):
        return "数据/缓存服务", "datastore"
    if category == "db" or protocol in database_protocols:
        return "数据库服务", "database"
    if protocol in datastore_protocols or asset_type in datastore_protocols:
        return "数据/缓存服务", "datastore"
    if category == "network" or protocol in {"network_cli"}:
        return "网络与安全设备", "network"
    if category == "storage":
        return "存储服务", "storage"
    if category == "middleware":
        return "中间件/应用支撑", "middleware"
    if category == "bigdata":
        return "大数据/分析平台", "bigdata"
    if category == "container":
        return "容器/云原生平台", "container"
    if category == "virtualization":
        return "虚拟化/云平台", "virtualization"
    if category == "monitor":
        return "监控告警平台", "monitor"
    if category == "service":
        return "应用/网络服务", "service"
    if category == "discovery":
        return "服务发现/注册中心", "discovery"
    if category == "oob":
        return "硬件带外管理", "oob"
    if category == "security":
        return "安全/身份平台", "security"
    if category == "ai":
        return "AI/模型平台", "ai"
    if category == "cicd":
        return "CI/CD 发布平台", "cicd"
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


def _inspection_checks(inspection: dict[str, Any] | None) -> list[dict[str, Any]]:
    checks = inspection.get("checks", []) if isinstance(inspection, dict) else []
    return [check for check in checks if isinstance(check, dict)]


def _network_peer_role(line: str, check_name: str) -> tuple[str, int]:
    text = f"{check_name} {line}".lower()
    if any(token in text for token in ("root", "default", "route", "trunk", "core", "uplink", "aggregation", "agg", "router", "firewall")):
        return "上联/核心侧候选", 78
    if any(token in text for token in ("access", "edge", "downlink", "ap", "phone", "camera", "pc", "printer")):
        return "下联/接入侧候选", 70
    if "mac" in text or "arp" in text:
        return "下联或二层学习端候选", 58
    return "网络邻居", 68


def _network_endpoint_from_line(line: str) -> str:
    patterns = (
        r"(?:GigabitEthernet|XGigabitEthernet|Ten-GigabitEthernet|FortyGigE|HundredGigE|Ethernet|Eth|GE|Gi|Te|Fa|Port-channel|Bridge-Aggregation|Vlanif|Vlan)\S+",
        r"\b(?:ge|xe|et)-\d+/\d+/\d+(?:\.\d+)?\b",
    )
    for pattern in patterns:
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            return match.group(0)
    return "接口见证据"


def _network_peer_from_line(line: str) -> str:
    clean = re.sub(r"\s+", " ", line).strip()
    if not clean:
        return ""
    ip_match = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", clean)
    if ip_match:
        return ip_match.group(0)
    mac_match = re.search(r"\b[0-9a-f]{2}(?:[:-][0-9a-f]{2}){5}\b|\b[0-9a-f]{4}[-.][0-9a-f]{4}[-.][0-9a-f]{4}\b", clean, re.IGNORECASE)
    if mac_match:
        return mac_match.group(0)
    parts = [part for part in re.split(r"\s+", clean) if part]
    for part in parts:
        if re.match(
            r"^(?:GigabitEthernet|XGigabitEthernet|Ten-GigabitEthernet|FortyGigE|HundredGigE|Ethernet|Eth|GE|Gi|Te|Fa|Port-channel|Bridge-Aggregation|Vlanif|Vlan)\S+$",
            part,
            re.IGNORECASE,
        ):
            continue
        if any(ch.isalpha() for ch in part) and not re.match(r"^(interface|local|port|vlan|mac|ip|address)$", part, re.I):
            return part[:80]
    return clean[:80]


def _network_relations_from_inspection(
    context: dict[str, Any],
    inspection: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    relations: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    host = str(context.get("host") or "")
    checks = _inspection_checks(inspection)
    signal_names = {
        "neighbors",
        "lldp",
        "cdp",
        "mac_table",
        "arp_table",
        "routes",
        "vlans",
        "stp",
        "interfaces",
        "interface_errors",
    }
    for check in checks:
        name = str(check.get("name") or "").lower()
        title = str(check.get("title") or "").lower()
        command = str(check.get("command") or "").lower()
        signal_text = f"{name} {title} {command}"
        if not any(signal in signal_text for signal in signal_names):
            continue
        output = str(check.get("output") or "")
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        for line in lines[:18]:
            if len(line) < 5 or re.match(r"^-+$", line):
                continue
            role, confidence = _network_peer_role(line, name)
            peer = _network_peer_from_line(line)
            if not peer or peer.lower() in {"interface", "local", "port"}:
                continue
            endpoint = _network_endpoint_from_line(line)
            key = (peer.lower(), endpoint.lower(), role)
            if key in seen:
                continue
            seen.add(key)
            relations.append(
                {
                    "direction": "bidirectional",
                    "peer": peer,
                    "peer_role": role,
                    "endpoint": endpoint,
                    "protocol": "lldp/cdp/mac/arp/stp/route",
                    "evidence": line[:320],
                    "confidence": confidence,
                }
            )
            if len(relations) >= 8:
                return relations
    if host and not relations:
        relations.append(
            {
                "direction": "unknown",
                "peer": "待发现网络邻居",
                "peer_role": "上下联关系待确认",
                "endpoint": host,
                "protocol": "network_cli/snmp",
                "evidence": "当前巡检未获得可解析的 LLDP/CDP/MAC/ARP/STP 证据；建议启用 LLDP/CDP 或补充 SNMP/配置备份后再确认上下联。",
                "confidence": 35,
            }
        )
    return relations


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


def _fallback_relations(context: dict[str, Any], inspection: dict[str, Any] | None) -> list[dict[str, Any]]:
    relations: list[dict[str, Any]] = []
    host = str(context.get("host") or "")
    protocol = str(context.get("protocol") or "")
    asset_type = str(context.get("asset_type") or "")
    port = context.get("port")
    role_label, role_category = _role_for(asset_type, protocol)
    checks = inspection.get("checks", []) if isinstance(inspection, dict) else []
    listen_evidence = ""
    outbound_evidence = ""
    database_session_evidence = ""
    for check in checks:
        if not isinstance(check, dict):
            continue
        title = str(check.get("title") or check.get("name") or "")
        command = str(check.get("command") or "")
        output = str(check.get("output") or "")
        haystack = f"{title}\n{command}\n{output}".lower()
        if not listen_evidence and ("listen" in haystack or "监听" in title or "端口" in title):
            listen_evidence = output.strip().replace("\r", "")[:260]
        if not outbound_evidence and ("estab" in haystack or "established" in haystack or "连接" in title):
            outbound_evidence = output.strip().replace("\r", "")[:260]
        if not database_session_evidence and (
            "session" in haystack
            or "processlist" in haystack
            or "pg_stat_activity" in haystack
            or "v$session" in haystack
            or "dm_exec_sessions" in haystack
            or "会话" in title
        ):
            database_session_evidence = output.strip().replace("\r", "")[:300]
    if host:
        relations.append(
            {
                "direction": "inbound",
                "peer": "OpsCore 当前会话 / 运维入口",
                "peer_role": "运维访问方",
                "endpoint": f"{host}:{port}" if port else host,
                "protocol": protocol,
                "evidence": "来自当前资产连接信息；业务上游需结合监听端口、访问日志和会话证据继续确认。",
                "confidence": 70,
            }
        )
    if role_category == "network":
        relations.extend(_network_relations_from_inspection(context, inspection))
        return relations[:10]
    if database_session_evidence and role_category == "database":
        relations.append(
            {
                "direction": "inbound",
                "peer": "数据库客户端 / 业务连接池",
                "peer_role": "上游应用或 DBA 会话",
                "endpoint": "客户端主机 / 程序名见证据",
                "protocol": protocol,
                "evidence": database_session_evidence,
                "confidence": 68,
            }
        )
    if listen_evidence:
        relations.append(
            {
                "direction": "inbound",
                "peer": "业务调用方 / 用户入口",
                "peer_role": "上游访问方",
                "endpoint": "监听端口",
                "protocol": "tcp/udp",
                "evidence": listen_evidence,
                "confidence": 55,
            }
        )
    if outbound_evidence:
        relations.append(
            {
                "direction": "outbound",
                "peer": "外部依赖 / 下游服务",
                "peer_role": "下游依赖",
                "endpoint": "已建立连接",
                "protocol": "tcp",
                "evidence": outbound_evidence,
                "confidence": 45,
            }
        )
    return relations[:6]


def _relation_strategy_for(context: dict[str, Any]) -> list[dict[str, str]]:
    asset_type = str(context.get("asset_type") or "").lower()
    protocol = str(context.get("protocol") or "").lower()
    role_label, role_category = _role_for(asset_type, protocol)

    def item(direction: str, title: str, method: str, evidence: str, tool_hint: str) -> dict[str, str]:
        return {
            "direction": direction,
            "title": title,
            "method": method,
            "evidence": evidence,
            "tool_hint": tool_hint,
        }

    if role_category == "database":
        if protocol == "oracle" or asset_type == "oracle":
            return [
                item("inbound", "业务到 Oracle 的连接", "查询 v$session/v$process/v$instance，按 MACHINE、PROGRAM、USERNAME、STATUS 汇总客户端来源。", "v$session、v$process、监听状态、会话状态分布", "database_execute_sql"),
                item("outbound", "Oracle 对外依赖", "查询 DB Link、外部表、目录对象和调度作业，确认数据库主动访问的下游。", "DBA_DB_LINKS、DBA_EXTERNAL_TABLES、DBA_SCHEDULER_JOBS", "database_execute_sql"),
            ]
        if protocol in {"mysql", "mariadb", "tidb"} or asset_type in {"mysql", "mariadb", "tidb"}:
            return [
                item("inbound", "业务到 MySQL/TiDB 的连接", "读取 SHOW PROCESSLIST、performance_schema 连接与账号维度，按 Host/User/DB/Command 聚合。", "SHOW PROCESSLIST、performance_schema.threads、information_schema.processlist", "database_execute_sql"),
                item("outbound", "复制与外部依赖", "检查主从/复制、Federated 表、事件调度和外部插件状态。", "SHOW SLAVE/REPLICA STATUS、SHOW EVENTS、information_schema", "database_execute_sql"),
            ]
        if protocol == "postgresql" or asset_type == "postgresql":
            return [
                item("inbound", "业务到 PostgreSQL 的连接", "读取 pg_stat_activity，按 client_addr/application_name/usename/state 聚合客户端来源。", "pg_stat_activity、pg_locks、pg_stat_database", "database_execute_sql"),
                item("outbound", "复制/外部表依赖", "检查 FDW、订阅发布、复制槽和外部服务访问。", "pg_foreign_server、pg_stat_subscription、pg_replication_slots", "database_execute_sql"),
            ]
        if protocol in {"mssql", "sqlserver"} or asset_type in {"mssql", "sqlserver"}:
            return [
                item("inbound", "业务到 SQL Server 的连接", "读取 sys.dm_exec_sessions / sys.dm_exec_connections，按 host_name/program_name/login_name 聚合。", "sys.dm_exec_sessions、sys.dm_exec_connections、sys.dm_exec_requests", "database_execute_sql"),
                item("outbound", "Linked Server/作业依赖", "检查 Linked Server、SQL Agent Job 和外部数据源。", "sys.servers、msdb.dbo.sysjobs、sys.external_data_sources", "database_execute_sql"),
            ]
        if protocol == "dameng" or asset_type == "dameng":
            return [
                item("inbound", "业务到达梦的连接", "读取 V$SESSIONS，按 CLNT_IP/USER_NAME/STATE 汇总客户端来源。", "V$SESSIONS、V$INSTANCE、会话状态", "database_execute_sql"),
                item("outbound", "达梦外部依赖", "检查 DBLink、作业和外部对象配置。", "DBA_DB_LINKS、系统作业视图、外部对象视图", "database_execute_sql"),
            ]
        return [
            item("inbound", f"业务到{role_label}的连接", "读取数据库原生活跃会话视图，按客户端地址、程序名、账号和库名汇总。", "活跃会话、连接数、客户端主机、程序名", "database_execute_sql"),
            item("outbound", "数据库外部依赖", "检查复制、DBLink、外部表、调度作业和插件。", "复制状态、外部连接、调度任务", "database_execute_sql"),
        ]

    if role_category == "linux":
        return [
            item("inbound", "业务/用户到主机的连接", "通过 ss/netstat 读取监听端口和已建立连接，再结合 nginx/apache/ssh/docker 日志确认来源。", "ss -lntup、ss -tnp state established、last、journalctl、容器端口映射", "ssh_execute_command"),
            item("outbound", "主机到下游服务", "通过 ss/lsof/进程环境/容器配置识别主动连接的数据库、API、中间件和远端端口。", "ss -tnp state established、lsof -i、docker inspect、进程命令行", "ssh_execute_command"),
        ]

    if role_category == "windows":
        return [
            item("inbound", "业务/用户到 Windows 的连接", "使用 Get-NetTCPConnection/netstat、事件日志和 IIS/RDP/WinRM 日志识别访问方。", "Get-NetTCPConnection、netstat -ano、Security Event、IIS logs", "winrm_execute_command"),
            item("outbound", "Windows 到下游服务", "结合 TCP 连接、进程 PID、服务配置和计划任务确认主动访问的远端。", "Get-NetTCPConnection、Get-Process、Get-Service、ScheduledTask", "winrm_execute_command"),
        ]

    if role_category == "network":
        return [
            item("bidirectional", "网络邻居与上下联", "优先读取 LLDP/CDP 明细；如果邻居协议未启用，再用 MAC 地址表、ARP、VLAN/Trunk、STP 根端口和默认路由交叉判断上联、下联或未知邻居。", "display/show lldp neighbors、cdp neighbors、mac-address-table、arp、vlan/trunk、stp、route", "network_cli_execute_command / snmp_get"),
            item("bidirectional", "交换机端口角色识别", "按接口状态、描述、VLAN、Trunk、聚合口、错误包和 MAC 学习数量识别核心口、上联口、接入口、服务器口、AP 口和异常端口。", "display/show interface brief、interface counters errors、vlan、trunk、port-channel/Bridge-Aggregation", "network_cli_execute_command"),
            item("outbound", "路由与三层出口", "读取路由表、默认路由、三层接口和网关邻居，把三层出口标成上联候选；方向证据不足时保留 unknown，不强行编业务名。", "display/show ip route、route、ip interface brief、arp", "network_cli_execute_command"),
            item("inbound", "管理入口", "检查 SSH/Telnet/SNMP 管理会话、VTY/ACL 和最近登录用户，区分运维入口与业务转发流量。", "show/display users、ssh server/status、user-interface/vty、ACL/SNMP 配置", "network_cli_execute_command"),
        ]

    if role_category == "storage":
        return [
            item("inbound", "业务到存储的访问", "读取导出、共享、Bucket、卷或客户端连接，确认哪些业务主机正在访问该存储。", "NFS exports、SMB sessions、ceph status、bucket policy、NAS 会话/日志", "storage_execute_command / storage_api_request"),
            item("outbound", "存储到下游依赖", "检查复制、备份、远端池、对象存储网关、DNS/NTP/认证等外部依赖。", "复制任务、远端集群、备份任务、认证/时间同步配置", "storage_execute_command / storage_api_request"),
        ]

    if role_category == "middleware":
        return [
            item("inbound", "业务到中间件的连接", "读取监听端口、客户端连接、Topic/Queue/Consumer、访问日志和服务注册信息。", "ss/netstat、broker/client stats、consumer group、访问日志", "middleware_execute_command / middleware_api_request"),
            item("outbound", "中间件到下游依赖", "检查配置文件、注册中心、数据库连接、集群节点和外部 API 依赖。", "配置文件、集群成员、注册中心、连接池、错误日志", "middleware_execute_command / middleware_api_request"),
        ]

    if role_category == "bigdata":
        return [
            item("inbound", "作业/用户到大数据平台", "读取队列、作业、提交端、租户和用户维度，确认谁在使用该集群或组件。", "YARN/Spark/Flink/调度平台 API、作业历史、队列指标", "bigdata_api_request / db_execute_query"),
            item("outbound", "大数据平台到存储/元数据依赖", "检查 HDFS、Hive Metastore、对象存储、数据库、调度器和外部 Catalog 依赖。", "metastore、catalog、warehouse、HDFS/ObjectStore、调度任务", "bigdata_api_request / db_execute_query"),
        ]

    if role_category == "container":
        return [
            item("inbound", "用户/流水线到容器平台", "读取集群事件、API 审计、镜像仓库访问和工作负载变更记录。", "K8s events/audit、Harbor project、runtime logs、部署记录", "k8s_api_request / container_execute_command"),
            item("outbound", "容器平台到外部依赖", "识别镜像仓库、存储类、服务发现、Ingress/Service、外部数据库和 API。", "Service/Ingress、PVC/StorageClass、image registry、Pod env/config", "k8s_api_request / container_execute_command"),
        ]

    if role_category == "virtualization":
        return [
            item("inbound", "平台管理与租户访问", "通过平台 API 读取管理连接、集群、宿主机、虚拟机和租户入口。", "vCenter/ESXi/云平台 API 会话、任务、事件", "virtualization_api_request"),
            item("outbound", "虚拟化平台下游", "读取宿主机、存储、网络、备份和镜像仓库依赖。", "host/datastore/network/task/event API", "virtualization_api_request"),
        ]

    if role_category in {"api", "service", "discovery"}:
        return [
            item("inbound", "业务到 API 的调用", "通过访问日志、网关日志、请求头和证书信息确认调用方。", "HTTP access log、gateway log、TLS cert、request headers", "service_probe_request / http_api_request"),
            item("outbound", "API 到下游服务", "结合配置、健康检查、调用日志和依赖接口列表识别下游。", "配置只读读取、健康检查、应用日志、OpenAPI/Swagger", "http_api_request"),
        ]

    if role_category in {"monitor", "security", "oob", "ai", "cicd"}:
        return [
            item("inbound", "平台使用方与采集入口", "读取登录/审计/任务/采集目标，确认哪些系统、用户或 Agent 正在调用该平台。", "审计日志、API token 使用、采集目标、任务/告警事件", "当前资产协议工具"),
            item("outbound", "平台管理或采集的对象", "读取目标清单、规则、任务、Webhook、通知和外部系统配置，确认平台连接到哪些对象。", "targets、rules、jobs、webhook、integration、endpoint list", "当前资产协议工具"),
        ]

    return [
        item("inbound", "访问方识别", "先用当前协议只读探测监听、会话、日志或 API 事件，再按来源聚合访问方。", "协议原生只读巡检结果", "当前资产协议工具"),
        item("outbound", "外部依赖识别", "先用当前协议只读探测远端连接、配置、任务或 API 依赖，再按目标聚合下游。", "远端连接、配置、任务、日志", "当前资产协议工具"),
    ]


def _normalize_relations(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    normalized = []
    allowed = {"inbound", "outbound", "bidirectional", "unknown"}
    for item in value[:12]:
        if not isinstance(item, dict):
            continue
        direction = str(item.get("direction") or "unknown").strip().lower()
        if direction not in allowed:
            direction = "unknown"
        peer = str(item.get("peer") or item.get("target") or item.get("name") or "").strip()
        if not peer:
            continue
        confidence_raw = item.get("confidence", 50)
        try:
            confidence = int(confidence_raw)
        except Exception:
            confidence = 50
        normalized.append(
            {
                "direction": direction,
                "peer": peer[:120],
                "peer_role": str(item.get("peer_role") or item.get("role") or "")[:120],
                "endpoint": str(item.get("endpoint") or item.get("address") or "")[:160],
                "protocol": str(item.get("protocol") or "")[:80],
                "evidence": str(item.get("evidence") or item.get("reason") or "")[:320],
                "confidence": max(0, min(100, confidence)),
            }
        )
    return normalized


def _normalize_relation_strategies(value: Any, context: dict[str, Any]) -> list[dict[str, str]]:
    source = value if isinstance(value, list) and value else _relation_strategy_for(context)
    if _looks_like_stale_relation_strategy(source, context):
        source = _relation_strategy_for(context)
    normalized: list[dict[str, str]] = []
    allowed = {"inbound", "outbound", "bidirectional", "unknown"}
    for item in source[:6]:
        if not isinstance(item, dict):
            continue
        direction = str(item.get("direction") or "unknown").strip().lower()
        if direction not in allowed:
            direction = "unknown"
        title = str(item.get("title") or item.get("name") or "").strip()
        method = str(item.get("method") or item.get("description") or "").strip()
        evidence = str(item.get("evidence") or item.get("source") or "").strip()
        tool_hint = str(item.get("tool_hint") or item.get("tool") or "").strip()
        if not title and not method:
            continue
        normalized.append(
            {
                "direction": direction,
                "title": title[:120],
                "method": method[:280],
                "evidence": evidence[:180],
                "tool_hint": tool_hint[:120],
            }
        )
    return normalized


def _looks_like_stale_relation_strategy(source: Any, context: dict[str, Any]) -> bool:
    if not isinstance(source, list) or not source:
        return False
    _, role_category = _role_for(
        str(context.get("asset_type") or ""),
        str(context.get("protocol") or ""),
    )
    if role_category in {"linux", "windows", "api", "general"}:
        return False
    joined = "\n".join(
        " ".join(str(item.get(field) or "") for field in ("title", "method", "evidence", "tool_hint"))
        for item in source
        if isinstance(item, dict)
    ).lower()
    stale_markers = {
        "ssh_execute_command",
        "winrm_execute_command",
        "ss -lntup",
        "get-nettcpconnection",
        "业务/用户到主机",
        "windows 到下游",
        "http access log",
    }
    return any(marker in joined for marker in stale_markers)


def _normalized_role_fields(profile: dict[str, Any], context: dict[str, Any]) -> tuple[str, str]:
    role_label, role_category = _role_for(
        str(context.get("asset_type") or ""),
        str(context.get("protocol") or ""),
    )
    profile_label = str(profile.get("role_label") or "").strip()
    profile_category = str(profile.get("role_category") or "").strip().lower()
    fallback_categories = {"", "linux", "windows", "api", "general"}
    stale_labels = {"linux/unix 主机", "linux 主机", "windows 主机", "http/api 服务", "运维资产"}
    catalog_specific = role_category not in {"linux", "windows", "api", "general"}
    if catalog_specific and (
        profile_category in fallback_categories
        or profile_label.strip().lower() in stale_labels
    ):
        return role_label, role_category
    return (profile_label or role_label)[:80], (profile_category or role_category)[:60]


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
    checks = _inspection_checks(inspection)
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
        focus_areas.insert(0, {"title": "接口、邻居和上下联", "reason": "优先检查 LLDP/CDP、MAC/ARP、VLAN/Trunk、STP 根桥/阻塞端口、路由和接口错误，所有上下联结论必须带证据与置信度。", "priority": "P0"})
    elif role_category == "storage":
        focus_areas.insert(0, {"title": "容量与数据保护", "reason": "优先检查容量水位、卷/池状态、复制、快照和备份任务。", "priority": "P0"})
    elif role_category == "middleware":
        focus_areas.insert(0, {"title": "进程、端口和业务队列", "reason": "优先检查服务进程、监听端口、队列/Topic、集群状态和近期错误日志。", "priority": "P0"})
    elif role_category == "bigdata":
        focus_areas.insert(0, {"title": "集群组件与作业状态", "reason": "优先检查组件健康、作业失败、队列资源、元数据和存储依赖。", "priority": "P0"})
    elif role_category == "container":
        focus_areas.insert(0, {"title": "工作负载与节点状态", "reason": "优先检查节点、Pod/容器、事件、镜像仓库和存储挂载。", "priority": "P0"})
    elif role_category == "virtualization":
        focus_areas.insert(0, {"title": "集群、宿主机和存储", "reason": "优先检查宿主机状态、资源池、Datastore、虚机告警和快照风险。", "priority": "P0"})
    elif role_category in {"monitor", "security", "oob", "ai", "cicd", "service", "discovery", "api"}:
        focus_areas.insert(0, {"title": "平台连通与外部依赖", "reason": "优先检查 API/协议连通、认证状态、目标清单、规则/任务和外部集成。", "priority": "P0"})

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
            "relations": _fallback_relations(context, inspection),
            "relation_strategies": _relation_strategy_for(context),
            "services": [],
            "tags": context.get("tags") or [],
            "source": source,
            "source_summary": inspection.get("summary") if isinstance(inspection, dict) else "",
            "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        context,
    )


def _normalize_profile(profile: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    role_label, role_category = _normalized_role_fields(profile, context)
    normalized = {
        "version": PROFILE_VERSION,
        "session_id": context.get("session_id"),
        "asset_key": context.get("asset_key"),
        "host": context.get("host"),
        "port": context.get("port"),
        "remark": context.get("remark") or "",
        "asset_type": context.get("asset_type") or profile.get("asset_type") or "",
        "protocol": context.get("protocol") or profile.get("protocol") or "",
        "role_label": role_label,
        "role_category": role_category,
        "purpose": str(profile.get("purpose") or "")[:700],
        "confidence": int(profile.get("confidence") or 50),
        "risk_level": str(profile.get("risk_level") or "watch"),
        "evidence": profile.get("evidence") if isinstance(profile.get("evidence"), list) else [],
        "focus_areas": profile.get("focus_areas") if isinstance(profile.get("focus_areas"), list) else [],
        "relations": _normalize_relations(profile.get("relations")) or _fallback_relations(context, None),
        "relation_strategies": _normalize_relation_strategies(profile.get("relation_strategies"), context),
        "services": profile.get("services") if isinstance(profile.get("services"), list) else [],
        "tags": profile.get("tags") if isinstance(profile.get("tags"), list) else context.get("tags") or [],
        "source": str(profile.get("source") or "ai"),
        "source_summary": str(profile.get("source_summary") or "")[:700],
        "profile_prompt": str(profile.get("profile_prompt") or "")[:1800],
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

    selected_model = resolve_assistant_model_id(model_name)
    prompt = f"""
你是企业 AIOps 平台的资产画像分析器。请根据资产连接信息、只读巡检结果和最近会话内容，判断这是什么资产、可能承担什么业务角色、后续排查应该重点关注什么。

只输出 JSON 对象，不要 Markdown，不要解释。字段：
role_label, role_category, purpose, confidence, risk_level, evidence, focus_areas, relations, relation_strategies, services, tags, source_summary, profile_prompt。

要求：
- role_label 用中文短语，例如“Oracle 数据库服务”“Linux 应用服务器”“Windows 主机”“网络交换设备”。
- role_category 用英文小写分类，例如 database/linux/windows/network/storage/virtualization/api/general。
- confidence 是 0-100 整数。
- risk_level 只能是 normal/watch/high。
- evidence 最多 6 条，每条含 label,value,source。
- focus_areas 最多 6 条，每条含 title,reason,priority，priority 用 P0/P1/P2。
- relations 最多 10 条，用于描述资产互联关系；每条含 direction,peer,peer_role,endpoint,protocol,evidence,confidence。
- relations.direction 只能是 inbound/outbound/bidirectional/unknown；inbound 表示“哪些业务/系统/用户连接它”，outbound 表示“它主动连接哪些下游/数据库/API/中间件”，bidirectional 表示双向依赖，unknown 表示方向证据不足。
- relations 必须基于监听端口、已建立连接、访问日志、进程、容器、数据库连接、网络邻居/MAC/ARP/VLAN/STP/路由、会话上下文或巡检证据推断；不确定时写 unknown，不要编造业务名。
- 额外输出 relation_strategies，用于说明不同资产类型应该如何继续采集互联证据；每条含 direction,title,method,evidence,tool_hint。
- relation_strategies 必须协议感知：Linux/SSH 看 ss、lsof、日志、容器；Windows/WinRM 看 Get-NetTCPConnection、事件/IIS/RDP 日志；数据库看原生活跃会话和外部依赖视图；网络设备看 CLI/SNMP 的 LLDP/CDP、ARP、MAC、VLAN/Trunk、STP、路由、接口错误和端口描述；API/虚拟化看平台 API、访问日志和事件。
- 如果是交换机/路由器/防火墙，不要只写“上下行”；应输出证据化的上联候选、下联/接入侧候选、三层出口、管理入口和未知邻居，并用 confidence 表达确定程度。
- profile_prompt 是写给主会话模型的专业提示词，必须基于本资产画像汇聚生成，说明资产角色、业务用途、排查优先级、风险边界、工具使用注意事项；不要超过 900 字。
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
    thinking_mode = assistant_thinking_mode() if assistant_task_enabled("asset_profile_prompt") else "off"
    async for event in execute_chat_stream(selected_model, messages, thinking_mode, None):
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
    profile = memory_db.get_asset_profile(session_id)
    if not profile:
        return None
    try:
        context = session_asset_context(session_id)
    except Exception:
        context = {
            "session_id": session_id,
            "asset_key": profile.get("asset_key") or "",
            "host": profile.get("host") or "",
            "port": profile.get("port"),
            "remark": profile.get("remark") or "",
            "asset_type": profile.get("asset_type") or "",
            "protocol": profile.get("protocol") or "",
            "tags": profile.get("tags") or [],
        }
    return _normalize_profile(profile, context)


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
    relations = profile.get("relations") or []
    if relations:
        lines.append("")
        lines.append("### 互联关系")
        for item in relations:
            lines.append(
                "- "
                f"{item.get('direction') or 'unknown'} | "
                f"{item.get('peer') or '-'} | "
                f"{item.get('endpoint') or '-'} | "
                f"{item.get('protocol') or '-'} | "
                f"证据：{item.get('evidence') or '-'}"
            )
    strategies = profile.get("relation_strategies") or []
    if strategies:
        lines.append("")
        lines.append("### 互联采集策略")
        for item in strategies:
            lines.append(
                "- "
                f"{item.get('direction') or 'unknown'} | "
                f"{item.get('title') or '-'} | "
                f"{item.get('method') or '-'} | "
                f"证据源：{item.get('evidence') or '-'}"
            )
    lines.append("")
    lines.append("### 后续排查重点")
    for item in profile.get("focus_areas") or []:
        lines.append(f"- [{item.get('priority') or 'P1'}] {item.get('title')}: {item.get('reason')}")
    return "\n".join(lines)


def profile_to_system_prompt(profile: dict[str, Any] | None) -> str:
    if not profile:
        return ""
    profile_prompt = str(profile.get("profile_prompt") or "").strip()
    if not profile_prompt:
        synthesized = []
        role_label = str(profile.get("role_label") or "").strip()
        purpose = str(profile.get("purpose") or "").strip()
        risk_level = str(profile.get("risk_level") or "").strip()
        confidence = profile.get("confidence")
        if role_label:
            synthesized.append(f"资产角色：{role_label}。")
        if purpose:
            synthesized.append(f"业务用途：{purpose}")
        if risk_level or confidence is not None:
            synthesized.append(f"画像状态：风险等级 {risk_level or 'unknown'}，置信度 {confidence if confidence is not None else 'unknown'}。")
        evidence_lines = []
        for item in profile.get("evidence") or []:
            if isinstance(item, dict):
                label = str(item.get("label") or "证据").strip()
                value = str(item.get("value") or "").strip()
                source = str(item.get("source") or "").strip()
                if value:
                    suffix = f"（来源：{source}）" if source else ""
                    evidence_lines.append(f"- {label}: {value}{suffix}")
        if evidence_lines:
            synthesized.append("画像证据：\n" + "\n".join(evidence_lines[:6]))
        relation_lines = []
        for item in profile.get("relations") or []:
            if isinstance(item, dict):
                direction = str(item.get("direction") or "unknown").strip()
                peer = str(item.get("peer") or "").strip()
                endpoint = str(item.get("endpoint") or "").strip()
                protocol = str(item.get("protocol") or "").strip()
                evidence = str(item.get("evidence") or "").strip()
                if peer:
                    relation_lines.append(f"- {direction}: {peer} {endpoint} {protocol}，证据：{evidence or '待验证'}".strip())
        if relation_lines:
            synthesized.append("互联关系：\n" + "\n".join(relation_lines[:8]))
        strategy_lines = []
        for item in profile.get("relation_strategies") or []:
            if isinstance(item, dict):
                direction = str(item.get("direction") or "unknown").strip()
                title = str(item.get("title") or "").strip()
                method = str(item.get("method") or "").strip()
                evidence = str(item.get("evidence") or "").strip()
                if title or method:
                    strategy_lines.append(f"- {direction}: {title}；采集方式：{method}；证据源：{evidence or '待采集'}")
        if strategy_lines:
            synthesized.append("互联采集策略：\n" + "\n".join(strategy_lines[:6]))
        focus_lines = []
        for item in profile.get("focus_areas") or []:
            if isinstance(item, dict):
                title = str(item.get("title") or "").strip()
                reason = str(item.get("reason") or "").strip()
                priority = str(item.get("priority") or "P1").strip()
                if title:
                    focus_lines.append(f"- [{priority}] {title}: {reason or '按需关注'}")
        if focus_lines:
            synthesized.append("排查优先级：\n" + "\n".join(focus_lines[:6]))
        profile_prompt = "\n".join(synthesized).strip()
    if not profile_prompt:
        return ""
    return f"""
[资产画像提示词]
这段提示词由辅助思维模型或主模型在用户主动生成资产画像时汇聚写入。它可直接作为理解当前资产和制定排查路径的重要上下文，不需要每轮人工确认；如果后续工具结果与画像冲突，以当前工具结果为准。

{profile_prompt}
""".strip()
