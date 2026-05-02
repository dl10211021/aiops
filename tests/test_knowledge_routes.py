import asyncio
import unittest
import warnings
from unittest.mock import patch

from fastapi import HTTPException

from api import knowledge_routes, routes
from core.knowledge_base_service import KnowledgeBaseServiceError


warnings.filterwarnings(
    "ignore",
    message=r"Please use `import python_multipart` instead\.",
    category=PendingDeprecationWarning,
)


class TestKnowledgeRoutes(unittest.TestCase):
    def test_knowledge_routes_are_included_in_api_router(self):
        paths = {route.path for route in routes.router.routes}

        self.assertIn("/knowledge/upload", paths)
        self.assertIn("/knowledge/list", paths)
        self.assertIn("/knowledge/{filename}", paths)

    def test_upload_knowledge_document_preserves_response_shape(self):
        upload = object()

        with patch(
            "api.knowledge_routes.ingest_knowledge_document",
            return_value="注入成功",
        ):
            response = asyncio.run(knowledge_routes.upload_knowledge_document(upload))

        self.assertEqual(response.status, "success")
        self.assertEqual(response.message, "注入成功")

    def test_list_knowledge_documents_preserves_response_shape(self):
        with patch(
            "api.knowledge_routes.list_knowledge_document_records",
            return_value=["runbook.txt"],
        ):
            response = asyncio.run(knowledge_routes.list_knowledge_documents())

        self.assertEqual(response.status, "success")
        self.assertEqual(response.data, {"files": ["runbook.txt"]})

    def test_delete_knowledge_document_preserves_response_shape(self):
        with patch(
            "api.knowledge_routes.remove_knowledge_document_record",
            return_value="已成功从知识库中移除 runbook.txt",
        ):
            response = asyncio.run(knowledge_routes.delete_knowledge_document("runbook.txt"))

        self.assertEqual(response.status, "success")
        self.assertEqual(response.message, "已成功从知识库中移除 runbook.txt")

    def test_knowledge_route_errors_keep_http_semantics(self):
        with patch(
            "api.knowledge_routes.list_knowledge_document_records",
            side_effect=KnowledgeBaseServiceError(404, "知识库为空"),
        ):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(knowledge_routes.list_knowledge_documents())

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "知识库为空")


if __name__ == "__main__":
    unittest.main()
