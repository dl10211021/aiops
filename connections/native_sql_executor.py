"""Native SQL driver execution helpers."""

from __future__ import annotations

import logging

from connections.db_execution_result import query_success, statement_success

logger = logging.getLogger(__name__)

_MSSQL_ODBC_DRIVER_PRIORITY = (
    "ODBC Driver 17 for SQL Server",
    "ODBC Driver 18 for SQL Server",
    "SQL Server Native Client 11.0",
    "SQL Server",
)


def _select_mssql_odbc_driver(pyodbc_module) -> str:
    try:
        installed = [str(name) for name in pyodbc_module.drivers()]
    except Exception:
        installed = []

    for driver_name in _MSSQL_ODBC_DRIVER_PRIORITY:
        if driver_name in installed:
            return f"{{{driver_name}}}"
    for driver_name in installed:
        if "SQL Server" in driver_name:
            return f"{{{driver_name}}}"
    return "{ODBC Driver 17 for SQL Server}"


def execute_mysql(host, port, user, password, database, sql) -> dict:
    import pymysql

    try:
        # 使用 Cursor 生成字典形式的结果，大模型阅读非常友好
        with pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database or None,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10,
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                if cursor.description is None:
                    return statement_success(conn, cursor, sql)
                # 限制最大拉取 1000 条，防止内存溢出和前端卡死
                result = cursor.fetchmany(1000)
                return query_success(sql, result)
    except Exception as e:
        logger.error(f"MySQL 连接执行失败: {e}")
        return {"success": False, "error": str(e)}


def execute_postgresql(host, port, user, password, database, sql) -> dict:
    import psycopg2
    import psycopg2.extras

    try:
        # 使用 psycopg2 的 RealDictCursor 生成可读友好的字典
        with psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database or user or "postgres",
        ) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(sql)
                if cursor.description is None:
                    return statement_success(conn, cursor, sql)
                # 限制最大拉取 1000 条，防止大模型 token 爆仓
                result = cursor.fetchmany(1000)
                return query_success(sql, result, [dict(row) for row in result])
    except Exception as e:
        logger.error(f"PostgreSQL 连接执行失败: {e}")
        return {"success": False, "error": str(e)}


def execute_mssql(host, port, user, password, database, sql) -> dict:
    try:
        import pyodbc
    except ImportError:
        return {
            "success": False,
            "error": "缺少 pyodbc 依赖，请先安装 requirements.txt 中的 pyodbc，并确认系统已安装 Microsoft ODBC Driver 17 for SQL Server。",
        }

    try:
        driver = _select_mssql_odbc_driver(pyodbc)
        database_part = f"DATABASE={database};" if database else ""
        conn_str = (
            f"DRIVER={driver};SERVER={host},{int(port)};{database_part}"
            f"UID={user};PWD={password or ''};TrustServerCertificate=yes;"
        )
        with pyodbc.connect(conn_str, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            if cursor.description is None:
                return statement_success(conn, cursor, sql)
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchmany(1000)
            return query_success(sql, rows, [dict(zip(columns, row)) for row in rows])
    except Exception as e:
        logger.error(f"SQL Server 连接执行失败: {e}")
        return {"success": False, "error": str(e)}


def execute_dameng(host, port, user, password, database, sql) -> dict:
    try:
        import dmPython
    except ImportError:
        return {
            "success": False,
            "missing_driver": True,
            "error": "缺少 dmpython 依赖，请先安装 requirements.txt 中的 dmpython；达梦原生驱动导入名为 dmPython。",
        }

    conn = None
    cursor = None
    try:
        conn = dmPython.connect(
            user=user,
            password=password or "",
            server=host,
            port=int(port),
        )
        cursor = conn.cursor()
        cursor.execute(sql)
        if cursor.description is None:
            return statement_success(conn, cursor, sql)
        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchmany(1000)
        return query_success(sql, rows, [dict(zip(columns, row)) for row in rows])
    except Exception as e:
        logger.error(f"达梦数据库连接执行失败: {e}")
        return {"success": False, "error": str(e)}
    finally:
        try:
            if cursor is not None:
                cursor.close()
        except Exception:
            pass
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass
