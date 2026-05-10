import asyncio
import unittest
import warnings
from unittest.mock import patch

warnings.filterwarnings(
    "ignore",
    message=r"Please use `import python_multipart` instead\.",
    category=PendingDeprecationWarning,
)

from api import routes, system_info_routes


class TestSystemInfoRoutes(unittest.TestCase):
    def test_system_info_routes_are_included_in_api_router(self):
        paths = {route.path for route in routes.router.routes}

        self.assertIn("/oracle/client-config", paths)
        self.assertIn("/database/driver-capabilities", paths)
        self.assertIn("/hydrate/status", paths)

    def test_oracle_client_config_preserves_response_shape(self):
        config = {
            "detected": True,
            "lib_dir": "D:/oracle/instantclient",
            "source": "auto",
        }

        with patch(
            "api.system_info_routes.get_oracle_client_config_record",
            return_value=config,
        ):
            response = asyncio.run(system_info_routes.get_oracle_client_config())

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data, config)

    def test_database_driver_capabilities_preserves_response_shape(self):
        capabilities = {"drivers": {"oracle": {"id": "oracle", "ready": True}}}

        with patch(
            "api.system_info_routes.get_database_driver_capabilities_record",
            return_value=capabilities,
        ):
            response = asyncio.run(system_info_routes.get_database_driver_capabilities_api())

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data, capabilities)

    def test_refresh_query_clears_database_capabilities_cache_before_read(self):
        capabilities = {"drivers": {"oracle": {"id": "oracle", "ready": True}}}

        with (
            patch("api.system_info_routes.clear_database_capabilities_cache") as clear_cache,
            patch(
                "api.system_info_routes.get_database_driver_capabilities_record",
                return_value=capabilities,
            ) as get_capabilities,
        ):
            response = asyncio.run(
                system_info_routes.get_database_driver_capabilities_api(refresh=True)
            )

        clear_cache.assert_called_once()
        get_capabilities.assert_called_once()
        self.assertEqual(response.status, "success")
        self.assertEqual(response.data, capabilities)

    def test_hydrate_status_preserves_response_shape_without_importing_main_app(self):
        status = {"total": 3, "done": 2, "success": 1, "running": True}

        with patch("api.system_info_routes.get_hydrate_status_record", return_value=status):
            response = asyncio.run(system_info_routes.get_hydrate_status())

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data, status)


if __name__ == "__main__":
    unittest.main()
