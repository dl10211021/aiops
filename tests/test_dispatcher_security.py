import os
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
