"""Asset subtype, legacy asset rows, and login protocol normalization."""

from __future__ import annotations

from urllib.parse import urlparse


ASSET_CATALOG = [
    {
        "id": "linux",
        "label": "Linux / Unix",
        "category": "os",
        "protocol": "ssh",
        "default_port": 22,
        "inspection_profile": "linux",
    },
    {
        "id": "windows",
        "label": "Windows Server",
        "category": "os",
        "protocol": "winrm",
        "default_port": 5985,
        "inspection_profile": "winrm",
    },
    {
        "id": "aix",
        "label": "IBM AIX",
        "category": "os",
        "protocol": "ssh",
        "default_port": 22,
        "inspection_profile": "linux",
    },
    {
        "id": "mysql",
        "label": "MySQL",
        "category": "db",
        "protocol": "mysql",
        "default_port": 3306,
        "inspection_profile": "sql",
    },
    {
        "id": "oracle",
        "label": "Oracle",
        "category": "db",
        "protocol": "oracle",
        "default_port": 1521,
        "inspection_profile": "sql",
    },
    {
        "id": "postgresql",
        "label": "PostgreSQL",
        "category": "db",
        "protocol": "postgresql",
        "default_port": 5432,
        "inspection_profile": "sql",
    },
    {
        "id": "mssql",
        "label": "SQL Server",
        "category": "db",
        "protocol": "mssql",
        "default_port": 1433,
        "inspection_profile": "sql",
    },
    {
        "id": "redis",
        "label": "Redis",
        "category": "db",
        "protocol": "redis",
        "default_port": 6379,
        "inspection_profile": "redis",
    },
    {
        "id": "mongodb",
        "label": "MongoDB",
        "category": "db",
        "protocol": "mongodb",
        "default_port": 27017,
        "inspection_profile": "mongodb",
    },
    {
        "id": "clickhouse",
        "label": "ClickHouse",
        "category": "db",
        "protocol": "http_api",
        "default_port": 8123,
        "inspection_profile": "http_api",
    },
    {
        "id": "tidb",
        "label": "TiDB",
        "category": "db",
        "protocol": "mysql",
        "default_port": 4000,
        "inspection_profile": "sql",
    },
    {
        "id": "oceanbase",
        "label": "OceanBase",
        "category": "db",
        "protocol": "mysql",
        "default_port": 2881,
        "inspection_profile": "sql",
    },
    {
        "id": "dameng",
        "label": "达梦数据库 DM",
        "category": "db",
        "protocol": "http_api",
        "default_port": 5236,
        "inspection_profile": "http_api",
    },
    {
        "id": "kingbase",
        "label": "人大金仓 Kingbase",
        "category": "db",
        "protocol": "postgresql",
        "default_port": 54321,
        "inspection_profile": "sql",
    },
    {
        "id": "elasticsearch",
        "label": "ElasticSearch",
        "category": "db",
        "protocol": "http_api",
        "default_port": 9200,
        "inspection_profile": "http_api",
    },
    {
        "id": "docker",
        "label": "Docker Host",
        "category": "container",
        "protocol": "ssh",
        "default_port": 22,
        "inspection_profile": "linux",
    },
    {
        "id": "containerd",
        "label": "containerd Host",
        "category": "container",
        "protocol": "ssh",
        "default_port": 22,
        "inspection_profile": "linux",
    },
    {
        "id": "podman",
        "label": "Podman Host",
        "category": "container",
        "protocol": "ssh",
        "default_port": 22,
        "inspection_profile": "linux",
    },
    {
        "id": "harbor",
        "label": "Harbor Registry",
        "category": "container",
        "protocol": "http_api",
        "default_port": 443,
        "inspection_profile": "http_api",
    },
    {
        "id": "k8s",
        "label": "Kubernetes",
        "category": "container",
        "protocol": "k8s",
        "default_port": 6443,
        "inspection_profile": "k8s",
    },
    {
        "id": "nginx",
        "label": "Nginx",
        "category": "middleware",
        "protocol": "ssh",
        "default_port": 22,
        "inspection_profile": "linux",
    },
    {
        "id": "tomcat",
        "label": "Tomcat",
        "category": "middleware",
        "protocol": "ssh",
        "default_port": 22,
        "inspection_profile": "linux",
    },
    {
        "id": "kafka",
        "label": "Kafka",
        "category": "middleware",
        "protocol": "ssh",
        "default_port": 22,
        "inspection_profile": "linux",
    },
    {
        "id": "rabbitmq",
        "label": "RabbitMQ",
        "category": "middleware",
        "protocol": "http_api",
        "default_port": 15672,
        "inspection_profile": "http_api",
    },
    {
        "id": "rocketmq",
        "label": "RocketMQ",
        "category": "middleware",
        "protocol": "ssh",
        "default_port": 22,
        "inspection_profile": "linux",
    },
    {
        "id": "zookeeper",
        "label": "ZooKeeper",
        "category": "middleware",
        "protocol": "ssh",
        "default_port": 22,
        "inspection_profile": "linux",
    },
    {
        "id": "nacos",
        "label": "Nacos",
        "category": "middleware",
        "protocol": "http_api",
        "default_port": 8848,
        "inspection_profile": "http_api",
    },
    {
        "id": "consul",
        "label": "Consul",
        "category": "middleware",
        "protocol": "http_api",
        "default_port": 8500,
        "inspection_profile": "http_api",
    },
    {
        "id": "minio",
        "label": "MinIO",
        "category": "storage",
        "protocol": "http_api",
        "default_port": 9000,
        "inspection_profile": "http_api",
    },
    {
        "id": "prometheus",
        "label": "Prometheus",
        "category": "monitor",
        "protocol": "http_api",
        "default_port": 9090,
        "inspection_profile": "http_api",
    },
    {
        "id": "alertmanager",
        "label": "Alertmanager",
        "category": "monitor",
        "protocol": "http_api",
        "default_port": 9093,
        "inspection_profile": "http_api",
    },
    {
        "id": "grafana",
        "label": "Grafana",
        "category": "monitor",
        "protocol": "http_api",
        "default_port": 3000,
        "inspection_profile": "http_api",
    },
    {
        "id": "loki",
        "label": "Loki",
        "category": "monitor",
        "protocol": "http_api",
        "default_port": 3100,
        "inspection_profile": "http_api",
    },
    {
        "id": "victoriametrics",
        "label": "VictoriaMetrics",
        "category": "monitor",
        "protocol": "http_api",
        "default_port": 8428,
        "inspection_profile": "http_api",
    },
    {
        "id": "zabbix",
        "label": "Zabbix",
        "category": "monitor",
        "protocol": "http_api",
        "default_port": 80,
        "inspection_profile": "http_api",
    },
    {
        "id": "manageengine",
        "label": "ManageEngine / 卓豪监控",
        "category": "monitor",
        "protocol": "http_api",
        "default_port": 8443,
        "inspection_profile": "http_api",
    },
    {
        "id": "vmware",
        "label": "VMware vCenter / ESXi",
        "category": "virtualization",
        "protocol": "http_api",
        "default_port": 443,
        "inspection_profile": "http_api",
    },
    {
        "id": "kvm",
        "label": "KVM / Libvirt Host",
        "category": "virtualization",
        "protocol": "ssh",
        "default_port": 22,
        "inspection_profile": "linux",
    },
    {
        "id": "openstack",
        "label": "OpenStack",
        "category": "virtualization",
        "protocol": "http_api",
        "default_port": 5000,
        "inspection_profile": "http_api",
    },
    {
        "id": "proxmox",
        "label": "Proxmox VE",
        "category": "virtualization",
        "protocol": "http_api",
        "default_port": 8006,
        "inspection_profile": "http_api",
    },
    {
        "id": "hyperv",
        "label": "Microsoft Hyper-V",
        "category": "virtualization",
        "protocol": "winrm",
        "default_port": 5985,
        "inspection_profile": "winrm",
    },
    {
        "id": "zstack",
        "label": "ZStack",
        "category": "virtualization",
        "protocol": "http_api",
        "default_port": 5000,
        "inspection_profile": "http_api",
    },
    {
        "id": "switch",
        "label": "Switch / Router",
        "category": "network",
        "protocol": "ssh",
        "default_port": 22,
        "inspection_profile": "network_cli",
    },
    {
        "id": "firewall",
        "label": "Firewall",
        "category": "network",
        "protocol": "ssh",
        "default_port": 22,
        "inspection_profile": "network_cli",
    },
    {
        "id": "f5",
        "label": "F5 BIG-IP",
        "category": "network",
        "protocol": "http_api",
        "default_port": 443,
        "inspection_profile": "http_api",
    },
    {
        "id": "a10",
        "label": "A10 Load Balancer",
        "category": "network",
        "protocol": "http_api",
        "default_port": 443,
        "inspection_profile": "http_api",
    },
    {
        "id": "waf",
        "label": "WAF",
        "category": "network",
        "protocol": "http_api",
        "default_port": 443,
        "inspection_profile": "http_api",
    },
    {
        "id": "dns",
        "label": "DNS Server",
        "category": "network",
        "protocol": "ssh",
        "default_port": 22,
        "inspection_profile": "linux",
    },
    {
        "id": "vpn",
        "label": "VPN Gateway",
        "category": "network",
        "protocol": "ssh",
        "default_port": 22,
        "inspection_profile": "network_cli",
    },
    {
        "id": "ceph",
        "label": "Ceph Cluster",
        "category": "storage",
        "protocol": "ssh",
        "default_port": 22,
        "inspection_profile": "linux",
    },
    {
        "id": "nfs",
        "label": "NFS Server",
        "category": "storage",
        "protocol": "ssh",
        "default_port": 22,
        "inspection_profile": "linux",
    },
    {
        "id": "nas",
        "label": "NAS / SAN",
        "category": "storage",
        "protocol": "snmp",
        "default_port": 161,
        "inspection_profile": "snmp",
    },
    {
        "id": "s3",
        "label": "S3 / Object Storage",
        "category": "storage",
        "protocol": "http_api",
        "default_port": 443,
        "inspection_profile": "http_api",
    },
    {
        "id": "hdfs",
        "label": "HDFS",
        "category": "storage",
        "protocol": "ssh",
        "default_port": 22,
        "inspection_profile": "linux",
    },
    {
        "id": "glusterfs",
        "label": "GlusterFS",
        "category": "storage",
        "protocol": "ssh",
        "default_port": 22,
        "inspection_profile": "linux",
    },
    {
        "id": "backup",
        "label": "Backup System",
        "category": "storage",
        "protocol": "http_api",
        "default_port": 443,
        "inspection_profile": "http_api",
    },
    {
        "id": "snmp",
        "label": "SNMP Device",
        "category": "oob",
        "protocol": "snmp",
        "default_port": 161,
        "inspection_profile": "snmp",
    },
    {
        "id": "redfish",
        "label": "Redfish / iLO / iDRAC",
        "category": "oob",
        "protocol": "redfish",
        "default_port": 443,
        "inspection_profile": "http_api",
    },
    {
        "id": "ipmi",
        "label": "IPMI",
        "category": "oob",
        "protocol": "snmp",
        "default_port": 161,
        "inspection_profile": "snmp",
    },
    {
        "id": "bastion",
        "label": "堡垒机 / Bastion",
        "category": "security",
        "protocol": "http_api",
        "default_port": 443,
        "inspection_profile": "http_api",
    },
    {
        "id": "ldap",
        "label": "LDAP / Active Directory",
        "category": "security",
        "protocol": "http_api",
        "default_port": 389,
        "inspection_profile": "http_api",
    },
    {
        "id": "audit",
        "label": "Audit Platform",
        "category": "security",
        "protocol": "http_api",
        "default_port": 443,
        "inspection_profile": "http_api",
    },
]


