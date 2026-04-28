"""Central tool registry for protocol-aware AIOps sessions.

This is intentionally metadata-only: execution still lives in dispatcher.py.
Keeping schema selection here gives the model, API, and frontend the same
source of truth for which tools are available in a session.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.asset_protocols import (
    API_PROTOCOLS,
    CONTAINER_ASSET_TYPES,
    MIDDLEWARE_ASSET_TYPES,
    MONITORING_ASSET_TYPES,
    NETWORK_CLI_ASSET_TYPES,
    SQL_PROTOCOLS,
    STORAGE_ASSET_TYPES,
    VIRTUALIZATION_ASSET_TYPES,
    resolve_asset_identity,
)


JsonSchema = dict[str, Any]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    toolset: str
    scope: str
    description: str
    parameters: JsonSchema
    safety_category: str = "general"
    protocols: set[str] = field(default_factory=set)
    asset_types: set[str] = field(default_factory=set)
    excluded_asset_types: set[str] = field(default_factory=set)
    requires_virtual: bool = False

    def matches(self, context: dict[str, Any]) -> bool:
        target_scope = str(context.get("target_scope") or "asset")
        scope_matches = self.scope == target_scope or (self.scope == "group" and target_scope == "tag")
        if self.scope != "base" and not scope_matches:
            return False

        if self.scope == "base":
            if self.requires_virtual:
                identity = _identity(context)
                return identity["protocol"] == "virtual"
            return True

        if self.scope != "asset":
            return True

        identity = _identity(context)
        protocol = identity["protocol"]
        asset_type = identity["asset_type"]
        if self.protocols and protocol not in self.protocols:
            return False
        if self.asset_types and asset_type not in self.asset_types:
            return False
        if self.excluded_asset_types and asset_type in self.excluded_asset_types:
            return False
        return True

    def openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def public_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "toolset": self.toolset,
            "scope": self.scope,
            "description": self.description,
            "safety_category": self.safety_category,
            "protocols": sorted(self.protocols),
            "asset_types": sorted(self.asset_types),
            "requires_virtual": self.requires_virtual,
        }


def _obj(properties: dict[str, Any] | None = None, required: list[str] | None = None) -> JsonSchema:
    return {
        "type": "object",
        "properties": properties or {},
        "required": required or [],
    }


def _identity(context: dict[str, Any]) -> dict[str, Any]:
    return resolve_asset_identity(
        context.get("asset_type"),
        context.get("protocol"),
        context.get("extra_args") or {},
        context.get("host"),
        context.get("port"),
        context.get("remark"),
    )


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        existing = self._tools.get(tool.name)
        if existing and existing.toolset != tool.toolset:
            raise ValueError(f"tool name collision: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def all_tools(self) -> list[ToolDefinition]:
        return [self._tools[name] for name in sorted(self._tools)]

    def available(self, context: dict[str, Any]) -> list[ToolDefinition]:
        return [tool for tool in self.all_tools() if tool.matches(context)]

    def get_openai_tools(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        return [tool.openai_tool() for tool in self.available(context)]

    def catalog(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        active_names = {tool.name for tool in self.available(context or {})} if context is not None else set()
        toolsets: dict[str, dict[str, Any]] = {}
        for tool in self.all_tools():
            bucket = toolsets.setdefault(
                tool.toolset,
                {
                    "id": tool.toolset,
                    "tools": [],
                    "enabled": False,
                },
            )
            item = tool.public_dict()
            item["enabled"] = tool.name in active_names if context is not None else True
            bucket["tools"].append(item)
            bucket["enabled"] = bucket["enabled"] or item["enabled"]
        return {"toolsets": list(toolsets.values())}

    def prompt_lines(self, context: dict[str, Any]) -> str:
        lines = []
        for tool in self.available(context):
            if tool.name in {"send_notification", "search_knowledge_base", "web_search"}:
                continue
            lines.append(f"- {tool.name}: {tool.description}")
        return "\n".join(lines)


tool_registry = ToolRegistry()


def _register_builtin_tools() -> None:
    tool_registry.register(
        ToolDefinition(
            name="local_execute_script",
            toolset="skill-runtime",
            scope="base",
            safety_category="local",
            requires_virtual=True,
            description="仅用于 VIRTUAL 技能研发会话执行已挂载 Skill 目录内的脚本；真实资产会话禁止使用。",
            parameters=_obj(
                {
                    "command": {"type": "string", "description": "要运行的本地命令"},
                    "cwd": {"type": "string", "description": "工作目录，必须位于已挂载 Skill 目录内"},
                },
                ["command"],
            ),
        )
    )
    tool_registry.register(
        ToolDefinition(
            name="send_notification",
            toolset="platform",
            scope="base",
            description="完成重要排查、分析或高危修改后，向团队发送结果汇报。",
            parameters=_obj(
                {
                    "channel": {"type": "string", "enum": ["auto", "wechat", "dingtalk", "email"]},
                    "title": {"type": "string"},
                    "content": {"type": "string", "description": "Markdown 格式汇报内容"},
                },
                ["channel", "title", "content"],
            ),
        )
    )
    tool_registry.register(
        ToolDefinition(
            name="request_user_interaction",
            toolset="interaction",
            scope="base",
            description=(
                "向当前前台会话发起交互式输入或选择请求。用于必须由用户补充密码、文本、"
                "业务偏好或从多个方案中选择时；不要用普通文本等待用户回复。"
            ),
            parameters=_obj(
                {
                    "prompt": {"type": "string", "description": "展示给用户的问题或说明"},
                    "input_type": {
                        "type": "string",
                        "enum": ["text", "password", "choice"],
                        "description": "text 为普通输入，password 为敏感输入，choice 为选项选择",
                    },
                    "options": {
                        "type": "array",
                        "description": "input_type=choice 时使用的候选项",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string"},
                                "value": {"type": "string"},
                                "description": {"type": "string"},
                            },
                        },
                    },
                    "placeholder": {"type": "string"},
                    "timeout_seconds": {"type": "integer"},
                    "required": {"type": "boolean"},
                },
                ["prompt"],
            ),
        )
    )
    tool_registry.register(
        ToolDefinition(
            name="evolve_skill",
            toolset="skill-runtime",
            scope="base",
            safety_category="skill_change",
            description="创建或更新 my_custom_skills 下的技能文件。仅用于用户明确要求修改技能时。",
            parameters=_obj(
                {
                    "skill_id": {"type": "string"},
                    "file_name": {"type": "string"},
                    "content": {"type": "string"},
                },
                ["skill_id", "file_name", "content"],
            ),
        )
    )
    tool_registry.register(
        ToolDefinition(
            name="search_knowledge_base",
            toolset="knowledge",
            scope="base",
            description="检索企业运维知识库，用于 SOP、报错、资产说明和内部文档查询。",
            parameters=_obj({"query": {"type": "string"}}, ["query"]),
        )
    )
    tool_registry.register(
        ToolDefinition(
            name="web_search",
            toolset="knowledge",
            scope="base",
            description="本地知识库没有答案时，联网搜索实时资料、官方文档或社区方案。",
            parameters=_obj({"query": {"type": "string"}}, ["query"]),
        )
    )
    tool_registry.register(
        ToolDefinition(
            name="network_cli_execute_command",
            toolset="network-cli",
            scope="asset",
            protocols={"ssh"},
            asset_types={"switch"},
            safety_category="network_cli",
            description="当前已连接交换机/路由器 SSH CLI；直接执行 display/show/ping 等巡检命令，凭据由资产中心注入。",
            parameters=_obj({"command": {"type": "string"}}, ["command"]),
        )
    )
    tool_registry.register(
        ToolDefinition(
            name="linux_execute_command",
            toolset="linux-ssh",
            scope="asset",
            protocols={"ssh"},
            excluded_asset_types=set(NETWORK_CLI_ASSET_TYPES),
            safety_category="linux",
            description="当前已连接 Linux/Unix/KVM SSH 会话；直接在目标资产执行 CLI/巡检命令，凭据由资产中心注入。",
            parameters=_obj({"command": {"type": "string"}}, ["command"]),
        )
    )
    tool_registry.register(
        ToolDefinition(
            name="winrm_execute_command",
            toolset="windows-winrm",
            scope="asset",
            protocols={"winrm"},
            safety_category="windows",
            description="当前已连接 Windows WinRM 会话；直接执行 PowerShell/CMD 巡检命令，凭据由资产中心注入。",
            parameters=_obj({"command": {"type": "string", "description": "PowerShell/CMD 命令"}}, ["command"]),
        )
    )
    tool_registry.register(
        ToolDefinition(
            name="container_execute_command",
            toolset="container-runtime",
            scope="asset",
            protocols={"ssh"},
            asset_types=set(CONTAINER_ASSET_TYPES),
            safety_category="linux",
            description="当前已连接 Docker/containerd/Podman 宿主机；执行 docker/ctr/crictl/podman 等容器巡检命令，凭据由资产中心注入。",
            parameters=_obj({"command": {"type": "string"}}, ["command"]),
        )
    )
    tool_registry.register(
        ToolDefinition(
            name="middleware_execute_command",
            toolset="middleware-ssh",
            scope="asset",
            protocols={"ssh"},
            asset_types={item for item in MIDDLEWARE_ASSET_TYPES if item not in {"rabbitmq", "nacos", "consul", "minio"}},
            safety_category="linux",
            description="当前已连接中间件宿主机；执行 Nginx/Tomcat/Kafka/RocketMQ/ZooKeeper 等只读巡检命令。",
            parameters=_obj({"command": {"type": "string"}}, ["command"]),
        )
    )
    tool_registry.register(
        ToolDefinition(
            name="storage_execute_command",
            toolset="storage-ssh",
            scope="asset",
            protocols={"ssh"},
            asset_types={item for item in STORAGE_ASSET_TYPES if item in {"ceph", "nfs"}},
            safety_category="linux",
            description="当前已连接存储节点；执行 Ceph/NFS/备份节点等只读巡检命令。",
            parameters=_obj({"command": {"type": "string"}}, ["command"]),
        )
    )
    tool_registry.register(
        ToolDefinition(
            name="db_execute_query",
            toolset="sql-db",
            scope="asset",
            protocols=set(SQL_PROTOCOLS),
            safety_category="sql",
            description="当前已连接数据库资产；直接执行 SQL 巡检语句，不要传 host/user/password。",
            parameters=_obj(
                {
                    "db_type": {"type": "string", "enum": sorted(SQL_PROTOCOLS)},
                    "sql": {"type": "string", "description": "要执行的 SQL 查询语句"},
                },
                ["sql"],
            ),
        )
    )
    tool_registry.register(
        ToolDefinition(
            name="redis_execute_command",
            toolset="redis",
            scope="asset",
            protocols={"redis"},
            safety_category="redis",
            description="当前已连接 Redis 资产；通过托管凭据执行 Redis 命令。",
            parameters=_obj({"command": {"type": "string"}}, ["command"]),
        )
    )
    tool_registry.register(
        ToolDefinition(
            name="mongodb_find",
            toolset="mongodb",
            scope="asset",
            protocols={"mongodb"},
            safety_category="mongodb",
            description="当前已连接 MongoDB 资产；执行只读 find 查询，凭据由资产中心注入。",
            parameters=_obj(
                {
                    "database": {"type": "string"},
                    "collection": {"type": "string"},
                    "filter": {"type": "object"},
                    "projection": {"type": "object"},
                    "limit": {"type": "integer"},
                },
                ["collection"],
            ),
        )
    )
    tool_registry.register(
        ToolDefinition(
            name="http_api_request",
            toolset="http-api",
            scope="asset",
            protocols=set(API_PROTOCOLS),
            safety_category="http_api",
            description="当前已连接 API/监控/虚拟化/K8s/Redfish 资产；使用托管凭据访问目标 HTTP API。",
            parameters=_obj(
                {
                    "method": {"type": "string", "enum": ["GET", "HEAD", "POST"]},
                    "path": {"type": "string", "description": "API 路径，例如 /api/v1/query?query=up"},
                    "headers": {"type": "object"},
                    "body": {"type": "object"},
                },
                ["path"],
            ),
        )
    )
    tool_registry.register(
        ToolDefinition(
            name="k8s_api_request",
            toolset="kubernetes",
            scope="asset",
            protocols={"k8s"},
            asset_types={"k8s"},
            safety_category="http_api",
            description="当前已连接 Kubernetes API；使用托管 kubeconfig/bearer token 调用 K8s 只读 API。",
            parameters=_obj(
                {
                    "path": {"type": "string", "description": "Kubernetes API 路径，例如 /api/v1/nodes 或 /api/v1/pods"},
                    "method": {"type": "string", "enum": ["GET", "HEAD", "POST"]},
                    "headers": {"type": "object"},
                    "body": {"type": "object"},
                },
                ["path"],
            ),
        )
    )
    tool_registry.register(
        ToolDefinition(
            name="monitoring_api_query",
            toolset="monitoring",
            scope="asset",
            protocols={"http_api"},
            asset_types=set(MONITORING_ASSET_TYPES),
            safety_category="http_api",
            description="当前已连接监控平台；查询 Prometheus/Alertmanager/Grafana/Loki/Zabbix/ManageEngine 等只读 API。",
            parameters=_obj(
                {
                    "path": {"type": "string", "description": "监控 API 路径，例如 /api/v1/query?query=up"},
                    "method": {"type": "string", "enum": ["GET", "HEAD", "POST"]},
                    "headers": {"type": "object"},
                    "body": {"type": "object"},
                },
                ["path"],
            ),
        )
    )
    tool_registry.register(
        ToolDefinition(
            name="virtualization_api_request",
            toolset="virtualization",
            scope="asset",
            protocols={"http_api", "winrm"},
            asset_types=set(VIRTUALIZATION_ASSET_TYPES) - {"kvm"},
            safety_category="http_api",
            description="当前已连接虚拟化/云平台；访问 VMware/ZStack/OpenStack/Proxmox/Hyper-V 等平台 API 或 WinRM。",
            parameters=_obj(
                {
                    "path": {"type": "string"},
                    "method": {"type": "string", "enum": ["GET", "HEAD", "POST"]},
                    "headers": {"type": "object"},
                    "body": {"type": "object"},
                    "command": {"type": "string", "description": "Hyper-V WinRM 命令，仅 WinRM 协议使用"},
                },
                [],
            ),
        )
    )
    tool_registry.register(
        ToolDefinition(
            name="storage_api_request",
            toolset="storage",
            scope="asset",
            protocols={"http_api", "snmp"},
            asset_types=set(STORAGE_ASSET_TYPES) - {"ceph", "nfs"},
            safety_category="http_api",
            description="当前已连接 NAS/SAN/备份系统；使用 HTTP API 或 SNMP 做只读巡检。",
            parameters=_obj(
                {
                    "path": {"type": "string"},
                    "oid": {"type": "string"},
                    "method": {"type": "string", "enum": ["GET", "HEAD", "POST"]},
                    "headers": {"type": "object"},
                    "body": {"type": "object"},
                },
                [],
            ),
        )
    )
    tool_registry.register(
        ToolDefinition(
            name="snmp_get",
            toolset="snmp",
            scope="asset",
            protocols={"snmp"},
            safety_category="snmp",
            description="当前已连接 SNMP 资产；读取单个 OID，Community/SNMPv3 凭据由资产中心注入。",
            parameters=_obj({"oid": {"type": "string"}}, ["oid"]),
        )
    )
    tool_registry.register(
        ToolDefinition(
            name="execute_on_scope",
            toolset="batch",
            scope="group",
            safety_category="batch",
            description="在当前标签/组内的目标 SSH 资产上并发执行同一条巡检命令，并聚合同类输出。",
            parameters=_obj(
                {
                    "scope_target": {"type": "string", "description": "ALL 或逗号分隔目标"},
                    "command": {"type": "string"},
                },
                ["scope_target", "command"],
            ),
        )
    )
    tool_registry.register(
        ToolDefinition(
            name="list_active_sessions",
            toolset="orchestration",
            scope="global",
            description="列出平台已连接的活跃资产会话。",
            parameters=_obj(),
        )
    )
    tool_registry.register(
        ToolDefinition(
            name="dispatch_sub_agents",
            toolset="orchestration",
            scope="global",
            safety_category="batch",
            description="向多个会话并发下发自然语言调查任务。",
            parameters=_obj(
                {
                    "tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "target_session_id": {"type": "string"},
                                "task_description": {"type": "string"},
                            },
                            "required": ["target_session_id", "task_description"],
                        },
                    }
                },
                ["tasks"],
            ),
        )
    )
    tool_registry.register(
        ToolDefinition(
            name="search_assets_by_tag",
            toolset="orchestration",
            scope="global",
            description="根据标签搜索资产通讯录，只返回非敏感资产元数据。",
            parameters=_obj({"tags": {"type": "array", "items": {"type": "string"}}}, ["tags"]),
        )
    )


_register_builtin_tools()
