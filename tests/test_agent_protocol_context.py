import unittest

from core.agent_protocol_context import (
    allow_local_skill_scripts,
    format_extra_args_for_prompt,
    protocol_tool_guidance,
    protocol_tool_list,
)


class TestAgentProtocolContext(unittest.TestCase):
    def test_format_extra_args_masks_sensitive_values(self):
        formatted = format_extra_args_for_prompt(
            {
                "api_key": "secret",
                "region": "cn-north-1",
                "empty": "",
            }
        )

        self.assertIn("- api_key: (已托管，执行时自动注入)", formatted)
        self.assertIn("- region: cn-north-1", formatted)
        self.assertNotIn("secret", formatted)
        self.assertNotIn("empty", formatted)

    def test_protocol_tool_guidance_uses_network_tool_for_switch(self):
        guidance = protocol_tool_guidance("ssh", "switch", "10.0.0.1")

        self.assertIn("网络设备 CLI", guidance)
        self.assertIn("network_cli_execute_command", guidance)
        self.assertIn("不要使用 Linux 命令", guidance)

    def test_protocol_tool_guidance_uses_domain_tools_for_catalog_ssh_subtypes(self):
        cases = [
            ("h3c_switch", "network_cli_execute_command", "网络设备 CLI"),
            ("nas", "storage_execute_command", "存储节点"),
            ("synology_nas", "storage_execute_command", "存储节点"),
            ("process", "middleware_execute_command", "中间件主机"),
        ]

        for asset_type, tool_name, expected_text in cases:
            with self.subTest(asset_type=asset_type):
                guidance = protocol_tool_guidance("ssh", asset_type, "10.0.0.1")

                self.assertIn(tool_name, guidance)
                self.assertIn(expected_text, guidance)

    def test_protocol_tool_list_filters_local_execute_script_by_default(self):
        filtered = protocol_tool_list("virtual", has_skill_scripts=False)
        allowed = protocol_tool_list("virtual", has_skill_scripts=True)

        self.assertNotIn("- local_execute_script:", filtered)
        self.assertIn("- 本地技能脚本 (`local_execute_script`):", allowed)

    def test_protocol_tool_list_uses_chinese_names_with_tool_ids(self):
        tools = protocol_tool_list("ssh", asset_type="linux")

        self.assertIn("- Linux/Unix 命令 (`linux_execute_command`):", tools)
        self.assertNotIn("- linux_execute_command:", tools)

    def test_allow_local_skill_scripts_only_for_virtual_protocol(self):
        self.assertTrue(allow_local_skill_scripts("virtual"))
        self.assertFalse(allow_local_skill_scripts("ssh"))


if __name__ == "__main__":
    unittest.main()