ASSET_PROTOCOL_MAP = {
    "ssh": "ssh",
    "linux": "ssh",
    "unix": "ssh",
    "aix": "ssh",
    "kvm": "ssh",
    "docker": "ssh",
    "containerd": "ssh",
    "podman": "ssh",
    "switch": "ssh",
    "router": "ssh",
    "firewall": "ssh",
    "vpn": "ssh",
    "dns": "ssh",
    "network": "ssh",
    "window": "winrm",
    "winrm": "winrm",
    "windows": "winrm",
    "mysql": "mysql",
    "oracle": "oracle",
    "postgresql": "postgresql",
    "pg": "postgresql",
    "mssql": "mssql",
    "redis": "redis",
    "mongodb": "mongodb",
    "clickhouse": "http_api",
    "tidb": "mysql",
    "oceanbase": "mysql",
    "dameng": "http_api",
    "dm": "http_api",
    "kingbase": "postgresql",
    "elasticsearch": "http_api",
    "harbor": "http_api",
    "nginx": "ssh",
    "tomcat": "ssh",
    "kafka": "ssh",
    "rabbitmq": "http_api",
    "rocketmq": "ssh",
    "zookeeper": "ssh",
    "nacos": "http_api",
    "consul": "http_api",
    "minio": "http_api",
    "s3": "http_api",
    "object_storage": "http_api",
    "object-storage": "http_api",
    "oss": "http_api",
    "cos": "http_api",
    "obs": "http_api",
    "hdfs": "ssh",
    "glusterfs": "ssh",
    "api": "http_api",
    "http_api": "http_api",
    "http": "http_api",
    "https": "http_api",
    "vmware": "http_api",
    "vcenter": "http_api",
    "esxi": "http_api",
    "openstack": "http_api",
    "proxmox": "http_api",
    "hyperv": "winrm",
    "k8s": "k8s",
    "kubernetes": "k8s",
    "zstack": "http_api",
    "f5": "http_api",
    "a10": "http_api",
    "waf": "http_api",
    "zabbix": "http_api",
    "prometheus": "http_api",
    "alertmanager": "http_api",
    "grafana": "http_api",
    "loki": "http_api",
    "victoriametrics": "http_api",
    "promethues": "http_api",
    "manageengine": "http_api",
    "卓豪": "http_api",
    "ceph": "ssh",
    "nfs": "ssh",
    "nas": "snmp",
    "san": "snmp",
    "backup": "http_api",
    "redfish": "redfish",
    "ipmi": "snmp",
    "snmp": "snmp",
    "bastion": "http_api",
    "ldap": "http_api",
    "ad": "http_api",
    "audit": "http_api",
    "virtual": "virtual",
}

