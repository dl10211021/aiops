from connections.http_api_manager import build_base_url


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
