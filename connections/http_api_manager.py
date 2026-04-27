"""HTTP/API execution adapter for API-style assets."""

from __future__ import annotations

import base64
import json
import logging
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)


def build_base_url(host: str, port: int | None, extra_args: dict | None = None) -> str:
    extra_args = extra_args or {}
    raw_host = str(host or "").strip()
    if raw_host.startswith(("http://", "https://")):
        parsed = urllib.parse.urlparse(raw_host)
        scheme = parsed.scheme
        netloc = parsed.netloc
        base_path = parsed.path.rstrip("/")
        return urllib.parse.urlunparse((scheme, netloc, base_path, "", "", "")).rstrip("/")

    effective_port = int(port or 443)
    scheme = str(extra_args.get("scheme") or ("https" if effective_port == 443 else "http"))
    parsed = urllib.parse.urlparse(f"//{raw_host}")
    hostname = parsed.hostname or raw_host
    host_port = parsed.port or effective_port
    return f"{scheme}://{hostname}:{host_port}"


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

        token = extra_args.get("api_token") or extra_args.get("bearer_token")
        auth_header = str(extra_args.get("auth_header") or "Authorization")
        if token and auth_header not in headers:
            headers[auth_header] = f"Bearer {token}"

        if username and password and not token and "Authorization" not in headers:
            basic = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
            headers["Authorization"] = f"Basic {basic}"

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
