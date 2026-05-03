import unittest

from connections.db_execution_result import (
    query_success,
    should_commit_after_statement,
    statement_success,
    statement_type,
)


class FakeConnection:
    def __init__(self):
        self.committed = False

    def commit(self):
        self.committed = True


class FakeCursor:
    rowcount = 3


class DatabaseExecutionResultTest(unittest.TestCase):
    def test_statement_type_and_commit_rules_match_database_executor_contract(self):
        self.assertEqual(statement_type("  UPDATE app_config SET value='on'"), "update")
        with self.assertRaises(IndexError):
            statement_type("")
        self.assertTrue(should_commit_after_statement("UPDATE app_config SET value='on'"))
        self.assertFalse(should_commit_after_statement("SELECT 1"))
        self.assertFalse(should_commit_after_statement("SHOW DATABASES"))
        self.assertFalse(should_commit_after_statement("ROLLBACK"))

    def test_statement_success_commits_non_query_and_reports_affected_rows(self):
        conn = FakeConnection()

        result = statement_success(conn, FakeCursor(), "UPDATE app_config SET value='on'")

        self.assertTrue(conn.committed)
        self.assertEqual(
            result,
            {
                "success": True,
                "has_result_set": False,
                "statement_type": "update",
                "committed": True,
                "affected_rows": 3,
                "message": "UPDATE 已执行并提交",
                "data": [],
            },
        )

    def test_query_success_preserves_rows_without_committing(self):
        rows = [{"ok": 1}]

        result = query_success("SELECT 1", rows)

        self.assertEqual(
            result,
            {
                "success": True,
                "has_result_set": True,
                "statement_type": "select",
                "committed": False,
                "count": 1,
                "data": rows,
            },
        )


if __name__ == "__main__":
    unittest.main()
