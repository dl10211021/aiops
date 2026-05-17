from __future__ import annotations

import os

from core.asset_protocols import get_asset_definition
from core.agent_protocol_context import (
    format_extra_args_for_prompt,
    protocol_tool_guidance,
    protocol_tool_list,
)
from core.prompt_packs import (
    render_aiops_behavior_prompt,
    render_context_precedence_prompt,
    render_evidence_contract_prompt,
    render_ops_runbook_prompt,
    render_permission_mode_prompt,
    render_skill_install_prompt,
    render_web_browser_prompt,
)
from core.agent_session_context import AgentSessionContext

PROMPT_MANIFEST_VERSION = 1


_CATEGORY_LABELS = {
    "os": "操作系统",
    "db": "数据库",
    "container": "容器/云原生",
    "middleware": "中间件",
    "network": "网络设备",
    "monitor": "监控平台",
    "monitoring": "监控平台",
    "security": "安全设备/平台",
    "storage": "存储",
    "bigdata": "大数据",
    "virtualization": "虚拟化/云平台",
    "service": "网络服务探测",
    "api": "API 服务",
    "ai": "AI 平台",
    "cicd": "CI/CD 平台",
    "oob": "带外管理",
    "discovery": "发现/资产管理",
}


_PROTOCOL_MODE_LABELS = {
    "ssh": "SSH / Linux-Unix 终端会话",
    "winrm": "WinRM / Windows 远程管理会话",
    "virtual": "虚拟/本地技能研发会话",
    "http_api": "HTTP API 资产会话",
    "snmp": "SNMP 网络设备监控会话",
    "network_cli": "网络设备 CLI 会话",
    "k8s": "Kubernetes API 会话",
}


_SAFE_IDENTITY_ARG_KEYS = (
    "category",
    "sub_type",
    "asset_sub_type",
    "db_type",
    "device_type",
    "vendor",
    "platform",
    "engine",
    "product",
    "service_name",
    "database",
    "db_name",
    "login_protocol",
    "protocol",
)


def _clean_label(value: object) -> str:
    return str(value or "").strip()


def _humanize_identifier(value: object) -> str:
    raw = _clean_label(value)
    if not raw:
        return ""
    text = raw.replace("_", " ").replace("-", " ").strip()
    if text and text.isascii():
        return " ".join(part.upper() if len(part) <= 4 else part.capitalize() for part in text.split())
    return text


def _category_label(value: object) -> str:
    raw = _clean_label(value).lower()
    return _CATEGORY_LABELS.get(raw) or _humanize_identifier(value)


def _safe_identity_fields(extra_args: dict) -> str:
    fields = []
    for key in _SAFE_IDENTITY_ARG_KEYS:
        value = extra_args.get(key)
        if value is None or value == "":
            continue
        fields.append(f"{key}={value}")
    return "；".join(fields)


def _session_context_prompt(session_context: AgentSessionContext) -> str:
    protocol = str(session_context.protocol or "unknown").lower()
    asset_type = str(session_context.asset_type or "asset").lower()
    definition = get_asset_definition(asset_type) or {}
    extra_args = session_context.extra_args or {}
    category = definition.get("category") or extra_args.get("category") or ""
    definition_label = _clean_label(definition.get("label"))
    session_label = _PROTOCOL_MODE_LABELS.get(protocol)
    if not session_label:
        if category == "db" or extra_args.get("db_type"):
            session_label = f"{_humanize_identifier(protocol)} 数据库会话"
        elif category == "network" or extra_args.get("device_type") in {"network", "switch", "router", "firewall"}:
            session_label = f"{_humanize_identifier(protocol)} 网络设备会话"
        else:
            session_label = f"{_humanize_identifier(protocol) or protocol.upper()} 协议会话"
    asset_label = definition_label or _humanize_identifier(
        extra_args.get("sub_type")
        or extra_args.get("asset_sub_type")
        or extra_args.get("db_type")
        or extra_args.get("device_type")
        or asset_type
    )
    category_text = _category_label(category) if category else "未分类/自定义"
    identity_fields = _safe_identity_fields(extra_args)
    identity_line = f"- 资产识别：{asset_label}（类型 {asset_type}，分类 {category_text}，协议 {protocol}）"
    if identity_fields:
        identity_line += f"\n- 识别字段：{identity_fields}"
    return f"""[当前会话上下文]
- 会话类型：{session_label}
- {identity_line[2:]}
- 目标：{session_context.host or "未指定"}:{session_context.port or "未指定"}
- 登录身份：{session_context.username or "未指定"}
- 重要约束：不要假设所有会话都是 SSH，也不要把未知资产强行归类；必须按当前协议、资产识别字段和可用工具选择对应原生工具、命令、SQL、CLI 或 API。"""


def _asset_credentials_prompt(session_context: AgentSessionContext) -> str:
    extra_creds_str = format_extra_args_for_prompt(session_context.extra_args)
    return f"""[当前持有的资产凭证]
一台通过{session_context.protocol.upper()}协议纳管的 {session_context.asset_type.upper()} 资产：
- 目标IP/主机名: {session_context.host}
- 端口: {session_context.port}
- 账号: {session_context.username}
- 凭证信息: (已安全托管，底层工具执行时自动注入，无需在脚本中自行填写)\n{extra_creds_str}
{protocol_tool_guidance(session_context.protocol, session_context.asset_type, session_context.host)}"""


