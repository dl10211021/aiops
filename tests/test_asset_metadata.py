import unittest

from core import asset_capabilities
from core.asset_metadata import (
    ASSET_CATEGORY_DEFINITIONS,
    CONNECTOR_GROUP_DEFINITIONS,
    category_metadata,
    connector_metadata,
)


class AssetMetadataTests(unittest.TestCase):
    def test_category_metadata_returns_copy_with_id_and_fallback(self):
        db_metadata = category_metadata("db")
        self.assertEqual(db_metadata["id"], "db")
        self.assertEqual(db_metadata["label"], ASSET_CATEGORY_DEFINITIONS["db"]["label"])
        self.assertEqual(category_metadata("log")["label"], "日志平台")

        db_metadata["label"] = "mutated"
        self.assertEqual(category_metadata("db")["label"], ASSET_CATEGORY_DEFINITIONS["db"]["label"])
        self.assertEqual(category_metadata("missing")["id"], "missing")
        self.assertEqual(category_metadata("missing")["label"], ASSET_CATEGORY_DEFINITIONS["other"]["label"])

    def test_connector_metadata_returns_copy_with_id_and_fallback(self):
        sql_metadata = connector_metadata("native_sql")
        self.assertEqual(sql_metadata["id"], "native_sql")
        self.assertEqual(sql_metadata["tools"], CONNECTOR_GROUP_DEFINITIONS["native_sql"]["tools"])
        self.assertEqual(connector_metadata("log_api")["tools"], ["monitoring_api_query"])

        sql_metadata["tools"].append("mutated")
        self.assertEqual(connector_metadata("native_sql")["tools"], CONNECTOR_GROUP_DEFINITIONS["native_sql"]["tools"])
        self.assertEqual(connector_metadata("missing")["id"], "missing")
        self.assertEqual(connector_metadata("missing")["label"], CONNECTOR_GROUP_DEFINITIONS["unknown"]["label"])

    def test_asset_capabilities_keeps_backward_compatible_exports(self):
        self.assertIs(asset_capabilities.category_metadata, category_metadata)
        self.assertIs(asset_capabilities.connector_metadata, connector_metadata)
        self.assertIs(asset_capabilities.ASSET_CATEGORY_DEFINITIONS, ASSET_CATEGORY_DEFINITIONS)
        self.assertIs(asset_capabilities.CONNECTOR_GROUP_DEFINITIONS, CONNECTOR_GROUP_DEFINITIONS)


if __name__ == "__main__":
    unittest.main()
