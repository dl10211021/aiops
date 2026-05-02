import asyncio
import unittest
from unittest.mock import Mock

from core.application_lifecycle_service import start_app_services, stop_app_services


class FakeCronManager:
    def __init__(self):
        self.started = False

    def start_scheduler(self):
        self.started = True


class TestApplicationLifecycleService(unittest.TestCase):
    def test_start_app_services_starts_dependencies_and_schedules_hydration(self):
        heartbeat_starter = Mock()
        cron_manager = FakeCronManager()
        logger = Mock()
        scheduled = []
        hydrated = []

        async def hydration_runner():
            hydrated.append(True)

        def task_scheduler(coro):
            scheduled.append(coro)
            return "task-handle"

        result = start_app_services(
            task_scheduler=task_scheduler,
            heartbeat_starter=heartbeat_starter,
            cron_manager=cron_manager,
            hydration_runner=hydration_runner,
            logger=logger,
        )

        self.assertEqual(result, "task-handle")
        heartbeat_starter.assert_called_once_with()
        self.assertTrue(cron_manager.started)
        logger.info.assert_called_once_with("Heartbeat worker started.")
        self.assertEqual(len(scheduled), 1)

        asyncio.run(scheduled[0])

        self.assertEqual(hydrated, [True])

    def test_stop_app_services_logs_shutdown(self):
        logger = Mock()

        stop_app_services(logger)

        logger.info.assert_called_once_with("OpsCore Backend shutting down...")


if __name__ == "__main__":
    unittest.main()
