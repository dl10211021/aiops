from __future__ import annotations

from typing import Any

SQL_DRIVER_KEYS = {
    "oracle": "oracle",
    "mysql": "mysql",
    "postgresql": "postgresql",
    "mssql": "mssql",
    "dameng": "dameng",
    "dm": "dameng",
    "db2": "db2",
    "xugu": "xugu",
    "hive": "hive",
    "iotdb": "iotdb",
}


DATABASE_ALIASES = {
    "tidb": "mysql",
    "oceanbase": "mysql",
    "mariadb": "mysql",
    "kingbase": "postgresql",
    "opengauss": "postgresql",
    "greenplum": "postgresql",
    "vastbase": "postgresql",
    "doris_fe": "mysql",
    "starrocks_fe": "mysql",
    "greptime": "mysql",
    "pg": "postgresql",
    "sqlserver": "mssql",
    "sql_server": "mssql",
    "dm": "dameng",
}


DATABASE_HTTP_IDS = {
    "clickhouse",
    "doris_be",
    "elasticsearch",
    "hbase_master",
    "hbase_regionserver",
    "hugegraph",
    "influxdb",
    "nebula_graph",
    "nebula_graph_cluster",
    "starrocks_be",
}


DATABASE_HTTP_PROTOCOLS = {
    "clickhouse",
    "elasticsearch",
    "nebula_graph",
}


VIRTUALIZATION_API_PROTOCOLS = {
    "vmware",
    "openstack",
    "proxmox",
    "zstack",
}


STORAGE_API_PROTOCOLS = {
    "s3",
    "minio",
    "backup",
}

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

SERVICE_PROTOCOL_CREDENTIAL_FIELDS = {
    "ftp": ["host", "port", "username", "password"],
    "smtp": ["host", "port", "username", "password"],
    "pop3": ["host", "port", "username", "password"],
    "imap": ["host", "port", "username", "password"],
    "mqtt": ["host", "port", "username", "password"],
    "ipmi": ["host", "port", "username", "password"],
    "ldap": ["host", "port", "username", "password", "base_dn"],
    "jmx": ["host", "port", "username", "password"],
    "kafka": ["host", "port", "username", "password"],
}


DATABASE_DRIVER_REQUIRED_IDS = {
    "db2",
    "dameng",
    "dm",
    "hive",
    "iotdb",
    "xugu",
}


NETWORK_CLI_IDS = {
    "switch",
    "router",
    "firewall",
    "vpn",
    "dns",
}


OBJECT_STORAGE_IDS = {
    "s3",
    "minio",
    "oss",
    "cos",
    "obs",
    "object_storage",
    "object-storage",
}


MONITORING_QUERY_IDS = {
    "hertzbeat",
    "hertzbeat_token",
    "influxdb_promql",
    "kafka_promql",
    "tdengine_promql",
}


