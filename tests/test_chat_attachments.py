import io
import unittest
import zipfile

from core.chat_attachments import (
    CHAT_ATTACHMENT_MAX_SIZE,
    ChatAttachmentError,
    build_chat_attachment_preview,
    normalize_chat_attachments,
    preview_attachment_content,
)


class TestChatAttachments(unittest.TestCase):
    def test_normalize_attachment_sanitizes_metadata(self):
        attachments = normalize_chat_attachments(
            [
                {
                    "filename": "../screen.png",
                    "ext": ".png",
                    "size": 5,
                    "kind": "image",
                    "pages": 2,
                    "rows": 3,
                    "sheets": ["Sheet1", "x" * 120],
                    "truncated": True,
                    "data_url": "data:image/png;base64,aGVsbG8=",
                }
            ]
        )

        self.assertEqual(attachments[0]["filename"], "screen.png")
        self.assertEqual(attachments[0]["content_type"], "image/png")
        self.assertEqual(attachments[0]["sheets"], ["Sheet1", "x" * 80])
        self.assertNotIn("..", attachments[0]["filename"])

    def test_preview_attachment_content_parses_xlsx(self):
        xlsx_bytes = io.BytesIO()
        with zipfile.ZipFile(xlsx_bytes, "w") as zf:
            zf.writestr(
                "xl/sharedStrings.xml",
                """<?xml version="1.0" encoding="UTF-8"?>
                <sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
                  <si><t>资产</t></si><si><t>状态</t></si><si><t>oracle-01</t></si><si><t>异常</t></si>
                </sst>""",
            )
            zf.writestr(
                "xl/worksheets/sheet1.xml",
                """<?xml version="1.0" encoding="UTF-8"?>
                <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
                  <sheetData>
                    <row><c t="s"><v>0</v></c><c t="s"><v>1</v></c></row>
                    <row><c t="s"><v>2</v></c><c t="s"><v>3</v></c></row>
                  </sheetData>
                </worksheet>""",
            )

        preview = preview_attachment_content(
            "assets.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            xlsx_bytes.getvalue(),
        )

        self.assertIn("oracle-01", preview["text"])
        self.assertEqual(preview["rows"], 2)

    def test_build_chat_attachment_preview_rejects_empty_filename(self):
        with self.assertRaises(ChatAttachmentError) as ctx:
            build_chat_attachment_preview("", "text/plain", b"hello")

        self.assertEqual(ctx.exception.status_code, 422)

    def test_build_chat_attachment_preview_rejects_oversized_content(self):
        with self.assertRaises(ChatAttachmentError) as ctx:
            build_chat_attachment_preview(
                "large.txt",
                "text/plain",
                b"x" * (CHAT_ATTACHMENT_MAX_SIZE + 1),
            )

        self.assertEqual(ctx.exception.status_code, 413)
