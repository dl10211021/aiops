import os
import json
import asyncio
import logging
from core.dispatcher import dispatcher
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
from core.agent_attachments import (
    _attachment_metadata_for_memory,
    _build_current_user_content,
    _chat_image_attachments,
    _model_supports_image_input,
    _safe_user_message_for_memory,
)
from core.agent_approval import (
    record_headless_approval_block,
    record_tool_approval_request,
)
from core.agent_interactions import (
    _build_interaction_payload,
    _normalize_interaction_options,
    _wait_for_user_interaction,
)
from core.agent_runtime_config import (
    DEFAULT_AGENT_MAX_STEPS,
    DEFAULT_HEADLESS_AGENT_MAX_STEPS,
    MAX_AGENT_STEP_CAP,
    MIN_AGENT_STEP_CAP,
    agent_max_steps,
    agent_step_limit_instruction,
    clamp_agent_max_steps,
    get_agent_runtime_config,
    update_agent_runtime_config,
)
from core.agent_tool_events import (
    build_tool_end_event,
    parse_tool_arguments,
    summarize_tool_result_for_sse,
)
from core.embedding_config import (
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    get_embedding_config,
    update_embedding_config,
)
from core.redaction import redact_text
from core.safety_policy import approval_timeout_seconds
from core.tool_registry import tool_registry

cancel_flags = {}

logger = logging.getLogger(__name__)

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
            f"- {k}: {'(已托管，执行时自动注入)' if any(s in k.lower() for s in SENSITIVE_CONTEXT_KEYWORDS) else v}"
            for k, v in extra_args.items()
            if v
        ]
    )


async def get_available_models() -> list:
    return await get_available_models_for_provider()


async def get_available_models_for_provider(
    provider_id: str | None = None, refresh: bool = False
) -> list:
    try:
        from core.llm_factory import get_all_providers
        from openai import AsyncOpenAI
        import asyncio
        import logging
        
        providers = get_all_providers()
        if provider_id:
            providers = [p for p in providers if p.get("id") == provider_id]
        
        async def fetch_provider_models(p):
            models_list = []
            manual_models = [m.strip() for m in p.get("models", "").split(",") if m.strip()]
            
            if manual_models and not refresh:
                for m in manual_models:
                    models_list.append({"id": f"{p['id']}|{m}", "name": m})
            if (refresh or not models_list) and p.get("protocol") == "openai":
                try:
                    api_key = p.get("api_key")
                    if not api_key:
                        api_key = "dummy"
                        
                    base_url = p.get("base_url")
                    if not base_url:
                        base_url = "https://api.openai.com/v1"
                        
                    temp_client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=30.0)
                    response = await temp_client.models.list()
                    models_list = []
                    for m in response.data:
                        models_list.append({"id": f"{p['id']}|{m.id}", "name": m.id})
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Failed to fetch models for {p.get('name')}: {e}")
                    if manual_models:
                        models_list = [{"id": f"{p['id']}|{m}", "name": m} for m in manual_models]
            
            if not models_list:
                models_list.append({"id": f"{p['id']}|none", "name": "未获取到模型或配置错误"})
            
            return {"provider_id": p["id"], "provider_name": p["name"], "models": models_list}

        results = await asyncio.gather(*(fetch_provider_models(p) for p in providers))
        
        grouped_models = [res for res in results if res is not None]
        return grouped_models
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to fetch models: {e}")
        return []


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
    protocol: str, has_skill_scripts: bool = False, asset_type: str = ""
) -> str:
    context = {
        "target_scope": "asset",
        "asset_type": asset_type,
        "protocol": protocol,
        "extra_args": {"login_protocol": protocol} if protocol == "virtual" else {},
    }
    lines = tool_registry.prompt_lines(context).splitlines()
    if not has_skill_scripts:
        lines = [line for line in lines if not line.startswith("- local_execute_script:")]
    return "\n".join(lines)


