import unittest

from fastapi import HTTPException

from api.errors import raise_http_error


class FakeServiceError(Exception):
    status_code = 418
    detail = {"error": "teapot"}


class TestApiErrors(unittest.TestCase):
    def test_raise_http_error_preserves_status_detail_and_cause(self):
        exc = FakeServiceError("service failed")

        with self.assertRaises(HTTPException) as ctx:
            raise_http_error(exc)

        self.assertEqual(ctx.exception.status_code, 418)
        self.assertEqual(ctx.exception.detail, {"error": "teapot"})
        self.assertIs(ctx.exception.__cause__, exc)


if __name__ == "__main__":
    unittest.main()
