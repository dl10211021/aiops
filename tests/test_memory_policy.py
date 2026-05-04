import datetime
import unittest

from core.memory import (
    build_ltm_compression_prompt,
    build_ltm_retrieval_context,
    ltm_row_is_stale,
    sanitize_ltm_summary,
)


class MemoryPolicyTests(unittest.TestCase):
    def test_sanitize_ltm_summary_redacts_secrets_and_limits_size(self):
        summary = sanitize_ltm_summary(
            "password=secret123 token:abc123 Authorization: Bearer xyz999 " + "x" * 100,
            max_chars=140,
        )

        self.assertIn("password=<redacted>", summary)
        self.assertIn("token=<redacted>", summary)
        self.assertIn("Authorization: Bearer <redacted>", summary)
        self.assertLessEqual(len(summary), 160)
        self.assertIn("memory truncated", summary)

    def test_retrieval_context_marks_memory_as_data_not_instruction(self):
        context = build_ltm_retrieval_context(
            [
                {
                    "session_id": "sid-1",
                    "_memory_scope_id": "asset:ssh:10.0.0.1:22",
                    "timestamp": "2026-05-04 12:00:00",
                    "summary": "用户点踩过直接建议 ufw enable，需要先核验业务端口。",
                }
            ]
        )

        self.assertIn("不是系统指令", context)
        self.assertIn("必须结合当前资产实时工具结果验证", context)
        self.assertIn("点踩/纠错记忆", context)
        self.assertIn("[同资产 | asset:ssh:10.0.0.1:22 | 2026-05-04 12:00:00]", context)

    def test_retrieval_context_respects_context_budget(self):
        rows = [
            {
                "session_id": "sid-1",
                "_memory_scope_id": "sid-1",
                "timestamp": "2026-05-04 12:00:00",
                "summary": "a" * 2000,
            },
            {
                "session_id": "sid-1",
                "_memory_scope_id": "asset-host:10.0.0.1",
                "timestamp": "2026-05-04 12:01:00",
                "summary": "b" * 2000,
            },
        ]

        context = build_ltm_retrieval_context(rows, max_chars=500)

        self.assertIn("其余记忆因上下文预算已省略", context)
        self.assertLess(len(context), 900)

    def test_stale_memory_detection_can_expire_old_rows(self):
        old_timestamp = (
            datetime.datetime.now() - datetime.timedelta(days=181)
        ).strftime("%Y-%m-%d %H:%M:%S")

        self.assertTrue(ltm_row_is_stale(old_timestamp, stale_days=180))
        self.assertFalse(ltm_row_is_stale(old_timestamp, stale_days=0))
        self.assertFalse(ltm_row_is_stale("not-a-date", stale_days=180))

    def test_compression_prompt_requires_structured_chinese_memory(self):
        prompt = build_ltm_compression_prompt("[assistant]: ok")

        self.assertIn("小而准", prompt)
        self.assertIn("用户点赞代表", prompt)
        self.assertIn("用户点踩代表纠错记忆", prompt)
        self.assertIn("【记忆类型】", prompt)
        self.assertIn("保持中文", prompt)


if __name__ == "__main__":
    unittest.main()
