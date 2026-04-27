import unittest

from core.security import is_authorized_request


class TestSecurityAuth(unittest.TestCase):
    def test_auth_disabled_when_token_not_configured(self):
        self.assertTrue(is_authorized_request({}, None))
        self.assertTrue(is_authorized_request({}, ""))

    def test_accepts_x_api_key_header(self):
        self.assertTrue(is_authorized_request({"x-api-key": "secret"}, "secret"))

    def test_accepts_bearer_header(self):
        self.assertTrue(
            is_authorized_request({"authorization": "Bearer secret"}, "secret")
        )

    def test_rejects_missing_or_wrong_token(self):
        self.assertFalse(is_authorized_request({}, "secret"))
        self.assertFalse(is_authorized_request({"x-api-key": "wrong"}, "secret"))


if __name__ == "__main__":
    unittest.main()
