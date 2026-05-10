"""Asset protocol maps, aliases, and inference hints."""

from __future__ import annotations

from core.asset_catalog_builder import ASSET_CATALOG

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
    "dns": "dns",
    "network": "ssh",
    "window": "winrm",
    "winrm": "winrm",
    "windows": "winrm",
    "windows_script": "winrm",
    "mysql": "mysql",
    "oracle": "oracle",
    "postgresql": "postgresql",
    "pg": "postgresql",
    "mssql": "mssql",
    "redis": "redis",
    "memcached": "memcached",
    "mongodb": "mongodb",
    "clickhouse": "clickhouse",
    "tidb": "mysql",
    "oceanbase": "mysql",
    "dameng": "dameng",
    "dm": "dameng",
    "kingbase": "postgresql",
    "elasticsearch": "elasticsearch",
    "nebula_graph": "nebula_graph",
    "nebula_graph_cluster": "nebula_graph",
    "doris_fe": "mysql",
    "starrocks_fe": "mysql",
    "greptime": "mysql",
    "mariadb": "mysql",
    "sqlserver": "mssql",
    "opengauss": "postgresql",
    "greenplum": "postgresql",
    "vastbase": "postgresql",
    "db2": "db2",
    "hive": "hive",
    "iotdb": "iotdb",
    "xugu": "xugu",
    "harbor": "http_api",
    "nginx": "ssh",
    "tomcat": "ssh",
    "kafka": "ssh",
    "rabbitmq": "http_api",
    "rocketmq": "ssh",
    "zookeeper": "ssh",
    "nacos": "http_api",
    "consul": "http_api",
    "minio": "minio",
    "s3": "s3",
    "object_storage": "s3",
    "object-storage": "s3",
    "oss": "s3",
    "cos": "s3",
    "obs": "s3",
    "hdfs": "ssh",
    "glusterfs": "ssh",
    "api": "http",
    "api_code": "http",
    "website": "http",
    "fullsite": "http",
    "ssl_cert": "tls",
    "websocket": "websocket",
    "port": "tcp",
    "udp_port": "udp",
    "ping": "icmp",
    "ftp": "ftp",
    "smtp": "smtp",
    "pop3": "pop3",
    "netease_mailbox": "imap",
    "qq_mailbox": "imap",
    "mqtt": "mqtt",
    "ntp": "ntp",
    "modbus": "modbus",
    "s7": "s7",
    "registry": "registry",
    "http_api": "http_api",
    "http": "http",
    "https": "http",
    "vmware": "vmware",
    "vcenter": "vmware",
    "esxi": "ssh",
    "openstack": "openstack",
    "proxmox": "proxmox",
    "hyperv": "winrm",
    "k8s": "k8s",
    "kubernetes": "k8s",
    "zstack": "zstack",
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
    "nas": "ssh",
    "san": "ssh",
    "backup": "backup",
    "ipmi": "ipmi",
    "redfish": "redfish",
    "snmp": "snmp",
    "bastion": "http_api",
    "ldap": "ldap",
    "jmx": "jmx",
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

