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

    def test_high_frequency_asset_protocol_and_parameter_matrix(self):
        catalog = {item["id"]: item for item in asset_protocols.get_asset_catalog()}

        def fields(asset_id):
            return {param["field"] for param in catalog[asset_id].get("params", [])}

        self.assertEqual(len(catalog), len(asset_protocols.get_asset_catalog()))
        self.assertEqual(catalog["linux"]["protocol"], "ssh")
        self.assertEqual(catalog["linux"]["default_port"], 22)
        self.assertEqual(catalog["windows"]["protocol"], "winrm")
        self.assertEqual(catalog["windows"]["default_port"], 5985)
        self.assertIn("transport", fields("windows"))

        self.assertEqual(catalog["mysql"]["protocol"], "mysql")
        self.assertEqual(catalog["mysql"]["default_port"], 3306)
        self.assertFalse(fields("mysql") & {"sid", "service_name", "tns_alias", "oracle_connect_type"})

        self.assertEqual(catalog["oracle"]["protocol"], "oracle")
        self.assertEqual(catalog["oracle"]["default_port"], 1521)
        self.assertTrue({"sid", "service_name", "tns_alias", "oracle_connect_type"}.issubset(fields("oracle")))

        self.assertEqual(catalog["redis"]["capability"]["connector"], "native_kv")
        self.assertIn("db_index", fields("redis"))
        self.assertEqual(catalog["mongodb"]["capability"]["connector"], "native_document")
        self.assertIn("auth_source", fields("mongodb"))

        self.assertEqual(catalog["switch"]["protocol"], "ssh")
        self.assertEqual(catalog["switch"]["capability"]["connector"], "ssh_network_cli")
        self.assertIn("enable_pass", fields("switch"))
        self.assertEqual(catalog["tplink_switch"]["protocol"], "snmp")
        self.assertEqual(catalog["tplink_switch"]["default_port"], 161)

    def test_protocol_alias_assets_are_normalized_but_preserved_in_catalog(self):
        catalog = {item["id"]: item for item in asset_protocols.get_asset_catalog()}

        self.assertEqual(catalog["sqlserver"]["protocol"], "mssql")
        self.assertEqual(catalog["dm"]["protocol"], "dameng")
        self.assertEqual(catalog["kubernetes"]["protocol"], "k8s")


if __name__ == "__main__":
    unittest.main()
