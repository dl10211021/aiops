import asyncio
import json
import logging
import unittest
from unittest.mock import patch

from core.dispatcher_utility_tools import (
    _query_prefers_china_search,
    _run_baidu_html_search,
    _run_bing_html_search,
    _run_so360_html_search,
    execute_utility_tool,
    filter_assets_by_tags,
)


class DispatcherUtilityToolsTest(unittest.TestCase):
    def test_filter_assets_by_tags_hides_sensitive_fields(self):
        assets = [
            {
                "id": 1,
                "host": "10.0.0.1",
                "port": 22,
                "username": "ops",
                "password": "secret",
                "asset_type": "linux",
                "protocol": "ssh",
                "remark": "prod",
                "tags": ["prod", "db"],
            },
            {
                "id": 2,
                "host": "10.0.0.2",
                "password": "secret",
                "asset_type": "linux",
                "protocol": "ssh",
                "tags": ["dev"],
            },
        ]

        matched = filter_assets_by_tags(assets, ["prod", "db"])

        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["host"], "10.0.0.1")
        self.assertNotIn("password", matched[0])

    def test_send_notification_delegates_to_notifier(self):
        with patch("core.notifier.send_notification") as send_notification:
            send_notification.return_value = {"success": True}
            result = asyncio.run(
                execute_utility_tool(
                    "send_notification",
                    {"channel": "wechat", "title": "巡检", "content": "完成"},
                )
            )

        self.assertEqual(json.loads(result)["success"], True)
        send_notification.assert_called_once_with("wechat", "巡检", "完成")

    def test_search_knowledge_base_uses_vault_context_before_vector_store(self):
        with (
            patch(
                "core.knowledge_base_service.build_vault_rag_context_for_prompt",
                return_value={
                    "context": "[OpsCore RAG 证据上下文]\n192.168.11.132 是 kmstest 资产。",
                    "references": [{"title": "账号台账"}],
                },
            ),
            patch("core.llm_factory.get_embedding_client_and_model") as embedding_factory,
        ):
            result = asyncio.run(
                execute_utility_tool(
                    "search_knowledge_base",
                    {"query": "192.168.11.132是干嘛的"},
                )
            )

        payload = json.loads(result)
        self.assertEqual(payload["status"], "SUCCESS")
        self.assertEqual(payload["source"], "vault")
        self.assertIn("kmstest", payload["results"])
        embedding_factory.assert_not_called()

    def test_web_search_reports_success_from_search_provider(self):
        with patch(
            "core.dispatcher_utility_tools._run_duckduckgo_search",
            return_value=[{"title": "Python", "href": "https://www.python.org"}],
        ):
            result = asyncio.run(execute_utility_tool("web_search", {"query": "Python"}))

        payload = json.loads(result)
        self.assertEqual(payload["status"], "SUCCESS")
        self.assertEqual(payload["results"][0]["title"], "Python")

    def test_web_search_prefers_china_providers_for_chinese_queries(self):
        with (
            patch(
                "core.dispatcher_utility_tools._run_china_html_search",
                return_value=[{"title": "南京天气", "href": "https://weather.cma.cn", "body": "中央气象台"}],
            ) as china_search,
            patch("core.dispatcher_utility_tools._run_duckduckgo_search") as duckduckgo_search,
        ):
            result = asyncio.run(execute_utility_tool("web_search", {"query": "南京天气"}))

        payload = json.loads(result)
        self.assertEqual(payload["status"], "SUCCESS")
        self.assertEqual(payload["results"][0]["href"], "https://weather.cma.cn")
        china_search.assert_called_once()
        duckduckgo_search.assert_not_called()

    def test_web_search_falls_back_to_bing_html_when_duckduckgo_is_empty(self):
        with (
            patch("core.dispatcher_utility_tools._run_duckduckgo_search", return_value=[]),
            patch(
                "core.dispatcher_utility_tools._run_bing_html_search",
                return_value=[{"title": "Python", "href": "https://www.python.org", "body": "Official"}],
            ),
        ):
            result = asyncio.run(execute_utility_tool("web_search", {"query": "Python"}))

        payload = json.loads(result)
        self.assertEqual(payload["status"], "SUCCESS")
        self.assertEqual(payload["results"][0]["body"], "Official")

    def test_bing_html_search_parser_extracts_results(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _limit):
                return (
                    '<li class="b_algo"><h2><a href="https://www.python.org/">'
                    "Welcome to Python.org</a></h2><p>Official Python site.</p></li>"
                ).encode("utf-8")

        with patch("urllib.request.urlopen", return_value=FakeResponse()):
            results = _run_bing_html_search("Python", logger=__import__("logging").getLogger("test"))

        self.assertEqual(results[0]["title"], "Welcome to Python.org")
        self.assertEqual(results[0]["href"], "https://www.python.org/")

    def test_baidu_html_search_parser_extracts_results(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _limit):
                return (
                    '<div class="result c-container"><h3><a href="https://weather.cma.cn/">'
                    "中国天气</a></h3><div class=\"c-abstract\">中央气象台数据。</div></div></div>"
                ).encode("utf-8")

        with patch("urllib.request.urlopen", return_value=FakeResponse()):
            results = _run_baidu_html_search("南京天气", logger=logging.getLogger("test"))

        self.assertEqual(results[0]["title"], "中国天气")
        self.assertEqual(results[0]["href"], "https://weather.cma.cn/")
        self.assertIn("中央气象台", results[0]["body"])

    def test_so360_html_search_parser_extracts_results(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _limit):
                return (
                    '<li class="res-list"><h3><a href="https://www.qweather.com/">'
                    "和风天气</a></h3><p>天气预报与气象服务。</p></li>"
                ).encode("utf-8")

        with patch("urllib.request.urlopen", return_value=FakeResponse()):
            results = _run_so360_html_search("南京天气", logger=logging.getLogger("test"))

        self.assertEqual(results[0]["title"], "和风天气")
        self.assertEqual(results[0]["href"], "https://www.qweather.com/")

    def test_query_prefers_china_search_for_cn_context(self):
        self.assertTrue(_query_prefers_china_search("南京天气", {}))
        self.assertTrue(_query_prefers_china_search("nanjing weather", {}))
        self.assertTrue(_query_prefers_china_search("Oracle RAC 故障", {"region": "cn"}))
        self.assertFalse(_query_prefers_china_search("python documentation", {}))


if __name__ == "__main__":
    unittest.main()