def _trusted_operator_source_prompt() -> str:
    raw_ips = os.environ.get("OPSCORE_TRUSTED_SOURCE_IPS", "192.168.111.45")
    trusted_ips = [
        item.strip()
        for item in raw_ips.replace("，", ",").split(",")
        if item.strip()
    ]
    trusted_text = "、".join(trusted_ips) if trusted_ips else "未配置"
    return f"""[可信运维来源过滤]
- 以下来源 IP 视为 OpsCore 平台、本地浏览器、自动采集程序或已知运维跳板来源：{trusted_text}
- 分析 SSH/WinRM/数据库/网络设备登录日志时，来自上述来源的成功登录只能作为“平台巡检/运维访问事实”记录，默认不要升级为异常、暴力破解、凭证泄露或高风险项。
- 只有同时出现 Failed 登录、未知账号、非工作时间异常、来源不在可信列表、权限提升、横向移动、命令异常或用户明确要求排查该来源时，才可以把可信来源登录提升为风险。
- 如果报告里需要提到可信来源登录，请写成“来自可信运维来源/OpsCore 采集来源的访问”，不要反复给出高风险结论。"""


def render_chat_system_prompt(
    *,
    session_context: AgentSessionContext,
    base_prompt: str,
    skill_instructions: str,
    ltm_context: str,
    asset_profile_prompt: str = "",
    rag_context: str = "",
) -> str:
    return f"""
{base_prompt}

{_session_context_prompt(session_context)}

{_asset_credentials_prompt(session_context)}

{render_permission_mode_prompt(session_context)}

{_trusted_operator_source_prompt()}

{render_ops_runbook_prompt(session_context)}

{render_evidence_contract_prompt()}

{render_aiops_behavior_prompt(session_context)}

{render_skill_install_prompt()}

{render_web_browser_prompt()}

[使用的基础执行工具]
{protocol_tool_list(session_context.protocol, session_context.has_local_skill_scripts, session_context.asset_type)}

[当前已加载专业技能说明 (Skills)]
以下是当前专业技能的详细 <INSTRUCTIONS> 指令，请严格遵照其中的步骤进行操作
{skill_instructions}

{asset_profile_prompt}

{rag_context}

{ltm_context}

{render_context_precedence_prompt()}
"""


def build_chat_prompt_manifest(
    *,
    session_context: AgentSessionContext,
    has_skill_instructions: bool,
    has_asset_profile: bool,
    has_rag_context: bool,
    has_ltm_context: bool,
    analysis_only: bool = False,
) -> dict:
    modules = [
        "agent_profile",
        "session_context",
        "asset_credentials",
        "permission_mode",
        "trusted_operator_source",
        "ops_runbook",
        "evidence_contract",
        "aiops_behavior",
        "skill_install",
        "web_browser",
        "tool_catalog",
        "skill_instructions",
        "asset_profile",
        "rag_context",
        "ltm_context",
        "context_precedence",
    ]
    if analysis_only:
        modules.append("analysis_only")
    return {
        "version": PROMPT_MANIFEST_VERSION,
        "surface": "chat",
        "asset_type": session_context.asset_type,
        "protocol": session_context.protocol,
        "mode": "read_write" if session_context.allow_modifications else "read_only",
        "modules": modules,
        "enabled": {
            "skill_instructions": has_skill_instructions,
            "asset_profile": has_asset_profile,
            "rag_context": has_rag_context,
            "ltm_context": has_ltm_context,
            "analysis_only": analysis_only,
        },
    }


def build_headless_prompt_manifest(
    *,
    session_context: AgentSessionContext,
) -> dict:
    modules = [
        "agent_profile",
        "session_context",
        "asset_credentials",
        "trusted_operator_source",
        "ops_runbook",
        "evidence_contract",
        "delegated_task",
        "tool_catalog",
    ]
    return {
        "version": PROMPT_MANIFEST_VERSION,
        "surface": "headless",
        "asset_type": session_context.asset_type,
        "protocol": session_context.protocol,
        "mode": "read_write" if session_context.allow_modifications else "read_only",
        "modules": modules,
        "enabled": {
            "skill_paths": session_context.has_local_skill_scripts,
        },
    }


def render_headless_system_prompt(
    *,
    session_context: AgentSessionContext,
    base_prompt: str,
    task_description: str,
) -> str:
    return f"""{base_prompt}

{_session_context_prompt(session_context)}

{_asset_credentials_prompt(session_context)}

{_trusted_operator_source_prompt()}

{render_ops_runbook_prompt(session_context)}

{render_evidence_contract_prompt()}

[上级指挥官委派的任务]
你是第一线的运维管理工程师调用的 Agent。
上级委派给你的任务是：
{task_description}

请在当前的会话（{session_context.host}）内，利用你的技能和工具，全力完成该任务。
在完成操作、修复或检查完成后，给出一份详细的「执行结果报告」。该报告将直接返回给上级指挥官作为你的工作内容。
真实资产会话中，不要说“无法通过本地脚本”“改用平台原生工具”这类解释；直接通过当前会话的原生协议工具执行。

[使用的基础执行工具]
{protocol_tool_list(session_context.protocol, session_context.has_local_skill_scripts, session_context.asset_type)}
"""
