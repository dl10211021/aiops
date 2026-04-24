import os
import json
import asyncio
import logging
from core.dispatcher import dispatcher

cancel_flags = {}

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "models/gemini-embedding-001")
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "3072"))


async def get_available_models() -> list:
    try:
        from core.llm_factory import get_all_providers
        from openai import AsyncOpenAI
        import asyncio
        import logging
        
        providers = get_all_providers()
        
        async def fetch_provider_models(p):
            models_list = []
            manual_models = [m.strip() for m in p.get("models", "").split(",") if m.strip()]
            
            if manual_models:
                for m in manual_models:
                    models_list.append({"id": f"{p['id']}|{m}", "name": m})
            elif p.get("protocol") == "openai":
                try:
                    api_key = p.get("api_key")
                    if not api_key:
                        api_key = "dummy"
                        
                    base_url = p.get("base_url")
                    if not base_url:
                        base_url = "https://api.openai.com/v1"
                        
                    temp_client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=30.0)
                    response = await temp_client.models.list()
                    for m in response.data:
                        models_list.append({"id": f"{p['id']}|{m.id}", "name": m.id})
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Failed to fetch models for {p.get('name')}: {e}")
            
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
    model_name: str = "gemini-2.5-flash",
    thinking_mode: str = "off",
):
    cancel_flags[session_id] = False
    from connections.ssh_manager import ssh_manager
    from core.llm_factory import get_client_for_model

    emb_client, _ = get_client_for_model("gemini-2.5-flash")

    session_info = ssh_manager.active_sessions[session_id]["info"]
    allow_modifications = session_info.get("allow_modifications", False)
    active_skills = session_info.get("active_skills", [])
    agent_profile = session_info.get("agent_profile", "default")

    # 获取资产协议凭证信息，构建模型上下文
    asset_type = session_info.get("asset_type", "ssh")
    is_virtual = session_info.get("is_virtual", False)
    host = session_info.get("host", "")
    port = session_info.get("port", "")
    username = session_info.get("username", "")
    extra_args = session_info.get("extra_args", {})

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
        ltm_context = await memory_db.retrieve_ltm(session_id, user_message, emb_client)
    except Exception as e:
        logger.error(f"LTM retrieve error: {e}")
        ltm_context = ""

    # 凭证信息格式化为字符串 (已移除，防泄漏)

    SYSTEM_PROMPT = f"""
{base_prompt}

[当前持有的资产凭证]
一台通过{asset_type.upper()}协议纳管的资产：
- 目标IP/主机名: {host}
- 端口: {port}
- 账号: {username}
- 凭证信息: (已安全托管，底层工具执行时自动注入，无需在脚本中自行填写)\n{extra_creds_str}
{"⚠️ 注意：这是一个虚拟会话，请不要使用 `linux_execute_command`。你应该使用 `local_execute_script` 工具去执行本地的 Python 脚本来获取数据。" if is_virtual else "直接使用 `linux_execute_command` 执行 bash 命令。"}

[已知安全模式]
1. 用户动态加载的「可用Skills」决定了你「什么时候能调什么路」。仔细阅读已加载的技能说明！
2. 当前会话权限状态：{"**高级读写修改权限**：可以执行修改系统的操作" if allow_modifications else "**只读安全模式**：禁止修改系统的文件。除非用户强制要求，否则请确认后拒绝"}
3. 执行某些较高风险脚本时，请仔细参考技能说明中提供的 `<SKILL_ABSOLUTE_PATH>` 路径和 `cwd` 工作目录路径。不要自己凭空猜测目录。

[AIOps 专家行为准则 (CRITICAL)]
作为运维管理工程师现场助手级别的专业伙伴：
- **主动规划 (Proactive Planning)**：在接到运维操作任务时，明确列出操作思路和步骤 (Step 1, Step 2...)，不要盲目执行指令
- **根因分析 (Root Cause Analysis)**：不要肤浅地只看表面。要像一名工程师一样，一步一步深入地直接指向异常
- **闭环思维 (Closed-loop)**：操作、修复后自动执行修复验证确认修复
- **防死循环与边界 (Anti-Loop & Boundary)**：如果针对当前目标资产（{host}）连续执行工具 3 次依然失败（例如认证失败、网络超时），请【立即停止重试】，并将错误信息原本反馈给用户。绝不允许为了解决目标资产的问题，而去获取宿主机（你自身所在的机器）的信息作为替代，这会造成极大的误导。
- **自我进化与未知资产应对 (Self-Evolution)**：当用户要你「安装」「修复」「改」或「打一个新技能」时，不要说「没有权限」。使用 `evolve_skill` 去修复或变更你的代码。面对未知类型的设备，可使用 `local_execute_script` 动态生成脚本探测，但必须确保脚本是指向目标 {host} 的，而不是探测本机。

[使用的基础执行工具]
- linux_execute_command: 在远程的目标机器 {host} 上执行 bash 命令
- local_execute_script: 在本地执行 Python 或 Shell 脚本

[当前已加载专业技能说明 (Skills)]
以下是当前专业技能的详细 <INSTRUCTIONS> 指令，请严格遵照其中的步骤进行操作
{dispatcher.get_skill_instructions(active_skills)}

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
                yield f"data: {json.dumps({'type': 'error', 'content': '\u4efb\u52a1\u5df2\u88ab\u624b\u52a8\u4e2d\u6b62\u3002'})}\n\n"
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
                        yield f"data: {json.dumps({'type': 'chunk', 'content': '<think>\\n'})}\n\n"
                        is_thinking_stream = True
                    msg_chunk = json.dumps(
                        {"type": "chunk", "content": chunk["content"]}
                    )
                    yield f"data: {msg_chunk}\n\n"
                    thinking_content += chunk["content"]
                elif chunk["type"] == "content":
                    if is_thinking_stream:
                        yield f"data: {json.dumps({'type': 'chunk', 'content': '\\n</think>\\n'})}\n\n"
                        is_thinking_stream = False
                    msg_chunk = json.dumps(
                        {"type": "chunk", "content": chunk["content"]}
                    )
                    yield f"data: {msg_chunk}\n\n"
                    assistant_content += chunk["content"]
                elif chunk["type"] == "tool_calls":
                    if is_thinking_stream:
                        yield f"data: {json.dumps({'type': 'chunk', 'content': '\\n</think>\\n'})}\n\n"
                        is_thinking_stream = False
                    tool_calls = chunk["tool_calls"]

            if is_thinking_stream:
                yield f"data: {json.dumps({'type': 'chunk', 'content': '\\n</think>\\n'})}\n\n"
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

                display_cmd = func_args.get("command", str(func_args))
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
                    msg_ask = json.dumps({
                        "type": "tool_ask_approval", 
                        "tool_call_id": tc_id, # for new React frontend
                        "tool_name": func_name, # for new React frontend
                        "args": display_cmd, # for new React frontend
                        "id": tc_id, 
                        "tool": func_name, 
                        "cmd": display_cmd
                    })
                    yield f"data: {msg_ask}\n\n"
                    
                    future = asyncio.Future()
                    dispatcher.pending_approvals[tc_id] = future
                    try:
                        approved = await asyncio.wait_for(future, timeout=300.0) # wait up to 5 min
                    except asyncio.TimeoutError:
                        approved = False
                    
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

                preview = tool_res[:300] + "..." if len(tool_res) > 300 else tool_res
                msg_end = json.dumps(
                    {"type": "tool_end", "id": tc.get("id", ""), "result": preview}
                )
                yield f"data: {msg_end}\n\n"
                await asyncio.sleep(0.05)

                tool_msg = {
                    "tool_call_id": tc.get("id", ""),
                    "role": "tool",
                    "name": func_name,
                    "content": str(tool_res),
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
            yield f"data: {json.dumps({'type': 'error', 'content': '⚠️ 任务过于复杂，已达到 50 次最大思考上限，自动终止'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        # ÿֶԻ׽󣬴ڼ첽ѹ (̨ǰ)
        asyncio.create_task(
            memory_db.compress_and_store_ltm(session_id, emb_client)
        )

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Agent Loop Failed: {error_msg}")
        if "timeout" in error_msg.lower() or "connect" in error_msg.lower():
            yield f"data: {json.dumps({'type': 'error', 'content': '❌ **超时** 无法连接到 AI 模型接口(Google Gemini)\\n\\n**可能原因**\\n1. 你的网络无法直接访问 API\\n2. 代理设置有误'})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'error', 'content': f'❌ AI 思考时发生异常，请稍后再试。详细信息：`{error_msg}`'})}\n\n"
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
    model_name: str = "gemini-2.5-flash",
) -> str:
    """后台无头模式的 Agent 循环，用于协同任务的结果汇报。"""
    from connections.ssh_manager import ssh_manager
    from core.llm_factory import get_client_for_model

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
    is_virtual = session_info.get("is_virtual", False)
    host = session_info.get("host", "")
    port = session_info.get("port", "")
    username = session_info.get("username", "")
    extra_args = session_info.get("extra_args", {})

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

    extra_creds_str = "\\n".join([f"- {k}: {v}" for k, v in extra_args.items() if v])

    SYSTEM_PROMPT = f"""{base_prompt}

[当前持有的资产凭证]
一台通过{asset_type.upper()}协议纳管的资产：
- 目标IP/主机名: {host}
- 端口: {port}
- 账号: {username}
- 凭证信息: (已安全托管，底层工具执行时自动注入，无需在脚本中自行填写)\n{extra_creds_str}
{"⚠️ 注意：这是一个虚拟会话，请不要使用 `linux_execute_command`，应使用 `local_execute_script` 工具。" if is_virtual else "直接使用 `linux_execute_command` 执行 bash 命令。"}

[上级指挥官委派的任务]
你是第一线的运维管理工程师调用的 Agent。
上级委派给你的任务是：
{task_description}

请在当前的会话（{host}）内，利用你的技能和工具，全力完成该任务。
在完成操作、修复或检查完成后，给出一份详细的「执行结果报告」。该报告将直接返回给上级指挥官作为你的工作内容。
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
