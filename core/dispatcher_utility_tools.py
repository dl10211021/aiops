"""Notification and search-style utility tool execution."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Iterable

UTILITY_TOOL_NAMES = {
    "send_notification",
    "search_knowledge_base",
    "web_search",
    "search_assets_by_tag",
}


async def execute_utility_tool(
    tool_call_name: str,
    args: dict[str, Any],
    logger: logging.Logger | None = None,
) -> str:
    log = logger or logging.getLogger(__name__)
    if tool_call_name == "send_notification":
        return await _send_notification(args, log)
    if tool_call_name == "search_knowledge_base":
        return await _search_knowledge_base(args)
    if tool_call_name == "web_search":
        return await _web_search(args, log)
    if tool_call_name == "search_assets_by_tag":
        return await _search_assets_by_tag(args, log)
    return '{"error": "Unknown utility tool"}'


def filter_assets_by_tags(assets: Iterable[dict[str, Any]], tags_to_search: Iterable[str]) -> list[dict[str, Any]]:
    tags = list(tags_to_search)
    matched_assets = []
    for asset in assets:
        asset_tags = asset.get("tags", [])
        if all(tag in asset_tags for tag in tags):
            matched_assets.append(
                {
                    "id": asset.get("id"),
                    "host": asset.get("host"),
                    "port": asset.get("port"),
                    "username": asset.get("username"),
                    "asset_type": asset.get("asset_type"),
                    "protocol": asset.get("protocol"),
                    "remark": asset.get("remark"),
                    "tags": asset.get("tags"),
                }
            )
    return matched_assets


async def _send_notification(args: dict[str, Any], logger: logging.Logger) -> str:
    channel = args.get("channel", "auto")
    title = args.get("title")
    content = args.get("content")

    def do_notify():
        logger.info(f"AI 发起了群组通知 -> 渠道: {channel}, 标题: {title}")
        from core.notifier import send_notification

        result = send_notification(channel, title, content)
        return json.dumps(result)

    return await asyncio.to_thread(do_notify)


async def _search_knowledge_base(args: dict[str, Any]) -> str:
    query = str(args.get("query") or "").strip()
    if not query:
        return json.dumps({"error": "知识库检索关键词不能为空。"}, ensure_ascii=False)

    try:
        from core.knowledge_base_service import build_vault_rag_context_for_prompt

        vault_result = await asyncio.to_thread(build_vault_rag_context_for_prompt, query, limit=5)
        context = str(vault_result.get("context") or "").strip()
        if context:
            return json.dumps(
                {
                    "status": "SUCCESS",
                    "source": "vault",
                    "results": context,
                    "references": vault_result.get("references") or [],
                },
                ensure_ascii=False,
            )
    except Exception as exc:
        logging.getLogger(__name__).warning("vault knowledge lookup failed: %s", exc)

    try:
        from core.llm_factory import get_embedding_client_and_model
        from core.rag import kb_manager

        client, embedding_model = get_embedding_client_and_model()
        result = await asyncio.wait_for(
            kb_manager.search(query, client, embedding_model), timeout=60.0
        )
        return json.dumps({"status": "SUCCESS", "source": "vector", "results": result}, ensure_ascii=False)
    except asyncio.TimeoutError:
        return json.dumps({"error": "知识库检索超时被强制截断。"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"知识库检索异常: {str(e)}"}, ensure_ascii=False)


def _run_duckduckgo_search(query: str, logger: logging.Logger) -> list[dict[str, Any]]:
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS

    logger.info(f"AI 发起了外网检索: {query}")
    with DDGS() as ddgs:
        return [r for r in ddgs.text(query, max_results=5)]


async def _web_search(args: dict[str, Any], logger: logging.Logger) -> str:
    query = str(args.get("query") or "").strip()
    if not query:
        return json.dumps({"error": "联网搜索关键词不能为空。"}, ensure_ascii=False)
    try:
        results = await asyncio.wait_for(
            asyncio.to_thread(_run_duckduckgo_search, query, logger),
            timeout=20.0,
        )
        return json.dumps({"status": "SUCCESS", "results": results}, ensure_ascii=False)
    except asyncio.TimeoutError:
        return json.dumps({"error": "联网搜索超时，请稍后重试或换一个更具体的关键词。"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"外网检索异常: {str(e)}"}, ensure_ascii=False)


async def _search_assets_by_tag(args: dict[str, Any], logger: logging.Logger) -> str:
    tags_to_search = args.get("tags", [])
    from core.memory import memory_db

    try:
        all_assets = await asyncio.to_thread(memory_db.get_all_assets)
        matched_assets = filter_assets_by_tags(all_assets, tags_to_search)
        logger.info(f"AI 发起了全局资产检索 tags={tags_to_search}, 匹配 {len(matched_assets)} 台")
        return json.dumps(
            {
                "status": "SUCCESS",
                "matched_count": len(matched_assets),
                "assets": matched_assets,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        logger.error(f"search_assets_by_tag 发生异常: {e}")
        return json.dumps({"error": f"全局检索异常: {str(e)}"})
