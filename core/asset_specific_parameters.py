from __future__ import annotations

from copy import deepcopy
from typing import Any

from core.asset_parameter_templates import (
    GENERIC_HTTP_API_PARAMETERS,
    SHARED_PARAMETER_TEMPLATES,
    _boolean_parameter,
    _number_parameter,
    _select_parameter,
    _text_parameter,
)


def apply_asset_parameter_template(capability: dict[str, Any], asset_id: str) -> None:
    capability["parameter_template"] = deepcopy(
        SHARED_PARAMETER_TEMPLATES.get(str(capability.get("connector") or ""), [])
    )
    if capability.get("connector") == "virtualization_api" and asset_id != "openstack":
        virtualization_params: dict[str, list[dict[str, Any]]] = {
            "vmware": [
                {
                    "field": "vmware_session_id",
                    "label": "vCenter Session ID",
                    "type": "password",
                    "required": False,
                    "group": "vmware",
                },
                {
                    "field": "api_token",
                    "label": "API Token",
                    "type": "password",
                    "required": False,
                    "group": "vmware",
                },
            ],
            "proxmox": [
                {
                    "field": "api_token",
                    "label": "Proxmox API Token",
                    "type": "password",
                    "required": False,
                    "group": "proxmox",
                },
                _text_parameter("api_base_path", "API 基础路径", group="proxmox", default="/api2/json"),
                _text_parameter("node", "默认节点", group="proxmox"),
                _text_parameter("realm", "认证 Realm", group="proxmox", default="pam"),
                {
                    "field": "verify_ssl",
                    "label": "校验证书",
                    "type": "boolean",
                    "required": False,
                    "defaultValue": True,
                    "group": "proxmox",
                },
            ],
            "zstack": [
                {
                    "field": "zstack_session_uuid",
                    "label": "Session UUID",
                    "type": "password",
                    "required": False,
                    "group": "zstack",
                },
                {
                    "field": "api_token",
                    "label": "API Token / Session UUID",
                    "type": "password",
                    "required": False,
                    "group": "zstack",
                },
                {
                    "field": "auth_path",
                    "label": "登录路径",
                    "type": "text",
                    "required": False,
                    "defaultValue": "/zstack/v1/accounts/login",
                    "group": "zstack",
                }
            ],
        }
        capability["parameter_template"] = deepcopy(virtualization_params.get(asset_id, []))
    if asset_id == "ldap":
        capability["parameter_template"] = [
            {
                "field": "base_dn",
                "label": "Base DN",
                "type": "text",
                "required": False,
                "placeholder": "dc=example,dc=com",
                "group": "ldap",
            },
            {
                "field": "use_ssl",
                "label": "使用 LDAPS",
                "type": "boolean",
                "required": False,
                "defaultValue": False,
                "group": "ldap",
            },
        ]
    elif asset_id == "ipmi":
        capability["parameter_template"] = [
            {
                "field": "interface",
                "label": "IPMI 接口",
                "type": "select",
                "required": False,
                "defaultValue": "lanplus",
                "options": [
                    {"label": "LAN Plus", "value": "lanplus"},
                    {"label": "LAN", "value": "lan"},
                ],
                "group": "ipmi",
            }
        ]
    elif asset_id == "kafka_client":
        capability["parameter_template"] = [
            {
                "field": "security_protocol",
                "label": "安全协议",
                "type": "select",
                "required": False,
                "defaultValue": "PLAINTEXT",
                "options": [
                    {"label": "PLAINTEXT", "value": "PLAINTEXT"},
                    {"label": "SASL_PLAINTEXT", "value": "SASL_PLAINTEXT"},
                    {"label": "SASL_SSL", "value": "SASL_SSL"},
                    {"label": "SSL", "value": "SSL"},
                ],
                "group": "kafka",
            },
            {
                "field": "sasl_mechanism",
                "label": "SASL 机制",
                "type": "select",
                "required": False,
                "defaultValue": "PLAIN",
                "options": [
                    {"label": "PLAIN", "value": "PLAIN"},
                    {"label": "SCRAM-SHA-256", "value": "SCRAM-SHA-256"},
                    {"label": "SCRAM-SHA-512", "value": "SCRAM-SHA-512"},
                ],
                "group": "kafka",
            },
        ]
    elif asset_id == "jvm":
        capability["parameter_template"] = [
            {
                "field": "jmx_service_url",
                "label": "JMX Service URL",
                "type": "text",
                "required": False,
                "placeholder": "service:jmx:rmi:///jndi/rmi://host:9999/jmxrmi",
                "group": "jmx",
            }
        ]
    elif asset_id in {"mysql", "mariadb", "tidb", "oceanbase", "doris_fe", "greptime", "starrocks_fe"}:
        capability["parameter_template"] = [
            _select_parameter(
                "ssl_mode",
                "SSL 模式",
                group="mysql",
                default="preferred",
                options=[
                    ("禁用", "disabled"),
                    ("优先使用", "preferred"),
                    ("必须使用", "required"),
                    ("校验 CA", "verify_ca"),
                    ("校验主机名", "verify_identity"),
                ],
            ),
            _text_parameter("charset", "字符集", group="mysql", default="utf8mb4"),
            _number_parameter("connect_timeout", "连接超时(秒)", group="mysql", default=10),
        ]
    elif asset_id in {"postgresql", "kingbase", "greenplum", "opengauss", "vastbase"}:
        capability["parameter_template"] = [
            _select_parameter(
                "ssl_mode",
                "SSL Mode",
                group="postgresql",
                default="prefer",
                options=[
                    ("禁用", "disable"),
                    ("优先使用", "prefer"),
                    ("必须使用", "require"),
                    ("校验 CA", "verify-ca"),
                    ("校验主机名", "verify-full"),
                ],
            ),
            _text_parameter("search_path", "Search Path", group="postgresql"),
            _number_parameter("connect_timeout", "连接超时(秒)", group="postgresql", default=10),
        ]
    elif asset_id in {"mssql", "sqlserver"}:
        capability["parameter_template"] = [
            _boolean_parameter("encrypt", "启用加密", group="mssql", default=True),
            _boolean_parameter("trust_server_certificate", "信任服务器证书", group="mssql", default=False),
            _number_parameter("connect_timeout", "连接超时(秒)", group="mssql", default=10),
        ]
    elif asset_id == "oracle":
        capability["parameter_template"] = [
            _select_parameter(
                "oracle_connect_type",
                "Oracle 连接类型",
                group="oracle",
                default="sid",
                options=[
                    ("SID", "sid"),
                    ("服务名", "service_name"),
                    ("TNS Alias", "tns_alias"),
                ],
            ),
            _text_parameter("service_name", "服务名", group="oracle"),
            _text_parameter("sid", "SID", group="oracle"),
            _text_parameter("tns_alias", "TNS Alias", group="oracle"),
            _number_parameter("connect_timeout", "连接超时(秒)", group="oracle", default=10),
            _boolean_parameter("use_thick_mode", "启用 Thick Mode", group="oracle", default=False),
        ]
    elif asset_id in {"redis", "valkey", "kvrocks"}:
        capability["parameter_template"] = [
            _number_parameter("db_index", "数据库编号", group="redis", default=0),
            _boolean_parameter("tls", "启用 TLS", group="redis", default=False),
            _number_parameter("connect_timeout", "连接超时(秒)", group="redis", default=10),
        ]
    elif asset_id == "redis_cluster":
        capability["parameter_template"] = [
            _text_parameter("startup_nodes", "启动节点", group="redis_cluster", placeholder="host1:6379,host2:6379"),
            _boolean_parameter("tls", "启用 TLS", group="redis_cluster", default=False),
            _number_parameter("connect_timeout", "连接超时(秒)", group="redis_cluster", default=10),
        ]
    elif asset_id == "redis_sentinel":
        capability["parameter_template"] = [
            _text_parameter("sentinel_master", "Sentinel Master", group="redis_sentinel", default="mymaster"),
            _text_parameter("sentinel_nodes", "Sentinel 节点", group="redis_sentinel", placeholder="host1:26379,host2:26379"),
            _number_parameter("db_index", "数据库编号", group="redis_sentinel", default=0),
        ]
    elif asset_id == "memcached":
        capability["parameter_template"] = [
            _boolean_parameter("binary_protocol", "二进制协议", group="memcached", default=False),
            _number_parameter("connect_timeout", "连接超时(秒)", group="memcached", default=10),
        ]
    elif asset_id in {"mongodb", "mongodb_atlas"}:
        capability["parameter_template"] = [
            _text_parameter("auth_source", "认证库", group="mongodb", default="admin"),
            _text_parameter("replica_set", "Replica Set", group="mongodb"),
            _boolean_parameter("tls", "启用 TLS", group="mongodb", default=asset_id == "mongodb_atlas"),
            _text_parameter("read_preference", "Read Preference", group="mongodb", default="primary"),
            _number_parameter("connect_timeout", "连接超时(秒)", group="mongodb", default=10),
        ]
    elif asset_id == "shenyu":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            {
                "field": "gateway_port",
                "label": "网关端口",
                "type": "number",
                "required": False,
                "defaultValue": 9195,
                "group": "shenyu",
            },
            {
                "field": "metrics_port",
                "label": "指标端口",
                "type": "number",
                "required": False,
                "defaultValue": 8090,
                "group": "shenyu",
            },
        ]
    elif asset_id == "iceberg":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            {
                "field": "warehouse",
                "label": "Warehouse 路径",
                "type": "text",
                "required": False,
                "placeholder": "s3://bucket/warehouse 或 hdfs://...",
                "group": "iceberg",
            },
            {
                "field": "catalog_type",
                "label": "Catalog 类型",
                "type": "select",
                "required": False,
                "defaultValue": "rest",
                "options": [
                    {"label": "REST", "value": "rest"},
                    {"label": "Hive", "value": "hive"},
                    {"label": "Glue", "value": "glue"},
                    {"label": "Nessie", "value": "nessie"},
                ],
                "group": "iceberg",
            },
        ]
    elif asset_id == "rabbitmq":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            {
                "field": "amqp_port",
                "label": "AMQP 端口",
                "type": "number",
                "required": False,
                "defaultValue": 5672,
                "group": "rabbitmq",
            },
            {
                "field": "amqps_port",
                "label": "AMQPS 端口",
                "type": "number",
                "required": False,
                "defaultValue": 5671,
                "group": "rabbitmq",
            },
        ]
    elif asset_id == "activemq":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            {
                "field": "broker_port",
                "label": "Broker 端口",
                "type": "number",
                "required": False,
                "defaultValue": 61616,
                "group": "activemq",
            },
            {
                "field": "console_path",
                "label": "控制台路径",
                "type": "text",
                "required": False,
                "defaultValue": "/admin",
                "group": "activemq",
            },
        ]
    elif asset_id == "pulsar":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            {
                "field": "broker_port",
                "label": "Broker 端口",
                "type": "number",
                "required": False,
                "defaultValue": 6650,
                "group": "pulsar",
            },
            {
                "field": "broker_tls_port",
                "label": "Broker TLS 端口",
                "type": "number",
                "required": False,
                "defaultValue": 6651,
                "group": "pulsar",
            },
        ]
    elif asset_id == "emqx":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            {
                "field": "mqtt_port",
                "label": "MQTT TCP 端口",
                "type": "number",
                "required": False,
                "defaultValue": 1883,
                "group": "emqx",
            },
            {
                "field": "mqtt_tls_port",
                "label": "MQTT TLS 端口",
                "type": "number",
                "required": False,
                "defaultValue": 8883,
                "group": "emqx",
            },
            {
                "field": "management_port",
                "label": "管理 API 端口",
                "type": "number",
                "required": False,
                "defaultValue": 8081,
                "group": "emqx",
            },
        ]
    elif asset_id == "apollo":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            {
                "field": "portal_port",
                "label": "Portal 端口",
                "type": "number",
                "required": False,
                "defaultValue": 8070,
                "group": "apollo",
            },
            {
                "field": "admin_port",
                "label": "Admin Service 端口",
                "type": "number",
                "required": False,
                "defaultValue": 8090,
                "group": "apollo",
            },
        ]
    elif asset_id == "tomcat":
        capability["parameter_template"] = [
            {
                "field": "http_port",
                "label": "HTTP 服务端口",
                "type": "number",
                "required": False,
                "defaultValue": 8080,
                "group": "tomcat",
            },
            {
                "field": "shutdown_port",
                "label": "Shutdown 端口",
                "type": "number",
                "required": False,
                "defaultValue": 8005,
                "group": "tomcat",
            },
        ]
    elif asset_id == "nginx":
        capability["parameter_template"] = [
            {
                "field": "http_port",
                "label": "HTTP 服务端口",
                "type": "number",
                "required": False,
                "defaultValue": 80,
                "group": "nginx",
            },
            {
                "field": "https_port",
                "label": "HTTPS 服务端口",
                "type": "number",
                "required": False,
                "defaultValue": 443,
                "group": "nginx",
            },
        ]
    elif asset_id == "rocketmq":
        capability["parameter_template"] = [
            {
                "field": "namesrv_port",
                "label": "NameServer 端口",
                "type": "number",
                "required": False,
                "defaultValue": 9876,
                "group": "rocketmq",
            },
            {
                "field": "broker_port",
                "label": "Broker 端口",
                "type": "number",
                "required": False,
                "defaultValue": 10911,
                "group": "rocketmq",
            },
        ]
    elif asset_id == "zookeeper":
        capability["parameter_template"] = [
            {
                "field": "client_port",
                "label": "客户端端口",
                "type": "number",
                "required": False,
                "defaultValue": 2181,
                "group": "zookeeper",
            },
            {
                "field": "admin_port",
                "label": "AdminServer 端口",
                "type": "number",
                "required": False,
                "defaultValue": 8080,
                "group": "zookeeper",
            },
        ]
    elif asset_id == "kafka":
        capability["parameter_template"] = [
            {
                "field": "broker_port",
                "label": "Broker 端口",
                "type": "number",
                "required": False,
                "defaultValue": 9092,
                "group": "kafka",
            },
            {
                "field": "controller_port",
                "label": "Controller 端口",
                "type": "number",
                "required": False,
                "defaultValue": 9093,
                "group": "kafka",
            },
        ]
    elif asset_id == "ceph":
        capability["parameter_template"] = [
            {
                "field": "mon_v2_port",
                "label": "Monitor v2 端口",
                "type": "number",
                "required": False,
                "defaultValue": 3300,
                "group": "ceph",
            },
            {
                "field": "mon_v1_port",
                "label": "Monitor v1 端口",
                "type": "number",
                "required": False,
                "defaultValue": 6789,
                "group": "ceph",
            },
            {
                "field": "dashboard_port",
                "label": "Dashboard 端口",
                "type": "number",
                "required": False,
                "defaultValue": 8443,
                "group": "ceph",
            },
        ]
    elif asset_id == "nfs":
        capability["parameter_template"] = [
            {
                "field": "nfs_port",
                "label": "NFS 服务端口",
                "type": "number",
                "required": False,
                "defaultValue": 2049,
                "group": "nfs",
            },
            {
                "field": "export_path",
                "label": "导出路径",
                "type": "text",
                "required": False,
                "placeholder": "/data/share",
                "group": "nfs",
            },
        ]
    elif asset_id == "hdfs":
        capability["parameter_template"] = [
            {
                "field": "namenode_http_port",
                "label": "NameNode HTTP 端口",
                "type": "number",
                "required": False,
                "defaultValue": 9870,
                "group": "hdfs",
            },
            {
                "field": "namenode_rpc_port",
                "label": "NameNode RPC 端口",
                "type": "number",
                "required": False,
                "defaultValue": 8020,
                "group": "hdfs",
            },
            {
                "field": "datanode_http_port",
                "label": "DataNode HTTP 端口",
                "type": "number",
                "required": False,
                "defaultValue": 9864,
                "group": "hdfs",
            },
        ]
    elif asset_id == "glusterfs":
        capability["parameter_template"] = [
            {
                "field": "management_port",
                "label": "Gluster 管理端口",
                "type": "number",
                "required": False,
                "defaultValue": 24007,
                "group": "glusterfs",
            },
            {
                "field": "volume_name",
                "label": "卷名称",
                "type": "text",
                "required": False,
                "group": "glusterfs",
            },
        ]
    elif asset_id == "kvm":
        capability["parameter_template"] = [
            {
                "field": "libvirt_port",
                "label": "Libvirt TCP 端口",
                "type": "number",
                "required": False,
                "defaultValue": 16509,
                "group": "kvm",
            },
            {
                "field": "qemu_uri",
                "label": "QEMU URI",
                "type": "text",
                "required": False,
                "defaultValue": "qemu:///system",
                "group": "kvm",
            },
        ]
    elif asset_id == "prometheus":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            {
                "field": "query_path",
                "label": "即时查询路径",
                "type": "text",
                "required": False,
                "defaultValue": "/api/v1/query",
                "group": "prometheus",
            },
            {
                "field": "query_range_path",
                "label": "范围查询路径",
                "type": "text",
                "required": False,
                "defaultValue": "/api/v1/query_range",
                "group": "prometheus",
            },
            {
                "field": "targets_path",
                "label": "Targets 路径",
                "type": "text",
                "required": False,
                "defaultValue": "/api/v1/targets",
                "group": "prometheus",
            },
        ]
    elif asset_id == "alertmanager":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            {
                "field": "alerts_path",
                "label": "告警路径",
                "type": "text",
                "required": False,
                "defaultValue": "/api/v2/alerts",
                "group": "alertmanager",
            },
            {
                "field": "silences_path",
                "label": "静默路径",
                "type": "text",
                "required": False,
                "defaultValue": "/api/v2/silences",
                "group": "alertmanager",
            },
        ]
    elif asset_id == "grafana":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            {
                "field": "api_base_path",
                "label": "API 基础路径",
                "type": "text",
                "required": False,
                "defaultValue": "/api",
                "group": "grafana",
            },
            {
                "field": "dashboard_search_path",
                "label": "仪表盘搜索路径",
                "type": "text",
                "required": False,
                "defaultValue": "/api/search",
                "group": "grafana",
            },
            {
                "field": "org_id",
                "label": "组织 ID",
                "type": "number",
                "required": False,
                "defaultValue": 1,
                "group": "grafana",
            },
        ]
    elif asset_id == "loki":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            {
                "field": "query_path",
                "label": "日志查询路径",
                "type": "text",
                "required": False,
                "defaultValue": "/loki/api/v1/query",
                "group": "loki",
            },
            {
                "field": "query_range_path",
                "label": "日志范围查询路径",
                "type": "text",
                "required": False,
                "defaultValue": "/loki/api/v1/query_range",
                "group": "loki",
            },
        ]
    elif asset_id == "victoriametrics":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            {
                "field": "query_path",
                "label": "PromQL 查询路径",
                "type": "text",
                "required": False,
                "defaultValue": "/api/v1/query",
                "group": "victoriametrics",
            },
            {
                "field": "tenant_path",
                "label": "租户路径前缀",
                "type": "text",
                "required": False,
                "placeholder": "/select/0/prometheus",
                "group": "victoriametrics",
            },
        ]
    elif asset_id == "zabbix":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            {
                "field": "api_path",
                "label": "JSON-RPC API 路径",
                "type": "text",
                "required": False,
                "defaultValue": "/api_jsonrpc.php",
                "group": "zabbix",
            },
            {
                "field": "auth_mode",
                "label": "认证方式",
                "type": "select",
                "required": False,
                "defaultValue": "api_token",
                "options": [
                    {"label": "API Token", "value": "api_token"},
                    {"label": "用户名密码", "value": "password"},
                ],
                "group": "zabbix",
            },
        ]
    elif asset_id in {"hertzbeat", "hertzbeat_token"}:
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            {
                "field": "monitor_path",
                "label": "监控对象路径",
                "type": "text",
                "required": False,
                "defaultValue": "/api/monitor",
                "group": "hertzbeat",
            },
            {
                "field": "alert_path",
                "label": "告警路径",
                "type": "text",
                "required": False,
                "defaultValue": "/api/alerts",
                "group": "hertzbeat",
            },
            {
                "field": "token_header",
                "label": "Token 请求头",
                "type": "text",
                "required": False,
                "defaultValue": "Authorization",
                "group": "hertzbeat",
            },
        ]
    elif asset_id == "manageengine":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            {
                "field": "api_base_path",
                "label": "REST API 基础路径",
                "type": "text",
                "required": False,
                "defaultValue": "/api",
                "group": "manageengine",
            },
            {
                "field": "api_key",
                "label": "API Key",
                "type": "password",
                "required": False,
                "group": "manageengine",
            },
            {
                "field": "product",
                "label": "产品线",
                "type": "select",
                "required": False,
                "defaultValue": "opmanager",
                "options": [
                    {"label": "OpManager", "value": "opmanager"},
                    {"label": "Applications Manager", "value": "applications_manager"},
                    {"label": "ServiceDesk Plus", "value": "servicedesk_plus"},
                ],
                "group": "manageengine",
            },
        ]
    elif asset_id == "openai":
        capability["parameter_template"] = [
            {
                "field": "base_url",
                "label": "API Base URL",
                "type": "text",
                "required": False,
                "defaultValue": "https://api.openai.com/v1",
                "group": "openai",
            },
            {
                "field": "api_token",
                "label": "API Key",
                "type": "password",
                "required": False,
                "group": "openai",
            },
            {
                "field": "model",
                "label": "默认模型",
                "type": "text",
                "required": False,
                "placeholder": "gpt-5.2",
                "group": "openai",
            },
            {
                "field": "organization",
                "label": "Organization",
                "type": "text",
                "required": False,
                "group": "openai",
            },
        ]
    elif asset_id == "deepseek":
        capability["parameter_template"] = [
            {
                "field": "base_url",
                "label": "API Base URL",
                "type": "text",
                "required": False,
                "defaultValue": "https://api.deepseek.com",
                "group": "deepseek",
            },
            {
                "field": "api_token",
                "label": "API Key",
                "type": "password",
                "required": False,
                "group": "deepseek",
            },
            {
                "field": "model",
                "label": "默认模型",
                "type": "text",
                "required": False,
                "placeholder": "deepseek-chat",
                "group": "deepseek",
            },
        ]
    elif asset_id == "ollama":
        capability["parameter_template"] = [
            {
                "field": "base_url",
                "label": "API Base URL",
                "type": "text",
                "required": False,
                "defaultValue": "http://localhost:11434",
                "group": "ollama",
            },
            {
                "field": "model",
                "label": "默认模型",
                "type": "text",
                "required": False,
                "placeholder": "llama3.2",
                "group": "ollama",
            },
        ]
    elif asset_id == "lmstudio":
        capability["parameter_template"] = [
            {
                "field": "base_url",
                "label": "OpenAI 兼容地址",
                "type": "text",
                "required": False,
                "defaultValue": "http://localhost:1234/v1",
                "group": "lmstudio",
            },
            {
                "field": "api_token",
                "label": "API Key",
                "type": "password",
                "required": False,
                "placeholder": "lm-studio",
                "group": "lmstudio",
            },
            {
                "field": "model",
                "label": "已加载模型",
                "type": "text",
                "required": False,
                "group": "lmstudio",
            },
        ]
    elif asset_id == "redfish":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            {
                "field": "root_path",
                "label": "Service Root",
                "type": "text",
                "required": False,
                "defaultValue": "/redfish/v1",
                "group": "redfish",
            },
            {
                "field": "systems_path",
                "label": "Systems 路径",
                "type": "text",
                "required": False,
                "defaultValue": "/redfish/v1/Systems",
                "group": "redfish",
            },
        ]
    elif asset_id == "hikvision_isapi":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            {
                "field": "isapi_base_path",
                "label": "ISAPI 基础路径",
                "type": "text",
                "required": False,
                "defaultValue": "/ISAPI",
                "group": "hikvision",
            }
        ]
    elif asset_id == "dahua":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            {
                "field": "cgi_base_path",
                "label": "CGI 基础路径",
                "type": "text",
                "required": False,
                "defaultValue": "/cgi-bin",
                "group": "dahua",
            }
        ]
    elif asset_id == "uniview":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            {
                "field": "lapi_base_path",
                "label": "LAPI 基础路径",
                "type": "text",
                "required": False,
                "defaultValue": "/LAPI",
                "group": "uniview",
            }
        ]
    elif asset_id in {"bastion", "audit"}:
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            {
                "field": "tenant",
                "label": "租户/组织",
                "type": "text",
                "required": False,
                "group": "security",
            },
            {
                "field": "events_path",
                "label": "审计事件路径",
                "type": "text",
                "required": False,
                "defaultValue": "/api/events",
                "group": "security",
            },
        ]
    elif asset_id == "jenkins":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            {
                "field": "crumb_path",
                "label": "Crumb Issuer 路径",
                "type": "text",
                "required": False,
                "defaultValue": "/crumbIssuer/api/json",
                "group": "jenkins",
            },
            {
                "field": "job_path",
                "label": "任务路径前缀",
                "type": "text",
                "required": False,
                "defaultValue": "/job",
                "group": "jenkins",
            },
        ]
    elif asset_id == "harbor":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            {
                "field": "api_path",
                "label": "Harbor API 路径",
                "type": "text",
                "required": False,
                "defaultValue": "/api/v2.0",
                "group": "harbor",
            },
            {
                "field": "project_name",
                "label": "默认项目",
                "type": "text",
                "required": False,
                "group": "harbor",
            },
        ]
    elif asset_id in {"k8s", "kubernetes"}:
        capability["parameter_template"] = [
            {
                "field": "namespace",
                "label": "默认命名空间",
                "type": "text",
                "required": False,
                "defaultValue": "default",
                "group": "kubernetes",
            },
            {
                "field": "context",
                "label": "Kube Context",
                "type": "text",
                "required": False,
                "group": "kubernetes",
            },
            {
                "field": "bearer_token",
                "label": "Bearer Token",
                "type": "password",
                "required": False,
                "group": "kubernetes",
            },
            {
                "field": "verify_ssl",
                "label": "校验证书",
                "type": "boolean",
                "required": False,
                "defaultValue": True,
                "group": "kubernetes",
            },
        ]
    elif asset_id in {"nacos", "nacos_sd"}:
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            _text_parameter("namespace_id", "命名空间 ID", group="nacos", default="public"),
            _text_parameter("service_name", "服务名", group="nacos"),
            _text_parameter("group_name", "分组", group="nacos", default="DEFAULT_GROUP"),
            _text_parameter("config_path", "配置 OpenAPI 路径", group="nacos", default="/nacos/v1/cs/configs"),
            _text_parameter("instance_path", "实例 OpenAPI 路径", group="nacos", default="/nacos/v1/ns/instance"),
        ]
    elif asset_id in {"consul", "consul_sd"}:
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            _text_parameter("datacenter", "数据中心", group="consul"),
            _text_parameter("catalog_services_path", "服务目录路径", group="consul", default="/v1/catalog/services"),
            _text_parameter("agent_services_path", "Agent 服务路径", group="consul", default="/v1/agent/services"),
            _text_parameter("health_service_path", "健康检查路径前缀", group="consul", default="/v1/health/service"),
        ]
    elif asset_id == "airflow":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            _text_parameter("api_base_path", "REST API 基础路径", group="airflow", default="/api/v1"),
            _text_parameter("dags_path", "DAG 列表路径", group="airflow", default="/api/v1/dags"),
            _text_parameter("dag_runs_path", "DAG Run 路径模板", group="airflow", default="/api/v1/dags/{dag_id}/dagRuns"),
        ]
    elif asset_id == "dolphinscheduler":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            _text_parameter("api_base_path", "API 基础路径", group="dolphinscheduler", default="/dolphinscheduler"),
            _text_parameter("project_code", "项目 Code", group="dolphinscheduler"),
            _text_parameter("tenant_code", "租户 Code", group="dolphinscheduler"),
            _text_parameter("process_definition_path", "流程定义路径", group="dolphinscheduler", default="/projects/{projectCode}/process-definition"),
        ]
    elif asset_id in {"flink", "flink_on_yarn"}:
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            _text_parameter("jobs_path", "作业列表路径", group="flink", default="/jobs"),
            _text_parameter("job_detail_path", "作业详情路径模板", group="flink", default="/jobs/{job_id}"),
            _text_parameter("taskmanagers_path", "TaskManagers 路径", group="flink", default="/taskmanagers"),
            _text_parameter("yarn_application_id", "YARN Application ID", group="flink"),
        ]
    elif asset_id in {"hadoop", "hdfs_namenode"}:
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            _text_parameter("webhdfs_path", "WebHDFS 路径", group="hadoop", default="/webhdfs/v1"),
            _text_parameter("namenode_jmx_path", "NameNode JMX 路径", group="hadoop", default="/jmx"),
            _number_parameter("namenode_rpc_port", "NameNode RPC 端口", group="hadoop", default=8020),
            _text_parameter("hdfs_user", "HDFS 用户", group="hadoop"),
        ]
    elif asset_id == "hdfs_datanode":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            _text_parameter("datanode_jmx_path", "DataNode JMX 路径", group="hdfs_datanode", default="/jmx"),
            _number_parameter("datanode_ipc_port", "DataNode IPC 端口", group="hdfs_datanode", default=9867),
            _number_parameter("datanode_transfer_port", "DataNode 数据传输端口", group="hdfs_datanode", default=9866),
        ]
    elif asset_id == "yarn":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            _text_parameter("cluster_info_path", "集群信息路径", group="yarn", default="/ws/v1/cluster/info"),
            _text_parameter("cluster_metrics_path", "集群指标路径", group="yarn", default="/ws/v1/cluster/metrics"),
            _text_parameter("applications_path", "应用列表路径", group="yarn", default="/ws/v1/cluster/apps"),
            _text_parameter("queue", "默认队列", group="yarn"),
        ]
    elif asset_id == "spark":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            _text_parameter("master_ui_path", "Master UI 路径", group="spark", default="/"),
            _number_parameter("submission_rest_port", "提交 REST 端口", group="spark", default=6066),
            _text_parameter("submission_path", "提交 REST 路径", group="spark", default="/v1/submissions"),
            _text_parameter("master_url", "Spark Master URL", group="spark", placeholder="spark://host:7077"),
        ]
    elif asset_id == "storm":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            _text_parameter("cluster_summary_path", "集群摘要路径", group="storm", default="/api/v1/cluster/summary"),
            _text_parameter("topology_summary_path", "拓扑摘要路径", group="storm", default="/api/v1/topology/summary"),
        ]
    elif asset_id == "prestodb":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            _text_parameter("statement_path", "SQL 提交路径", group="prestodb", default="/v1/statement"),
            _text_parameter("catalog", "Catalog", group="prestodb"),
            _text_parameter("schema", "Schema", group="prestodb"),
            _text_parameter("source", "Source", group="prestodb", default="opscore"),
        ]
    elif asset_id in {"springboot2", "springboot3", "spring_gateway", "dynamic_tp"}:
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            _text_parameter("actuator_base_path", "Actuator 基础路径", group="spring", default="/actuator"),
            _text_parameter("health_path", "健康检查路径", group="spring", default="/actuator/health"),
            _text_parameter("metrics_path", "指标路径", group="spring", default="/actuator/metrics"),
            _text_parameter("env_path", "环境路径", group="spring", default="/actuator/env"),
        ]
        if asset_id == "spring_gateway":
            capability["parameter_template"].append(
                _text_parameter("gateway_routes_path", "网关路由路径", group="spring_gateway", default="/actuator/gateway/routes")
            )
        if asset_id == "dynamic_tp":
            capability["parameter_template"].append(
                _text_parameter("thread_pool_path", "线程池路径", group="dynamic_tp", default="/actuator/dynamic-tp")
            )
    elif asset_id == "eureka_sd":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            _text_parameter("eureka_base_path", "Eureka 基础路径", group="eureka", default="/eureka"),
            _text_parameter("apps_path", "应用列表路径", group="eureka", default="/eureka/apps"),
            _text_parameter("app_name", "应用名", group="eureka"),
        ]
    elif asset_id == "seatunnel":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            _text_parameter("rest_base_path", "REST API 基础路径", group="seatunnel", default="/hazelcast/rest/maps"),
            _text_parameter("running_jobs_path", "运行任务路径", group="seatunnel", default="/running-jobs"),
            _text_parameter("completed_jobs_path", "完成任务路径", group="seatunnel", default="/finished-jobs"),
        ]
    elif asset_id == "f5":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            _text_parameter("api_base_path", "iControl REST 基础路径", group="f5", default="/mgmt/tm"),
            _text_parameter("partition", "Partition", group="f5", default="Common"),
            _text_parameter("ltm_pools_path", "LTM Pool 路径", group="f5", default="/mgmt/tm/ltm/pool"),
            _text_parameter("ltm_virtuals_path", "LTM Virtual Server 路径", group="f5", default="/mgmt/tm/ltm/virtual"),
        ]
    elif asset_id == "a10":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            _text_parameter("api_base_path", "aXAPI 基础路径", group="a10", default="/axapi/v3"),
            _text_parameter("auth_path", "认证路径", group="a10", default="/axapi/v3/auth"),
            _text_parameter("partition", "Partition", group="a10"),
            _text_parameter("virtual_server_path", "虚拟服务路径", group="a10", default="/axapi/v3/slb/virtual-server"),
        ]
    elif asset_id == "waf":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            _text_parameter("vendor", "厂商/产品", group="waf"),
            _text_parameter("api_base_path", "管理 API 基础路径", group="waf", default="/api"),
            _text_parameter("policies_path", "策略路径", group="waf", default="/api/policies"),
            _text_parameter("events_path", "事件路径", group="waf", default="/api/events"),
        ]
    elif asset_id == "http_sd":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            _text_parameter("targets_path", "Targets 路径", group="http_sd", default="/targets"),
            _text_parameter("refresh_interval", "刷新间隔", group="http_sd", default="60s"),
            _text_parameter("label_prefix", "标签前缀", group="http_sd"),
        ]
    elif asset_id in {"influxdb_promql", "kafka_promql", "tdengine_promql"}:
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            _text_parameter("query_path", "PromQL 查询路径", group="promql", default="/api/v1/query"),
            _text_parameter("query_range_path", "PromQL 范围查询路径", group="promql", default="/api/v1/query_range"),
            _text_parameter("datasource", "数据源名称", group="promql"),
        ]
        if asset_id == "tdengine_promql":
            capability["parameter_template"].append(
                _text_parameter("rest_sql_path", "TDengine SQL REST 路径", group="tdengine", default="/rest/sql")
            )
    elif asset_id == "jetty":
        capability["parameter_template"] = deepcopy(GENERIC_HTTP_API_PARAMETERS) + [
            _text_parameter("health_path", "健康检查路径", group="jetty", default="/"),
            _number_parameter("jmx_port", "JMX 端口", group="jetty", default=1099),
            _text_parameter(
                "jmx_service_url",
                "JMX Service URL",
                group="jetty",
                placeholder="service:jmx:rmi:///jndi/rmi://host:1099/jmxrmi",
            ),
        ]
    elif asset_id in {"api", "api_code", "website", "fullsite"}:
        capability["parameter_template"] = [
            _select_parameter(
                "method",
                "请求方法",
                group="http_probe",
                default="GET",
                options=[
                    ("GET", "GET"),
                    ("HEAD", "HEAD"),
                    ("POST", "POST"),
                    ("PUT", "PUT"),
                    ("DELETE", "DELETE"),
                ],
            ),
            _text_parameter("path", "探测路径", group="http_probe", default="/"),
            _text_parameter("expected_status", "期望状态码", group="http_probe", default="200-399"),
            _text_parameter("match_keyword", "响应关键字", group="http_probe"),
            _number_parameter("probe_timeout", "超时(秒)", group="http_probe", default=10),
        ]
        if asset_id == "fullsite":
            capability["parameter_template"].append(
                _text_parameter("sitemap_path", "Sitemap 路径", group="fullsite", default="/sitemap.xml")
            )
    elif asset_id in {"dns", "dns_sd"}:
        capability["parameter_template"] = [
            _select_parameter(
                "record_type",
                "记录类型",
                group="dns",
                default="A",
                options=[
                    ("A", "A"),
                    ("AAAA", "AAAA"),
                    ("CNAME", "CNAME"),
                    ("MX", "MX"),
                    ("TXT", "TXT"),
                    ("SRV", "SRV"),
                ],
            ),
            _text_parameter("query_name", "查询域名", group="dns"),
            _text_parameter("expected_answer", "期望解析结果", group="dns"),
            _number_parameter("probe_timeout", "超时(秒)", group="dns", default=5),
        ]
    elif asset_id == "ssl_cert":
        capability["parameter_template"] = [
            _text_parameter("server_name", "SNI/证书域名", group="ssl_cert"),
            _number_parameter("expiry_warning_days", "到期提醒天数", group="ssl_cert", default=30),
            _boolean_parameter("verify_chain", "校验证书链", group="ssl_cert", default=True),
        ]
    elif asset_id == "websocket":
        capability["parameter_template"] = [
            _text_parameter("path", "WebSocket 路径", group="websocket", default="/"),
            _text_parameter("subprotocol", "Subprotocol", group="websocket"),
            _text_parameter("ping_payload", "Ping 内容", group="websocket"),
            _number_parameter("probe_timeout", "超时(秒)", group="websocket", default=10),
        ]
    elif asset_id in {"port", "udp_port", "ping", "ntp"}:
        capability["parameter_template"] = [
            _number_parameter("probe_timeout", "超时(秒)", group="probe", default=5),
            _number_parameter("retry", "重试次数", group="probe", default=2),
        ]
        if asset_id == "ping":
            capability["parameter_template"].append(
                _number_parameter("packet_count", "ICMP 包数量", group="ping", default=4)
            )
        if asset_id == "ntp":
            capability["parameter_template"].append(
                _number_parameter("max_offset_ms", "最大时间偏差(ms)", group="ntp", default=1000)
            )
    elif asset_id in {"ftp", "smtp", "pop3", "netease_mailbox", "qq_mailbox"}:
        protocol_group = "imap" if asset_id in {"netease_mailbox", "qq_mailbox"} else asset_id
        capability["parameter_template"] = [
            _select_parameter(
                "tls_mode",
                "TLS 模式",
                group=protocol_group,
                default="auto",
                options=[
                    ("自动", "auto"),
                    ("明文", "plain"),
                    ("STARTTLS", "starttls"),
                    ("TLS/SSL", "ssl"),
                ],
            ),
            _number_parameter("probe_timeout", "超时(秒)", group=protocol_group, default=10),
        ]
        if asset_id == "smtp":
            capability["parameter_template"].append(
                _text_parameter("mail_from", "发件人", group="smtp")
            )
        if asset_id in {"pop3", "netease_mailbox", "qq_mailbox"}:
            capability["parameter_template"].append(
                _text_parameter("mailbox", "邮箱目录", group=protocol_group, default="INBOX")
            )
    elif asset_id == "mqtt":
        capability["parameter_template"] = [
            _text_parameter("client_id", "Client ID", group="mqtt", default="opscore-probe"),
            _text_parameter("topic", "Topic", group="mqtt", default="$SYS/#"),
            _select_parameter(
                "qos",
                "QoS",
                group="mqtt",
                default="0",
                options=[("0", "0"), ("1", "1"), ("2", "2")],
            ),
            _boolean_parameter("tls", "启用 TLS", group="mqtt", default=False),
        ]
    elif asset_id == "modbus":
        capability["parameter_template"] = [
            _number_parameter("unit_id", "Unit ID", group="modbus", default=1),
            _number_parameter("register_address", "寄存器地址", group="modbus", default=0),
            _select_parameter(
                "function_code",
                "功能码",
                group="modbus",
                default="3",
                options=[
                    ("读保持寄存器", "3"),
                    ("读输入寄存器", "4"),
                    ("读线圈", "1"),
                    ("读离散输入", "2"),
                ],
            ),
        ]
    elif asset_id == "s7":
        capability["parameter_template"] = [
            _number_parameter("rack", "Rack", group="s7", default=0),
            _number_parameter("slot", "Slot", group="s7", default=1),
            _text_parameter("area", "数据区", group="s7", default="DB"),
            _number_parameter("db_number", "DB 编号", group="s7", default=1),
        ]
    elif asset_id in {"registry", "zookeeper_sd"}:
        capability["parameter_template"] = [
            _text_parameter("namespace", "命名空间/根路径", group="registry"),
            _text_parameter("service_name", "服务名", group="registry"),
            _number_parameter("probe_timeout", "超时(秒)", group="registry", default=5),
        ]
    if asset_id in {"redfish", "harbor", "manageengine", "bastion", "audit", "f5", "a10", "waf"}:
        for param in capability["parameter_template"]:
            if param.get("field") == "scheme":
                param["defaultValue"] = "https"
