import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core.connection_request_service import (
    asset_matches_connection_request,
    normalize_private_key_path,
    restore_connection_request_secrets,
    restore_masked_extra_args,
    restore_masked_password,
)


class FakeMemoryDB:
    def __init__(self, assets):
        self.assets = assets

    def get_all_assets(self):
        return self.assets


def request(**overrides):
    base = {
        "host": "db.local",
        "port": 3306,
        "username": "ops",
        "password": "********",
        "asset_type": "mysql",
        "protocol": "mysql",
        "extra_args": {"db_type": "mysql", "database": "********", "token": "plain"},
        "remark": "",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class TestConnectionRequestService(unittest.TestCase):
    def test_asset_match_uses_identity_not_only_raw_asset_type(self):
        req = request(asset_type="mysql", protocol="mysql")
        asset = {
            "host": "db.local",
            "port": 3306,
            "username": "ops",
            "asset_type": "database",
            "protocol": "mysql",
            "extra_args": {"db_type": "mysql"},
            "remark": "",
        }

        self.assertTrue(asset_matches_connection_request(asset, req))

    def test_restores_only_masked_extra_args_from_matching_asset(self):
        req = request()
        memory_db = FakeMemoryDB(
            [
                {
                    "host": "db.local",
                    "port": 3306,
                    "username": "ops",
                    "asset_type": "mysql",
                    "protocol": "mysql",
                    "extra_args": {
                        "db_type": "mysql",
                        "database": "ops_db",
                        "token": "stored-token",
                    },
                    "password": "stored-password",
                    "remark": "",
                }
            ]
        )

        restored = restore_masked_extra_args(req, memory_db)

        self.assertEqual(restored["database"], "ops_db")
        self.assertEqual(restored["token"], "plain")

    def test_restores_masked_password_from_matching_asset(self):
        req = request()
        memory_db = FakeMemoryDB(
            [
                {
                    "host": "db.local",
                    "port": 3306,
                    "username": "ops",
                    "asset_type": "mysql",
                    "protocol": "mysql",
                    "extra_args": {"db_type": "mysql"},
                    "password": "stored-password",
                    "remark": "",
                }
            ]
        )

        self.assertEqual(restore_masked_password(req, memory_db), "stored-password")

    def test_password_and_extra_args_passthrough_when_not_masked(self):
        req = request(password="typed", extra_args={"database": "typed-db"})
        memory_db = FakeMemoryDB([])

        self.assertEqual(restore_masked_password(req, memory_db), "typed")
        self.assertEqual(restore_masked_extra_args(req, memory_db), {"database": "typed-db"})

    def test_restores_request_extra_args_and_effective_password_together(self):
        req = request()
        memory_db = FakeMemoryDB(
            [
                {
                    "host": "db.local",
                    "port": 3306,
                    "username": "ops",
                    "asset_type": "mysql",
                    "protocol": "mysql",
                    "extra_args": {"db_type": "mysql", "database": "ops_db"},
                    "password": "stored-password",
                    "remark": "",
                }
            ]
        )

        restored_req, restored_password = restore_connection_request_secrets(req, memory_db)

        self.assertIsInstance(restored_req, SimpleNamespace)
        self.assertIsNot(restored_req, req)
        self.assertEqual(restored_req.extra_args["database"], "ops_db")
        self.assertEqual(restored_password, "stored-password")

    def test_restore_connection_request_secrets_uses_default_memory_db(self):
        req = request()
        memory_db = FakeMemoryDB(
            [
                {
                    "host": "db.local",
                    "port": 3306,
                    "username": "ops",
                    "asset_type": "mysql",
                    "protocol": "mysql",
                    "extra_args": {"db_type": "mysql", "database": "ops_db"},
                    "password": "stored-password",
                    "remark": "",
                }
            ]
        )

        with patch("core.memory.memory_db", memory_db):
            restored_req, restored_password = restore_connection_request_secrets(req)

        self.assertEqual(restored_req.extra_args["database"], "ops_db")
        self.assertEqual(restored_password, "stored-password")

    def test_normalize_private_key_path_treats_frontend_placeholder_as_empty(self):
        self.assertIsNone(normalize_private_key_path(None))
        self.assertIsNone(normalize_private_key_path(""))
        self.assertIsNone(normalize_private_key_path("string"))
        self.assertEqual(normalize_private_key_path("C:/keys/id_rsa"), "C:/keys/id_rsa")


if __name__ == "__main__":
    unittest.main()
