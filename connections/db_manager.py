import json
import logging
import os
from pathlib import Path
import importlib.util
import threading
from typing import Any

from connections.db_execution_result import (
    commit_if_needed,
    query_success,
    should_commit_after_statement,
    statement_success,
    statement_type,
)
from connections.oracle_client_discovery import (
    discover_oracle_client_lib_dir,
    oracle_thick_mode_default_enabled,
    truthy as _truthy,
)
from connections.native_sql_executor import (
    execute_dameng,
    execute_mssql,
    execute_mysql,
    execute_postgresql,
)
from connections.jdbc_executor import build_jdbc_url, execute_jdbc

logger = logging.getLogger(__name__)

_ORACLE_CLIENT_LOCK = threading.Lock()
_ORACLE_CLIENT_INIT_ATTEMPTED = False


def _oracle_thick_mode_enabled(extra_args: dict | None) -> bool:
    config = extra_args or {}
    if "use_thick_mode" in config:
        return _truthy(config.get("use_thick_mode"))
    return oracle_thick_mode_default_enabled()

DATABASE_DRIVER_ALIASES = {
    "tidb": "mysql",
    "oceanbase": "mysql",
    "mariadb": "mysql",
    "pg": "postgresql",
    "kingbase": "postgresql",
    "opengauss": "postgresql",
    "greenplum": "postgresql",
    "vastbase": "postgresql",
    "sqlserver": "mssql",
    "sql_server": "mssql",
    "doris_fe": "mysql",
    "starrocks_fe": "mysql",
    "greptime": "mysql",
    "dm": "dameng",
    "apache_hive": "hive",
    "apache_iotdb": "iotdb",
}

MSSQL_ODBC_DRIVER_PRIORITY = (
    "ODBC Driver 17 for SQL Server",
    "ODBC Driver 18 for SQL Server",
    "SQL Server Native Client 11.0",
    "SQL Server",
)

JDBC_DATABASE_DRIVERS: dict[str, dict[str, Any]] = {
    "dameng": {
        "label": "达梦数据库 DM",
        "default_port": 5236,
        "driver_class": "dm.jdbc.driver.DmDriver",
        "jar_names": ("DmJdbcDriver18.jar", "DmJdbcDriver.jar", "dmjdbc.jar"),
        "env_vars": ("OPSCORE_DAMENG_JDBC_JAR", "OPSCORE_DM_JDBC_JAR"),
        "url_template": "jdbc:dm://{host}:{port}",
        "database_url_template": "jdbc:dm://{host}:{port}/{database}",
        "recommended_path_windows": r"D:\AIOPS\jdbc_drivers\dameng\DmJdbcDriver18.jar",
        "recommended_path_linux": "/opt/opscore/jdbc/dameng/DmJdbcDriver18.jar",
        "test_statement": "SELECT 1",
    },
    "db2": {
        "label": "IBM DB2",
        "default_port": 50000,
        "driver_class": "com.ibm.db2.jcc.DB2Driver",
        "jar_names": ("db2jcc4.jar", "db2jcc.jar"),
        "env_vars": ("OPSCORE_DB2_JDBC_JAR",),
        "url_template": "jdbc:db2://{host}:{port}/{database}",
        "database_required": True,
        "recommended_path_windows": r"D:\AIOPS\jdbc_drivers\db2\db2jcc4.jar",
        "recommended_path_linux": "/opt/opscore/jdbc/db2/db2jcc4.jar",
        "test_statement": "SELECT 1 FROM SYSIBM.SYSDUMMY1",
    },
    "xugu": {
        "label": "虚谷数据库",
        "default_port": 5138,
        "driver_class": "com.xugu.cloudjdbc.Driver",
        "jar_names": ("xugu-jdbc.jar", "xugucloudjdbc.jar", "xugu.jar"),
        "env_vars": ("OPSCORE_XUGU_JDBC_JAR",),
        "url_template": "jdbc:xugu://{host}:{port}",
        "database_url_template": "jdbc:xugu://{host}:{port}/{database}",
        "recommended_path_windows": r"D:\AIOPS\jdbc_drivers\xugu\xugu-jdbc.jar",
        "recommended_path_linux": "/opt/opscore/jdbc/xugu/xugu-jdbc.jar",
        "test_statement": "SELECT 1",
    },
    "hive": {
        "label": "Apache Hive",
        "default_port": 10000,
        "driver_class": "org.apache.hive.jdbc.HiveDriver",
        "jar_names": ("hive-jdbc.jar", "hive-jdbc-standalone.jar", "hive-jdbc-uber.jar"),
        "env_vars": ("OPSCORE_HIVE_JDBC_JAR",),
        "url_template": "jdbc:hive2://{host}:{port}",
        "database_url_template": "jdbc:hive2://{host}:{port}/{database}",
        "recommended_path_windows": r"D:\AIOPS\jdbc_drivers\hive\hive-jdbc-standalone.jar",
        "recommended_path_linux": "/opt/opscore/jdbc/hive/hive-jdbc-standalone.jar",
        "test_statement": "SHOW DATABASES",
    },
    "iotdb": {
        "label": "Apache IoTDB",
        "default_port": 6667,
        "driver_class": "org.apache.iotdb.jdbc.IoTDBDriver",
        "jar_names": ("iotdb-jdbc.jar", "iotdb-jdbc-uber.jar"),
        "env_vars": ("OPSCORE_IOTDB_JDBC_JAR",),
        "url_template": "jdbc:iotdb://{host}:{port}",
        "database_url_template": "jdbc:iotdb://{host}:{port}/{database}",
        "recommended_path_windows": r"D:\AIOPS\jdbc_drivers\iotdb\iotdb-jdbc.jar",
        "recommended_path_linux": "/opt/opscore/jdbc/iotdb/iotdb-jdbc.jar",
        "test_statement": "SHOW VERSION",
    },
}