ASSET_TYPE_ALIASES = {
    "ssh": "linux",
    "unix": "linux",
    "window": "windows",
    "winrm": "windows",
    "pg": "postgresql",
    "postgres": "postgresql",
    "promethues": "prometheus",
    "router": "switch",
    "network": "switch",
    "fw": "firewall",
    "vcenter": "vmware",
    "esxi": "vmware",
    "kubernetes": "k8s",
    "dm": "dameng",
    "sqlserver": "mssql",
    "sql_server": "mssql",
    "san": "nas",
    "object_storage": "s3",
    "object-storage": "s3",
    "oss": "s3",
    "cos": "s3",
    "obs": "s3",
    "ad": "ldap",
    "卓豪": "manageengine",
    "manage-engine": "manageengine",
    "manage_engine": "manageengine",
}

GENERIC_ASSET_TYPES = {"", "api", "http", "https", "http_api", "virtual"}
LEGACY_GENERIC_TYPES = GENERIC_ASSET_TYPES | {"linux", "ssh"}

SQL_PROTOCOLS = {"mysql", "oracle", "postgresql", "mssql"}
DATASTORE_PROTOCOLS = {"redis", "mongodb"}
DB_PROTOCOLS = SQL_PROTOCOLS | DATASTORE_PROTOCOLS
SSH_PROTOCOLS = {"ssh"}
API_PROTOCOLS = {"http_api", "k8s", "redfish"}
SNMP_PROTOCOLS = {"snmp"}
NETWORK_CLI_ASSET_TYPES = {"switch", "firewall", "vpn"}
CONTAINER_ASSET_TYPES = {"docker", "containerd", "podman"}
MIDDLEWARE_ASSET_TYPES = {
    "nginx",
    "tomcat",
    "kafka",
    "rabbitmq",
    "rocketmq",
    "zookeeper",
    "nacos",
    "consul",
}
MONITORING_ASSET_TYPES = {
    "prometheus",
    "alertmanager",
    "grafana",
    "loki",
    "victoriametrics",
    "zabbix",
    "manageengine",
}
VIRTUALIZATION_ASSET_TYPES = {"vmware", "kvm", "openstack", "proxmox", "hyperv", "zstack"}
STORAGE_ASSET_TYPES = {"ceph", "nfs", "nas", "minio", "s3", "hdfs", "glusterfs", "backup"}

