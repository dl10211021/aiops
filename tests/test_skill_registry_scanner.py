import shutil
import unittest
from pathlib import Path

from core import skill_registry_scanner


class SkillRegistryScannerTests(unittest.TestCase):
    def tearDown(self):
        for path in (Path.cwd() / "tests").glob("tmp_skill_registry_scanner_*"):
            shutil.rmtree(path, ignore_errors=True)

    def _skill_dir(self, name: str, under: str = "my_custom_skills") -> Path:
        skill_dir = Path.cwd() / "tests" / f"tmp_skill_registry_scanner_{name}" / under / "safe-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        return skill_dir

    def test_parse_installed_skill_md_keeps_private_source_and_tool_count(self):
        skill_dir = self._skill_dir("installed")
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            "---\nname: safe-skill\ndescription: demo\n---\n\n### Check\n```python\nprint(1)\n```\n",
            encoding="utf-8",
        )

        skill = skill_registry_scanner.parse_installed_skill_md(str(skill_md), str(skill_dir))

        self.assertEqual(skill["id"], "safe-skill")
        self.assertEqual(skill["source_type"], "OpsCore 私有技能")
        self.assertEqual(skill["tool_count"], 1)
        self.assertFalse(skill.get("is_market", False))

    def test_parse_market_skill_md_marks_external_market_skill(self):
        skill_dir = self._skill_dir("market", "external_market")
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            "---\nname: market-skill\ndescription: demo\n---\n\nbody\n",
            encoding="utf-8",
        )

        skill = skill_registry_scanner.parse_market_skill_md(str(skill_md), str(skill_dir))

        self.assertEqual(skill["id"], "market-skill")
        self.assertEqual(skill["source_type"], "外部未知技能")
        self.assertTrue(skill["is_market"])

    def test_format_skills_for_ui_extracts_headings_and_keeps_fallback(self):
        formatted = skill_registry_scanner.format_skills_for_ui(
            [
                {
                    "id": "safe-skill",
                    "name": "Safe Skill",
                    "description": "demo",
                    "instructions": "### Health Check\n- **Disk**:\n",
                    "source_path": "x",
                    "source_type": "OpsCore 私有技能",
                    "tool_count": 1,
                },
                {
                    "id": "plain-skill",
                    "name": "Plain Skill",
                    "description": "demo",
                    "instructions": "plain body",
                    "source_path": "y",
                    "source_type": "OpsCore 内置技能",
                    "tool_count": 1,
                },
            ]
        )

        self.assertIn("Health Check", formatted[0]["tools"])
        self.assertIn("Disk", formatted[0]["tools"])
        self.assertEqual(formatted[1]["tools"], ["基于 Markdown 的自定义指令"])


if __name__ == "__main__":
    unittest.main()
