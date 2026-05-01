import unittest

from fastapi.testclient import TestClient

from main import app


class TestRequestContext(unittest.TestCase):
    def test_request_id_header_is_echoed(self):
        client = TestClient(app)

        response = client.get("/healthz", headers={"X-Request-ID": "req-test-123"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Request-ID"], "req-test-123")

    def test_request_id_header_is_generated_when_missing(self):
        client = TestClient(app)

        response = client.get("/healthz")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["X-Request-ID"].startswith("req_"))


if __name__ == "__main__":
    unittest.main()
