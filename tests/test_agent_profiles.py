import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from core import agent_profiles


class TestAgentProfiles(unittest.TestCase):
    def tearDown(self):
        for path in (Path.cwd() / "tests").glob("tmp_agent_profiles_*"):
            shutil.rmtree(path, ignore_errors=True)

    def _module_file(self, name: str) -> tuple[Path, str]:
        root = Path.cwd() / "tests" / f"tmp_agent_profiles_{name}"
        module_dir = root / "core"
        module_dir.mkdir(parents=True, exist_ok=True)
        module_file = module_dir / "agent_profiles.py"
        module_file.write_text("", encoding="utf-8")
        return root, str(module_file)

    def test_load_agent_profile_prompt_reads_workspace_soul(self):
        root, module_file = self._module_file("custom")
        profile_dir = root / "workspaces" / "ops"
        profile_dir.mkdir(parents=True, exist_ok=True)
        (profile_dir / "SOUL.md").write_text("自定义 Agent 人格", encoding="utf-8")

        with patch.object(agent_profiles, "__file__", module_file):
            prompt = agent_profiles.load_agent_profile_prompt("ops")

        self.assertEqual(prompt, "自定义 Agent 人格")

    def test_load_agent_profile_prompt_returns_default_when_missing(self):
        _, module_file = self._module_file("missing")

        with patch.object(agent_profiles, "__file__", module_file):
            prompt = agent_profiles.load_agent_profile_prompt("missing")

        self.assertEqual(prompt, agent_profiles.DEFAULT_AGENT_PROFILE_PROMPT)


if __name__ == "__main__":
    unittest.main()
