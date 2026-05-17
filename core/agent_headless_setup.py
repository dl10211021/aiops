from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from core.agent_prompts import build_headless_prompt_manifest, render_headless_system_prompt
from core.agent_session_context import AgentSessionContext, build_agent_session_context
from core.agent_profiles import load_agent_profile_prompt


class HeadlessAgentDispatcher(Protocol):
    def get_active_skill_paths(self, active_skills: list[str]) -> list[str]:
        ...

    def get_available_tools(self, context: dict) -> list[dict]:
        ...


@dataclass(frozen=True)
class HeadlessAgentRun:
    model_name: str
    session_context: AgentSessionContext
    agent_profile: str
    host: str
    messages: list[dict]
    context: dict
    tools: list[dict]


def prepare_headless_agent_run(
    *,
    session_id: str,
    task_description: str,
    inherited_allow_mod: bool,
    model_name: str | None,
    active_sessions: dict[str, dict],
    dispatcher: HeadlessAgentDispatcher,
    default_model_resolver: Callable[[], str],
    model_client_resolver: Callable[[str], tuple[Any, Any]],
    profile_loader: Callable[[str], str] = load_agent_profile_prompt,
) -> HeadlessAgentRun | None:
    if not model_name:
        model_name = default_model_resolver()

    _client, _ = model_client_resolver(model_name)

    if session_id not in active_sessions:
        return None

    session_info = active_sessions[session_id]["info"]
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
    base_prompt = profile_loader(agent_profile)

    system_prompt = render_headless_system_prompt(
        session_context=session_context,
        base_prompt=base_prompt,
        task_description=task_description,
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "请开始执行任务。"},
    ]
    context = session_context.tool_context(
        execution_mode="headless",
        trigger_source="background_agent",
    )
    context["prompt_modules"] = build_headless_prompt_manifest(
        session_context=session_context,
    )
    tools = dispatcher.get_available_tools(context)

    return HeadlessAgentRun(
        model_name=model_name,
        session_context=session_context,
        agent_profile=agent_profile,
        host=host,
        messages=messages,
        context=context,
        tools=tools,
    )
