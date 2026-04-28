import os
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


if __name__ == "__main__":
    unittest.main()
