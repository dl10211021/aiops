"""Primary access protocol matrix for OpsCore asset types."""

from __future__ import annotations

from typing import Any


PROTOCOL_LABELS = {
    "ssh": "SSH Shell / CLI",
    "telnet": "Telnet CLI",
    "snmp": "SNMP 只读采集",
    "winrm": "Windows WinRM / PowerShell",
    "oracle": "Oracle 原生连接",
    "mysql": "MySQL 协议",
    "postgresql": "PostgreSQL 协议",
    "mssql": "SQL Server 协议",
    "db2": "DB2 协议",
    "dameng": "达梦数据库协议",
    "xugu": "虚谷数据库协议",
    "hive": "Hive JDBC",
    "iotdb": "IoTDB JDBC",
    "jdbc": "JDBC 通用连接",
    "redis": "Redis 原生命令",
    "mongodb": "MongoDB 原生查询",
    "memcached": "Memcached 协议",
    "http": "HTTP/HTTPS 探测",
    "http_api": "HTTP/API 管理接口",
    "https": "HTTPS",
    "jmx": "JMX 指标采集",
    "prometheus": "Prometheus 指标接口",
    "k8s": "Kubernetes API",
    "vmware": "VMware vSphere API",
    "openstack": "OpenStack API",
    "proxmox": "Proxmox API",
    "zstack": "ZStack API",
    "redfish": "Redfish / iLO / iDRAC API",
    "ipmi": "IPMI",
    "ldap": "LDAP / Active Directory",
    "s3": "S3 对象存储 API",
    "minio": "MinIO API",
    "backup": "备份平台 API",
    "clickhouse": "ClickHouse HTTP/Native",
    "elasticsearch": "ElasticSearch HTTP API",
    "nebula_graph": "NebulaGraph / nGQL",
    "ngql": "NebulaGraph nGQL",
    "nginx": "Nginx Stub Status",
    "rocketmq": "RocketMQ 管理接口",
    "kafka": "Kafka 客户端协议",
    "kclient": "Kafka 客户端协议",
    "script": "采集脚本",
    "tcp": "TCP 端口探测",
    "udp": "UDP 端口探测",
    "icmp": "PING/ICMP",
    "dns": "DNS 查询",
    "tls": "TLS/证书检查",
    "ssl_cert": "TLS/证书检查",
    "websocket": "WebSocket",
    "ftp": "FTP",
    "smtp": "SMTP",
    "pop3": "POP3",
    "imap": "IMAP",
    "mqtt": "MQTT",
    "ntp": "NTP",
    "modbus": "Modbus",
    "s7": "S7",
    "registry": "注册中心协议",
    "consul_sd": "Consul 服务发现",
    "dns_sd": "DNS 服务发现",
    "eureka_sd": "Eureka 服务发现",
    "http_sd": "HTTP 服务发现",
    "nacos_sd": "Nacos 服务发现",
    "zookeeper_sd": "ZooKeeper 服务发现",
    "virtual": "虚拟会话能力",
}

PROTOCOL_PORTS = {
    "ssh": 22,
    "telnet": 23,
    "snmp": 161,
    "winrm": 5985,
    "oracle": 1521,
    "mysql": 3306,
    "postgresql": 5432,
    "mssql": 1433,
    "db2": 50000,
    "dameng": 5236,
    "xugu": 5138,
    "hive": 10000,
    "iotdb": 6667,
    "redis": 6379,
    "mongodb": 27017,
    "memcached": 11211,
    "http": 80,
    "http_api": 443,
    "https": 443,
    "jmx": 1099,
    "prometheus": 9090,
    "k8s": 6443,
    "redfish": 443,
    "ipmi": 623,
    "ldap": 389,
    "s3": 443,
    "minio": 9000,
    "tcp": 80,
    "udp": 53,
    "dns": 53,
    "tls": 443,
    "ftp": 21,
    "smtp": 25,
    "pop3": 110,
    "imap": 993,
    "mqtt": 1883,
    "ntp": 123,
    "modbus": 502,
    "s7": 102,
}

OPERATION_PURPOSE = "operation"
MONITORING_PURPOSE = "monitoring"
PROBE_PURPOSE = "probe"

SQL_NATIVE_PROTOCOLS = {
    "oracle",
    "mysql",
    "postgresql",
    "mssql",
    "db2",
    "dameng",
    "xugu",
    "hive",
    "iotdb",
}
DATASTORE_PROTOCOLS = {"redis", "mongodb", "memcached", "nebula_graph", "ngql"}
NETWORK_CLI_ASSET_TYPES = {
    "switch",
    "router",
    "firewall",
    "vpn",
    "network_device",
    "cisco_switch",
    "h3c_switch",
    "hpe_switch",
    "huawei_switch",
    "tplink_switch",
}
NETWORK_API_ASSET_TYPES = {"f5", "a10", "waf", "firewall"}
OS_ASSET_TYPES = {
    "linux",
    "unix",
    "aix",
    "ubuntu",
    "centos",
    "redhat",
    "debian",
    "fedora_coreos",
    "opensuse",
    "rocky",
    "freebsd",
    "alma_linux",
    "euleros",
    "coreos",
}
PROBE_PROTOCOLS = {
    "http",
    "https",
    "tcp",
    "udp",
    "icmp",
    "dns",
    "tls",
    "ftp",
    "smtp",
    "pop3",
    "imap",
    "mqtt",
    "ntp",
    "modbus",
    "s7",
    "registry",
    "websocket",
}


