import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.custom_skill_create_service import (
    CustomSkillCreateServiceError,
    create_custom_skill_record,
)


class FakeDispatcher:
    def __init__(self):
        self.refresh_calls = []

    def _backup_existing_skill_file(self, path: str):
        target = Path(path)
        if not target.exists():
            return None
        versions_dir = target.parent / ".versions"
        versions_dir.mkdir(exist_ok=True)
        backup = versions_dir / f"{target.name}.test.bak"
        backup.write_bytes(target.read_bytes())
        return str(backup)

    def refresh_skills(self, force=False):
        self.refresh_calls.append(force)


class TestCustomSkillCreateService(unittest.TestCase):
    def test_creates_skill_and_optional_script_under_custom_base(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / "custom"
            dispatcher = FakeDispatcher()

            result = create_custom_skill_record(
                base_dir,
                dispatcher,
                skill_id="new-skill",
                description="demo",
                instructions="body",
                script_name="check.py",
                script_content="print('ok')",
            )

            skill_dir = base_dir / "new-skill"
            self.assertTrue((skill_dir / "SKILL.md").exists())
            self.assertTrue((skill_dir / "check.py").exists())
            self.assertFalse(result["data"]["updated"])
            self.assertEqual(result["data"]["backup_paths"], [])
            self.assertEqual(dispatcher.refresh_calls, [True])

    def test_create_uses_default_dispatcher_when_not_injected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / "custom"
            dispatcher = FakeDispatcher()

            with patch("core.dispatcher.dispatcher", dispatcher):
                result = create_custom_skill_record(
                    base_dir,
                    skill_id="new-skill",
                    description="demo",
                    instructions="body",
                )

            self.assertEqual(result["data"]["skill_id"], "new-skill")
            self.assertEqual(dispatcher.refresh_calls, [True])

    def test_rejects_invalid_or_duplicate_skill_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / "custom"
            dispatcher = FakeDispatcher()

            with self.assertRaises(CustomSkillCreateServiceError) as invalid_ctx:
                create_custom_skill_record(
                    base_dir,
                    dispatcher,
                    skill_id="../escape",
                    description="demo",
                    instructions="body",
                )

            existing = base_dir / "existing-skill"
            existing.mkdir(parents=True)
            (existing / "SKILL.md").write_text(
                "---\nname: existing-skill\ndescription: demo\n---\n",
                encoding="utf-8",
            )
            with self.assertRaises(CustomSkillCreateServiceError) as duplicate_ctx:
                create_custom_skill_record(
                    base_dir,
                    dispatcher,
                    skill_id="existing-skill",
                    description="demo",
                    instructions="body",
                )

        self.assertEqual(invalid_ctx.exception.status_code, 422)
        self.assertEqual(duplicate_ctx.exception.status_code, 409)

    def test_overwrite_versions_existing_skill_and_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / "custom"
            dispatcher = FakeDispatcher()
            skill_dir = base_dir / "existing-skill"
            skill_dir.mkdir(parents=True)
            old_skill = "---\nname: existing-skill\ndescription: old\n---\n\nold\n"
            old_script = "print('old')\n"
            (skill_dir / "SKILL.md").write_text(old_skill, encoding="utf-8")
            (skill_dir / "check.py").write_text(old_script, encoding="utf-8")

            result = create_custom_skill_record(
                base_dir,
                dispatcher,
                skill_id="existing-skill",
                description="new",
                instructions="new body",
                script_name="check.py",
                script_content="print('new')\n",
                overwrite_existing=True,
            )

            backups = result["data"]["backup_paths"]
            skill_backup = Path(backups[0]).read_text(encoding="utf-8")
            script_backup = Path(backups[1]).read_text(encoding="utf-8")

        self.assertTrue(result["data"]["updated"])
        self.assertEqual(skill_backup, old_skill)
        self.assertEqual(script_backup, old_script)

    def test_script_name_and_content_must_be_provided_together(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(CustomSkillCreateServiceError) as ctx:
                create_custom_skill_record(
                    Path(tmp) / "custom",
                    FakeDispatcher(),
                    skill_id="new-skill",
                    description="demo",
                    instructions="body",
                    script_name="check.py",
                    script_content=None,
                )

        self.assertEqual(ctx.exception.status_code, 422)
