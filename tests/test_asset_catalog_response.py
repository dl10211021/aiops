import unittest

from core.asset_catalog_response import build_asset_types_response


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
