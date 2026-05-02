from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FrontendEntry:
    html: str | None = None
    fallback: dict[str, Any] | None = None


def get_legacy_static_dir(base_path: str) -> str | None:
    static_dir = os.path.join(base_path, "static")
    return static_dir if os.path.exists(static_dir) else None


def get_react_assets_dir(base_path: str) -> str | None:
    react_assets = os.path.join(base_path, "static_react", "assets")
    return react_assets if os.path.exists(react_assets) else None


def resolve_frontend_entry(base_path: str) -> FrontendEntry:
    react_index = os.path.join(base_path, "static_react", "index.html")
    if os.path.exists(react_index):
        with open(react_index, "r", encoding="utf-8") as file:
            return FrontendEntry(html=file.read())

    html_path = os.path.join(base_path, "frontend_demo.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as file:
            return FrontendEntry(html=file.read())

    return FrontendEntry(fallback={"status": "ok", "message": "Backend is running."})
