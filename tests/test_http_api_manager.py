from unittest.mock import patch

from connections.http_api_manager import build_base_url, http_api_executor


def test_build_base_url_supports_configured_base_path():
    assert (
        build_base_url("api.local", 8443, {"scheme": "https", "base_path": "/v1"})
        == "https://api.local:8443/v1"
    )


def test_build_base_url_preserves_url_path_by_default():
    assert build_base_url("https://api.local/root/", 443, {}) == "https://api.local/root"


def test_build_base_url_allows_base_path_to_override_url_path():
    assert (
        build_base_url("https://api.local/root/", 443, {"base_path": "/ops"})
        == "https://api.local/ops"
    )


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, _size):
        return b'{"ok":true}'

    def getcode(self):
        return 200


def _captured_headers(**kwargs):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["headers"] = dict(request.header_items())
        captured["timeout"] = timeout
        return _FakeResponse()

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = http_api_executor.request(**kwargs)

    assert result["success"] is True
    return captured["headers"]


def test_kibana_basic_auth_adds_kbn_xsrf_header():
    headers = _captured_headers(
        asset_type="elastic_stack",
        host="logs.local",
        port=5601,
        username="elastic",
        password="secret",
        extra_args={"scheme": "http"},
        method="GET",
        path="/api/status",
    )

    assert headers["Authorization"].startswith("Basic ")
    assert headers["Kbn-xsrf"] == "true"


def test_authorization_header_detection_is_case_insensitive():
    headers = _captured_headers(
        asset_type="graylog",
        host="graylog.local",
        port=9000,
        username="ignored",
        password="ignored",
        extra_args={"scheme": "http"},
        method="GET",
        path="/api/system",
        headers={"authorization": "Bearer caller-token"},
    )

    assert headers["Authorization"] == "Bearer caller-token"


def test_token_header_field_is_honored_for_api_assets():
    headers = _captured_headers(
        asset_type="hertzbeat",
        host="monitor.local",
        port=1157,
        username="",
        password=None,
        extra_args={
            "scheme": "http",
            "api_token": "managed-token",
            "token_header": "X-Auth-Token",
        },
        method="GET",
        path="/api/monitor",
    )

    assert headers["X-auth-token"] == "managed-token"


def test_api_key_defaults_to_x_api_key_header():
    headers = _captured_headers(
        asset_type="manageengine",
        host="manage.local",
        port=8060,
        username="",
        password=None,
        extra_args={"scheme": "http", "api_key": "managed-key"},
        method="GET",
        path="/api/status",
    )

    assert headers["X-api-key"] == "managed-key"


def test_auth_type_controls_authorization_token_prefix():
    headers = _captured_headers(
        asset_type="opensearch",
        host="search.local",
        port=9200,
        username="",
        password=None,
        extra_args={"scheme": "http", "api_token": "encoded-user-pass", "auth_type": "basic"},
        method="GET",
        path="/_cluster/health",
    )

    assert headers["Authorization"] == "Basic encoded-user-pass"


def test_custom_headers_are_injected_without_overwriting_call_headers():
    headers = _captured_headers(
        asset_type="elastic_stack",
        host="logs.local",
        port=5601,
        username="",
        password=None,
        extra_args={
            "scheme": "http",
            "custom_headers": "Authorization: Bearer managed\nkbn-xsrf: true\nX-Trace: asset",
        },
        method="GET",
        path="/api/status",
        headers={"X-Trace": "caller"},
    )

    assert headers["Authorization"] == "Bearer managed"
    assert headers["Kbn-xsrf"] == "true"
    assert headers["X-trace"] == "caller"


def test_graylog_adds_requested_by_header_for_api_assets():
    headers = _captured_headers(
        asset_type="graylog",
        host="graylog.local",
        port=9000,
        username="admin",
        password="secret",
        extra_args={"scheme": "http"},
        method="GET",
        path="/api/system",
    )

    assert headers["X-requested-by"] == "OpsCore"
