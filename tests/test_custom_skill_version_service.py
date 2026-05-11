import os
import tempfile
import unittest
from pathlib import Path

from core.custom_skill_version_service import (
    CustomSkillVersionServiceError,
    list_custom_skill_version_records,
)


class TestCustomSkillVersionService(unittest.TestCase):
    def test_lists_matching_versions_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / "custom"
            versions_dir = base_dir / "safe-skill" / ".versions"
            versions_dir.mkdir(parents=True)
            (base_dir / "safe-skill" / "SKILL.md").write_text("current", encoding="utf-8")
            older = versions_dir / "SKILL.md.20260428010101.1.bak"
            newer = versions_dir / "SKILL.md.20260428020202.1.bak"
            ignored = versions_dir / "notes.py.20260428020202.1.bak"
            older.write_text("older", encoding="utf-8")
            newer.write_text("newer", encoding="utf-8")
            ignored.write_text("ignored", encoding="utf-8")
            os.utime(older, (100, 100))
            os.utime(newer, (100, 100))

            versions = list_custom_skill_version_records(base_dir, "safe-skill")

        self.assertEqual([item["id"] for item in versions], [newer.name, older.name])
        self.assertEqual({item["file_name"] for item in versions}, {"SKILL.md"})

    def test_missing_skill_maps_to_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(CustomSkillVersionServiceError) as ctx:
                list_custom_skill_version_records(Path(tmp) / "custom", "missing-skill")

        self.assertEqual(ctx.exception.status_code, 404)

    def test_invalid_path_maps_to_storage_error_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(CustomSkillVersionServiceError) as ctx:
                list_custom_skill_version_records(Path(tmp) / "custom", "../escape")

        self.assertEqual(ctx.exception.status_code, 422)
