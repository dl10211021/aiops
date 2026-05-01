import unittest
from unittest.mock import patch

from core import safety_policy_service
from core.safety_policy_service import (
    SafetyPolicyServiceError,
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
