"""Backend-driven slash command catalog for AIOps sessions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SlashCommand:
    id: str
    label: str
    description: str
    prompt_template: str
    category: str = "ops"

    def render(self, context: dict[str, Any], active_tools: list[str] | None = None) -> dict[str, Any]:
        target = "{asset_type}/{protocol} {host}".format(
            asset_type=context.get("asset_type") or "asset",
            protocol=context.get("protocol") or "protocol",
            host=context.get("host") or "",
        ).strip()
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "category": self.category,
            "prompt": self.prompt_template.format(
                target=target,
                tool_list=", ".join(active_tools or []) or "当前会话原生协议工具",
            ),
        }


COMMANDS = [
    SlashCommand(
        "inspect",
        "/inspect 只读巡检",
        "按当前协议执行系统、数据库、容器、网络或平台巡检",
        "请对当前资产 {target} 执行一次完整只读巡检。必须使用当前会话的原生协议工具，不要使用本地脚本。输出包括：关键健康状态、异常项、风险等级、建议下一步。",
    ),
    SlashCommand(
        "config",
        "/config 当前配置",
        "查看实例关键配置和运行参数",
        "请查看当前资产 {target} 的关键配置信息。必须使用当前会话的原生协议工具，不要重新登录或要求我提供账号密码。请按“基础信息、资源/版本、网络/监听、关键配置、异常项”输出。",
    ),
    SlashCommand(
        "status",
        "/status 当前状态",
        "快速确认在线状态、核心指标和告警线索",
        "请快速检查当前资产 {target} 的运行状态。优先返回在线性、核心服务/实例状态、资源使用率、近期错误或告警线索。",
    ),
    SlashCommand(
        "tools",
        "/tools 可用工具",
        "解释当前会话启用的工具和安全边界",
        "请说明当前资产 {target} 已启用的工具和正确使用边界。当前工具包括：{tool_list}。请特别说明哪些操作只读可执行，哪些需要审批或会被硬拦截。",
    ),
    SlashCommand(
        "risk",
        "/risk 风险排查",
        "只读模式下做安全和稳定性风险扫描",
        "请在只读模式下对当前资产 {target} 做风险排查。禁止修改配置、重启服务、删除文件或写入数据。请输出高风险、中风险、低风险和需要人工确认的事项。",
    ),
    SlashCommand(
        "capacity",
        "/capacity 容量分析",
        "分析资源容量、水位、趋势和扩容风险",
        "请对当前资产 {target} 做容量分析。优先检查 CPU、内存、磁盘、数据库空间、Pod/节点资源或平台容量，并给出未来风险和扩容建议。",
    ),
]


def render_slash_commands(context: dict[str, Any], active_tools: list[str] | None = None) -> list[dict[str, Any]]:
    return [command.render(context, active_tools) for command in COMMANDS]
