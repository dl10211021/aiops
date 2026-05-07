from __future__ import annotations

from typing import Any


TOOL_LABELS: dict[str, str] = {
    "ai_platform_api_request": "AI 平台接口",
    "bigdata_api_request": "大数据平台接口",
    "cicd_api_request": "CI/CD 平台接口",
    "container_api_request": "容器平台接口",
    "container_execute_command": "容器主机命令",
    "database_api_request": "数据库管理接口",
    "db_execute_query": "数据库 SQL 执行",
    "discovery_api_request": "服务发现接口",
    "dispatch_sub_agents": "多会话协同调度",
    "evolve_skill": "技能进化",
    "execute_on_scope": "批量范围执行",
    "http_api_request": "通用 HTTP/API",
    "k8s_api_request": "Kubernetes 集群 API",
    "linux_execute_command": "Linux/Unix 命令",
    "list_active_sessions": "活跃会话列表",
    "local_execute_script": "本地技能脚本",
    "memcached_execute_command": "Memcached 命令",
    "memory_delete": "删除会话记忆",
    "memory_edit": "修订会话记忆",
    "memory_list": "列出会话记忆",
    "memory_read": "读取会话记忆",
    "memory_write": "写入会话记忆",
    "middleware_api_request": "中间件管理接口",
    "middleware_execute_command": "中间件主机命令",
    "mongodb_find": "MongoDB 查询",
    "monitoring_api_query": "监控平台查询",
    "network_api_request": "网络设备接口",
    "network_cli_execute_command": "网络设备 CLI",
    "oob_api_request": "硬件带外接口",
    "redis_execute_command": "Redis 命令",
    "request_user_interaction": "用户交互确认",
    "search_assets_by_tag": "按标签搜索资产",
    "search_knowledge_base": "检索知识库",
    "security_api_request": "安全身份接口",
    "send_notification": "发送通知",
    "service_probe_request": "业务服务探测",
    "snmp_get": "SNMP 读取",
    "storage_api_request": "存储/备份接口",
    "storage_execute_command": "存储节点命令",
    "virtualization_api_request": "虚拟化平台接口",
    "web_search": "联网搜索",
    "winrm_execute_command": "Windows PowerShell 命令",
}

TOOLSET_LABELS: dict[str, str] = {
    "ai-platform-api": "AI 平台接口",
    "batch": "批量任务",
    "bigdata-api": "大数据平台接口",
    "cicd-api": "CI/CD 平台接口",
    "container-api": "容器平台接口",
    "container-runtime": "容器运行时工具",
    "database-api": "数据库平台接口",
    "discovery-api": "服务发现接口",
    "http-api": "通用 API 工具",
    "interaction": "交互确认",
    "knowledge": "知识库",
    "kubernetes": "Kubernetes 工具",
    "linux-ssh": "Linux 运维工具",
    "memcached": "Memcached 工具",
    "memory": "会话记忆工具",
    "middleware-api": "中间件管理接口",
    "middleware-ssh": "中间件主机工具",
    "mongodb": "MongoDB 工具",
    "monitoring": "监控平台工具",
    "network-api": "网络设备接口",
    "network-cli": "网络 CLI 工具",
    "oob-api": "硬件带外接口",
    "orchestration": "编排调度",
    "platform": "平台工具",
    "redis": "Redis 工具",
    "security-api": "安全身份接口",
    "service-probe": "服务探测工具",
    "skill-runtime": "技能运行时",
    "snmp": "SNMP 读取工具",
    "sql-db": "数据库 SQL 工具",
    "storage": "存储/备份工具",
    "storage-ssh": "存储节点工具",
    "virtualization": "虚拟化平台工具",
    "windows-winrm": "Windows 运维工具",
}


def tool_label(name: str) -> str:
    return TOOL_LABELS.get(name, name)


def toolset_label(name: str) -> str:
    return TOOLSET_LABELS.get(name, name)


def asset_tool_detail(name: str) -> dict[str, Any]:
    return {"name": name, "label": tool_label(name)}
