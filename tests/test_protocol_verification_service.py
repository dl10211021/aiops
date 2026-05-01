import unittest

from core.protocol_verification_service import (
    ProtocolVerificationServiceError,
    build_protocol_verification_matrix,
    build_protocol_verification_overview,
    get_protocol_verification_asset,
)


class FakeProtocolAssetStore:
    def get_all_assets(self):
        return [
            {
                "id": 1,
                "remark": "linux-prod",
                "host": "10.0.0.10",
                "port": 22,
                "username": "root",
                "password": "secret",
                "asset_type": "linux",
                "protocol": "ssh",
                "extra_args": {"api_token": "token"},
            }
        ]

    def get_asset(self, asset_id: int):
        for asset in self.get_all_assets():
            if asset["id"] == asset_id:
                return asset
        return None


class TestProtocolVerificationService(unittest.TestCase):
    def test_build_overview_delegates_to_protocol_matrix(self):
        overview = build_protocol_verification_overview(FakeProtocolAssetStore())

        self.assertEqual(overview["summary"]["asset_total"], 1)
        self.assertEqual(overview["summary"]["protocols"]["ssh"], 1)

    def test_asset_matrix_requires_existing_asset(self):
        matrix = build_protocol_verification_matrix(FakeProtocolAssetStore(), 1)

        self.assertEqual(matrix["asset"]["id"], 1)
        self.assertIn("connection_test", [step["id"] for step in matrix["steps"]])

    def test_missing_asset_raises_404(self):
        with self.assertRaises(ProtocolVerificationServiceError) as ctx:
            get_protocol_verification_asset(FakeProtocolAssetStore(), 404)

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "资产不存在")
