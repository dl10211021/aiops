import unittest

import pyarrow as pa

from core.lancedb_utils import ensure_lancedb_table


class TestRagLanceDB(unittest.TestCase):
    def test_existing_knowledge_table_is_opened_when_create_races(self):
        class FakeLanceDB:
            def __init__(self):
                self.opened = False

            def table_names(self):
                return []

            def create_table(self, name, schema):
                raise RuntimeError(f"Table '{name}' already exists")

            def open_table(self, name):
                self.opened = True
                return {"name": name}

        db = FakeLanceDB()
        schema = pa.schema([pa.field("id", pa.string())])

        table = ensure_lancedb_table(db, "knowledge_base", schema)

        self.assertEqual(table, {"name": "knowledge_base"})
        self.assertTrue(db.opened)


if __name__ == "__main__":
    unittest.main()