DATABASE_OPERATION_PROFILES: dict[str, dict] = {
    "oracle": {
        "id": "oracle",
        "label": "Oracle",
        "identity_label": "SID / Service Name / TNS Alias",
        "default_port": 1521,
        "test_statement": "SELECT 1 FROM DUAL",
        "readonly_examples": [
            "SELECT * FROM v$version",
            "SELECT name, open_mode FROM v$database",
            "SELECT username, account_status FROM dba_users FETCH FIRST 20 ROWS ONLY",
        ],
        "write_requires_approval": True,
        "hard_block_examples": ["DROP DATABASE", "DROP USER", "DROP TABLESPACE"],
        "operator_note": (
            "Oracle 资产默认使用 python-oracledb Thick Mode，AI 只需要提供 SQL。SID/Service Name/"
            "TNS Alias、账号和密码由资产中心注入；请在后端启动前准备 Oracle Instant Client。"
        ),
    },
    "mysql": {
        "id": "mysql",
        "label": "MySQL / TiDB / OceanBase(MySQL)",
        "identity_label": "Database Name",
        "default_port": 3306,
        "test_statement": "SELECT 1",
        "readonly_examples": [
            "SELECT VERSION() AS version",
            "SHOW GLOBAL STATUS LIKE 'Threads_connected'",
            "SHOW PROCESSLIST",
        ],
        "write_requires_approval": True,
        "hard_block_examples": ["DROP DATABASE", "DROP SCHEMA"],
        "operator_note": (
            "MySQL 兼容资产使用 PyMySQL 原生连接，TiDB/OceanBase MySQL 模式归并到同一数据库能力。"
        ),
    },
    "postgresql": {
        "id": "postgresql",
        "label": "PostgreSQL / Kingbase",
        "identity_label": "Database Name",
        "default_port": 5432,
        "test_statement": "SELECT 1",
        "readonly_examples": [
            "SELECT version()",
            "SELECT datname, numbackends FROM pg_stat_database ORDER BY numbackends DESC",
        ],
        "write_requires_approval": True,
        "hard_block_examples": ["DROP DATABASE", "DROP SCHEMA"],
        "operator_note": "PostgreSQL 兼容资产使用 psycopg2 原生连接。",
    },
    "mssql": {
        "id": "mssql",
        "label": "SQL Server",
        "identity_label": "Database Name",
        "default_port": 1433,
        "test_statement": "SELECT 1",
        "readonly_examples": [
            "SELECT @@VERSION AS version",
            "SELECT name, state_desc FROM sys.databases",
        ],
        "write_requires_approval": True,
        "hard_block_examples": ["DROP DATABASE"],
        "operator_note": "SQL Server 资产使用 pyodbc + Microsoft ODBC Driver 17 原生连接；如环境已安装 Driver 18，OpsCore 会兼容使用。",
    },
    "redis": {
        "id": "redis",
        "label": "Redis",
        "identity_label": "Database Index",
        "default_port": 6379,
        "test_statement": "PING",
        "readonly_examples": ["INFO", "DBSIZE", "CLIENT LIST"],
        "write_requires_approval": True,
        "hard_block_examples": ["FLUSHALL", "FLUSHDB"],
        "operator_note": "Redis 使用 redis-py 原生客户端；只读巡检优先 INFO/DBSIZE/TTL/TYPE/SCAN。",
    },
    "mongodb": {
        "id": "mongodb",
        "label": "MongoDB",
        "identity_label": "Database Name",
        "default_port": 27017,
        "test_statement": "find admin.system.version",
        "readonly_examples": ["find system.version", "dbStats", "serverStatus"],
        "write_requires_approval": True,
        "hard_block_examples": ["dropDatabase", "drop"],
        "operator_note": "MongoDB 使用 PyMongo；当前工具优先提供只读 find 查询。",
    },
    "dameng": {
        "id": "dameng",
        "label": "达梦数据库 DM",
        "identity_label": "Schema / Database",
        "default_port": 5236,
        "test_statement": "SELECT 1",
        "readonly_examples": ["SELECT * FROM v$version", "SELECT username FROM dba_users"],
        "write_requires_approval": True,
        "hard_block_examples": ["DROP TABLE", "DROP USER"],
        "operator_note": "达梦优先使用 dmPython 原生驱动接入；如离线环境暂无法安装 dmpython，可继续用 JayDeBeApi + 达梦 JDBC 驱动兜底。",
    },
    "db2": {
        "id": "db2",
        "label": "IBM DB2",
        "identity_label": "Database Name",
        "default_port": 50000,
        "test_statement": "SELECT 1 FROM SYSIBM.SYSDUMMY1",
        "readonly_examples": ["SELECT CURRENT SERVER FROM SYSIBM.SYSDUMMY1", "SELECT TABSCHEMA, TABNAME FROM SYSCAT.TABLES FETCH FIRST 20 ROWS ONLY"],
        "write_requires_approval": True,
        "hard_block_examples": ["DROP DATABASE", "DROP TABLE"],
        "operator_note": "DB2 通过 JayDeBeApi + IBM db2jcc4.jar 接入；通常必须填写数据库名。",
    },
    "xugu": {
        "id": "xugu",
        "label": "虚谷数据库",
        "identity_label": "Database Name",
        "default_port": 5138,
        "test_statement": "SELECT 1",
        "readonly_examples": ["SELECT 1", "SELECT * FROM SYS_TABLES"],
        "write_requires_approval": True,
        "hard_block_examples": ["DROP DATABASE", "DROP TABLE"],
        "operator_note": "虚谷通过 JayDeBeApi + 虚谷 JDBC 驱动接入；驱动类和 JDBC URL 可在资产参数里覆盖。",
    },
    "hive": {
        "id": "hive",
        "label": "Apache Hive",
        "identity_label": "Database Name",
        "default_port": 10000,
        "test_statement": "SHOW DATABASES",
        "readonly_examples": ["SHOW DATABASES", "SHOW TABLES", "SELECT * FROM default.sample_07 LIMIT 10"],
        "write_requires_approval": True,
        "hard_block_examples": ["DROP DATABASE", "DROP TABLE"],
        "operator_note": "Hive 通过 HiveServer2 JDBC 接入；请配置 Hive JDBC standalone/uber jar，Kerberos/SSL 可通过 JDBC URL 覆盖。",
    },
    "iotdb": {
        "id": "iotdb",
        "label": "Apache IoTDB",
        "identity_label": "Database / Path",
        "default_port": 6667,
        "test_statement": "SHOW VERSION",
        "readonly_examples": ["SHOW VERSION", "SHOW DATABASES", "SHOW TIMESERIES LIMIT 20"],
        "write_requires_approval": True,
        "hard_block_examples": ["DELETE DATABASE", "DROP TIMESERIES"],
        "operator_note": "IoTDB 通过官方 JDBC 驱动接入，默认 JDBC 端口 6667；复杂集群参数可在 JDBC URL 中覆盖。",
    },
}


