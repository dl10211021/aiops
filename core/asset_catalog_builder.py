from __future__ import annotations

from core.hertzbeat_asset_catalog import HERTZBEAT_ASSET_CATALOG

BASE_ASSET_CATALOG = [
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
        "label": "VMware vCenter (API)",
        "category": "virtualization",
        "protocol": "vmware",
        "default_port": 443,
        "inspection_profile": "http_api",
    },
    {
        "id": "esxi",
        "label": "VMware ESXi 主机 (SSH)",
        "category": "virtualization",
        "protocol": "ssh",
        "default_port": 22,
        "inspection_profile": "linux",
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
        "protocol": "zstack",
        "default_port": 8080,
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


EXCLUDED_HERTZBEAT_ASSET_IDS = {
    # HertzBeat ships a sample custom application. It is useful for their
    # template examples, but in OpsCore it pollutes the production asset catalog.
    "a_example",
}

NETWORK_CLI_VENDOR_ASSET_IDS = {
    "cisco_switch",
    "h3c_switch",
    "hpe_switch",
    "huawei_switch",
    "tplink_switch",
}


def _merge_asset_catalog(*catalogs: list[dict]) -> list[dict]:
    merged: list[dict] = []
    index: dict[str, dict] = {}
    for catalog in catalogs:
        for item in catalog:
            asset_id = str(item.get("id") or "").strip()
            if not asset_id:
                continue
            if item.get("source") == "hertzbeat" and asset_id in EXCLUDED_HERTZBEAT_ASSET_IDS:
                continue
            if asset_id in index:
                target = index[asset_id]
                for key in ("params", "hertzbeat_category", "hertzbeat_protocols"):
                    if key in item and key not in target:
                        target[key] = item[key]
                if item.get("source") == "hertzbeat":
                    target["hertzbeat_supported"] = True
                continue
            entry = dict(item)
            if entry.get("source") == "hertzbeat":
                entry["hertzbeat_supported"] = True
            merged.append(entry)
            index[asset_id] = entry
    return merged


ASSET_PROTOCOL_OVERRIDES = {
    # HertzBeat describes these through JDBC, but OpsCore can operate them
    # through an existing compatible native SQL driver.
    "mariadb": "mysql",
    "sqlserver": "mssql",
    "opengauss": "postgresql",
    "greenplum": "postgresql",
    "vastbase": "postgresql",
    "doris_fe": "mysql",
    "starrocks_fe": "mysql",
    "greptime": "mysql",
    "db2": "db2",
    "dameng": "dameng",
    "dm": "dameng",
    "hive": "hive",
    "iotdb": "iotdb",
    "xugu": "xugu",
    "memcached": "memcached",
    # These databases expose query/control APIs over HTTP, but the asset
    # protocol should still read as a database protocol in OpsCore.
    "clickhouse": "clickhouse",
    "elasticsearch": "elasticsearch",
    "nebula_graph": "nebula_graph",
    "nebula_graph_cluster": "nebula_graph",
    # Platform APIs keep their domain protocol name for operators while still
    # using the HTTP execution adapter underneath.
    "kubernetes": "k8s",
    "vmware": "vmware",
    "openstack": "openstack",
    "proxmox": "proxmox",
    "zstack": "zstack",
    "s3": "s3",
    "minio": "minio",
    "backup": "backup",
    "ipmi": "ipmi",
    "ldap": "ldap",
    "dns_sd": "dns",
    "jvm": "jmx",
    "kafka_client": "kafka",
    "zookeeper_sd": "tcp",
    # Service probes are not management APIs. Keep the user-facing protocol
    # close to the actual target so asset filters stay understandable.
    "api": "http",
    "website": "http",
    "fullsite": "http",
    "api_code": "http",
    "dns": "dns",
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
    # HertzBeat runs Windows Script through a collector. OpsCore operates
    # Windows command sessions through WinRM/PowerShell.
    "windows_script": "winrm",
}

ASSET_PORT_OVERRIDES = {
    "deepseek": 443,
    "openai": 443,
    "dns": 53,
    "udp_port": 53,
    "ping": 0,
    "ntp": 123,
    "netease_mailbox": 993,
    "qq_mailbox": 993,
    "activemq": 8161,
    "consul_sd": 8500,
    "dns_sd": 53,
    "eureka_sd": 8761,
    "hadoop": 9870,
    "hdfs_datanode": 9864,
    "hdfs_namenode": 9870,
    "doris_fe": 9030,
    "starrocks_fe": 9030,
    "greptime": 4002,
    "hive": 10000,
    "iceberg": 8181,
    "iotdb": 6667,
    "jetty": 8080,
    "nacos_sd": 8848,
    "prestodb": 8080,
    "pulsar": 8080,
    "shenyu": 9095,
    "spark": 8080,
    "spring_gateway": 8080,
    "zookeeper_sd": 2181,
    "nebula_graph": 9669,
    "nebula_graph_cluster": 9669,
    "ipmi": 623,
    "ldap": 389,
    "zstack": 8080,
}


ASSET_CATEGORY_OVERRIDES = {
    # Synology is a NAS/SAN storage appliance. HertzBeat classifies it as a
    # server-style SNMP target, but in OpsCore operators expect it under
    # storage and backup.
    "synology_nas": "storage",
    "dns": "service",
    "hertzbeat": "monitor",
    "hertzbeat_token": "monitor",
    "influxdb_promql": "monitor",
    "kafka_promql": "monitor",
    "tdengine_promql": "monitor",
    "doris_be": "db",
    "doris_fe": "db",
    "greptime": "db",
    "hbase_master": "db",
    "hbase_regionserver": "db",
    "hive": "db",
    "hugegraph": "db",
    "influxdb": "db",
    "iotdb": "db",
    "starrocks_be": "db",
    "starrocks_fe": "db",
}


def _apply_protocol_overrides(catalog: list[dict]) -> list[dict]:
    result = []
    for item in catalog:
        entry = dict(item)
        category_override = ASSET_CATEGORY_OVERRIDES.get(entry.get("id"))
        if category_override:
            entry["category"] = category_override
        if entry.get("id") in NETWORK_CLI_VENDOR_ASSET_IDS:
            entry["category"] = "network"
            entry["protocol"] = "ssh"
            entry["default_port"] = 22
            entry["inspection_profile"] = "network_cli"
        override = ASSET_PROTOCOL_OVERRIDES.get(entry.get("id"))
        if override:
            entry["protocol"] = override
            if override == "winrm":
                entry["inspection_profile"] = "winrm"
            elif override in {"mysql", "oracle", "postgresql", "mssql", "db2", "dameng", "xugu", "hive", "iotdb"}:
                entry["inspection_profile"] = "sql"
            elif override in {
                "clickhouse",
                "elasticsearch",
                "nebula_graph",
                "vmware",
                "openstack",
                "proxmox",
                "zstack",
                "s3",
                "minio",
                "backup",
                "http",
                "tls",
                "websocket",
                "tcp",
                "udp",
                "icmp",
                "ftp",
                "smtp",
                "pop3",
                "imap",
                "mqtt",
                "ntp",
                "modbus",
                "s7",
                "registry",
            }:
                entry["inspection_profile"] = "http_api"
            elif override == "k8s":
                entry["inspection_profile"] = "k8s"
            else:
                entry["inspection_profile"] = override
            if override == "winrm" and entry.get("default_port") == 22:
                entry["default_port"] = 5985
        port_override = ASSET_PORT_OVERRIDES.get(entry.get("id"))
        if port_override is not None:
            entry["default_port"] = port_override
        result.append(entry)
    return result


ASSET_CATALOG = _apply_protocol_overrides(_merge_asset_catalog(BASE_ASSET_CATALOG, HERTZBEAT_ASSET_CATALOG))
