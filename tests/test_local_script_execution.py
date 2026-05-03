import json
import shutil
import unittest
from pathlib import Path

from core.local_script_execution import execute_local_script, validate_local_execution


class LocalScriptExecutionTests(unittest.TestCase):
    def tearDown(self):
        for path in (Path.cwd() / "tests").glob("tmp_local_script_execution_*"):
            shutil.rmtree(path, ignore_errors=True)

    def _root(self, name: str) -> Path:
        root = Path.cwd() / "tests" / f"tmp_local_script_execution_{name}"
        root.mkdir(parents=True, exist_ok=True)
        return root

    def test_validate_local_execution_allows_interpreter_under_active_skill_path(self):
        skill_dir = self._root("allowed") / "safe-skill"
        skill_dir.mkdir()

        allowed, reason = validate_local_execution(
            "python check.py",
            str(skill_dir),
            [str(skill_dir)],
        )

        self.assertTrue(allowed, reason)

    def test_validate_local_execution_rejects_shell_control_operators(self):
        skill_dir = self._root("shell_control") / "safe-skill"
        skill_dir.mkdir()

        allowed, reason = validate_local_execution(
            "python check.py && whoami",
            str(skill_dir),
            [str(skill_dir)],
        )

        self.assertFalse(allowed)
        self.assertIn("Shell", reason)

    def test_execute_local_script_sets_utf8_mode(self):
        skill_dir = self._root("utf8")
        (skill_dir / "check_env.py").write_text(
            "import os\nprint(os.environ.get('PYTHONUTF8'))\n",
            encoding="utf-8",
        )

        payload = json.loads(execute_local_script("python check_env.py", str(skill_dir)))

        self.assertEqual(payload["status"], "SUCCESS")
        self.assertIn("1", payload["output"])


if __name__ == "__main__":
    unittest.main()
