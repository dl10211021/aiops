from __future__ import annotations

import os


DEFAULT_AGENT_PROFILE_PROMPT = "你是 OpsCore 的高级 AI 运维专家。"


def agent_profile_path(agent_profile: str) -> str:
    return os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "workspaces",
        agent_profile,
        "SOUL.md",
    )


def load_agent_profile_prompt(agent_profile: str) -> str:
    profile_path = agent_profile_path(agent_profile)
    if os.path.exists(profile_path):
        with open(profile_path, "r", encoding="utf-8") as profile_file:
            return profile_file.read()
    return DEFAULT_AGENT_PROFILE_PROMPT
