import unittest

from core.session_export import chat_history_messages, format_session_history_markdown


class TestSessionExport(unittest.TestCase):
    def test_format_session_history_markdown_includes_attachment_details(self):
        markdown = format_session_history_markdown(
            [
                {"role": "system", "content": "ignore"},
                {
                    "role": "user",
                    "content": "请分析附件",
                    "attachments": [
                        {
                            "filename": "assets.xlsx",
                            "ext": ".xlsx",
                            "size": 1200,
                            "rows": 3,
                            "pages": None,
                            "truncated": True,
                        }
                    ],
                },
                {"role": "assistant", "content": "分析完成"},
            ],
            "oracle-01",
        )

        self.assertIn("# Chat History: oracle-01", markdown)
        self.assertIn("## User", markdown)
        self.assertIn("### Attachments", markdown)
        self.assertIn("- assets.xlsx (.xlsx；1200 bytes；3 行；已截断)", markdown)
        self.assertIn("## AI Assistant", markdown)

    def test_chat_history_messages_filters_non_chat_roles(self):
        messages = chat_history_messages(
            [
                {"role": "system", "content": "ignore"},
                {"role": "user", "content": "keep"},
                {"role": "tool", "content": "ignore"},
                {"role": "assistant", "content": "keep"},
            ]
        )

        self.assertEqual([item["role"] for item in messages], ["user", "assistant"])
