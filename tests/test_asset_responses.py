import unittest

from core.asset_responses import mask_asset_response, mask_asset_responses
from core.memory import DEFAULT_SENSITIVE_EXTRA_ARG_KEYS


class TestAssetResponses(unittest.TestCase):
    def test_mask_asset_response_masks_password_and_sensitive_extra_args(self):
        asset = {
            "host": "prom.local",
            "password": "real-password",
            "extra_args": {
                "api_key": "real-key",
                "api_token": "real-token",
                "category": "monitor",
            },
        }

        masked = mask_asset_response(asset, DEFAULT_SENSITIVE_EXTRA_ARG_KEYS)

        self.assertEqual(masked["password"], "********")
        self.assertEqual(masked["extra_args"]["api_key"], "********")
        self.assertEqual(masked["extra_args"]["api_token"], "********")
        self.assertEqual(masked["extra_args"]["category"], "monitor")
        self.assertEqual(asset["password"], "real-password")
        self.assertEqual(asset["extra_args"]["api_key"], "real-key")

    def test_mask_asset_responses_handles_list(self):
        masked = mask_asset_responses(
            [
                {"host": "a.local", "password": "secret", "extra_args": {}},
                {"host": "b.local", "password": "", "extra_args": {"category": "db"}},
            ],
            DEFAULT_SENSITIVE_EXTRA_ARG_KEYS,
        )

        self.assertEqual(masked[0]["password"], "********")
        self.assertEqual(masked[1]["password"], "")
        self.assertEqual(masked[1]["extra_args"]["category"], "db")
