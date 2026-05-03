import asyncio
import json
import unittest
from unittest.mock import patch

from core.dispatcher_database_tools import DATABASE_TOOL_NAMES, execute_database_tool


class DispatcherDatabaseToolsTests(unittest.TestCase):
    def test_database_tool_names_cover_native_datastore_tools(self):
        self.assertLessEqual(
            {"db_execute_query", "redis_execute_command", "memcached_execute_command", "mongodb_find"},
            DATABASE_TOOL_NAMES,
        )

    def test_sql_query_rejects_non_sql_protocol(self):
        result = asyncio.run(
            execute_database_tool(
                "db_execute_query",
                {"sql": "SELECT 1"},
                {
                    "asset_type": "redis",
                    "protocol": "redis",
                    "host": "redis.local",
                    "port": 6379,
                    "username": "ops",
                    "password": "secret",
                    "extra_args": {"db_type": "redis"},
                },
            )
        )

        payload = json.loads(result)
        self.assertEqual(payload["status"], "ERROR")
        self.assertIn("不能使用 db_execute_query", payload["error"])

    def test_mongodb_find_uses_managed_context_credentials(self):
        with patch("connections.datastore_manager.mongo_executor.find") as find:
            find.return_value = {"success": True, "documents": []}
            result = asyncio.run(
                execute_database_tool(
                    "mongodb_find",
                    {"collection": "events", "filter": {"level": "warn"}},
                    {
                        "host": "mongo.local",
                        "port": 27017,
                        "username": "ops",
                        "password": "secret",
                        "extra_args": {"database": "ops"},
                    },
                )
            )

        self.assertTrue(json.loads(result)["success"])
        find.assert_called_once_with(
            host="mongo.local",
            port=27017,
            username="ops",
            password="secret",
            database="ops",
            collection="events",
            filter_doc={"level": "warn"},
            projection=None,
            limit=100,
            extra_args={"database": "ops"},
        )


if __name__ == "__main__":
    unittest.main()
