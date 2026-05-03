import unittest

from core import asset_capabilities
from core.asset_parameter_templates import (
    GENERIC_HTTP_API_PARAMETERS,
    SHARED_PARAMETER_TEMPLATES,
    _boolean_parameter,
    _number_parameter,
    _password_parameter,
    _select_parameter,
    _text_parameter,
)


class AssetParameterTemplateTests(unittest.TestCase):
    def test_parameter_builders_preserve_frontend_contract(self):
        self.assertEqual(
            _text_parameter("base_path", "API 基础路径", group="http", default="/api"),
            {
                "field": "base_path",
                "label": "API 基础路径",
                "type": "text",
                "required": False,
                "group": "http",
                "defaultValue": "/api",
            },
        )
        self.assertEqual(_password_parameter("token", "Token", group="http")["type"], "password")
        self.assertEqual(_number_parameter("port", "端口", group="net", default=80)["defaultValue"], 80)
        self.assertEqual(_boolean_parameter("tls", "TLS", group="net", default=True)["defaultValue"], True)
        self.assertEqual(
            _select_parameter(
                "scheme",
                "协议",
                group="http",
                default="https",
                options=[("HTTP", "http"), ("HTTPS", "https")],
            )["options"],
            [{"label": "HTTP", "value": "http"}, {"label": "HTTPS", "value": "https"}],
        )

    def test_shared_templates_keep_core_connector_parameters(self):
        ssh_fields = {param["field"] for param in SHARED_PARAMETER_TEMPLATES["ssh_shell"]}
        object_storage_fields = {param["field"] for param in SHARED_PARAMETER_TEMPLATES["object_storage_api"]}

        self.assertIn("shell", ssh_fields)
        self.assertIn("sudo_method", ssh_fields)
        self.assertIn("endpoint_url", object_storage_fields)
        self.assertIn("access_key", object_storage_fields)
        self.assertEqual(GENERIC_HTTP_API_PARAMETERS[0]["field"], "scheme")

    def test_asset_capabilities_keeps_backward_compatible_parameter_exports(self):
        self.assertIs(asset_capabilities.GENERIC_HTTP_API_PARAMETERS, GENERIC_HTTP_API_PARAMETERS)
        self.assertIs(asset_capabilities.SHARED_PARAMETER_TEMPLATES, SHARED_PARAMETER_TEMPLATES)
        self.assertIs(asset_capabilities._text_parameter, _text_parameter)


if __name__ == "__main__":
    unittest.main()
