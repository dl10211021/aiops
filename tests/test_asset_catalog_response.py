import unittest

from core.asset_catalog_response import build_asset_type_form_catalog_response, build_asset_types_response


class TestAssetCatalogResponse(unittest.TestCase):
    def test_build_asset_types_response_groups_categories_and_connectors(self):
        response = build_asset_types_response(
            [
                {
                    "id": "mysql",
                    "category": "db",
                    "capability": {"connector": "database"},
                },
                {
                    "id": "oracle",
                    "category": "db",
                    "capability": {"connector": "database"},
                },
                {
                    "id": "s3",
                    "category": "storage",
                    "capability": {"connector": "object_storage"},
                },
            ]
        )

        category_ids = [item["id"] for item in response["categories"]]
        connector_ids = [item["id"] for item in response["connector_groups"]]

        self.assertEqual(response["types"][0]["id"], "mysql")
        self.assertEqual(category_ids.count("db"), 1)
        self.assertIn("storage", category_ids)
        self.assertEqual(connector_ids.count("database"), 1)
        self.assertIn("object_storage", connector_ids)

    def test_build_asset_type_form_catalog_omits_duplicate_capability_payload(self):
        response = build_asset_type_form_catalog_response(
            [
                {
                    "id": "oracle",
                    "label": "Oracle",
                    "category": "db",
                    "protocol": "oracle",
                    "default_port": 1521,
                    "params": [{"field": "oracle_connect_type"}],
                    "access_protocols": [{"protocol": "oracle", "label": "Oracle"}],
                    "category_meta": {"label": "数据库"},
                    "capability": {
                        "family": "database",
                        "connector": "native_sql",
                        "operation_model": "managed_session",
                        "tools": ["db_execute_query"],
                        "credential_fields": ["host", "port", "username", "password"],
                        "driver_key": "oracle",
                        "maturity": "native",
                        "connector_group": {"id": "native_sql", "label": "原生 SQL"},
                        "parameter_template": [{"field": "oracle_connect_type"}],
                        "tool_details": [{"name": "db_execute_query"}],
                        "setup": {"env_vars": {"OPSCORE_ORACLE_CLIENT_LIB_DIR": "..."}},
                        "risk_model": {"safety_category": "sql"},
                    },
                }
            ]
        )

        item = response["types"][0]
        self.assertEqual(item["params"], [{"field": "oracle_connect_type"}])
        self.assertEqual(item["access_protocols"][0]["protocol"], "oracle")
        self.assertEqual(item["capability"]["connector"], "native_sql")
        self.assertEqual(item["capability"]["tools"], ["db_execute_query"])
        self.assertNotIn("category_meta", item)
        self.assertNotIn("parameter_template", item["capability"])
        self.assertNotIn("tool_details", item["capability"])
        self.assertNotIn("setup", item["capability"])
