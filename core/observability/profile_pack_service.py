from __future__ import annotations

from core.observability.profile_packs import builtin_profile_packs
from core.observability.store import ObservabilityStore, get_observability_store


class ProfilePackService:
    def __init__(self, store: ObservabilityStore | None = None):
        self.store = store or get_observability_store()

    def sync_builtin_packs(self) -> list[dict]:
        records = []
        for pack in builtin_profile_packs():
            records.append(self.store.upsert("profile_packs", pack.to_record()))
        return records

    def list_packs(self) -> list[dict]:
        self.sync_builtin_packs()
        return self.store.list("profile_packs", order_by="id ASC")

    def get_pack(self, pack_id: str) -> dict | None:
        self.sync_builtin_packs()
        return self.store.get("profile_packs", pack_id)


def get_profile_pack_service(store: ObservabilityStore | None = None) -> ProfilePackService:
    return ProfilePackService(store)

