import json
import logging

logger = logging.getLogger(__name__)


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
                database=database,
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=10,
            ) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql)
                    # 限制最大拉取 1000 条，防止内存溢出和前端卡死
                    result = cursor.fetchmany(1000)
                    return {"success": True, "count": len(result), "data": result}
        except Exception as e:
            logger.error(f"MySQL 连接执行失败: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def _execute_oracle(host, port, user, password, sid_or_service_name, sql) -> dict:
        import oracledb

        try:
            # 开启 python-oracledb 的 Thin 模式，不需要安装任何额外的 Oracle Client 驱动，也不需要 JDBC 繁琐配置。非常牛。
            dsn = f"{host}:{port}/{sid_or_service_name}"
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
            return {"success": False, "error": str(e)}

    @staticmethod
    def _execute_postgresql(host, port, user, password, database, sql) -> dict:
        import psycopg2
        import psycopg2.extras

        try:
            # 使用 psycopg2 的 RealDictCursor 生成可读友好的字典
            with psycopg2.connect(
                host=host, port=port, user=user, password=password, database=database
            ) as conn:
                with conn.cursor(
                    cursor_factory=psycopg2.extras.RealDictCursor
                ) as cursor:
                    cursor.execute(sql)
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

    def execute_query(
        self,
        db_type: str,
        host: str,
        port: int,
        user: str,
        password: str | None,
        database: str,
        sql: str,
    ) -> str:
        """根据数据库类型路由到对应的原生驱动"""
        db_type = db_type.lower()
        if db_type == "mysql":
            res = self._execute_mysql(host, port, user, password, database, sql)
        elif db_type == "oracle":
            res = self._execute_oracle(
                host, port, user, password, database, sql
            )  # database 此处意为 SID
        elif db_type in ["pg", "postgresql"]:
            res = self._execute_postgresql(host, port, user, password, database, sql)
        else:
            res = {
                "success": False,
                "error": f"暂不支持的原生数据库类型: {db_type}。目前支持 mysql, oracle, postgresql。",
            }

        return json.dumps(
            res, ensure_ascii=False, default=str
        )  # default=str 解决 datetime 等无法 JSON 序列化的问题


db_executor = DatabaseExecutor()