PORT_ASSET_HINTS = {
    22: "linux",
    80: "zabbix",
    443: "http_api",
    161: "snmp",
    1433: "mssql",
    1521: "oracle",
    3306: "mysql",
    5432: "postgresql",
    5985: "windows",
    5986: "windows",
    6379: "redis",
    8123: "clickhouse",
    2881: "oceanbase",
    4000: "tidb",
    5236: "dameng",
    6443: "k8s",
    8006: "proxmox",
    8443: "manageengine",
    8500: "consul",
    8848: "nacos",
    9000: "minio",
    9090: "prometheus",
    9093: "alertmanager",
    9200: "elasticsearch",
    3000: "grafana",
    3100: "loki",
    8428: "victoriametrics",
    15672: "rabbitmq",
    27017: "mongodb",
}

KEYWORD_ASSET_HINTS = [
    ("prometheus", "prometheus"),
    ("promethues", "prometheus"),
    ("zabbix", "zabbix"),
    ("manageengine", "manageengine"),
    ("manage-engine", "manageengine"),
    ("卓豪", "manageengine"),
    ("alertmanager", "alertmanager"),
    ("grafana", "grafana"),
    ("victoriametrics", "victoriametrics"),
    ("victoria", "victoriametrics"),
    ("loki", "loki"),
    ("mysql", "mysql"),
    ("oracle", "oracle"),
    ("postgresql", "postgresql"),
    ("postgres", "postgresql"),
    ("mssql", "mssql"),
    ("sqlserver", "mssql"),
    ("sql server", "mssql"),
    ("redis", "redis"),
    ("mongodb", "mongodb"),
    ("mongo", "mongodb"),
    ("clickhouse", "clickhouse"),
    ("tidb", "tidb"),
    ("oceanbase", "oceanbase"),
    ("dameng", "dameng"),
    ("达梦", "dameng"),
    ("kingbase", "kingbase"),
    ("人大金仓", "kingbase"),
    ("elasticsearch", "elasticsearch"),
    ("elastic", "elasticsearch"),
    ("docker", "docker"),
    ("containerd", "containerd"),
    ("podman", "podman"),
    ("harbor", "harbor"),
    ("nginx", "nginx"),
    ("tomcat", "tomcat"),
    ("kafka", "kafka"),
    ("rabbitmq", "rabbitmq"),
    ("rocketmq", "rocketmq"),
    ("zookeeper", "zookeeper"),
    ("nacos", "nacos"),
    ("consul", "consul"),
    ("minio", "minio"),
    ("object storage", "s3"),
    ("object-storage", "s3"),
    ("object_storage", "s3"),
    ("s3", "s3"),
    ("oss", "s3"),
    ("cos", "s3"),
    ("obs", "s3"),
    ("对象存储", "s3"),
    ("hdfs", "hdfs"),
    ("glusterfs", "glusterfs"),
    ("gluster", "glusterfs"),
    ("windows", "windows"),
    ("window", "windows"),
    ("winrm", "windows"),
    ("vmware", "vmware"),
    ("vcenter", "vmware"),
    ("esxi", "vmware"),
    ("openstack", "openstack"),
    ("proxmox", "proxmox"),
    ("hyper-v", "hyperv"),
    ("hyperv", "hyperv"),
    ("kubernetes", "k8s"),
    ("k8s", "k8s"),
    ("zstack", "zstack"),
    ("f5", "f5"),
    ("a10", "a10"),
    ("firewall", "firewall"),
    ("防火墙", "firewall"),
    ("waf", "waf"),
    ("dns", "dns"),
    ("vpn", "vpn"),
    ("ceph", "ceph"),
    ("nfs", "nfs"),
    ("nas", "nas"),
    ("san", "nas"),
    ("backup", "backup"),
    ("备份", "backup"),
    ("redfish", "redfish"),
    ("ilo", "redfish"),
    ("idrac", "redfish"),
    ("ipmi", "ipmi"),
    ("bastion", "bastion"),
    ("堡垒机", "bastion"),
    ("ldap", "ldap"),
    ("active directory", "ldap"),
    ("ad", "ldap"),
    ("audit", "audit"),
    ("审计", "audit"),
    ("snmp", "snmp"),
    ("switch", "switch"),
    ("router", "switch"),
    ("交换机", "switch"),
    ("linux", "linux"),
]


