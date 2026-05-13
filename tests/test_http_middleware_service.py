import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.responses import Response

from core.http_middleware_service import (
    SECURITY_HEADERS,
    dispatch_api_token_auth,
    dispatch_request_id,
    dispatch_security_headers,
    requires_api_token_auth,
    resolve_request_id,
)
from core.request_context import current_request_id


class TestHttpMiddlewareService(unittest.TestCase):
    def test_resolve_request_id_uses_header_or_generates_id(self):
        self.assertEqual(resolve_request_id({"X-Request-ID": "req-client"}), "req-client")

        fake_uuid = SimpleNamespace(hex="abc123")
        with patch("core.http_middleware_service.uuid.uuid4", return_value=fake_uuid):
            self.assertEqual(resolve_request_id({}), "req_abc123")

    def test_dispatch_request_id_sets_context_state_and_response_header(self):
        request = SimpleNamespace(headers={"X-Request-ID": "req-test"}, state=SimpleNamespace())
        seen_context = {}

        async def call_next(_request):
            seen_context["request_id"] = current_request_id()
            return Response()

        response = asyncio.run(dispatch_request_id(request, call_next))

        self.assertEqual(seen_context["request_id"], "req-test")
        self.assertEqual(request.state.request_id, "req-test")
        self.assertEqual(response.headers["X-Request-ID"], "req-test")
        self.assertIsNone(current_request_id())

    def test_requires_api_token_auth_only_for_api_non_options_requests(self):
        self.assertTrue(requires_api_token_auth("/api/v1/assets", "GET"))
        self.assertFalse(requires_api_token_auth("/api/v1/assets", "OPTIONS"))
        self.assertFalse(requires_api_token_auth("/healthz", "GET"))

    def test_dispatch_api_token_auth_blocks_invalid_token(self):
        request = SimpleNamespace(
            headers={},
            method="GET",
            url=SimpleNamespace(path="/api/v1/assets"),
        )
        call_next = Mock()

        response = asyncio.run(dispatch_api_token_auth(request, call_next, "secret"))

        self.assertEqual(response.status_code, 401)
        call_next.assert_not_called()

    def test_dispatch_api_token_auth_allows_valid_token(self):
        request = SimpleNamespace(
            headers={"Authorization": "Bearer secret"},
            method="GET",
            url=SimpleNamespace(path="/api/v1/assets"),
        )

        async def call_next(_request):
            return Response(status_code=204)

        response = asyncio.run(dispatch_api_token_auth(request, call_next, "secret"))

        self.assertEqual(response.status_code, 204)

    def test_dispatch_security_headers_preserves_existing_headers(self):
        async def call_next(_request):
            response = Response()
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
            return response

        response = asyncio.run(dispatch_security_headers(SimpleNamespace(), call_next))

        self.assertEqual(response.headers["X-Frame-Options"], "SAMEORIGIN")
        for header, value in SECURITY_HEADERS.items():
            self.assertIn(header, response.headers)
            if header != "X-Frame-Options":
                self.assertEqual(response.headers[header], value)

    def test_dispatch_security_headers_sets_frontend_cache_policy(self):
        async def call_next(_request):
            return Response()

        async def missing_asset(_request):
            return Response(status_code=404)

        asset_response = asyncio.run(dispatch_security_headers(
            SimpleNamespace(url=SimpleNamespace(path="/assets/index-abcd.js")),
            call_next,
        ))
        missing_asset_response = asyncio.run(dispatch_security_headers(
            SimpleNamespace(url=SimpleNamespace(path="/assets/missing.js")),
            missing_asset,
        ))
        index_response = asyncio.run(dispatch_security_headers(
            SimpleNamespace(url=SimpleNamespace(path="/")),
            call_next,
        ))

        self.assertEqual(
            asset_response.headers["Cache-Control"],
            "public, max-age=31536000, immutable",
        )
        self.assertEqual(missing_asset_response.headers["Cache-Control"], "no-store")
        self.assertEqual(index_response.headers["Cache-Control"], "no-cache")


if __name__ == "__main__":
    unittest.main()
