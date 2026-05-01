import json
import shutil
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from connections.db_manager import (
    DatabaseExecutor,
    discover_jdbc_driver,
    get_database_operation_profile,
    normalize_database_driver_key,
)


class FakeCursor:
    description = [("COL1",)]

    def __init__(self):
        self.sql = ""

    def execute(self, sql):
        self.sql = sql

    def fetchmany(self, limit):
        return [(1,)]

    def close(self):
        pass


class FakeConnection:
    def __init__(self):
        self.cursor_obj = FakeCursor()
        self.closed = False

    def cursor(self):
        return self.cursor_obj

    def close(self):
        self.closed = True


class TestDbManagerJdbc(unittest.TestCase):
    def tearDown(self):
        for path in (Path.cwd() / "tests").glob("tmp_jdbc_*"):
            shutil.rmtree(path, ignore_errors=True)

    def test_dm_alias_normalizes_to_dameng_profile(self):
        self.assertEqual(normalize_database_driver_key("dm"), "dameng")
        self.assertEqual(get_database_operation_profile("dm")["id"], "dameng")

    def test_mysql_compatible_analytics_aliases_normalize_to_mysql(self):
        for alias in ("doris_fe", "starrocks_fe", "greptime"):
            self.assertEqual(normalize_database_driver_key(alias), "mysql")

    def test_hive_and_iotdb_profiles_expose_jdbc_defaults(self):
        self.assertEqual(normalize_database_driver_key("apache_hive"), "hive")
        self.assertEqual(get_database_operation_profile("hive")["default_port"], 10000)
        self.assertEqual(normalize_database_driver_key("apache_iotdb"), "iotdb")
        self.assertEqual(get_database_operation_profile("iotdb")["default_port"], 6667)

    def test_discover_jdbc_driver_uses_configured_jar(self):
        root = Path.cwd() / "tests" / "tmp_jdbc_discovery"
        root.mkdir(parents=True, exist_ok=True)
        jar = root / "DmJdbcDriver18.jar"
        jar.write_text("fake", encoding="utf-8")

        result = discover_jdbc_driver("dameng", {"jdbc_jar": str(jar)})

        self.assertTrue(result["detected"])
        self.assertEqual(result["jar_paths"], [str(jar.resolve())])
        self.assertEqual(result["driver_class"], "dm.jdbc.driver.DmDriver")

    def test_execute_jdbc_uses_driver_class_url_and_jars(self):
        root = Path.cwd() / "tests" / "tmp_jdbc_execute"
        root.mkdir(parents=True, exist_ok=True)
        jar = root / "db2jcc4.jar"
        jar.write_text("fake", encoding="utf-8")
        fake_conn = FakeConnection()
        calls = []

        fake_jaydebeapi = types.SimpleNamespace(
            connect=lambda driver, url, creds, jars: calls.append(
                {"driver": driver, "url": url, "creds": creds, "jars": jars}
            ) or fake_conn
        )

        with patch.dict(sys.modules, {"jaydebeapi": fake_jaydebeapi}):
            result_text = DatabaseExecutor().execute_query(
                "db2",
                "db.local",
                50000,
                "db2inst1",
                "secret",
                "SAMPLE",
                "SELECT 1 FROM SYSIBM.SYSDUMMY1",
                {"jdbc_jar": str(jar)},
            )

        result = json.loads(result_text)
        self.assertTrue(result["success"])
        self.assertEqual(result["data"], [{"COL1": 1}])
        self.assertEqual(calls[0]["driver"], "com.ibm.db2.jcc.DB2Driver")
        self.assertEqual(calls[0]["url"], "jdbc:db2://db.local:50000/SAMPLE")
        self.assertEqual(calls[0]["creds"], ["db2inst1", "secret"])
        self.assertEqual(calls[0]["jars"], [str(jar.resolve())])

    def test_execute_jdbc_reports_missing_jar_with_setup_hint(self):
        result_text = DatabaseExecutor().execute_query(
            "xugu",
            "db.local",
            5138,
            "SYSDBA",
            "secret",
            "TEST",
            "SELECT 1",
            {},
        )

        result = json.loads(result_text)
        self.assertFalse(result["success"])
        self.assertIn("JDBC 驱动 jar", result["error"])


if __name__ == "__main__":
    unittest.main()
