import os
import json
import asyncio
import logging
from core.dispatcher import dispatcher
from core.asset_protocols import API_PROTOCOLS, SQL_PROTOCOLS, normalize_protocol
from core.redaction import redact_json_text, redact_text
from core.safety_policy import approval_timeout_seconds
from core.tool_registry import tool_registry

cancel_flags = {}

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "")
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "3072"))
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


def record_tool_approval_request(
    *,
    tool_call_id: str,
    session_id: str,
    tool_name: str,
    args: dict,
    reason: str,
    context: dict,
) -> dict:
    from core.approval_queue import record_approval_request

    return record_approval_request(
        tool_call_id=tool_call_id,
        session_id=session_id,
        tool_name=tool_name,
        args=args,
        reason=reason,
        context=context,
        timeout_seconds=approval_timeout_seconds(),
    )


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
    if protocol == "ssh":
        return (
            f"连接状态：后端已经建立到目标 {host} 的 SSH 会话。你已经在该资产上下文内，"
            "直接调用 `linux_execute_command` 执行巡检命令；不要再编写连接脚本或尝试重新登录。"
        )
    if protocol == "winrm":
        return (
            f"连接状态：后端已经建立到 Windows 目标 {host} 的 WinRM 会话。你已经在该系统上下文内，"
            "直接调用 `winrm_execute_command` 执行 PowerShell/CMD 巡检；不要再编写 WinRM/Python 连接脚本，"
            "也不要向用户解释“无法通过本地脚本”。"
        )
    if protocol in SQL_PROTOCOLS:
        return (
            f"连接状态：后端已经建立到 {asset_type.upper()} 数据库 {host} 的托管会话。"
            "你当前连接的是数据库实例，不是操作系统 Shell；直接调用 `db_execute_query` 执行 SQL 巡检，"
            "不要在工具参数里填写 host/user/password，也不要尝试 SSH/WinRM 登录。"
        )
    if protocol == "redis":
        return "当前 Redis 资产使用 `redis_execute_command`，凭据由资产中心托管注入。"
    if protocol == "mongodb":
        return "当前 MongoDB 资产使用 `mongodb_find` 做只读查询，凭据由资产中心托管注入。"
    if protocol in API_PROTOCOLS:
        return (
            "当前 API/监控/虚拟化资产使用 `http_api_request` 调用目标 API；"
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


def update_embedding_config(model: str, dim: int):
    global EMBEDDING_MODEL, EMBEDDING_DIM
    EMBEDDING_MODEL = model
    EMBEDDING_DIM = dim
    logger.info(f"Embedding config updated: model={model}, dim={dim}")


def get_embedding_config():
    return EMBEDDING_MODEL, EMBEDDING_DIM


# 从 SQLite 持久化用户模型
from core.memory import memory_db


async def chat_stream_agent(
    session_id: str,
    user_message: str,
    model_name: str | None = None,
    thinking_mode: str = "off",
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

    # µһûʴݿ
    new_user_msg = {"role": "user", "content": user_message}
    memory_db.append_message(session_id, new_user_msg)
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

        for iteration in range(50):  # չ 50
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
                    func_args = json.loads(
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
                    tool_res = json.dumps({"status": "ERROR", "error": f"参数 JSON 格式无效，请检查是否包含未转义字符或格式错误: {parse_error}"})
                    msg_end = json.dumps({"type": "tool_end", "id": tc_id, "result": "❌ JSON解析错误"})
                    yield f"data: {msg_end}\n\n"
                    tool_msg = {"tool_call_id": tc_id, "role": "tool", "name": func_name, "content": tool_res}
                    messages.append(tool_msg)
                    memory_db.append_message(session_id, tool_msg)
                    continue

                # ======== NEW APPROVAL LOGIC ========
                needs_approval, reason = dispatcher.check_approval_needed(func_name, func_args, context)
                
                if needs_approval:
                    record_tool_approval_request(
                        tool_call_id=tc_id,
                        session_id=session_id,
                        tool_name=func_name,
                        args=func_args,
                        reason=reason,
                        context=context,
                    )
                    msg_ask = json.dumps({
                        "type": "tool_ask_approval", 
                        "tool_call_id": tc_id, # for new React frontend
                        "tool_name": func_name, # for new React frontend
                        "args": display_cmd, # for new React frontend
                        "reason": reason,
                        "id": tc_id, 
                        "tool": func_name, 
                        "cmd": display_cmd
                    })
                    yield f"data: {msg_ask}\n\n"
                    
                    future = asyncio.Future()
                    dispatcher.pending_approvals[tc_id] = future
                    try:
                        approved = await asyncio.wait_for(future, timeout=float(approval_timeout_seconds()))
                    except asyncio.TimeoutError:
                        approved = False
                        try:
                            from core.approval_queue import mark_approval_timeout

                            mark_approval_timeout(tc_id)
                        except KeyError:
                            pass
                    
                    if tc_id in dispatcher.pending_approvals:
                        del dispatcher.pending_approvals[tc_id]
                        
                    if not approved:
                        tool_res = '{"status": "BLOCKED", "error": "User rejected this execution."}'
                        msg_end = json.dumps(
                            {"type": "tool_end", "id": tc_id, "result": "❌ 已被用户拦截"}
                        )
                        yield f"data: {msg_end}\n\n"
                        
                        tool_msg = {
                            "tool_call_id": tc_id,
                            "role": "tool",
                            "name": func_name,
                            "content": tool_res,
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
                safe_tool_res = redact_json_text(str(tool_res))

                preview = safe_tool_res[:300] + "..." if len(safe_tool_res) > 300 else safe_tool_res
                msg_end = json.dumps(
                    {"type": "tool_end", "id": tc.get("id", ""), "result": preview}
                )
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
            max_steps_payload = {
                "type": "error",
                "content": "⚠️ 任务过于复杂，已达到 50 次最大思考上限，自动终止",
            }
            yield f"data: {json.dumps(max_steps_payload)}\n\n"
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
    }
    tools = dispatcher.get_available_tools(context)

    try:
        from core.llm_execution import execute_chat_stream

        assistant_content = ""
        for iteration in range(50):
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
                    func_args = json.loads(
                        tc.get("function", {}).get("arguments", "{}")
                    )
                except Exception:
                    func_args = {}

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
                "任务过于复杂，Agent 执行已达到 50 轮上限，已被强制终止。以下是最后一轮结果："
                + assistant_content
            )

        return (
            f"来自 {agent_profile} Agent ({host}) 的协同任务报告：\n"
            + assistant_content
        )
    except Exception as e:
        return f"协同任务执行失败。目标节点 {host} 执行报错: {e}"
