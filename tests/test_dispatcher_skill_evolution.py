import json
import shutil
import unittest
from pathlib import Path

from core.dispatcher_skill_evolution import execute_skill_evolution_tool


class DispatcherSkillEvolutionTests(unittest.TestCase):
    def tearDown(self):
        for path in (Path.cwd() / "tests").glob("tmp_dispatcher_skill_evolution_*"):
            shutil.rmtree(path, ignore_errors=True)

    def _root(self, name: str) -> Path:
        root = Path.cwd() / "tests" / f"tmp_dispatcher_skill_evolution_{name}"
        root.mkdir(parents=True, exist_ok=True)
        return root

    def test_execute_skill_evolution_writes_and_refreshes(self):
        calls = []
        root = self._root("write")
        content = "---\nname: safe-skill\ndescription: demo\n---\n\nbody\n"

        result = execute_skill_evolution_tool(
            {"skill_id": "safe-skill", "file_name": "SKILL.md", "content": content},
            str(root),
            lambda: calls.append("refresh"),
        )

        payload = json.loads(result)
        self.assertEqual(payload["status"], "SUCCESS")
        self.assertEqual((root / "safe-skill" / "SKILL.md").read_text(encoding="utf-8"), content)
        self.assertEqual(calls, ["refresh"])

    def test_execute_skill_evolution_rejects_invalid_resource_name(self):
        root = self._root("invalid")
        result = execute_skill_evolution_tool(
            {"skill_id": "safe-skill", "file_name": "../bad.py", "content": "bad"},
            str(root),
            lambda: None,
        )

        payload = json.loads(result)
        self.assertIn("非法", payload["error"])
        self.assertFalse((root / "safe-skill").exists())


if __name__ == "__main__":
    unittest.main()
