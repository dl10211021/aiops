from __future__ import annotations

from core.asset_protocols import (
    API_PROTOCOLS,
    DATABASE_HTTP_PROTOCOLS,
    SERVICE_ASSET_TYPES,
    SERVICE_PROBE_PROTOCOLS,
    SQL_PROTOCOLS,
    STORAGE_API_PROTOCOLS,
    VIRTUALIZATION_API_PROTOCOLS,
    normalize_protocol,
)
from core.tool_registry import tool_registry


SENSITIVE_CONTEXT_KEYWORDS = {
    "bearer_token",
    "kubeconfig",
    "api_token",
    "v3_auth_pass",
    "v3_priv_pass",
    "community_string",
    "enable_pass",
    "password",
    "secret",
    "token",
    "api_key",
}


def format_extra_args_for_prompt(extra_args: dict) -> str:
    return "\\n".join(
        [
            (
                f"- {k}: "
                f"{'(已托管，执行时自动注入)' if any(s in k.lower() for s in SENSITIVE_CONTEXT_KEYWORDS) else v}"
            )
            for k, v in extra_args.items()
            if v
        ]
    )


def protocol_tool_guidance(protocol: str, asset_type: str, host: str) -> str:
    protocol = normalize_protocol(asset_type, protocol)
    if protocol == "ssh" and asset_type in {"switch"}:
        return (
            f"连接状态：后端已经建立到网络设备 {host} 的 SSH CLI 会话。你已经在该交换机/路由器上下文内，"
            "直接调用 `network_cli_execute_command` 执行 display/show/ping 等只读巡检命令；"
            "不要使用 Linux 命令，不要编写连接脚本或重新登录。"
        )
    if protocol == "ssh" and asset_type in {"ceph", "nfs", "hdfs", "glusterfs"}:
        return (
            f"连接状态：后端已经建立到存储节点 {host} 的 SSH 会话。"
            "直接调用 `storage_execute_command` 执行 Ceph/NFS/HDFS/GlusterFS 只读巡检命令；"
            "不要把它当普通 Linux 主机泛化操作，扩容、删除、修复、重平衡等动作必须走审批。"
        )
    if protocol == "ssh":
        return (
            f"连接状态：后端已经建立到目标 {host} 的 SSH 会话。你已经在该资产上下文内，"
            "直接调用 `linux_execute_command` 执行巡检命令；不要再编写连接脚本或尝试重新登录。"
        )
    if protocol == "winrm":
        if asset_type == "hyperv":
            return (
                f"连接状态：后端已经建立到 Hyper-V 主机 {host} 的 WinRM 会话。"
                "直接调用 `winrm_execute_command` 执行 Get-VM、Get-VMHost、Get-VMSwitch 等 PowerShell 巡检命令；"
                "不要把它当作 VMware/OpenStack/ZStack API，也不要重新登录。"
            )
        return (
            f"连接状态：后端已经建立到 Windows 目标 {host} 的 WinRM 会话。你已经在该系统上下文内，"
            "直接调用 `winrm_execute_command` 执行 PowerShell/CMD 巡检；不要再编写 WinRM/Python 连接脚本，"
            "也不要向用户解释“无法通过本地脚本”。读取 Security 安全日志失败时，先用 `whoami /groups` "
            "确认当前账号是否属于 Administrators 或 Event Log Readers，并明确说明需要补足 Windows 事件日志读取权限；"
            "不要笼统归因成 WinRM 限制。"
        )
    if protocol in SQL_PROTOCOLS:
        try:
            from connections.db_manager import get_database_operation_profile

            profile = get_database_operation_profile(asset_type or protocol)
        except Exception:
            profile = {}
        profile_label = profile.get("label") or asset_type.upper()
        identity_label = profile.get("identity_label") or "Database / SID"
        test_statement = profile.get("test_statement") or "SELECT 1"
        examples = "；".join(profile.get("readonly_examples") or [])
        return (
            f"连接状态：后端已经建立到 {profile_label} 数据库 {host} 的托管会话。"
            f"当前连接标识字段是 {identity_label}，验证语句是 `{test_statement}`。"
            "你当前连接的是数据库实例，不是操作系统 Shell；直接调用 `db_execute_query` 执行 SQL 读取或经审批的变更，"
            "不要在工具参数里填写 host/user/password，也不要尝试 SSH/WinRM 登录。"
            "只读巡检优先使用 SELECT/SHOW/DESCRIBE/EXPLAIN/WITH 等查询；INSERT/UPDATE/DELETE/DDL/权限变更必须走审批。"
            + (f"常用只读示例：{examples}。" if examples else "")
        )
    if protocol == "redis":
        return "当前 Redis 资产使用 `redis_execute_command`，凭据由资产中心托管注入。"
    if protocol == "memcached":
        return "当前 Memcached 资产使用 `memcached_execute_command`，支持 version、stats、get、gets 等只读命令。"
    if protocol == "mongodb":
        return "当前 MongoDB 资产使用 `mongodb_find` 做只读查询，凭据由资产中心托管注入。"
    if protocol in DATABASE_HTTP_PROTOCOLS:
        return (
            f"当前 {asset_type or protocol} 是数据库管理接口资产，不是通用业务 API。"
            "使用 `database_api_request` 通过数据库自身查询/管理接口执行巡检或经审批的配置操作，"
            "凭据由资产中心托管注入；写入、删除索引、修改集群配置等操作必须走审批。"
        )
    if protocol in VIRTUALIZATION_API_PROTOCOLS:
        return (
            f"当前 {asset_type or protocol} 是虚拟化/私有云平台资产。"
            "使用 `virtualization_api_request` 通过平台 API 做只读巡检或经审批的配置操作，"
            "不要把它当作普通主机 Shell，也不要绕过资产中心凭据。"
        )
    if protocol in STORAGE_API_PROTOCOLS:
        return (
            f"当前 {asset_type or protocol} 是存储平台资产。"
            "使用 `storage_api_request` 执行对象存储、备份或存储管理面的只读巡检；"
            "删除对象、修改策略、清理备份等高风险动作必须走审批。"
        )
    if protocol in SERVICE_PROBE_PROTOCOLS or asset_type in SERVICE_ASSET_TYPES:
        return (
            f"当前 {asset_type or protocol} 是业务探测资产。"
            "使用 `service_probe_request` 做只读连通性、证书、端口或协议握手探测；"
            "它不是管理 API，不要用它修改目标系统配置。"
        )
    if protocol == "http_api":
        active_names = {
            tool.name
            for tool in tool_registry.available(
                {
                    "target_scope": "asset",
                    "asset_type": asset_type,
                    "protocol": protocol,
                    "extra_args": {},
                }
            )
        }
        for tool_name in (
            "bigdata_api_request",
            "middleware_api_request",
            "discovery_api_request",
            "container_api_request",
            "network_api_request",
            "security_api_request",
            "cicd_api_request",
            "ai_platform_api_request",
            "oob_api_request",
        ):
            if tool_name in active_names:
                return (
                    f"当前 {asset_type or protocol} 是平台管理 API 资产。"
                    f"使用 `{tool_name}` 调用目标只读接口，Token、Basic Auth 等凭据由资产中心托管注入；"
                    "涉及配置变更、删除、重启、发布等操作必须走审批。"
                )
    if protocol in API_PROTOCOLS:
        return (
            "当前 API/监控平台资产使用 `http_api_request` 调用目标 API；"
            "Token、Basic Auth 等凭据由资产中心托管注入。"
        )
    if protocol == "snmp":
        return "当前 SNMP 资产使用 `snmp_get` 读取 OID，Community/SNMP 凭据由资产中心托管注入。"
    return (
        "当前真实资产没有专用原生协议工具时，应直接报告工具缺口；"
        "`local_execute_script` 只允许 VIRTUAL 技能研发会话使用，不能代替真实资产协议连接。"
    )


def protocol_tool_list(
    protocol: str,
    has_skill_scripts: bool = False,
    asset_type: str = "",
) -> str:
    context = {
        "target_scope": "asset",
        "asset_type": asset_type,
        "protocol": protocol,
        "extra_args": {"login_protocol": protocol} if protocol == "virtual" else {},
    }
    lines = tool_registry.prompt_lines(context).splitlines()
    if not has_skill_scripts:
        lines = [
            line
            for line in lines
            if not line.startswith("- local_execute_script:")
        ]
    return "\n".join(lines)


def allow_local_skill_scripts(protocol: str) -> bool:
    return normalize_protocol(protocol=protocol) == "virtual"
