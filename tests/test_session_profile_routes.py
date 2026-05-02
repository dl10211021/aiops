import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from api import routes


class TestSessionProfileRoutes(unittest.TestCase):
    def test_get_active_session_profile_returns_profile_payload(self):
        profile = {"session_id": "sid-1", "risk_level": "watch"}

        with patch("core.session_profile.get_session_profile", return_value=profile) as get_profile:
            response = asyncio.run(routes.get_active_session_profile("sid-1"))

        get_profile.assert_called_once_with("sid-1")
        self.assertEqual(response.status, "success")
        self.assertEqual(response.data, {"profile": profile})

    def test_generate_active_session_profile_forwards_options_and_response(self):
        profile = {"session_id": "sid-1", "risk_level": "normal"}
        generate_profile = AsyncMock(return_value=profile)

        with patch("core.session_profile.generate_session_profile", generate_profile):
            response = asyncio.run(
                routes.generate_active_session_profile(
                    "sid-1",
                    routes.SessionProfileGenerateRequest(
                        model_name="ops-model",
                        include_inspection=False,
                    ),
                )
            )

        generate_profile.assert_awaited_once_with(
            "sid-1",
            model_name="ops-model",
            include_inspection=False,
        )
        self.assertEqual(response.status, "success")
        self.assertEqual(response.message, "资产画像已生成")
        self.assertEqual(response.data, {"profile": profile})

    def test_generate_active_session_profile_maps_missing_session_to_404(self):
        generate_profile = AsyncMock(side_effect=ValueError("会话不存在"))

        with patch("core.session_profile.generate_session_profile", generate_profile):
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(
                    routes.generate_active_session_profile(
                        "missing",
                        routes.SessionProfileGenerateRequest(),
                    )
                )

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "会话不存在")


if __name__ == "__main__":
    unittest.main()
