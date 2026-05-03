import unittest
from unittest.mock import patch

from core.agent_prompts import (
    render_chat_system_prompt,
    render_headless_system_prompt,
)
from core.agent_session_context import build_agent_session_context


class AgentPromptTests(unittest.TestCase):
    def _session_context(self, protocol: str = "ssh"):
        return build_agent_session_context(
            "sid-prompt",
            {
                "asset_type": "virtual" if protocol == "virtual" else "linux",
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

        self.assertTrue(prompt.startswith("\nBASE\n\n[当前持有的资产凭证]"))
        self.assertIn("一台通过SSH协议纳管的 LINUX 资产", prompt)
        self.assertIn("- api_token: (已托管，执行时自动注入)", prompt)
        self.assertIn("**只读巡检模式**", prompt)
        self.assertIn("[当前已加载专业技能说明 (Skills)]", prompt)
        self.assertIn("<INSTRUCTIONS>check</INSTRUCTIONS>", prompt)
        self.assertIn("LTM-CONTEXT", prompt)
        protocol_tool_list.assert_called_once_with("ssh", False, "linux")

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

        self.assertTrue(prompt.startswith("BASE\n\n[当前持有的资产凭证]"))
        self.assertIn("一台通过VIRTUAL协议纳管的 VIRTUAL 资产", prompt)
        self.assertIn("[上级指挥官委派的任务]", prompt)
        self.assertIn("检查 Skills 工程结构", prompt)
        self.assertIn("VIRTUAL-TOOLS", prompt)
        self.assertNotIn("[当前已加载专业技能说明 (Skills)]", prompt)
        protocol_tool_list.assert_called_once_with("virtual", True, "virtual")


if __name__ == "__main__":
    unittest.main()