def get_asset_catalog() -> list[dict]:
    return [dict(item) for item in ASSET_CATALOG]


def get_asset_definition(asset_type: str | None) -> dict | None:
    subtype = canonical_asset_type(asset_type)
    for item in ASSET_CATALOG:
        if item["id"] == subtype:
            return dict(item)
    return None


def _clean(value: object) -> str:
    return str(value or "").strip().lower()


def _catalog_ids() -> set[str]:
    return {item["id"] for item in ASSET_CATALOG}


def _alias_asset_type(value: str | None) -> str:
    subtype = _clean(value)
    return ASSET_TYPE_ALIASES.get(subtype, subtype)


def _port_from_host(host: str | None) -> int | None:
    raw = str(host or "").strip()
    if not raw:
        return None
    try:
        parsed = urlparse(raw if "://" in raw else f"//{raw}")
        return parsed.port
    except ValueError:
        return None


def _keyword_hint(*values: object) -> str | None:
    text = " ".join(str(v or "") for v in values).lower()
    for keyword, asset_type in KEYWORD_ASSET_HINTS:
        if keyword in text:
            return asset_type
    return None


def _has_legacy_identity_hint(
    extra_args: dict,
    host: str | None,
    port: int | None,
    remark: str | None,
) -> bool:
    if extra_args.get("sub_type") or extra_args.get("device_type") or extra_args.get("db_type"):
        return True
    if _keyword_hint(remark, host):
        return True
    effective_port = _port_from_host(host) or (int(port) if port else None)
    return bool(effective_port and effective_port in PORT_ASSET_HINTS and effective_port != 22)


