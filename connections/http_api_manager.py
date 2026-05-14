"""HTTP/API execution adapter for API-style assets."""

from __future__ import annotations

import base64
import json
import logging
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)


def _has_header(headers: dict, name: str) -> bool:
    expected = name.lower()
    return any(str(key).lower() == expected for key in headers)


def _set_header_if_missing(headers: dict, name: str, value: str) -> None:
    if not _has_header(headers, name):
        headers[name] = value


def _clean_auth_type(value: object) -> str:
    auth_type = str(value or "auto").strip().lower().replace("-", "_")
    return auth_type if auth_type in {"auto", "bearer", "basic", "api_key", "raw"} else "auto"


def _prefix_token_value(token_value: str, auth_type: str, header_name: str) -> str:
    if auth_type == "raw":
        return token_value
    if auth_type == "basic":
        return token_value if token_value.lower().startswith("basic ") else f"Basic {token_value}"
    if auth_type == "bearer":
        return token_value if token_value.lower().startswith("bearer ") else f"Bearer {token_value}"
    if auth_type == "api_key":
        return token_value
    if header_name.lower() == "authorization" and not token_value.lower().startswith(
        ("bearer ", "basic ", "token ", "apikey ", "api-key ")
    ):
        return f"Bearer {token_value}"
    return token_value


def _managed_token_header(extra_args: dict) -> tuple[str | None, str | None]:
    token = (
        extra_args.get("api_token")
        or extra_args.get("bearer_token")
        or extra_args.get("api_key")
    )
    if not token:
        return None, None

    token_value = str(token).strip()
    auth_type = _clean_auth_type(extra_args.get("auth_type") or extra_args.get("token_type"))
    header_name = str(
        extra_args.get("auth_header")
        or extra_args.get("token_header")
        or ("X-API-Key" if extra_args.get("api_key") or auth_type == "api_key" else "Authorization")
    ).strip()
    if not header_name:
        header_name = "X-API-Key" if auth_type == "api_key" else "Authorization"
    token_value = _prefix_token_value(token_value, auth_type, header_name)
    return header_name, token_value


def _managed_custom_headers(extra_args: dict) -> dict[str, str]:
    raw = extra_args.get("custom_headers") or extra_args.get("headers")
    if not raw:
        return {}
    if isinstance(raw, dict):
        return {str(key).strip(): str(value) for key, value in raw.items() if str(key).strip()}
    text = str(raw).strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        return {str(key).strip(): str(value) for key, value in parsed.items() if str(key).strip()}

    headers: dict[str, str] = {}
    for line in text.splitlines():
        item = line.strip()
        if not item or item.startswith("#") or ":" not in item:
            continue
        key, value = item.split(":", 1)
        key = key.strip()
        if key:
            headers[key] = value.strip()
    return headers


def _apply_managed_auth_headers(
    *,
    headers: dict,
    asset_type: str,
    username: str,
    password: str | None,
    extra_args: dict,
) -> None:
    for header_name, header_value in _managed_custom_headers(extra_args).items():
        _set_header_if_missing(headers, header_name, header_value)

    token_header, token_value = _managed_token_header(extra_args)
    if token_header and token_value:
        _set_header_if_missing(headers, token_header, token_value)

    if username and password and not _has_header(headers, "Authorization"):
        basic = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {basic}"

    if str(asset_type or "").lower() in {"elastic_stack", "kibana"}:
        _set_header_if_missing(headers, "kbn-xsrf", "true")
    if str(asset_type or "").lower() == "graylog":
        _set_header_if_missing(headers, "X-Requested-By", "OpsCore")


def build_base_url(host: str, port: int | None, extra_args: dict | None = None) -> str:
    extra_args = extra_args or {}
    raw_host = str(host or "").strip()
    configured_base_path = str(
        extra_args.get("base_path") or extra_args.get("api_base_path") or ""
    ).strip()
    if raw_host.startswith(("http://", "https://")):
        parsed = urllib.parse.urlparse(raw_host)
        scheme = parsed.scheme
        netloc = parsed.netloc
        base_path = (configured_base_path or parsed.path).strip().rstrip("/")
        if base_path and not base_path.startswith("/"):
            base_path = f"/{base_path}"
        return urllib.parse.urlunparse((scheme, netloc, base_path, "", "", "")).rstrip("/")

    effective_port = int(port or 443)
    scheme = str(extra_args.get("scheme") or ("https" if effective_port == 443 else "http"))
    parsed = urllib.parse.urlparse(f"//{raw_host}")
    hostname = parsed.hostname or raw_host
    host_port = parsed.port or effective_port
    base_path = configured_base_path.rstrip("/")
    if base_path and not base_path.startswith("/"):
        base_path = f"/{base_path}"
    return f"{scheme}://{hostname}:{host_port}{base_path}"


class HttpApiExecutor:
    def request(
        self,
        *,
        asset_type: str,
        host: str,
        port: int,
        username: str = "",
        password: str | None = None,
        extra_args: dict | None = None,
        method: str = "GET",
        path: str = "/",
        headers: dict | None = None,
        body: object | None = None,
        timeout: int = 15,
    ) -> dict:
        extra_args = extra_args or {}
        headers = dict(headers or {})
        method = str(method or "GET").upper()
        if not path:
            path = "/"
        if not str(path).startswith("/"):
            path = f"/{path}"

        base_url = build_base_url(host, port, extra_args)
        url = urllib.parse.urljoin(f"{base_url}/", str(path).lstrip("/"))

        _apply_managed_auth_headers(
            headers=headers,
            asset_type=asset_type,
            username=username,
            password=password,
            extra_args=extra_args,
        )

        data = None
        if body not in (None, ""):
            if isinstance(body, (dict, list)):
                data = json.dumps(body).encode("utf-8")
                headers.setdefault("Content-Type", "application/json")
            elif isinstance(body, str):
                data = body.encode("utf-8")
            else:
                data = json.dumps(body).encode("utf-8")
                headers.setdefault("Content-Type", "application/json")

        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read(2 * 1024 * 1024)
                text = raw.decode("utf-8", errors="replace")
                return {
                    "success": 200 <= resp.getcode() < 400,
                    "status_code": resp.getcode(),
                    "asset_type": asset_type,
                    "url": url,
                    "output": text,
                }
        except urllib.error.HTTPError as e:
            text = e.read(2 * 1024 * 1024).decode("utf-8", errors="replace")
            return {
                "success": False,
                "status_code": e.code,
                "asset_type": asset_type,
                "url": url,
                "error": text or str(e),
            }
        except Exception as e:
            logger.error("HTTP/API request failed: %s", e)
            return {"success": False, "asset_type": asset_type, "url": url, "error": str(e)}


http_api_executor = HttpApiExecutor()
