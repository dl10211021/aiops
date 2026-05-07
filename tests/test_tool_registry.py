import unittest

from api.asset_routes import get_asset_catalog
from core.tool_registry import tool_registry


def enabled_tool_names(context):
    catalog = tool_registry.catalog(context)
    return {
        tool["name"]
        for toolset in catalog["toolsets"]
        for tool in toolset["tools"]
        if tool.get("enabled")
    }


def enabled_tool(context, name):
    catalog = tool_registry.catalog(context)
    for toolset in catalog["toolsets"]:
        for tool in toolset["tools"]:
            if tool.get("enabled") and tool["name"] == name:
                return tool
    return None


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

    def test_sql_tool_description_explains_readwrite_execution_boundary(self):
        tool = enabled_tool(
            {
                "target_scope": "asset",
                "asset_type": "oracle",
                "protocol": "oracle",
                "extra_args": {"db_type": "oracle"},
            },
            "db_execute_query",
        )

        self.assertIsNotNone(tool)
        description = tool["description"]
        self.assertIn("执行 SQL", description)
        self.assertIn("变更类 SQL", description)
        self.assertIn("审批", description)
        self.assertNotIn("只支持 SELECT", description)

    def test_memcached_session_enables_memcached_tool(self):
        names = enabled_tool_names(
            {
                "target_scope": "asset",
                "asset_type": "memcached",
                "protocol": "memcached",
                "extra_args": {"category": "db"},
            }
        )

        self.assertIn("memcached_execute_command", names)
        self.assertNotIn("redis_execute_command", names)
        self.assertNotIn("db_execute_query", names)

    def test_dameng_session_enables_sql_tool(self):
        names = enabled_tool_names(
            {
                "target_scope": "asset",
                "asset_type": "dameng",
                "protocol": "dameng",
                "extra_args": {"db_type": "dameng"},
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

    def test_interaction_tool_is_available_in_all_sessions(self):
        names = enabled_tool_names(
            {
                "target_scope": "asset",
                "asset_type": "linux",
                "protocol": "ssh",
                "extra_args": {},
            }
        )

        self.assertIn("request_user_interaction", names)

    def test_memory_tools_are_available_in_all_sessions(self):
        names = enabled_tool_names(
            {
                "target_scope": "asset",
                "asset_type": "linux",
                "protocol": "ssh",
                "extra_args": {},
            }
        )

        self.assertIn("memory_list", names)
        self.assertIn("memory_read", names)
        self.assertIn("memory_write", names)
        self.assertIn("memory_edit", names)
        self.assertIn("memory_delete", names)

    def test_s3_session_enables_storage_api_tool(self):
        names = enabled_tool_names(
            {
                "target_scope": "asset",
                "asset_type": "s3",
                "protocol": "s3",
                "extra_args": {"category": "storage", "sub_type": "s3"},
            }
        )

        self.assertIn("storage_api_request", names)
        self.assertNotIn("linux_execute_command", names)

    def test_ceph_session_enables_storage_command_not_linux(self):
        names = enabled_tool_names(
            {
                "target_scope": "asset",
                "asset_type": "ceph",
                "protocol": "ssh",
                "extra_args": {"category": "storage", "sub_type": "ceph"},
            }
        )

        self.assertIn("storage_execute_command", names)
        self.assertNotIn("linux_execute_command", names)

    def test_nas_session_uses_snmp_not_storage_api(self):
        names = enabled_tool_names(
            {
                "target_scope": "asset",
                "asset_type": "nas",
                "protocol": "snmp",
                "extra_args": {"category": "storage", "sub_type": "nas"},
            }
        )

        self.assertIn("snmp_get", names)
        self.assertNotIn("storage_api_request", names)

    def test_clickhouse_session_uses_database_http_tooling(self):
        names = enabled_tool_names(
            {
                "target_scope": "asset",
                "asset_type": "clickhouse",
                "protocol": "clickhouse",
                "extra_args": {"category": "db", "db_type": "clickhouse"},
            }
        )

        self.assertIn("database_api_request", names)
        self.assertNotIn("http_api_request", names)
        self.assertNotIn("db_execute_query", names)

    def test_vmware_session_enables_virtualization_api_tool(self):
        names = enabled_tool_names(
            {
                "target_scope": "asset",
                "asset_type": "vmware",
                "protocol": "vmware",
                "extra_args": {"category": "virtualization", "sub_type": "vmware"},
            }
        )

        self.assertIn("virtualization_api_request", names)
        self.assertNotIn("http_api_request", names)
        self.assertNotIn("linux_execute_command", names)

    def test_openstack_session_enables_virtualization_api_tool(self):
        names = enabled_tool_names(
            {
                "target_scope": "asset",
                "asset_type": "openstack",
                "protocol": "openstack",
                "extra_args": {"category": "virtualization", "sub_type": "openstack"},
            }
        )

        self.assertIn("virtualization_api_request", names)
        self.assertNotIn("http_api_request", names)
        self.assertNotIn("linux_execute_command", names)

    def test_zstack_session_enables_virtualization_api_tool(self):
        names = enabled_tool_names(
            {
                "target_scope": "asset",
                "asset_type": "zstack",
                "protocol": "zstack",
                "extra_args": {"category": "virtualization", "sub_type": "zstack"},
            }
        )

        self.assertIn("virtualization_api_request", names)
        self.assertNotIn("http_api_request", names)
        self.assertNotIn("linux_execute_command", names)

    def test_hyperv_session_enables_winrm_not_virtualization_api(self):
        names = enabled_tool_names(
            {
                "target_scope": "asset",
                "asset_type": "hyperv",
                "protocol": "winrm",
                "extra_args": {"category": "virtualization", "sub_type": "hyperv"},
            }
        )

        self.assertIn("winrm_execute_command", names)
        self.assertNotIn("virtualization_api_request", names)
        self.assertNotIn("linux_execute_command", names)

    def test_k8s_session_enables_k8s_tool_not_generic_http(self):
        names = enabled_tool_names(
            {
                "target_scope": "asset",
                "asset_type": "k8s",
                "protocol": "k8s",
                "extra_args": {"category": "container", "sub_type": "k8s"},
            }
        )

        self.assertIn("k8s_api_request", names)
        self.assertNotIn("http_api_request", names)

    def test_monitoring_session_enables_monitoring_tool_not_generic_http(self):
        names = enabled_tool_names(
            {
                "target_scope": "asset",
                "asset_type": "prometheus",
                "protocol": "http_api",
                "extra_args": {"category": "monitor", "sub_type": "prometheus"},
            }
        )

        self.assertIn("monitoring_api_query", names)
        self.assertNotIn("http_api_request", names)

    def test_hertzbeat_session_enables_monitoring_tool_not_generic_http(self):
        names = enabled_tool_names(
            {
                "target_scope": "asset",
                "asset_type": "hertzbeat",
                "protocol": "http_api",
                "extra_args": {"category": "monitor", "sub_type": "hertzbeat"},
            }
        )

        self.assertIn("monitoring_api_query", names)
        self.assertNotIn("http_api_request", names)

    def test_domain_http_assets_use_business_tools_not_generic_http(self):
        cases = [
            ("airflow", "bigdata_api_request"),
            ("rabbitmq", "middleware_api_request"),
            ("harbor", "container_api_request"),
            ("f5", "network_api_request"),
            ("bastion", "security_api_request"),
            ("dahua", "oob_api_request"),
            ("consul_sd", "discovery_api_request"),
            ("ollama", "ai_platform_api_request"),
            ("jenkins", "cicd_api_request"),
        ]
        for asset_type, tool_name in cases:
            with self.subTest(asset_type=asset_type):
                names = enabled_tool_names(
                    {
                        "target_scope": "asset",
                        "asset_type": asset_type,
                        "protocol": "http_api",
                        "extra_args": {"sub_type": asset_type},
                    }
                )

                self.assertIn(tool_name, names)
                self.assertNotIn("http_api_request", names)

    def test_tcp_service_asset_enables_service_probe_not_http_api(self):
        names = enabled_tool_names(
            {
                "target_scope": "asset",
                "asset_type": "port",
                "protocol": "tcp",
                "extra_args": {"category": "service", "sub_type": "port"},
            }
        )

        self.assertIn("service_probe_request", names)
        self.assertNotIn("http_api_request", names)

    def test_generic_api_service_asset_enables_service_probe_not_http_api(self):
        names = enabled_tool_names(
            {
                "target_scope": "asset",
                "asset_type": "api",
                "protocol": "http",
                "extra_args": {"category": "service", "sub_type": "api"},
            }
        )

        self.assertIn("service_probe_request", names)
        self.assertNotIn("http_api_request", names)

    def test_dns_service_asset_enables_service_probe_not_network_cli(self):
        names = enabled_tool_names(
            {
                "target_scope": "asset",
                "asset_type": "dns",
                "protocol": "dns",
                "extra_args": {"category": "service", "sub_type": "dns"},
            }
        )

        self.assertIn("service_probe_request", names)
        self.assertNotIn("network_cli_execute_command", names)
        self.assertNotIn("linux_execute_command", names)

    def test_all_registered_tools_have_chinese_display_labels(self):
        missing = []
        for tool in tool_registry.all_tools():
            public = tool.public_dict()
            label = str(public.get("label") or "")
            if not label or label == tool.name or all(ord(ch) < 128 for ch in label):
                missing.append(tool.name)

        self.assertEqual(missing, [])

    def test_asset_capability_tools_are_registered_and_named(self):
        issues = []
        for asset in get_asset_catalog():
            capability = asset.get("capability") or {}
            tools = capability.get("tools") or []
            details = {item.get("name"): item for item in capability.get("tool_details") or []}
            for tool_name in tools:
                if not tool_registry.get(tool_name):
                    issues.append((asset["id"], tool_name, "not_registered"))
                    continue
                detail = details.get(tool_name)
                if not detail or not detail.get("label") or detail.get("label") == tool_name:
                    issues.append((asset["id"], tool_name, "missing_label"))

        self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()
