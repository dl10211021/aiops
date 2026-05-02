from __future__ import annotations

import os


def load_dotenv_if_available(app_file: str) -> bool:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return False

    env_path = os.path.join(os.path.dirname(app_file), ".env")
    if not os.path.exists(env_path):
        return False

    load_dotenv(env_path, override=True)
    return True
