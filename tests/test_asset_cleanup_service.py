import unittest
from unittest.mock import patch

from core.asset_cleanup_service import (
    apply_asset_cleanup_record,
    build_asset_cleanup_plan_record,
)


class TestAssetCleanupService(unittest.TestCase):
    def test_build_asset_cleanup_plan_record_uses_cleanup_module(self):
        plan = {"changes": [], "duplicates": [], "summary": {"assets_scanned": 2}}

        with patch("core.asset_cleanup_service.asset_cleanup.build_asset_cleanup_plan", return_value=plan):
            self.assertEqual(build_asset_cleanup_plan_record(), plan)

    def test_apply_asset_cleanup_record_uses_cleanup_module(self):
        report = {
            "backup_path": "asset_cleanup_backup.json",
            "removed_ids": [1],
            "summary": {"duplicates_removed": 1},
        }

        with patch("core.asset_cleanup_service.asset_cleanup.apply_asset_cleanup", return_value=report):
            self.assertEqual(apply_asset_cleanup_record(), report)


if __name__ == "__main__":
    unittest.main()
