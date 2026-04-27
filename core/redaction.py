"""Secret redaction for tool output, logs, and chat-visible traces.

Adapted for OpsCore from the MIT-licensed Hermes Agent redaction design.
The redactor is intentionally display-layer focused: managed credentials remain
available to protocol adapters, but secret-like values are masked before output
is shown to users or written into model-visible memory.
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


SENSITIVE_KEYS = {
    "access_token",
    "refresh_token",
    "id_token",
    "token",
    "api_key",
    "apikey",
    "client_secret",
    "password",
    "passwd",
    "auth",
    "jwt",
    "secret",
    "private_key",
    "authorization",
    "bearer_token",
    "community_string",
    "v3_auth_pass",
    "v3_priv_pass",
    "enable_pass",
    "enable_password",
}

PREFIX_PATTERNS = [
    r"sk-[A-Za-z0-9_-]{10,}",
    r"sk_[A-Za-z0-9_]{10,}",
    r"gpustack_[A-Za-z0-9_]{10,}",
    r"ghp_[A-Za-z0-9]{10,}",
    r"github_pat_[A-Za-z0-9_]{10,}",
    r"AIza[A-Za-z0-9_-]{30,}",
    r"AKIA[A-Z0-9]{16}",
    r"hf_[A-Za-z0-9]{10,}",
    r"xox[baprs]-[A-Za-z0-9-]{10,}",
    r"eyJ[A-Za-z0-9_-]{10,}(?:\.[A-Za-z0-9_=-]{4,}){0,2}",
]

PREFIX_RE = re.compile(
    r"(?<![A-Za-z0-9_-])(" + "|".join(PREFIX_PATTERNS) + r")(?![A-Za-z0-9_-])"
)
ENV_ASSIGN_RE = re.compile(
    r"([A-Z0-9_]*(?:API_?KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|AUTH)[A-Z0-9_]*)\s*=\s*(['\"]?)(\S+)\2",
    re.IGNORECASE,
)
JSON_FIELD_RE = re.compile(
    r'("(?:api_?key|token|secret|password|access_token|refresh_token|authorization|bearer_token|private_key)")\s*:\s*"([^"]*)"',
    re.IGNORECASE,
)
AUTH_HEADER_RE = re.compile(r"(Authorization:\s*(?:Bearer|Basic)\s+)(\S+)", re.IGNORECASE)
DB_CONNSTR_RE = re.compile(
    r"((?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp|oracle|mssql)://[^:\s]+:)([^@\s]+)(@)",
    re.IGNORECASE,
)
URL_WITH_QUERY_RE = re.compile(r"(https?|wss?)://[^\s?#]+\?[^\s#]+")
PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN[A-Z ]*PRIVATE KEY-----[\s\S]*?-----END[A-Z ]*PRIVATE KEY-----"  # allow-secret
)


def mask_token(token: str) -> str:
    if len(token) < 18:
        return "***"
    return f"{token[:6]}...{token[-4:]}"


def _redact_url(match: re.Match[str]) -> str:
    url = match.group(0)
    try:
        parts = urlsplit(url)
        query = []
        for key, value in parse_qsl(parts.query, keep_blank_values=True):
            query.append((key, "***" if key.lower() in SENSITIVE_KEYS else value))
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    except Exception:
        return url


def redact_text(value: str) -> str:
    """Mask common secret patterns in free-form text."""
    if not value:
        return value

    text = PRIVATE_KEY_RE.sub("-----BEGIN PRIVATE KEY-----***-----END PRIVATE KEY-----", value)  # allow-secret
    text = URL_WITH_QUERY_RE.sub(_redact_url, text)
    text = DB_CONNSTR_RE.sub(r"\1***\3", text)
    text = AUTH_HEADER_RE.sub(r"\1***", text)
    text = JSON_FIELD_RE.sub(lambda m: f'{m.group(1)}: "{mask_token(m.group(2))}"', text)
    text = ENV_ASSIGN_RE.sub(lambda m: f"{m.group(1)}=***", text)
    text = PREFIX_RE.sub(lambda m: mask_token(m.group(1)), text)
    return text


def redact_value(value: Any) -> Any:
    """Recursively redact strings in JSON-like values."""
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if str(key).lower() in SENSITIVE_KEYS:
                redacted[key] = "***"
            else:
                redacted[key] = redact_value(item)
        return redacted
    return value


def redact_json_text(value: str) -> str:
    """Redact a JSON string if possible, otherwise redact as plain text."""
    try:
        parsed = json.loads(value)
    except Exception:
        return redact_text(value)
    return json.dumps(redact_value(parsed), ensure_ascii=False, default=str)