def allow_local_skill_scripts(protocol: str) -> bool:
    return normalize_protocol(protocol=protocol) == "virtual"


# 从 SQLite 持久化用户模型
from core.memory import memory_db


async def chat_stream_agent(
    session_id: str,
    user_message: str,
    user_display_message: str | None = None,
    model_name: str | None = None,
    thinking_mode: str = "off",
    user_attachments: list[dict] | None = None,
):
    cancel_flags[session_id] = False
    from connections.ssh_manager import ssh_manager
    from core.llm_factory import get_client_for_model, get_default_model_id, get_embedding_client_and_model

    if not model_name:
        model_name = get_default_model_id()

    emb_client, embedding_model = get_embedding_client_and_model(model_name)

    session_info = ssh_manager.active_sessions[session_id]["info"]
    allow_modifications = session_info.get("allow_modifications", False)
    active_skills = session_info.get("active_skills", [])
    agent_profile = session_info.get("agent_profile", "default")

    # 获取资产协议凭证信息，构建模型上下文
    asset_type = session_info.get("asset_type", "ssh")
    protocol = session_info.get("protocol", asset_type)
    is_virtual = session_info.get("is_virtual", False)
    host = session_info.get("host", "")
    port = session_info.get("port", "")
    username = session_info.get("username", "")
    extra_args = session_info.get("extra_args", {})
    password = session_info.get("password")

    # 从外部 Markdown 文件加载 Agent 的核心人格 (Soul)
    profile_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "workspaces",
        agent_profile,
        "SOUL.md",
    )

    if os.path.exists(profile_path):
        with open(profile_path, "r", encoding="utf-8") as f:
            base_prompt = f.read()
    else:
        base_prompt = "你是 OpsCore 的高级 AI 运维专家。"

    # 从 LanceDB 获取长期记忆（与当前话题相关的历史摘要）
    try:
        ltm_context = await memory_db.retrieve_ltm(
            session_id, user_message, emb_client, embedding_model
        )
    except Exception as e:
        logger.error(f"LTM retrieve error: {e}")
        ltm_context = ""

    # 凭证信息格式化为字符串 (已移除，防泄漏)

    extra_creds_str = format_extra_args_for_prompt(extra_args)
    active_skill_paths = dispatcher.get_active_skill_paths(active_skills)
    local_skill_scripts_allowed = allow_local_skill_scripts(protocol)
    SYSTEM_PROMPT = f"""
{base_prompt}

[当前持有的资产凭证]
一台通过{protocol.upper()}协议纳管的 {asset_type.upper()} 资产：
- 目标IP/主机名: {host}
- 端口: {port}
- 账号: {username}
- 凭证信息: (已安全托管，底层工具执行时自动注入，无需在脚本中自行填写)\n{extra_creds_str}
{protocol_tool_guidance(protocol, asset_type, host)}

[已知安全模式]
1. 用户动态加载的「可用Skills」决定了你「什么时候能调什么路」。仔细阅读已加载的技能说明！
2. 当前会话权限状态：{"**高级读写修改权限**：可以执行修改系统的操作" if allow_modifications else "**只读巡检模式**：允许执行不改变目标状态的查询/巡检命令；禁止文件写入、服务启停、账号权限、数据修改、安装卸载等变更操作。"}
3. 执行某些较高风险脚本时，请仔细参考技能说明中提供的 `<SKILL_ABSOLUTE_PATH>` 路径和 `cwd` 工作目录路径。不要自己凭空猜测目录。

[AIOps 专家行为准则 (CRITICAL)]
作为运维管理工程师现场助手级别的专业伙伴：
- **启用超能力 (Using Superpowers)**：你现在已被赋予 OpsCore 平台的“Superpowers”（超能力扩展）。你必须将已挂载的专业技能 (Skills) 视为你的第一准则。**只要有挂载的 Skill，你必须无条件、优先遵照 Skill 内部的 `<INSTRUCTIONS>` 步骤进行思考、规划和执行！绝对不允许跳过 Skill 的流程去自由发挥。**
- **主动规划 (Proactive Planning)**：在接到运维操作任务时，明确列出操作思路和步骤 (Step 1, Step 2...)，不要盲目执行指令- **根因分析 (Root Cause Analysis)**：不要肤浅地只看表面。要像一名工程师一样，一步一步深入地直接指向异常
- **闭环思维 (Closed-loop)**：操作、修复后自动执行修复验证确认修复
- **连接失败与防死循环 (Anti-Loop & Boundary)**：对目标资产（{host}）的系统级交互【必须且只能】通过当前协议对应的原生工具完成。如果原生工具报错“认证失败”或“无法连接”，代表系统底层通信已断开。此时请【立即停止重试】并直接向用户报告失败。绝不允许编写 Paramiko/WinRM/数据库/API 脚本尝试绕过资产中心凭据，也绝不允许获取宿主机信息作为替代。
- **自我进化与未知资产应对 (Self-Evolution)**：当用户要你「安装」「修复」「改」或「打一个新技能」时，使用 `evolve_skill` 去修复或变更你的代码。只有 `VIRTUAL` 技能研发会话允许使用本地脚本；Windows、Linux、数据库、API、SNMP 等真实资产会话禁止用本地脚本代替原生协议工具。
- **用户交互请求 (Interactive Input)**：当确实需要用户补充密码、选择方案、确认偏好或提供业务上下文时，调用 `request_user_interaction`，让前端弹出输入/选择卡片；不要在普通文本里等待用户输入。
- **工具执行表达规范**：真实资产会话中，不要说“无法通过本地脚本”“改用平台原生工具”这类解释；直接说明“正在通过当前会话的原生协议工具执行巡检”即可。

[使用的基础执行工具]
{protocol_tool_list(protocol, local_skill_scripts_allowed and bool(active_skill_paths), asset_type)}

[当前已加载专业技能说明 (Skills)]
以下是当前专业技能的详细 <INSTRUCTIONS> 指令，请严格遵照其中的步骤进行操作
{dispatcher.get_skill_instructions(active_skills, allow_local_scripts=local_skill_scripts_allowed)}

{ltm_context}
"""

    # 从 SQLite 中读取之前的有效会话（去掉之前的 system 提示词）
    db_messages = memory_db.get_messages(session_id)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for msg in db_messages:
        if msg.get("role") != "system":
            messages.append(msg)

    current_user_content = _build_current_user_content(user_message, user_attachments or [], model_name)
    safe_user_msg = _safe_user_message_for_memory(
        user_display_message or user_message,
        user_attachments or [],
    )
    new_user_msg = {"role": "user", "content": current_user_content}
    memory_db.append_message(session_id, safe_user_msg)
    messages.append(new_user_msg)

    context = {
        "session_id": session_id,
        "os_type": "linux",
        "allow_modifications": allow_modifications,
        "active_skills": active_skills,
        "active_skill_paths": active_skill_paths if local_skill_scripts_allowed else [],
        "asset_type": asset_type,
        "protocol": protocol,
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "extra_args": extra_args,
        "target_scope": session_info.get("target_scope", "asset"),
        "scope_value": session_info.get("scope_value", None),
    }
    tools = dispatcher.get_available_tools(context)

    try:
        # Initial status
        yield f"data: {json.dumps({'type': 'status', 'content': '🤖 AI 正在分析并规划执行路径...'})}\n\n"
        await asyncio.sleep(0.05)

        max_steps = agent_max_steps("chat")
        for iteration in range(max_steps):
            logger.info(
                f"Loop {iteration} for {session_id}, cancel_flags: {cancel_flags.get(session_id)}"
            )
            if cancel_flags.get(session_id) is True:
                cancel_flags[session_id] = False
                cancel_payload = {"type": "error", "content": "任务已被手动中止。"}
                yield f"data: {json.dumps(cancel_payload)}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                break

            from core.llm_execution import execute_chat_stream

            assistant_content = ""
            thinking_content = ""
            tool_calls = []

            msg_status = json.dumps({"type": "status", "content": "💭 思考中..."})
            yield f"data: {msg_status}\n\n"

            is_thinking_stream = False
            async for chunk in execute_chat_stream(
                model_name, messages, thinking_mode, tools=tools
            ):
                if cancel_flags.get(session_id) is True:
                    break
                if chunk["type"] == "thinking":
                    if not is_thinking_stream:
                        think_start = json.dumps(
                            {"type": "chunk", "content": "<think>\n"}
                        )
                        yield f"data: {think_start}\n\n"
                        is_thinking_stream = True
                    msg_chunk = json.dumps(
                        {"type": "chunk", "content": chunk["content"]}
                    )
                    yield f"data: {msg_chunk}\n\n"
                    thinking_content += chunk["content"]
                elif chunk["type"] == "content":
                    if is_thinking_stream:
                        think_end = json.dumps(
                            {"type": "chunk", "content": "\n</think>\n"}
                        )
                        yield f"data: {think_end}\n\n"
                        is_thinking_stream = False
                    msg_chunk = json.dumps(
                        {"type": "chunk", "content": chunk["content"]}
                    )
                    yield f"data: {msg_chunk}\n\n"
                    assistant_content += chunk["content"]
                elif chunk["type"] == "tool_calls":
                    if is_thinking_stream:
                        think_end = json.dumps(
                            {"type": "chunk", "content": "\n</think>\n"}
                        )
                        yield f"data: {think_end}\n\n"
                        is_thinking_stream = False
                    tool_calls = chunk["tool_calls"]

            if is_thinking_stream:
                think_end = json.dumps({"type": "chunk", "content": "\n</think>\n"})
                yield f"data: {think_end}\n\n"
                is_thinking_stream = False

            safe_msg = {"role": "assistant", "content": assistant_content}
            if thinking_content:
                safe_msg["reasoning_content"] = thinking_content
            if tool_calls:
                safe_msg["tool_calls"] = tool_calls

            messages.append(safe_msg)
            memory_db.append_message(session_id, safe_msg)

            if not tool_calls:
                msg_done = json.dumps({"type": "done"})
                yield f"data: {msg_done}\n\n"
                break

            for tc in tool_calls:
                func_name = tc.get("function", {}).get("name", "")
                parse_error = None
                try:
                    func_args = parse_tool_arguments(
                        tc.get("function", {}).get("arguments", "{}")
                    )
                except Exception as e:
                    func_args = {}
                    parse_error = str(e)

                display_cmd = redact_text(str(func_args.get("command", str(func_args))))
                if parse_error:
                    display_cmd = "JSON解析失败: " + parse_error
                tc_id = tc.get("id", "")

                if parse_error:
                    tool_res = json.dumps(
                        {
                            "status": "ERROR",
                            "error_type": "tool_arguments_invalid",
                            "error": f"参数 JSON 格式无效，请检查是否包含未转义字符或格式错误: {parse_error}",
                            "hint": "请重新生成工具参数，复杂 PowerShell/SQL 片段需要正确转义。",
                        },
                        ensure_ascii=False,
                    )
                    msg_end, safe_tool_res = build_tool_end_event(tc_id, func_name, tool_res)
                    yield f"data: {msg_end}\n\n"
                    tool_msg = {"tool_call_id": tc_id, "role": "tool", "name": func_name, "content": safe_tool_res}
                    messages.append(tool_msg)
                    memory_db.append_message(session_id, tool_msg)
                    continue

                if func_name == "request_user_interaction":
                    payload = _build_interaction_payload(tc_id, func_args)
                    future = asyncio.Future()
                    dispatcher.pending_interactions[tc_id] = {
                        "future": future,
                        "session_id": session_id,
                    }
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    tool_res, safe_tool_res = await _wait_for_user_interaction(tc_id, payload, future)
                    tool_msg = {
                        "tool_call_id": tc_id,
                        "role": "tool",
                        "name": func_name,
                        "content": tool_res,
                    }
                    messages.append(tool_msg)
                    try:
                        interaction_result = json.loads(safe_tool_res)
                    except Exception:
                        interaction_result = {}
                    interaction_done = json.dumps(
                        {
                            "type": "user_interaction_done",
                            "request_id": tc_id,
                            "status": interaction_result.get("status") or "submitted",
                            "input_type": payload["input_type"],
                            "value": interaction_result.get("value") or "",
                            "label": interaction_result.get("label") or "",
                        },
                        ensure_ascii=False,
                    )
                    yield f"data: {interaction_done}\n\n"
                    memory_db.append_message(
                        session_id,
                        {
                            "tool_call_id": tc_id,
                            "role": "tool",
                            "name": func_name,
                            "content": safe_tool_res,
                        },
                    )
                    continue

                # ======== NEW APPROVAL LOGIC ========
                needs_approval, reason = dispatcher.check_approval_needed(func_name, func_args, context)
                approval_required = False
                
                if needs_approval:
                    approval_required = True
                    approval_record = record_tool_approval_request(
                        tool_call_id=tc_id,
                        session_id=session_id,
                        tool_name=func_name,
                        args=func_args,
                        reason=reason,
                        context=context,
                    )
                    policy_metadata = (approval_record.get("metadata") or {}).get("policy") or {}
                    msg_ask = json.dumps({
                        "type": "tool_ask_approval", 
                        "tool_call_id": tc_id, # for new React frontend
                        "tool_name": func_name, # for new React frontend
                        "args": display_cmd, # for new React frontend
                        "reason": reason,
                        "actions": policy_metadata.get("actions") or [],
                        "primary_action": policy_metadata.get("primary_action"),
                        "id": tc_id, 
                        "tool": func_name, 
                        "cmd": display_cmd
                    })
                    yield f"data: {msg_ask}\n\n"
                    
                    future = asyncio.Future()
                    dispatcher.pending_approvals[tc_id] = future
                    approval_timed_out = False
                    try:
                        approved = await asyncio.wait_for(future, timeout=float(approval_timeout_seconds()))
                    except asyncio.TimeoutError:
                        approved = False
                        approval_timed_out = True
                        try:
                            from core.approval_queue import mark_approval_timeout

                            mark_approval_timeout(tc_id)
                        except KeyError:
                            pass
                    
                    if tc_id in dispatcher.pending_approvals:
                        del dispatcher.pending_approvals[tc_id]
                        
                    if not approved:
                        tool_res = json.dumps(
                            {
                                "status": "BLOCKED",
                                "error_type": "approval_timeout" if approval_timed_out else "approval_rejected",
                                "error": "审批超时，工具调用已取消。" if approval_timed_out else "用户拒绝执行该工具调用。",
                                "hint": "如仍需执行，请重新发送任务并完成审批。" if approval_timed_out else "如需再次执行，请重新发送任务并选择批准。",
                            },
                            ensure_ascii=False,
                        )
                        msg_end, safe_tool_res = build_tool_end_event(tc_id, func_name, tool_res)
                        yield f"data: {msg_end}\n\n"
                        
                        tool_msg = {
                            "tool_call_id": tc_id,
                            "role": "tool",
                            "name": func_name,
                            "content": safe_tool_res,
                        }
                        messages.append(tool_msg)
                        memory_db.append_message(session_id, tool_msg)
                        continue
                # ====================================

                msg_start = json.dumps(
                    {
                        "type": "tool_start",
                        "id": tc_id,
                        "tool": func_name,
                        "cmd": display_cmd,
                    }
                )
                yield f"data: {msg_start}\n\n"
                await asyncio.sleep(0.05)

                tool_res = await dispatcher.route_and_execute(
                    func_name, func_args, context
                )
                if approval_required:
                    try:
                        from core.approval_queue import record_approval_execution

                        record_approval_execution(tc_id, tool_res)
                    except KeyError:
                        pass
                msg_end, safe_tool_res = build_tool_end_event(tc.get("id", ""), func_name, tool_res)
                yield f"data: {msg_end}\n\n"
                await asyncio.sleep(0.05)

                tool_msg = {
                    "tool_call_id": tc.get("id", ""),
                    "role": "tool",
                    "name": func_name,
                    "content": safe_tool_res,
                }
                messages.append(tool_msg)
                memory_db.append_message(session_id, tool_msg)

            msg_loop = json.dumps(
                {
                    "type": "status",
                    "content": f"🔄 收集结果，执行第 {iteration + 2} 步...",
                }
            )
            yield f"data: {msg_loop}\n\n"
            await asyncio.sleep(0.05)

        else:
            limit_status_payload = {
                "type": "status",
                "content": f"已达到 {max_steps} 步执行保护上限，正在整理阶段性报告...",
            }
            yield f"data: {json.dumps(limit_status_payload, ensure_ascii=False)}\n\n"

            summary_messages = messages + [
                {"role": "system", "content": agent_step_limit_instruction(max_steps)}
            ]
            summary_content = ""
            try:
                from core.llm_execution import execute_chat_stream

                async for chunk in execute_chat_stream(
                    model_name, summary_messages, "off", tools=None
                ):
                    if chunk["type"] == "content":
                        summary_content += chunk["content"]
                        yield f"data: {json.dumps({'type': 'chunk', 'content': chunk['content']}, ensure_ascii=False)}\n\n"
                    elif chunk["type"] == "thinking":
                        continue
                if not summary_content.strip():
                    summary_content = (
                        f"已达到 {max_steps} 步执行保护上限，系统已停止继续调用工具。"
                        "当前模型未能生成阶段性报告，请根据上方工具结果继续拆分任务。"
                    )
                    yield f"data: {json.dumps({'type': 'chunk', 'content': summary_content}, ensure_ascii=False)}\n\n"
            except Exception as summary_error:
                summary_content = (
                    f"已达到 {max_steps} 步执行保护上限，且阶段性报告生成失败：{summary_error}。"
                    "请将任务拆成更小范围后重试。"
                )
                yield f"data: {json.dumps({'type': 'chunk', 'content': summary_content}, ensure_ascii=False)}\n\n"

            safe_summary_msg = {"role": "assistant", "content": summary_content}
            messages.append(safe_summary_msg)
            memory_db.append_message(session_id, safe_summary_msg)
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        # ÿֶԻ׽󣬴ڼ첽ѹ (̨ǰ)
        asyncio.create_task(
            memory_db.compress_and_store_ltm(session_id, emb_client, embedding_model)
        )

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Agent Loop Failed: {error_msg}")
        if "timeout" in error_msg.lower() or "connect" in error_msg.lower():
            timeout_payload = {
                "type": "error",
                "content": "❌ **超时** 无法连接到 AI 模型接口\n\n"
                "**可能原因**\n1. 模型服务地址不可达\n2. API Key 或模型名称配置不正确",
            }
            yield f"data: {json.dumps(timeout_payload)}\n\n"
        else:
            error_payload = {
                "type": "error",
                "content": f"❌ AI 思考时发生异常，请稍后再试。详细信息：`{error_msg}`",
            }
            yield f"data: {json.dumps(error_payload)}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"


