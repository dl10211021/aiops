import hmac
from collections.abc import Mapping


def is_authorized_request(headers: Mapping[str, str], configured_token: str | None) -> bool:
    """Validate optional API token auth.

    If no token is configured the app remains usable for local development.
    """
    if not configured_token:
        return True

    normalized = {str(k).lower(): str(v) for k, v in headers.items()}
    supplied = normalized.get("x-api-key", "")
    auth_header = normalized.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        supplied = auth_header.split(" ", 1)[1].strip()

    return bool(supplied) and hmac.compare_digest(supplied, configured_token)
