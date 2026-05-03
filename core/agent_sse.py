from __future__ import annotations

import json


def sse_event(payload: dict, *, ensure_ascii: bool = True) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=ensure_ascii)}\n\n"


def sse_raw(serialized_payload: str) -> str:
    return f"data: {serialized_payload}\n\n"