SQL_PROTOCOLS = {"mysql", "oracle", "postgresql", "mssql", "db2", "dameng", "xugu", "hive", "iotdb"}
DATASTORE_PROTOCOLS = {"redis", "mongodb", "memcached"}
DATABASE_HTTP_PROTOCOLS = {"clickhouse", "elasticsearch", "nebula_graph"}
DATABASE_HTTP_ASSET_TYPES = {
    item["id"]
    for item in ASSET_CATALOG
    if item.get("category") == "db" and item.get("protocol") in (DATABASE_HTTP_PROTOCOLS | {"http_api"})
}
VIRTUALIZATION_API_PROTOCOLS = {"vmware", "openstack", "proxmox", "zstack"}
STORAGE_API_PROTOCOLS = {"s3", "minio", "backup"}
SERVICE_PROBE_PROTOCOLS = {
    "http",
    "tls",
    "websocket",
    "tcp",
    "udp",
    "icmp",
    "dns",
    "ftp",
    "smtp",
    "pop3",
    "imap",
    "mqtt",
    "ntp",
    "modbus",
    "s7",
    "registry",
    "ipmi",
    "ldap",
    "jmx",
    "kafka",
}
DB_PROTOCOLS = SQL_PROTOCOLS | DATASTORE_PROTOCOLS | DATABASE_HTTP_PROTOCOLS
SSH_PROTOCOLS = {"ssh"}
API_PROTOCOLS = (
    {"http_api", "k8s", "redfish"}
    | DATABASE_HTTP_PROTOCOLS
    | VIRTUALIZATION_API_PROTOCOLS
    | STORAGE_API_PROTOCOLS
    | SERVICE_PROBE_PROTOCOLS
)
SNMP_PROTOCOLS = {"snmp"}
NETWORK_CLI_ASSET_TYPES = {
    "switch",
    "firewall",
    "vpn",
    "cisco_switch",
    "h3c_switch",
    "hpe_switch",
    "huawei_switch",
    "tplink_switch",
}
NETWORK_DUAL_PROTOCOL_ASSET_TYPES = {
    "firewall",
}
CONTAINER_ASSET_TYPES = {"docker", "containerd", "podman"}
MIDDLEWARE_ASSET_TYPES = {
    "nginx",
    "tomcat",
    "kafka",
    "process",
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
    "hertzbeat",
    "hertzbeat_token",
    "influxdb_promql",
    "kafka_promql",
    "tdengine_promql",
}
VIRTUALIZATION_ASSET_TYPES = {"vmware", "kvm", "openstack", "proxmox", "hyperv", "zstack"}
STORAGE_ASSET_TYPES = {"ceph", "nfs", "nas", "synology_nas", "minio", "s3", "hdfs", "glusterfs", "backup"}
STORAGE_SSH_ASSET_TYPES = {
    item
    for item in STORAGE_ASSET_TYPES
    if item in {"ceph", "nfs", "nas", "synology_nas", "hdfs", "glusterfs"}
}
SERVICE_ASSET_TYPES = {item["id"] for item in ASSET_CATALOG if item.get("category") == "service"}


def _category_asset_types(category: str, protocol: str | None = None) -> set[str]:
    return {
        item["id"]
        for item in ASSET_CATALOG
        if item.get("category") == category and (protocol is None or item.get("protocol") == protocol)
    }


BIGDATA_API_ASSET_TYPES = _category_asset_types("bigdata", "http_api")
CONTAINER_API_ASSET_TYPES = _category_asset_types("container", "http_api")
MIDDLEWARE_API_ASSET_TYPES = _category_asset_types("middleware", "http_api")
NETWORK_API_ASSET_TYPES = _category_asset_types("network", "http_api") | NETWORK_DUAL_PROTOCOL_ASSET_TYPES
NETWORK_SSH_ASSET_TYPES = NETWORK_CLI_ASSET_TYPES | NETWORK_API_ASSET_TYPES
SECURITY_API_ASSET_TYPES = _category_asset_types("security", "http_api")
OOB_API_ASSET_TYPES = _category_asset_types("oob", "http_api")
DISCOVERY_API_ASSET_TYPES = _category_asset_types("discovery", "http_api")
AI_PLATFORM_API_ASSET_TYPES = _category_asset_types("ai", "http_api")
CICD_API_ASSET_TYPES = _category_asset_types("cicd", "http_api")
DOMAIN_HTTP_API_ASSET_TYPES = (
    BIGDATA_API_ASSET_TYPES
    | CONTAINER_API_ASSET_TYPES
    | MIDDLEWARE_API_ASSET_TYPES
    | NETWORK_API_ASSET_TYPES
    | SECURITY_API_ASSET_TYPES
    | OOB_API_ASSET_TYPES
    | DISCOVERY_API_ASSET_TYPES
    | AI_PLATFORM_API_ASSET_TYPES
    | CICD_API_ASSET_TYPES
)

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
    11211: "memcached",
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
    ("esxi", "esxi"),
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
