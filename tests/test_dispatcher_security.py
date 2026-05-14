import os
import asyncio
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from core.dispatcher import SkillDispatcher


class TestDispatcherSecurity(unittest.TestCase):
    def test_local_execution_requires_cwd_under_active_skill_path(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        skill_dir = str(Path.cwd() / "my_custom_skills" / "linux")

        allowed, reason = dispatcher._validate_local_execution(
            "python scripts/check.py",
            skill_dir,
            {"active_skill_paths": [skill_dir]},
        )
        self.assertTrue(allowed, reason)

        allowed, reason = dispatcher._validate_local_execution(
            "python scripts/check.py",
            str(Path.cwd()),
            {"active_skill_paths": [skill_dir]},
        )
        self.assertFalse(allowed)
        self.assertIn("已挂载 Skill", reason)

    def test_local_execution_rejects_shell_control_operators(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        skill_dir = str(Path.cwd() / "my_custom_skills" / "linux")
        allowed, reason = dispatcher._validate_local_execution(
            "python scripts/check.py && whoami",
            skill_dir,
            {"active_skill_paths": [skill_dir]},
        )

        self.assertFalse(allowed)
        self.assertIn("Shell", reason)

    def test_readonly_blocked_commands_do_not_request_approval(self):
        policy_path = str(Path.cwd() / "dispatcher_security_policy_missing.json")
        if os.path.exists(policy_path):
            os.remove(policy_path)

        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        try:
            with patch("core.safety_policy.POLICY_PATH", policy_path):
                readonly_needs_approval, _ = dispatcher.check_approval_needed(
                    "linux_execute_command",
                    {"command": "systemctl restart nginx"},
                    {"allow_modifications": False},
                )
                readwrite_needs_approval, _ = dispatcher.check_approval_needed(
                    "linux_execute_command",
                    {"command": "systemctl restart nginx"},
                    {"allow_modifications": True},
                )
        finally:
            if os.path.exists(policy_path):
                os.remove(policy_path)

        self.assertFalse(readonly_needs_approval)
        self.assertTrue(readwrite_needs_approval)

    def test_hard_blocked_commands_do_not_request_approval(self):
        policy_path = str(Path.cwd() / "dispatcher_security_policy_hard_block.json")
        if os.path.exists(policy_path):
            os.remove(policy_path)

        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        try:
            with patch("core.safety_policy.POLICY_PATH", policy_path):
                needs_approval, reason = dispatcher.check_approval_needed(
                    "db_execute_query",
                    {"sql": "DROP USER app_user CASCADE"},
                    {"allow_modifications": True, "asset_type": "oracle", "protocol": "oracle"},
                )
        finally:
            if os.path.exists(policy_path):
                os.remove(policy_path)

        self.assertFalse(needs_approval)
        self.assertEqual(reason, "")

    def test_runtime_external_effect_requires_approval_even_with_auto_approve(self):
        dispatcher = SkillDispatcher.__new__(SkillDispatcher)

        with patch(
            "connections.ssh_manager.ssh_manager.active_sessions",
            {"sid-auto": {"info": {"auto_approve_all": True}}},
        ):
            needs_approval, reason = dispatcher.check_approval_needed(
                "send_notification",
                {"channel": "wechat", "title": "巡检", "message": "done"},
                {"session_id": "sid-auto", "allow_modifications": True},
            )

        self.assertTrue(needs_approval)
        self.assertIn("工具执行策略要求审批", reason)

    def test_auto_approve_only_bypasses_safety_policy_not_runtime_policy(self):
        policy_path = str(Path.cwd() / "dispatcher_security_policy_auto_approve.json")
        if os.path.exists(policy_path):
            os.remove(policy_path)

        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        try:
            with (
                patch("core.safety_policy.POLICY_PATH", policy_path),
                patch(
                    "connections.ssh_manager.ssh_manager.active_sessions",
                    {"sid-auto": {"info": {"auto_approve_all": True}}},
                ),
            ):
                needs_approval, reason = dispatcher.check_approval_needed(
                    "linux_execute_command",
                    {"command": "systemctl restart nginx"},
                    {
                        "session_id": "sid-auto",
                        "allow_modifications": True,
                        "asset_type": "linux",
                        "protocol": "ssh",
                    },
                )
        finally:
            if os.path.exists(policy_path):
                os.remove(policy_path)

        self.assertFalse(needs_approval)
        self.assertEqual(reason, "")

    def test_hard_blocked_execution_returns_policy_metadata(self):
        policy_path = str(Path.cwd() / "dispatcher_security_policy_block_metadata.json")
        if os.path.exists(policy_path):
            os.remove(policy_path)

        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        try:
            with patch("core.safety_policy.POLICY_PATH", policy_path):
                result = asyncio.run(
                    dispatcher.route_and_execute(
                        "db_execute_query",
                        {"sql": "DROP USER app_user CASCADE"},
                        {"allow_modifications": True, "asset_type": "oracle", "protocol": "oracle"},
                    )
                )
        finally:
            if os.path.exists(policy_path):
                os.remove(policy_path)

        payload = json.loads(result)
        self.assertEqual(payload["status"], "BLOCKED")
        self.assertEqual(payload["policy_decision"], "deny")
        self.assertEqual(payload["primary_action"]["id"], "sql.dangerous_drop")
        self.assertEqual(payload["tool_policy"]["name"], "db_execute_query")
        self.assertEqual(payload["tool_policy"]["operation_mode"], "read_write")
        self.assertEqual(payload["tool_policy"]["approval_policy"], "guarded_write")
        self.assertEqual(payload["tool_policy"]["evidence_family"], "database")


if __name__ == "__main__":
    unittest.main()
