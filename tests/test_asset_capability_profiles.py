import unittest

from core import asset_capabilities
from core.asset_capability_profiles import (
    DATABASE_ALIASES,
    PROTOCOL_CAPABILITY_PROFILES,
    SERVICE_PROTOCOL_CREDENTIAL_FIELDS,
    SPECIAL_CAPABILITY_OVERRIDES,
)


class AssetCapabilityProfileTests(unittest.TestCase):
    def test_database_aliases_and_special_overrides_cover_core_datastores(self):
        self.assertEqual(DATABASE_ALIASES["tidb"], "mysql")
        self.assertEqual(DATABASE_ALIASES["opengauss"], "postgresql")
        self.assertEqual(SPECIAL_CAPABILITY_OVERRIDES["oracle"]["tools"], ["db_execute_query"])
        self.assertEqual(SPECIAL_CAPABILITY_OVERRIDES["redis"]["connector"], "native_kv")

    def test_protocol_profiles_keep_native_and_service_probe_contracts(self):
        self.assertEqual(PROTOCOL_CAPABILITY_PROFILES["ssh"]["connector"], "ssh_shell")
        self.assertEqual(PROTOCOL_CAPABILITY_PROFILES["winrm"]["tools"], ["winrm_execute_command"])
        self.assertEqual(PROTOCOL_CAPABILITY_PROFILES["mongodb"]["tools"], ["mongodb_find"])
        self.assertEqual(SERVICE_PROTOCOL_CREDENTIAL_FIELDS["ldap"], ["host", "port", "username", "password", "base_dn"])

    def test_asset_capabilities_keeps_backward_compatible_profile_exports(self):
        self.assertIs(asset_capabilities.DATABASE_ALIASES, DATABASE_ALIASES)
        self.assertIs(asset_capabilities.SPECIAL_CAPABILITY_OVERRIDES, SPECIAL_CAPABILITY_OVERRIDES)
        self.assertIs(asset_capabilities.PROTOCOL_CAPABILITY_PROFILES, PROTOCOL_CAPABILITY_PROFILES)


if __name__ == "__main__":
    unittest.main()