def protocol_label(protocol: str) -> str:
    return PROTOCOL_LABELS.get(protocol, protocol.upper())


def _normalize_protocol(protocol: object) -> str:
    raw = str(protocol or "").strip()
    lower = raw.lower()
    aliases = {
        "nebulagraph": "nebula_graph",
        "ssl_cert": "tls",
    }
    return aliases.get(raw, aliases.get(lower, lower))


def _role_label(role: str) -> str:
    return {
        "default": "默认",
        "alternate": "可选",
        "current_unsupported": "当前配置",
    }.get(role, role)


def _purpose_label(purpose: str) -> str:
    return {
        OPERATION_PURPOSE: "运维接入",
        MONITORING_PURPOSE: "监控采集",
        PROBE_PURPOSE: "连通探测",
    }.get(purpose, purpose)


def _entry(
    protocol: str,
    *,
    purpose: str,
    role: str,
    source: str,
    default_protocol: str,
    default_port: int | None = None,
    label: str | None = None,
    security: str = "recommended",
    description: str | None = None,
    supported: bool = True,
) -> dict[str, Any]:
    protocol = _normalize_protocol(protocol)
    return {
        "protocol": protocol,
        "label": label or protocol_label(protocol),
        "purpose": purpose,
        "purpose_label": _purpose_label(purpose),
        "role": role,
        "role_label": _role_label(role),
        "source": source,
        "default_port": default_port if default_port is not None else PROTOCOL_PORTS.get(protocol),
        "security": security,
        "description": description or "",
        "is_default": protocol == default_protocol and role == "default",
        "supported": supported,
    }


def _add(entries: list[dict[str, Any]], entry: dict[str, Any]) -> None:
    protocol = entry["protocol"]
    purpose = entry["purpose"]
    for current in entries:
        if current["protocol"] != protocol or current["purpose"] != purpose:
            continue
        if entry["role"] == "default" or current["role"] != "default":
            current.update(entry)
        return
    entries.append(entry)