def _infer_from_legacy_device_type(
    device_type: str,
    protocol: str,
    host: str | None,
    port: int | None,
    remark: str | None,
    extra_args: dict,
) -> str | None:
    device_type = _clean(device_type)
    if not device_type:
        return None

    keyword = _keyword_hint(
        remark,
        host,
        extra_args.get("db_type"),
        extra_args.get("database"),
        extra_args.get("db_name"),
    )
    if keyword and keyword != "linux":
        return keyword

    effective_port = _port_from_host(host) or (int(port) if port else None)
    if device_type in {"database", "db"}:
        return _alias_asset_type(extra_args.get("db_type")) or PORT_ASSET_HINTS.get(effective_port)
    if device_type in {"api", "monitor", "monitoring"}:
        hint = PORT_ASSET_HINTS.get(effective_port)
        if hint and hint not in {"linux", "http_api"}:
            return hint
        return "http_api"
    if device_type in {"network", "switch", "router"}:
        return "switch"
    if device_type in {"windows", "window", "winrm"}:
        return "windows"
    if device_type in {"linux", "ssh"}:
        return "linux"
    if device_type in _catalog_ids():
        return device_type
    mapped_protocol = ASSET_PROTOCOL_MAP.get(device_type)
    if mapped_protocol == "winrm":
        return "windows"
    if mapped_protocol == "ssh":
        return "linux"
    if mapped_protocol == "http_api":
        return keyword or "http_api"
    if mapped_protocol in DB_PROTOCOLS or mapped_protocol in {"k8s", "snmp", "redfish"}:
        return mapped_protocol
    return None


def canonical_asset_type(
    asset_type: str | None = None,
    protocol: str | None = None,
    extra_args: dict | None = None,
    host: str | None = None,
    port: int | None = None,
    remark: str | None = None,
) -> str:
    """Resolve business asset subtype, including legacy linux/virtual rows."""
    extra_args = extra_args or {}
    explicit_subtype = _alias_asset_type(
        extra_args.get("sub_type")
        or extra_args.get("asset_sub_type")
        or extra_args.get("asset_type")
    )
    if explicit_subtype in _catalog_ids():
        return explicit_subtype

    subtype = _alias_asset_type(asset_type)
    proto = _clean(protocol or extra_args.get("login_protocol") or extra_args.get("protocol"))
    is_legacy = proto in {"", "virtual"} and subtype in LEGACY_GENERIC_TYPES

    if is_legacy:
        if proto == "virtual" and not str(host or "").strip():
            return subtype if subtype in _catalog_ids() else "virtual"

        inferred = _infer_from_legacy_device_type(
            extra_args.get("device_type", ""),
            proto,
            host,
            port,
            remark,
            extra_args,
        )
        if inferred:
            return _alias_asset_type(inferred)

        keyword = _keyword_hint(remark, host)
        if keyword:
            return _alias_asset_type(keyword)

        effective_port = _port_from_host(host) or (int(port) if port else None)
        port_hint = PORT_ASSET_HINTS.get(effective_port)
        if port_hint and port_hint != "http_api":
            return _alias_asset_type(port_hint)

    if subtype in _catalog_ids():
        return subtype

    if subtype in {"http_api", "api", "http", "https"}:
        keyword = _keyword_hint(remark, host)
        return _alias_asset_type(keyword) if keyword else "http_api"

    protocol_asset = _alias_asset_type(proto)
    if protocol_asset in _catalog_ids():
        return protocol_asset
    if proto == "winrm":
        return "windows"
    if proto in DB_PROTOCOLS or proto in {"k8s", "snmp", "redfish"}:
        return proto
    if proto == "ssh":
        return "linux"
    if proto == "http_api":
        return "http_api"
    return subtype or protocol_asset or "virtual"