SPECIAL_CAPABILITY_OVERRIDES: dict[str, dict[str, Any]] = {
    "oracle": {
        "family": "database",
        "connector": "native_sql",
        "driver_key": "oracle",
        "tools": ["db_execute_query"],
        "credential_fields": ["host", "port", "username", "password", "sid_or_service_name"],
        "setup": {
            "python_package": "oracledb",
            "external_client": "Oracle Instant Client（默认兼容模式）",
            "external_client_required": False,
            "recommended_path_windows": r"D:\AIOPS\oracle_instantclient\instantclient_23_0",
            "recommended_path_linux": "/opt/opscore/oracle/instantclient",
            "env_vars": [
                "OPSCORE_ORACLE_THICK_MODE",
                "OPSCORE_ORACLE_CLIENT_LIB_DIR",
                "OPSCORE_ORACLE_CLIENT_ROOT",
            ],
            "note": "默认使用 python-oracledb Thick Mode 兼容旧库、TNS 和老版本密码校验；需要纯 Thin Mode 时可通过资产参数或环境变量关闭。",
        },
        "maturity": "native",
    },
    "mysql": {
        "family": "database",
        "connector": "native_sql",
        "driver_key": "mysql",
        "tools": ["db_execute_query"],
        "credential_fields": ["host", "port", "username", "password", "database"],
        "setup": {
            "python_package": "pymysql",
            "external_client_required": False,
            "note": "Uses PyMySQL; no system client is required.",
        },
        "maturity": "native",
    },
    "postgresql": {
        "family": "database",
        "connector": "native_sql",
        "driver_key": "postgresql",
        "tools": ["db_execute_query"],
        "credential_fields": ["host", "port", "username", "password", "database"],
        "setup": {
            "python_package": "psycopg2",
            "external_client_required": False,
            "note": "Uses psycopg2-binary by default.",
        },
        "maturity": "native",
    },
    "mssql": {
        "family": "database",
        "connector": "native_sql",
        "driver_key": "mssql",
        "tools": ["db_execute_query"],
        "credential_fields": ["host", "port", "username", "password", "database"],
        "setup": {
            "python_package": "pyodbc",
            "external_client": "Microsoft ODBC Driver 17 for SQL Server",
            "external_client_required": True,
            "note": "优先使用 pyodbc + Microsoft ODBC Driver 17；如运行环境只有 Driver 18，OpsCore 会兼容使用。",
        },
        "maturity": "native",
    },
    "redis": {
        "family": "database",
        "connector": "native_kv",
        "driver_key": "redis",
        "tools": ["redis_execute_command"],
        "credential_fields": ["host", "port", "password"],
        "setup": {
            "python_package": "redis",
            "external_client_required": False,
            "note": "Uses redis-py; no system client is required.",
        },
        "maturity": "native",
    },
    "memcached": {
        "family": "database",
        "connector": "native_kv",
        "driver_key": "memcached",
        "operation_model": "native_client",
        "tools": ["memcached_execute_command"],
        "credential_fields": ["host", "port"],
        "safety_category": "memcached",
        "setup": {
            "python_package": None,
            "external_client_required": False,
            "note": "Uses Memcached text protocol over TCP; read-only version/stats/get are supported without an external driver.",
        },
        "maturity": "native",
    },
    "mongodb": {
        "family": "database",
        "connector": "native_document",
        "driver_key": "mongodb",
        "tools": ["mongodb_find"],
        "credential_fields": ["host", "port", "username", "password", "database"],
        "setup": {
            "python_package": "pymongo",
            "external_client_required": False,
            "note": "Uses PyMongo; no system client is required.",
        },
        "maturity": "native",
    },
    "linux": {
        "family": "operating_system",
        "connector": "ssh_shell",
        "tools": ["linux_execute_command"],
        "credential_fields": ["host", "port", "username", "password"],
        "maturity": "native",
    },
    "windows": {
        "family": "operating_system",
        "connector": "winrm_powershell",
        "tools": ["winrm_execute_command"],
        "credential_fields": ["host", "port", "username", "password"],
        "setup": {
            "python_package": "pywinrm",
            "external_client_required": False,
            "note": "Requires WinRM enabled on the Windows target.",
        },
        "maturity": "native",
    },
    "windows_script": {
        "family": "operating_system",
        "connector": "winrm_powershell",
        "tools": ["winrm_execute_command"],
        "credential_fields": ["host", "port", "username", "password"],
        "setup": {
            "python_package": "pywinrm",
            "external_client_required": False,
            "note": "HertzBeat 的 Windows Script 是采集器执行 CMD/PowerShell；OpsCore 统一按 WinRM/PowerShell 接入。",
        },
        "maturity": "native",
    },
    "hyperv": {
        "family": "virtualization",
        "connector": "winrm_powershell",
        "operation_model": "managed_session",
        "tools": ["winrm_execute_command"],
        "credential_fields": ["host", "port", "username", "password"],
        "setup": {
            "python_package": "pywinrm",
            "external_client_required": False,
            "note": "Requires WinRM enabled and Hyper-V PowerShell module available on the target host.",
        },
        "maturity": "native",
    },
    "s3": {
        "family": "storage",
        "connector": "object_storage_api",
        "tools": ["storage_api_request"],
        "credential_fields": ["host", "port", "access_key", "secret_key", "bucket"],
        "setup": {
            "python_package": "boto3",
            "external_client_required": False,
            "note": "Uses boto3 S3-compatible APIs. Read-only bucket/object discovery is supported; write operations still require approval policy coverage.",
        },
        "maturity": "native",
    },
    "minio": {
        "family": "storage",
        "connector": "object_storage_api",
        "tools": ["storage_api_request"],
        "credential_fields": ["host", "port", "access_key", "secret_key", "bucket"],
        "setup": {
            "python_package": "boto3",
            "external_client_required": False,
            "note": "Uses boto3 S3-compatible APIs. Configure endpoint_url for non-standard MinIO deployments if host/port is not enough.",
        },
        "maturity": "native",
    },
    "ipmi": {
        "family": "hardware_oob",
        "connector": "service_probe",
        "operation_model": "probe_client",
        "tools": ["service_probe_request"],
        "credential_fields": ["host", "port", "username", "password"],
        "safety_category": "http_api",
        "setup": {
            "python_package": None,
            "external_client_required": False,
            "note": "IPMI/BMC 标准远程管理通常使用 UDP 623。当前先提供只读连通性探测，电源控制等写操作后续应接专用 IPMI 适配器并走审批。",
        },
        "maturity": "generic",
    },
    "ldap": {
        "family": "security",
        "connector": "service_probe",
        "operation_model": "probe_client",
        "tools": ["service_probe_request"],
        "credential_fields": ["host", "port", "username", "password", "base_dn"],
        "safety_category": "http_api",
        "setup": {
            "python_package": None,
            "external_client_required": False,
            "note": "LDAP/AD 标准端口为 389，LDAPS 常用 636。当前先提供 TCP/健康探测，目录查询后续应接 ldap3 专用适配器。",
        },
        "maturity": "generic",
    },
    "dns_sd": {
        "family": "discovery",
        "connector": "service_probe",
        "operation_model": "probe_client",
        "tools": ["service_probe_request"],
        "credential_fields": ["host", "port"],
        "safety_category": "http_api",
        "maturity": "generic",
    },
    "zookeeper_sd": {
        "family": "discovery",
        "connector": "service_probe",
        "operation_model": "probe_client",
        "tools": ["service_probe_request"],
        "credential_fields": ["host", "port"],
        "safety_category": "http_api",
        "maturity": "generic",
    },
    "jvm": {
        "family": "middleware",
        "connector": "service_probe",
        "operation_model": "probe_client",
        "tools": ["service_probe_request"],
        "credential_fields": ["host", "port", "username", "password"],
        "safety_category": "http_api",
        "setup": {
            "python_package": None,
            "external_client_required": False,
            "note": "JMX/RMI 端口通常由应用启动参数配置。当前先提供 TCP 健康探测，MBean 查询后续接 JMX 专用适配器。",
        },
        "maturity": "generic",
    },
    "kafka_client": {
        "family": "middleware",
        "connector": "service_probe",
        "operation_model": "probe_client",
        "tools": ["service_probe_request"],
        "credential_fields": ["host", "port", "username", "password"],
        "safety_category": "http_api",
        "setup": {
            "python_package": None,
            "external_client_required": False,
            "note": "Kafka Broker 客户端入口通常是 9092。当前先提供 TCP 连通性探测，Topic/Consumer Group 管理后续接 Kafka Admin 适配器。",
        },
        "maturity": "generic",
    },
}


