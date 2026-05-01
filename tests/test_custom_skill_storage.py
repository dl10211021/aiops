import tempfile
import unittest
from pathlib import Path

from core.custom_skill_storage import (
    CustomSkillStorageError,
    atomic_replace_bytes,
    resolve_custom_skill_dir,
    resolve_custom_skill_file,
    resolve_custom_skill_version_file,
)


class TestCustomSkillStorage(unittest.TestCase):
    def test_resolves_safe_custom_skill_paths_under_base_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / "custom"

            skill_dir = resolve_custom_skill_dir(base_dir, "safe-skill_1")
            skill_file = resolve_custom_skill_file(base_dir, "safe-skill_1", "SKILL.md")
            version_file = resolve_custom_skill_version_file(
                base_dir,
                "safe-skill_1",
                "SKILL.md.20260428010101.1.bak",
            )

        self.assertEqual(skill_dir.name, "safe-skill_1")
        self.assertEqual(skill_file.name, "SKILL.md")
        self.assertEqual(version_file.parent.name, ".versions")

    def test_rejects_traversal_and_nested_file_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / "custom"

            with self.assertRaises(CustomSkillStorageError) as dir_ctx:
                resolve_custom_skill_dir(base_dir, "../escape")
            with self.assertRaises(CustomSkillStorageError) as file_ctx:
                resolve_custom_skill_file(base_dir, "safe-skill", "../SKILL.md")
            with self.assertRaises(CustomSkillStorageError) as version_ctx:
                resolve_custom_skill_version_file(base_dir, "safe-skill", "../old.bak")

        self.assertEqual(dir_ctx.exception.status_code, 422)
        self.assertEqual(file_ctx.exception.status_code, 422)
        self.assertEqual(version_ctx.exception.status_code, 422)

    def test_atomic_replace_bytes_replaces_file_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "SKILL.md"
            target.write_text("old", encoding="utf-8")

            atomic_replace_bytes(target, b"new")

            self.assertEqual(target.read_text(encoding="utf-8"), "new")
