import json
import shutil
import sys
import types
from pathlib import Path

from connections.db_manager import DatabaseExecutor


class NonQueryCursor:
    description = None
    rowcount = 3

    def __init__(self):
        self.fetched = False
        self.sql = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql):
        self.sql = sql

    def fetchmany(self, limit):
        self.fetched = True
        raise AssertionError("non-query statements must not fetch rows")

    def close(self):
        pass


class ContextConnection:
    def __init__(self):
        self.cursor_obj = NonQueryCursor()
        self.committed = False
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self, *args, **kwargs):
        return self.cursor_obj

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


def _assert_non_query_result(result_text, connection):
    result = json.loads(result_text)
    assert result["success"] is True
    assert result["has_result_set"] is False
    assert result["statement_type"] == "update"
    assert result["committed"] is True
    assert result["affected_rows"] == 3
    assert result["data"] == []
    assert connection.cursor_obj.fetched is False
    assert connection.committed is True


def test_mysql_non_query_statement_does_not_fetch(monkeypatch):
    connection = ContextConnection()
    fake_pymysql = types.SimpleNamespace(
        connect=lambda **kwargs: connection,
        cursors=types.SimpleNamespace(DictCursor=object),
    )
    monkeypatch.setitem(sys.modules, "pymysql", fake_pymysql)

    result_text = DatabaseExecutor().execute_query(
        "mysql",
        "db.local",
        3306,
        "root",
        "secret",
        "ops",
        "UPDATE app_config SET value='on'",
        {},
    )

    _assert_non_query_result(result_text, connection)


def test_postgresql_non_query_statement_does_not_fetch(monkeypatch):
    connection = ContextConnection()
    fake_extras = types.SimpleNamespace(RealDictCursor=object)
    fake_psycopg2 = types.SimpleNamespace(
        connect=lambda **kwargs: connection,
        extras=fake_extras,
    )
    monkeypatch.setitem(sys.modules, "psycopg2", fake_psycopg2)
    monkeypatch.setitem(sys.modules, "psycopg2.extras", fake_extras)

    result_text = DatabaseExecutor().execute_query(
        "postgresql",
        "db.local",
        5432,
        "postgres",
        "secret",
        "ops",
        "UPDATE app_config SET value='on'",
        {},
    )

    _assert_non_query_result(result_text, connection)


def test_mssql_non_query_statement_does_not_fetch(monkeypatch):
    connection = ContextConnection()
    fake_pyodbc = types.SimpleNamespace(connect=lambda *args, **kwargs: connection)
    monkeypatch.setitem(sys.modules, "pyodbc", fake_pyodbc)

    result_text = DatabaseExecutor().execute_query(
        "mssql",
        "db.local",
        1433,
        "sa",
        "secret",
        "ops",
        "UPDATE app_config SET value='on'",
        {},
    )

    _assert_non_query_result(result_text, connection)


def test_jdbc_non_query_statement_does_not_fetch(monkeypatch):
    connection = ContextConnection()
    root = Path.cwd() / "tests" / "tmp_jdbc_non_query"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    jar = root / "db2jcc4.jar"
    jar.write_text("fake", encoding="utf-8")
    fake_jaydebeapi = types.SimpleNamespace(
        connect=lambda driver, url, creds, jars: connection
    )
    monkeypatch.setitem(sys.modules, "jaydebeapi", fake_jaydebeapi)

    try:
        result_text = DatabaseExecutor().execute_query(
            "db2",
            "db.local",
            50000,
            "db2inst1",
            "secret",
            "SAMPLE",
            "UPDATE app_config SET value='on'",
            {"jdbc_jar": str(jar)},
        )

        _assert_non_query_result(result_text, connection)
        assert connection.closed is True
    finally:
        shutil.rmtree(root, ignore_errors=True)
