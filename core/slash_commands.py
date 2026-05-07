"""Backend-driven slash command catalog for AIOps sessions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.tool_display import tool_label


@dataclass(frozen=True)
class SlashCommand:
    id: str
    label: str
    description: str
    prompt_template: str
    category: str = "通用"
    scope_type: str = "global"
    asset_types: tuple[str, ...] = ()
    protocols: tuple[str, ...] = ()
    readonly: bool = True
    pinned: bool = False
    sort_order: int = 100
    source: str = "builtin"

    def matches(self, context: dict[str, Any]) -> bool:
        asset_type = str(context.get("asset_type") or "").lower()
        protocol = str(context.get("protocol") or "").lower()
        if self.scope_type == "global":
            return True
        asset_match = not self.asset_types or asset_type in self.asset_types
        protocol_match = not self.protocols or protocol in self.protocols
        if self.scope_type == "asset_type":
            return bool(self.asset_types and asset_match and protocol_match)
        if self.scope_type == "protocol":
            return bool(self.protocols and protocol_match)
        return False

    def render(self, context: dict[str, Any], active_tools: list[str] | None = None) -> dict[str, Any]:
        target = "{asset_type}/{protocol} {host}".format(
            asset_type=context.get("asset_type") or "asset",
            protocol=context.get("protocol") or "protocol",
            host=context.get("host") or "",
        ).strip()
        variables = {
            "target": target,
            "tool_list": _tool_list_text(active_tools),
            "host": context.get("host") or "",
            "port": context.get("port") or "",
            "asset_type": context.get("asset_type") or "",
            "protocol": context.get("protocol") or "",
            "remark": context.get("remark") or "",
            "username": context.get("username") or "",
        }
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "category": self.category,
            "scope_type": self.scope_type,
            "asset_type": self.asset_types[0] if self.asset_types else "",
            "protocol": self.protocols[0] if self.protocols else "",
            "asset_types": list(self.asset_types),
            "protocols": list(self.protocols),
            "readonly": self.readonly,
            "pinned": self.pinned,
            "enabled": True,
            "sort_order": self.sort_order,
            "source": self.source,
            "is_override": False,
            "builtin_id": self.id,
            "prompt": safe_format(self.prompt_template, variables),
            "prompt_template": self.prompt_template,
        }


def safe_format(template: str, variables: dict[str, Any]) -> str:
    rendered = str(template or "")
    for key, value in variables.items():
        rendered = rendered.replace("{" + key + "}", str(value))
    return rendered


def _tool_list_text(active_tools: list[str] | None) -> str:
    labels = [tool_label(str(tool_name)) for tool_name in active_tools or []]
    return "、".join(labels) or "当前会话原生协议工具"


DATABASE_COMMAND_ASSET_TYPES = (
    "oracle",
    "mysql",
    "mariadb",
    "tidb",
    "oceanbase",
    "postgresql",
    "postgres",
    "opengauss",
    "kingbase",
    "vastbase",
    "mssql",
    "sqlserver",
    "dameng",
    "dm",
)

DATABASE_COMMAND_PROTOCOLS = (
    "oracle",
    "mysql",
    "postgresql",
    "mssql",
    "dameng",
    "sql",
    "jdbc",
)


COMMANDS = [
    SlashCommand(
        "inspect",
        "/inspect 只读巡检",
        "按当前协议执行完整只读巡检",
        "请对当前资产 {target} 执行一次完整只读巡检。必须使用当前会话的原生协议工具，不要使用本地脚本。输出包括：关键健康状态、异常项、风险等级、建议下一步。",
        pinned=True,
        sort_order=1,
    ),
    SlashCommand(
        "status",
        "/status 当前状态",
        "快速确认在线状态、核心指标和告警线索",
        "请快速检查当前资产 {target} 的运行状态。优先返回在线性、核心服务/实例状态、资源使用率、近期错误或告警线索。",
        pinned=True,
        sort_order=2,
    ),
    SlashCommand(
        "config",
        "/config 当前配置",
        "查看实例关键配置和运行参数",
        "请查看当前资产 {target} 的关键配置信息。必须使用当前会话的原生协议工具，不要重新登录或要求我提供账号密码。请按“基础信息、资源/版本、网络/监听、关键配置、异常项”输出。",
        sort_order=3,
    ),
    SlashCommand(
        "risk",
        "/risk 风险排查",
        "只读模式下做安全和稳定性风险扫描",
        "请在只读模式下对当前资产 {target} 做风险排查。禁止修改配置、重启服务、删除文件或写入数据。请输出高风险、中风险、低风险和需要人工确认的事项。",
        sort_order=4,
    ),
    SlashCommand(
        "tools",
        "/tools 可用工具",
        "解释当前会话启用的工具和安全边界",
        "请说明当前资产 {target} 已启用的工具和正确使用边界。当前工具包括：{tool_list}。请特别说明哪些操作只读可执行，哪些需要审批或会被硬拦截。",
        sort_order=5,
    ),
    SlashCommand(
        "database-inspect",
        "/db-inspect 数据库巡检",
        "按当前数据库类型执行完整只读巡检",
        "请对当前数据库 {target} 做一次完整只读巡检。使用当前会话数据库工具，不要本地脚本，不要写入。先识别数据库类型和版本，再按该类型选择只读 SQL：连接/会话、容量、锁等待、慢 SQL/高耗 SQL、错误/告警、复制/集群、关键配置。输出：健康结论、证据 SQL 摘要、风险等级、P0/P1/P2 建议。",
        category="数据库巡检",
        scope_type="asset_type",
        asset_types=DATABASE_COMMAND_ASSET_TYPES,
        protocols=DATABASE_COMMAND_PROTOCOLS,
        pinned=True,
        sort_order=30,
    ),
    SlashCommand(
        "database-slow-sql",
        "/db-slow 慢SQL分析",
        "按数据库类型查找慢 SQL、高耗 SQL、等待和锁线索",
        "请对当前数据库 {target} 做只读慢 SQL 和高耗 SQL 分析。先判断数据库类型，再使用对应系统视图或性能视图查询。不要执行写入、kill、flush 或参数变更。输出：Top SQL、耗时/等待/锁、影响范围、证据 SQL 摘要、优化建议。",
        category="数据库巡检",
        scope_type="asset_type",
        asset_types=DATABASE_COMMAND_ASSET_TYPES,
        protocols=DATABASE_COMMAND_PROTOCOLS,
        sort_order=34,
    ),
    SlashCommand(
        "database-baseline",
        "/db-baseline 配置基线",
        "检查数据库关键参数、账号、安全和高风险配置",
        "请对当前数据库 {target} 做只读配置基线检查。先识别数据库类型，再检查版本、关键参数、账号状态、权限风险、审计/日志、备份线索和高危默认配置。不要修改任何参数或账号。输出：异常项、风险等级、证据 SQL 摘要和整改建议。",
        category="数据库巡检",
        scope_type="asset_type",
        asset_types=DATABASE_COMMAND_ASSET_TYPES,
        protocols=DATABASE_COMMAND_PROTOCOLS,
        sort_order=35,
    ),
    SlashCommand(
        "database-index",
        "/db-index 索引健康",
        "分析索引、表空间/膨胀、热点对象和容量风险",
        "请对当前数据库 {target} 做只读索引和对象健康分析。先识别数据库类型，再检查大表、索引失效/未使用、表空间或数据文件水位、膨胀/碎片、热点对象和容量风险。不要 rebuild、analyze、vacuum 或执行任何写入。输出：对象清单、风险等级、证据 SQL 摘要和建议动作。",
        category="数据库巡检",
        scope_type="asset_type",
        asset_types=DATABASE_COMMAND_ASSET_TYPES,
        protocols=DATABASE_COMMAND_PROTOCOLS,
        sort_order=36,
    ),
    SlashCommand(
        "linux-services",
        "/services 服务状态",
        "查看 Linux 失败服务、关键服务和最近错误",
        "请使用当前 Linux/SSH 会话只读检查 {target} 的服务状态：失败服务、关键服务运行状态、最近 systemd 错误。不要重启或修改服务。",
        category="操作系统",
        scope_type="asset_type",
        asset_types=("linux", "ubuntu", "debian", "redhat", "centos", "rocky", "alma", "suse"),
        protocols=("ssh",),
        pinned=True,
        sort_order=11,
    ),
    SlashCommand(
        "linux-security-log",
        "/logs 安全日志",
        "读取登录失败、sudo、SSH、安全错误线索",
        "请只读检查 {target} 的安全日志和认证日志，重点关注 SSH 登录失败、sudo 失败、异常用户、近期高频错误。不要清理日志或修改配置。",
        category="操作系统",
        scope_type="asset_type",
        asset_types=("linux", "ubuntu", "debian", "redhat", "centos", "rocky", "alma", "suse"),
        protocols=("ssh",),
        sort_order=12,
    ),
    SlashCommand(
        "linux-mounts",
        "/mounts 挂载检查",
        "检查磁盘、fstab、挂载选项和 noexec 风险",
        "请只读检查 {target} 的磁盘、文件系统、fstab、当前挂载选项和 /tmp、/dev/shm 等安全挂载情况。不要执行 mount/umount 或写入磁盘。",
        category="操作系统",
        scope_type="asset_type",
        asset_types=("linux", "ubuntu", "debian", "redhat", "centos", "rocky", "alma", "suse"),
        protocols=("ssh",),
        sort_order=13,
    ),
    SlashCommand(
        "linux-network",
        "/network 网络监听",
        "检查端口监听、连接、路由和防火墙摘要",
        "请只读检查 {target} 的端口监听、网络连接、路由、防火墙状态摘要和异常外联线索。不要发起端口扫描或修改网络配置。",
        category="操作系统",
        scope_type="asset_type",
        asset_types=("linux", "ubuntu", "debian", "redhat", "centos", "rocky", "alma", "suse"),
        protocols=("ssh",),
        sort_order=14,
    ),
    SlashCommand(
        "windows-eventlog",
        "/eventlog 事件日志",
        "读取 Windows 系统、应用和安全事件摘要",
        "请使用当前 WinRM 会话只读检查 {target} 的系统、应用、安全事件日志摘要，重点关注最近错误、登录失败、服务异常和重启原因。",
        category="操作系统",
        scope_type="asset_type",
        asset_types=("windows", "windows_server"),
        protocols=("winrm",),
        pinned=True,
        sort_order=21,
    ),
    SlashCommand(
        "windows-services",
        "/win-services 服务状态",
        "检查 Windows 自动服务、失败服务和关键服务",
        "请只读检查 {target} 的 Windows 服务状态，列出自动启动但未运行、最近失败和关键业务服务状态。不要启动、停止或修改服务。",
        category="操作系统",
        scope_type="asset_type",
        asset_types=("windows", "windows_server"),
        protocols=("winrm",),
        sort_order=22,
    ),
    SlashCommand(
        "oracle-health",
        "/oracle-health 实例健康",
        "检查 Oracle 实例、监听、会话和等待事件",
        "请使用当前 Oracle 会话只读检查 {target}：实例状态、数据库版本、监听/服务名线索、会话数、等待事件、告警日志线索。不要执行 DDL/DML。",
        category="数据库巡检",
        scope_type="asset_type",
        asset_types=("oracle",),
        protocols=("oracle", "sql"),
        pinned=True,
        sort_order=31,
    ),
    SlashCommand(
        "oracle-tablespace",
        "/tablespace 表空间",
        "检查表空间水位、数据文件和自动扩展",
        "请只读检查 {target} 的表空间使用率、数据文件、自动扩展、临时表空间和即将满的风险，按紧急程度输出。",
        category="数据库巡检",
        scope_type="asset_type",
        asset_types=("oracle",),
        protocols=("oracle", "sql"),
        sort_order=32,
    ),
    SlashCommand(
        "oracle-locks",
        "/locks 锁等待",
        "检查阻塞、锁等待和长事务",
        "请只读检查 {target} 的阻塞会话、锁等待、长事务、活跃 SQL 和影响范围。不要 kill session，不要修改系统参数。",
        category="数据库巡检",
        scope_type="asset_type",
        asset_types=("oracle",),
        protocols=("oracle", "sql"),
        sort_order=33,
    ),
    SlashCommand(
        "mysql-health",
        "/mysql-health 实例健康",
        "检查 MySQL 版本、连接、慢 SQL 和复制状态",
        "请使用当前 MySQL 会话只读检查 {target}：版本、运行时长、连接数、慢查询、错误计数、复制状态和容量风险。不要执行写入 SQL。",
        category="数据库巡检",
        scope_type="asset_type",
        asset_types=("mysql", "mariadb"),
        protocols=("mysql", "sql"),
        pinned=True,
        sort_order=41,
    ),
    SlashCommand(
        "mysql-process",
        "/processlist 会话列表",
        "查看 MySQL 活跃连接、锁等待和长查询",
        "请只读检查 {target} 的 processlist、长查询、锁等待和异常来源 IP，输出可能影响业务的 SQL 线索。",
        category="数据库巡检",
        scope_type="asset_type",
        asset_types=("mysql", "mariadb"),
        protocols=("mysql", "sql"),
        sort_order=42,
    ),
    SlashCommand(
        "postgres-health",
        "/pg-health 实例健康",
        "检查 PostgreSQL 连接、复制、锁等待和膨胀风险",
        "请使用当前 PostgreSQL 会话只读检查 {target}：版本、连接数、复制状态、锁等待、长事务、膨胀风险、慢查询线索和容量风险。不要执行写入 SQL。",
        category="数据库巡检",
        scope_type="asset_type",
        asset_types=("postgresql", "postgres", "opengauss", "kingbase", "vastbase"),
        protocols=("postgresql", "sql"),
        pinned=True,
        sort_order=43,
    ),
    SlashCommand(
        "mssql-health",
        "/mssql-health 实例健康",
        "检查 SQL Server 作业、等待、阻塞和数据库状态",
        "请使用当前 SQL Server 会话只读检查 {target}：实例版本、数据库状态、阻塞、等待类型、作业失败、错误日志线索和容量风险。不要执行写入 SQL。",
        category="数据库巡检",
        scope_type="asset_type",
        asset_types=("mssql", "sqlserver"),
        protocols=("mssql", "sql"),
        pinned=True,
        sort_order=44,
    ),
    SlashCommand(
        "mongodb-health",
        "/mongo-health 实例健康",
        "检查 MongoDB 副本集、连接、慢操作和存储水位",
        "请只读检查 {target} 的 MongoDB 状态：版本、副本集/分片状态、连接数、慢操作、锁/队列、存储空间和高风险配置。",
        category="数据库巡检",
        scope_type="asset_type",
        asset_types=("mongodb", "mongo"),
        protocols=("mongodb",),
        pinned=True,
        sort_order=45,
    ),
    SlashCommand(
        "elastic-health",
        "/es-health 集群健康",
        "检查 Elasticsearch 集群、索引、分片和磁盘水位",
        "请只读检查 {target} 的 Elasticsearch 健康：cluster health、节点状态、索引异常、未分配分片、磁盘水位、慢查询和安全配置风险。",
        category="数据库巡检",
        scope_type="asset_type",
        asset_types=("elasticsearch", "elastic", "opensearch"),
        protocols=("http_api",),
        pinned=True,
        sort_order=46,
    ),
    SlashCommand(
        "redis-health",
        "/redis-health Redis 健康",
        "检查 Redis 内存、持久化、连接和慢日志",
        "请只读检查 {target} 的 Redis info、内存水位、客户端连接、持久化状态、复制状态、慢日志摘要和高风险配置。",
        category="数据库巡检",
        scope_type="asset_type",
        asset_types=("redis",),
        protocols=("redis",),
        pinned=True,
        sort_order=51,
    ),
    SlashCommand(
        "middleware-health",
        "/middleware 中间件健康",
        "检查中间件进程、端口、日志、队列或集群状态",
        "请只读检查 {target} 的中间件健康状态：进程/服务、监听端口、版本、集群/队列状态、近期错误日志、资源水位和业务影响。",
        category="中间件",
        scope_type="asset_type",
        asset_types=("nginx", "tomcat", "kafka", "rabbitmq", "rocketmq", "zookeeper", "nacos", "consul", "harbor"),
        protocols=("ssh", "http_api"),
        pinned=True,
        sort_order=56,
    ),
    SlashCommand(
        "k8s-workloads",
        "/workloads 工作负载",
        "检查 K8s 节点、Pod、事件和异常工作负载",
        "请只读检查 {target} 的 Kubernetes 节点、Pod、Deployment/StatefulSet、近期事件、重启次数和 Pending/CrashLoop 风险。",
        category="容器平台",
        scope_type="asset_type",
        asset_types=("kubernetes", "k8s", "openshift"),
        protocols=("kubernetes", "k8s"),
        pinned=True,
        sort_order=61,
    ),
    SlashCommand(
        "vmware-health",
        "/vmware-health 虚拟化健康",
        "检查虚拟化平台主机、集群、存储和虚机风险",
        "请只读检查 {target} 的虚拟化平台健康：主机状态、集群资源、Datastore 水位、异常虚机、快照风险和告警摘要。",
        category="虚拟化",
        scope_type="asset_type",
        asset_types=("vmware", "esxi", "vcenter", "proxmox", "openstack"),
        protocols=("vmware", "virtual", "http_api"),
        pinned=True,
        sort_order=71,
    ),
    SlashCommand(
        "network-device-health",
        "/net-health 网络设备健康",
        "检查网络设备接口、路由、邻居、CPU/内存和告警",
        "请只读检查 {target} 的网络设备健康：设备型号/版本、CPU/内存、接口状态、错误包、路由/邻居摘要、HA 状态和近期告警。不要修改配置。",
        category="网络",
        scope_type="asset_type",
        asset_types=("network_device", "switch", "router", "firewall", "f5", "a10", "waf", "vpn"),
        protocols=("ssh", "snmp", "http_api"),
        pinned=True,
        sort_order=76,
    ),
    SlashCommand(
        "s3-buckets",
        "/buckets 存储桶",
        "检查 S3 Bucket 清单、公开访问和生命周期策略",
        "请只读检查 {target} 的对象存储 Bucket 清单、公开访问风险、生命周期策略、版本控制、加密和跨区域复制状态。",
        category="存储",
        scope_type="asset_type",
        asset_types=("s3", "minio", "oss", "cos", "obs", "object_storage"),
        protocols=("s3", "http_api"),
        pinned=True,
        sort_order=81,
    ),
    SlashCommand(
        "storage-health",
        "/storage 存储健康",
        "检查块/文件/分布式存储容量、告警和副本状态",
        "请只读检查 {target} 的存储健康：容量水位、卷/池状态、副本/恢复状态、近期告警、性能瓶颈和数据保护风险。",
        category="存储",
        scope_type="asset_type",
        asset_types=("ceph", "nfs", "nas", "san", "hdfs", "glusterfs", "backup"),
        protocols=("ssh", "snmp", "http_api"),
        pinned=True,
        sort_order=82,
    ),
    SlashCommand(
        "monitoring-alerts",
        "/alerts 告警摘要",
        "检查监控平台当前告警、规则和采集目标状态",
        "请只读检查 {target} 的监控平台状态：当前告警、采集目标在线性、规则/通知异常、近期错误和需要优先处置的对象。",
        category="监控告警",
        scope_type="asset_type",
        asset_types=("prometheus", "alertmanager", "grafana", "loki", "victoriametrics", "zabbix", "manageengine"),
        protocols=("http_api",),
        pinned=True,
        sort_order=86,
    ),
    SlashCommand(
        "oob-hardware",
        "/hardware 硬件健康",
        "检查带外管理、硬件传感器、电源、风扇和磁盘",
        "请只读检查 {target} 的硬件健康：电源、风扇、温度、磁盘、RAID、日志事件和保修/型号线索，按严重程度输出。",
        category="带外/硬件",
        scope_type="asset_type",
        asset_types=("redfish", "ilo", "idrac", "ipmi", "snmp_device"),
        protocols=("redfish", "snmp", "http_api"),
        pinned=True,
        sort_order=88,
    ),
    SlashCommand(
        "api-health",
        "/api-health API 健康",
        "检查 HTTP/API 连通、认证、关键端点和错误摘要",
        "请只读检查 {target} 的 API 健康状态：认证方式、关键端点连通性、版本信息、错误响应和可观测性线索。不要调用写接口。",
        category="平台/API",
        scope_type="protocol",
        protocols=("http_api", "rest", "api"),
        sort_order=91,
    ),
]


def _custom_matches(command: dict[str, Any], context: dict[str, Any]) -> bool:
    if not command.get("enabled", True):
        return False
    scope_type = str(command.get("scope_type") or "global").lower()
    asset_type = str(context.get("asset_type") or "").lower()
    protocol = str(context.get("protocol") or "").lower()
    host = str(context.get("host") or "").lower()
    if scope_type == "global":
        return True
    if scope_type == "asset_type":
        return asset_type == str(command.get("asset_type") or "").lower()
    if scope_type == "protocol":
        return protocol == str(command.get("protocol") or "").lower()
    if scope_type == "asset":
        return (
            asset_type == str(command.get("asset_type") or "").lower()
            and protocol == str(command.get("protocol") or "").lower()
            and host == str(command.get("host") or "").lower()
        )
    return False


def _render_custom(command: dict[str, Any], context: dict[str, Any], active_tools: list[str] | None) -> dict[str, Any]:
    rendered = SlashCommand(
        id=str(command.get("id") or ""),
        label=str(command.get("label") or ""),
        description=str(command.get("description") or ""),
        prompt_template=str(command.get("prompt_template") or ""),
        category=str(command.get("category") or "自定义"),
        scope_type=str(command.get("scope_type") or "global"),
        readonly=bool(command.get("readonly", True)),
        pinned=bool(command.get("pinned", False)),
        sort_order=int(command.get("sort_order") or 1),
        source="custom",
    ).render(context, active_tools)
    rendered.update(
        {
            "asset_type": command.get("asset_type") or "",
            "protocol": command.get("protocol") or "",
            "host": command.get("host") or "",
            "enabled": bool(command.get("enabled", True)),
        }
    )
    return rendered


def _render_builtin_with_override(
    command: SlashCommand,
    override: dict[str, Any] | None,
    context: dict[str, Any],
    active_tools: list[str] | None,
) -> dict[str, Any]:
    if not override:
        return command.render(context, active_tools)

    base = command.render(context, active_tools)
    template = str(override.get("prompt_template") or base.get("prompt_template") or "")
    merged = {
        **base,
        "label": str(override.get("label") or base["label"]),
        "description": str(override.get("description") or base["description"]),
        "prompt_template": template,
        "category": str(override.get("category") or base["category"]),
        "scope_type": str(override.get("scope_type") or base["scope_type"]),
        "asset_type": override.get("asset_type") or base.get("asset_type") or "",
        "protocol": override.get("protocol") or base.get("protocol") or "",
        "host": override.get("host") or "",
        "readonly": bool(override.get("readonly", base.get("readonly", True))),
        "pinned": bool(override.get("pinned", base.get("pinned", False))),
        "enabled": bool(override.get("enabled", True)),
        "sort_order": int(override.get("sort_order") or base.get("sort_order") or 1),
        "source": "builtin_override",
        "is_override": True,
        "builtin_id": command.id,
    }
    merged["prompt"] = safe_format(
        template,
        {
            "target": "{asset_type}/{protocol} {host}".format(
                asset_type=context.get("asset_type") or "asset",
                protocol=context.get("protocol") or "protocol",
                host=context.get("host") or "",
            ).strip(),
            "tool_list": _tool_list_text(active_tools),
            "host": context.get("host") or "",
            "port": context.get("port") or "",
            "asset_type": context.get("asset_type") or "",
            "protocol": context.get("protocol") or "",
            "remark": context.get("remark") or "",
            "username": context.get("username") or "",
        },
    )
    return merged


def render_builtin_templates(
    context: dict[str, Any],
    active_tools: list[str] | None = None,
    custom_commands: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    overrides = {str(command.get("id")): command for command in custom_commands or []}
    templates = [
        _render_builtin_with_override(command, overrides.get(command.id), context, active_tools)
        for command in COMMANDS
        if command.matches(context)
    ]
    return sorted(templates, key=lambda item: (not item.get("pinned"), int(item.get("sort_order") or 101), item.get("label", "")))


def render_slash_commands(
    context: dict[str, Any],
    active_tools: list[str] | None = None,
    custom_commands: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    builtin_ids = {command.id for command in COMMANDS}
    commands = [
        command
        for command in render_builtin_templates(context, active_tools, custom_commands)
        if command.get("enabled", True)
    ]
    for command in custom_commands or []:
        if str(command.get("id")) in builtin_ids:
            continue
        if _custom_matches(command, context):
            commands.append(_render_custom(command, context, active_tools))
    return sorted(commands, key=lambda item: (not item.get("pinned"), int(item.get("sort_order") or 101), item.get("label", "")))
