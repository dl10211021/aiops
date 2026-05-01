import tempfile
import unittest
from pathlib import Path

from core.custom_skill_migration_service import (
    CustomSkillMigrationServiceError,
    migrate_custom_skill_record,
)


class FakeDispatcher:
    def __init__(self):
        self.refresh_calls = []

    def refresh_skills(self, force=False):
        self.refresh_calls.append(force)


class TestCustomSkillMigrationService(unittest.TestCase):
    def test_migrates_skill_directory_and_refreshes_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "external-skill"
            source.mkdir()
            (source / "SKILL.md").write_text(
                "---\nname: imported-skill\ndescription: demo\n---\n\nbody\n",
                encoding="utf-8",
            )
            (source / "notes.md").write_text("notes", encoding="utf-8")
            base_dir = root / "custom"
            dispatcher = FakeDispatcher()

            result = migrate_custom_skill_record(
                base_dir,
                dispatcher,
                source_path=str(source),
                target_dir_name="imported-skill",
            )

            dest = base_dir / "imported-skill"
            self.assertTrue((dest / "SKILL.md").is_file())
            self.assertEqual((dest / "notes.md").read_text(encoding="utf-8"), "notes")
            self.assertEqual(dispatcher.refresh_calls, [True])
            self.assertEqual(result["message"], "卡带 imported-skill 已成功导入专属库！")

    def test_overwrites_existing_destination_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "external-skill"
            source.mkdir()
            (source / "SKILL.md").write_text(
                "---\nname: imported-skill\ndescription: new\n---\n\nnew\n",
                encoding="utf-8",
            )
            base_dir = root / "custom"
            existing = base_dir / "imported-skill"
            existing.mkdir(parents=True)
            (existing / "stale.txt").write_text("stale", encoding="utf-8")

            migrate_custom_skill_record(
                base_dir,
                FakeDispatcher(),
                source_path=str(source),
                target_dir_name="imported-skill",
            )

            self.assertFalse((existing / "stale.txt").exists())
            self.assertIn("description: new", (existing / "SKILL.md").read_text(encoding="utf-8"))

    def test_rejects_missing_source_or_skill_md_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base_dir = root / "custom"
            empty_source = root / "empty"
            empty_source.mkdir()

            with self.assertRaises(CustomSkillMigrationServiceError) as missing_dir_ctx:
                migrate_custom_skill_record(
                    base_dir,
                    FakeDispatcher(),
                    source_path=str(root / "missing"),
                    target_dir_name="imported-skill",
                )
            with self.assertRaises(CustomSkillMigrationServiceError) as missing_skill_ctx:
                migrate_custom_skill_record(
                    base_dir,
                    FakeDispatcher(),
                    source_path=str(empty_source),
                    target_dir_name="imported-skill",
                )

            self.assertFalse((base_dir / "imported-skill").exists())

        self.assertEqual(missing_dir_ctx.exception.status_code, 422)
        self.assertEqual(missing_skill_ctx.exception.status_code, 422)

    def test_rejects_invalid_target_dir_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "external-skill"
            source.mkdir()
            (source / "SKILL.md").write_text(
                "---\nname: imported-skill\ndescription: demo\n---\n",
                encoding="utf-8",
            )

            with self.assertRaises(CustomSkillMigrationServiceError) as ctx:
                migrate_custom_skill_record(
                    root / "custom",
                    FakeDispatcher(),
                    source_path=str(source),
                    target_dir_name="../escape",
                )

        self.assertEqual(ctx.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
