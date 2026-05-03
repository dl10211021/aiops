import unittest

from connections.jdbc_executor import build_jdbc_url, execute_jdbc


DRIVERS = {
    "db2": {
        "label": "IBM DB2",
        "default_port": 50000,
        "url_template": "jdbc:db2://{host}:{port}/{database}",
        "database_required": True,
    },
    "dameng": {
        "label": "达梦数据库 DM",
        "default_port": 5236,
        "url_template": "jdbc:dm://{host}:{port}",
        "database_url_template": "jdbc:dm://{host}:{port}/{database}",
    },
}


class JdbcExecutorTest(unittest.TestCase):
    def test_build_jdbc_url_supports_custom_url_and_default_port(self):
        custom = build_jdbc_url(
            DRIVERS,
            "db2",
            "db.local",
            50000,
            "SAMPLE",
            {"jdbc_url": "jdbc:custom://{host}:{port}/{database}"},
        )
        defaulted = build_jdbc_url(DRIVERS, "dameng", "dm.local", None, "", {})

        self.assertEqual(custom, "jdbc:custom://db.local:50000/SAMPLE")
        self.assertEqual(defaulted, "jdbc:dm://dm.local:5236")

    def test_build_jdbc_url_enforces_required_database(self):
        with self.assertRaisesRegex(ValueError, "IBM DB2 JDBC 连接需要填写数据库名"):
            build_jdbc_url(DRIVERS, "db2", "db.local", 50000, "", {})

    def test_execute_jdbc_rejects_unsupported_driver_before_importing_jaydebeapi(self):
        result = execute_jdbc(
            "unknown",
            "db.local",
            1,
            "user",
            "secret",
            "",
            "SELECT 1",
            {},
            DRIVERS,
            lambda value: str(value or ""),
            lambda *_args: {},
        )

        self.assertEqual(
            result,
            {"success": False, "error": "暂不支持的 JDBC 数据库类型: unknown"},
        )


if __name__ == "__main__":
    unittest.main()
