import unittest

from core.session_groups import apply_primary_session_group, normalize_session_group_name


class TestSessionGroups(unittest.TestCase):
    def test_normalize_session_group_name_compacts_whitespace(self):
        self.assertEqual(normalize_session_group_name("  数据库   核心组  "), "数据库 核心组")

    def test_apply_primary_session_group_preserves_secondary_tags(self):
        self.assertEqual(
            apply_primary_session_group(["旧组", "P0", "数据库"], "数据库核心组"),
            ["数据库核心组", "P0", "数据库"],
        )

    def test_apply_primary_session_group_rejects_blank_name(self):
        with self.assertRaises(ValueError):
            apply_primary_session_group(["旧组"], "   ")


if __name__ == "__main__":
    unittest.main()