def normalize_protocol(
    asset_type: str | None = None,
    protocol: str | None = None,
    extra_args: dict | None = None,
    host: str | None = None,
    port: int | None = None,
    remark: str | None = None,
) -> str:
    """Resolve login protocol while keeping asset_type as the business subtype."""
    extra_args = extra_args or {}
    explicit = (
        protocol
        or extra_args.get("login_protocol")
        or extra_args.get("protocol")
        or ""
    )
    value = str(explicit).strip().lower()
    subtype = canonical_asset_type(asset_type, protocol, extra_args, host, port, remark)

    # Legacy rows often used "virtual" because non-ssh asset_type was treated as
    # virtual. Re-resolve it from asset_type when we can classify the subtype.
    if value == "virtual" and not str(host or "").strip():
        return "virtual"

    if value in {"api", "http_api"}:
        subtype_protocol = ASSET_PROTOCOL_MAP.get(subtype)
        if subtype_protocol in {"k8s", "snmp", "redfish"}:
            return subtype_protocol
        return "http_api"

    if value == "virtual" and not _has_legacy_identity_hint(extra_args, host, port, remark):
        return "virtual"

    if value and value != "virtual":
        return ASSET_PROTOCOL_MAP.get(value, value)

    definition = get_asset_definition(subtype)
    if definition:
        return definition["protocol"]
    if subtype:
        return ASSET_PROTOCOL_MAP.get(subtype, subtype)
    return value or "virtual"


def normalize_extra_args(asset_type: str, protocol: str, extra_args: dict | None = None) -> dict:
    args = dict(extra_args or {})
    definition = get_asset_definition(asset_type) or {}

    if "enable_password" in args and "enable_pass" not in args:
        args["enable_pass"] = args["enable_password"]

    if protocol == "virtual":
        args["login_protocol"] = "virtual"
        return args

    if definition.get("category"):
        args.setdefault("category", definition["category"])
    if asset_type not in GENERIC_ASSET_TYPES:
        args.setdefault("sub_type", asset_type)
    args["login_protocol"] = protocol

    if protocol in SQL_PROTOCOLS:
        args["db_type"] = protocol
    elif protocol in DATASTORE_PROTOCOLS:
        args.setdefault("db_type", protocol)
    return args


def resolve_asset_identity(
    asset_type: str | None = None,
    protocol: str | None = None,
    extra_args: dict | None = None,
    host: str | None = None,
    port: int | None = None,
    remark: str | None = None,
) -> dict:
    """Return canonical asset subtype, login protocol, and normalized metadata."""
    extra_args = extra_args or {}
    subtype = canonical_asset_type(asset_type, protocol, extra_args, host, port, remark)
    login_protocol = normalize_protocol(subtype, protocol, extra_args, host, port, remark)
    definition = get_asset_definition(subtype) or {}
    return {
        "asset_type": subtype,
        "protocol": login_protocol,
        "category": definition.get("category"),
        "inspection_profile": definition.get("inspection_profile"),
        "extra_args": normalize_extra_args(subtype, login_protocol, extra_args),
    }


def is_ssh_protocol(protocol: str | None) -> bool:
    return normalize_protocol(protocol=protocol) in SSH_PROTOCOLS


def is_db_protocol(protocol: str | None) -> bool:
    return normalize_protocol(protocol=protocol) in DB_PROTOCOLS


def is_api_protocol(protocol: str | None) -> bool:
    return normalize_protocol(protocol=protocol) in API_PROTOCOLS
