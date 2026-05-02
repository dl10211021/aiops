import asyncio
import unittest

from core.session_profile_service import (
    SessionProfileServiceError,
    generate_session_profile_record,
    get_session_profile_record,
)


class TestSessionProfileService(unittest.TestCase):
    def test_get_session_profile_record_runs_loader(self):
        profile = {"session_id": "sid-1", "risk_level": "watch"}

        response = asyncio.run(
            get_session_profile_record("sid-1", loader=lambda session_id: profile)
        )

        self.assertEqual(response, profile)

    def test_generate_session_profile_record_forwards_options(self):
        calls = []

        async def generator(session_id, model_name=None, include_inspection=True):
            calls.append(
                {
                    "session_id": session_id,
                    "model_name": model_name,
                    "include_inspection": include_inspection,
                }
            )
            return {"session_id": session_id, "risk_level": "normal"}

        response = asyncio.run(
            generate_session_profile_record(
                "sid-1",
                model_name="ops-model",
                include_inspection=False,
                generator=generator,
            )
        )

        self.assertEqual(response["risk_level"], "normal")
        self.assertEqual(
            calls,
            [
                {
                    "session_id": "sid-1",
                    "model_name": "ops-model",
                    "include_inspection": False,
                }
            ],
        )

    def test_generate_session_profile_record_maps_missing_session_to_service_error(self):
        async def generator(session_id, model_name=None, include_inspection=True):
            raise ValueError("会话不存在")

        with self.assertRaises(SessionProfileServiceError) as ctx:
            asyncio.run(generate_session_profile_record("missing", generator=generator))

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "会话不存在")


if __name__ == "__main__":
    unittest.main()