def normalize_database_driver_key(db_type: str | None) -> str:
    raw = str(db_type or "").strip().lower()
    return DATABASE_DRIVER_ALIASES.get(raw, raw)


def get_database_operation_profile(db_type: str | None) -> dict:
    key = normalize_database_driver_key(db_type)
    return dict(DATABASE_OPERATION_PROFILES.get(key, {}))


def _module_installed(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _dm_python_installed() -> bool:
    return _module_installed("dmPython") or _module_installed("dmpython")


def _split_paths(value: Any) -> list[Path]:
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        raw_items = value
    else:
        raw_items = str(value).replace(";", os.pathsep).split(os.pathsep)
    paths: list[Path] = []
    for item in raw_items:
        text = str(item or "").strip()
        if not text:
            continue
        paths.append(Path(os.path.expandvars(text)).expanduser())
    return paths


def _jdbc_search_roots() -> list[Path]:
    project_root = Path(__file__).resolve().parent.parent
    roots = [
        Path(os.path.expandvars(value)).expanduser()
        for value in (
            os.getenv("OPSCORE_JDBC_DRIVER_DIR"),
            os.getenv("JDBC_DRIVER_DIR"),
        )
        if value
    ]
    roots.extend(
        [
            project_root.parent / "jdbc_drivers",
            project_root / "jdbc_drivers",
            Path("D:/AIOPS/jdbc_drivers"),
            Path("/opt/opscore/jdbc"),
        ]
    )
    return roots


def discover_jdbc_driver(db_type: str | None, extra_args: dict | None = None) -> dict:
    key = normalize_database_driver_key(db_type)
    meta = JDBC_DATABASE_DRIVERS.get(key)
    if not meta:
        return {"detected": False, "jar_paths": [], "source": "unsupported", "driver_class": ""}

    config = extra_args or {}
    candidates: list[Path] = []
    candidates.extend(_split_paths(config.get("jdbc_jar") or config.get("jdbc_jar_path") or config.get("jdbc_jars")))
    for env_name in meta.get("env_vars", ()):
        candidates.extend(_split_paths(os.getenv(env_name)))

    for root in _jdbc_search_roots():
        if not root.exists():
            continue
        if root.is_file() and root.suffix.lower() == ".jar":
            candidates.append(root)
            continue
        search_dirs = [root, root / key]
        for folder in search_dirs:
            if not folder.is_dir():
                continue
            for jar_name in meta.get("jar_names", ()):
                candidates.append(folder / jar_name)
            try:
                candidates.extend(folder.glob("*.jar"))
            except OSError:
                pass

    seen: set[str] = set()
    valid: list[str] = []
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if not resolved.is_file() or resolved.suffix.lower() != ".jar":
            continue
        text = str(resolved)
        if text not in seen:
            seen.add(text)
            valid.append(text)

    return {
        "detected": bool(valid),
        "jar_paths": valid,
        "source": "configured" if valid else "none",
        "driver_class": str(config.get("jdbc_driver_class") or meta.get("driver_class") or ""),
        "recommended_path_windows": meta.get("recommended_path_windows", ""),
        "recommended_path_linux": meta.get("recommended_path_linux", ""),
        "env_vars": list(meta.get("env_vars", ())) + ["OPSCORE_JDBC_DRIVER_DIR"],
    }


def _mssql_odbc_drivers() -> list[str]:
    try:
        import pyodbc

        return list(pyodbc.drivers())
    except Exception:
        return []


def _preferred_mssql_odbc_driver(drivers: list[str]) -> str:
    for driver_name in MSSQL_ODBC_DRIVER_PRIORITY:
        if driver_name in drivers:
            return driver_name
    for driver_name in drivers:
        if "SQL Server" in driver_name:
            return driver_name
    return ""


def get_database_driver_capabilities() -> dict:
    """Return database connector readiness and installation hints for the UI."""
    oracle_client = discover_oracle_client_lib_dir()
    oracle_package_installed = _module_installed("oracledb")
    mssql_drivers = _mssql_odbc_drivers()
    preferred_mssql_driver = _preferred_mssql_odbc_driver(mssql_drivers)
    dameng_jdbc_driver = discover_jdbc_driver("dameng")
    dameng_native_ready = _dm_python_installed()
    dameng_jdbc_ready = _module_installed("jaydebeapi") and dameng_jdbc_driver["detected"]
    capabilities = {
        "oracle": {
            "id": "oracle",
            "label": "Oracle",
            "connector": "native_sql",
            "python_package": "oracledb",
            "python_import": "oracledb",
            "default_mode": "thick",
            "python_package_installed": oracle_package_installed,
            "external_client_required": True,
            "external_client_detected": oracle_client["detected"],
            "external_client_name": "Oracle Instant Client",
            "status": (
                "ready"
                if oracle_package_installed and oracle_client["detected"]
                else "missing_python_package"
                if not oracle_package_installed
                else "missing_external_client"
            ),
            "recommended_path_windows": r"D:\AIOPS\oracle_instantclient\instantclient_23_0",
            "recommended_path_linux": "/opt/opscore/oracle/instantclient",
            "env_vars": {
                "OPSCORE_ORACLE_THICK_MODE": "true",
                "OPSCORE_ORACLE_CLIENT_LIB_DIR": "${ORACLE_INSTANT_CLIENT_DIR}",
                "OPSCORE_ORACLE_CLIENT_ROOT": "${ORACLE_INSTANT_CLIENT_ROOT}",
            },
            "install_hint": (
                "默认使用 python-oracledb Thick Mode。请安装 Oracle Instant Client，"
                "并配置 OPSCORE_ORACLE_CLIENT_LIB_DIR 或放到自动发现目录。只有确认目标库支持 "
                "Thin Mode 时，才显式设置 use_thick_mode=false 或 OPSCORE_ORACLE_THICK_MODE=false "
                "并重启后端。"
            ),
            "test_sql": "SELECT 1 FROM DUAL",
            "operation_profile": get_database_operation_profile("oracle"),
            "oracle_client": oracle_client,
        },
        "mysql": {
            "id": "mysql",
            "label": "MySQL / TiDB / OceanBase(MySQL)",
            "connector": "native_sql",
            "python_package": "pymysql",
            "python_package_installed": _module_installed("pymysql"),
            "external_client_required": False,
            "external_client_detected": True,
            "external_client_name": "",
            "status": "ready" if _module_installed("pymysql") else "missing_python_package",
            "install_hint": "使用 PyMySQL 原生驱动，不需要额外安装系统客户端；确认 requirements.txt 已安装即可。",
            "test_sql": "SELECT 1",
            "operation_profile": get_database_operation_profile("mysql"),
        },
        "postgresql": {
            "id": "postgresql",
            "label": "PostgreSQL / Kingbase",
            "connector": "native_sql",
            "python_package": "psycopg2",
            "python_package_installed": _module_installed("psycopg2"),
            "external_client_required": False,
            "external_client_detected": True,
            "external_client_name": "",
            "status": "ready" if _module_installed("psycopg2") else "missing_python_package",
            "install_hint": "使用 psycopg2-binary；Linux 离线部署时如不用 binary 包，需要准备 libpq/编译依赖。",
            "test_sql": "SELECT 1",
            "operation_profile": get_database_operation_profile("postgresql"),
        },
        "mssql": {
            "id": "mssql",
            "label": "SQL Server",
            "connector": "native_sql",
            "python_package": "pyodbc",
            "python_package_installed": _module_installed("pyodbc"),
            "external_client_required": True,
            "external_client_detected": bool(mssql_drivers),
            "external_client_name": "Microsoft ODBC Driver 17 for SQL Server",
            "status": (
                "ready"
                if _module_installed("pyodbc") and mssql_drivers
                else "missing_external_client"
            ),
            "detected_drivers": mssql_drivers,
            "preferred_driver": preferred_mssql_driver or "ODBC Driver 17 for SQL Server",
            "install_hint": "除 pyodbc 外，运行机器优先安装 Microsoft ODBC Driver 17 for SQL Server；如已有 Driver 18，OpsCore 会自动兼容。",
            "test_sql": "SELECT 1",
            "operation_profile": get_database_operation_profile("mssql"),
        },
        "redis": {
            "id": "redis",
            "label": "Redis",
            "connector": "native_kv",
            "python_package": "redis",
            "python_package_installed": _module_installed("redis"),
            "external_client_required": False,
            "external_client_detected": True,
            "external_client_name": "",
            "status": "ready" if _module_installed("redis") else "missing_python_package",
            "install_hint": "使用 redis-py 原生客户端，不需要额外系统客户端。",
            "test_command": "PING",
            "operation_profile": get_database_operation_profile("redis"),
        },
        "mongodb": {
            "id": "mongodb",
            "label": "MongoDB",
            "connector": "native_document",
            "python_package": "pymongo",
            "python_package_installed": _module_installed("pymongo"),
            "external_client_required": False,
            "external_client_detected": True,
            "external_client_name": "",
            "status": "ready" if _module_installed("pymongo") else "missing_python_package",
            "install_hint": "使用 PyMongo 原生客户端，不需要额外系统客户端。",
            "test_command": "find admin.system.version",
            "operation_profile": get_database_operation_profile("mongodb"),
        },
        "dameng": {
            "id": "dameng",
            "label": "达梦数据库 DM",
            "connector": "native_sql",
            "python_package": "dmpython",
            "python_import": "dmPython",
            "python_package_installed": dameng_native_ready,
            "external_client_required": False,
            "external_client_detected": dameng_jdbc_driver["detected"],
            "external_client_name": "达梦 JDBC Driver（可选兜底）",
            "status": "ready" if dameng_native_ready or dameng_jdbc_ready else "missing_python_package",
            "install_hint": (
                "优先安装 dmpython 使用达梦原生连接；离线环境如果暂不能安装 dmpython，仍可配置 "
                "JayDeBeApi + 达梦 JDBC jar 作为兜底。"
            ),
            "test_sql": "SELECT 1",
            "operation_profile": get_database_operation_profile("dameng"),
            "jdbc_fallback": {
                "connector": "database_jdbc",
                "python_package": "JayDeBeApi",
                "python_package_installed": _module_installed("jaydebeapi"),
                "detected_jars": dameng_jdbc_driver["jar_paths"],
                "driver_class": dameng_jdbc_driver["driver_class"],
                "recommended_path_windows": JDBC_DATABASE_DRIVERS["dameng"].get("recommended_path_windows", ""),
                "recommended_path_linux": JDBC_DATABASE_DRIVERS["dameng"].get("recommended_path_linux", ""),
                "env_vars": dameng_jdbc_driver["env_vars"],
            },
        },
    }
    for key, meta in JDBC_DATABASE_DRIVERS.items():
        if key == "dameng":
            continue
        jdbc_driver = discover_jdbc_driver(key)
        package_ready = _module_installed("jaydebeapi")
        capabilities[key] = {
            "id": key,
            "label": meta["label"],
            "connector": "database_jdbc",
            "python_package": "JayDeBeApi",
            "python_package_installed": package_ready,
            "external_client_required": True,
            "external_client_detected": jdbc_driver["detected"],
            "external_client_name": f"{meta['label']} JDBC Driver",
            "status": "ready" if package_ready and jdbc_driver["detected"] else "missing_external_client",
            "detected_jars": jdbc_driver["jar_paths"],
            "recommended_path_windows": meta.get("recommended_path_windows", ""),
            "recommended_path_linux": meta.get("recommended_path_linux", ""),
            "env_vars": {
                env_name: f"${{{env_name}}}"
                for env_name in jdbc_driver["env_vars"]
            },
            "install_hint": (
                f"下载 {meta['label']} 官方 JDBC 驱动 jar，放到推荐目录，或设置 "
                f"{', '.join(jdbc_driver['env_vars'])}。Linux 部署同样使用这些环境变量。"
            ),
            "test_sql": meta.get("test_statement") or "SELECT 1",
            "operation_profile": get_database_operation_profile(key),
            "jdbc_driver": jdbc_driver,
        }
    return {"drivers": capabilities, "oracle_client": oracle_client}


class DatabaseExecutor:
    """
    统一的数据库直连查询引擎（黑盒模式）。
    对大模型屏蔽环境依赖和转义问题，直接返回 JSON 格式结果。
    """

    @staticmethod
    def _statement_type(sql: str) -> str:
        return statement_type(sql)

    @staticmethod
    def _should_commit_after_statement(sql: str) -> bool:
        return should_commit_after_statement(sql)

    @staticmethod
    def _commit_if_needed(conn: Any, sql: str) -> None:
        commit_if_needed(conn, sql)

    @staticmethod
    def _query_success(sql: str, rows: list[Any], data: list[Any] | None = None) -> dict:
        return query_success(sql, rows, data)

    @staticmethod
    def _statement_success(conn: Any, cursor: Any, sql: str) -> dict:
        return statement_success(conn, cursor, sql)

    @staticmethod
    def _execute_mysql(host, port, user, password, database, sql) -> dict:
        return execute_mysql(host, port, user, password, database, sql)

    @staticmethod
    def _init_oracle_client_if_requested(oracledb, extra_args: dict | None) -> None:
        global _ORACLE_CLIENT_INIT_ATTEMPTED
        config = extra_args or {}
        if not _oracle_thick_mode_enabled(config):
            return

        with _ORACLE_CLIENT_LOCK:
            if _ORACLE_CLIENT_INIT_ATTEMPTED:
                return
            lib_dir = discover_oracle_client_lib_dir(config).get("lib_dir")
            kwargs = {"lib_dir": str(lib_dir)} if lib_dir else {}
            oracledb.init_oracle_client(**kwargs)
            _ORACLE_CLIENT_INIT_ATTEMPTED = True

    @staticmethod
    def _oracle_dsn(oracledb, host, port, sid_or_service_name, extra_args: dict | None) -> str:
        config = extra_args or {}
        sid = config.get("SID") or config.get("sid")
        service_name = config.get("service_name")
        tns_alias = config.get("tns_alias")
        connect_type = str(
            config.get("oracle_connect_type") or config.get("connect_type") or ""
        ).strip().lower()
        if connect_type in {"tns", "tns_alias"}:
            return str(tns_alias or sid_or_service_name or "")
        if tns_alias:
            return str(tns_alias)
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
        if "DPY-2019" in raw:
            return (
                f"{raw}\n"
                "OpsCore Oracle 现在默认使用 python-oracledb Thick Mode，但当前 Python "
                "后端进程已经创建过 thin mode 连接，同一进程内不能再切换到 thick mode。"
                "处理方式：停止并重新启动后端，让 Oracle 在第一次连接前完成 Thick Mode "
                "初始化；同时确认 OPSCORE_ORACLE_CLIENT_LIB_DIR 指向 Oracle Instant Client。"
            )
        if "DPI-1047" in raw or "Oracle Client library cannot be loaded" in raw:
            return (
                f"{raw}\n"
                "OpsCore Oracle 默认使用 python-oracledb Thick Mode，但当前后端没有加载到 "
                "Oracle Instant Client。请安装 Instant Client，并设置 "
                "OPSCORE_ORACLE_CLIENT_LIB_DIR；如果确实要使用 Thin Mode，请显式设置 "
                "use_thick_mode=false 或 OPSCORE_ORACLE_THICK_MODE=false 后重启后端。"
            )
        if "DPY-3015" in raw:
            return (
                f"{raw}\n"
                "当前 Oracle 连接仍落到了 python-oracledb Thin Mode；目标账号使用了旧版 "
                "10G password verifier，Thin Mode 不支持。处理方式：重启后端，让 Oracle "
                "在第一次连接前按默认 Thick Mode 初始化；或让 DBA 重置该用户密码生成 "
                "11G/12C verifier。"
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
                    if cursor.description is None:
                        return DatabaseExecutor._statement_success(conn, cursor, sql)

                    # 限制最大拉取 1000 条，防止大模型 token 爆仓
                    rows = cursor.fetchmany(1000) or []

                    # 处理列名映射
                    columns = [col[0] for col in (cursor.description or [])]
                    result_dicts = [dict(zip(columns, row)) for row in rows]

                    return DatabaseExecutor._query_success(sql, rows, result_dicts)
        except Exception as e:
            logger.error(f"Oracle 连接执行失败: {e}")
            return {"success": False, "error": DatabaseExecutor._oracle_error_message(e)}

    @staticmethod
    def _execute_postgresql(host, port, user, password, database, sql) -> dict:
        return execute_postgresql(host, port, user, password, database, sql)

    @staticmethod
    def _execute_mssql(host, port, user, password, database, sql) -> dict:
        return execute_mssql(host, port, user, password, database, sql)

    @staticmethod
    def _execute_dameng(host, port, user, password, database, sql, extra_args: dict | None = None) -> dict:
        result = execute_dameng(host, port, user, password, database, sql)
        if result.get("success") or not result.get("missing_driver"):
            return result

        jdbc_driver = discover_jdbc_driver("dameng", extra_args)
        if _module_installed("jaydebeapi") and jdbc_driver["detected"]:
            fallback = execute_jdbc(
                "dameng",
                host,
                port,
                user,
                password,
                database,
                sql,
                extra_args,
                JDBC_DATABASE_DRIVERS,
                normalize_database_driver_key,
                discover_jdbc_driver,
            )
            if fallback.get("success"):
                fallback["connector"] = "database_jdbc"
            return fallback
        return result

    @staticmethod
    def _jdbc_url(db_type: str, host, port, database: str, extra_args: dict | None) -> str:
        return build_jdbc_url(
            JDBC_DATABASE_DRIVERS,
            db_type,
            host,
            port,
            database,
            extra_args,
        )

    @staticmethod
    def _execute_jdbc(db_type, host, port, user, password, database, sql, extra_args: dict | None = None) -> dict:
        return execute_jdbc(
            db_type,
            host,
            port,
            user,
            password,
            database,
            sql,
            extra_args,
            JDBC_DATABASE_DRIVERS,
            normalize_database_driver_key,
            discover_jdbc_driver,
        )

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
        db_type = normalize_database_driver_key(db_type)
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
        elif db_type == "dameng":
            res = self._execute_dameng(host, port, user, password, database, sql, extra_args)
        elif db_type in JDBC_DATABASE_DRIVERS:
            res = self._execute_jdbc(db_type, host, port, user, password, database, sql, extra_args)
        else:
            res = {
                "success": False,
                "error": f"暂不支持的原生数据库类型: {db_type}。目前支持 mysql, oracle, postgresql, mssql, db2, dameng, xugu, hive, iotdb。",
            }

        return json.dumps(
            res, ensure_ascii=False, default=str
        )  # default=str 解决 datetime 等无法 JSON 序列化的问题


db_executor = DatabaseExecutor()
