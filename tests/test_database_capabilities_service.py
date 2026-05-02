import unittest
from unittest.mock import patch

from core.database_capabilities_service import (
    get_database_driver_capabilities_record,
    get_oracle_client_config_record,
)


class TestDatabaseCapabilitiesService(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
