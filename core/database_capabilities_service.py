from __future__ import annotations

from typing import Any

from connections import db_manager


def get_oracle_client_config_record() -> dict[str, Any]:
    return db_manager.discover_oracle_client_lib_dir()


def get_database_driver_capabilities_record() -> dict[str, Any]:
    return db_manager.get_database_driver_capabilities()
