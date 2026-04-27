import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from api import routes


class TestSkillSecurity(unittest.TestCase):
    def test_evolve_skill_rejects_nested_file_name(self):
        from core.dispatcher import dispatcher

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(dispatcher, "_custom_skills_base", return_value=str(Path(tmp) / "custom")):
                result = asyncio.run(
                    dispatcher.route_and_execute(
                        "evolve_skill",
                        {
                            "skill_id": "safe-skill",
                            "file_name": "nested/SKILL.md",
                            "content": "---\nname: safe-skill\ndescription: demo\n---\n\nbody\n",
                        },
                        {"allow_modifications": True},
                    )
                )

        self.assertIn("非法文件名", json.loads(result)["error"])

    def test_evolve_skill_validates_skill_frontmatter(self):
        from core.dispatcher import dispatcher

        with tempfile.TemporaryDirectory() as tmp:
            target_base = Path(tmp) / "custom"
            with patch.object(dispatcher, "_custom_skills_base", return_value=str(target_base)):
                result = asyncio.run(
                    dispatcher.route_and_execute(
                        "evolve_skill",
                        {
                            "skill_id": "safe-skill",
                            "file_name": "SKILL.md",
                            "content": "missing frontmatter",
                        },
                        {"allow_modifications": True},
                    )
                )

            self.assertFalse((target_base / "safe-skill" / "SKILL.md").exists())

        self.assertIn("frontmatter", json.loads(result)["error"])

    def test_skill_frontmatter_validation_accepts_crlf(self):
        from core.dispatcher import dispatcher

        valid, reason = dispatcher._validate_skill_frontmatter(
            "safe-skill",
            "---\r\nname: safe-skill\r\ndescription: demo\r\n---\r\n\r\nbody\r\n",
        )

        self.assertTrue(valid, reason)

    def test_evolve_skill_writes_atomically_and_versions_existing_file(self):
        from core.dispatcher import dispatcher

        old_content = "---\nname: safe-skill\ndescription: old\n---\n\nold\n"
        new_content = "---\nname: safe-skill\ndescription: new\n---\n\nnew\n"
        with tempfile.TemporaryDirectory() as tmp:
            target_base = Path(tmp) / "custom"
            skill_dir = target_base / "safe-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(old_content, encoding="utf-8")

            with (
                patch.object(dispatcher, "_custom_skills_base", return_value=str(target_base)),
                patch.object(dispatcher, "refresh_skills"),
            ):
                result = asyncio.run(
                    dispatcher.route_and_execute(
                        "evolve_skill",
                        {
                            "skill_id": "safe-skill",
                            "file_name": "SKILL.md",
                            "content": new_content,
                        },
                        {"allow_modifications": True},
                    )
                )

            payload = json.loads(result)
            backups = list((skill_dir / ".versions").glob("SKILL.md.*.bak"))
            self.assertEqual(payload["status"], "SUCCESS")
            self.assertEqual((skill_dir / "SKILL.md").read_text(encoding="utf-8"), new_content)
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(encoding="utf-8"), old_content)

    def test_active_skill_paths_still_returns_registered_skill_paths(self):
        from core.dispatcher import SkillDispatcher

        dispatcher = SkillDispatcher.__new__(SkillDispatcher)
        dispatcher.skills_registry = {
            "safe-skill": {"source_path": str(Path.cwd() / "my_custom_skills" / "safe-skill")}
        }
        with patch.object(dispatcher, "refresh_skills"):
            paths = dispatcher.get_active_skill_paths(["safe-skill", "missing"])

        self.assertEqual(len(paths), 1)
        self.assertTrue(paths[0].endswith(str(Path("my_custom_skills") / "safe-skill")))

    def test_create_skill_rejects_invalid_id_with_http_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(routes, "CUSTOM_SKILLS_DIR", Path(tmp) / "custom"):
                with self.assertRaises(HTTPException) as ctx:
                    asyncio.run(
                        routes.create_skill(
                            routes.CreateSkillRequest(
                                skill_id="../escape",
                                description="bad",
                                instructions="bad",
                            )
                        )
                    )

        self.assertEqual(ctx.exception.status_code, 422)

    def test_create_skill_duplicate_returns_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            target_base = Path(tmp) / "custom"
            existing = target_base / "existing-skill"
            existing.mkdir(parents=True)
            (existing / "SKILL.md").write_text(
                "---\nname: existing-skill\ndescription: demo\n---\n",
                encoding="utf-8",
            )

            with patch.object(routes, "CUSTOM_SKILLS_DIR", target_base):
                with self.assertRaises(HTTPException) as ctx:
                    asyncio.run(
                        routes.create_skill(
                            routes.CreateSkillRequest(
                                skill_id="existing-skill",
                                description="demo",
                                instructions="body",
                            )
                        )
                    )

        self.assertEqual(ctx.exception.status_code, 409)

    def test_create_skill_writes_to_custom_skills_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            target_base = Path(tmp) / "custom"
            with (
                patch.object(routes, "CUSTOM_SKILLS_DIR", target_base),
                patch("core.dispatcher.dispatcher.refresh_skills"),
            ):
                response = asyncio.run(
                    routes.create_skill(
                        routes.CreateSkillRequest(
                            skill_id="new-skill",
                            description="demo",
                            instructions="body",
                            script_name="../check.py",
                            script_content="print('ok')",
                        )
                    )
                )

            self.assertEqual(response.status, "success")
            self.assertTrue((target_base / "new-skill" / "SKILL.md").exists())
            self.assertTrue((target_base / "new-skill" / "check.py").exists())

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

    def test_list_skill_versions_returns_backups_for_single_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target_base = Path(tmp) / "custom"
            versions_dir = target_base / "safe-skill" / ".versions"
            versions_dir.mkdir(parents=True)
            (target_base / "safe-skill" / "SKILL.md").write_text(
                "---\nname: safe-skill\ndescription: current\n---\n\ncurrent\n",
                encoding="utf-8",
            )
            (versions_dir / "SKILL.md.20260428010101.1.bak").write_text("old", encoding="utf-8")
            (versions_dir / "notes.py.20260428010101.1.bak").write_text("ignore", encoding="utf-8")

            with patch.object(routes, "CUSTOM_SKILLS_DIR", target_base):
                response = asyncio.run(routes.list_skill_versions("safe-skill"))

        versions = response.data["versions"]
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0]["id"], "SKILL.md.20260428010101.1.bak")

    def test_rollback_skill_version_restores_backup_and_versions_current_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target_base = Path(tmp) / "custom"
            skill_dir = target_base / "safe-skill"
            versions_dir = skill_dir / ".versions"
            versions_dir.mkdir(parents=True)
            current = "---\nname: safe-skill\ndescription: current\n---\n\ncurrent\n"
            previous = "---\nname: safe-skill\ndescription: previous\n---\n\nprevious\n"
            (skill_dir / "SKILL.md").write_text(current, encoding="utf-8")
            version_id = "SKILL.md.20260428010101.1.bak"
            (versions_dir / version_id).write_text(previous, encoding="utf-8")

            with (
                patch.object(routes, "CUSTOM_SKILLS_DIR", target_base),
                patch("core.dispatcher.dispatcher.refresh_skills"),
            ):
                response = asyncio.run(
                    routes.rollback_skill_version(
                        "safe-skill",
                        routes.SkillRollbackRequest(
                            file_name="SKILL.md",
                            version_id=version_id,
                        ),
                    )
                )

            backups = list(versions_dir.glob("SKILL.md.*.bak"))
            self.assertEqual(response.status, "success")
            self.assertEqual((skill_dir / "SKILL.md").read_text(encoding="utf-8"), previous)
            self.assertGreaterEqual(len(backups), 2)
            self.assertTrue(any(path.read_text(encoding="utf-8") == current for path in backups))

    def test_rollback_skill_version_rejects_traversal_version_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            target_base = Path(tmp) / "custom"
            skill_dir = target_base / "safe-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: safe-skill\ndescription: current\n---\n\ncurrent\n",
                encoding="utf-8",
            )

            with patch.object(routes, "CUSTOM_SKILLS_DIR", target_base):
                with self.assertRaises(HTTPException) as ctx:
                    asyncio.run(
                        routes.rollback_skill_version(
                            "safe-skill",
                            routes.SkillRollbackRequest(
                                file_name="SKILL.md",
                                version_id="../escape.bak",
                            ),
                        )
                    )

        self.assertEqual(ctx.exception.status_code, 422)

    def test_rollback_skill_version_validates_skill_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            target_base = Path(tmp) / "custom"
            skill_dir = target_base / "safe-skill"
            versions_dir = skill_dir / ".versions"
            versions_dir.mkdir(parents=True)
            current = "---\nname: safe-skill\ndescription: current\n---\n\ncurrent\n"
            (skill_dir / "SKILL.md").write_text(current, encoding="utf-8")
            version_id = "SKILL.md.20260428010101.1.bak"
            (versions_dir / version_id).write_text("missing frontmatter", encoding="utf-8")

            with patch.object(routes, "CUSTOM_SKILLS_DIR", target_base):
                with self.assertRaises(HTTPException) as ctx:
                    asyncio.run(
                        routes.rollback_skill_version(
                            "safe-skill",
                            routes.SkillRollbackRequest(
                                file_name="SKILL.md",
                                version_id=version_id,
                            ),
                        )
                    )

            self.assertEqual((skill_dir / "SKILL.md").read_text(encoding="utf-8"), current)

        self.assertEqual(ctx.exception.status_code, 422)

    def test_rollback_skill_version_rejects_non_utf8_skill_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            target_base = Path(tmp) / "custom"
            skill_dir = target_base / "safe-skill"
            versions_dir = skill_dir / ".versions"
            versions_dir.mkdir(parents=True)
            current = "---\nname: safe-skill\ndescription: current\n---\n\ncurrent\n"
            (skill_dir / "SKILL.md").write_text(current, encoding="utf-8")
            version_id = "SKILL.md.20260428010101.1.bak"
            (versions_dir / version_id).write_bytes(b"\xff\xfe\x00")

            with patch.object(routes, "CUSTOM_SKILLS_DIR", target_base):
                with self.assertRaises(HTTPException) as ctx:
                    asyncio.run(
                        routes.rollback_skill_version(
                            "safe-skill",
                            routes.SkillRollbackRequest(
                                file_name="SKILL.md",
                                version_id=version_id,
                            ),
                        )
                    )

            self.assertEqual((skill_dir / "SKILL.md").read_text(encoding="utf-8"), current)

        self.assertEqual(ctx.exception.status_code, 422)

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
