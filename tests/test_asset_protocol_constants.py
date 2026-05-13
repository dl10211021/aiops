import unittest

from core import asset_protocols
from core.asset_protocol_constants import (
    API_PROTOCOLS,
    ASSET_PROTOCOL_MAP,
    ASSET_TYPE_ALIASES,
    CONTAINER_API_ASSET_TYPES,
    DATABASE_HTTP_ASSET_TYPES,
    DB_PROTOCOLS,
    DOMAIN_HTTP_API_ASSET_TYPES,
    KEYWORD_ASSET_HINTS,
    LOG_PLATFORM_ASSET_TYPES,
    MIDDLEWARE_ASSET_TYPES,
    NETWORK_API_ASSET_TYPES,
    NETWORK_CLI_ASSET_TYPES,
    NETWORK_SSH_ASSET_TYPES,
    MIDDLEWARE_API_ASSET_TYPES,
    PORT_ASSET_HINTS,
    SQL_PROTOCOLS,
    STORAGE_SSH_ASSET_TYPES,
    STORAGE_ASSET_TYPES,
)


class AssetProtocolConstantsTests(unittest.TestCase):
    def test_protocol_maps_keep_primary_asset_aliases(self):
        self.assertEqual(ASSET_PROTOCOL_MAP["mysql"], "mysql")
        self.assertEqual(ASSET_PROTOCOL_MAP["kubernetes"], "k8s")
        self.assertEqual(ASSET_PROTOCOL_MAP["nas"], "ssh")
        self.assertEqual(ASSET_PROTOCOL_MAP["kafka"], "ssh")
        self.assertEqual(ASSET_PROTOCOL_MAP["promethues"], "http_api")
        self.assertEqual(ASSET_PROTOCOL_MAP["elastic_stack"], "http_api")
        self.assertEqual(ASSET_PROTOCOL_MAP["graylog"], "http_api")
        self.assertEqual(ASSET_TYPE_ALIASES["postgres"], "postgresql")
        self.assertEqual(ASSET_TYPE_ALIASES["manage_engine"], "manageengine")
        self.assertEqual(ASSET_TYPE_ALIASES["elk"], "elastic_stack")
        self.assertEqual(ASSET_TYPE_ALIASES["graylog2"], "graylog")

    def test_protocol_groups_cover_native_and_probe_connectors(self):
        self.assertLessEqual({"mysql", "oracle", "postgresql"}, SQL_PROTOCOLS)
        self.assertLessEqual({"mysql", "redis", "clickhouse"}, DB_PROTOCOLS)
        self.assertLessEqual({"http_api", "k8s", "vmware", "s3", "dns"}, API_PROTOCOLS)

    def test_derived_asset_sets_are_built_from_catalog_categories(self):
        self.assertIn("clickhouse", DATABASE_HTTP_ASSET_TYPES)
        self.assertIn("rabbitmq", MIDDLEWARE_API_ASSET_TYPES)
        self.assertIn("harbor", CONTAINER_API_ASSET_TYPES)
        self.assertIn("rabbitmq", DOMAIN_HTTP_API_ASSET_TYPES)
        self.assertLessEqual({"elastic_stack", "graylog", "loki"}, LOG_PLATFORM_ASSET_TYPES)

    def test_domain_shell_asset_sets_cover_catalog_specific_types(self):
        self.assertLessEqual(
            {"cisco_switch", "h3c_switch", "hpe_switch", "huawei_switch", "tplink_switch"},
            NETWORK_CLI_ASSET_TYPES,
        )
        self.assertIn("firewall", NETWORK_API_ASSET_TYPES)
        self.assertIn("firewall", NETWORK_SSH_ASSET_TYPES)
        self.assertIn("process", MIDDLEWARE_ASSET_TYPES)
        self.assertIn("synology_nas", STORAGE_ASSET_TYPES)
        self.assertLessEqual({"nas", "synology_nas"}, STORAGE_SSH_ASSET_TYPES)

    def test_inference_hints_keep_legacy_detection_contracts(self):
        self.assertEqual(PORT_ASSET_HINTS[3306], "mysql")
        self.assertEqual(PORT_ASSET_HINTS[6443], "k8s")
        self.assertEqual(PORT_ASSET_HINTS[5601], "kibana")
        self.assertEqual(PORT_ASSET_HINTS[9600], "logstash")
        self.assertIn(("kubernetes", "k8s"), KEYWORD_ASSET_HINTS)
        self.assertIn(("卓豪", "manageengine"), KEYWORD_ASSET_HINTS)
        self.assertIn(("elk", "elastic_stack"), KEYWORD_ASSET_HINTS)
        self.assertIn(("graylog", "graylog"), KEYWORD_ASSET_HINTS)

    def test_asset_protocols_keeps_backward_compatible_constant_exports(self):
        self.assertIs(asset_protocols.ASSET_PROTOCOL_MAP, ASSET_PROTOCOL_MAP)
        self.assertIs(asset_protocols.DB_PROTOCOLS, DB_PROTOCOLS)
        self.assertIs(asset_protocols.KEYWORD_ASSET_HINTS, KEYWORD_ASSET_HINTS)


if __name__ == "__main__":
    unittest.main()
