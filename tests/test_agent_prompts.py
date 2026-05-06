import unittest
from unittest.mock import patch

from core.agent_prompts import (
    render_chat_system_prompt,
    render_headless_system_prompt,
)
from core.agent_session_context import build_agent_session_context


class AgentPromptTests(unittest.TestCase):
    def _session_context(self, protocol: str = "ssh", asset_type: str | None = None):
        resolved_asset_type = asset_type or ("virtual" if protocol == "virtual" else "linux")
        return build_agent_session_context(
            "sid-prompt",
            {
                "asset_type": resolved_asset_type,
                "protocol": protocol,
                "host": "ops.local",
                "port": 22,
                "username": "ops",
                "allow_modifications": False,
                "active_skills": ["diagnose"],
                "extra_args": {"api_token": "secret-token", "region": "cn"},
            },
            skill_path_resolver=lambda active_skills: [
                f"D:/skills/{name}" for name in active_skills
            ],
        )

    @patch("core.agent_prompts.protocol_tool_list")
    @patch("core.agent_prompts.protocol_tool_guidance")
    @patch("core.agent_prompts.format_extra_args_for_prompt")
    def test_chat_prompt_keeps_credentials_tools_skills_and_memory_sections(
        self,
        format_extra_args,
        protocol_guidance,
        protocol_tool_list,
    ):
        format_extra_args.return_value = "- api_token: (已托管，执行时自动注入)"
        protocol_guidance.return_value = "GUIDANCE"
        protocol_tool_list.return_value = "TOOLS"

        prompt = render_chat_system_prompt(
            session_context=self._session_context(),
            base_prompt="BASE",
            skill_instructions="<INSTRUCTIONS>check</INSTRUCTIONS>",
            ltm_context="LTM-CONTEXT",
        )

        self.assertTrue(prompt.startswith("\nBASE\n\n[当前会话上下文]"))
        self.assertIn("会话类型：SSH / Linux-Unix 终端会话", prompt)
        self.assertIn("资产识别：Linux / Unix（类型 linux，分类 操作系统，协议 ssh）", prompt)
        self.assertIn("不要假设所有会话都是 SSH", prompt)
        self.assertIn("一台通过SSH协议纳管的 LINUX 资产", prompt)
        self.assertIn("- api_token: (已托管，执行时自动注入)", prompt)
        self.assertIn("**只读巡检模式**", prompt)
        self.assertIn("[当前已加载专业技能说明 (Skills)]", prompt)
        self.assertIn("<INSTRUCTIONS>check</INSTRUCTIONS>", prompt)
        self.assertIn("LTM-CONTEXT", prompt)
        self.assertIn("[上下文优先级]", prompt)
        self.assertIn("资产画像提示词", prompt)
        self.assertLess(prompt.index("LTM-CONTEXT"), prompt.index("[上下文优先级]"))
        protocol_tool_list.assert_called_once_with("ssh", False, "linux")

    def test_chat_prompt_declares_profile_and_current_evidence_over_ltm(self):
        prompt = render_chat_system_prompt(
            session_context=self._session_context(),
            base_prompt="BASE",
            skill_instructions="SKILL",
            asset_profile_prompt="[资产画像提示词]\n安全状态：UFW active",
            ltm_context="历史记忆：UFW 未启用",
        )

        self.assertIn("长期记忆只是历史经验", prompt)
        self.assertIn("当前原生协议工具结果", prompt)
        self.assertIn("资产画像提示词", prompt)
        self.assertLess(prompt.index("历史记忆：UFW 未启用"), prompt.index("[上下文优先级]"))

    def test_chat_prompt_uses_database_session_context_without_ssh_assumption(self):
        prompt = render_chat_system_prompt(
            session_context=self._session_context(protocol="oracle", asset_type="oracle"),
            base_prompt="BASE",
            skill_instructions="SKILL",
            ltm_context="",
        )

        self.assertIn("会话类型：Oracle 数据库会话", prompt)
        self.assertIn("资产识别：Oracle（类型 oracle，分类 数据库，协议 oracle）", prompt)
        self.assertIn("一台通过ORACLE协议纳管的 ORACLE 资产", prompt)
        self.assertNotIn("目前你正处于一个 SSH 终端会话", prompt)

    def test_chat_prompt_preserves_custom_asset_identity_fields(self):
        context = build_agent_session_context(
            "sid-custom-asset",
            {
                "asset_type": "nebula_graph_cluster",
                "protocol": "nebula_graph",
                "host": "graph.local",
                "port": 9669,
                "username": "graph",
                "allow_modifications": False,
                "active_skills": [],
                "extra_args": {
                    "category": "db",
                    "sub_type": "nebula_graph_cluster",
                    "vendor": "vesoft",
                    "engine": "graph",
                    "token": "secret-token",
                },
            },
            skill_path_resolver=lambda active_skills: [],
        )

        prompt = render_chat_system_prompt(
            session_context=context,
            base_prompt="BASE",
            skill_instructions="",
            ltm_context="",
        )

        self.assertIn("会话类型：Nebula Graph 数据库会话", prompt)
        self.assertIn(
            "资产识别：NebulaGraph集群（类型 nebula_graph_cluster，分类 数据库，协议 nebula_graph）",
            prompt,
        )
        self.assertIn("识别字段：category=db；sub_type=nebula_graph_cluster；vendor=vesoft；engine=graph", prompt)
        self.assertNotIn("secret-token", prompt)

    @patch("core.agent_prompts.protocol_tool_list")
    @patch("core.agent_prompts.protocol_tool_guidance")
    @patch("core.agent_prompts.format_extra_args_for_prompt")
    def test_headless_prompt_uses_task_and_virtual_skill_tool_visibility(
        self,
        format_extra_args,
        protocol_guidance,
        protocol_tool_list,
    ):
        format_extra_args.return_value = "- region: cn"
        protocol_guidance.return_value = "VIRTUAL-GUIDANCE"
        protocol_tool_list.return_value = "VIRTUAL-TOOLS"

        prompt = render_headless_system_prompt(
            session_context=self._session_context(protocol="virtual"),
            base_prompt="BASE",
            task_description="检查 Skills 工程结构",
        )

        self.assertTrue(prompt.startswith("BASE\n\n[当前会话上下文]"))
        self.assertIn("会话类型：虚拟/本地技能研发会话", prompt)
        self.assertIn("一台通过VIRTUAL协议纳管的 VIRTUAL 资产", prompt)
        self.assertIn("[上级指挥官委派的任务]", prompt)
        self.assertIn("检查 Skills 工程结构", prompt)
        self.assertIn("VIRTUAL-TOOLS", prompt)
        self.assertNotIn("[当前已加载专业技能说明 (Skills)]", prompt)
        protocol_tool_list.assert_called_once_with("virtual", True, "virtual")


if __name__ == "__main__":
    unittest.main()
