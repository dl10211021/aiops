from __future__ import annotations

import logging
import os


logger = logging.getLogger(__name__)

DEFAULT_AGENT_MAX_STEPS = 80
DEFAULT_HEADLESS_AGENT_MAX_STEPS = 60
MIN_AGENT_STEP_CAP = 10
MAX_AGENT_STEP_CAP = 200


def clamp_agent_max_steps(value: int, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(MIN_AGENT_STEP_CAP, min(number, MAX_AGENT_STEP_CAP))


def _bounded_int_env(
    name: str,
    default: int,
    minimum: int = MIN_AGENT_STEP_CAP,
    maximum: int = MAX_AGENT_STEP_CAP,
) -> int:
    raw_value = os.environ.get(name)
    if raw_value is None or str(raw_value).strip() == "":
        return default
    try:
        value = int(str(raw_value).strip())
    except (TypeError, ValueError):
        logger.warning("Invalid integer env %s=%r, using default %s", name, raw_value, default)
        return default
    return max(minimum, min(value, maximum))


def agent_max_steps(execution_mode: str = "chat") -> int:
    if execution_mode == "headless":
        return _bounded_int_env(
            "OPSCORE_HEADLESS_AGENT_MAX_STEPS",
            _bounded_int_env("OPSCORE_AGENT_MAX_STEPS", DEFAULT_HEADLESS_AGENT_MAX_STEPS),
        )
    return _bounded_int_env("OPSCORE_AGENT_MAX_STEPS", DEFAULT_AGENT_MAX_STEPS)


def get_agent_runtime_config() -> dict:
    return {
        "chat_max_steps": agent_max_steps("chat"),
        "headless_max_steps": agent_max_steps("headless"),
        "min_steps": MIN_AGENT_STEP_CAP,
        "max_steps": MAX_AGENT_STEP_CAP,
        "defaults": {
            "chat_max_steps": DEFAULT_AGENT_MAX_STEPS,
            "headless_max_steps": DEFAULT_HEADLESS_AGENT_MAX_STEPS,
        },
        "env_keys": {
            "chat_max_steps": "OPSCORE_AGENT_MAX_STEPS",
            "headless_max_steps": "OPSCORE_HEADLESS_AGENT_MAX_STEPS",
        },
    }


def update_agent_runtime_config(chat_max_steps: int, headless_max_steps: int) -> dict:
    chat_steps = clamp_agent_max_steps(chat_max_steps, DEFAULT_AGENT_MAX_STEPS)
    headless_steps = clamp_agent_max_steps(
        headless_max_steps,
        DEFAULT_HEADLESS_AGENT_MAX_STEPS,
    )
    os.environ["OPSCORE_AGENT_MAX_STEPS"] = str(chat_steps)
    os.environ["OPSCORE_HEADLESS_AGENT_MAX_STEPS"] = str(headless_steps)
    return get_agent_runtime_config()


def agent_step_limit_instruction(max_steps: int) -> str:
    return (
        f"OpsCore 已达到 {max_steps} 步执行保护上限。"
        "现在必须停止继续调用任何工具，直接基于已有对话和工具返回输出阶段性运维报告。"
        "报告需要包含：已完成检查、关键发现、风险等级、未完成项目、下一步建议。"
        "如果信息不足，要明确说明缺口，不要假装已完成。"
    )
