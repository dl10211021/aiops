import asyncio
import sys
import unittest
import warnings
from types import ModuleType
from unittest.mock import patch

warnings.filterwarnings(
    "ignore",
    message=r"Please use `import python_multipart` instead\.",
    category=PendingDeprecationWarning,
)

from api import routes


class TestSystemInfoRoutes(unittest.TestCase):
    def test_oracle_client_config_preserves_response_shape(self):
        config = {
            "detected": True,
            "lib_dir": "D:/oracle/instantclient",
            "source": "auto",
        }

        with patch(
            "api.routes.get_oracle_client_config_record",
            return_value=config,
        ):
            response = asyncio.run(routes.get_oracle_client_config())

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data, config)

    def test_database_driver_capabilities_preserves_response_shape(self):
        capabilities = {"drivers": {"oracle": {"id": "oracle", "ready": True}}}

        with patch(
            "api.routes.get_database_driver_capabilities_record",
            return_value=capabilities,
        ):
            response = asyncio.run(routes.get_database_driver_capabilities_api())

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data, capabilities)

    def test_hydrate_status_preserves_response_shape_without_importing_main_app(self):
        status = {"total": 3, "done": 2, "success": 1, "running": True}
        fake_main = ModuleType("main")
        fake_main.hydrate_status = status

        with patch.dict(sys.modules, {"main": fake_main}):
            response = asyncio.run(routes.get_hydrate_status())

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data, status)


if __name__ == "__main__":
    unittest.main()
