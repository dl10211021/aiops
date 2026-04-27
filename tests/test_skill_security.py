import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from api import routes


class TestSkillSecurity(unittest.TestCase):
    def test_migrate_skill_rejects_traversal_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "market-skill"
            source.mkdir()
            (source / "SKILL.md").write_text(
                "---\nname: market-skill\ndescription: demo\n---\n",
                encoding="utf-8",
            )

            with patch.object(routes, "CUSTOM_SKILLS_DIR", root / "custom"):
                with self.assertRaises(HTTPException) as ctx:
                    asyncio.run(
                        routes.migrate_skill(
                            routes.MigrateRequest(
                                source_path=str(source),
                                target_dir_name="../escape",
                            )
                        )
                    )

        self.assertEqual(ctx.exception.status_code, 422)

    def test_migrate_skill_copies_only_valid_skill_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "market-skill"
            source.mkdir()
            (source / "SKILL.md").write_text(
                "---\nname: market-skill\ndescription: demo\n---\n\nbody\n",
                encoding="utf-8",
            )
            target_base = root / "custom"

            with (
                patch.object(routes, "CUSTOM_SKILLS_DIR", target_base),
                patch("core.dispatcher.dispatcher.refresh_skills"),
            ):
                response = asyncio.run(
                    routes.migrate_skill(
                        routes.MigrateRequest(
                            source_path=str(source),
                            target_dir_name="market_skill",
                        )
                    )
                )

            self.assertEqual(response.status, "success")
            self.assertTrue((target_base / "market_skill" / "SKILL.md").exists())

    def test_prompts_reference_registered_subagent_tool_name(self):
        root = Path.cwd()
        checked = [
            root / "api" / "routes.py",
            root / "core" / "heartbeat.py",
            root / "workspaces" / "master" / "SOUL.md",
        ]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in checked)

        self.assertNotIn("delegate_task_to_agent", combined)
        self.assertIn("dispatch_sub_agents", combined)


if __name__ == "__main__":
    unittest.main()