async def dispatch_group_tasks(tasks: list[dict], allow_mod: bool) -> list[dict]:
    """批量调度并执行一组任务"""
    # 强制执行最大并发度为 10，保护系统内存和API限制
    sem = asyncio.Semaphore(10)

    async def run_task(task):
        target_sid = task.get("target_session_id")
        task_desc = task.get("task_description")

        if not target_sid or not task_desc:
            return {
                "session_id": target_sid,
                "status": "ERROR",
                "error": "Invalid task definition",
            }

        from connections.ssh_manager import ssh_manager

        target_info = ssh_manager.active_sessions.get(target_sid, {}).get("info", {})
        target_name = target_info.get("remark") or target_info.get("host") or target_sid

        logger.warning(
            f"🤖 [Swarm 协同] 指挥官 Agent 正在向子会话 {target_name} ({target_sid}) 下达自然语言任务: {task_desc}"
        )

        try:
            # Set a strict 60s timeout per sub-agent to prevent hanging
            result = await asyncio.wait_for(
                headless_agent_chat(
                    target_sid,
                    task_desc,
                    inherited_allow_mod=allow_mod,
                ),
                timeout=60.0,
            )
            return {
                "session_id": target_sid,
                "status": "SUCCESS",
                "report": result,
            }
        except asyncio.TimeoutError:
            return {
                "session_id": target_sid,
                "status": "ERROR",
                "error": "跨域协同超时 (60秒) 被强行中断。",
            }
        except Exception as e:
            return {
                "session_id": target_sid,
                "status": "ERROR",
                "error": f"跨域协同异常: {str(e)}",
            }

    async def bound_run_task(task):
        async with sem:
            return await run_task(task)

    results = await asyncio.gather(*(bound_run_task(task) for task in tasks))
    return list(results)


