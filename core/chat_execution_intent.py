from __future__ import annotations

from dataclasses import dataclass
from typing import Any


EXECUTION_REQUEST_KEYWORDS = (
    "当前资产",
    "当前会话",
    "原生协议工具",
    "执行",
    "巡检",
    "检查",
    "查看",
    "查询",
    "排查",
    "诊断",
    "健康",
    "状态",
    "风险",
    "配置",
    "表空间",
    "锁",
    "慢 sql",
    "慢sql",
    "高耗",
    "sql",
)

NON_EXECUTION_TOOL_INFO_KEYWORDS = (
    "可用工具",
    "工具和正确使用边界",
    "说明当前资产",
    "解释当前",
)


@dataclass(frozen=True)
class ExecutionIntent:
    target_scope: str
    requires_live_evidence: bool
    allowed_tool_family: str
    reason: str
    source: str
    first_step_tool_names: tuple[str, ...] = ()


def _context_intent(context: dict[str, Any]) -> dict[str, Any]:
    value = context.get("execution_intent")
    return value if isinstance(value, dict) else {}


def classify_execution_intent(
    *,
    latest_user_text: str,
    context: dict[str, Any],
    native_tool_names: tuple[str, ...],
) -> ExecutionIntent:
    target_scope = str(context.get("target_scope") or "asset")
    protocol = str(context.get("protocol") or "").lower()
    explicit_intent = _context_intent(context)
    explicit_requires = explicit_intent.get("requires_live_evidence")

    if target_scope != "asset":
        return ExecutionIntent(target_scope, False, "none", "非资产会话不强制采集现场证据", "scope")
    if protocol == "virtual":
        return ExecutionIntent(target_scope, False, "none", "虚拟会话没有可强制的资产原生协议工具", "protocol")
    if not native_tool_names:
        return ExecutionIntent(target_scope, False, "none", "当前会话没有可用原生协议工具", "tool_registry")

    if explicit_requires is True:
        return ExecutionIntent(
            target_scope=target_scope,
            requires_live_evidence=True,
            allowed_tool_family=str(explicit_intent.get("allowed_tool_family") or "native_asset_protocol"),
            reason=str(explicit_intent.get("reason") or "上游会话声明本轮需要实时证据"),
            source=str(explicit_intent.get("source") or "context"),
            first_step_tool_names=native_tool_names,
        )
    if explicit_requires is False:
        return ExecutionIntent(
            target_scope=target_scope,
            requires_live_evidence=False,
            allowed_tool_family="none",
            reason=str(explicit_intent.get("reason") or "上游会话声明本轮不需要实时执行"),
            source=str(explicit_intent.get("source") or "context"),
            first_step_tool_names=native_tool_names,
        )

    text = latest_user_text.lower()
    if not text:
        return ExecutionIntent(target_scope, False, "none", "用户消息为空", "message")
    if any(keyword in text for keyword in NON_EXECUTION_TOOL_INFO_KEYWORDS):
        return ExecutionIntent(target_scope, False, "none", "用户是在询问工具边界或解释信息", "message")
    if any(keyword in text for keyword in EXECUTION_REQUEST_KEYWORDS):
        return ExecutionIntent(
            target_scope=target_scope,
            requires_live_evidence=True,
            allowed_tool_family="native_asset_protocol",
            reason="用户请求包含资产检查、查询、巡检或诊断意图",
            source="message_keywords",
            first_step_tool_names=native_tool_names,
        )

    return ExecutionIntent(target_scope, False, "none", "未识别到现场执行意图", "message")
