import logging
import unittest

from core.request_context import current_request_id, request_id_context


class TestRequestContextCore(unittest.TestCase):
    def test_request_id_context_sets_and_resets_value(self):
        self.assertIsNone(current_request_id())
        with request_id_context("req-unit"):
            self.assertEqual(current_request_id(), "req-unit")
        self.assertIsNone(current_request_id())

    def test_log_record_has_request_id_after_main_configures_factory(self):
        import main  # noqa: F401

        with request_id_context("req-log"):
            record = logging.getLogger("opscore.test").makeRecord(
                "opscore.test",
                logging.INFO,
                __file__,
                1,
                "hello",
                args=(),
                exc_info=None,
            )

        self.assertEqual(record.request_id, "req-log")


if __name__ == "__main__":
    unittest.main()
