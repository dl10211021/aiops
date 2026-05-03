import unittest

from core import asset_protocols
from core.asset_catalog_builder import (
    ASSET_CATALOG,
    ASSET_PROTOCOL_OVERRIDES,
    BASE_ASSET_CATALOG,
    _apply_protocol_overrides,
    _merge_asset_catalog,
)


class AssetCatalogBuilderTests(unittest.TestCase):
    def test_merge_asset_catalog_preserves_base_and_marks_hertzbeat_support(self):
        merged = _merge_asset_catalog(
            [{"id": "oracle", "protocol": "oracle"}],
            [{"id": "oracle", "source": "hertzbeat", "params": [{"field": "timeout"}]}],
        )

        self.assertEqual(merged, [{"id": "oracle", "protocol": "oracle", "params": [{"field": "timeout"}], "hertzbeat_supported": True}])

    def test_merge_asset_catalog_excludes_hertzbeat_examples(self):
        merged = _merge_asset_catalog([{"id": "linux"}], [{"id": "a_example", "source": "hertzbeat"}])

        self.assertEqual(merged, [{"id": "linux"}])

    def test_apply_protocol_overrides_preserves_existing_port_and_profile_rules(self):
        result = _apply_protocol_overrides(
            [
                {"id": "windows_script", "protocol": "ssh", "default_port": 22},
                {"id": "dns", "protocol": "http_api", "default_port": 80},
                {"id": "mariadb", "protocol": "jdbc", "default_port": 3306},
            ]
        )
        by_id = {item["id"]: item for item in result}

        self.assertEqual(by_id["windows_script"]["protocol"], "winrm")
        self.assertEqual(by_id["windows_script"]["default_port"], 5985)
        self.assertEqual(by_id["windows_script"]["inspection_profile"], "winrm")
        self.assertEqual(by_id["dns"]["protocol"], "dns")
        self.assertEqual(by_id["dns"]["default_port"], 53)
        self.assertEqual(by_id["mariadb"]["protocol"], "mysql")
        self.assertEqual(by_id["mariadb"]["inspection_profile"], "sql")

    def test_asset_protocols_keeps_backward_compatible_catalog_exports(self):
        self.assertIs(asset_protocols.ASSET_CATALOG, ASSET_CATALOG)
        self.assertIs(asset_protocols.BASE_ASSET_CATALOG, BASE_ASSET_CATALOG)
        self.assertIs(asset_protocols.ASSET_PROTOCOL_OVERRIDES, ASSET_PROTOCOL_OVERRIDES)


if __name__ == "__main__":
    unittest.main()
