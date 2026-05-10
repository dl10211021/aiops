import unittest
from unittest.mock import patch

from core.database_capabilities_service import (
    clear_database_capabilities_cache,
    get_database_driver_capabilities_record,
    get_oracle_client_config_record,
)


class TestDatabaseCapabilitiesService(unittest.TestCase):
    def setUp(self):
        clear_database_capabilities_cache()

    def tearDown(self):
        clear_database_capabilities_cache()

    def test_get_oracle_client_config_record_uses_db_manager(self):
        config = {"detected": True, "lib_dir": "D:/oracle/instantclient"}

        with patch(
            "core.database_capabilities_service.db_manager.discover_oracle_client_lib_dir",
            return_value=config,
        ):
            self.assertEqual(get_oracle_client_config_record(), config)

    def test_get_database_driver_capabilities_record_uses_db_manager(self):
        capabilities = {"drivers": {"oracle": {"id": "oracle", "ready": True}}}

        with patch(
            "core.database_capabilities_service.db_manager.get_database_driver_capabilities",
            return_value=capabilities,
        ):
            self.assertEqual(get_database_driver_capabilities_record(), capabilities)

    def test_database_driver_capabilities_are_cached_briefly(self):
        capabilities = {"drivers": {"oracle": {"id": "oracle", "ready": True}}}

        with patch(
            "core.database_capabilities_service.db_manager.get_database_driver_capabilities",
            return_value=capabilities,
        ) as loader:
            self.assertEqual(get_database_driver_capabilities_record(), capabilities)
            self.assertEqual(get_database_driver_capabilities_record(), capabilities)

        self.assertEqual(loader.call_count, 1)


if __name__ == "__main__":
    unittest.main()
