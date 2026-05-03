from __future__ import annotations

from typing import Protocol

from core.agent_attachments import (
    _build_current_user_content,
    _safe_user_message_for_memory,
)


class AgentMemoryStore(Protocol):
    def get_messages(self, session_id: str) -> list[dict]:
        ...

    def append_message(self, session_id: str, message: dict) -> None:
        ...


def build_chat_message_history(
    *,
    memory_store: AgentMemoryStore,
    session_id: str,
    system_prompt: str,
    user_message: str,
    user_display_message: str | None,
    user_attachments: list[dict],
    model_name: str | None,
) -> list[dict]:
    messages = [{"role": "system", "content": system_prompt}]

    for msg in memory_store.get_messages(session_id):
        if msg.get("role") != "system":
            messages.append(msg)

    current_user_content = _build_current_user_content(
        user_message,
        user_attachments,
        model_name,
    )
    safe_user_msg = _safe_user_message_for_memory(
        user_display_message or user_message,
        user_attachments,
    )
    new_user_msg = {"role": "user", "content": current_user_content}
    memory_store.append_message(session_id, safe_user_msg)
    messages.append(new_user_msg)
    return messages
