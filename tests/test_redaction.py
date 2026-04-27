import json
import unittest

from core.redaction import redact_json_text, redact_text, redact_value


class TestRedaction(unittest.TestCase):
    def test_redacts_known_api_key_prefixes(self):
        text = "API Key: gpustack_1111111111111111_22222222222222222222222222222222"

        redacted = redact_text(text)

        self.assertIn("gpusta...", redacted)
        self.assertNotIn("22222222222222222222222222222222", redacted)

    def test_redacts_json_secret_fields(self):
        payload = {
            "success": True,
            "password": "ExampleP@ssw0rd!",
            "nested": {"api_key": "sk-abcdefghijklmnopqrstuvwxyz"},
        }

        redacted = redact_value(payload)

        self.assertEqual(redacted["password"], "***")
        self.assertEqual(redacted["nested"]["api_key"], "***")

    def test_redacts_db_connection_url(self):
        text = "mysql://root:ExampleP%40ssw0rd!@172.17.10.2:3306/ops"

        self.assertNotIn("ExampleP", redact_text(text))

    def test_redact_json_text_preserves_json_shape(self):
        text = json.dumps({"authorization": "Bearer abcdefghijklmnopqrstuvwxyz"})

        parsed = json.loads(redact_json_text(text))

        self.assertEqual(parsed["authorization"], "***")


if __name__ == "__main__":
    unittest.main()
