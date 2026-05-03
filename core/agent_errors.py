from __future__ import annotations


def build_agent_loop_error_payload(error_msg: str) -> dict:
    if "timeout" in error_msg.lower() or "connect" in error_msg.lower():
        return {
            "type": "error",
            "content": "❌ **超时** 无法连接到 AI 模型接口\n\n"
            "**可能原因**\n1. 模型服务地址不可达\n2. API Key 或模型名称配置不正确",
        }
    return {
        "type": "error",
        "content": f"❌ AI 思考时发生异常，请稍后再试。详细信息：`{error_msg}`",
    }
