import unittest

from core import safety_policy
from core.safety_tool_categories import TOOL_CATEGORY


class SafetyToolCategoryTests(unittest.TestCase):
    def test_core_tool_categories_cover_existing_protocol_families(self):
        self.assertEqual(TOOL_CATEGORY["linux_execute_command"], "linux")
        self.assertEqual(TOOL_CATEGORY["winrm_execute_command"], "windows")
        self.assertEqual(TOOL_CATEGORY["db_execute_query"], "sql")
        self.assertEqual(TOOL_CATEGORY["network_cli_execute_command"], "network")
        self.assertEqual(TOOL_CATEGORY["k8s_api_request"], "http")
        self.assertEqual(TOOL_CATEGORY["snmp_get"], "snmp")

    def test_safety_policy_keeps_backward_compatible_tool_category_export(self):
        self.assertIs(safety_policy.TOOL_CATEGORY, TOOL_CATEGORY)


if __name__ == "__main__":
    unittest.main()
