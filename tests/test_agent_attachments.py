import unittest

from core.agent_attachments import (
    _attachment_metadata_for_memory,
    _build_current_user_content,
    _chat_image_attachments,
    _model_supports_image_input,
    _safe_user_message_for_memory,
)


class TestAgentAttachments(unittest.TestCase):
    def test_safe_user_message_keeps_metadata_without_payload(self):
        message = _safe_user_message_for_memory(
            "请分析附件",
            [
                {
                    "filename": "screen.png",
                    "ext": ".png",
                    "size": 128,
                    "kind": "image",
                    "data_url": "data:image/png;base64,AAA",
                    "sheets": ["Sheet1"],
                    "truncated": True,
                }
            ],
        )

        self.assertEqual(message["content"], "请分析附件")
        self.assertEqual(message["attachments"][0]["filename"], "screen.png")
        self.assertEqual(message["attachments"][0]["sheets"], ["Sheet1"])
        self.assertTrue(message["attachments"][0]["truncated"])
        self.assertNotIn("data_url", message["attachments"][0])

    def test_attachment_metadata_for_memory_limits_items_and_skips_non_dicts(self):
        attachments = [
            {"filename": f"file-{index}.txt", "size": index}
            for index in range(10)
        ]
        metadata = _attachment_metadata_for_memory([None, *attachments])

        self.assertEqual(len(metadata), 8)
        self.assertEqual(metadata[0]["filename"], "file-0.txt")
        self.assertEqual(metadata[-1]["filename"], "file-7.txt")

    def test_chat_image_attachments_detects_images_and_caps_at_five(self):
        attachments = [
            {"filename": f"screen-{index}.png", "content_type": "image/png"}
            for index in range(7)
        ]
        attachments.append({"filename": "note.txt", "content_type": "text/plain"})

        images = _chat_image_attachments(attachments)

        self.assertEqual(len(images), 5)
        self.assertEqual(images[0]["filename"], "screen-0.png")
        self.assertEqual(images[-1]["filename"], "screen-4.png")

    def test_build_current_user_content_requires_supported_image_model(self):
        attachments = [{"data_url": "data:image/png;base64,AAA"}]

        self.assertEqual(
            _build_current_user_content("看图", attachments, "text-only-model"),
            "看图",
        )

        content = _build_current_user_content("看图", attachments, "gpt-4o")
        self.assertEqual(content[0], {"type": "text", "text": "看图"})
        self.assertEqual(
            content[1],
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAA"}},
        )

    def test_model_supports_image_input_markers(self):
        self.assertTrue(_model_supports_image_input("claude-3-7-sonnet"))
        self.assertTrue(_model_supports_image_input("qwen2.5-vl"))
        self.assertFalse(_model_supports_image_input("text-embedding-3-large"))


if __name__ == "__main__":
    unittest.main()
