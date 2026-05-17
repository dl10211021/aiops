import unittest

from api.asset_routes import get_asset_catalog
from core.tool_display import toolset_label
from core.tool_policy_validation import validate_tool_runtime_policies
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

    def test_dispatch_sub_agents_schema_exposes_scope_boundary(self):
        tool = enabled_tool(
            {
                "target_scope": "global",
                "asset_type": "virtual",
                "protocol": "virtual",
                "extra_args": {},
            },
            "dispatch_sub_agents",
        )

        self.assertIsNotNone(tool)
        definition = tool_registry.get("dispatch_sub_agents")
        self.assertIsNotNone(definition)
        parameters = definition.parameters["properties"]
        self.assertIn("dispatch_scope", parameters)
        self.assertEqual(parameters["dispatch_scope"]["enum"], ["global", "group"])
        self.assertIn("group_name", parameters)
        self.assertIn("当前会话组", tool["description"])

    def test_tool_catalog_exposes_runtime_policy_metadata(self):
        linux_tool = enabled_tool(
            {
                "target_scope": "asset",
                "asset_type": "linux",
                "protocol": "ssh",
                "extra_args": {},
            },
            "linux_execute_command",
        )
        sql_tool = enabled_tool(
            {
                "target_scope": "asset",
                "asset_type": "mysql",
                "protocol": "mysql",
                "extra_args": {"db_type": "mysql"},
            },
            "db_execute_query",
        )
        memory_delete = enabled_tool(
            {
                "target_scope": "asset",
                "asset_type": "linux",
                "protocol": "ssh",
                "extra_args": {},
            },
            "memory_delete",
        )

        self.assertEqual(linux_tool["operation_mode"], "read_write")
        self.assertEqual(linux_tool["approval_policy"], "guarded_write")
        self.assertEqual(linux_tool["evidence_family"], "host_cli")
        self.assertEqual(linux_tool["ui_renderer"], "terminal")
        self.assertFalse(linux_tool["concurrency_safe"])
        self.assertIn("delay_seconds", linux_tool["retry_policy"])
        self.assertEqual(sql_tool["evidence_family"], "database")
        self.assertEqual(sql_tool["ui_renderer"], "sql_result")
        self.assertEqual(memory_delete["operation_mode"], "destructive")
        self.assertTrue(memory_delete["destructive"])
        self.assertEqual(memory_delete["approval_policy"], "always_required")
        self.assertEqual(memory_delete["metadata_version"], 2)

    def test_skill_tools_are_not_misclassified_as_destructive(self):
        skills_list = enabled_tool(
            {
                "target_scope": "asset",
                "asset_type": "linux",
                "protocol": "ssh",
                "extra_args": {},
            },
            "skills_list",
        )
        skill_view = enabled_tool(
            {
                "target_scope": "asset",
                "asset_type": "linux",
                "protocol": "ssh",
                "extra_args": {},
            },
            "skill_view",
        )

        self.assertEqual(skills_list["operation_mode"], "read")
        self.assertFalse(skills_list["destructive"])
        self.assertEqual(skill_view["operation_mode"], "read")
        self.assertFalse(skill_view["destructive"])

    def test_all_registered_tool_runtime_policies_are_consistent(self):
        self.assertEqual(validate_tool_runtime_policies(tool_registry.all_tools()), [])

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

    def test_firewall_can_use_ssh_or_api_tooling(self):
        ssh_names = enabled_tool_names(
            {
                "target_scope": "asset",
                "asset_type": "firewall",
                "protocol": "ssh",
                "extra_args": {"category": "network", "sub_type": "firewall"},
            }
        )
        api_names = enabled_tool_names(
            {
                "target_scope": "asset",
                "asset_type": "firewall",
                "protocol": "http_api",
                "extra_args": {"category": "network", "sub_type": "firewall"},
            }
        )

        self.assertIn("network_cli_execute_command", ssh_names)
        self.assertNotIn("linux_execute_command", ssh_names)
        self.assertIn("network_api_request", api_names)
        self.assertNotIn("http_api_request", api_names)
        self.assertNotIn("network_cli_execute_command", api_names)

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

    def test_nas_session_enables_storage_command_not_linux(self):
        names = enabled_tool_names(
            {
                "target_scope": "asset",
                "asset_type": "nas",
                "protocol": "ssh",
                "extra_args": {"category": "storage", "sub_type": "nas"},
            }
        )

        self.assertIn("storage_execute_command", names)
        self.assertNotIn("linux_execute_command", names)
        self.assertNotIn("storage_api_request", names)

    def test_catalog_declared_tools_are_enabled_for_new_asset_types(self):
        missing = []
        for item in get_asset_catalog():
            capability = item.get("capability") or {}
            declared_tools = capability.get("tools") or []
            if not declared_tools:
                continue

            names = enabled_tool_names(
                {
                    "target_scope": "asset",
                    "asset_type": item["id"],
                    "protocol": item.get("protocol"),
                    "extra_args": {
                        "category": item.get("category"),
                        "sub_type": item["id"],
                        "db_type": capability.get("driver_key") or item["id"],
                    },
                }
            )
            missing.extend(
                f"{item['id']}:{tool_name}"
                for tool_name in declared_tools
                if tool_name not in names
            )

        self.assertEqual(missing, [])

    def test_specific_catalog_ssh_types_use_domain_tools_not_linux(self):
        cases = [
            ("h3c_switch", "network_cli_execute_command", True),
            ("huawei_switch", "network_cli_execute_command", True),
            ("synology_nas", "storage_execute_command", True),
            ("kafka", "middleware_execute_command", True),
            ("process", "middleware_execute_command", True),
        ]
        for asset_type, tool_name, excludes_linux in cases:
            with self.subTest(asset_type=asset_type):
                item = next(asset for asset in get_asset_catalog() if asset["id"] == asset_type)
                names = enabled_tool_names(
                    {
                        "target_scope": "asset",
                        "asset_type": item["id"],
                        "protocol": item.get("protocol"),
                        "extra_args": {"category": item.get("category"), "sub_type": item["id"]},
                    }
                )

                self.assertIn(tool_name, names)
                if excludes_linux:
                    self.assertNotIn("linux_execute_command", names)

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

    def test_logging_platform_session_enables_log_query_tool_not_generic_http(self):
        for asset_type in ("elastic_stack", "graylog", "loki", "opensearch"):
            with self.subTest(asset_type=asset_type):
                names = enabled_tool_names(
                    {
                        "target_scope": "asset",
                        "asset_type": asset_type,
                        "protocol": "http_api",
                        "extra_args": {"category": "log", "sub_type": asset_type},
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

    def test_all_registered_toolsets_have_chinese_display_labels(self):
        missing = []
        for toolset in {tool.toolset for tool in tool_registry.all_tools()}:
            label = toolset_label(toolset)
            if not label or label == toolset or all(ord(ch) < 128 for ch in label):
                missing.append(toolset)

        self.assertEqual(sorted(missing), [])

    def test_prompt_lines_show_chinese_labels_with_original_tool_ids(self):
        expectations = [
            (
                {"target_scope": "asset", "asset_type": "linux", "protocol": "ssh"},
                "- Linux/Unix 命令 (`linux_execute_command`):",
                "- linux_execute_command:",
            ),
            (
                {"target_scope": "asset", "asset_type": "windows", "protocol": "winrm"},
                "- Windows PowerShell 命令 (`winrm_execute_command`):",
                "- winrm_execute_command:",
            ),
            (
                {"target_scope": "asset", "asset_type": "oracle", "protocol": "oracle"},
                "- 数据库 SQL 执行 (`db_execute_query`):",
                "- db_execute_query:",
            ),
            (
                {"target_scope": "asset", "asset_type": "redis", "protocol": "redis"},
                "- Redis 命令 (`redis_execute_command`):",
                "- redis_execute_command:",
            ),
            (
                {
                    "target_scope": "asset",
                    "asset_type": "switch",
                    "protocol": "snmp",
                    "extra_args": {"category": "network", "sub_type": "h3c_switch"},
                },
                "- SNMP 读取 (`snmp_get`):",
                "- snmp_get:",
            ),
            (
                {
                    "target_scope": "asset",
                    "asset_type": "zabbix",
                    "protocol": "http_api",
                    "extra_args": {"category": "monitor", "sub_type": "zabbix"},
                },
                "- 监控平台查询 (`monitoring_api_query`):",
                "- monitoring_api_query:",
            ),
            (
                {
                    "target_scope": "asset",
                    "asset_type": "vmware",
                    "protocol": "api",
                    "extra_args": {
                        "category": "virtualization",
                        "sub_type": "vmware",
                    },
                },
                "- 虚拟化平台接口 (`virtualization_api_request`):",
                "- virtualization_api_request:",
            ),
        ]

        for context, expected_label, raw_prefix in expectations:
            with self.subTest(expected_label=expected_label):
                prompt = tool_registry.prompt_lines(context)
                self.assertIn(expected_label, prompt)
                self.assertNotIn(raw_prefix, prompt)
                self.assertIn("模式：", prompt)
                self.assertIn("审批：", prompt)
                self.assertIn("证据：", prompt)

    def test_prompt_lines_expose_runtime_policy_boundaries(self):
        linux_prompt = tool_registry.prompt_lines(
            {"target_scope": "asset", "asset_type": "linux", "protocol": "ssh"}
        )
        mysql_prompt = tool_registry.prompt_lines(
            {
                "target_scope": "asset",
                "asset_type": "mysql",
                "protocol": "mysql",
                "extra_args": {"db_type": "mysql"},
            }
        )
        web_prompt = tool_registry.prompt_lines({"target_scope": "asset", "asset_type": "linux", "protocol": "ssh"})

        self.assertIn("Linux/Unix 命令 (`linux_execute_command`): [模式：读写受控；审批：写入受控；证据：主机命令证据]", linux_prompt)
        self.assertIn("数据库 SQL 执行 (`db_execute_query`): [模式：读写受控；审批：写入受控；证据：数据库证据]", mysql_prompt)
        self.assertNotIn("发送通知", web_prompt)

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
