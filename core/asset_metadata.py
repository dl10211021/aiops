from __future__ import annotations

from copy import deepcopy
from typing import Any

ASSET_CATEGORY_DEFINITIONS: dict[str, dict[str, Any]] = {
    "os": {
        "label": "操作系统与主机",
        "group": "基础设施",
        "order": 10,
        "description": "Linux、Windows、Unix 等主机操作系统。",
    },
    "db": {
        "label": "数据库与缓存",
        "group": "数据服务",
        "order": 20,
        "description": "关系型数据库、缓存、文档数据库和兼容数据库。",
    },
    "container": {
        "label": "容器与云原生",
        "group": "基础设施",
        "order": 30,
        "description": "Kubernetes、Docker、容器运行时与云原生组件。",
    },
    "middleware": {
        "label": "中间件与消息",
        "group": "应用支撑",
        "order": 40,
        "description": "Web、中间件、消息队列、配置中心和协调服务。",
    },
    "bigdata": {
        "label": "大数据与分析",
        "group": "数据服务",
        "order": 45,
        "description": "大数据、分析计算、调度和数据平台组件。",
    },
    "network": {
        "label": "网络设备",
        "group": "基础设施",
        "order": 50,
        "description": "交换机、路由器、防火墙、负载均衡和 VPN。",
    },
    "storage": {
        "label": "存储与备份",
        "group": "基础设施",
        "order": 60,
        "description": "文件、块、对象存储、备份和归档平台。",
    },
    "virtualization": {
        "label": "虚拟化与私有云",
        "group": "基础设施",
        "order": 70,
        "description": "VMware、OpenStack、Proxmox、Hyper-V 等平台。",
    },
    "monitor": {
        "label": "监控与告警",
        "group": "平台工具",
        "order": 80,
        "description": "Prometheus、Grafana、Zabbix、日志和告警平台。",
    },
    "service": {
        "label": "应用与网络服务",
        "group": "平台工具",
        "order": 90,
        "description": "HTTP/API、DNS、证书、端口和业务可用性服务。",
    },
    "discovery": {
        "label": "服务发现",
        "group": "平台工具",
        "order": 95,
        "description": "Consul、Nacos、Kubernetes 等发现源。",
    },
    "oob": {
        "label": "硬件带外",
        "group": "基础设施",
        "order": 100,
        "description": "Redfish、iLO、iDRAC、IPMI 和硬件管理接口。",
    },
    "security": {
        "label": "安全与身份",
        "group": "平台工具",
        "order": 110,
        "description": "堡垒机、LDAP、审计和安全平台。",
    },
    "ai": {
        "label": "AI 与大模型",
        "group": "平台工具",
        "order": 120,
        "description": "大模型 API、推理服务和 AI 平台。",
    },
    "cicd": {
        "label": "CI/CD 与发布",
        "group": "平台工具",
        "order": 130,
        "description": "构建、发布和流水线平台。",
    },
    "custom": {
        "label": "自定义与扩展",
        "group": "其它",
        "order": 900,
        "description": "暂未归类或自定义接入对象。",
    },
    "other": {
        "label": "其它",
        "group": "其它",
        "order": 999,
        "description": "无法自动归类的资产。",
    },
}


