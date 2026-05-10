import tempfile
import unittest
from pathlib import Path

from core.skill_registry_service import SkillRegistryService


def write_skill(root: Path, skill_id: str, body: str = "### Run Check\nbody") -> Path:
    skill_dir = root / skill_id
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {skill_id}\ndescription: Demo skill\n---\n\n{body}\n",
        encoding="utf-8",
    )
    return skill_dir


class TestSkillRegistryService(unittest.TestCase):
    def test_refresh_scans_installed_skills_and_uses_cache_until_forced(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_root = Path(tmp) / "skills"
            write_skill(skill_root, "demo-skill")
            service = SkillRegistryService(
                skill_directories=[str(skill_root)],
                market_directories=[],
                refresh_interval=3600,
            )

            service.refresh_skills()
            write_skill(skill_root, "new-skill")
            service.refresh_skills()

            self.assertIn("demo-skill", service.skills_registry)
            self.assertNotIn("new-skill", service.skills_registry)

            service.refresh_skills(force=True)

            self.assertIn("new-skill", service.skills_registry)

    def test_market_scan_excludes_installed_skill_folder_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_root = Path(tmp) / "skills"
            market_root = Path(tmp) / "market"
            write_skill(skill_root, "local-skill")
            write_skill(market_root, "local-skill")
            write_skill(market_root, "market-skill")
            service = SkillRegistryService(
                skill_directories=[str(skill_root)],
                market_directories=[str(market_root)],
            )
            service.refresh_skills(force=True)

            result = service.get_market_skills()

            self.assertEqual([skill["id"] for skill in result], ["market-skill"])
            self.assertTrue(result[0]["is_market"])

    def test_skill_instructions_respect_protocol_only_sessions(self):
        service = SkillRegistryService(skill_directories=[], market_directories=[])
        service.skills_registry = {
            "safe-skill": {
                "id": "safe-skill",
                "name": "Safe Skill",
                "instructions": "Run protocol checks only.",
                "source_path": "C:/skills/safe-skill",
            }
        }

        instructions = service.get_skill_instructions(
            ["safe-skill"],
            allow_local_scripts=False,
        )

        self.assertIn("协议优先约束", instructions)
        self.assertIn("Run protocol checks only.", instructions)
        self.assertNotIn("<SKILL_ABSOLUTE_PATH>", instructions)

    def test_active_skill_paths_are_real_paths_for_registered_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_root = Path(tmp) / "skills"
            skill_dir = write_skill(skill_root, "safe-skill")
            service = SkillRegistryService(
                skill_directories=[str(skill_root)],
                market_directories=[],
            )

            paths = service.get_active_skill_paths(["safe-skill", "missing"])

            self.assertEqual(paths, [str(skill_dir.resolve())])


if __name__ == "__main__":
    unittest.main()
