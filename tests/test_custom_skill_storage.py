import tempfile
import unittest
from pathlib import Path

from core.custom_skill_storage import (
    CustomSkillStorageError,
    atomic_replace_bytes,
    normalize_custom_skill_file_name,
    resolve_custom_skill_dir,
    resolve_custom_skill_file,
    resolve_custom_skill_resource_file,
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

    def test_resolves_nested_bundled_resource_paths_under_skill_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / "custom"

            script_file = resolve_custom_skill_resource_file(
                base_dir,
                "safe-skill",
                "scripts/helpers/check.py",
            )
            eval_file = resolve_custom_skill_resource_file(
                base_dir,
                "safe-skill",
                "evals/evals.json",
            )

        self.assertEqual(script_file.parts[-3:], ("scripts", "helpers", "check.py"))
        self.assertEqual(eval_file.parts[-2:], ("evals", "evals.json"))

    def test_rejects_unsafe_nested_resource_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / "custom"

            with self.assertRaises(CustomSkillStorageError) as traversal_ctx:
                resolve_custom_skill_resource_file(base_dir, "safe-skill", "scripts/../SKILL.md")
            with self.assertRaises(CustomSkillStorageError) as unknown_dir_ctx:
                resolve_custom_skill_resource_file(base_dir, "safe-skill", "notes/internal.md")
            with self.assertRaises(CustomSkillStorageError) as drive_ctx:
                normalize_custom_skill_file_name("C:/secret.txt", allow_nested=True)

        self.assertEqual(traversal_ctx.exception.status_code, 422)
        self.assertEqual(unknown_dir_ctx.exception.status_code, 422)
        self.assertEqual(drive_ctx.exception.status_code, 422)

    def test_atomic_replace_bytes_replaces_file_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "SKILL.md"
            target.write_text("old", encoding="utf-8")

            atomic_replace_bytes(target, b"new")

            self.assertEqual(target.read_text(encoding="utf-8"), "new")
