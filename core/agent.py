import asyncio
import logging
from core.dispatcher import dispatcher
from core.agent_errors import build_agent_loop_error_payload
from core.agent_headless_loop import run_headless_agent_loop
from core.agent_headless_setup import prepare_headless_agent_run
from core.agent_chat_setup import prepare_chat_agent_run
from core.agent_ltm import schedule_ltm_compression
from core.agent_runtime_config import (
    DEFAULT_AGENT_MAX_STEPS,
    DEFAULT_HEADLESS_AGENT_MAX_STEPS,
    MAX_AGENT_STEP_CAP,
    MIN_AGENT_STEP_CAP,
    agent_max_steps,
    clamp_agent_max_steps,
    get_agent_runtime_config,
    update_agent_runtime_config,
)
from core.agent_sse import sse_event
from core.agent_step_summary import stream_step_limit_summary
from core.agent_streaming import AgentStreamState, stream_assistant_response
from core.agent_tool_loop import process_chat_tool_calls
from core.agent_task_dispatch import dispatch_group_tasks as run_group_tasks
from core.model_catalog import get_available_models, get_available_models_for_provider
from core.embedding_config import (
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    get_embedding_config,
    update_embedding_config,
)

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
    from core.llm_factory import get_default_model_id, get_embedding_client_and_model

    run = await prepare_chat_agent_run(
        session_id=session_id,
        user_message=user_message,
        user_display_message=user_display_message,
        model_name=model_name,
        user_attachments=user_attachments,
        active_sessions=ssh_manager.active_sessions,
        dispatcher=dispatcher,
        memory_store=memory_db,
        event_logger=logger,
        default_model_resolver=get_default_model_id,
        embedding_resolver=get_embedding_client_and_model,
    )
    model_name = run.model_name
    emb_client = run.embedding_client
    embedding_model = run.embedding_model
    messages = run.messages
    context = run.context
    tools = run.tools

    try:
        # Initial status
        yield sse_event({"type": "status", "content": "🤖 AI 正在分析并规划执行路径..."})
        await asyncio.sleep(0.05)

        max_steps = agent_max_steps("chat")
        for iteration in range(max_steps):
            logger.info(
                f"Loop {iteration} for {session_id}, cancel_flags: {cancel_flags.get(session_id)}"
            )
            if cancel_flags.get(session_id) is True:
                cancel_flags[session_id] = False
                cancel_payload = {"type": "error", "content": "任务已被手动中止。"}
                yield sse_event(cancel_payload)
                yield sse_event({"type": "done"})
                break

            yield sse_event({"type": "status", "content": "💭 思考中..."})

            stream_state = AgentStreamState()
            async for event in stream_assistant_response(
                model_name=model_name,
                messages=messages,
                thinking_mode=thinking_mode,
                tools=tools,
                state=stream_state,
                cancel_requested=lambda: cancel_flags.get(session_id) is True,
            ):
                yield event

            tool_calls = stream_state.tool_calls
            safe_msg = stream_state.assistant_message()
            messages.append(safe_msg)
            memory_db.append_message(session_id, safe_msg)

            if not tool_calls:
                yield sse_event({"type": "done"})
                break

            async for event in process_chat_tool_calls(
                tool_calls=tool_calls,
                session_id=session_id,
                messages=messages,
                memory_store=memory_db,
                dispatcher=dispatcher,
                context=context,
                iteration=iteration,
            ):
                yield event

        else:
            async for event in stream_step_limit_summary(
                model_name=model_name,
                messages=messages,
                session_id=session_id,
                max_steps=max_steps,
                memory_store=memory_db,
            ):
                yield event

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
        yield sse_event(error_payload)
        yield sse_event({"type": "done"})


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

    run = prepare_headless_agent_run(
        session_id=session_id,
        task_description=task_description,
        inherited_allow_mod=inherited_allow_mod,
        model_name=model_name,
        active_sessions=ssh_manager.active_sessions,
        dispatcher=dispatcher,
        default_model_resolver=get_default_model_id,
        model_client_resolver=get_client_for_model,
    )

    if run is None:
        return f"目标会话 {session_id} 不在线或已过期。"

    try:
        return await run_headless_agent_loop(
            model_name=run.model_name,
            messages=run.messages,
            tools=run.tools,
            context=run.context,
            session_id=session_id,
            agent_profile=run.agent_profile,
            host=run.host,
            dispatcher=dispatcher,
            event_logger=logger,
        )
    except Exception as e:
        return f"协同任务执行失败。目标节点 {run.host} 执行报错: {e}"