async def headless_agent_chat(
    session_id: str,
    task_description: str,
    inherited_allow_mod: bool = False,
    model_name: str | None = None,
) -> str:
    """后台无头模式的 Agent 循环，用于协同任务的结果汇报。"""
    from connections.ssh_manager import ssh_manager
    from core.llm_factory import get_client_for_model, get_default_model_id

    if not model_name:
        model_name = get_default_model_id()
    client, _ = get_client_for_model(model_name)

    if session_id not in ssh_manager.active_sessions:
        return f"目标会话 {session_id} 不在线或已过期。"

    session_info = ssh_manager.active_sessions[session_id]["info"]
    # 继承父级 allow_modifications 并结合当前会话的权限，两者必须同时为 True 才允许
    allow_modifications = inherited_allow_mod and session_info.get(
        "allow_modifications", False
    )
    active_skills = session_info.get("active_skills", [])
    agent_profile = session_info.get("agent_profile", "default")
    asset_type = session_info.get("asset_type", "ssh")
    protocol = session_info.get("protocol", asset_type)
    is_virtual = session_info.get("is_virtual", False)
    host = session_info.get("host", "")
    port = session_info.get("port", "")
    username = session_info.get("username", "")
    extra_args = session_info.get("extra_args", {})
    password = session_info.get("password")

    profile_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "workspaces",
        agent_profile,
        "SOUL.md",
    )
    if os.path.exists(profile_path):
        with open(profile_path, "r", encoding="utf-8") as f:
            base_prompt = f.read()
    else:
        base_prompt = "你是 OpsCore 的高级 AI 运维专家。"

    extra_creds_str = format_extra_args_for_prompt(extra_args)
    active_skill_paths = dispatcher.get_active_skill_paths(active_skills)
    local_skill_scripts_allowed = allow_local_skill_scripts(protocol)

    SYSTEM_PROMPT = f"""{base_prompt}

[当前持有的资产凭证]
一台通过{protocol.upper()}协议纳管的 {asset_type.upper()} 资产：
- 目标IP/主机名: {host}
- 端口: {port}
- 账号: {username}
- 凭证信息: (已安全托管，底层工具执行时自动注入，无需在脚本中自行填写)\n{extra_creds_str}
{protocol_tool_guidance(protocol, asset_type, host)}

[上级指挥官委派的任务]
你是第一线的运维管理工程师调用的 Agent。
上级委派给你的任务是：
{task_description}

请在当前的会话（{host}）内，利用你的技能和工具，全力完成该任务。
在完成操作、修复或检查完成后，给出一份详细的「执行结果报告」。该报告将直接返回给上级指挥官作为你的工作内容。
真实资产会话中，不要说“无法通过本地脚本”“改用平台原生工具”这类解释；直接通过当前会话的原生协议工具执行。

[使用的基础执行工具]
{protocol_tool_list(protocol, local_skill_scripts_allowed and bool(active_skill_paths), asset_type)}
"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "请开始执行任务。"},
    ]

    context = {
        "session_id": session_id,
        "os_type": "linux",
        "allow_modifications": allow_modifications,
        "active_skills": active_skills,
        "active_skill_paths": active_skill_paths if local_skill_scripts_allowed else [],
        "asset_type": asset_type,
        "protocol": protocol,
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "extra_args": extra_args,
        "target_scope": session_info.get("target_scope", "asset"),
        "scope_value": session_info.get("scope_value", None),
        "execution_mode": "headless",
        "trigger_source": "background_agent",
    }
    tools = dispatcher.get_available_tools(context)

    try:
        from core.llm_execution import execute_chat_stream

        assistant_content = ""
        max_steps = agent_max_steps("headless")
        for iteration in range(max_steps):
            assistant_content = ""
            thinking_content = ""
            tool_calls = []

            async for chunk in execute_chat_stream(
                model_name, messages, "off", tools=tools
            ):
                if chunk["type"] == "thinking":
                    thinking_content += chunk["content"]
                elif chunk["type"] == "content":
                    assistant_content += chunk["content"]
                elif chunk["type"] == "tool_calls":
                    tool_calls = chunk["tool_calls"]

            if not tool_calls:
                break

            safe_msg = {"role": "assistant", "content": assistant_content}
            if thinking_content:
                safe_msg["reasoning_content"] = thinking_content
            safe_msg["tool_calls"] = tool_calls

            messages.append(safe_msg)

            for tc in tool_calls:
                func_name = tc.get("function", {}).get("name", "")
                try:
                    func_args = parse_tool_arguments(
                        tc.get("function", {}).get("arguments", "{}")
                    )
                except Exception:
                    func_args = {}

                needs_approval, reason = dispatcher.check_approval_needed(
                    func_name, func_args, context
                )
                if needs_approval:
                    blocked = record_headless_approval_block(
                        tool_call_id=tc.get("id", ""),
                        session_id=session_id,
                        tool_name=func_name,
                        args=func_args,
                        reason=reason,
                        context=context,
                    )
                    logger.warning(
                        "Blocked unattended tool call requiring approval: session=%s tool=%s approval=%s",
                        session_id,
                        func_name,
                        blocked.get("id"),
                    )
                    tool_res = json.dumps(
                        {
                            "status": "BLOCKED",
                            "error": f"后台自治任务触发审批策略，已自动阻断: {reason}",
                            "approval_id": blocked.get("id"),
                        },
                        ensure_ascii=False,
                    )
                else:
                    tool_res = await dispatcher.route_and_execute(
                        func_name, func_args, context
                    )

                tool_msg = {
                    "tool_call_id": tc.get("id", ""),
                    "role": "tool",
                    "name": func_name,
                    "content": str(tool_res),
                }
                messages.append(tool_msg)
        else:
            return (
                f"任务达到 {max_steps} 步执行保护上限，系统已停止继续调用工具。以下是最后一轮阶段性结果："
                + assistant_content
            )

        return (
            f"来自 {agent_profile} Agent ({host}) 的协同任务报告：\n"
            + assistant_content
        )
    except Exception as e:
        return f"协同任务执行失败。目标节点 {host} 执行报错: {e}"
