import unittest

from core.hydration_status_service import (
    finish_hydrate_run,
    get_hydrate_status_record,
    record_hydrate_done,
    record_hydrate_success,
    start_hydrate_run,
)


class TestHydrationStatusService(unittest.TestCase):
    def setUp(self):
        start_hydrate_run(0)
        finish_hydrate_run()

    def test_hydrate_status_tracks_run_progress(self):
        start_hydrate_run(3)
        record_hydrate_success()
        record_hydrate_done()
        record_hydrate_done()

        self.assertEqual(
            get_hydrate_status_record(),
            {"total": 3, "done": 2, "success": 1, "running": True},
        )

        finish_hydrate_run()

        self.assertEqual(
            get_hydrate_status_record(),
            {"total": 3, "done": 2, "success": 1, "running": False},
        )

    def test_hydrate_status_read_returns_copy(self):
        start_hydrate_run(1)
        status = get_hydrate_status_record()

        status["done"] = 99

        self.assertEqual(get_hydrate_status_record()["done"], 0)


if __name__ == "__main__":
    unittest.main()
