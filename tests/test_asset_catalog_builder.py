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
        for asset_id in ("h3c_switch", "huawei_switch", "cisco_switch", "tplink_switch"):
            with self.subTest(asset_id=asset_id):
                self.assertEqual(catalog[asset_id]["category"], "network")
                self.assertEqual(catalog[asset_id]["protocol"], "ssh")
                self.assertEqual(catalog[asset_id]["default_port"], 22)
                self.assertEqual(catalog[asset_id]["inspection_profile"], "network_cli")
                self.assertEqual(catalog[asset_id]["capability"]["connector"], "ssh_network_cli")
                self.assertIn("enable_pass", fields(asset_id))
                access_protocols = catalog[asset_id]["access_protocols"]
                ssh_access = [item for item in access_protocols if item["protocol"] == "ssh"]
                snmp_access = [item for item in access_protocols if item["protocol"] == "snmp"]
                self.assertTrue(ssh_access and ssh_access[0]["is_default"])
                self.assertTrue(snmp_access and snmp_access[0]["purpose"] == "monitoring")
        for asset_id in ("nas", "synology_nas"):
            with self.subTest(asset_id=asset_id):
                self.assertEqual(catalog[asset_id]["category"], "storage")
                self.assertEqual(catalog[asset_id]["protocol"], "ssh")
                self.assertEqual(catalog[asset_id]["default_port"], 22)
                self.assertEqual(catalog[asset_id]["inspection_profile"], "linux")
                access_protocols = catalog[asset_id]["access_protocols"]
                self.assertTrue([item for item in access_protocols if item["protocol"] == "ssh" and item["is_default"]])
                self.assertTrue([item for item in access_protocols if item["protocol"] == "snmp" and item["purpose"] == "monitoring"])
        self.assertEqual(catalog["idrac"]["category"], "oob")
        self.assertEqual(catalog["idrac"]["protocol"], "redfish")
        self.assertEqual(catalog["idrac"]["default_port"], 443)
        self.assertEqual(catalog["idrac"]["inspection_profile"], "http_api")
        self.assertTrue(
            [
                item
                for item in catalog["idrac"]["access_protocols"]
                if item["protocol"] == "snmp" and item["purpose"] == "monitoring"
            ]
        )

    def test_protocol_alias_assets_are_normalized_but_preserved_in_catalog(self):
        catalog = {item["id"]: item for item in asset_protocols.get_asset_catalog()}

        self.assertEqual(catalog["sqlserver"]["protocol"], "mssql")
        self.assertEqual(catalog["dm"]["protocol"], "dameng")
        self.assertEqual(catalog["kubernetes"]["protocol"], "k8s")


if __name__ == "__main__":
    unittest.main()
