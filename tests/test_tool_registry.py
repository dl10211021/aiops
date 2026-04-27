import unittest

from core.tool_registry import tool_registry


def enabled_tool_names(context):
    catalog = tool_registry.catalog(context)
    return {
        tool["name"]
        for toolset in catalog["toolsets"]
        for tool in toolset["tools"]
        if tool.get("enabled")
    }


class TestToolRegistry(unittest.TestCase):
    def test_windows_session_enables_winrm_only(self):
        names = enabled_tool_names(
            {
                "target_scope": "asset",
                "asset_type": "windows",
                "protocol": "winrm",
                "extra_args": {},
            }
        )

        self.assertIn("winrm_execute_command", names)
        self.assertNotIn("linux_execute_command", names)
        self.assertNotIn("local_execute_script", names)

    def test_mysql_session_enables_sql_tool(self):
        names = enabled_tool_names(
            {
                "target_scope": "asset",
                "asset_type": "mysql",
                "protocol": "mysql",
                "extra_args": {"db_type": "mysql"},
            }
        )

        self.assertIn("db_execute_query", names)
        self.assertNotIn("linux_execute_command", names)

    def test_switch_session_enables_network_cli_not_linux(self):
        names = enabled_tool_names(
            {
                "target_scope": "asset",
                "asset_type": "switch",
                "protocol": "ssh",
                "extra_args": {"category": "network"},
            }
        )

        self.assertIn("network_cli_execute_command", names)
        self.assertNotIn("linux_execute_command", names)

    def test_virtual_session_is_the_only_scope_with_local_script(self):
        names = enabled_tool_names(
            {
                "target_scope": "asset",
                "asset_type": "linux",
                "protocol": "virtual",
                "extra_args": {"login_protocol": "virtual"},
            }
        )

        self.assertIn("local_execute_script", names)

    def test_tag_scope_keeps_group_batch_tool(self):
        names = enabled_tool_names({"target_scope": "tag", "extra_args": {}})

        self.assertIn("execute_on_scope", names)


if __name__ == "__main__":
    unittest.main()