PROTOCOL_CAPABILITY_PROFILES: dict[str, dict[str, Any]] = {
    "ssh": {
        "family": "operating_system",
        "connector": "ssh_shell",
        "operation_model": "managed_session",
        "tools": ["linux_execute_command"],
        "credential_fields": ["host", "port", "username", "password"],
        "safety_category": "linux",
        "maturity": "generic",
    },
    "winrm": {
        "family": "operating_system",
        "connector": "winrm_powershell",
        "operation_model": "managed_session",
        "tools": ["winrm_execute_command"],
        "credential_fields": ["host", "port", "username", "password"],
        "safety_category": "windows",
        "maturity": "generic",
    },
    "http_api": {
        "family": "api_platform",
        "connector": "http_api",
        "operation_model": "api_client",
        "tools": ["http_api_request"],
        "credential_fields": ["host", "port", "username", "password", "api_token"],
        "safety_category": "http_api",
        "maturity": "generic",
    },
    "redfish": {
        "family": "hardware_oob",
        "connector": "redfish_api",
        "operation_model": "api_client",
        "tools": ["http_api_request"],
        "credential_fields": ["host", "port", "username", "password"],
        "safety_category": "http_api",
        "maturity": "generic",
    },
    "k8s": {
        "family": "container",
        "connector": "kubernetes_api",
        "operation_model": "api_client",
        "tools": ["k8s_api_request"],
        "credential_fields": ["host", "port", "bearer_token", "kubeconfig"],
        "safety_category": "http_api",
        "maturity": "native",
    },
    "snmp": {
        "family": "network",
        "connector": "snmp",
        "operation_model": "native_client",
        "tools": ["snmp_get"],
        "credential_fields": ["host", "port", "community", "snmp_v3_credentials"],
        "safety_category": "snmp",
        "maturity": "generic",
    },
    "redis": SPECIAL_CAPABILITY_OVERRIDES["redis"],
    "mongodb": SPECIAL_CAPABILITY_OVERRIDES["mongodb"],
    "mysql": SPECIAL_CAPABILITY_OVERRIDES["mysql"],
    "oracle": SPECIAL_CAPABILITY_OVERRIDES["oracle"],
    "postgresql": SPECIAL_CAPABILITY_OVERRIDES["postgresql"],
    "mssql": SPECIAL_CAPABILITY_OVERRIDES["mssql"],
}
