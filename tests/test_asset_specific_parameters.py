import unittest
from copy import deepcopy

from core.asset_capability_profiles import PROTOCOL_CAPABILITY_PROFILES
from core.asset_specific_parameters import apply_asset_parameter_template


class AssetSpecificParameterTests(unittest.TestCase):
    def test_applies_shared_template_for_shell_connector(self):
        capability = {"connector": "ssh_shell"}

        apply_asset_parameter_template(capability, "linux")

        fields = {param["field"] for param in capability["parameter_template"]}
        self.assertIn("shell", fields)
        self.assertIn("sudo_method", fields)

    def test_applies_database_specific_template(self):
        capability = {"connector": "native_sql"}

        apply_asset_parameter_template(capability, "oracle")

        fields = {param["field"] for param in capability["parameter_template"]}
        self.assertIn("oracle_connect_type", fields)
        self.assertIn("use_thick_mode", fields)

    def test_applies_http_api_https_default_for_sensitive_platforms(self):
        capability = deepcopy(PROTOCOL_CAPABILITY_PROFILES["http_api"])

        apply_asset_parameter_template(capability, "redfish")

        scheme = next(param for param in capability["parameter_template"] if param["field"] == "scheme")
        self.assertEqual(scheme["defaultValue"], "https")


if __name__ == "__main__":
    unittest.main()
