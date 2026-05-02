import unittest

from api.mappers import (
    chat_stream_agent_kwargs,
    session_webhook_delivery_kwargs,
    tool_approval_response_kwargs,
)
from api.schemas import ChatRequest, SessionWebhookSendRequest


class TestApiMappers(unittest.TestCase):
    def test_chat_stream_agent_kwargs_preserves_request_fields(self):
        req = ChatRequest(
            session_id="sid-1",
            message="查一下磁盘",
            display_message="/inspect disk",
            model_name="ops-model",
            thinking_mode="high",
            attachments=[{"kind": "text", "filename": "note.txt", "text": "context"}],
        )

        self.assertEqual(
            chat_stream_agent_kwargs(req),
            {
                "session_id": "sid-1",
                "user_message": "查一下磁盘",
                "user_display_message": "/inspect disk",
                "model_name": "ops-model",
                "thinking_mode": "high",
                "user_attachments": req.attachments,
            },
        )

    def test_chat_stream_agent_kwargs_defaults_blank_thinking_mode_to_off(self):
        req = ChatRequest(session_id="sid-1", message="hello", thinking_mode="")

        self.assertEqual(chat_stream_agent_kwargs(req)["thinking_mode"], "off")

    def test_session_webhook_delivery_kwargs_preserves_all_request_fields(self):
        req = SessionWebhookSendRequest(
            webhook_url="https://ops.example.com/hook",
            payload_type="summary",
            channel="wechat",
            title="日报",
            model_name="ops-model",
            allow_private_targets=True,
        )

        self.assertEqual(
            session_webhook_delivery_kwargs(req),
            {
                "webhook_url": "https://ops.example.com/hook",
                "payload_type": "summary",
                "channel": "wechat",
                "title": "日报",
                "model_name": "ops-model",
                "allow_private_targets": True,
            },
        )

    def test_tool_approval_response_kwargs_omits_data_for_pending_future(self):
        self.assertEqual(
            tool_approval_response_kwargs(
                {
                    "message": "Approval action submitted.",
                    "approval": None,
                    "include_approval": False,
                }
            ),
            {"status": "success", "message": "Approval action submitted."},
        )

    def test_tool_approval_response_kwargs_includes_orphaned_approval_record(self):
        approval = {"id": "call-1", "status": "approved"}

        self.assertEqual(
            tool_approval_response_kwargs(
                {
                    "message": "Approval action recorded.",
                    "approval": approval,
                    "include_approval": True,
                }
            ),
            {
                "status": "success",
                "message": "Approval action recorded.",
                "data": {"approval": approval},
            },
        )


if __name__ == "__main__":
    unittest.main()
