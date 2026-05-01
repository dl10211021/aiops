import unittest

from core.asset_service import (
    AssetServiceError,
    batch_import_asset_records,
    get_saved_asset_record,
    list_saved_asset_records,
    remove_saved_asset_record,
    save_asset_record,
    update_saved_asset_record,
)
from core.memory import DEFAULT_SENSITIVE_EXTRA_ARG_KEYS


class FakeAssetStore:
    sensitive_keys = list(DEFAULT_SENSITIVE_EXTRA_ARG_KEYS)

    def __init__(self):
        self.saved = None
        self.updated = None
        self.deleted = []
        self.batch_saved = None
        self.assets = {
            1: {
                "id": 1,
                "remark": "Prometheus",
                "host": "prom.local",
                "port": 9090,
                "username": "api",
                "password": "secret",
                "asset_type": "prometheus",
                "protocol": "http_api",
                "agent_profile": "default",
                "extra_args": {"api_token": "token", "category": "monitor"},
                "skills": ["prometheus"],
                "tags": ["monitor"],
            }
        }

    def get_all_assets(self):
        return [dict(asset) for asset in self.assets.values()]

    def save_asset(self, *args):
        self.saved = args

    def get_asset(self, asset_id: int):
        asset = self.assets.get(asset_id)
        return dict(asset) if asset else None

    def update_asset(self, asset_id: int, payload: dict):
        self.updated = (asset_id, payload)
        if asset_id not in self.assets:
            return None
        updated = dict(self.assets[asset_id])
        updated.update(payload)
        return updated

    def delete_asset(self, asset_id: int):
        self.deleted.append(asset_id)

    def save_assets_batch(self, items: list[dict]):
        self.batch_saved = items


class TestAssetService(unittest.TestCase):
    def test_list_and_get_mask_sensitive_fields(self):
        store = FakeAssetStore()

        assets = list_saved_asset_records(store)
        asset = get_saved_asset_record(store, 1)

        self.assertEqual(assets[0]["password"], "********")
        self.assertEqual(assets[0]["extra_args"]["api_token"], "********")
        self.assertEqual(asset["password"], "********")
        self.assertEqual(asset["extra_args"]["category"], "monitor")

    def test_save_asset_maps_payload_to_memory_call(self):
        store = FakeAssetStore()
        save_asset_record(
            store,
            {
                "remark": "K8s",
                "host": "k8s.local",
                "port": 6443,
                "username": "admin",
                "password": "secret",
                "asset_type": "k8s",
                "agent_profile": "default",
                "extra_args": {"bearer_token": "token"},
                "skills": ["k8s-ops"],
                "tags": ["prod"],
                "protocol": "k8s",
            },
        )

        self.assertEqual(store.saved[1], "k8s.local")
        self.assertEqual(store.saved[5], "k8s")
        self.assertEqual(store.saved[10], "k8s")

    def test_update_missing_asset_raises_404(self):
        with self.assertRaises(AssetServiceError) as ctx:
            update_saved_asset_record(FakeAssetStore(), 404, {"host": "missing"})

        self.assertEqual(ctx.exception.status_code, 404)

    def test_delete_delegates_to_store_without_changing_legacy_missing_behavior(self):
        store = FakeAssetStore()

        remove_saved_asset_record(store, 404)

        self.assertEqual(store.deleted, [404])

    def test_batch_import_requires_items_and_returns_counts(self):
        store = FakeAssetStore()

        result = batch_import_asset_records(store, [{"host": "db.local"}])

        self.assertEqual(result, {"imported": 1, "total": 1})
        self.assertEqual(store.batch_saved, [{"host": "db.local"}])
        with self.assertRaises(AssetServiceError) as ctx:
            batch_import_asset_records(store, [])
        self.assertEqual(ctx.exception.status_code, 422)

    def test_batch_import_wraps_store_errors(self):
        class BrokenStore(FakeAssetStore):
            def save_assets_batch(self, items: list[dict]):
                raise RuntimeError("disk full")

        with self.assertRaises(AssetServiceError) as ctx:
            batch_import_asset_records(BrokenStore(), [{"host": "db.local"}])

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("disk full", ctx.exception.detail)
