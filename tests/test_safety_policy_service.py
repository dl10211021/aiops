import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core import safety_policy_service
from core.safety_policy_service import (
    SafetyPolicyServiceError,
    build_safety_policy_test_context,
    build_safety_policy_test_tool_args,
    explain_safety_policy_test,
    explain_safety_policy_decision,
    get_safety_policy_record,
    save_safety_policy_record,
)


class TestSafetyPolicyService(unittest.TestCase):
    def test_get_safety_policy_delegates_to_policy_store(self):
        with patch.object(safety_policy_service, "get_safety_policy", return_value={"version": 1}):
            self.assertEqual(get_safety_policy_record(), {"version": 1})

    def test_save_policy_maps_validation_errors_to_422(self):
        with patch.object(safety_policy_service, "save_safety_policy", side_effect=ValueError("bad policy")):
            with self.assertRaises(SafetyPolicyServiceError) as ctx:
                save_safety_policy_record({"bad": True})

        self.assertEqual(ctx.exception.status_code, 422)
        self.assertEqual(ctx.exception.detail, "bad policy")

    def test_save_policy_maps_unexpected_errors_to_500(self):
        with patch.object(safety_policy_service, "save_safety_policy", side_effect=RuntimeError("disk full")):
            with self.assertRaises(SafetyPolicyServiceError) as ctx:
                save_safety_policy_record({"version": 1})

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("disk full", ctx.exception.detail)

    def test_explain_policy_decision_delegates_to_core_policy(self):
        with patch.object(
            safety_policy_service,
            "explain_policy_decision",
            return_value={"decision": "allow"},
        ) as explain:
            result = explain_safety_policy_decision("linux_execute_command", {"command": "uptime"}, {})

        self.assertEqual(result["decision"], "allow")
        explain.assert_called_once_with("linux_execute_command", {"command": "uptime"}, {})

    def test_build_safety_policy_test_tool_args_maps_protocol_tools(self):
        db_payload = SimpleNamespace(tool_name="db_execute_query", sql="SELECT 1", command="", method="", path="", oid="", body=None)
        http_payload = SimpleNamespace(
            tool_name="service_probe_request",
            sql="",
            command="",
            method="post",
            path="/health",
            oid="",
            body={"timeout": 3},
        )
        snmp_payload = SimpleNamespace(tool_name="snmp_get", sql="", command="", method="", path="", oid="1.3.6.1", body=None)
        skill_payload = SimpleNamespace(tool_name="evolve_skill", sql="", command="safe-skill", method="", path="SKILL.md", oid="", body=None)

        self.assertEqual(build_safety_policy_test_tool_args(db_payload), {"sql": "SELECT 1"})
        self.assertEqual(
            build_safety_policy_test_tool_args(http_payload),
            {"method": "POST", "path": "/health", "oid": "", "body": {"timeout": 3}},
        )
        self.assertEqual(build_safety_policy_test_tool_args(snmp_payload), {"oid": "1.3.6.1"})
        self.assertEqual(
            build_safety_policy_test_tool_args(skill_payload),
            {"skill_id": "safe-skill", "file_name": "SKILL.md"},
        )

    def test_build_safety_policy_test_context_normalizes_empty_fields(self):
        payload = SimpleNamespace(
            allow_modifications=True,
            asset_type=None,
            protocol="mysql",
            host=None,
            trigger_source=None,
            tags=["核心"],
        )

        context = build_safety_policy_test_context(payload)

        self.assertTrue(context["allow_modifications"])
        self.assertEqual(context["asset_type"], "")
        self.assertEqual(context["protocol"], "mysql")
        self.assertEqual(context["host"], "")
        self.assertEqual(context["trigger_source"], "chat")
        self.assertEqual(context["tags"], ["核心"])

    def test_explain_safety_policy_test_uses_built_args_and_context(self):
        payload = SimpleNamespace(
            tool_name="linux_execute_command",
            command="uptime",
            sql="",
            method="",
            path="",
            oid="",
            body=None,
            allow_modifications=False,
            asset_type="linux",
            protocol="ssh",
            host="10.0.0.10",
            trigger_source="chat",
            tags=[],
        )
        with patch.object(
            safety_policy_service,
            "explain_safety_policy_decision",
            return_value={"decision": "allow"},
        ) as explain:
            result = explain_safety_policy_test(payload)

        self.assertEqual(result["decision"], "allow")
        explain.assert_called_once_with(
            "linux_execute_command",
            {"command": "uptime"},
            {
                "allow_modifications": False,
                "asset_type": "linux",
                "protocol": "ssh",
                "host": "10.0.0.10",
                "trigger_source": "chat",
                "tags": [],
            },
        )
