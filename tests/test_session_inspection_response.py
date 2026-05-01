import unittest

from core.session_inspection_response import build_inspection_response_payload


class TestSessionInspectionResponse(unittest.TestCase):
    def test_warning_report_is_successful_api_response(self):
        report = {"status": "warning", "summary": "部分检查失败"}

        payload = build_inspection_response_payload(report)

        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["message"], "部分检查失败")
        self.assertIs(payload["data"]["inspection"], report)

    def test_error_report_keeps_error_status_and_message_fallback(self):
        report = {"status": "error", "message": "会话不存在"}

        payload = build_inspection_response_payload(report)

        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["message"], "会话不存在")

    def test_missing_status_defaults_to_error(self):
        payload = build_inspection_response_payload({})

        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["message"], "")
