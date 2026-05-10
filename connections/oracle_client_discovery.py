"""Oracle Instant Client discovery helpers."""

from __future__ import annotations

import os
from pathlib import Path

ORACLE_CLIENT_LIB_NAMES = ("oci.dll", "libclntsh.so", "libclntsh.dylib")


def truthy(value) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def oracle_thick_mode_default_enabled() -> bool:
    env_value = os.getenv("OPSCORE_ORACLE_THICK_MODE")
    if env_value is not None and str(env_value).strip():
        return truthy(env_value)
    if truthy(os.getenv("OPSCORE_ORACLE_THIN_MODE")) or truthy(
        os.getenv("OPSCORE_ORACLE_FORCE_THIN")
    ):
        return False
    return True


def oracle_client_mode_flags() -> dict:
    return {
        "thick_mode_env_enabled": truthy(os.getenv("OPSCORE_ORACLE_THICK_MODE")),
        "thick_mode_default_enabled": oracle_thick_mode_default_enabled(),
    }


def valid_oracle_client_dir(path: str | os.PathLike | None) -> Path | None:
    if not path:
        return None
    try:
        candidate = Path(os.path.expandvars(str(path))).expanduser()
        if not candidate.is_dir():
            return None
        if any(
            (candidate / lib_name).exists() for lib_name in ORACLE_CLIENT_LIB_NAMES
        ):
            return candidate.resolve()
    except OSError:
        return None
    return None


def oracle_client_search_roots() -> list[Path]:
    roots: list[Path] = []
    for env_name in ("OPSCORE_ORACLE_CLIENT_ROOT", "ORACLE_HOME"):
        value = os.getenv(env_name)
        if value:
            roots.append(Path(value))

    project_root = Path(__file__).resolve().parent.parent
    roots.extend(
        [
            project_root.parent / "oracle_instantclient",
            project_root / "oracle_instantclient",
            Path("D:/AIOPS/oracle_instantclient"),
            Path("C:/oracle"),
            Path("C:/instantclient"),
        ]
    )
    return roots


def discover_oracle_client_lib_dir(extra_args: dict | None = None) -> dict:
    """Find an Oracle Instant Client directory without persisting machine paths."""
    config = extra_args or {}
    explicit = (
        config.get("oracle_client_lib_dir")
        or config.get("instant_client_dir")
        or os.getenv("OPSCORE_ORACLE_CLIENT_LIB_DIR")
    )
    explicit_path = valid_oracle_client_dir(explicit)
    if explicit_path:
        return {
            "detected": True,
            "lib_dir": str(explicit_path),
            "source": "explicit",
            **oracle_client_mode_flags(),
        }

    for root in oracle_client_search_roots():
        if not root.exists():
            continue
        candidates: list[Path] = []
        if valid_oracle_client_dir(root):
            candidates.append(root)
        try:
            candidates.extend(
                path for path in root.glob("instantclient*") if path.is_dir()
            )
        except OSError:
            continue
        valid = [
            path
            for path in (valid_oracle_client_dir(candidate) for candidate in candidates)
            if path
        ]
        valid = sorted(set(valid), key=lambda item: item.name, reverse=True)
        if valid:
            return {
                "detected": True,
                "lib_dir": str(valid[0]),
                "source": "auto",
                **oracle_client_mode_flags(),
            }

    return {
        "detected": False,
        "lib_dir": "",
        "source": "none",
        **oracle_client_mode_flags(),
    }