def build_access_protocols(item: dict[str, Any]) -> list[dict[str, Any]]:
    """Build a small, operation-first access list for a catalog item.

    OpsCore is an AI operations platform, not a monitoring-protocol encyclopedia.
    Keep the catalog focused on the main way the AI logs in, queries, inspects,
    or operates the asset. Protocol-specific assets such as SNMP, Redfish, IPMI,
    HTTP probes, and JDBC databases can still be modeled directly by choosing
    those asset types, but we do not attach every possible monitoring protocol
    to each ordinary asset type.
    """
    asset_id = str(item.get("id") or "").strip().lower()
    category = str(item.get("category") or "other").strip().lower()
    default_protocol = _normalize_protocol(item.get("protocol"))
    default_port = item.get("default_port")
    entries: list[dict[str, Any]] = []

    if default_protocol:
        purpose = PROBE_PURPOSE if default_protocol in PROBE_PROTOCOLS else OPERATION_PURPOSE
        _add(entries, _entry(
            default_protocol,
            purpose=purpose,
            role="default",
            source="OpsCore 资产目录",
            default_protocol=default_protocol,
            default_port=default_port,
            description="平台默认接入方式，决定会话工具、只读巡检和 AI 可执行动作边界。",
        ))

    if asset_id in NETWORK_CLI_ASSET_TYPES or (category == "network" and default_protocol == "ssh"):
        _add(entries, _entry(
            "ssh",
            purpose=OPERATION_PURPOSE,
            role="default" if default_protocol == "ssh" else "alternate",
            source="网络设备运维规则",
            default_protocol=default_protocol,
            label="网络设备 SSH CLI",
            description="网络设备主推荐方式，适合执行 show/display 等只读或经审批操作。",
        ))

    hertzbeat_protocols = {str(protocol).strip().lower() for protocol in item.get("hertzbeat_protocols", [])}
    if "snmp" in hertzbeat_protocols and default_protocol != "snmp":
        _add(entries, _entry(
            "snmp",
            purpose=MONITORING_PURPOSE,
            role="alternate",
            source="HertzBeat 监控目录",
            default_protocol=default_protocol,
            default_port=161,
            security="read_only",
            description="保留 SNMP 作为只读指标/OID 采集，不作为 AI 运维主接入协议。",
        ))

    if asset_id in NETWORK_API_ASSET_TYPES or (category == "network" and default_protocol == "http_api"):
        _add(entries, _entry(
            "http_api",
            purpose=OPERATION_PURPOSE,
            role="default" if default_protocol == "http_api" else "alternate",
            source="网络设备运维规则",
            default_protocol=default_protocol,
            label="网络设备 HTTP/API 管理接口",
            description="适合防火墙、负载均衡、WAF 等平台化网络设备管理接口。",
        ))
        _add(entries, _entry(
            "ssh",
            purpose=OPERATION_PURPOSE,
            role="alternate",
            source="网络设备运维规则",
            default_protocol=default_protocol,
            label="网络设备 SSH CLI",
            description="保留 CLI 只读排查能力。",
        ))

    if category == "os" or asset_id in OS_ASSET_TYPES:
        if default_protocol != "winrm":
            _add(entries, _entry(
                "ssh",
                purpose=OPERATION_PURPOSE,
                role="default" if default_protocol == "ssh" else "alternate",
                source="主机运维规则",
                default_protocol=default_protocol,
                description="Linux/Unix 主机默认运维接入方式。",
            ))
        if default_protocol == "winrm" or asset_id == "windows":
            _add(entries, _entry(
                "winrm",
                purpose=OPERATION_PURPOSE,
                role="default" if default_protocol == "winrm" else "alternate",
                source="主机运维规则",
                default_protocol=default_protocol,
                description="Windows 主机默认 PowerShell 接入方式。",
            ))

    if category == "db":
        if default_protocol in SQL_NATIVE_PROTOCOLS:
            _add(entries, _entry(
                default_protocol,
                purpose=OPERATION_PURPOSE,
                role="default",
                source="数据库运维规则",
                default_protocol=default_protocol,
                default_port=default_port,
                description="平台优先使用的数据库原生只读 SQL 接入。",
            ))
        elif default_protocol in DATASTORE_PROTOCOLS:
            _add(entries, _entry(
                default_protocol,
                purpose=OPERATION_PURPOSE,
                role="default",
                source="数据库运维规则",
                default_protocol=default_protocol,
                default_port=default_port,
                description="非 SQL 数据服务的原生命令或查询接入。",
            ))
        else:
            _add(entries, _entry(
                "http_api",
                purpose=OPERATION_PURPOSE,
                role="default" if default_protocol == "http_api" else "alternate",
                source="数据库运维规则",
                default_protocol=default_protocol,
                description="部分数据库管理面或云数据库通过 HTTP/API 执行只读查询和指标读取。",
            ))

    if category in {"middleware", "bigdata"}:
        if default_protocol in {"ssh", "http_api", "kafka", "jmx"}:
            _add(entries, _entry(
                default_protocol,
                purpose=OPERATION_PURPOSE,
                role="default",
                source="中间件运维规则",
                default_protocol=default_protocol,
                default_port=default_port,
                label="中间件主机 SSH Shell" if default_protocol == "ssh" else None,
                description="中间件默认运维入口，用于只读巡检、状态查询和经审批动作。",
            ))

    if category == "container":
        if default_protocol in {"ssh", "k8s", "http_api"}:
            _add(entries, _entry(
                default_protocol,
                purpose=OPERATION_PURPOSE,
                role="default",
                source="容器平台运维规则",
                default_protocol=default_protocol,
                default_port=default_port,
                description="容器主机或平台默认运维接入方式。",
            ))
    if category in {"storage", "oob"}:
        if default_protocol:
            _add(entries, _entry(
                default_protocol,
                purpose=OPERATION_PURPOSE,
                role="default",
                source="存储/带外接入规则",
                default_protocol=default_protocol,
                default_port=default_port,
                label="存储设备 SSH CLI" if category == "storage" and default_protocol == "ssh" else None,
                description="平台默认接入方式。",
            ))

    if category in {"monitor", "virtualization", "security", "ai", "cicd"} and default_protocol:
        _add(entries, _entry(
            default_protocol,
            purpose=OPERATION_PURPOSE,
            role="default",
            source="平台类资产运维规则",
            default_protocol=default_protocol,
            default_port=default_port,
            description="平台类资产默认通过产品 API 或专用协议执行查询和运维动作。",
        ))

    if category == "service" and default_protocol:
        _add(entries, _entry(
            default_protocol,
            purpose=PROBE_PURPOSE,
            role="default",
            source="服务探测规则",
            default_protocol=default_protocol,
            default_port=default_port,
            security="read_only",
            description="业务服务和发现类资产以只读探测为主。",
        ))

    return entries


def mark_current_protocol(
    access_protocols: list[dict[str, Any]],
    current_protocol: str,
    *,
    include_current: bool = True,
) -> list[dict[str, Any]]:
    current_protocol = _normalize_protocol(current_protocol)
    result = []
    found = False
    for entry in access_protocols:
        item = dict(entry)
        item["is_current"] = item.get("protocol") == current_protocol
        if item["is_current"]:
            found = True
        result.append(item)
    if include_current and current_protocol and not found:
        result.append(_entry(
            current_protocol,
            purpose=OPERATION_PURPOSE,
            role="current_unsupported",
            source="当前资产配置",
            default_protocol="",
            security="needs_review",
            description="当前资产保存的协议不在资产类型推荐矩阵内，请复核资产类型或接入协议。",
            supported=False,
        ) | {"is_current": True, "is_default": False})
    return result
