import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from core.custom_skill_catalog_service import (
    CUSTOM_SKILL_CATALOG_CACHE_TTL_SECONDS,
    CustomSkillCatalogServiceError,
    clear_custom_skill_catalog_cache,
    get_custom_skill_detail,
    list_custom_skill_catalog,
    scan_custom_skill_catalog,
)


class FakeDispatcher:
    def __init__(self, market_skills=None):
        self.skills_registry = {
            "local-skill": {
                "instructions": "local body",
                "source_path": "local/path",
            }
        }
        self.market_skills = market_skills or []
        self.refresh_calls = []

    def refresh_skills(self, force=False):
        self.refresh_calls.append(force)

    def get_all_registered_skills(self):
        return [{"id": "local-skill", "is_market": False}]

    def get_market_skills(self):
        return self.market_skills


class TestCustomSkillCatalogService(unittest.TestCase):
    def setUp(self):
        clear_custom_skill_catalog_cache()

    def tearDown(self):
        clear_custom_skill_catalog_cache()
        for path in (Path.cwd() / "tests").glob("tmp_custom_skill_catalog_service_*"):
            shutil.rmtree(path, ignore_errors=True)

    def _root(self, name: str) -> Path:
        root = Path.cwd() / "tests" / f"tmp_custom_skill_catalog_service_{name}"
        root.mkdir(parents=True, exist_ok=True)
        return root

    def test_scan_refreshes_dispatcher_with_force(self):
        dispatcher = FakeDispatcher()

        result = scan_custom_skill_catalog(dispatcher)

        self.assertEqual(dispatcher.refresh_calls, [True])
        self.assertEqual(result["message"], "扫描完成！本地技能库已更新。")

    def test_scan_uses_default_dispatcher_when_not_injected(self):
        dispatcher = FakeDispatcher()

        with patch("core.dispatcher.dispatcher", dispatcher):
            result = scan_custom_skill_catalog()

        self.assertEqual(dispatcher.refresh_calls, [True])
        self.assertEqual(result["message"], "扫描完成！本地技能库已更新。")

    def test_list_merges_local_registry_and_market_skills(self):
        dispatcher = FakeDispatcher(market_skills=[{"id": "market-skill", "is_market": True}])

        result = list_custom_skill_catalog(dispatcher)

        self.assertEqual(
            result["registry"],
            [
                {"id": "local-skill", "is_market": False},
                {"id": "market-skill", "is_market": True},
            ],
        )

    def test_default_list_uses_short_lived_cache_until_scan(self):
        dispatcher = FakeDispatcher(market_skills=[{"id": "market-skill", "is_market": True}])

        with patch("core.dispatcher.dispatcher", dispatcher):
            first = list_custom_skill_catalog()
            dispatcher.market_skills.append({"id": "new-market-skill", "is_market": True})
            second = list_custom_skill_catalog()
            scan_custom_skill_catalog()
            third = list_custom_skill_catalog()

        self.assertEqual(first, second)
        self.assertNotIn({"id": "new-market-skill", "is_market": True}, second["registry"])
        self.assertIn({"id": "new-market-skill", "is_market": True}, third["registry"])

    def test_default_registry_cache_is_long_enough_for_repeated_ui_opens(self):
        self.assertGreaterEqual(CUSTOM_SKILL_CATALOG_CACHE_TTL_SECONDS, 300)

    def test_detail_prefers_local_registry_body(self):
        dispatcher = FakeDispatcher()

        detail = get_custom_skill_detail("local-skill", dispatcher=dispatcher)

        self.assertEqual(detail["instructions"], "local body")
        self.assertEqual(detail["source_path"], "local/path")

    def test_detail_reads_market_skill_md_when_not_local(self):
        source = self._root("market") / "market-skill"
        source.mkdir()
        skill_md = "---\nname: market-skill\ndescription: demo\n---\n\nmarket body\n"
        (source / "SKILL.md").write_text(skill_md, encoding="utf-8")
        dispatcher = FakeDispatcher(
            market_skills=[
                {
                    "id": "market-skill",
                    "source_path": str(source),
                }
            ]
        )

        detail = get_custom_skill_detail("market-skill", dispatcher=dispatcher)

        self.assertEqual(detail["instructions"], skill_md)
        self.assertEqual(detail["source_path"], str(source))

    def test_detail_raises_not_found_for_unknown_skill(self):
        with self.assertRaises(CustomSkillCatalogServiceError) as ctx:
            get_custom_skill_detail("missing-skill", dispatcher=FakeDispatcher())

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "找不到该技能")


if __name__ == "__main__":
    unittest.main()
