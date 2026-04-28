import json
import logging
import os
import threading

logger = logging.getLogger(__name__)

_ORACLE_CLIENT_LOCK = threading.Lock()
_ORACLE_CLIENT_INIT_ATTEMPTED = False


def _truthy(value) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


class DatabaseExecutor:
    """
    统一的数据库直连查询引擎（黑盒模式）。
    对大模型屏蔽环境依赖和转义问题，直接返回 JSON 格式结果。
    """

    @staticmethod
    def _execute_mysql(host, port, user, password, database, sql) -> dict:
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
                        return {"success": True, "affected_rows": cursor.rowcount, "data": []}
                    # 限制最大拉取 1000 条，防止内存溢出和前端卡死
                    result = cursor.fetchmany(1000)
                    return {"success": True, "count": len(result), "data": result}
        except Exception as e:
            logger.error(f"MySQL 连接执行失败: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def _init_oracle_client_if_requested(oracledb, extra_args: dict | None) -> None:
        global _ORACLE_CLIENT_INIT_ATTEMPTED
        config = extra_args or {}
        use_thick = _truthy(config.get("use_thick_mode")) or _truthy(
            os.getenv("OPSCORE_ORACLE_THICK_MODE")
        )
        if not use_thick:
            return

        with _ORACLE_CLIENT_LOCK:
            if _ORACLE_CLIENT_INIT_ATTEMPTED:
                return
            lib_dir = (
                config.get("oracle_client_lib_dir")
                or config.get("instant_client_dir")
                or os.getenv("OPSCORE_ORACLE_CLIENT_LIB_DIR")
                or None
            )
            kwargs = {"lib_dir": str(lib_dir)} if lib_dir else {}
            oracledb.init_oracle_client(**kwargs)
            _ORACLE_CLIENT_INIT_ATTEMPTED = True

    @staticmethod
    def _oracle_dsn(oracledb, host, port, sid_or_service_name, extra_args: dict | None) -> str:
        config = extra_args or {}
        sid = config.get("SID") or config.get("sid")
        service_name = config.get("service_name")
        connect_type = str(
            config.get("oracle_connect_type") or config.get("connect_type") or ""
        ).strip().lower()
        if sid and not service_name:
            return oracledb.makedsn(host, int(port), sid=str(sid))
        if service_name:
            return oracledb.makedsn(host, int(port), service_name=str(service_name))
        if sid_or_service_name:
            if connect_type in {"service", "service_name"}:
                return oracledb.makedsn(host, int(port), service_name=str(sid_or_service_name))
            return oracledb.makedsn(host, int(port), sid=str(sid_or_service_name))
        return f"{host}:{port}/{sid_or_service_name}"

    @staticmethod
    def _oracle_error_message(error: Exception) -> str:
        raw = str(error)
        if "DPY-3015" in raw:
            return (
                f"{raw}\n"
                "OpsCore 当前 Oracle 连接使用 python-oracledb thin mode；目标账号使用了旧版 "
                "10G password verifier，thin mode 不支持。处理方式：让 DBA 重置该用户密码生成 "
                "11G/12C verifier，或安装 Oracle Instant Client 并设置 "
                "OPSCORE_ORACLE_THICK_MODE=true 和 OPSCORE_ORACLE_CLIENT_LIB_DIR。"
            )
        return raw

    @staticmethod
    def _execute_oracle(host, port, user, password, sid_or_service_name, sql, extra_args: dict | None = None) -> dict:
        import oracledb

        try:
            DatabaseExecutor._init_oracle_client_if_requested(oracledb, extra_args)
            dsn = DatabaseExecutor._oracle_dsn(oracledb, host, port, sid_or_service_name, extra_args)
            # 创建连接
            with oracledb.connect(user=user, password=password, dsn=dsn) as conn:
                with conn.cursor() as cursor:
                    # 设定输出以字典形式返回，防止大模型看到全是 List 和 Tuple 的数组崩溃
                    cursor.execute(sql)

                    # 限制最大拉取 1000 条，防止大模型 token 爆仓
                    rows = cursor.fetchmany(1000) or []

                    # 处理列名映射
                    columns = [col[0] for col in (cursor.description or [])]
                    result_dicts = [dict(zip(columns, row)) for row in rows]

                    return {
                        "success": True,
                        "count": len(result_dicts),
                        "data": result_dicts,
                    }
        except Exception as e:
            logger.error(f"Oracle 连接执行失败: {e}")
            return {"success": False, "error": DatabaseExecutor._oracle_error_message(e)}

    @staticmethod
    def _execute_postgresql(host, port, user, password, database, sql) -> dict:
        import psycopg2
        import psycopg2.extras

        try:
            # 使用 psycopg2 的 RealDictCursor 生成可读友好的字典
            with psycopg2.connect(
                host=host, port=port, user=user, password=password, database=database or user or "postgres"
            ) as conn:
                with conn.cursor(
                    cursor_factory=psycopg2.extras.RealDictCursor
                ) as cursor:
                    cursor.execute(sql)
                    if cursor.description is None:
                        return {"success": True, "affected_rows": cursor.rowcount, "data": []}
                    # 限制最大拉取 1000 条，防止大模型 token 爆仓
                    result = cursor.fetchmany(1000)
                    return {
                        "success": True,
                        "count": len(result),
                        "data": [dict(r) for r in result],
                    }
        except Exception as e:
            logger.error(f"PostgreSQL 连接执行失败: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def _execute_mssql(host, port, user, password, database, sql) -> dict:
        try:
            import pyodbc
        except ImportError:
            return {
                "success": False,
                "error": "缺少 pyodbc 依赖，请先安装 requirements.txt 中的 pyodbc，并确认系统已安装 SQL Server ODBC Driver。",
            }

        try:
            driver = "{ODBC Driver 18 for SQL Server}"
            database_part = f"DATABASE={database};" if database else ""
            conn_str = (
                f"DRIVER={driver};SERVER={host},{int(port)};{database_part}"
                f"UID={user};PWD={password or ''};TrustServerCertificate=yes;"
            )
            with pyodbc.connect(conn_str, timeout=10) as conn:
                cursor = conn.cursor()
                cursor.execute(sql)
                if cursor.description is None:
                    return {"success": True, "affected_rows": cursor.rowcount, "data": []}
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchmany(1000)
                return {
                    "success": True,
                    "count": len(rows),
                    "data": [dict(zip(columns, row)) for row in rows],
                }
        except Exception as e:
            logger.error(f"SQL Server 连接执行失败: {e}")
            return {"success": False, "error": str(e)}

    def execute_query(
        self,
        db_type: str,
        host: str,
        port: int,
        user: str,
        password: str | None,
        database: str,
        sql: str,
        extra_args: dict | None = None,
    ) -> str:
        """根据数据库类型路由到对应的原生驱动"""
        db_type = db_type.lower()
        if db_type == "mysql":
            res = self._execute_mysql(host, port, user, password, database, sql)
        elif db_type == "oracle":
            res = self._execute_oracle(
                host, port, user, password, database, sql, extra_args
            )  # database 此处意为 SID 或 service_name
        elif db_type in ["pg", "postgresql"]:
            res = self._execute_postgresql(host, port, user, password, database, sql)
        elif db_type in ["mssql", "sqlserver", "sql_server"]:
            res = self._execute_mssql(host, port, user, password, database, sql)
        else:
            res = {
                "success": False,
                "error": f"暂不支持的原生数据库类型: {db_type}。目前支持 mysql, oracle, postgresql, mssql。",
            }

        return json.dumps(
            res, ensure_ascii=False, default=str
        )  # default=str 解决 datetime 等无法 JSON 序列化的问题


db_executor = DatabaseExecutor()
