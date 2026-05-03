import json
import asyncio
import logging
from core.dispatcher import dispatcher
from core.agent_approval import (
    record_headless_approval_block,
    record_tool_approval_request,
)
from core.agent_errors import build_agent_loop_error_payload
from core.agent_interactions import (
    _build_interaction_payload,
    _normalize_interaction_options,
    _wait_for_user_interaction,
)
from core.agent_ltm import retrieve_ltm_context, schedule_ltm_compression
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
from core.agent_message_history import build_chat_message_history
from core.agent_prompts import (
    render_chat_system_prompt,
    render_headless_system_prompt,
)
from core.agent_session_context import build_agent_session_context
from core.agent_task_dispatch import dispatch_group_tasks as run_group_tasks
from core.agent_tool_events import (
    build_tool_end_event,
    parse_tool_arguments,
    summarize_tool_result_for_sse,
)
from core.agent_profiles import load_agent_profile_prompt
from core.model_catalog import get_available_models, get_available_models_for_provider
from core.embedding_config import (
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    get_embedding_config,
    update_embedding_config,
)
from core.redaction import redact_text
from core.safety_policy import approval_timeout_seconds

cancel_flags = {}

logger = logging.getLogger(__name__)

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
    session_context = build_agent_session_context(
        session_id,
        session_info,
        skill_path_resolver=dispatcher.get_active_skill_paths,
    )
    active_skills = session_context.active_skills
    agent_profile = session_context.agent_profile

    # 从外部 Markdown 文件加载 Agent 的核心人格 (Soul)
    base_prompt = load_agent_profile_prompt(agent_profile)

    ltm_context = await retrieve_ltm_context(
        memory_store=memory_db,
        session_id=session_id,
        user_message=user_message,
        emb_client=emb_client,
        embedding_model=embedding_model,
        event_logger=logger,
    )

    SYSTEM_PROMPT = render_chat_system_prompt(
        session_context=session_context,
        base_prompt=base_prompt,
        skill_instructions=dispatcher.get_skill_instructions(
            active_skills,
            allow_local_scripts=session_context.local_skill_scripts_allowed,
        ),
        ltm_context=ltm_context,
    )

    messages = build_chat_message_history(
        memory_store=memory_db,
        session_id=session_id,
        system_prompt=SYSTEM_PROMPT,
        user_message=user_message,
        user_display_message=user_display_message,
        user_attachments=user_attachments or [],
        model_name=model_name,
    )

    context = session_context.tool_context()
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

        schedule_ltm_compression(
            memory_store=memory_db,
            session_id=session_id,
            emb_client=emb_client,
            embedding_model=embedding_model,
        )

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Agent Loop Failed: {error_msg}")
        error_payload = build_agent_loop_error_payload(error_msg)
        yield f"data: {json.dumps(error_payload)}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"


async def dispatch_group_tasks(tasks: list[dict], allow_mod: bool) -> list[dict]:
    """批量调度并执行一组任务"""
    async def run_headless_task(
        target_sid: str,
        task_desc: str,
        inherited_allow_mod: bool,
    ) -> str:
        return await headless_agent_chat(
            target_sid,
            task_desc,
            inherited_allow_mod=inherited_allow_mod,
        )

    return await run_group_tasks(
        tasks,
        allow_mod,
        task_runner=run_headless_task,
        event_logger=logger,
    )


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
    session_context = build_agent_session_context(
        session_id,
        session_info,
        skill_path_resolver=dispatcher.get_active_skill_paths,
        allow_modifications=(
            inherited_allow_mod and session_info.get("allow_modifications", False)
        ),
    )
    agent_profile = session_context.agent_profile
    host = session_context.host

    base_prompt = load_agent_profile_prompt(agent_profile)

    SYSTEM_PROMPT = render_headless_system_prompt(
        session_context=session_context,
        base_prompt=base_prompt,
        task_description=task_description,
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "请开始执行任务。"},
    ]

    context = session_context.tool_context(
        execution_mode="headless",
        trigger_source="background_agent",
    )
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
