import unittest

from core.knowledge_vector_config import knowledge_vector_table_name


class TestKnowledgeVectorConfig(unittest.TestCase):
    def test_legacy_dimension_keeps_original_table_name(self):
        self.assertEqual(knowledge_vector_table_name(3072), "knowledge_base")

    def test_local_embedding_dimension_uses_dimension_scoped_table(self):
        self.assertEqual(knowledge_vector_table_name(1024), "knowledge_base_1024")


if __name__ == "__main__":
    unittest.main()
