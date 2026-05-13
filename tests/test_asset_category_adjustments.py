import unittest

from core import asset_capabilities
from core.asset_category_adjustments import _category_adjustment


class AssetCategoryAdjustmentTests(unittest.TestCase):
    def test_ssh_category_adjustments_route_to_protocol_specific_connectors(self):
        self.assertEqual(
            _category_adjustment("switch", "network", "ssh"),
            {
                "family": "network",
                "connector": "ssh_network_cli",
                "tools": ["network_cli_execute_command"],
                "safety_category": "network_cli",
            },
        )
        self.assertEqual(
            _category_adjustment("docker", "container", "ssh"),
            {"family": "container", "connector": "container_shell", "tools": ["container_execute_command"]},
        )

    def test_http_category_adjustments_route_platform_api_tools(self):
        self.assertEqual(
            _category_adjustment("jenkins", "cicd", "http_api"),
            {"family": "cicd", "connector": "cicd_api", "tools": ["cicd_api_request"]},
        )
        self.assertEqual(
            _category_adjustment("zabbix", "monitor", "http_api"),
            {"family": "monitoring", "connector": "monitoring_api", "tools": ["monitoring_api_query"]},
        )
        self.assertEqual(
            _category_adjustment("graylog", "log", "http_api"),
            {
                "family": "logging",
                "connector": "log_api",
                "operation_model": "log_query_client",
                "tools": ["monitoring_api_query"],
                "credential_fields": ["host", "port", "username", "password", "api_token"],
                "safety_category": "http_api",
                "maturity": "generic",
            },
        )

    def test_storage_and_service_probe_adjustments_preserve_credentials(self):
        self.assertEqual(_category_adjustment("s3", "storage", "s3")["connector"], "storage_api")
        ldap_adjustment = _category_adjustment("ldap", "service", "ldap")
        self.assertEqual(ldap_adjustment["connector"], "service_probe")
        self.assertEqual(ldap_adjustment["credential_fields"], ["host", "port", "username", "password", "base_dn"])

    def test_asset_capabilities_keeps_backward_compatible_adjustment_export(self):
        self.assertIs(asset_capabilities._category_adjustment, _category_adjustment)


if __name__ == "__main__":
    unittest.main()