CONNECTOR_GROUP_DEFINITIONS: dict[str, dict[str, Any]] = {
    "native_sql": {
        "label": "数据库 SQL",
        "group": "数据库",
        "order": 10,
        "tools": ["db_execute_query"],
        "description": "Oracle、MySQL、PostgreSQL、SQL Server 等 SQL 数据库。",
    },
    "native_kv": {
        "label": "键值数据库/缓存",
        "group": "数据库",
        "order": 20,
        "tools": ["redis_execute_command", "memcached_execute_command"],
        "description": "Redis、Valkey、Memcached 等键值数据库和缓存服务。",
    },
    "native_document": {
        "label": "文档数据库",
        "group": "数据库",
        "order": 30,
        "tools": ["mongodb_find"],
        "description": "MongoDB 等文档数据库。",
    },
    "database_http": {
        "label": "数据库管理接口",
        "group": "数据库",
        "order": 35,
        "tools": ["database_api_request"],
        "description": "ClickHouse、ElasticSearch 等当前通过数据库自身查询/管理接口接入，后续可升级为专用驱动。",
    },
    "database_driver": {
        "label": "数据库专用驱动",
        "group": "数据库",
        "order": 38,
        "tools": [],
        "description": "DB2、达梦、虚谷等需要补专用 Python/JDBC/ODBC 驱动适配的数据库。",
    },
    "database_jdbc": {
        "label": "数据库 JDBC",
        "group": "数据库",
        "order": 39,
        "tools": ["db_execute_query"],
        "description": "DB2、达梦、虚谷等通过 JayDeBeApi 和厂商 JDBC jar 接入的数据库。",
    },
    "container_shell": {
        "label": "容器主机 Shell",
        "group": "主机与命令行",
        "order": 39,
        "tools": ["container_execute_command"],
        "description": "Docker、containerd、Podman 等容器主机的命令行操作入口。",
    },
    "ssh_shell": {
        "label": "SSH Shell",
        "group": "主机与命令行",
        "order": 40,
        "tools": ["linux_execute_command"],
        "description": "Linux/Unix 主机、部分中间件和存储节点。",
    },
    "middleware_shell": {
        "label": "中间件主机 Shell",
        "group": "主机与命令行",
        "order": 42,
        "tools": ["middleware_execute_command"],
        "description": "Nginx、Tomcat、Kafka 等部署在主机上的中间件命令行入口。",
    },
    "storage_shell": {
        "label": "存储节点 Shell",
        "group": "主机与命令行",
        "order": 44,
        "tools": ["storage_execute_command"],
        "description": "Ceph、NFS、HDFS、GlusterFS 等存储节点命令行入口。",
    },
    "virtualization_shell": {
        "label": "虚拟化主机 Shell",
        "group": "主机与命令行",
        "order": 46,
        "tools": ["linux_execute_command"],
        "description": "KVM/Libvirt 等虚拟化宿主机命令行入口。",
    },
    "ai_compute_shell": {
        "label": "AI/GPU 主机 Shell",
        "group": "主机与命令行",
        "order": 48,
        "tools": ["linux_execute_command"],
        "description": "NVIDIA/GPU 等 AI 计算节点命令行入口。",
    },
    "ssh_network_cli": {
        "label": "网络设备 CLI",
        "group": "主机与命令行",
        "order": 50,
        "tools": ["network_cli_execute_command"],
        "description": "交换机、路由器、防火墙等交互式网络 CLI。",
    },
    "winrm_powershell": {
        "label": "Windows PowerShell",
        "group": "主机与命令行",
        "order": 60,
        "tools": ["winrm_execute_command"],
        "description": "Windows Server 与 Hyper-V WinRM。",
    },
    "http_api": {
        "label": "HTTP/API",
        "group": "平台 API",
        "order": 70,
        "tools": ["http_api_request"],
        "description": "通用 HTTP API、业务服务和平台 API。",
    },
    "custom_api": {
        "label": "自定义接口",
        "group": "平台 API",
        "order": 71,
        "tools": ["http_api_request"],
        "description": "自定义扩展、示例应用和暂未标准化的平台接口。",
    },
    "container_api": {
        "label": "容器平台接口",
        "group": "平台 API",
        "order": 72,
        "tools": ["container_api_request"],
        "description": "Harbor、容器平台控制面等 API 接入。",
    },
    "middleware_api": {
        "label": "中间件管理接口",
        "group": "平台 API",
        "order": 74,
        "tools": ["middleware_api_request"],
        "description": "RabbitMQ、Nacos、Consul、Spring Boot 等中间件管理或健康接口。",
    },
    "bigdata_api": {
        "label": "大数据平台接口",
        "group": "平台 API",
        "order": 76,
        "tools": ["bigdata_api_request"],
        "description": "Hadoop、Flink、Spark、Doris、StarRocks 等大数据平台接口。",
    },
    "monitoring_api": {
        "label": "监控平台接口",
        "group": "平台 API",
        "order": 78,
        "tools": ["monitoring_api_query"],
        "description": "Prometheus、Grafana、Zabbix、Loki、ManageEngine 等监控平台接口。",
    },
    "kubernetes_api": {
        "label": "Kubernetes API",
        "group": "平台 API",
        "order": 80,
        "tools": ["k8s_api_request"],
        "description": "Kubernetes API Server。",
    },
    "virtualization_api": {
        "label": "虚拟化平台接口",
        "group": "平台 API",
        "order": 82,
        "tools": ["virtualization_api_request"],
        "description": "VMware、OpenStack、Proxmox、ZStack 等虚拟化/私有云平台接口。",
    },
    "network_api": {
        "label": "网络设备接口",
        "group": "平台 API",
        "order": 84,
        "tools": ["network_api_request"],
        "description": "F5、A10、WAF 等网络设备管理接口。",
    },
    "storage_api": {
        "label": "存储管理接口",
        "group": "平台 API",
        "order": 86,
        "tools": ["storage_api_request"],
        "description": "备份系统、存储平台管理面等 HTTP/API 接口。",
    },
    "security_api": {
        "label": "安全身份接口",
        "group": "平台 API",
        "order": 88,
        "tools": ["security_api_request"],
        "description": "堡垒机、LDAP/AD、审计平台等安全与身份接口。",
    },
    "redfish_api": {
        "label": "Redfish/OOB API",
        "group": "平台 API",
        "order": 90,
        "tools": ["http_api_request"],
        "description": "硬件带外管理 API。",
    },
    "oob_api": {
        "label": "硬件/视频设备接口",
        "group": "平台 API",
        "order": 92,
        "tools": ["oob_api_request"],
        "description": "海康、大华、宇视等硬件或视频设备管理接口。",
    },
    "discovery_api": {
        "label": "服务发现接口",
        "group": "平台 API",
        "order": 94,
        "tools": ["discovery_api_request"],
        "description": "Consul、Nacos、Eureka、DNS/HTTP 服务发现接口。",
    },
    "service_probe": {
        "label": "业务探测接口",
        "group": "平台 API",
        "order": 96,
        "tools": ["service_probe_request"],
        "description": "HTTP、端口、证书、邮件、MQTT、Modbus 等业务可用性探测入口。",
    },
    "ai_platform_api": {
        "label": "AI 平台接口",
        "group": "平台 API",
        "order": 98,
        "tools": ["ai_platform_api_request"],
        "description": "OpenAI、Ollama、DeepSeek、LM Studio 等 AI 服务接口。",
    },
    "cicd_api": {
        "label": "CI/CD 平台接口",
        "group": "平台 API",
        "order": 99,
        "tools": ["cicd_api_request"],
        "description": "Jenkins 等构建发布平台接口。",
    },
    "snmp": {
        "label": "SNMP",
        "group": "网络与硬件",
        "order": 100,
        "tools": ["snmp_get"],
        "description": "SNMP 网络、存储和硬件设备。",
    },
    "object_storage_api": {
        "label": "对象存储 API",
        "group": "存储",
        "order": 110,
        "tools": ["storage_api_request"],
        "description": "S3/MinIO/OSS/COS/OBS 等对象存储 API。",
    },
    "unknown": {
        "label": "待适配",
        "group": "其它",
        "order": 999,
        "tools": [],
        "description": "需要补专用连接器或协议适配。",
    },
}


def category_metadata(category: str | None) -> dict[str, Any]:
    key = str(category or "other").strip().lower() or "other"
    metadata = deepcopy(ASSET_CATEGORY_DEFINITIONS.get(key, ASSET_CATEGORY_DEFINITIONS["other"]))
    metadata["id"] = key
    return metadata


def connector_metadata(connector: str | None) -> dict[str, Any]:
    key = str(connector or "unknown").strip().lower() or "unknown"
    metadata = deepcopy(CONNECTOR_GROUP_DEFINITIONS.get(key, CONNECTOR_GROUP_DEFINITIONS["unknown"]))
    metadata["id"] = key
    return metadata
