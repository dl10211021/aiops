from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from core.agent_protocol_context import allow_local_skill_scripts
from core.session_groups import DEFAULT_SESSION_GROUP, normalize_session_group_name


SkillPathResolver = Callable[[list[str]], list[str]]


@dataclass(frozen=True)
class AgentSessionContext:
    session_id: str
    allow_modifications: bool
    active_skills: list[str]
    agent_profile: str
    asset_type: str
    protocol: str
    is_virtual: bool
    host: str
    port: Any
    username: str
    password: Any
    extra_args: dict[str, Any]
    group_name: str
    tags: list[str]
    target_scope: str
    scope_value: Any
    active_skill_paths: list[str]
    local_skill_scripts_allowed: bool

    @property
    def has_local_skill_scripts(self) -> bool:
        return self.local_skill_scripts_allowed and bool(self.active_skill_paths)

    def tool_context(
        self,
        *,
        execution_mode: str | None = None,
        trigger_source: str | None = None,
    ) -> dict[str, Any]:
        context = {
            "session_id": self.session_id,
            "os_type": "linux",
            "allow_modifications": self.allow_modifications,
            "session_mode": "readwrite" if self.allow_modifications else "readonly",
            "active_skills": self.active_skills,
            "active_skill_paths": (
                self.active_skill_paths if self.local_skill_scripts_allowed else []
            ),
            "asset_type": self.asset_type,
            "protocol": self.protocol,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "extra_args": self.extra_args,
            "group_name": self.group_name,
            "tags": self.tags,
            "target_scope": self.target_scope,
            "scope_value": self.scope_value,
            "memory_scope_ids": self.memory_scope_ids(),
        }
        if execution_mode is not None:
            context["execution_mode"] = execution_mode
        if trigger_source is not None:
            context["trigger_source"] = trigger_source
        return context

    def memory_scope_ids(self) -> list[str]:
        """Return the only long-term memory scope allowed for this chat session.

        Knowledge base/RAG content is shared through its own retrieval path.
        Conversation memory is intentionally isolated per session to prevent
        another round, host, or asset-kind memory from affecting this session.
        """
        session_scope = str(self.session_id or "").strip().lower()
        return [session_scope] if session_scope else []


def build_agent_session_context(
    session_id: str,
    session_info: dict[str, Any],
    *,
    skill_path_resolver: SkillPathResolver,
    allow_modifications: bool | None = None,
) -> AgentSessionContext:
    active_skills = session_info.get("active_skills", [])
    asset_type = session_info.get("asset_type", "ssh")
    protocol = session_info.get("protocol", asset_type)
    local_skill_scripts_allowed = allow_local_skill_scripts(protocol)
    tags = list(session_info.get("tags") or [DEFAULT_SESSION_GROUP])
    group_name = normalize_session_group_name(tags[0] if tags else DEFAULT_SESSION_GROUP) or DEFAULT_SESSION_GROUP

    return AgentSessionContext(
        session_id=session_id,
        allow_modifications=(
            session_info.get("allow_modifications", False)
            if allow_modifications is None
            else allow_modifications
        ),
        active_skills=active_skills,
        agent_profile=session_info.get("agent_profile", "default"),
        asset_type=asset_type,
        protocol=protocol,
        is_virtual=session_info.get("is_virtual", False),
        host=session_info.get("host", ""),
        port=session_info.get("port", ""),
        username=session_info.get("username", ""),
        password=session_info.get("password"),
        extra_args=session_info.get("extra_args", {}),
        group_name=group_name,
        tags=tags,
        target_scope=session_info.get("target_scope", "asset"),
        scope_value=session_info.get("scope_value", None),
        active_skill_paths=skill_path_resolver(active_skills),
        local_skill_scripts_allowed=local_skill_scripts_allowed,
    )
