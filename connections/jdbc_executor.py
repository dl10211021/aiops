"""JDBC URL construction and JayDeBeApi execution helpers."""

from __future__ import annotations

import logging
from collections.abc import Callable

from connections.db_execution_result import query_success, statement_success

logger = logging.getLogger(__name__)


def build_jdbc_url(
    drivers: dict[str, dict],
    db_type: str,
    host,
    port,
    database: str,
    extra_args: dict | None,
) -> str:
    config = extra_args or {}
    if config.get("jdbc_url"):
        return str(config["jdbc_url"]).format(
            host=host,
            port=port,
            database=database or "",
        )
    meta = drivers[db_type]
    if database and meta.get("database_url_template"):
        template = meta["database_url_template"]
    else:
        template = meta["url_template"]
    if meta.get("database_required") and not database:
        raise ValueError(f"{meta['label']} JDBC 连接需要填写数据库名。")
    return str(template).format(
        host=host,
        port=int(port or meta["default_port"]),
        database=database or "",
    )


def execute_jdbc(
    db_type,
    host,
    port,
    user,
    password,
    database,
    sql,
    extra_args: dict | None,
    drivers: dict[str, dict],
    normalize_driver_key: Callable[[str | None], str],
    discover_driver: Callable[[str | None, dict | None], dict],
) -> dict:
    db_type = normalize_driver_key(db_type)
    meta = drivers.get(db_type)
    if not meta:
        return {"success": False, "error": f"暂不支持的 JDBC 数据库类型: {db_type}"}

    try:
        import jaydebeapi
    except ImportError:
        return {
            "success": False,
            "error": "缺少 JayDeBeApi/JPype1 依赖，请安装 requirements.txt 后再连接 JDBC 数据库资产。",
        }

    jdbc_driver = discover_driver(db_type, extra_args)
    if not jdbc_driver["jar_paths"]:
        return {
            "success": False,
            "error": (
                f"未找到 {meta['label']} JDBC 驱动 jar。请将驱动放到 "
                f"{meta.get('recommended_path_windows')} 或 {meta.get('recommended_path_linux')}，"
                f"也可以在资产扩展参数 jdbc_jar 中填写路径，或设置 {', '.join(jdbc_driver['env_vars'])}。"
            ),
        }

    try:
        url = build_jdbc_url(drivers, db_type, host, port, database, extra_args)
        driver_class = jdbc_driver["driver_class"]
        conn = jaydebeapi.connect(
            driver_class,
            url,
            [user or "", password or ""],
            jdbc_driver["jar_paths"],
        )
        try:
            cursor = conn.cursor()
            try:
                cursor.execute(sql)
                description = cursor.description or []
                if not description:
                    return statement_success(conn, cursor, sql)
                columns = [col[0] for col in description]
                rows = cursor.fetchmany(1000)
                return query_success(
                    sql,
                    rows,
                    [dict(zip(columns, row)) for row in rows],
                )
            finally:
                try:
                    cursor.close()
                except Exception:
                    pass
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"JDBC 数据库连接执行失败 [{db_type}]: {e}")
        return {"success": False, "error": str(e)}
