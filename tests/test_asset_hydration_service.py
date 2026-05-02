import asyncio
import unittest
from unittest.mock import Mock

from core.asset_hydration_service import hydrate_assets
from core.hydration_status_service import (
    finish_hydrate_run,
    get_hydrate_status_record,
    start_hydrate_run,
)


def _asset(host: str, **overrides):
    asset = {
        "host": host,
        "port": None,
        "username": None,
        "password": "secret",
        "skills": ["linux"],
        "agent_profile": "default",
        "remark": "server",
        "asset_type": "ssh",
        "protocol": None,
        "extra_args": {},
        "tags": ["未分组"],
    }
    asset.update(overrides)
    return asset


class FakeMemoryDb:
    def __init__(self, assets):
        self.assets = assets

    def get_all_assets(self):
        return self.assets


class FakeSshManager:
    def __init__(self, failing_hosts=None):
        self.failing_hosts = set(failing_hosts or [])
        self.calls = []

    def connect(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs["host"] in self.failing_hosts:
            raise RuntimeError("connection failed")
        return f"sid-{kwargs['host']}"


class TestAssetHydrationService(unittest.TestCase):
    def setUp(self):
        start_hydrate_run(0)
        finish_hydrate_run()

    def test_hydrate_assets_reconnects_assets_and_tracks_status(self):
        memory_db = FakeMemoryDb(
            [
                _asset("10.0.0.1"),
                _asset("10.0.0.2", port=2200, username="ops", tags=["prod"]),
            ]
        )
        ssh_manager = FakeSshManager()
        logger = Mock()

        asyncio.run(hydrate_assets(memory_db, ssh_manager, logger))

        self.assertEqual(
            get_hydrate_status_record(),
            {"total": 2, "done": 2, "success": 2, "running": False},
        )
        self.assertEqual(len(ssh_manager.calls), 2)
        self.assertEqual(ssh_manager.calls[0]["port"], 22)
        self.assertEqual(ssh_manager.calls[0]["username"], "")
        self.assertFalse(ssh_manager.calls[0]["allow_modifications"])
        self.assertTrue(ssh_manager.calls[0]["lazy"])
        self.assertEqual(ssh_manager.calls[1]["port"], 2200)
        self.assertEqual(ssh_manager.calls[1]["username"], "ops")
        logger.info.assert_called_once()

    def test_hydrate_assets_records_failed_connection_without_stopping_batch(self):
        memory_db = FakeMemoryDb([_asset("10.0.0.1"), _asset("10.0.0.2")])
        ssh_manager = FakeSshManager(failing_hosts={"10.0.0.2"})
        logger = Mock()

        asyncio.run(hydrate_assets(memory_db, ssh_manager, logger))

        self.assertEqual(
            get_hydrate_status_record(),
            {"total": 2, "done": 2, "success": 1, "running": False},
        )
        logger.error.assert_called_once()
        logger.info.assert_called_once()

    def test_hydrate_assets_finishes_empty_run(self):
        memory_db = FakeMemoryDb([])
        ssh_manager = FakeSshManager()
        logger = Mock()

        asyncio.run(hydrate_assets(memory_db, ssh_manager, logger))

        self.assertEqual(
            get_hydrate_status_record(),
            {"total": 0, "done": 0, "success": 0, "running": False},
        )
        self.assertEqual(ssh_manager.calls, [])
        logger.info.assert_not_called()


if __name__ == "__main__":
    unittest.main()
